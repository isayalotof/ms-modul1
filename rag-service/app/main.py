import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api import router, health_router
from app.database import test_connection, close_db
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application"""
    # Startup
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")

    # Create upload directories
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.temp_dir, exist_ok=True)
    logger.info(f"Upload directory: {settings.upload_dir}")
    logger.info(f"Temp directory: {settings.temp_dir}")

    # Test database connection
    logger.info("Testing database connection...")
    db_ok = await test_connection()
    if not db_ok:
        logger.warning("Database connection failed, but continuing startup")

    logger.info(f"Embedding model: {settings.embedding_model}")
    logger.info(f"Anthropic model: {settings.anthropic_model}")
    logger.info("Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down service...")
    await close_db()
    logger.info("Service stopped")


# Create FastAPI application
app = FastAPI(
    title="RAG Service",
    description="Retrieval Augmented Generation microservice with PostgreSQL and pgvector",
    version=settings.service_version,
    lifespan=lifespan,
    debug=settings.debug
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "details": str(exc) if settings.debug else None
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
