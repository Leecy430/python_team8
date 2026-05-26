"""
modules/calendar_sync.py
Google Calendar ICS URL fetch → 파싱 → DB 저장
- 서버 시작 시 1회 sync
- 매일 06:00 KST 자동 sync
- 캘린더 2개 (개인 + 한국 공휴일) 합쳐서 저장
"""

import requests
from icalendar import Calendar
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

load_dotenv(override=True)
KST = timezone(timedelta(hours=9))

ICS_URLS = [
    os.getenv("GOOGLE_CALENDAR_ICS_URL_1", "..."),
    os.getenv("GOOGLE_CALENDAR_ICS_URL_2", "..."),
]

def fetch_ics(url: str) -> bytes:
    """URL에서 ICS 파일 fetch"""
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.content

def sync_calendar() -> int:
    """ICS URL 2개 fetch → 파싱 → calendar 테이블 저장"""
    from core.database import get_conn
    conn = get_conn()
    conn.execute('DELETE FROM calendar')
    inserted = 0

    for url in ICS_URLS:
        try:
            content = fetch_ics(url)
            cal = Calendar.from_ical(content)

            for component in cal.walk():
                if component.name != 'VEVENT':
                    continue

                title = str(component.get('SUMMARY', '제목없음'))
                start = component.get('DTSTART').dt
                end   = component.get('DTEND').dt

                if hasattr(start, 'hour'):
                    start_str = start.astimezone(KST).strftime('%Y-%m-%d %H:%M')
                    end_str   = end.astimezone(KST).strftime('%Y-%m-%d %H:%M')
                else:
                    start_str = start.strftime('%Y-%m-%d')
                    end_str   = end.strftime('%Y-%m-%d')

                conn.execute('''
                    INSERT INTO calendar (title, start_time, end_time, location, description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, start_str, end_str,
                      str(component.get('LOCATION', '')),
                      str(component.get('DESCRIPTION', ''))))
                inserted += 1

        except Exception as e:
            print(f"[calendar_sync] {url} fetch 실패: {e}")

    conn.commit()
    conn.close()
    print(f"[calendar_sync] {inserted}개 일정 sync 완료 ({datetime.now(tz=KST).strftime('%Y-%m-%d %H:%M')})")
    return inserted

def get_today_events(date: str = None) -> list[dict]:
    """오늘 일정 조회"""
    from core.database import get_conn
    if date is None:
        date = datetime.now(tz=KST).strftime('%Y-%m-%d')

    conn = get_conn()
    rows = conn.execute('''
        SELECT title, start_time, end_time, location
        FROM calendar
        WHERE start_time LIKE ?
        ORDER BY start_time
    ''', (f'{date}%',)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_week_events(date: str = None) -> list[dict]:
    """이번 주 일정 조회"""
    from core.database import get_conn
    if date is None:
        today = datetime.now(tz=KST)
    else:
        today = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=KST)

    week_start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
    week_end   = (today + timedelta(days=6 - today.weekday())).strftime('%Y-%m-%d')

    conn = get_conn()
    rows = conn.execute('''
        SELECT title, start_time, end_time, location
        FROM calendar
        WHERE start_time >= ? AND start_time <= ?
        ORDER BY start_time
    ''', (week_start, week_end + ' 23:59')).fetchall()
    conn.close()
    return [dict(r) for r in rows]