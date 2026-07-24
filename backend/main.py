import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import CORS_ORIGINS
from backend.database.session import init_db
from backend.services.classifier_stream import classifier_stream
from backend.routers import alerts, auth, children, message, classifier

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
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(children.router)
app.include_router(alerts.router)
app.include_router(message.router)
app.include_router(classifier.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
