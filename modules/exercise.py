"""
modules/exercise.py
운동 루틴 추천 + 시간표 공강 운동 추천 + MET 기반 칼로리 계산
"""

import anthropic
import json
import os
from dotenv import load_dotenv
load_dotenv(override=True)
from core.database import get_conn
from datetime import datetime, timezone, timedelta

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
KST = timezone(timedelta(hours=9))

# ── MET 기반 칼로리 계산 ─────────────────────────────────

MET_TABLE = {
    "걷기":        3.5,
    "달리기":      8.0,
    "스쿼트":      5.0,
    "푸시업":      4.0,
    "플랭크":      3.0,
    "줄넘기":      10.0,
    "자전거":      6.0,
    "계단오르기":  6.0,
    "스트레칭":    2.5,
    "요가":        2.5,
    "데드리프트":  6.0,
    "벤치프레스":  5.0,
}

def calc_calories(exercise_name: str, duration_min: float, weight_kg: float) -> float:
    """MET 기반 칼로리 소모 계산"""
    met = MET_TABLE.get(exercise_name, 4.0)
    return met * weight_kg * (duration_min / 60)

def save_exercise(name: str, duration_min: float, weight_kg: float = 70.0):
    """운동 기록 저장"""
    kcal = calc_calories(name, duration_min, weight_kg)
    met = MET_TABLE.get(name, 4.0)
    conn = get_conn()
    conn.execute("""
        INSERT INTO exercises (done_at, name, met, duration_min, kcal_burned)
        VALUES (?, ?, ?, ?, ?)
    """, (datetime.now(tz=KST).isoformat(), name, met, duration_min, kcal))
    conn.commit()
    conn.close()
    print(f"✅ 운동 저장: {name} {duration_min}분 → {kcal:.0f}kcal")

# ── 오늘 운동 루틴 추천 ──────────────────────────────────

def get_exercise_recommendation(date: str = None) -> dict:
    """
    삼성헬스 + 인바디 데이터 기반 오늘 운동 루틴 추천
    반환: {"routine": [...], "total_kcal": ..., "comment": "..."}
    """
    if date is None:
        date = datetime.now(tz=KST).strftime("%Y-%m-%d")

    conn = get_conn()

    # 인바디
    inbody = conn.execute("""
        SELECT weight_kg, skeletal_muscle_kg, body_fat_pct,
               arm_r_kg, arm_l_kg, leg_r_kg, leg_l_kg, trunk_kg, bmr_kcal
        FROM inbody ORDER BY measured_at DESC LIMIT 1
    """).fetchone()

    # 최근 7일 운동
    recent_ex = conn.execute("""
        SELECT name, duration_min, kcal_burned
        FROM exercises WHERE date(done_at) >= date(?, '-7 days')
        ORDER BY done_at DESC
    """, (date,)).fetchall()

    # 어제 수면
    sleep = conn.execute("""
        SELECT duration_min, sleep_score, efficiency
        FROM sleep WHERE date <= ? ORDER BY date DESC LIMIT 1
    """, (date,)).fetchone()

    # 오늘 심박수
    hr = conn.execute("""
        SELECT bpm FROM heart_rate
        WHERE date(datetime) = ? ORDER BY datetime DESC LIMIT 1
    """, (date,)).fetchone()

    conn.close()

    weight = inbody["weight_kg"] if inbody else 70
    body_fat = inbody["body_fat_pct"] if inbody else 20
    sleep_score = sleep["sleep_score"] if sleep else 70
    current_bpm = hr["bpm"] if hr else 70
    recent_names = [e["name"] for e in recent_ex]

    prompt = f"""나의 건강 데이터야:

- 체중: {weight}kg, 체지방률: {body_fat}%
- 어제 수면 점수: {sleep_score}점
- 현재 심박수: {current_bpm}bpm
- 최근 7일 운동: {', '.join(recent_names) if recent_names else '없음'}

오늘 운동 루틴을 추천해줘. 아래 JSON 형식으로만 응답해줘. 다른 말은 하지 마.

{{
  "routine": [
    {{"name": "운동명", "sets": 세트수, "duration_min": 시간, "kcal": 예상칼로리}},
    ...
  ],
  "total_kcal": 총예상칼로리,
  "intensity": "저강도|중강도|고강도",
  "comment": "오늘 루틴 추천 이유 한 줄"
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
    return json.loads(text.strip())

# ── 공강 운동 추천 ───────────────────────────────────────

LOCATION_EXERCISES = {
    "학교": ["계단오르기", "스트레칭", "걷기", "플랭크", "푸시업"],
    "집":   ["스쿼트", "푸시업", "플랭크", "줄넘기", "요가", "스트레칭"],
    "알바": ["스트레칭", "걷기"],
}

def get_free_slot_exercise(day_of_week: int = None) -> list[dict]:
    """
    오늘 시간표 공강 시간에 맞는 운동 추천
    반환: [{"time": "12:00~13:00", "duration_min": 60, "exercises": [...]}]
    """
    if day_of_week is None:
        day_of_week = datetime.now(tz=KST).weekday()  # 0=월

    conn = get_conn()
    schedule = conn.execute("""
        SELECT start_time, end_time FROM schedule
        WHERE day_of_week = ? ORDER BY start_time
    """, (day_of_week,)).fetchall()
    conn.close()

    if not schedule:
        return []

    recommendations = []
    for i in range(len(schedule) - 1):
        end_h, end_m = map(int, schedule[i]["end_time"].split(":"))
        start_h, start_m = map(int, schedule[i+1]["start_time"].split(":"))
        gap = (start_h * 60 + start_m) - (end_h * 60 + end_m)

        if gap >= 30:
            location_exercises = LOCATION_EXERCISES.get("학교", [])
            suitable = [e for e in location_exercises
                       if MET_TABLE.get(e, 4) * gap / 60 < gap * 0.5][:3]
            recommendations.append({
                "time": f"{schedule[i]['end_time']}~{schedule[i+1]['start_time']}",
                "duration_min": gap,
                "location": "학교",
                "exercises": suitable or location_exercises[:3],
            })

    return recommendations
