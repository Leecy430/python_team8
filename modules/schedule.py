import anthropic
import base64
import json
from core.database import get_conn
import os
from dotenv import load_dotenv
load_dotenv(override=True)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")

def parse_schedule_from_image(image_path):
    """이미지에서 시간표 추출 (Claude Vision)"""
    img_data = image_to_base64(image_path)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_data
                    }
                },
                {
                    "type": "text",
                    "text": """이 시간표 이미지를 분석해서 아래 JSON 형식으로만 응답해줘. 다른 말은 하지 마.

[
  {
    "day_of_week": 0,
    "start_time": "09:00",
    "end_time": "11:00",
    "subject": "과목명",
    "professor": "교수명",
    "classroom": "강의실"
  }
]

day_of_week: 0=월 1=화 2=수 3=목 4=금
시간은 HH:MM 형식으로."""
                }
            ]
        }]
    )

    text = response.content[0].text.strip()
    # ```json 블록 제거
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    print("Claude 응답:", text[:200])  # 디버그용
    return json.loads(text)

def save_schedule(schedule_list):
    """파싱된 시간표 DB에 저장"""
    conn = get_conn()
    conn.execute("DELETE FROM schedule")  # 기존 시간표 초기화
    conn.executemany("""
        INSERT INTO schedule (day_of_week, start_time, end_time, subject, professor, classroom)
        VALUES (:day_of_week, :start_time, :end_time, :subject, :professor, :classroom)
    """, schedule_list)
    conn.commit()
    conn.close()
    print(f"✅ 시간표 저장 완료: {len(schedule_list)}개 수업")

def get_schedule():
    """시간표 전체 조회"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT day_of_week, start_time, end_time, subject, professor, classroom
        FROM schedule ORDER BY day_of_week, start_time
    """).fetchall()
    conn.close()
    days = ['월','화','수','목','금']
    return [dict(zip(['day_of_week','start_time','end_time','subject','professor','classroom'], r)) for r in rows]

def get_free_slots():
    """30분 이상 공강 탐색"""
    conn = get_conn()
    schedule = conn.execute("""
        SELECT day_of_week, start_time, end_time
        FROM schedule ORDER BY day_of_week, start_time
    """).fetchall()
    conn.close()

    from itertools import groupby
    free_slots = []
    for day, classes in groupby(schedule, key=lambda x: x[0]):
        classes = list(classes)
        for i in range(len(classes) - 1):
            end   = classes[i][2]
            start = classes[i+1][1]
            # 분 계산
            end_min   = int(end[:2])*60   + int(end[3:])
            start_min = int(start[:2])*60 + int(start[3:])
            gap = start_min - end_min
            if gap >= 30:
                days = ['월','화','수','목','금']
                free_slots.append({
                    'day': days[day],
                    'start': end,
                    'end': start,
                    'duration_min': gap
                })
    return free_slots