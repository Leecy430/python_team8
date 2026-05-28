"""
modules/walk.py
퇴근길 산책 경로 추천 - Kakao Maps API
"""

import requests
import os
from dotenv import load_dotenv
load_dotenv(override=True)
from core.database import get_conn
from datetime import datetime, timezone, timedelta

KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")
KST = timezone(timedelta(hours=9))

# ── 위치 설정 조회 ───────────────────────────────────────

def get_locations() -> dict:
    """DB에서 집/학교/알바 위치 조회"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT name, address, lat, lon FROM location_settings"
    ).fetchall()
    conn.close()
    return {r["name"]: dict(r) for r in rows}

def set_location(name: str, address: str, lat: float, lon: float,
                 start_time: str = None, end_time: str = None):
    """위치 설정 저장"""
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO location_settings
        (name, address, lat, lon, start_time, end_time)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, address, lat, lon, start_time, end_time))
    conn.commit()
    conn.close()
    print(f"✅ 위치 저장: {name} ({address})")

# ── 현재 위치 추론 ───────────────────────────────────────

def get_current_location_name() -> str:
    """시간표 기반으로 현재 위치 추론"""
    now = datetime.now(tz=KST)
    current_time = now.strftime("%H:%M")
    day_of_week = now.weekday()  # 0=월

    conn = get_conn()
    schedule = conn.execute("""
        SELECT start_time, end_time FROM schedule
        WHERE day_of_week = ? AND start_time <= ? AND end_time >= ?
    """, (day_of_week, current_time, current_time)).fetchone()
    conn.close()

    if schedule:
        return "학교"
    return "집"

# ── 도보 경로 조회 (Kakao Maps) ──────────────────────────

def get_walk_route(origin_lat: float, origin_lon: float,
                   dest_lat: float, dest_lon: float) -> dict:
    """
    Kakao Maps로 도보 경로 조회
    반환: {"distance_m": ..., "duration_min": ..., "steps": ...}
    """
    if not KAKAO_API_KEY:
        return _dummy_route()

    try:
        res = requests.get(
            "https://apis-navi.kakaomobility.com/v1/directions",
            headers={"Authorization": f"KakaoAK {KAKAO_API_KEY}"},
            params={
                "origin": f"{origin_lon},{origin_lat}",
                "destination": f"{dest_lon},{dest_lat}",
                "priority": "RECOMMEND",
            },
            timeout=5
        )
        data = res.json()
        route = data["routes"][0]["summary"]

        # 경로 좌표 추출 (지도 폴리라인용)
        path = []
        for section in data["routes"][0].get("sections", []):
            for road in section.get("roads", []):
                vs = road.get("vertexes", [])
                for i in range(0, len(vs) - 1, 2):
                    path.append({"lng": vs[i], "lat": vs[i+1]})

        return {
            "distance_m":   route["distance"],
            "duration_min": route["duration"] // 60,
            "taxi_fare":    route.get("fare", {}).get("taxi", 0),
            "path":         path,
        }
    except Exception as e:
        print(f"Kakao Maps 오류: {e}")
        return _dummy_route()

# ── 산책 추천 통합 ───────────────────────────────────────

def get_walk_recommendation(date: str = None) -> dict:
    """
    오늘 걸음수 부족 여부 확인 → 산책 경로 추천
    반환: {"recommend": bool, "reason": "...", "route": {...}, "extra_steps": ...}
    """
    if date is None:
        date = datetime.now(tz=KST).strftime("%Y-%m-%d")

    conn = get_conn()
    steps = conn.execute(
        "SELECT count FROM steps_daily WHERE date = ?", (date,)
    ).fetchone()
    conn.close()

    today_steps = steps["count"] if steps else 0
    goal = 8000
    remaining = max(0, goal - today_steps)

    if remaining == 0:
        return {
            "recommend": False,
            "reason": f"오늘 목표 {goal:,}보 달성! 🎉",
            "route": None,
            "extra_steps": 0,
        }

    # 위치 가져오기
    locations = get_locations()
    home = locations.get("집")
    current_loc_name = get_current_location_name()
    current_loc = locations.get(current_loc_name)

    # 현재 집에 있으면 학교를 출발지로 대체 (퇴근길 경로 미리 보기)
    if current_loc_name == "집" and "학교" in locations:
        current_loc = locations["학교"]
        current_loc_name = "학교"

    route = None
    if home and current_loc and current_loc_name != "집":
        route = get_walk_route(
            current_loc["lat"], current_loc["lon"],
            home["lat"], home["lon"]
        )

    # 예상 추가 걸음수 (1m ≈ 1.3걸음)
    extra_steps = int(route["distance_m"] * 1.3) if route else remaining

    return {
        "recommend":    True,
        "reason":       f"오늘 {today_steps:,}보 / 목표 {goal:,}보 ({remaining:,}보 부족)",
        "route":        route,
        "extra_steps":  extra_steps,
        "from":         current_loc_name,
        "to":           "집",
        "origin_lat":   current_loc["lat"] if current_loc else None,
        "origin_lon":   current_loc["lon"] if current_loc else None,
        "dest_lat":     home["lat"] if home else None,
        "dest_lon":     home["lon"] if home else None,
    }

def _dummy_route() -> dict:
    return {"distance_m": 1200, "duration_min": 15, "taxi_fare": 0}
