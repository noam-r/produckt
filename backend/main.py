"""
ProDuckt FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.config import settings
from backend.database import engine, Base
import backend.models  # Import all models to register them with SQLAlchemy


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup: Create tables if they don't exist (development only)
    if settings.environment == "development":
        Base.metadata.create_all(bind=engine)

    yield

    # Shutdown: Clean up resources
    pass


# Create FastAPI app
app = FastAPI(
    title="ProDuckt API",
    description="MRD Orchestration Platform using Claude 3.5 Sonnet",
    version="1.0.0",
    lifespan=lifespan
)

# Configure middlewares
# Note: Middleware order matters - they execute in reverse order of addition

# CORS middleware (executes last, so added first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware (executes first, so added last)
from backend.middleware.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "ProDuckt API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/debug/cors")
async def debug_cors():
    """Debug CORS configuration."""
    return {
        "cors_origins": settings.get_cors_origins(),
        "cors_origins_raw": settings.cors_origins
    }


@app.get("/debug/config")
async def debug_config():
    """Debug configuration values."""
    return {
        "anthropic_api_timeout": settings.anthropic_api_timeout,
        "anthropic_model": settings.anthropic_model,
        "environment": settings.environment
    }


# Import and include routers
from backend.routers import auth, initiatives, questions, context, agents, jobs, admin

app.include_router(auth.router)
app.include_router(initiatives.router, prefix="/api")
app.include_router(questions.router, prefix="/api")
app.include_router(context.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(jobs.router)
app.include_router(admin.router, prefix="/api")

# Additional routers will be added in later stages
# from backend.routers import context, users, questions
# app.include_router(context.router, prefix="/api/context", tags=["context"])
# app.include_router(users.router, prefix="/api/users", tags=["users"])
# app.include_router(questions.router, prefix="/api/questions", tags=["questions"])
