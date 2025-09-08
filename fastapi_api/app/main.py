from fastapi import FastAPI
from .websocketServer import router  #@router.websocket("/ai"
import logging, os, numpy as np

try:
    from tflite_runtime.interpreter import Interpreter
except ImportError:
    from tensorflow.lite.python.interpreter import Interpreter  # fallback

from . import websocketServer

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")          # 로거
logger = logging.getLogger(__name__)

app = FastAPI()

MODEL_PATH = os.getenv("TFLITE_PATH", "/fastapp/AI_Language/models/multi_hand_gesture_classifier.tflite")
_interpreter = None
_in_det = None
_out_det = None

@app.on_event("startup")  #서버가 시작되면 실행
def load_model():
    global _interpreter, _in_det, _out_det
    try:
        _interpreter = Interpreter(model_path=MODEL_PATH)
        _interpreter.allocate_tensors()
        _in_det = _interpreter.get_input_details()
        _out_det = _interpreter.get_output_details()
        logger.info(f"TFLite loaded: in={_in_det[0]['shape']} out={_out_det[0]['shape']} path={MODEL_PATH}")
    except Exception:
        logger.exception("Failed to load TFLite model")

def predict_landmarks(landmarks):  # 추론
    # "landmarks": [ [ { "x": number, "y": number }, ... ], ... ]

    def to_text(landmarks):
        if not landmarks:
            return np.zeros((1, 1, 2), dtype=np.float32)
        # hands > dict points
        if isinstance(landmarks[0], list) and landmarks[0] and isinstance(landmarks[0][0], dict):
            arr = np.asarray([[[float(p["x"]), float(p["y"])] for p in hand] for hand in landmarks], dtype=np.float32)
        # hands > list points
        elif isinstance(landmarks[0], list) and landmarks[0] and isinstance(landmarks[0][0], (int, float)):
            arr = np.asarray(landmarks, dtype=np.float32)  # shape (T,2)
        # single hand as dict list
        elif isinstance(landmarks[0], dict):
            arr = np.asarray([[float(p["x"]), float(p["y"])] for p in landmarks], dtype=np.float32)  # (T,2)
        else:
            arr = np.asarray(landmarks, dtype=np.float32)
        return arr

    x = to_text(landmarks)
    if x.ndim == 3:
        x = x[0]
    if x.ndim == 2:
        x = x[None, ...]

    _interpreter.set_tensor(_in_det[0]["index"], x)
    _interpreter.invoke()
    y = _interpreter.get_tensor(_out_det[0]["index"])

    probs = y[0].tolist()
    pred_idx = int(np.argmax(y[0]))
    score = float(max(probs))

    return  "ai_result",str(pred_idx), score

# 여기에 새로운 함수 추가
def predict_landmarks_sequence(frame_sequence):
    """15프레임 시퀀스를 처리하는 함수"""
    try:
        # frame_sequence: [[[x,y], [x,y], ...], [...], ...]  # 15프레임 x 21좌표

        # numpy 배열로 변환
        if isinstance(frame_sequence[0][0], list):
            # 이미 [[x,y], [x,y]] 형태
            arr = np.asarray(frame_sequence, dtype=np.float32)  # (15, 21, 2)
        else:
            # 다른 형태면 변환
            arr = np.asarray(frame_sequence, dtype=np.float32)

        logger.info("시퀀스 입력 shape: %s", arr.shape)

        # 모델 입력 형태에 맞게 reshape
        # 모델이 (15, 21*2) = (15, 42) 형태를 원한다면:
        if arr.shape == (15, 21, 2):
            x = arr.reshape(1, 15, 42)  # (1, 15, 42)
        else:
            # 다른 경우에 대한 처리
            x = arr.reshape(1, 15, -1)

        logger.info("모델 입력 shape: %s", x.shape)

        _interpreter.set_tensor(_in_det[0]["index"], x)
        _interpreter.invoke()
        y = _interpreter.get_tensor(_out_det[0]["index"])

        probs = y[0].tolist()
        pred_idx = int(np.argmax(y[0]))
        score = float(max(probs))

        # 수어 번역 결과 매핑 (예시)
        sign_language_map = {
            0: "안녕하세요",
            1: "감사합니다",
            2: "죄송합니다",
            3: "좋아요",
            4: "싫어요",
            # 더 많은 매핑 추가
        }

        translated_text = sign_language_map.get(pred_idx, f"수어_{pred_idx}")

        return "subtitle", translated_text, score

    except Exception as e:
        logger.exception("시퀀스 추론 실패: %s", e)
        return "subtitle", "인식 실패", 0.0

@app.get("/ai/health")
def health():
    return {"status": "ok", "model_loaded": _interpreter is not None}

app.include_router(websocketServer.router)

logger.info("FastAPI 컨테이너 실행됨 (8001)")