"""FastAPI Application Entry Point for Real-Time Fraud Detection & Risk Engine.

Configures CORS, life cycle events, Prometheus metrics, and REST routes.
"""

from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from database.connection import init_db
from services.api.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("fraud-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    logger.info("Initializing database schema...")
    try:
        init_db()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.warning("Database init warning: %s", e)
    yield
    logger.info("Shutting down Fraud Detection API.")


app = FastAPI(
    title="Real-Time Payment Fraud Detection & Risk Engine",
    description=(
        "Production-oriented streaming payment fraud detection API with "
        "calibrated XGBoost classifier, unsupervised Isolation Forest, "
        "SHAP explanations, and deterministic risk policy arbitration."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

# Mount Prometheus Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Mount Web Dashboard
web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "web")
if os.path.exists(web_dir):
    app.mount("/dashboard", StaticFiles(directory=web_dir, html=True), name="dashboard")

# Register API Routes
app.include_router(router)


@app.get("/")
def root():
    return {
        "service": "Real-Time Payment Fraud Detection & Risk Engine",
        "version": "1.0.0",
        "documentation": "/docs",
        "dashboard": "/dashboard",
        "health": "/api/v1/health",
        "metrics": "/metrics",
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run("services.api.main:app", host=host, port=port, reload=True)
