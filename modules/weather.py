"""
modules/weather.py
WeatherAPI.com 연동
1. get_current_weather()  - 지금 당장 날씨
2. get_hourly_weather()   - 오늘 1시간 단위 날씨
3. get_daily_forecast()   - 오늘~3일치 날씨 요약
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv(override=True)
WEATHER_API_KEY = os.getenv("WEATHERAPI_KEY")
BASE_URL = "http://api.weatherapi.com/v1"

def get_current_weather(location: str = "Michuhol-gu, Incheon") -> dict:
    """현재 날씨 조회"""
    try:
        res = requests.get(f"{BASE_URL}/current.json", params={
            "key": WEATHER_API_KEY,
            "q": location,
            "lang": "ko"
        }, timeout=5)
        data = res.json()
        if "error" in data:
            raise ValueError("지역명을 영어로 입력해주세요. (예: Incheon, Seoul)")
        current = data["current"]
        return {
            "temp_c":     current["temp_c"],
            "feels_like": current["feelslike_c"],
            "condition":  current["condition"]["text"],
            "humidity":   current["humidity"],
            "wind_kph":   current["wind_kph"],
            "is_raining": current["precip_mm"] > 0,
            "uv":         current["uv"],
            "icon":       "https:" + current["condition"]["icon"],
        }
    except ValueError:
        raise
    except Exception as e:
        raise ConnectionError(f"날씨 API 연결 실패: {e}")

def get_hourly_weather(location: str = "Michuhol-gu, Incheon") -> list[dict]:
    """
    오늘 1시간 단위 날씨 반환
    반환: [{"time": "09:00", "temp_c": 18.0, "condition": "맑음", ...}, ...]
    """
    try:
        res = requests.get(f"{BASE_URL}/forecast.json", params={
            "key": WEATHER_API_KEY,
            "q": location,
            "days": 1,
            "lang": "ko"
        }, timeout=5)
        data = res.json()
        if "error" in data:
            raise ValueError("지역명을 영어로 입력해주세요. (예: Incheon, Seoul)")
        hours = data["forecast"]["forecastday"][0]["hour"]
        result = []
        for h in hours:
            result.append({
                "time":       h["time"][-5:],
                "temp_c":     h["temp_c"],
                "feels_like": h["feelslike_c"],
                "condition":  h["condition"]["text"],
                "humidity":   h["humidity"],
                "wind_kph":   h["wind_kph"],
                "is_raining": h["precip_mm"] > 0,
                "uv":         h["uv"],
                "icon":       "https:" + h["condition"]["icon"],
            })
        return result
    except ValueError:
        raise
    except Exception as e:
        raise ConnectionError(f"날씨 API 연결 실패: {e}")

def get_daily_forecast(location: str = "Michuhol-gu, Incheon", days: int = 3) -> list[dict]:
    """
    오늘~3일치 날씨 요약 반환
    반환: [{"date": "2026-05-10", "max_c": 22, "min_c": 14, ...}, ...]
    """
    try:
        res = requests.get(f"{BASE_URL}/forecast.json", params={
            "key": WEATHER_API_KEY,
            "q": location,
            "days": days,
            "lang": "ko"
        }, timeout=5)
        data = res.json()
        if "error" in data:
            raise ValueError("지역명을 영어로 입력해주세요. (예: Incheon, Seoul)")
        result = []
        for day in data["forecast"]["forecastday"]:
            d = day["day"]
            result.append({
                "date":         day["date"],
                "max_c":        d["maxtemp_c"],
                "min_c":        d["mintemp_c"],
                "avg_c":        d["avgtemp_c"],
                "condition":    d["condition"]["text"],
                "rain_chance":  d["daily_chance_of_rain"],
                "is_raining":   d["daily_will_it_rain"] == 1,
                "max_wind_kph": d["maxwind_kph"],
                "humidity":     d["avghumidity"],
                "uv":           d["uv"],
                "icon":         "https:" + d["condition"]["icon"],
            })
        return result
    except ValueError:
        raise
    except Exception as e:
        raise ConnectionError(f"날씨 API 연결 실패: {e}")