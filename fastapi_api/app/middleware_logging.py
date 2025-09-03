import json, re, time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

SAFE_PATHS = ("/api/translate",)  # 로깅할 엔드포인트만 지정
MASK = re.compile(r"(Authorization|token|password)", re.I)

def mask(d: dict):
    return {k: ("***" if MASK.search(k) else v) for k, v in d.items()}

class TranslateLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path not in SAFE_PATHS:
            return await call_next(request)

        t0 = time.time()
        body_bytes = await request.body()
        try:
            payload = json.loads(body_bytes or b"{}")
        except Exception:
            payload = {}

        # 다운스트림에서 다시 읽을 수 있게 body 재주입
        request._body = body_bytes

        response: Response = await call_next(request)
        elapsed = (time.time() - t0) * 1000

        # 응답 본문 추출(가능한 경우만)
        translated = None
        try:
            if "application/json" in response.headers.get("content-type", ""):
                translated = json.loads(response.body.decode("utf-8")).get("translated")
        except Exception:
            pass

        request.app.logger.info({
            "event": "translate",
            "path": request.url.path,
            "ms": round(elapsed, 1),
            "origin": mask(payload).get("message"),
            "translated": translated,
        })
        return response
