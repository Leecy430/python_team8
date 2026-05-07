import anthropic
import base64
import json
import os
from dotenv import load_dotenv
load_dotenv(override=True)
from datetime import datetime, timezone, timedelta
from core.database import get_conn

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
KST = timezone(timedelta(hours=9))

def process_inbody_image(image_path: str) -> dict:
    with open(image_path, "rb") as f:
        img_data = base64.standard_b64encode(f.read()).decode("utf-8")

    ext = image_path.split(".")[-1].lower()
    media_type = "image/jpeg" if ext in ["jpg","jpeg"] else "image/png"

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
                    "text": "인바디 결과지에서 수치를 추출해서 아래 JSON 형식으로만 응답해줘. 없는 값은 null로.\n\n{\"weight_kg\": 숫자, \"skeletal_muscle_kg\": 숫자, \"body_fat_kg\": 숫자, \"body_fat_pct\": 숫자, \"bmi\": 숫자, \"arm_r_kg\": 숫자, \"arm_l_kg\": 숫자, \"leg_r_kg\": 숫자, \"leg_l_kg\": 숫자, \"trunk_kg\": 숫자, \"bmr_kcal\": 숫자}"
                }
            ]
        }]
    )

    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    data = json.loads(text.strip())
    data["measured_at"] = datetime.now(tz=KST).strftime("%Y-%m-%d")

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
    print(f"✅ 인바디 저장: {data['measured_at']} {data['weight_kg']}kg")
    return data
