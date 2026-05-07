"""
modules/weather.py
WeatherAPI.com 연동 - 현재 날씨 조회
"""

import requests
import os
from dotenv import load_dotenv
load_dotenv(override=True)

WEATHER_API_KEY = os.getenv("WEATHERAPI_KEY")
BASE_URL = "http://api.weatherapi.com/v1"

# 기본 위치 (사용자 설정 전 기본값: 서울)
DEFAULT_LOCATION = "Seoul"

def get_current_weather(location: str = None) -> dict:
    """
    현재 날씨 조회
    반환: {"temp_c": 18.0, "condition": "맑음", "humidity": 60,
            "wind_kph": 10, "is_raining": False, "icon": "..."}
    """
    if not WEATHER_API_KEY:
        return _dummy_weather()

    loc = location or DEFAULT_LOCATION
    try:
        res = requests.get(f"{BASE_URL}/current.json", params={
            "key": WEATHER_API_KEY,
            "q": loc,
            "lang": "ko"
        }, timeout=5)
        data = res.json()
        current = data["current"]
        return {
            "temp_c":    current["temp_c"],
            "feels_like": current["feelslike_c"],
            "condition": current["condition"]["text"],
            "humidity":  current["humidity"],
            "wind_kph":  current["wind_kph"],
            "is_raining": current["precip_mm"] > 0,
            "uv":        current["uv"],
            "icon":      "https:" + current["condition"]["icon"],
        }
    except Exception as e:
        print(f"날씨 API 오류: {e}")
        return _dummy_weather()

def is_good_for_walk(weather: dict = None) -> tuple[bool, str]:
    """
    산책하기 좋은 날씨인지 판단
    반환: (가능여부, 이유)
    """
    if weather is None:
        weather = get_current_weather()

    if weather.get("is_raining"):
        return False, "비가 오고 있어요 ☔"
    if weather.get("temp_c", 20) >= 35:
        return False, "폭염 주의! 실외 활동을 자제하세요 🌡️"
    if weather.get("temp_c", 20) <= -10:
        return False, "한파 주의! 실외 활동을 자제하세요 🥶"
    if weather.get("wind_kph", 0) >= 50:
        return False, "강풍 주의! 산책을 자제하세요 💨"
    return True, f"산책하기 좋은 날씨예요! {weather.get('temp_c')}°C {weather.get('condition')}"

def _dummy_weather() -> dict:
    """API 키 없을 때 더미 날씨"""
    return {
        "temp_c": 18.0,
        "feels_like": 17.0,
        "condition": "맑음",
        "humidity": 55,
        "wind_kph": 8,
        "is_raining": False,
        "uv": 3,
        "icon": "",
    }
