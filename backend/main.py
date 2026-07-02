from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core import config
from services.classifier_stream import classifier_stream
from database.session import init_db
from routers import alerts, auth, children, ingest

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    try:
        await classifier_stream.ensure_connected()
        logger.info("Classifier connected successfully")
    except ConnectionError:
        logger.warning("Classifier not connected at startup — will retry on ingest")
    yield


app = FastAPI(title="TellMom API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(children.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(ingest.classifier_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
