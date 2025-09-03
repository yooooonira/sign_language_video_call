# from fastapi import FastAPI
# from .websockets import router
# import logging


# logging.basicConfig(level=logging.INFO,
#                     format="%(asctime)s %(levelname)s %(name)s - %(message)s",
#                     force=True,)  # uvicorn 기본 로그 덮기 

# logger = logging.getLogger(__name__)

# app = FastAPI()


# @app.get("/ai/health")
# def health():
#     return {"status": "ok"}

# app.include_router(router)
# logger.info("FastAPI 컨테이너 실행됨 (8000)") #★


import os
import logging
from fastapi import FastAPI
from .websockets import router

# LOG_LEVEL 환경변수 반영
level_name = os.getenv("LOG_LEVEL", "INFO").upper()
level = getattr(logging, level_name, logging.INFO)
logging.basicConfig(
    level=level,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/ai/health")
def health():
    return {"status": "ok"}

app.include_router(router)
logger.info("FastAPI 컨테이너 실행됨 (8001)")