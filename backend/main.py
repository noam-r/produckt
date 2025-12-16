"""
ProDuckt FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from backend.config import settings
from backend.database import engine, Base
from backend.logging_config import setup_logging
import backend.models  # Import all models to register them with SQLAlchemy
from sqlalchemy import text

# Configure logging before anything else
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting ProDuckt API - Environment: {settings.environment}")

    # Create tables if they don't exist (development only)
    if settings.environment == "development":
        logger.info("Development mode: Creating database tables if needed")
        Base.metadata.create_all(bind=engine)

    # Start background job worker
    logger.info("Starting background job worker...")
    from backend.services.job_worker import start_job_worker
    start_job_worker(poll_interval=2)
    logger.info("Background job worker started")

    logger.info("ProDuckt API startup complete")

    yield

    # Shutdown: Clean up resources
    logger.info("Shutting down ProDuckt API")
    from backend.services.job_worker import stop_job_worker
    stop_job_worker()
    logger.info("Background job worker stopped")


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
logger.info(f"Configuring CORS for origins: {settings.get_cors_origins()}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware (executes second to last)
from backend.middleware.request_logging import RequestLoggingMiddleware
app.add_middleware(RequestLoggingMiddleware)

# Rate limiting middleware (executes first, so added last)
from backend.middleware.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)


@app.get("/health")
async def health_check():
    """
    Health check endpoint for Docker and monitoring.
    Checks database connectivity and returns service status.
    """
    from fastapi import HTTPException
    from backend.database import SessionLocal
    
    health_status = {
        "status": "healthy",
        "environment": settings.environment,
        "version": "1.0.0",
        "components": {}
    }
    
    # Check database connectivity
    try:
        db = SessionLocal()
        try:
            # Execute a simple query to verify database connection
            db.execute(text("SELECT 1"))
            db.commit()
            db_type = "sqlite" if settings.database_url.startswith("sqlite") else "postgresql"
            health_status["components"]["database"] = {
                "status": "healthy",
                "type": db_type
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Health check failed: Database connection error - {str(e)}", exc_info=True)
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: Database connection failed - {str(e)}"
        )
    
    return health_status


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


@app.get("/debug/job-worker")
async def debug_job_worker():
    """Debug job worker status."""
    from backend.services.job_worker import get_job_worker
    from backend.database import SessionLocal
    from backend.models import Job, JobStatus
    from sqlalchemy import func
    
    worker = get_job_worker()
    
    # Get job statistics
    db = SessionLocal()
    try:
        job_stats = db.query(
            Job.status, 
            func.count(Job.id).label('count')
        ).group_by(Job.status).all()
        
        pending_jobs = db.query(Job).filter(Job.status == JobStatus.PENDING).count()
        
    finally:
        db.close()
    
    worker_health = worker.get_health_status() if worker else None
    
    return {
        "worker_exists": worker is not None,
        "worker_health": worker_health,
        "job_statistics": {str(status): count for status, count in job_stats},
        "pending_jobs_count": pending_jobs,
        "recommendations": {
            "worker_ok": worker is not None and worker.running,
            "jobs_processing": pending_jobs == 0,
            "action_needed": "Restart backend service" if not worker else None
        }
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
