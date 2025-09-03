import json, re, time
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest

SAFE_PREFIX = "/api/translate"
MASK = re.compile(r"(Authorization|token|password)", re.I)

def mask(d: dict):
    return {k: ("***" if MASK.search(k) else v) for k, v in d.items()}

class TranslateLogMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest):
        if request.path.startswith(SAFE_PREFIX) and request.method == "POST":
            request._start_ts = time.time()
            try:
                request._raw = request.body
                request._json = json.loads(request._raw or b"{}")
            except Exception:
                request._json = {}

    def process_response(self, request: HttpRequest, response):
        if getattr(request, "_json", None) is not None:
            ms = int((time.time() - getattr(request, "_start_ts", time.time())) * 1000)
            translated = None
            try:
                if "application/json" in response.get("Content-Type", ""):
                    translated = json.loads(response.content.decode("utf-8")).get("translated")
            except Exception:
                pass
            from django.conf import settings
            import logging
            logger = logging.getLogger(getattr(settings, "APP_LOGGER", "app"))
            logger.info({
                "event": "translate",
                "path": request.path,
                "ms": ms,
                "origin": mask(request._json).get("message"),
                "translated": translated,
            })
        return response