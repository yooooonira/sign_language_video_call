from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .state import hub
import asyncio, json
from datetime import datetime

router = APIRouter()

def debug_log(message: str, data=None):
    """디버그 로그 헬퍼 함수"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")
    if data:
        print(f"[{timestamp}] Data: {data}")

@router.websocket("/ai") # 클라이언트는 ws://localhost:8000/ai 로 연결. ai붙으면 허브로 들어감
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    role: str = Query(default="client"),   # "client"(프런트) | "ai"(워커)
    room: str = Query(default="")
):
    await websocket.accept() # 클라이언트의 WebSocket 연결 요청을 수락
    await hub.add(websocket, role=role, room=room) # 허브에 등록

    # 연결 시 로그
    debug_log(f"🔌 WebSocket connected - Role: {role}, Room: {room}")

    try:
        while True:
            message = await websocket.receive()

            # ---- 텍스트 수신 (JSON) ----
            if "text" in message and message["text"] is not None:
                raw = message["text"]

                # JSON이면 type 기반 라우팅
                try:
                    data = json.loads(raw)
                    debug_log(f"📨 Received message type: {data.get('type')} from {role}")
                except Exception as e:
                    debug_log(f"❌ JSON parse error: {e}")
                    # JSON 아니면 같은 방 브로드캐스트(기존 동작 유지)
                    for client in list(hub.in_room(room)):
                        if client is not websocket:
                            await client.send_text(raw)
                    continue

                mtype = data.get("type")
                room_id = data.get("room_id") or room

                # 1) 프런트 -> AI 워커 : 좌표 전달
                if mtype == "hand_landmarks":
                    landmarks_count = len(data.get("landmarks", []))
                    hands_detected = sum(len(hand) for hand in data.get("landmarks", []))
                    debug_log(f"👋 Hand landmarks received - {landmarks_count} hands, {hands_detected} total points")
                    debug_log(f"📍 First landmark sample", data.get("landmarks", [[]])[0][:2] if data.get("landmarks") else "No data")

                    # AI 워커에게 전달
                    ai_clients = list(hub.by_role_in_room("ai", room_id))
                    debug_log(f"🤖 Forwarding to {len(ai_clients)} AI workers in room {room_id}")

                    payload = json.dumps(data)
                    for client in ai_clients:
                        if client is not websocket:
                            await client.send_text(payload)
                            debug_log(f"✅ Sent landmarks to AI worker")

                    if not ai_clients:
                        debug_log(f"⚠️  No AI workers found in room {room_id}")
                    continue

                # 2) AI 워커 -> 프런트 : 자막 전달
                if mtype == "ai_result":
                    translated_text = data.get("text", "")
                    confidence = data.get("score", 0)
                    frame_id = data.get("frame_id", "unknown")

                    debug_log(f"🎯 AI translation result received:")
                    debug_log(f"   📝 Text: '{translated_text}'")
                    debug_log(f"   🎲 Score: {confidence}")
                    debug_log(f"   🆔 Frame ID: {frame_id}")

                    # 프런트엔드 클라이언트들에게 전달
                    client_list = list(hub.by_role_in_room("client", room_id))
                    debug_log(f"📱 Forwarding to {len(client_list)} frontend clients in room {room_id}")

                    payload = json.dumps(data)
                    for client in client_list:
                        if client is not websocket:
                            await client.send_text(payload)
                            debug_log(f"✅ Sent translation to frontend client")

                    if not client_list:
                        debug_log(f"⚠️  No frontend clients found in room {room_id}")
                    continue

                # 3) 그 외 메시지 타입들 (ai_status 등)
                if mtype == "ai_status":
                    user_id = data.get("user_id", "unknown")
                    enabled = data.get("enabled", False)
                    debug_log(f"🔄 AI status change - User: {user_id}, Enabled: {enabled}")

                # 4) 그 외 텍스트는 같은 방 브로드캐스트(기존 동작 유지)
                debug_log(f"🔄 Broadcasting message type '{mtype}' to room {room_id}")
                payload = json.dumps(data)
                broadcasted = 0
                for client in list(hub.in_room(room_id)):
                    if client is not websocket:
                        await client.send_text(payload)
                        broadcasted += 1
                debug_log(f"📡 Broadcasted to {broadcasted} clients")
                continue

    except WebSocketDisconnect:
        debug_log(f"🔌 WebSocket disconnected - Role: {role}, Room: {room}")
    except asyncio.TimeoutError:
        debug_log(f"⏰ WebSocket timeout - Role: {role}, Room: {room}")
    except Exception as e:
        debug_log(f"❌ Unexpected error: {e}")
    finally:
        hub.remove(websocket)
        debug_log(f"🗑️  Removed from hub - Role: {role}, Room: {room}")

# 추가로 허브 상태를 확인하는 엔드포인트 (선택사항)
@router.get("/debug/hub-status")
async def get_hub_status():
    """현재 허브 상태를 확인하는 디버그 엔드포인트"""
    status = {
        "total_connections": len(hub._connections) if hasattr(hub, '_connections') else "unknown",
        "rooms": {},
        "roles": {"client": 0, "ai": 0}
    }

    # 방별, 역할별 통계 (hub 구현에 따라 조정 필요)
    try:
        for room_name in getattr(hub, '_rooms', {}):
            room_clients = list(hub.in_room(room_name))
            ai_clients = list(hub.by_role_in_room("ai", room_name))
            client_clients = list(hub.by_role_in_room("client", room_name))

            status["rooms"][room_name] = {
                "total": len(room_clients),
                "ai_workers": len(ai_clients),
                "frontend_clients": len(client_clients)
            }

            status["roles"]["client"] += len(client_clients)
            status["roles"]["ai"] += len(ai_clients)
    except:
        status["note"] = "Hub inspection failed - check hub implementation"

    return status