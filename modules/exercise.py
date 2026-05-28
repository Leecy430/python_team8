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
from core.feedback_db import get_recent_bad_feedback
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

    bad_feedbacks = get_recent_bad_feedback('exercise_routine', limit=3)
    feedback_warning = ''
    if bad_feedbacks:
        directives = []
        for f in bad_feedbacks:
            content = f['content']
            context = f.get('context', '')

            if any(kw in content for kw in ['시간', '많', '길', '오래', '지루']):
                directives.append("운동 종목 수를 줄여줘. 2개 이하로만 추천해.")
            if any(kw in content for kw in ['힘들', '세다', '강도', '빡', '어렵', '힘']):
                directives.append("저강도 운동만 추천해줘. 고강도 운동은 절대 포함하지 마.")
            if any(kw in content for kw in ['같', '똑같', '반복', '또', '다시']):
                if '이전 추천:' in context:
                    prev = context.split('이전 추천:')[-1].strip()
                    directives.append(f"이전에 추천했던 [{prev}]는 절대 포함하지 마.")
            if not directives:
                directives.append(f"사용자 불만: {content}. 이를 반영해서 완전히 다른 루틴을 추천해줘.")

        feedback_warning = (
            "⚠️ 이전 추천에 대한 사용자 불만 - 반드시 아래 지시를 따라줘:\n"
            + '\n'.join(f"  - {d}" for d in directives)
            + "\n\n"
        )

    prompt = f"""{feedback_warning}나의 건강 데이터야:

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


def get_free_slot_exercise(day_of_week: int = None) -> list[dict]:
    """
    오늘 시간표 공강 시간에 맞는 운동 추천 (AI 기반 + 피드백 반영)
    반환: [{"time": "12:00~13:00", "duration_min": 60, "location": "학교", "exercises": [...]}]
    """
    if day_of_week is None:
        day_of_week = datetime.now(tz=KST).weekday()

    conn = get_conn()
    schedule = conn.execute("""
        SELECT start_time, end_time FROM schedule
        WHERE day_of_week = ? ORDER BY start_time
    """, (day_of_week,)).fetchall()

    inbody = conn.execute("""
        SELECT weight_kg, body_fat_pct FROM inbody ORDER BY measured_at DESC LIMIT 1
    """).fetchone()

    today = datetime.now(tz=KST).strftime("%Y-%m-%d")
    recent_ex = conn.execute("""
        SELECT name FROM exercises WHERE date(done_at) >= date(?, '-7 days')
        ORDER BY done_at DESC LIMIT 10
    """, (today,)).fetchall()
    conn.close()

    if not schedule:
        return []

    # 공강 슬롯 계산
    slots = []
    for i in range(len(schedule) - 1):
        end_h, end_m = map(int, schedule[i]["end_time"].split(":"))
        start_h, start_m = map(int, schedule[i+1]["start_time"].split(":"))
        gap = (start_h * 60 + start_m) - (end_h * 60 + end_m)
        if gap >= 30:
            slots.append({
                "time": f"{schedule[i]['end_time']}~{schedule[i+1]['start_time']}",
                "duration_min": gap,
                "location": "학교",
            })

    if not slots:
        return []

    weight = inbody["weight_kg"] if inbody else 70
    body_fat = inbody["body_fat_pct"] if inbody else 20
    recent_names = [e["name"] for e in recent_ex]

    bad_feedbacks = get_recent_bad_feedback('exercise_slot', limit=3)
    feedback_warning = ''
    if bad_feedbacks:
        directives = []
        for f in bad_feedbacks:
            content = f['content']
            context = f.get('context', '')

            # 시간/양 관련 불만 → max_exercise_min 줄이기
            if any(kw in content for kw in ['시간', '많', '길', '오래', '지루']):
                directives.append("max_exercise_min을 20으로 설정해줘. 운동에 쓰는 시간을 20분 이내로 제한해.")

            # 강도 관련 불만 → 가장 가벼운 것만
            if any(kw in content for kw in ['힘들', '세다', '강도', '빡', '어렵', '힘']):
                directives.append("강도가 가장 낮은 운동만 추천해줘. 스트레칭이나 가볍게 걷기 정도만.")

            # 반복/같은 추천 불만 → 이전 운동 회피
            if any(kw in content for kw in ['같', '똑같', '반복', '또', '다시']):
                if '이전 추천:' in context:
                    prev = context.split('이전 추천:')[-1].strip()
                    directives.append(f"이전에 추천했던 [{prev}]는 절대 추천하지 마. 완전히 다른 것으로.")

            # 아무 키워드도 안 걸리면 기본 지시
            if not directives:
                directives.append(f"사용자 불만: {content}. 이를 반영해서 완전히 다른 운동을 추천해줘.")

        feedback_warning = (
            "⚠️ 이전 추천에 대한 사용자 불만 - 반드시 아래 지시를 따라줘:\n"
            + '\n'.join(f"  - {d}" for d in directives)
            + "\n\n"
        )

    slots_info = '\n'.join(
        f"  - {s['time']} ({s['duration_min']}분)"
        for s in slots
    )
    available = ', '.join(MET_TABLE.keys())

    prompt = f"""{feedback_warning}나의 건강 데이터야:
- 체중: {weight}kg, 체지방률: {body_fat}%
- 최근 7일 운동: {', '.join(recent_names) if recent_names else '없음'}
- 장소: 학교 (수업 사이 공강)

오늘 공강 시간대 (이 목록 그대로만 반환해줘. 임의로 추가하거나 분할하지 마):
{slots_info}

공강 시간은 수업과 수업 사이 틈새 시간이야.
계단오르기, 걷기, 스트레칭처럼 부담 없이 몸을 움직이는 활동 위주로 각 슬롯당 2~3개만 추천해줘.
땀이 많이 나거나 다음 수업에 지장이 생기는 고강도 운동은 피해줘.

exercises 배열에는 반드시 아래 목록에 있는 이름만 정확히 그대로 써줘. 변형하거나 새로 만들지 마:
{available}

반드시 위 공강 시간대 개수({len(slots)}개)만큼만 JSON 배열로 반환해줘. 다른 말은 하지 마.
[
  {{"time": "HH:MM~HH:MM", "exercises": ["운동명1", "운동명2"]}},
  ...
]"""

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

    # duration_min·location은 AI가 아닌 우리가 계산한 값을 사용
    slot_map = {s["time"]: s for s in slots}
    filtered = [r for r in result if r.get("time") in slot_map]

    if not filtered:
        for i, slot in enumerate(slots):
            slot["exercises"] = result[i]["exercises"] if i < len(result) else ["걷기", "스트레칭"]
        return slots

    for r in filtered:
        base = slot_map[r["time"]]
        r["duration_min"] = base["duration_min"]
        r["location"] = base["location"]
    return filtered
