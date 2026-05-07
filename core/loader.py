import sqlite3
import pandas as pd
from datetime import timezone, timedelta, datetime
from core.database import get_conn

KST = timezone(timedelta(hours=9))

def epoch_ms_to_date(ms):
    return datetime.fromtimestamp(ms / 1000, tz=KST).strftime("%Y-%m-%d")

def read_sh_csv(path):
    return pd.read_csv(path, skiprows=1, on_bad_lines='skip')

# ── 걸음수 ──────────────────────────────────────────────
def load_steps(csv_path):
    df = read_sh_csv(csv_path)
    cols = df.columns.tolist()

    df['day_ms']   = pd.to_numeric(df[cols[11]], errors='coerce')
    df['count']    = pd.to_numeric(df[cols[4]],  errors='coerce')
    df['distance'] = pd.to_numeric(df[cols[7]],  errors='coerce')
    df['calorie']  = pd.to_numeric(df[cols[8]],  errors='coerce')
    df = df.dropna(subset=['day_ms', 'count'])

    # 같은 날짜 중 걸음수 가장 많은 행만 사용
    df['date'] = df['day_ms'].apply(epoch_ms_to_date)
    df = df.sort_values('count', ascending=False).drop_duplicates('date')

    conn = get_conn()
    inserted = 0
    for _, row in df.iterrows():
        conn.execute("""
            INSERT OR REPLACE INTO steps_daily (date, count, distance_m, calorie)
            VALUES (?, ?, ?, ?)
        """, (row['date'], int(row['count']),
              float(row['distance']) if pd.notna(row['distance']) else None,
              float(row['calorie'])  if pd.notna(row['calorie'])  else None))
        inserted += 1
    conn.commit()
    conn.close()
    print(f"✅ 걸음수 적재 완료: {inserted}일치")

# ── 수면 ────────────────────────────────────────────────
def load_sleep(csv_path):
    df = read_sh_csv(csv_path)

    conn = get_conn()
    inserted = 0

    for _, row in df.iterrows():
        # start_time 후보 2개 중 유효한 것 사용
        start_raw = row.get('physical_recovery')
        end_raw   = row.get('is_integrated')

        # 둘 다 없으면 두번째 후보
        if pd.isna(start_raw):
            start_raw = row.get('com.samsung.health.sleep.create_sh_ver')
            end_raw   = row.get('com.samsung.health.sleep.pkg_name')

        if pd.isna(start_raw):
            continue

        try:
            start_dt = pd.to_datetime(start_raw, utc=True).tz_convert('Asia/Seoul')
            end_dt   = pd.to_datetime(end_raw,   utc=True).tz_convert('Asia/Seoul')
        except:
            continue

        date         = start_dt.strftime("%Y-%m-%d")
        sleep_score  = pd.to_numeric(row.get('efficiency'),         errors='coerce')
        duration_min = pd.to_numeric(row.get('sleep_score'),        errors='coerce')
        efficiency   = pd.to_numeric(row.get('original_efficiency'),errors='coerce')
        mental       = pd.to_numeric(row.get('mental_recovery'),    errors='coerce')
        physical     = pd.to_numeric(row.get('wake_score'),         errors='coerce')
        rem_min      = pd.to_numeric(row.get('rem_score'),          errors='coerce')
        light_min    = pd.to_numeric(row.get('total_light_duration'),errors='coerce')

        # duration이 비현실적이면 스킵 (0~900분 범위만)
        if pd.isna(duration_min) or not (0 < duration_min < 900):
            continue

        conn.execute("""
            INSERT INTO sleep
            (date, start_time, end_time, duration_min, sleep_score,
             efficiency, physical_recovery, mental_recovery, total_rem_min)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date,
              start_dt.isoformat(), end_dt.isoformat(),
              float(duration_min),
              float(sleep_score)  if pd.notna(sleep_score)  else None,
              float(efficiency)   if pd.notna(efficiency)   else None,
              float(physical)     if pd.notna(physical)     else None,
              float(mental)       if pd.notna(mental)       else None,
              float(rem_min)      if pd.notna(rem_min)      else None))
        inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ 수면 적재 완료: {inserted}건")

# ── 심박수 ───────────────────────────────────────────────
def load_heart_rate(csv_path):
    df = read_sh_csv(csv_path)

    TAG_MAP = {
        '21000': '일반', '21301': '안정', '21310': '운동후',
        '21316': '일상안정', '21118': '운동중', '23333': '수면중',
    }

    conn = get_conn()
    inserted = 0

    for _, row in df.iterrows():
        start_raw = row.get('com.samsung.health.heart_rate.heart_beat_count')
        if pd.isna(start_raw):
            continue
        try:
            dt = pd.to_datetime(start_raw, utc=True).tz_convert('Asia/Seoul').isoformat()
        except:
            continue

        bpm     = pd.to_numeric(row.get('com.samsung.health.heart_rate.client_data_id'), errors='coerce')
        bpm_max = pd.to_numeric(row.get('com.samsung.health.heart_rate.max'), errors='coerce')
        bpm_min = pd.to_numeric(row.get('com.samsung.health.heart_rate.datauuid'), errors='coerce')
        tag_raw = str(int(row.get('source'))) if pd.notna(row.get('source')) else None
        tag     = TAG_MAP.get(tag_raw, '일반')

        if pd.isna(bpm) or bpm > 250 or bpm < 30:
            continue

        conn.execute("""
            INSERT INTO heart_rate (datetime, bpm, bpm_min, bpm_max, tag)
            VALUES (?, ?, ?, ?, ?)
        """, (dt, int(bpm),
              int(bpm_min) if pd.notna(bpm_min) and bpm_min < 250 else None,
              int(bpm_max) if pd.notna(bpm_max) and bpm_max < 250 else None,
              tag))
        inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ 심박수 적재 완료: {inserted}건")

# ── 인바디 수동입력 ──────────────────────────────────────
def load_inbody(data: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO inbody
        (measured_at, weight_kg, skeletal_muscle_kg, body_fat_kg, body_fat_pct,
         bmi, arm_r_kg, arm_l_kg, leg_r_kg, leg_l_kg, trunk_kg, bmr_kcal)
        VALUES (:measured_at, :weight_kg, :skeletal_muscle_kg, :body_fat_kg,
                :body_fat_pct, :bmi, :arm_r_kg, :arm_l_kg,
                :leg_r_kg, :leg_l_kg, :trunk_kg, :bmr_kcal)
    """, data)
    conn.commit()
    conn.close()
    print(f"✅ 인바디 입력 완료: {data['measured_at']}")


if __name__ == "__main__":
    from pathlib import Path

    # ↓↓ 여기에 실제 CSV 파일 경로 입력 ↓↓
    STEP_CSV  = "data/com.samsung.shealth.step_daily_trend.20260430122188.csv"
    SLEEP_CSV = "data/com.samsung.shealth.sleep.20260430122188.csv"
    HR_CSV    = "data/com.samsung.shealth.tracker.heart_rate.20260430122188.csv"
    
    if Path(STEP_CSV).exists():
        load_steps(STEP_CSV)
    else:
        print(f"⚠️  파일 없음: {STEP_CSV}")

    if Path(SLEEP_CSV).exists():
        load_sleep(SLEEP_CSV)
    else:
        print(f"⚠️  파일 없음: {SLEEP_CSV}")

    if Path(HR_CSV).exists():
        load_heart_rate(HR_CSV)
    else:
        print(f"⚠️  파일 없음: {HR_CSV}")

    # 인바디 샘플 (실제 값으로 수정)
    load_inbody({
        # 인바디는 처음 한 번만 실행 (이후 주석처리)
        # load_inbody({...})
        'measured_at': '2026-05-05',
        'weight_kg': 70.0,
        'skeletal_muscle_kg': 32.0,
        'body_fat_kg': 11.0,
        'body_fat_pct': 15.7,
        'bmi': 22.5,
        'arm_r_kg': 3.1, 'arm_l_kg': 3.0,
        'leg_r_kg': 9.5, 'leg_l_kg': 9.4,
        'trunk_kg': 26.8,
        'bmr_kcal': 1750,
    })