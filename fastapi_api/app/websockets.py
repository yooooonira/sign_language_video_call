# from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
# from .state import hub  #허브에 등록용 
# import asyncio, json  
# import logging


# logger = logging.getLogger(__name__)

# router = APIRouter()

# @router.websocket("/ai") # 클라이언트는 ws://localhost:8000/ai 로 연결. ai붙으면 허브로 들어감
# async def websocket_endpoint(  # 프런트에서 값가져오기
#     websocket: WebSocket,
#     token: str | None = Query(default=None),
#     role: str =  Query(...),
#     room: str = Query(default="")
# ):
#     await websocket.accept() # 클라이언트의 WebSocket 연결 요청을 수락
#     await hub.add(websocket, role=role, room=room) # 허브에 등록
#     logger.info("연결됨 role=%s room=%s", role, room or "(없음)") # ★ 영통안해도 뜸

#     try:
#         logger.info("WS 루프 시작")
#         while True:
#             message = await websocket.receive() #프런트에서 받고 
#             logger.info("WS 프런트 수신: keys=%s type=%s", list(message.keys()), message.get("type"))
            
#             if message.get("type") == "websocket.disconnect":#못받으면 break 나가기
#                 logger.info("WS -> websocket disconnect")
#                 break

#             if "text" in message and message["text"] is not None: #받은거 처리 
#                 raw = message["text"] #원천 
#                 logger.info("프런트 수신(raw, len=%d, head300=%r)", len(raw), raw[:300])

#                 # JSON이면 type 기반 라우팅
#                 try:
#                     data = json.loads(raw)
#                 except Exception:
#                     # JSON 아니면 같은 방 브로드캐스트(기존 동작 유지)
#                     logger.exception("JSON 파싱 실패 -> 같은 방 브로드캐스트")
#                     room_id = hub.room_of(websocket)
#                     for client in list(hub.in_room(room_id)):
#                         if client is not websocket:
#                             await client.send_text(raw)
#                     continue

#                 mtype = data.get("type")
#                 room_id = data.get("room_id") or hub.room_of(websocket)

#                 # 1) 프런트 -> AI 워커 : 좌표 전달
#                 if mtype == "hand_landmarks":
#                     payload = json.dumps(data)
#                     logger.info("AI로 전달 시작")
#                     for client in hub.by_role_in_room("ai", room_id):
#                             if client is not websocket:
#                                 try:
#                                     await client.send_text(payload)
#                                 except Exception:
#                                     logger.exception("AI로 전달 실패")
#                     logger.info("AI로 전달 종료")
#                     continue

#                 # 2) AI 워커 -> 프런트 : 자막 전달
#                 if mtype == "ai_result":
#                     payload = json.dumps(data)
#                     logger.info("클라이언트로 전달 시작")
#                     for client in hub.by_role_in_room("client", room_id):
#                         if client is not websocket:
#                             try:
#                                 await client.send_text(payload)
#                             except Exception:
#                                 logger.exception("클라이언트로 전달 실패")
#                     logger.info("클라이언트로 전달 종료")
#                     continue

#                 # 3) 그 외 텍스트는 같은 방 브로드캐스트(기존 동작 유지)
#                 payload = json.dumps(data)
#                 logger.info("브로드캐스트 시작")
#                 for client in list(hub.in_room(room_id)):
#                     if client is not websocket:
#                         try:
#                             await client.send_text(payload)
#                         except Exception:
#                             logger.exception("브로드캐스트 전송 실패")
#                 logger.info("브로드캐스트 종료")
#                 continue

#     except (WebSocketDisconnect, asyncio.TimeoutError):
#         logger.info("WS 예외 종료")
#     except Exception:
#         logger.exception("WS 루프 오류")
#     finally:
#         await hub.remove(websocket)
#         logger.info("hub 완료")

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import os, json, time, uuid, hashlib, logging
from typing import Any, Dict, Optional, List

router = APIRouter()
log = logging.getLogger("app.ws")

# ====== 설정 ======
AI_WS_TOKEN = os.getenv("AI_WS_TOKEN", "change-me-dev")
ALLOWED_ORIGINS = {
    o.strip() for o in os.getenv(
        "ALLOWED_WS_ORIGINS",
        "https://sign-language-video-call-frontend.vercel.app,https://5range.site,https://www.5range.site"
    ).split(",")
    if o.strip()
}
ALLOWED_ROLES = {"user", "ai", "client"}

# 엄격 모드: 브라우저(user/client)엔 Origin 필수
WS_REQUIRE_ORIGIN = os.getenv("WS_REQUIRE_ORIGIN", "1") == "1"

@router.websocket("/ai")
async def ai_ws(
    ws: WebSocket,
    token: str = Query(...),
    role: str = Query(...),
    room: str = Query(default=""),
):
    await ws.accept()
    start_ts = time.time()

    origin_hdr = ws.headers.get("origin")
    peer = f"{ws.client.host}:{ws.client.port}" if ws.client else "unknown"

    # 역할 정규화
    role = (role or "").lower()

    # 1) 역할 검사
    if role not in ALLOWED_ROLES:
        log.warning({"event": "ws_reject", "reason": "role", "role": role, "peer": peer})
        await ws.close(code=1008)
        return

    # 2) 토큰 검사
    if token != AI_WS_TOKEN:
        log.warning({"event": "ws_reject", "reason": "token", "peer": peer})
        await ws.close(code=1008)
        return

    # 3) Origin 검사: 브라우저(user/client)만 엄격 적용
    is_browser = role in {"user", "client"}
    if WS_REQUIRE_ORIGIN and is_browser:
        if not origin_hdr:
            log.warning({"event": "ws_reject", "reason": "origin_missing", "peer": peer})
            await ws.close(code=1008)
            return
        if ALLOWED_ORIGINS and origin_hdr not in ALLOWED_ORIGINS:
            log.warning({"event": "ws_reject", "reason": "origin", "origin": origin_hdr, "peer": peer})
            await ws.close(code=1008)
            return

    log.info({"event": "ws_accept", "origin": origin_hdr, "role": role, "room": room or None, "peer": peer})
    # ... (이하 기존 로직 동일: coords_rx/caption 처리)

# ====== 유틸 ======
def _peer(ws: WebSocket) -> str:
    try:
        return f"{ws.client.host}:{ws.client.port}"
    except Exception:
        return "unknown"

def _hash_short(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:12]

def _summarize_payload(raw: str, parsed: Dict[str, Any]) -> str:
    """텍스트가 있으면 텍스트, 없으면 좌표 페이로드를 짧게 요약"""
    origin = parsed.get("text") or parsed.get("raw_text")
    if origin:
        return origin
    return f"[len={len(raw)} hash={_hash_short(raw.encode())}]"

# ====== 메인 엔드포인트 ======
@router.websocket("/ai")
async def ai_ws(
    ws: WebSocket,
    token: str = Query(...),
    role: str = Query(...),
    room: str = Query(default=""),
):
    """
    클라이언트 → 서버:
      - 텍스트 에코: {"text": "...", "room_id": "...", "corr_id": "..."}
      - 좌표 전송 : {"type":"coords","hands":[[{x,y,z}*21],...],"room_id":"...","corr_id":"...","ts":...}

    서버 → 클라이언트:
      - 좌표 ACK : {"type":"coords_ack","corr_id":"...","hands":N,"count":POINTS}
      - 캡션     : {"type":"caption","text":"...","corr_id":"..."}
    """
    # 먼저 수락 (검증 후 거절 시 1008로 닫음)
    await ws.accept()
    start_ts = time.time()

    origin_hdr = ws.headers.get("origin")
    if ALLOWED_ORIGINS and origin_hdr not in ALLOWED_ORIGINS:
        log.warning({"event": "ws_reject", "reason": "origin", "origin": origin_hdr, "peer": _peer(ws)})
        await ws.close(code=1008)
        return
    if role not in ALLOWED_ROLES:
        log.warning({"event": "ws_reject", "reason": "role", "role": role, "peer": _peer(ws)})
        await ws.close(code=1008)
        return
    if token != AI_WS_TOKEN:
        log.warning({"event": "ws_reject", "reason": "token", "peer": _peer(ws)})
        await ws.close(code=1008)
        return

    log.info({"event": "ws_accept", "origin": origin_hdr, "role": role, "room": room or None, "peer": _peer(ws)})

    room_id: Optional[str] = room or None
    corr_seed: Optional[str] = None

    try:
        while True:
            raw = await ws.receive_text()
            t0 = time.time()

            # JSON 파싱
            try:
                msg = json.loads(raw)
            except Exception:
                msg = {"raw": raw}

            # room/corr 보정
            if room_id is None:
                room_id = msg.get("room_id") or "unknown"
            if corr_seed is None:
                corr_seed = msg.get("corr_id") or str(uuid.uuid4())
            corr_id = msg.get("corr_id") or corr_seed

            # ---- 좌표 수신 경로 -------------------------------------------------
            if msg.get("type") == "coords":
                hands: List[List[Dict[str, float]]] = msg.get("hands", [])
                hands_n = len(hands)
                points = sum(len(h) for h in hands)

                # 수신 로그
                log.info({
                    "event": "coords_rx",
                    "room_id": room_id,
                    "role": role,
                    "corr_id": corr_id,
                    "hands": hands_n,
                    "points": points,
                })

                # ACK 회신 (브라우저 콘솔에서 수신 확인용)
                await ws.send_json({
                    "type": "coords_ack",
                    "corr_id": corr_id,
                    "hands": hands_n,
                    "count": points
                })

                # (검증용) 아주 단순한 캡션도 같이 내려서 DOM 표시까지 즉시 확인
                # 실제 수어 인식 모델 연결 전까지만 사용하세요.
                caption_text = f"좌표 수신: hands={hands_n}, points={points}"
                elapsed_ms = int((time.time() - t0) * 1000)
                log.info({
                    "event": "caption",
                    "room_id": room_id,
                    "role": role,
                    "corr_id": corr_id,
                    "origin": "[coords]",
                    "translated": caption_text,
                    "ms": elapsed_ms,
                })
                await ws.send_json({"type": "caption", "text": caption_text, "corr_id": corr_id})
                continue

            # ---- 텍스트 에코 경로 -----------------------------------------------
            if "text" in msg and msg["text"] is not None:
                origin_txt = msg["text"]
                log.info({
                    "event": "caption_rx",
                    "room_id": room_id,
                    "role": role,
                    "corr_id": corr_id,
                    "origin": origin_txt,
                })
                # (현재는 에코)
                translated = origin_txt
                elapsed_ms = int((time.time() - t0) * 1000)
                log.info({
                    "event": "caption",
                    "room_id": room_id,
                    "role": role,
                    "corr_id": corr_id,
                    "origin": origin_txt,
                    "translated": translated,
                    "ms": elapsed_ms,
                })
                await ws.send_json({"type": "caption", "text": translated, "corr_id": corr_id})
                continue

            # ---- 그 외 미처리 ---------------------------------------------------
            log.info({
                "event": "unhandled",
                "room_id": room_id,
                "role": role,
                "corr_id": corr_id,
                "keys": list(msg.keys())
            })

    except WebSocketDisconnect:
        alive_ms = int((time.time() - start_ts) * 1000)
        log.info({
            "event": "ws_disconnect",
            "room_id": room_id,
            "corr_id": corr_seed,
            "alive_ms": alive_ms
        })