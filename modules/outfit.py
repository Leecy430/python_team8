"""
modules/outfit.py
시간표 + 캘린더 + 시간대별 날씨 → 옷차림/우산 추천
"""

import anthropic
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from core.database import get_conn
from modules.weather import get_hourly_weather
from modules.calendar_sync import get_today_events

load_dotenv(override=True)
KST = timezone(timedelta(hours=9))

_outfit_cache: dict = {}  # { "YYYY-MM-DD": result }

def get_today_schedule(day_of_week: int = None) -> list[dict]:
    """시간표에서 오늘 수업 목록 반환"""
    if day_of_week is None:
        day_of_week = datetime.now(tz=KST).weekday()

    conn = get_conn()
    rows = conn.execute("""
        SELECT start_time, end_time, subject, classroom
        FROM schedule WHERE day_of_week = ?
        ORDER BY start_time
    """, (day_of_week,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_outfit_recommendation(location: str = "Michuhol-gu, Incheon") -> dict:
    load_dotenv(override=True)
    now = datetime.now(tz=KST)
    today = now.strftime('%Y-%m-%d')

    if today in _outfit_cache:
        return _outfit_cache[today]

    api_key = os.getenv("ANTHROPIC_API_KEY").strip()
    client = anthropic.Anthropic(api_key=api_key)
    day_of_week = now.weekday()
    days = ['월', '화', '수', '목', '금', '토', '일']

    # 시간표 + 캘린더 일정 통합
    schedule = get_today_schedule(day_of_week)
    calendar = get_today_events(today)

    # 모든 일정 합치기
    all_events = []
    for s in schedule:
        all_events.append({
            "title": s["subject"],
            "start": s["start_time"],
            "end":   s["end_time"],
            "type":  "수업"
        })
    for c in calendar:
        start = c["start_time"]
        end   = c["end_time"]
        start = start[11:16] if len(start) > 10 else "종일"
        end   = end[11:16]   if len(end) > 10   else "종일"
        all_events.append({
            "title": c["title"],
            "start": start,
            "end":   end,
            "type":  "일정"
        })
    all_events.sort(key=lambda x: x["start"] if x["start"] != "종일" else "00:00")

    # 출발/귀가 시간 계산은 종일 일정 제외
    timed_events = [e for e in all_events if e["start"] != "종일"]

    if not timed_events:
        return {
            "has_events": False,
            "message": f"오늘({days[day_of_week]})은 일정이 없어요!" if not all_events
                       else f"오늘({days[day_of_week]})은 종일 일정만 있어요!",
        }

    first_event = timed_events[0]
    last_event  = timed_events[-1]

    h, m = map(int, first_event["start"].split(":"))
    dep_total = h * 60 + m - 30
    dep_h, dep_m = divmod(dep_total, 60)
    departure = f"{dep_h:02d}:{dep_m:02d}"
    arrival   = last_event["end"]

    hourly = get_hourly_weather(location)
    dep_hour  = int(departure.split(":")[0])
    arr_hour  = int(arrival.split(":")[0])

    dep_weather = hourly[dep_hour]
    arr_weather = hourly[min(arr_hour, 23)]
    mid_weather = hourly[(dep_hour + arr_hour) // 2]

    events_text = "\n".join([
        f"  - {e['start']}~{e['end']} {e['title']} ({e['type']})"
        for e in all_events
    ])

    prompt = f"""오늘 나의 일정과 날씨야:

【오늘 일정】
{events_text}

【나가는 시간: {departure}】
- 기온: {dep_weather['temp_c']}°C (체감 {dep_weather['feels_like']}°C)
- 날씨: {dep_weather['condition']}
- 비: {'옴' if dep_weather['is_raining'] else '없음'}
- 자외선 지수: {dep_weather['uv']}

【귀가 시간: {arrival}】
- 기온: {arr_weather['temp_c']}°C (체감 {arr_weather['feels_like']}°C)
- 날씨: {arr_weather['condition']}
- 비: {'옴' if arr_weather['is_raining'] else '없음'}
- 자외선 지수: {arr_weather['uv']}

【중간 시간대】
- 기온: {mid_weather['temp_c']}°C
- 날씨: {mid_weather['condition']}
- 자외선 지수: {mid_weather['uv']}

나가는 시간과 귀가 시간의 온도차, 비 여부, 자외선 지수를 고려해서 옷차림을 추천해줘.
자외선 지수 3 이상이면 썬크림, 6 이상이면 양산도 추천해줘.
낮에 나가서 밤에 들어오면 겉옷을 챙기라고 해줘.

아래 JSON 형식으로만 응답해줘. 다른 말은 하지 마.

{{
  "departure": "{departure}",
  "arrival": "{arrival}",
  "umbrella": true or false,
  "sunscreen": true or false,
  "parasol": true or false,
  "outer": "겉옷 추천 또는 필요없음",
  "top": "상의 추천",
  "bottom": "하의 추천",
  "extra": "추가 조언 한 줄 (자외선, 우산, 온도차 등)",
  "comment": "전체 한 줄 코멘트"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    result = json.loads(text.strip())
    result["has_events"] = True
    result["events"] = all_events
    result["dep_weather"] = dep_weather
    result["arr_weather"] = arr_weather
    _outfit_cache[today] = result
    return result