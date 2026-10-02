"""FastAPI Application Entry Point for Real-Time Fraud Detection & Risk Engine.

Configures CORS, life cycle events, Prometheus metrics, and REST routes.
"""

from contextlib import asynccontextmanager
import logging
import os
import sys

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces OWASP recommended security headers on all incoming/outgoing HTTP traffic."""
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


# CORS Middleware
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(SecurityHeadersMiddleware)
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

# Mount Web Dashboard (React 19 + Tailwind CSS production build)
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")

if os.path.exists(frontend_dist):
    app.mount("/dashboard", StaticFiles(directory=frontend_dist, html=True), name="dashboard")

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
