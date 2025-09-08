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

# >>> 추가: (10,21,2) → (1,10,55) 전처리 (임시 패딩 버전)
def preprocess_to_55(frames_10x21x2: np.ndarray) -> np.ndarray:
    """
    입력: (10, 21, 2) float32
    출력: (1, 10, 55) float32
    NOTE: 현재는 42 뒤에 13개 0을 패딩. 학습시 사용한 55차 전처리(정규화/거리/각도 등)를
          알고 있다면 반드시 그 규칙대로 계산해 교체하세요.
    """
    assert frames_10x21x2.shape == (10, 21, 2)
    base = frames_10x21x2.reshape(10, 42).astype(np.float32)  # (10,42)
    pad = np.zeros((10, 13), dtype=np.float32)                # (10,13)
    feats = np.concatenate([base, pad], axis=1)               # (10,55)
    return feats[np.newaxis, :, :]                            # (1,10,55)
# <<< 추가 끝

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

# 10프레임 시퀀스 처리
def predict_landmarks_sequence(frame_sequence):
    """10프레임 시퀀스를 처리하는 함수"""
    try:
        # numpy 배열로 변환
        if isinstance(frame_sequence[0][0], list):
            arr = np.asarray(frame_sequence, dtype=np.float32)  # (10, 21, 2)
        else:
            arr = np.asarray(frame_sequence, dtype=np.float32)

        logger.info("시퀀스 입력 shape: %s", arr.shape)

        # 10프레임, 21개 좌표, 2차원(x,y)인지 확인
        if arr.shape == (10, 21, 2):
            # (10, 21, 2) → (1, 10, 42) 로 변환
            x = arr.reshape(1, 10, 42)
        else:
            # 다른 형태면 에러
            raise ValueError(f"예상하지 못한 입력 형태: {arr.shape}")

        logger.info("모델 입력 shape: %s", x.shape)

        _interpreter.set_tensor(_in_det[0]["index"], x)
        _interpreter.invoke()
        y = _interpreter.get_tensor(_out_det[0]["index"])

        probs = y[0].tolist()
        pred_idx = int(np.argmax(y[0]))
        score = float(max(probs))

        sign_language_map = {
            0: "안녕하세요",
            1: "감사합니다",
            2: "죄송합니다",
            3: "좋아요",
            4: "싫어요",
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