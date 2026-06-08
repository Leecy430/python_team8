"""
pt/notifier.py
SSE(Server-Sent Events) 기반 실시간 PT 알림 스트림
"""

import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/pt", tags=["pt-coach"])

# 연결된 SSE 구독자 큐 목록
_subscribers: list[asyncio.Queue] = []


async def broadcast(notification: dict):
    """모든 SSE 구독자에게 알림 전송"""
    dead = []
    for q in _subscribers:
        try:
            q.put_nowait(notification)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass


@router.get("/stream")
async def pt_stream():
    """
    SSE 스트림 엔드포인트.
    클라이언트는 여기에 연결해서 피티쌤 알림을 실시간으로 수신한다.
    30초마다 heartbeat(:)를 전송해 연결을 유지한다.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=10)
    _subscribers.append(queue)

    async def generate():
        try:
            while True:
                try:
                    notification = await asyncio.wait_for(queue.get(), timeout=30)
                    data = json.dumps(notification, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            try:
                _subscribers.remove(queue)
            except ValueError:
                pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/status")
def pt_status():
    """현재 PT 코치 상태 조회"""
    from pt.coach import _state, classify_bpm
    return {
        "subscribers": len(_subscribers),
        "last_zone": _state["last_zone"],
        "last_trigger_times": {
            k: v.isoformat() for k, v in _state["last_trigger_times"].items()
        },
        "high_intensity_active": _state["high_intensity_start"] is not None,
    }
