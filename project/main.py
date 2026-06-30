import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from classifier_client import classifier_client
from routers import ingest, flags, parent

logger = logging.getLogger(__name__)

app = FastAPI(title="Child Safety Chat Monitor")

app.include_router(ingest.router, prefix="/api")
app.include_router(flags.router, prefix="/api")
app.include_router(parent.router, prefix="/api")

FRONTEND_DIR = Path(__file__).parent / "frontend"


@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.on_event("startup")
async def startup():
    try:
        await classifier_client.ensure_connected()
        logger.info("Classifier connected successfully")
    except ConnectionError:
        logger.warning("Classifier not connected at startup — will retry on ingest")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
