from fastapi import FastAPI
from .websockets import router as ws_router

app = FastAPI()

@app.get("/ai/health")
def health():
    return {"status": "ok"}

app.include_router(ws_router)