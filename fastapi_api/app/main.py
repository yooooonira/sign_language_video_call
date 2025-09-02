from fastapi import FastAPI
from .websockets import router
import logging


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/ai/health")
def health():
    return {"status": "ok"}

app.include_router(router)
logger.info("FastAPI 컨테이너 실행됨 (8000)")
