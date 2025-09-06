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


@app.get("/ai/health")
def health():
    return {"status": "ok", "model_loaded": _interpreter is not None}

app.include_router(websocketServer.router)

logger.info("FastAPI 컨테이너 실행됨 (8001)")
