# fastapi_api/app/main.py
from fastapi import FastAPI
from .websockets import router
import logging, os, numpy as np

try:
    from tflite_runtime.interpreter import Interpreter
except ImportError:
    from tensorflow.lite.python.interpreter import Interpreter  # fallback

from . import websockets 

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()

MODEL_PATH = os.getenv("TFLITE_PATH", "/fastapp/AI_Language/models/multi_hand_gesture_classifier.tflite")
_interpreter = None
_in_det = None
_out_det = None

@app.on_event("startup")
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

def predict_landmarks(landmarks):  # landmarks: List[List[float]]
    if _interpreter is None:
        raise RuntimeError("model_not_loaded")
    x = np.asarray(landmarks, dtype=np.float32)
    if x.ndim == 2:
        x = x[None, ...]  # (T,D) -> (1,T,D)
    _interpreter.set_tensor(_in_det[0]["index"], x)
    _interpreter.invoke()
    y = _interpreter.get_tensor(_out_det[0]["index"])
    probs = y[0].tolist()
    pred_idx = int(np.argmax(y[0]))
    return pred_idx, probs

@app.get("/ai/health")
def health():
    return {"status": "ok", "model_loaded": _interpreter is not None}

app.include_router(websockets.router)

logger.info("FastAPI 컨테이너 실행됨 (8001)")
