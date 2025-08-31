from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .state import hub
import asyncio, json
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ai") # 클라이언트는 ws://localhost:8000/ai 로 연결. ai붙으면 허브로 들어감
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    role: str = Query(default="client"),   # "client"(프런트) | "ai"(워커)
    room: str = Query(default="")
):
    client_info = f"[{role}:{room}]"
    logger.info(f"{client_info} WebSocket connection attempt from {websocket.client}")

    await websocket.accept() # 클라이언트의 WebSocket 연결 요청을 수락
    await hub.add(websocket, role=role, room=room) # 허브에 등록

    logger.info(f"{client_info} WebSocket connected successfully")
    logger.info(f"Hub status - Room '{room}': {len(list(hub.in_room(room)))} total, "
               f"{len(list(hub.by_role_in_room('client', room)))} clients, "
               f"{len(list(hub.by_role_in_room('ai', room)))} AI workers")

    try:
        while True:
            message = await websocket.receive()

            # ---- 텍스트 수신 (JSON) ----
            if "text" in message and message["text"] is not None:
                raw = message["text"]

                # 메시지 길이 체크 (너무 길면 줄임)
                log_msg = raw if len(raw) <= 200 else raw[:200] + "..."
                logger.info(f"{client_info} Received message: {log_msg}")

                # JSON 파싱 시도
                try:
                    data = json.loads(raw)
                except Exception as e:
                    logger.warning(f"{client_info} Failed to parse JSON: {e}")
                    # JSON 아니면 같은 방 브로드캐스트(기존 동작 유지)
                    for client in list(hub.in_room(room)):
                        if client is not websocket:
                            await client.send_text(raw)
                    continue

                mtype = data.get("type")
                room_id = data.get("room_id") or room
                timestamp = data.get("timestamp", "N/A")

                logger.info(f"{client_info} Parsed JSON - Type: {mtype}, Room: {room_id}, Timestamp: {timestamp}")

                # 1) 프런트 -> AI 워커 : 좌표 전달
                if mtype == "hand_landmarks":
                    landmarks = data.get("landmarks", [])
                    hands_count = len(landmarks)
                    total_points = sum(len(hand) for hand in landmarks) if landmarks else 0

                    logger.info(f"{client_info} HAND_LANDMARKS - Hands: {hands_count}, Total points: {total_points}")

                    # 첫 번째 손의 첫 번째 점 좌표 샘플 로그
                    if landmarks and landmarks[0]:
                        sample_point = landmarks[0][0]
                        logger.info(f"{client_info} Sample coordinate - Hand1[0]: x={sample_point.get('x', 'N/A'):.3f}, y={sample_point.get('y', 'N/A'):.3f}")

                    # AI 워커 찾기
                    ai_workers = list(hub.by_role_in_room("ai", room_id))
                    logger.info(f"{client_info} Found {len(ai_workers)} AI workers for room '{room_id}'")

                    if ai_workers:
                        payload = json.dumps(data)
                        sent_count = 0
                        for client in ai_workers:
                            if client is not websocket:
                                try:
                                    await client.send_text(payload)
                                    sent_count += 1
                                except Exception as e:
                                    logger.error(f"{client_info} Failed to send to AI worker: {e}")

                        logger.info(f"{client_info} Hand landmarks sent to {sent_count} AI workers")
                    else:
                        logger.warning(f"{client_info} No AI workers available in room '{room_id}'")

                    continue

                # 2) AI 워커 -> 프런트 : 자막 전달
                if mtype == "ai_result":
                    result_text = data.get("text", "")
                    score = data.get("score", "N/A")

                    logger.info(f"{client_info} AI_RESULT - Text: '{result_text}', Score: {score}")

                    # 프런트엔드 클라이언트 찾기
                    front_clients = list(hub.by_role_in_room("client", room_id))
                    logger.info(f"{client_info} Found {len(front_clients)} frontend clients for room '{room_id}'")

                    if front_clients:
                        payload = json.dumps(data)
                        sent_count = 0
                        for client in front_clients:
                            if client is not websocket:
                                try:
                                    await client.send_text(payload)
                                    sent_count += 1
                                except Exception as e:
                                    logger.error(f"{client_info} Failed to send to frontend client: {e}")

                        logger.info(f"{client_info} AI result sent to {sent_count} frontend clients")
                    else:
                        logger.warning(f"{client_info} No frontend clients available in room '{room_id}'")

                    continue

                # 3) 그 외 텍스트는 같은 방 브로드캐스트(기존 동작 유지)
                logger.info(f"{client_info} Broadcasting message type '{mtype}' to room '{room_id}'")
                payload = json.dumps(data)
                broadcast_count = 0
                for client in list(hub.in_room(room_id)):
                    if client is not websocket:
                        try:
                            await client.send_text(payload)
                            broadcast_count += 1
                        except Exception as e:
                            logger.error(f"{client_info} Failed to broadcast to client: {e}")

                logger.info(f"{client_info} Message broadcasted to {broadcast_count} clients")
                continue

    except WebSocketDisconnect:
        logger.info(f"{client_info} WebSocket disconnected normally")
    except asyncio.TimeoutError:
        logger.warning(f"{client_info} WebSocket timeout")
    except Exception as e:
        logger.error(f"{client_info} WebSocket error: {e}")
    finally:
        hub.remove(websocket)
        logger.info(f"{client_info} WebSocket removed from hub")
        logger.info(f"Hub status after removal - Room '{room}': {len(list(hub.in_room(room)))} remaining clients")