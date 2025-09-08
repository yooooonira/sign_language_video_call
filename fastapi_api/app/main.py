# --- 파일: fastapp/app/main.py ---

from fastapi import FastAPI
from .websocketServer import router  # @router.websocket("/ai")
import logging, os, numpy as np

try:
    from tflite_runtime.interpreter import Interpreter
except ImportError:
    from tensorflow.lite.python.interpreter import Interpreter  # fallback

from . import websocketServer

# <<< ADD: 학습과 동일 전처리를 위해 사용 (벡터 정규화 + 각도 등) -----------------
from modules.utils import Vector_Normalization
# >>> ADD END ------------------------------------------------------------------

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
# 화면 노이즈 감소용 신뢰도 임계치
MIN_CONF = float(os.getenv("MIN_CONFIDENCE", "0.8"))
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

        # >>> ADD: 입출력 shape/피처차원/클래스수 로깅 + 타입판단
        in_shape  = tuple(int(s) for s in _in_det[0]['shape'])
        out_shape = tuple(int(s) for s in _out_det[0]['shape'])
        feature_dim = int(in_shape[-1]) if len(in_shape) >= 3 else None
        num_classes = int(out_shape[-1]) if len(out_shape) >= 1 else None
        USE_JAMO = (num_classes == len(ACTIONS))

        logger.info("TFLite loaded: in=%s out=%s path=%s", in_shape, out_shape, MODEL_PATH)
        logger.info("TFLite feature_dim(per frame) = %s", feature_dim)
        logger.info("TFLite num_classes = %s", num_classes)
        logger.info("★★★ MODEL TYPE = %s", "JAMO" if USE_JAMO else "SENTENCE")
        # <<< ADD END

    except Exception:
        logger.exception("Failed to load TFLite model")
# >>> CHANGED END
# =========================================================


# =========================================================
# 전처리/보정 유틸
# =========================================================

# <<< ADD: (10,21,2) → (1,10,55) 전처리 (학습과 동일 경로) -----------------------
def frames_to_feats_55(frames_10x21x2: np.ndarray) -> np.ndarray:
    """
    입력: (10,21,2)  float32  [각 프레임에 21개 (x,y)]
    출력: (1,10,55) float32  [학습 당시와 동일한 55차 특징]
    NOTE:
      - 학습 코드에서 사용하던 Vector_Normalization + angle 기반 특징을 그대로 사용
      - joint는 (42,2)로 만들고, 0..20(=21개)에만 현재 손(한 손) 좌표를 채움
    """
    assert frames_10x21x2.shape == (10, 21, 2), f"unexpected shape {frames_10x21x2.shape}"
    feats = []
    for f in range(10):
        # (21,2) → (42,2) joint로 확장 (학습 코드 호환)
        joint = np.zeros((42, 2), dtype=np.float32)
        joint[:21, :] = frames_10x21x2[f]

        # 학습과 동일 전처리
        vector, angle_label = Vector_Normalization(joint)  # <-- 중요!
        d = np.concatenate([vector.flatten(), angle_label.flatten()]).astype(np.float32)
        feats.append(d)

    X = np.stack(feats, axis=0)  # (10, F)  보통 F=55
    # 기대 차원 로깅
    exp = int(_in_det[0]['shape'][2])
    if X.shape[1] != exp:
        logger.warning("per-frame feature mismatch: got=%d expected=%d", X.shape[1], exp)
    return X[None, :, :]         # (1,10,F)
# >>> ADD END ------------------------------------------------------------------


# <<< CHANGED: 어떤 입력이 와도 (1,10,55)로 강제 변환(패딩 제거, 전처리 적용) -------
def _coerce_to_1x10x55(arr: np.ndarray) -> np.ndarray:
    """
    허용 케이스와 변환:
      - (21,2)      : 단일 프레임 → 10프레임 타일링 → frames_to_feats_55()
      - (10,21,2)   : 그대로 frames_to_feats_55()
      - (10,42)     : 좌표로 간주해 (10,21,2)로 reshape 후 frames_to_feats_55()
      - (1,10,42)   : 좌표로 간주해 (10,21,2)로 reshape 후 frames_to_feats_55()
      - (10,55)     : 이미 특징이면 배치 축만 추가
      - (1,10,55)   : 그대로 통과
    """
    arr = np.asarray(arr, dtype=np.float32)

    # (1,*,*) → (*,*)로 평탄화
    if arr.ndim == 3 and arr.shape[0] == 1:
        arr = arr[0]

    # 단일 프레임 → 10프레임 복제 후 학습 전처리
    if arr.shape == (21, 2):
        arr10 = np.tile(arr[None, :, :], (10, 1, 1))      # (10,21,2)
        return frames_to_feats_55(arr10)                   # (1,10,55)

    # 표준 시퀀스(좌표) → 학습 전처리
    if arr.shape == (10, 21, 2):
        return frames_to_feats_55(arr)                     # (1,10,55)

    # (10,42) / (1,10,42) 좌표 → (10,21,2)로 바꾼 뒤 전처리
    if arr.shape == (10, 42):
        return frames_to_feats_55(arr.reshape(10, 21, 2))
    if arr.shape == (1, 10, 42):
        return frames_to_feats_55(arr.reshape(10, 21, 2))

    # 이미 특징(55)인 경우만 그대로
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

# >>> CHANGED: 단건 경로도 안전하게 (1,10,55)로 맞춰 추론
def predict_landmarks(landmarks):
    """
    landmarks 예시:
      - [ {x:float, y:float}, ... ] (길이 21)          -> (21,2)로 파싱
      - [ [x,y], [x,y], ... ] (길이 21)               -> (21,2)
      - 그 외 (10,21,2) / (10,42) / (10,55) / (1,10,42) / (1,10,55)
    반환: ("ai_result", str(pred_idx), score)
    """

    def to_ndarray(landmarks):
        if not landmarks:
            return np.zeros((21, 2), dtype=np.float32)
        first = landmarks[0]
        # dict 포맷([{x,y}, ...])
        if isinstance(first, dict) and "x" in first and "y" in first:
            # 단일 프레임(21개 포인트) 가정
            return np.asarray([[float(p["x"]), float(p["y"])] for p in landmarks], dtype=np.float32)  # (21,2)
        # 리스트 포맷([x,y] ...]
        if isinstance(first, (list, tuple)) and len(first) >= 2:
            return np.asarray(landmarks, dtype=np.float32)
        # 이미 ndarray
        return np.asarray(landmarks, dtype=np.float32)

    try:
        x_raw = to_ndarray(landmarks)
        x = _coerce_to_1x10x55(x_raw)  # <<< 핵심: (1,10,55)로 강제 변환

        # dtype 일치
        x = x.astype(_in_det[0]["dtype"], copy=False)

        # 안전 로깅(크래시 방지: assert 대신 경고)
        if len(_in_det[0]["shape"]) >= 3:
            expected = int(_in_det[0]["shape"][2])
            if x.shape[2] != expected:
                logger.warning("predict_landmarks() feature_dim mismatch: got=%d expected=%d", x.shape[2], expected)

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
# >>> CHANGED END


# >>> CHANGED: 시퀀스 경로도 (1,10,55)로 강제 변환 + 자모/문장 분기 + 임계치 필터
def predict_landmarks_sequence(frame_sequence):
    """
    10프레임 시퀀스 처리:
      frame_sequence 예시: (10,21,2) 또는 호환 가능한 형태
    반환: ("subtitle", translated_text, score)
    """
    try:
        arr = np.asarray(frame_sequence, dtype=np.float32)
        logger.info("시퀀스 입력 shape: %s", arr.shape)

        # 핵심: 어떤 형태든 (1,10,55)로 보정 (학습 전처리 적용)
        x = _coerce_to_1x10x55(arr)                           # (1,10,55)

        # dtype 일치
        x = x.astype(_in_det[0]["dtype"], copy=False)

        # 디버그: 기대 피처 차원 확인
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

        # <<< ADD: 낮은 신뢰도는 화면에 표시하지 않음
        if score < MIN_CONF:
            return "subtitle", "", score
        # >>> ADD END

        # 모델 타입에 따라 텍스트 생성
        if USE_JAMO:
            # 자모 모델: 인덱스를 자모 한 글자로 반환 (프런트에서 합성)
            translated_text = ACTIONS[pred_idx] if 0 <= pred_idx < len(ACTIONS) else ""
        else:
            # 문장/구 모델: 클래스 맵 필요
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
# >>> CHANGED END
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
