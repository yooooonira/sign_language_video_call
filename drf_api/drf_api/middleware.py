import json
import re
import time
from typing import Optional

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

SAFE_PREFIX = "/api/translate"
MASK = re.compile(r"(Authorization|token|password)", re.I)


def mask(d: dict) -> dict:
    return {k: ("***" if MASK.search(k) else v) for k, v in d.items()}


class TranslateLogMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest) -> None:
        if request.path.startswith(SAFE_PREFIX) and request.method == "POST":
            request._start_ts = time.time()  # type: ignore
            try:
                request._raw = request.body  # type: ignore
                request._json = json.loads(request._raw or b"{}")  # type: ignore
            except Exception:
                request._json = {}  # type: ignore

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        if getattr(request, "_json", None) is not None:
            ms = int((time.time() - getattr(request, "_start_ts", time.time())) * 1000)
            translated: Optional[str] = None
            try:
                if "application/json" in response.get("Content-Type", ""):
                    response_data = json.loads(response.content.decode("utf-8"))
                    translated = response_data.get("translated")
            except Exception:
                pass

            import logging

            from django.conf import settings

            logger = logging.getLogger(getattr(settings, "APP_LOGGER", "app"))
            logger.info({
                "event": "translate",
                "path": request.path,
                "ms": ms,
                "origin": mask(getattr(request, "_json", {})).get("message"),
                "translated": translated,
            })
        return response
