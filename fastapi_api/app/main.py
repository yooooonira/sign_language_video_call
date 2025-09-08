from fastapi import FastAPI
from .websocketServer import router  # @router.websocket("/ai")
import logging, os, numpy as np

try:
    from tflite_runtime.interpreter import Interpreter
except ImportError:
    from tensorflow.lite.python.interpreter import Interpreter  # fallback

# --- AI_Language 경로 추가 (Vector_Normalization 사용) ---------------------
import sys
AI_LANGUAGE_DIR = os.getenv("AI_LANGUAGE_DIR", "/fastapp/AI_Language")
if os.path.isdir(AI_LANGUAGE_DIR) and AI_LANGUAGE_DIR not in sys.path:
    sys.path.insert(0, AI_LANGUAGE_DIR)
else:
    print(f"[WARN] AI_LANGUAGE_DIR not found: {AI_LANGUAGE_DIR}")

try:
    from ..AI_Language.Sign_Language_Translation.modules.utils import Vector_Normalization  # 학습 전처리 경로
    HAVE_VECTOR = True
except Exception as e:
    print(f"[WARN] cannot import modules.utils.Vector_Normalization -> {e}")
    HAVE_VECTOR = False
# ------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()

MODEL_PATH = os.getenv(
    "TFLITE_PATH",
    "/fastapp/AI_Language/models/multi_hand_gesture_classifier.tflite"
)
ALWAYS_EMIT = os.getenv("ALWAYS_EMIT_CAPTION", "") == "1"

_interpreter = None
_in_det = None
_out_det = None

# --- 라벨/임계값 -----------------------------------------------------------
ACTIONS = [
    'ㄱ','ㄴ','ㄷ','ㄹ','ㅁ','ㅂ','ㅅ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ',
    'ㅏ','ㅑ','ㅓ','ㅕ','ㅗ','ㅛ','ㅜ','ㅠ','ㅡ','ㅣ',
    'ㅐ','ㅒ','ㅔ','ㅖ','ㅢ','ㅚ','ㅟ'
]
USE_JAMO = False  # num_classes == len(ACTIONS) 이면 자모 모델
MIN_CONF = float(os.getenv("MIN_CONFIDENCE", "0.8"))
# ------------------------------------------------------------------------


@app.on_event("startup")
def load_model():
    """TFLite 로딩 및 모델 타입 자동판단"""
    global _interpreter, _in_det, _out_det, USE_JAMO
    try:
        _interpreter = Interpreter(model_path=MODEL_PATH)
        _interpreter.allocate_tensors()
        _in_det = _interpreter.get_input_details()
        _out_det = _interpreter.get_output_details()

        in_shape  = tuple(int(s) for s in _in_det[0]['shape'])
        out_shape = tuple(int(s) for s in _out_det[0]['shape'])
        feature_dim = int(in_shape[-1]) if len(in_shape) >= 3 else None
        num_classes = int(out_shape[-1]) if len(out_shape) >= 1 else None
        USE_JAMO = (num_classes == len(ACTIONS))

        logger.info("TFLite loaded: in=%s out=%s path=%s", in_shape, out_shape, MODEL_PATH)
        logger.info("feature_dim=%s num_classes=%s", feature_dim, num_classes)
        logger.info("MODEL TYPE = %s", "JAMO" if USE_JAMO else "SENTENCE")
        logger.info("Vector_Normalization available = %s (from %s)", HAVE_VECTOR, AI_LANGUAGE_DIR)
    except Exception:
        logger.exception("Failed to load TFLite model")


# -------------------------- 전처리 유틸 -----------------------------------
def _frames_to_feats_55(frames_10x21x2: np.ndarray) -> np.ndarray:
    """(10,21,2) -> (1,10,55)  학습과 동일 경로(Vector_Normalization)"""
    assert frames_10x21x2.shape == (10, 21, 2), f"unexpected shape {frames_10x21x2.shape}"
    feats = []
    for f in range(10):
        joint = np.zeros((42, 2), dtype=np.float32)
        joint[:21, :] = frames_10x21x2[f]
        vector, angle_label = Vector_Normalization(joint)
        d = np.concatenate([vector.flatten(), angle_label.flatten()]).astype(np.float32)
        feats.append(d)
    X = np.stack(feats, axis=0)  # (10,55)
    return X[None, :, :]         # (1,10,55)


def _fallback_preprocess_to_55(frames_10x21x2: np.ndarray) -> np.ndarray:
    """임시 폴백: 정확도 낮을 수 있음 (학습전처리와 다름)"""
    base = frames_10x21x2.reshape(10, 42).astype(np.float32)
    pad = np.zeros((10, 13), dtype=np.float32)
    feats = np.concatenate([base, pad], axis=1)  # (10,55)
    return feats[None, :, :]                      # (1,10,55)


def _coerce_to_1x10x55(arr: np.ndarray) -> np.ndarray:
    """
    허용 케이스:
      - (21,2)       : 단일 프레임 → 10프레임 타일링 → (전처리)
      - (10,21,2)    : (전처리)
      - (10,42)/(1,10,42) : 좌표로 간주, reshape 후 전처리
      - (10,55)/(1,10,55) : 이미 특징이면 그대로
    """
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim == 3 and arr.shape[0] == 1:
        arr = arr[0]

    if arr.shape == (21, 2):
        arr = np.tile(arr[None, :, :], (10, 1, 1))  # (10,21,2)

    if arr.shape == (10, 21, 2):
        if HAVE_VECTOR:
            return _frames_to_feats_55(arr)
        else:
            logging.warning("Using FALLBACK preprocessing (accuracy may degrade)")
            return _fallback_preprocess_to_55(arr)

    if arr.shape == (10, 42):
        return _coerce_to_1x10x55(arr.reshape(10, 21, 2))
    if arr.shape == (1, 10, 42):
        return _coerce_to_1x10x55(arr.reshape(10, 21, 2))

    if arr.shape == (10, 55):
        return arr[None, :, :]
    if arr.shape == (1, 10, 55):
        return arr

    raise ValueError(f"지원하지 않는 입력 형태: {arr.shape}")


# -------------------------- 공통 라벨링 -----------------------------------
_SENTENCE_MAP = {
    0: "안녕하세요",
    1: "감사합니다",
    2: "죄송합니다",
    3: "좋아요",
    4: "싫어요",
}

def _label_from_idx(idx: int) -> str:
    if USE_JAMO:
        return ACTIONS[idx] if 0 <= idx < len(ACTIONS) else ""
    return _SENTENCE_MAP.get(idx, f"수어_{idx}")


# -------------------------- 추론 함수 -------------------------------------
def infer_any(x_1x10x55: np.ndarray):
    """(1,10,55) 입력으로 직접 추론"""
    x = x_1x10x55.astype(_in_det[0]["dtype"], copy=False)
    _interpreter.set_tensor(_in_det[0]["index"], x)
    _interpreter.invoke()
    y = _interpreter.get_tensor(_out_det[0]["index"])
    probs = y[0].tolist()
    idx = int(np.argmax(y[0]))
    score = float(max(probs))
    return idx, score


def predict_from_single_frame(points_21x2):
    """(21,2) 단일 프레임 추론 → (label, score)"""
    try:
        x = _coerce_to_1x10x55(np.asarray(points_21x2, dtype=np.float32))
        idx, score = infer_any(x)
        label = _label_from_idx(idx)
        if score < MIN_CONF and not ALWAYS_EMIT:
            return "", score
        return label, score

    except Exception:
        logger.exception("단일 프레임 추론 실패")
        return "", 0.0


def predict_from_sequence(frames_10x21x2):
    """(10,21,2) 시퀀스 추론 → (label, score)"""
    try:
        arr = np.asarray(frames_10x21x2, dtype=np.float32)
        x = _coerce_to_1x10x55(arr)
        expected = int(_in_det[0]["shape"][2]) if len(_in_det[0]["shape"]) >= 3 else None
        got = int(x.shape[2])
        if expected is not None and got != expected:
            logger.warning("feature dim mismatch: got=%d expected=%d", got, expected)
        idx, score = infer_any(x)
        label = _label_from_idx(idx)
        if score < MIN_CONF and not ALWAYS_EMIT:
            return "", score
        return label, score
    except Exception:
        logger.exception("시퀀스 추론 실패")
        return "", 0.0


# -------------------------- 헬스/라우팅 -----------------------------------
@app.get("/ai/health")
def health():
    return {"status": "ok", "model_loaded": _interpreter is not None}

app.include_router(router)
logger.info("FastAPI 컨테이너 실행됨 (8001)")
