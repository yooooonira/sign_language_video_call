# from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
# import os, json, time, uuid, hashlib, logging
# from typing import Any, Dict, Optional, List

# router = APIRouter()
# log = logging.getLogger("app.ws")

# # ====== 설정 ======
# AI_WS_TOKEN = os.getenv("AI_WS_TOKEN", "change-me-dev")
# ALLOWED_ORIGINS = {
#     o.strip() for o in os.getenv(
#         "ALLOWED_WS_ORIGINS",
#         "https://sign-language-video-call-frontend.vercel.app,https://5range.site,https://www.5range.site"
#     ).split(",")
#     if o.strip()
# }
# ALLOWED_ROLES = {"user", "ai", "client"}

# # 엄격 모드: 브라우저(user/client)엔 Origin 필수
# WS_REQUIRE_ORIGIN = os.getenv("WS_REQUIRE_ORIGIN", "1") == "1"

# @router.websocket("/ai")
# async def ai_ws(
#     ws: WebSocket,
#     token: str = Query(...),
#     role: str = Query(...),
#     room: str = Query(default=""),
# ):
#     await ws.accept()
#     start_ts = time.time()

#     origin_hdr = ws.headers.get("origin")
#     peer = f"{ws.client.host}:{ws.client.port}" if ws.client else "unknown"

#     # 역할 정규화
#     role = (role or "").lower()

#     # 1) 역할 검사
#     if role not in ALLOWED_ROLES:
#         log.warning({"event": "ws_reject", "reason": "role", "role": role, "peer": peer})
#         await ws.close(code=1008)
#         return

#     # 2) 토큰 검사
#     if token != AI_WS_TOKEN:
#         log.warning({"event": "ws_reject", "reason": "token", "peer": peer})
#         await ws.close(code=1008)
#         return

#     # 3) Origin 검사: 브라우저(user/client)만 엄격 적용
#     is_browser = role in {"user", "client"}
#     if WS_REQUIRE_ORIGIN and is_browser:
#         if not origin_hdr:
#             log.warning({"event": "ws_reject", "reason": "origin_missing", "peer": peer})
#             await ws.close(code=1008)
#             return
#         if ALLOWED_ORIGINS and origin_hdr not in ALLOWED_ORIGINS:
#             log.warning({"event": "ws_reject", "reason": "origin", "origin": origin_hdr, "peer": peer})
#             await ws.close(code=1008)
#             return

#     log.info({"event": "ws_accept", "origin": origin_hdr, "role": role, "room": room or None, "peer": peer})
#     # ... (이하 기존 로직 동일: coords_rx/caption 처리)

# # ====== 유틸 ======
# def _peer(ws: WebSocket) -> str:
#     try:
#         return f"{ws.client.host}:{ws.client.port}"
#     except Exception:
#         return "unknown"

# def _hash_short(b: bytes) -> str:
#     return hashlib.sha256(b).hexdigest()[:12]

# def _summarize_payload(raw: str, parsed: Dict[str, Any]) -> str:
#     """텍스트가 있으면 텍스트, 없으면 좌표 페이로드를 짧게 요약"""
#     origin = parsed.get("text") or parsed.get("raw_text")
#     if origin:
#         return origin
#     return f"[len={len(raw)} hash={_hash_short(raw.encode())}]"

# # ====== 메인 엔드포인트 ======
# @router.websocket("/ai")
# async def ai_ws(
#     ws: WebSocket,
#     token: str = Query(...),
#     role: str = Query(...),
#     room: str = Query(default=""),
# ):
#     """
#     클라이언트 → 서버:
#       - 텍스트 에코: {"text": "...", "room_id": "...", "corr_id": "..."}
#       - 좌표 전송 : {"type":"coords","hands":[[{x,y,z}*21],...],"room_id":"...","corr_id":"...","ts":...}

#     서버 → 클라이언트:
#       - 좌표 ACK : {"type":"coords_ack","corr_id":"...","hands":N,"count":POINTS}
#       - 캡션     : {"type":"caption","text":"...","corr_id":"..."}
#     """
#     # 먼저 수락 (검증 후 거절 시 1008로 닫음)
#     await ws.accept()
#     start_ts = time.time()

#     origin_hdr = ws.headers.get("origin")
#     if ALLOWED_ORIGINS and origin_hdr not in ALLOWED_ORIGINS:
#         log.warning({"event": "ws_reject", "reason": "origin", "origin": origin_hdr, "peer": _peer(ws)})
#         await ws.close(code=1008)
#         return
#     if role not in ALLOWED_ROLES:
#         log.warning({"event": "ws_reject", "reason": "role", "role": role, "peer": _peer(ws)})
#         await ws.close(code=1008)
#         return
#     if token != AI_WS_TOKEN:
#         log.warning({"event": "ws_reject", "reason": "token", "peer": _peer(ws)})
#         await ws.close(code=1008)
#         return

#     log.info({"event": "ws_accept", "origin": origin_hdr, "role": role, "room": room or None, "peer": _peer(ws)})

#     room_id: Optional[str] = room or None
#     corr_seed: Optional[str] = None

#     try:
#         while True:
#             raw = await ws.receive_text()
#             t0 = time.time()

#             # JSON 파싱
#             try:
#                 msg = json.loads(raw)
#             except Exception:
#                 msg = {"raw": raw}

#             # room/corr 보정
#             if room_id is None:
#                 room_id = msg.get("room_id") or "unknown"
#             if corr_seed is None:
#                 corr_seed = msg.get("corr_id") or str(uuid.uuid4())
#             corr_id = msg.get("corr_id") or corr_seed

#             # ---- 좌표 수신 경로 -------------------------------------------------
#             if msg.get("type") == "coords":
#                 hands: List[List[Dict[str, float]]] = msg.get("hands", [])
#                 hands_n = len(hands)
#                 points = sum(len(h) for h in hands)

#                 # 수신 로그
#                 log.info({
#                     "event": "coords_rx",
#                     "room_id": room_id,
#                     "role": role,
#                     "corr_id": corr_id,
#                     "hands": hands_n,
#                     "points": points,
#                 })

#                 # ACK 회신 (브라우저 콘솔에서 수신 확인용)
#                 await ws.send_json({
#                     "type": "coords_ack",
#                     "corr_id": corr_id,
#                     "hands": hands_n,
#                     "count": points
#                 })

#                 # (검증용) 아주 단순한 캡션도 같이 내려서 DOM 표시까지 즉시 확인
#                 # 실제 수어 인식 모델 연결 전까지만 사용하세요.
#                 caption_text = f"좌표 수신: hands={hands_n}, points={points}"
#                 elapsed_ms = int((time.time() - t0) * 1000)
#                 log.info({
#                     "event": "caption",
#                     "room_id": room_id,
#                     "role": role,
#                     "corr_id": corr_id,
#                     "origin": "[coords]",
#                     "translated": caption_text,
#                     "ms": elapsed_ms,
#                 })
#                 await ws.send_json({"type": "caption", "text": caption_text, "corr_id": corr_id})
#                 continue

#             # ---- 텍스트 에코 경로 -----------------------------------------------
#             if "text" in msg and msg["text"] is not None:
#                 origin_txt = msg["text"]
#                 log.info({
#                     "event": "caption_rx",
#                     "room_id": room_id,
#                     "role": role,
#                     "corr_id": corr_id,
#                     "origin": origin_txt,
#                 })
#                 # (현재는 에코)
#                 translated = origin_txt
#                 elapsed_ms = int((time.time() - t0) * 1000)
#                 log.info({
#                     "event": "caption",
#                     "room_id": room_id,
#                     "role": role,
#                     "corr_id": corr_id,
#                     "origin": origin_txt,
#                     "translated": translated,
#                     "ms": elapsed_ms,
#                 })
#                 await ws.send_json({"type": "caption", "text": translated, "corr_id": corr_id})
#                 continue

#             # ---- 그 외 미처리 ---------------------------------------------------
#             log.info({
#                 "event": "unhandled",
#                 "room_id": room_id,
#                 "role": role,
#                 "corr_id": corr_id,
#                 "keys": list(msg.keys())
#             })

#     except WebSocketDisconnect:
#         alive_ms = int((time.time() - start_ts) * 1000)
#         log.info({
#             "event": "ws_disconnect",
#             "room_id": room_id,
#             "corr_id": corr_seed,
#             "alive_ms": alive_ms
#         })




from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import os, json, time, uuid, hashlib, logging
from typing import Any, Dict, Optional, List

router = APIRouter()
log = logging.getLogger("app.ws")

# ====== 설정 ======
AI_WS_TOKEN = os.getenv("AI_WS_TOKEN", "change-me-dev")

# 환경변수(ALLOWED_WS_ORIGINS)는 콤마로 구분된 목록.
# 비교 오류를 막기 위해 모두 소문자 + 끝 슬래시 제거로 정규화합니다.
def _normalize_origin(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    return s.strip().rstrip("/").lower()

ALLOWED_ORIGINS_RAW = os.getenv(
    "ALLOWED_WS_ORIGINS",
    "https://sign-language-video-call-frontend.vercel.app,https://5range.site,https://www.5range.site",
)
ALLOWED_ORIGINS: set[str] = {
    o for o in (_normalize_origin(x) for x in ALLOWED_ORIGINS_RAW.split(",")) if o
}

ALLOWED_ROLES = {"user", "ai", "client"}

# 브라우저(user/client) 역할에만 Origin 강제 (기본 1=켜짐)
WS_REQUIRE_ORIGIN = os.getenv("WS_REQUIRE_ORIGIN", "1") == "1"

# ====== 유틸 ======
def _peer(ws: WebSocket) -> str:
    try:
        return f"{ws.client.host}:{ws.client.port}"
    except Exception:
        return "unknown"

def _hash_short(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:12]

def _summarize_payload(raw: str, parsed: Dict[str, Any]) -> str:
    """텍스트가 있으면 텍스트, 없으면 페이로드 길이/해시로 요약"""
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
      - 텍스트: {"text": "...", "room_id": "...", "corr_id": "..."}
      - 좌표  : {"type":"coords","hands":[[{x,y,z}*21],...],"room_id":"...","corr_id":"...","ts":...}

    서버 → 클라이언트:
      - 좌표 ACK : {"type":"coords_ack","corr_id":"...","hands":N,"count":POINTS}
      - 캡션     : {"type":"caption","text":"...","corr_id":"..."}
    """
    # 선수락 → 검증 실패 시 1008로 종료
    await ws.accept()
    start_ts = time.time()
    peer = _peer(ws)

    # 헤더/쿼리 정규화
    origin_hdr_raw = ws.headers.get("origin")
    origin_hdr = _normalize_origin(origin_hdr_raw)
    role = (role or "").lower()

    # ---- 검증 ---------------------------------------------------------------
    if role not in ALLOWED_ROLES:
        log.warning({"event": "ws_reject", "reason": "role", "role": role, "peer": peer})
        await ws.close(code=1008)
        return

    if token != AI_WS_TOKEN:
        log.warning({"event": "ws_reject", "reason": "token", "peer": peer})
        await ws.close(code=1008)
        return

    # 브라우저 역할은 Origin 필수/허용목록 검사
    if WS_REQUIRE_ORIGIN and role in {"user", "client"}:
        if not origin_hdr:
            log.warning({"event": "ws_reject", "reason": "origin_missing", "peer": peer})
            await ws.close(code=1008)
            return
        if ALLOWED_ORIGINS and origin_hdr not in ALLOWED_ORIGINS:
            log.warning({
                "event": "ws_reject",
                "reason": "origin",
                "origin": origin_hdr_raw,   # 원본 표시(디버깅용)
                "peer": peer
            })
            await ws.close(code=1008)
            return

    log.info({
        "event": "ws_accept",
        "origin": origin_hdr_raw,
        "role": role,
        "room": room or None,
        "peer": peer
    })

    # ---- 메시지 루프 --------------------------------------------------------
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
                msg = {"raw_text": raw}

            # room/corr 보정
            if room_id is None:
                room_id = msg.get("room_id") or "unknown"
            if corr_seed is None:
                corr_seed = msg.get("corr_id") or str(uuid.uuid4())
            corr_id = msg.get("corr_id") or corr_seed

            # 좌표 수신
            if msg.get("type") == "coords":
                hands: List[List[Dict[str, float]]] = msg.get("hands", [])
                hands_n = len(hands)
                points = sum(len(h) for h in hands)

                log.info({
                    "event": "coords_rx",
                    "room_id": room_id,
                    "role": role,
                    "corr_id": corr_id,
                    "hands": hands_n,
                    "points": points,
                })

                # ACK
                await ws.send_json({
                    "type": "coords_ack",
                    "corr_id": corr_id,
                    "hands": hands_n,
                    "count": points
                })

                # (검증용) 간단 캡션
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

            # 텍스트 에코
            if "text" in msg and msg["text"] is not None:
                origin_txt = msg["text"]
                log.info({
                    "event": "caption_rx",
                    "room_id": room_id,
                    "role": role,
                    "corr_id": corr_id,
                    "origin": origin_txt,
                })
                translated = origin_txt  # 현재는 에코
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

            # 미처리
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
