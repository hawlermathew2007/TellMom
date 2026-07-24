import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import CORS_ORIGINS
from backend.database.session import init_db
from backend.services.classifier_stream import classifier_stream
from backend.routers import alerts, auth, children, message, classifier, management
from backend.services.proxy_manager import proxy_manager
from backend.services.proxy_agent import load_state, ProxyState

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    load_state()
    state = ProxyState.current()
    proxy_manager.update_config(
        getattr(state, "proxy_url", ""),
        getattr(state, "username", ""),
        getattr(state, "password", ""),
        getattr(state, "local_url", ""),
    )
    try:
        await classifier_stream.ensure_connected()
        logger.debug("Classifier connected successfully")
    except ConnectionError:
        logger.debug("Classifier not connected at startup — will retry on ingest")
    yield


app = FastAPI(title="TellMom API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(children.router)
app.include_router(alerts.router)
app.include_router(message.router)
app.include_router(classifier.router)
app.include_router(management.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
