"""
modules/nutrition.py
음식 사진 → Claude Vision으로 음식 인식 → 로컬 식품 DB 조회 → meals 테이블 저장
"""

import anthropic
import base64
import json
import sqlite3
import os
from dotenv import load_dotenv
load_dotenv(override=True)
from datetime import datetime, timezone, timedelta
from core.database import get_conn

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
KST = timezone(timedelta(hours=9))
FOOD_DB_PATH = "db/static_food.db"  # 로컬 식품영양정보 DB

# ── 이미지 → 음식 인식 ───────────────────────────────────

def recognize_food(image_path: str) -> list[dict]:
    """
    음식 사진을 Claude Vision에 전달 → 음식명 리스트 반환
    반환: [{"food_name": "비빔밥", "amount_g": 300}, ...]
    """
    with open(image_path, "rb") as f:
        img_data = base64.standard_b64encode(f.read()).decode("utf-8")

    ext = image_path.split(".")[-1].lower()
    media_type = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": img_data}
                },
                {
                    "type": "text",
                    "text": """이 음식 사진을 분석해서 아래 JSON 형식으로만 응답해줘. 다른 말은 하지 마.

[
  {"food_name": "음식명", "amount_g": 예상중량(숫자)}
]

음식명은 한국어로, 중량은 일반적인 1인분 기준으로 추정해줘."""
                }
            ]
        }]
    )

    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())

# ── 로컬 식품 DB 조회 ────────────────────────────────────

def search_food_db(food_name: str) -> dict | None:
    """
    로컬 식품영양정보 DB에서 음식명으로 영양소 조회
    반환: {"food_name": ..., "kcal": ..., "protein_g": ..., "carb_g": ..., "fat_g": ...}
    """
    if not os.path.exists(FOOD_DB_PATH):
        # DB 없으면 더미 데이터 반환
        return _dummy_nutrition(food_name)

    conn = sqlite3.connect(FOOD_DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT * FROM food_info
        WHERE food_name LIKE ?
        LIMIT 1
    """, (f"%{food_name}%",)).fetchone()
    conn.close()

    if row:
        return dict(row)
    return _dummy_nutrition(food_name)

def _dummy_nutrition(food_name: str) -> dict:
    """식품 DB 없을 때 더미 영양소 반환"""
    dummy = {
        "비빔밥": {"kcal": 550, "protein_g": 15, "carb_g": 90, "fat_g": 12},
        "김치찌개": {"kcal": 180, "protein_g": 12, "carb_g": 10, "fat_g": 8},
        "삼겹살": {"kcal": 450, "protein_g": 25, "carb_g": 0, "fat_g": 38},
        "된장찌개": {"kcal": 150, "protein_g": 10, "carb_g": 8, "fat_g": 6},
        "라면": {"kcal": 500, "protein_g": 10, "carb_g": 75, "fat_g": 16},
    }
    for key, val in dummy.items():
        if key in food_name or food_name in key:
            return {"food_name": food_name, **val}
    return {"food_name": food_name, "kcal": 300, "protein_g": 10, "carb_g": 40, "fat_g": 10}

# ── 식단 저장 ────────────────────────────────────────────

def save_meal(food_name: str, nutrition: dict, image_path: str = None):
    """인식된 음식 → meals 테이블 저장"""
    conn = get_conn()
    now = datetime.now(tz=KST).isoformat()
    conn.execute("""
        INSERT INTO meals (eaten_at, food_name, kcal, protein_g, carb_g, fat_g, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (now, food_name,
          nutrition.get("kcal"), nutrition.get("protein_g"),
          nutrition.get("carb_g"), nutrition.get("fat_g"),
          image_path))
    conn.commit()
    conn.close()
    print(f"✅ 식단 저장: {food_name} {nutrition.get('kcal')}kcal")

# ── 오늘 식단 조회 ───────────────────────────────────────

def get_today_meals(date: str = None) -> list[dict]:
    """오늘 먹은 식단 전체 조회"""
    if date is None:
        date = datetime.now(tz=KST).strftime("%Y-%m-%d")
    conn = get_conn()
    rows = conn.execute("""
        SELECT eaten_at, food_name, kcal, protein_g, carb_g, fat_g
        FROM meals WHERE date(eaten_at) = ?
        ORDER BY eaten_at
    """, (date,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_today_nutrition_summary(date: str = None) -> dict:
    """오늘 총 영양소 합계"""
    meals = get_today_meals(date)
    return {
        "total_kcal":    sum(m["kcal"] or 0 for m in meals),
        "total_protein": sum(m["protein_g"] or 0 for m in meals),
        "total_carb":    sum(m["carb_g"] or 0 for m in meals),
        "total_fat":     sum(m["fat_g"] or 0 for m in meals),
        "meal_count":    len(meals),
    }

# ── 통합 실행 (사진 업로드 → 저장) ─────────────────────

def process_food_image(image_path: str) -> list[dict]:
    """
    사진 업로드 → 인식 → DB 조회 → 저장까지 한번에
    반환: 저장된 음식 목록
    """
    foods = recognize_food(image_path)
    results = []
    for food in foods:
        nutrition = search_food_db(food["food_name"])
        # 중량 비율 적용 (100g 기준 DB라면)
        ratio = food.get("amount_g", 100) / 100
        adjusted = {
            "kcal":      (nutrition.get("kcal") or 0) * ratio,
            "protein_g": (nutrition.get("protein_g") or 0) * ratio,
            "carb_g":    (nutrition.get("carb_g") or 0) * ratio,
            "fat_g":     (nutrition.get("fat_g") or 0) * ratio,
        }
        save_meal(food["food_name"], adjusted, image_path)
        results.append({"food_name": food["food_name"], **adjusted})
    return results
