"""
modules/calendar_sync.py
Google Calendar API 연동 - 오늘 일정 가져오기
"""

import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

load_dotenv(override=True)

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CREDENTIALS_PATH = 'db/credentials.json'
TOKEN_PATH = 'db/token.pickle'
KST = timezone(timedelta(hours=9))

def get_calendar_service():
    """Google Calendar 서비스 객체 반환"""
    creds = None

    # 기존 토큰 있으면 불러오기
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as f:
            creds = pickle.load(f)

    # 토큰 없거나 만료됐으면 재인증
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as f:
            pickle.dump(creds, f)

    return build('calendar', 'v3', credentials=creds)

def get_today_events() -> list[dict]:
    """
    오늘 구글 캘린더 일정 가져오기
    반환: [{"title": "...", "start": "HH:MM", "end": "HH:MM"}, ...]
    """
    service = get_calendar_service()

    now = datetime.now(tz=KST)
    today_start = now.replace(hour=0, minute=0, second=0).isoformat()
    today_end   = now.replace(hour=23, minute=59, second=59).isoformat()

    events_result = service.events().list(
        calendarId='primary',
        timeMin=today_start,
        timeMax=today_end,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    result = []
    for e in events:
        start = e['start'].get('dateTime', e['start'].get('date', ''))
        end   = e['end'].get('dateTime', e['end'].get('date', ''))
        # HH:MM 형식으로 변환
        try:
            start_time = datetime.fromisoformat(start).astimezone(KST).strftime('%H:%M')
            end_time   = datetime.fromisoformat(end).astimezone(KST).strftime('%H:%M')
        except:
            start_time = start
            end_time   = end
        result.append({
            "title": e.get('summary', '제목 없음'),
            "start": start_time,
            "end":   end_time,
        })
    return result