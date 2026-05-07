import sqlite3
import pandas as pd
from core.database import get_conn

# ── 오늘 기준 단일 조회 ─────────────────────────────────

def get_today_steps(date=None):
    conn = get_conn()
    if date is None:
        date = conn.execute("SELECT MAX(date) FROM steps_daily").fetchone()[0]
    row = conn.execute(
        "SELECT date, count, distance_m, calorie FROM steps_daily WHERE date=?", (date,)
    ).fetchone()
    conn.close()
    if row is None:
        return {'date': date, 'count': 0, 'distance_m': 0, 'calorie': 0}
    return dict(row)

def get_today_sleep(date=None):
    conn = get_conn()
    if date is None:
        date = conn.execute("SELECT MAX(date) FROM sleep").fetchone()[0]
    row = conn.execute("""
        SELECT date, duration_min, sleep_score, efficiency,
               physical_recovery, mental_recovery, total_rem_min
        FROM sleep WHERE date <= ?
        ORDER BY date DESC, duration_min DESC LIMIT 1
    """, (date,)).fetchone()
    conn.close()
    return dict(row) if row else {}

def get_today_heart_rate(date=None):
    conn = get_conn()
    if date is None:
        date = conn.execute("SELECT MAX(date(datetime)) FROM heart_rate").fetchone()[0]
    row = conn.execute("""
        SELECT datetime, bpm, bpm_min, bpm_max, tag
        FROM heart_rate WHERE date(datetime) = ?
        ORDER BY datetime DESC LIMIT 1
    """, (date,)).fetchone()
    conn.close()
    return dict(row) if row else {}

def get_latest_inbody():
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM inbody ORDER BY measured_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else {}

# ── 기간별 시계열 (차트용) ──────────────────────────────

def get_steps_timeseries(days=30):
    conn = get_conn()
    df = pd.read_sql("""
        SELECT date, count, distance_m, calorie
        FROM steps_daily ORDER BY date DESC LIMIT ?
    """, conn, params=(days,))
    conn.close()
    return df.sort_values('date').reset_index(drop=True)

def get_sleep_timeseries(days=30):
    conn = get_conn()
    df = pd.read_sql("""
        SELECT date, duration_min, sleep_score, efficiency
        FROM sleep ORDER BY date DESC LIMIT ?
    """, conn, params=(days,))
    conn.close()
    return df.sort_values('date').reset_index(drop=True)

def get_heartrate_timeseries(date=None):
    conn = get_conn()
    if date is None:
        date = conn.execute("SELECT MAX(date(datetime)) FROM heart_rate").fetchone()[0]
    df = pd.read_sql("""
        SELECT datetime, bpm, bpm_min, bpm_max, tag
        FROM heart_rate WHERE date(datetime) = ?
        ORDER BY datetime
    """, conn, params=(date,))
    conn.close()
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df

# ── 대시보드 통합 스냅샷 ────────────────────────────────

def get_snapshot(date=None):
    return {
        'steps'     : get_today_steps(date),
        'sleep'     : get_today_sleep(date),
        'heart_rate': get_today_heart_rate(date),
        'inbody'    : get_latest_inbody(),
    }

# ── 전체 날짜 목록 ──────────────────────────────────────

def get_all_dates():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT date FROM steps_daily ORDER BY date").fetchall()
    conn.close()
    return [r[0] for r in rows]

# ── CSV Replay 스트림 ───────────────────────────────────

def replay_stream(start=None, end=None):
    """
    날짜 순서대로 스냅샷을 yield
    사용 예:
        for date, snap in replay_stream('2026-01-01', '2026-04-30'):
            print(date, snap['steps']['count'])
    """
    dates = get_all_dates()
    if start:
        dates = [d for d in dates if d >= start]
    if end:
        dates = [d for d in dates if d <= end]
    for d in dates:
        yield d, get_snapshot(d)


if __name__ == "__main__":
    dates = get_all_dates()
    print(f"DB 날짜 범위: {dates[0]} ~ {dates[-1]} ({len(dates)}일)")

    print("\n=== 최근 5일 스냅샷 ===")
    for d in dates[-5:]:
        snap = get_snapshot(d)
        s = snap['steps']
        sl = snap['sleep']
        hr = snap['heart_rate']
        steps_str = f"{s.get('count', 0):,}보"
        dur_str   = f"{sl.get('duration_min', 0):.0f}분" if sl.get('duration_min') else '-'
        bpm_str   = f"{hr.get('bpm', '-')}bpm"
        print(f"  {d}  👟{steps_str}  💤{dur_str}  ❤️{bpm_str}")