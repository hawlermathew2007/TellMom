from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from config import settings
from routes import auth, messages, alerts
from services.data_retention import start_retention_scheduler

# Logging
log_path = Path("logs/app.log")
log_path.parent.mkdir(parents=True, exist_ok=True)
log_path.touch(exist_ok=True)

logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle: startup and shutdown"""
    # Startup
    logger.info("[+] Child Safety Monitor starting...")
    logger.info(f"Database: {settings.database_url}")
    logger.info(f"Model: {settings.model_path}")
    logger.info(f"Device: {settings.device}")

    # Start data retention scheduler (COPPA compliance)
    scheduler_task = start_retention_scheduler()

    yield

    # Shutdown
    logger.info("[+] Child Safety Monitor shutting down...")

app = FastAPI(
    title="Child Safety Monitor API",
    description="Backend for real-time grooming detection & parent alerts",
    version="1.0.0",
    lifespan=lifespan,
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


# Root
@app.get("/")
async def root():
    """API root"""
    return {
        "message": "Child Safety Monitor API",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.fast_api_host,
        port=settings.fast_api_port,
        reload=settings.debug
    )
