"""
server.py
FastAPI 백엔드 서버 - 모든 모듈 연결
실행: uvicorn server:app --reload --port 8000
"""

from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import shutil
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta


# 모듈 임포트
from core.database import init_db, get_conn
from core.feedback_db import init_feedback_db, save_feedback
from core.replay import get_snapshot, get_steps_timeseries, get_sleep_timeseries, get_heartrate_timeseries, get_all_dates
from modules.nutrition import process_food_image, get_today_meals, get_today_nutrition_summary
from modules.diet import get_diet_recommendation
from modules.exercise import get_exercise_recommendation, get_free_slot_exercise, save_exercise
from modules.weather import get_current_weather
from modules.walk import get_walk_recommendation, set_location, get_locations
from modules.schedule import parse_schedule_from_image, save_schedule, get_schedule, get_free_slots, get_today_schedule
from modules.outfit import get_outfit_recommendation
from modules.inbody import process_inbody_image
from apscheduler.schedulers.background import BackgroundScheduler
from modules.calendar_sync import sync_calendar


KST = timezone(timedelta(hours=9))
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="세얼간이 건강지킴이 API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프론트엔드 정적 파일
if Path("frontend").exists():
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

# ── DB 초기화 ────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
    init_feedback_db()
    
    # 캘린더 즉시 sync
    try:
        count = sync_calendar()
        print(f"✅ 캘린더 sync 완료 ({count}개)")
    except Exception as e:
        print(f"⚠️ 캘린더 sync 실패: {e}")
    
    # 매일 06:00 KST 자동 sync
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(sync_calendar, 'cron', hour=6, minute=0)
    scheduler.start()
    
    print("✅ 서버 시작 완료")
# ── 메인 페이지 ──────────────────────────────────────────

@app.get("/")
def root():
    index = Path("frontend/index.html")
    if index.exists():
        return FileResponse(index)
    return {"status": "ok", "message": "세얼간이 API 서버"}

@app.get("/diet")
def diet_page():
    return FileResponse(Path("frontend/diet.html"))

@app.get("/exercise")
def exercise_page():
    return FileResponse(Path("frontend/exercise.html"))

@app.get("/settings")
def settings_page():
    return FileResponse(Path("frontend/settings.html"))

# ════════════════════════════════════════════════════════
# 대시보드
# ════════════════════════════════════════════════════════

@app.get("/api/dashboard")
def dashboard(date: str = None):
    """메인 대시보드 - 오늘 전체 데이터 스냅샷"""
    if date is None:
        date = datetime.now(tz=KST).strftime("%Y-%m-%d")

    snap = get_snapshot(date)
    weather = get_current_weather()
    walk = get_walk_recommendation(date)

    return {
        "date":       date,
        "steps":      snap["steps"],
        "sleep":      snap["sleep"],
        "heart_rate": snap["heart_rate"],
        "inbody":     snap["inbody"],
        "weather":    weather,
        "walk_ok":    walk.get("recommend", False),
        "walk_msg":   walk.get("reason", ""),
    }

@app.get("/api/dashboard/dates")
def get_dates():
    """DB에 있는 전체 날짜 목록 (replay용)"""
    return {"dates": get_all_dates()}

# ════════════════════════════════════════════════════════
# 걸음수
# ════════════════════════════════════════════════════════

@app.get("/api/steps")
def steps(date: str = None):
    if date is None:
        date = datetime.now(tz=KST).strftime("%Y-%m-%d")
    snap = get_snapshot(date)
    return snap["steps"]

@app.get("/api/steps/timeseries")
def steps_timeseries(days: int = 30):
    df = get_steps_timeseries(days)
    return df.to_dict(orient="records")

# ════════════════════════════════════════════════════════
# 수면
# ════════════════════════════════════════════════════════

@app.get("/api/sleep")
def sleep(date: str = None):
    snap = get_snapshot(date)
    return snap["sleep"]

@app.get("/api/sleep/timeseries")
def sleep_timeseries(days: int = 30):
    df = get_sleep_timeseries(days)
    return df.to_dict(orient="records")

# ════════════════════════════════════════════════════════
# 심박수
# ════════════════════════════════════════════════════════

@app.get("/api/heartrate")
def heartrate(date: str = None):
    df = get_heartrate_timeseries(date)
    df["datetime"] = df["datetime"].astype(str)
    return df.to_dict(orient="records")

# ════════════════════════════════════════════════════════
# 식단
# ════════════════════════════════════════════════════════

@app.post("/api/meals/photo")
async def upload_food_photo(file: UploadFile = File(...)):
    path = UPLOAD_DIR / file.filename
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        results = process_food_image(str(path))
        return {"success": True, "foods": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/meals")
def meals(date: str = None):
    if date is None:
        date = datetime.now(tz=KST).strftime("%Y-%m-%d")
    return {
        "meals":   get_today_meals(date),
        "summary": get_today_nutrition_summary(date),
    }

@app.get("/api/meals/recommend")
def meal_recommend(date: str = None):
    try:
        return get_diet_recommendation(date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ════════════════════════════════════════════════════════
# 운동
# ════════════════════════════════════════════════════════

@app.get("/api/exercise/recommend")
def exercise_recommend(date: str = None):
    try:
        return get_exercise_recommendation(date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/exercise/free-slots")
def exercise_free_slots(day: int = None):
    if day is None:
        day = datetime.now(tz=KST).weekday()
    return {"slots": get_free_slot_exercise(day)}

@app.post("/api/exercise/save")
def exercise_save(name: str, duration_min: float, weight_kg: float = 70.0):
    save_exercise(name, duration_min, weight_kg)
    return {"success": True}

# ════════════════════════════════════════════════════════
# 날씨
# ════════════════════════════════════════════════════════

@app.get("/api/weather")
def weather(location: str = None):
    return get_current_weather(location)

# ════════════════════════════════════════════════════════
# 산책
# ════════════════════════════════════════════════════════

@app.get("/api/walk/recommend")
def walk_recommend(date: str = None):
    return get_walk_recommendation(date)

@app.post("/api/walk/location")
def save_location(name: str, address: str, lat: float, lon: float,
                  start_time: str = None, end_time: str = None):
    set_location(name, address, lat, lon, start_time, end_time)
    return {"success": True}

@app.get("/api/walk/locations")
def locations():
    return get_locations()

# ════════════════════════════════════════════════════════
# 시간표
# ════════════════════════════════════════════════════════

@app.post("/api/schedule/photo")
async def upload_schedule_photo(file: UploadFile = File(...)):
    path = UPLOAD_DIR / file.filename
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        result = parse_schedule_from_image(str(path))
        save_schedule(result)
        return {"success": True, "schedule": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/schedule")
def schedule():
    return {"schedule": get_schedule()}

@app.get("/api/schedule/free-slots")
def schedule_free_slots():
    day = datetime.now(tz=KST).weekday()
    return {"free_slots": get_free_slots(), "day": day}

@app.get("/today-schedule") # 추가
def today_schedule(date: str = None):
    return get_today_schedule(date)

# ════════════════════════════════════════════════════════
# 인바디
# ════════════════════════════════════════════════════════

@app.get("/api/inbody")
def inbody():
    snap = get_snapshot()
    return snap["inbody"]

@app.post("/api/inbody/photo")
async def upload_inbody_photo(file: UploadFile = File(...)):
    path = UPLOAD_DIR / file.filename
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        result = process_inbody_image(str(path))
        return {"success": True, "inbody": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ════════════════════════════════════════════════════════
# 옷차림
# ════════════════════════════════════════════════════════

@app.get("/api/outfit")
def outfit(location: str = None):
    if location is None:
        location = "Michuhol-gu, Incheon"
    try:
        return get_outfit_recommendation(location)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
from pydantic import BaseModel

# ════════════════════════════════════════════════════════
# 피드백
# ════════════════════════════════════════════════════════

class FeedbackRequest(BaseModel):
    type: str       # 'exercise_routine' | 'exercise_slot' | 'diet'
    rating: str     # 'bad' | 'good'
    content: str    # 피드백 텍스트
    context: str = ""

@app.post("/api/feedback")
def submit_feedback(data: FeedbackRequest):
    save_feedback(data.type, data.rating, data.content, data.context)
    return {"success": True}

class RealtimeHealthData(BaseModel):
    steps: int
    heart_rate: float
    sleep_minutes: int
    sleep_start: str = ""
    sleep_end: str = ""

@app.post("/health/realtime")
async def receive_realtime_health(data: RealtimeHealthData):
    now_kst = datetime.now(tz=KST)
    date_str = now_kst.strftime("%Y-%m-%d")
    datetime_str = now_kst.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()
    cur = conn.cursor()

    # 걸음수 저장 (0 이상이면 저장)
    if data.steps >= 0:
        cur.execute("""
            INSERT INTO steps_daily (date, count, distance_m, calorie)
            VALUES (?, ?, 0, 0)
            ON CONFLICT(date) DO UPDATE SET count=excluded.count
        """, (date_str, data.steps))

    # 심박수 저장 (0보다 클 때만)
    if data.heart_rate > 0:
        cur.execute("""
            INSERT INTO heart_rate (datetime, bpm, bpm_min, bpm_max, tag)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime_str, int(data.heart_rate), int(data.heart_rate), int(data.heart_rate), "realtime"))

    # 수면 저장 (0보다 클 때만)
    if data.sleep_minutes > 0 and data.sleep_start:
        cur.execute("""
            SELECT id FROM sleep WHERE date=? AND start_time=?
        """, (date_str, data.sleep_start))
        existing = cur.fetchone()
        if not existing:
            cur.execute("""
                INSERT INTO sleep (date, start_time, end_time, duration_min)
                VALUES (?, ?, ?, ?)
            """, (date_str, data.sleep_start, data.sleep_end, data.sleep_minutes))

    conn.commit()
    conn.close()

    print(f"저장완료: 걸음수={data.steps}, 심박수={data.heart_rate}, 수면={data.sleep_minutes}분, {data.sleep_start}~{data.sleep_end}")
    return {"status": "ok", "received": data.dict()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)