"""
modules/diet.py
식단 추천 - Claude API로 개인화된 다음 끼니 추천
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

def get_diet_recommendation(date: str = None) -> dict:
    """
    오늘 데이터 기반으로 다음 끼니 추천
    반환: {"meals": [...], "comment": "...", "calorie_balance": ...}
    """
    if date is None:
        date = datetime.now(tz=KST).strftime("%Y-%m-%d")

    conn = get_conn()

    # 오늘 섭취 칼로리
    meals = conn.execute("""
        SELECT food_name, kcal, protein_g, carb_g, fat_g
        FROM meals WHERE date(eaten_at) = ?
    """, (date,)).fetchall()

    # 오늘 걸음수 (칼로리 소모)
    steps = conn.execute(
        "SELECT count, calorie FROM steps_daily WHERE date = ?", (date,)
    ).fetchone()

    # 인바디 (BMR)
    inbody = conn.execute(
        "SELECT bmr_kcal, weight_kg FROM inbody ORDER BY measured_at DESC LIMIT 1"
    ).fetchone()

    conn.close()

    total_intake = sum(m["kcal"] or 0 for m in meals)
    total_protein = sum(m["protein_g"] or 0 for m in meals)
    total_carb = sum(m["carb_g"] or 0 for m in meals)
    total_fat = sum(m["fat_g"] or 0 for m in meals)
    burned = steps["calorie"] if steps and steps["calorie"] else 0
    bmr = inbody["bmr_kcal"] if inbody and inbody["bmr_kcal"] else None
    weight = inbody["weight_kg"] if inbody and inbody["weight_kg"] else 70

    # 고정 신체정보 (2003년생 남성 174cm)
    HEIGHT_CM = 174
    AGE       = 23
    GENDER    = "남성"

    # 인바디 BMR 없으면 Mifflin-St Jeor로 계산
    if not bmr:
        bmr = round(10 * weight + 6.25 * HEIGHT_CM - 5 * AGE + 5)

    # 일일 목표 칼로리 = BMR × 1.5
    calorie_goal  = round(bmr * 1.5)
    protein_goal  = round(weight * 1.6)
    fat_goal      = round(calorie_goal * 0.25 / 9)
    carb_goal     = round((calorie_goal - protein_goal * 4 - fat_goal * 9) / 4)

    # 남은 칼로리 여유 = 목표 - 이미 먹은 것 + 운동 소모
    calorie_remaining = calorie_goal - total_intake + burned

    bad_feedbacks = get_recent_bad_feedback('diet', limit=3)
    feedback_warning = ''
    if bad_feedbacks:
        directives = []
        for f in bad_feedbacks:
            content = f['content']
            context = f.get('context', '')

            if any(kw in content for kw in ['칼로리', '높', '많', '살', '부담']):
                directives.append("칼로리가 낮은 메뉴 위주로 추천해줘. 500kcal 이하 메뉴만.")
            if any(kw in content for kw in ['같', '똑같', '반복', '또', '비슷']):
                if '추천 메뉴:' in context:
                    prev = context.split('추천 메뉴:')[-1].strip()
                    directives.append(f"이전에 추천했던 [{prev}]는 절대 추천하지 마. 완전히 다른 종류로.")
            if any(kw in content for kw in ['맵', '짜', '느끼', '달', '자극']):
                directives.append("자극적이지 않고 담백한 메뉴를 추천해줘.")
            if not directives:
                directives.append(f"사용자 불만: {content}. 이를 반영해서 완전히 다른 메뉴를 추천해줘.")

        feedback_warning = (
            "⚠️ 이전 식단 추천에 대한 사용자 불만 - 반드시 아래 지시를 따라줘:\n"
            + '\n'.join(f"  - {d}" for d in directives)
            + "\n\n"
        )

    prompt = f"""{feedback_warning}아래는 나의 신체정보와 오늘 건강 데이터야:

[신체정보]
- 성별: {GENDER} / 나이: {AGE}세 / 키: {HEIGHT_CM}cm / 체중: {weight}kg
- 기초대사량(BMR): {bmr}kcal
- 일일 권장 칼로리 목표: {calorie_goal}kcal (BMR × 1.5)
- 권장 단백질: {protein_goal}g / 탄수화물: {carb_goal}g / 지방: {fat_goal}g

[오늘 섭취 현황]
- 섭취 칼로리: {total_intake:.0f}kcal (단백질 {total_protein:.0f}g, 탄수화물 {total_carb:.0f}g, 지방 {total_fat:.0f}g)
- 운동 소모: {burned:.0f}kcal
- 남은 칼로리 여유: {calorie_remaining:.0f}kcal (목표 {calorie_goal}kcal - 섭취 {total_intake:.0f}kcal + 소모 {burned:.0f}kcal)

위 데이터를 바탕으로 다음 끼니 추천 메뉴 3가지를 아래 JSON 형식으로만 응답해줘. 다른 말은 하지 마.
추천 메뉴의 칼로리 합이 '남은 칼로리 여유'에 맞도록 조절해줘.

{{
  "meals": [
    {{"name": "메뉴명", "kcal": 숫자, "reason": "추천 이유 한 줄"}},
    {{"name": "메뉴명", "kcal": 숫자, "reason": "추천 이유 한 줄"}},
    {{"name": "메뉴명", "kcal": 숫자, "reason": "추천 이유 한 줄"}}
  ],
  "comment": "오늘 영양 상태 및 목표 대비 현황 한 줄 코멘트",
  "calorie_balance": {calorie_remaining:.0f}
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
