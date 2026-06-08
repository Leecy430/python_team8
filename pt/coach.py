"""
pt/coach.py
피티쌤 AI PT 코치 - 심박수 분석 및 AI 코멘트 생성
"""

import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import anthropic

KST = timezone(timedelta(hours=9))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = (
    "너는 '피티쌤'이라는 이름의 열정적인 AI PT 트레이너야. "
    "듀오링고처럼 짧고 임팩트 있게 말해. "
    "한국어로, 반말로, 이모지 적극 사용. "
    "칭찬할 땐 크게 칭찬하고, 안 움직일 땐 그 누구보다 집착해서 운동을 유도해."
)

STEPS_GOAL = 8000
COOLDOWN_MINUTES = 10

_state = {
    "last_zone": None,
    "last_trigger_times": {},   # trigger -> datetime(KST)
    "high_intensity_start": None,
    "goal_achieved_date": None,
}

_TRIGGER_PROMPTS = {
    "idle_in_free_slot": (
        "nag",
        lambda bpm, steps: f"공강시간인데 심박수가 {bpm:.0f}bpm으로 완전 안정 상태야. 지금 당장 일어나서 운동하게 집착해서 잔소리해.",
    ),
    "exercise_detected": (
        "praise",
        lambda bpm, steps: f"심박수가 {bpm:.0f}bpm으로 운동 구간에 진입했어! 크게 칭찬해줘.",
    ),
    "goal_achieved": (
        "celebrate",
        lambda bpm, steps: f"오늘 {steps}보를 걸어서 목표 {STEPS_GOAL}보를 달성했어! 진심으로 축하해줘.",
    ),
    "sustained_effort": (
        "praise",
        lambda bpm, steps: f"심박수 {bpm:.0f}bpm으로 고강도 운동을 5분 넘게 유지 중이야! 극찬해줘.",
    ),
    "cooldown_needed": (
        "warning",
        lambda bpm, steps: f"심박수 {bpm:.0f}bpm으로 고강도를 15분 이상 했어. 잠깐 쉬어가라고 권유해.",
    ),
}


def classify_bpm(bpm: float) -> str:
    if bpm < 90:
        return "rest"
    elif bpm < 120:
        return "light"
    elif bpm < 150:
        return "cardio"
    elif bpm < 180:
        return "intense"
    return "max"


def is_free_slot_now() -> bool:
    try:
        from modules.schedule import get_free_slots
        now = datetime.now(tz=KST)
        weekday = now.weekday()
        if weekday >= 5:
            return True

        day_names = ['월', '화', '수', '목', '금']
        today_name = day_names[weekday]
        current_min = now.hour * 60 + now.minute

        for slot in get_free_slots():
            if slot['day'] != today_name:
                continue
            sh, sm = map(int, slot['start'].split(':'))
            eh, em = map(int, slot['end'].split(':'))
            if sh * 60 + sm <= current_min <= eh * 60 + em:
                return True
        return False
    except Exception:
        return False


def _can_trigger(trigger: str) -> bool:
    last = _state["last_trigger_times"].get(trigger)
    if last is None:
        return True
    elapsed = (datetime.now(tz=KST) - last).total_seconds() / 60
    return elapsed >= COOLDOWN_MINUTES


def _mark_triggered(trigger: str):
    _state["last_trigger_times"][trigger] = datetime.now(tz=KST)


def generate_comment(trigger: str, bpm: float, steps: int) -> str:
    _, prompt_fn = _TRIGGER_PROMPTS[trigger]
    user_msg = prompt_fn(bpm, steps) + " 1~2문장, 최대 50자 이내로만 답해."
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=120,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text.strip()


def check_and_notify(bpm: float, steps: int) -> Optional[dict]:
    now = datetime.now(tz=KST)
    zone = classify_bpm(bpm)

    # 고강도 진입 시각 추적
    if zone in ("intense", "max"):
        if _state["high_intensity_start"] is None:
            _state["high_intensity_start"] = now
        elapsed_high = (now - _state["high_intensity_start"]).total_seconds() / 60
    else:
        _state["high_intensity_start"] = None
        elapsed_high = 0.0

    trigger = None

    # 우선순위 순으로 트리거 판단
    if elapsed_high >= 15 and _can_trigger("cooldown_needed"):
        trigger = "cooldown_needed"
    elif elapsed_high >= 5 and _can_trigger("sustained_effort"):
        trigger = "sustained_effort"
    elif zone in ("cardio", "intense", "max") and _state["last_zone"] in (None, "rest", "light") and _can_trigger("exercise_detected"):
        trigger = "exercise_detected"
    elif steps >= STEPS_GOAL and _state.get("goal_achieved_date") != now.strftime("%Y-%m-%d") and _can_trigger("goal_achieved"):
        trigger = "goal_achieved"
        _state["goal_achieved_date"] = now.strftime("%Y-%m-%d")
    elif zone == "rest" and is_free_slot_now() and _can_trigger("idle_in_free_slot"):
        trigger = "idle_in_free_slot"

    _state["last_zone"] = zone

    if trigger is None:
        return None

    _mark_triggered(trigger)
    notif_type, _ = _TRIGGER_PROMPTS[trigger]
    message = generate_comment(trigger, bpm, steps)

    return {
        "id": str(uuid.uuid4()),
        "type": notif_type,
        "message": message,
        "trigger": trigger,
        "bpm": bpm,
        "steps": steps,
        "timestamp": now.isoformat(),
    }
