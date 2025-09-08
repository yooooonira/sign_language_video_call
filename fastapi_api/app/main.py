# --- 파일: fastapp/app/main.py ---

from fastapi import FastAPI
from .websocketServer import router  # @router.websocket("/ai")
import logging, os, numpy as np

try:
    from tflite_runtime.interpreter import Interpreter
except ImportError:
    from tensorflow.lite.python.interpreter import Interpreter  # fallback

from . import websocketServer

# <<< ADD: modules.utils 를 찾기 위해 AI_Language 경로를 sys.path에 추가 ----------------
import sys
AI_LANGUAGE_DIR = os.getenv("AI_LANGUAGE_DIR", "/fastapp/AI_Language")
if os.path.isdir(AI_LANGUAGE_DIR) and AI_LANGUAGE_DIR not in sys.path:
    sys.path.insert(0, AI_LANGUAGE_DIR)
else:
    # 경로가 없으면 경고 (fallback 전처리 사용)
    print(f"[WARN] AI_LANGUAGE_DIR not found: {AI_LANGUAGE_DIR}")

try:
    # AI_Language/modules/utils.py 안의 Vector_Normalization 사용
    from modules.utils import Vector_Normalization  # noqa: E402
    HAVE_VECTOR = True
except Exception as e:
    print(f"[WARN] cannot import modules.utils.Vector_Normalization -> {e}")
    HAVE_VECTOR = False
# >>> ADD END -------------------------------------------------------------------

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
_interpreter = None
_in_det = None
_out_det = None

# =========================================================
# <<< ADD: 자모 라벨과 모델 타입 플래그(자동판단용)
ACTIONS = [
    'ㄱ','ㄴ','ㄷ','ㄹ','ㅁ','ㅂ','ㅅ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ',
    'ㅏ','ㅑ','ㅓ','ㅕ','ㅗ','ㅛ','ㅜ','ㅠ','ㅡ','ㅣ',
    'ㅐ','ㅒ','ㅔ','ㅖ','ㅢ','ㅚ','ㅟ'
]
USE_JAMO = False  # num_classes == len(ACTIONS) 이면 자모 모델로 간주
MIN_CONF = float(os.getenv("MIN_CONFIDENCE", "0.8"))  # 낮은 확률 필터
# >>> ADD END
# =========================================================


# =========================================================
# <<< CHANGED: load_model 에 로깅/모델타입 자동판단 추가
# =========================================================
@app.on_event("startup")  # 서버가 시작되면 실행
def load_model():
    global _interpreter, _in_det, _out_det, USE_JAMO
    try:
        _interpreter = Interpreter(model_path=MODEL_PATH)
        _interpreter.allocate_tensors()
        _in_det = _interpreter.get_input_details()
        _out_det = _interpreter.get_output_details()

        # 입출력 shape/피처차원/클래스수 로깅 + 타입판단
        in_shape  = tuple(int(s) for s in _in_det[0]['shape'])
        out_shape = tuple(int(s) for s in _out_det[0]['shape'])
        feature_dim = int(in_shape[-1]) if len(in_shape) >= 3 else None
        num_classes = int(out_shape[-1]) if len(out_shape) >= 1 else None
        USE_JAMO = (num_classes == len(ACTIONS))

        logger.info("TFLite loaded: in=%s out=%s path=%s", in_shape, out_shape, MODEL_PATH)
        logger.info("TFLite feature_dim(per frame) = %s", feature_dim)
        logger.info("TFLite num_classes = %s", num_classes)
        logger.info("★★★ MODEL TYPE = %s", "JAMO" if USE_JAMO else "SENTENCE")

        # <<< ADD: Vector_Normalization import 성공/실패 정보
        logger.info("Vector_Normalization available = %s (from %s)", HAVE_VECTOR, AI_LANGUAGE_DIR)
        # >>> ADD END

    except Exception:
        logger.exception("Failed to load TFLite model")
# >>> CHANGED END
# =========================================================


# =========================================================
# 전처리/보정 유틸
# =========================================================

# <<< ADD: 학습 전처리 버전 (Vector_Normalization 이 있을 때만 사용) --------------
def frames_to_feats_55(frames_10x21x2: np.ndarray) -> np.ndarray:
    """
    입력: (10,21,2) float32
    출력: (1,10,55) float32  (Vector_Normalization 기반, 학습과 동일 경로)
    """
    assert frames_10x21x2.shape == (10, 21, 2), f"unexpected shape {frames_10x21x2.shape}"
    feats = []
    for f in range(10):
        # 학습 코드가 (42,2) joint를 받도록 되어 있으므로 21개만 채움
        joint = np.zeros((42, 2), dtype=np.float32)
        joint[:21, :] = frames_10x21x2[f]
        vector, angle_label = Vector_Normalization(joint)
        d = np.concatenate([vector.flatten(), angle_label.flatten()]).astype(np.float32)
        feats.append(d)
    X = np.stack(feats, axis=0)  # (10,55 예상)
    return X[None, :, :]         # (1,10,55)
# >>> ADD END ------------------------------------------------------------------


# <<< ADD: 임시(폴백) 전처리 — Vector_Normalization 을 못 쓸 때만 사용 --------------
def fallback_preprocess_to_55(frames_10x21x2: np.ndarray) -> np.ndarray:
    """
    입력: (10,21,2) → 좌표 42개 평탄화 + 13개 zero padding = 55
    ※ 정확도는 낮을 수 있음(학습 전처리와 다름). 임시 비상용.
    """
    base = frames_10x21x2.reshape(10, 42).astype(np.float32)  # (10,42)
    pad = np.zeros((10, 13), dtype=np.float32)                # (10,13)
    feats = np.concatenate([base, pad], axis=1)               # (10,55)
    return feats[None, :, :]                                  # (1,10,55)
# >>> ADD END ------------------------------------------------------------------


# <<< CHANGED: 어떤 입력이 와도 (1,10,55)로 강제 변환(전처리/폴백 자동 선택) --------
def _coerce_to_1x10x55(arr: np.ndarray) -> np.ndarray:
    """
    허용 케이스와 변환:
      - (21,2)      : 단일 프레임 → 10프레임 타일링 → (전처리)
      - (10,21,2)   : (전처리)
      - (10,42)     : 좌표로 간주해 (10,21,2)로 reshape 후 (전처리)
      - (1,10,42)   : 좌표로 간주해 (10,21,2)로 reshape 후 (전처리)
      - (10,55)/(1,10,55): 이미 특징이면 그대로
    """
    arr = np.asarray(arr, dtype=np.float32)

    # (1,*,*) → (*,*)로 평탄화
    if arr.ndim == 3 and arr.shape[0] == 1:
        arr = arr[0]

    # (21,2) → 10프레임 복제
    if arr.shape == (21, 2):
        arr = np.tile(arr[None, :, :], (10, 1, 1))  # (10,21,2)

    # 좌표 시퀀스 → 특징
    if arr.shape == (10, 21, 2):
        if HAVE_VECTOR:
            return frames_to_feats_55(arr)
        else:
            logger.warning("Using FALLBACK preprocessing (accuracy may degrade)")
            return fallback_preprocess_to_55(arr)

    # 좌표 평탄화(10,42)/(1,10,42)
    if arr.shape == (10, 42):
        arr = arr.reshape(10, 21, 2)
        return _coerce_to_1x10x55(arr)
    if arr.shape == (1, 10, 42):
        arr = arr.reshape(10, 21, 2)
        return _coerce_to_1x10x55(arr)

    # 이미 특징이면 그대로
    if arr.shape == (10, 55):
        return arr[None, :, :]
    if arr.shape == (1, 10, 55):
        return arr

    raise ValueError(f"지원하지 않는 입력 형태: {arr.shape}")
# >>> CHANGED END --------------------------------------------------------------
# =========================================================


# =========================================================
# 추론 함수들
# =========================================================

def predict_landmarks(landmarks):
    """단건(한 프레임) 추론: 내부에서 10프레임으로 타일링 후 시퀀스 경로로 처리"""
    def to_ndarray(landmarks):
        if not landmarks:
            return np.zeros((21, 2), dtype=np.float32)
        first = landmarks[0]
        if isinstance(first, dict) and "x" in first and "y" in first:
            return np.asarray([[float(p["x"]), float(p["y"])] for p in landmarks], dtype=np.float32)  # (21,2)
        if isinstance(first, (list, tuple)) and len(first) >= 2:
            return np.asarray(landmarks, dtype=np.float32)
        return np.asarray(landmarks, dtype=np.float32)

    try:
        x_raw = to_ndarray(landmarks)
        x = _coerce_to_1x10x55(x_raw)
        x = x.astype(_in_det[0]["dtype"], copy=False)
        _interpreter.set_tensor(_in_det[0]["index"], x)
        _interpreter.invoke()
        y = _interpreter.get_tensor(_out_det[0]["index"])
        probs = y[0].tolist()
        pred_idx = int(np.argmax(y[0]))
        score = float(max(probs))
        return "ai_result", str(pred_idx), score
    except Exception as e:
        logger.exception("단일 추론 실패: %s", e)
        return "ai_result", "-1", 0.0


def predict_landmarks_sequence(frame_sequence):
    """10프레임 시퀀스 추론"""
    try:
        arr = np.asarray(frame_sequence, dtype=np.float32)
        logger.info("시퀀스 입력 shape: %s", arr.shape)

        x = _coerce_to_1x10x55(arr)   # (1,10,55)
        x = x.astype(_in_det[0]["dtype"], copy=False)

        expected = int(_in_det[0]["shape"][2]) if len(_in_det[0]["shape"]) >= 3 else None
        got = int(x.shape[2])
        logger.info("모델 입력 shape(보정 후): %s, feature=%s", x.shape, got)
        if expected is not None and got != expected:
            logger.warning("feature dim mismatch: got=%d expected=%d", got, expected)

        _interpreter.set_tensor(_in_det[0]["index"], x)
        _interpreter.invoke()
        y = _interpreter.get_tensor(_out_det[0]["index"])

        probs = y[0].tolist()
        pred_idx = int(np.argmax(y[0]))
        score = float(max(probs))

        # 낮은 신뢰도는 출력하지 않음
        if score < MIN_CONF:
            return "subtitle", "", score

        if USE_JAMO:
            translated_text = ACTIONS[pred_idx] if 0 <= pred_idx < len(ACTIONS) else ""
        else:
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
# =========================================================


# =========================================================
# 헬스체크 & 라우팅
# =========================================================
@app.get("/ai/health")
def health():
    return {"status": "ok", "model_loaded": _interpreter is not None}

app.include_router(websocketServer.router)

logger.info("FastAPI 컨테이너 실행됨 (8001)")
# =========================================================
