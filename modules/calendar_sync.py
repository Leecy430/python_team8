"""
modules/calendar_sync.py
Google Calendar ICS 파일 파싱 → DB 저장
"""

from icalendar import Calendar
import sqlite3
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(override=True)
KST = timezone(timedelta(hours=9))
ICS_PATH = 'data/leecy430@gmail.com.ics'

def sync_calendar_from_ics(ics_path: str = ICS_PATH) -> int:
    """ICS 파일 파싱 → calendar 테이블 저장"""
    from core.database import get_conn
    conn = get_conn()
    conn.execute('DELETE FROM calendar')
    inserted = 0

    with open(ics_path, 'rb') as f:
        cal = Calendar.from_ical(f.read())

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

    conn.commit()
    conn.close()
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