from fastapi import FastAPI
from .websockets import router
import logging


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
                    force=True,)  # uvicorn 기본 로그 덮기 

logger = logging.getLogger(__name__)
log = logging.getLogger("app.main")

app = FastAPI()

@app.get("/ai/health")
def health():
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    # 앱 부팅 로그
    log.info({"event": "app_start", "port": 8001})


app.include_router(router)
logger.info("FastAPI 컨테이너 실행됨 (8000)") #★





