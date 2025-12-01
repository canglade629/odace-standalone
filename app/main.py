"""Main FastAPI application."""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.models import HealthResponse
from app.core.rate_limiter import limiter
from app.api.routes import bronze, silver, gold, pipeline, files, data, jobs, admin, docs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import all pipeline modules to trigger registration
import app.pipelines.bronze.accueillants
import app.pipelines.bronze.geo
import app.pipelines.bronze.logement
import app.pipelines.bronze.transport
import app.pipelines.bronze.zones_attraction
import app.pipelines.bronze.siae_postes
import app.pipelines.bronze.siae_structures
import app.pipelines.silver.accueillants
import app.pipelines.silver.geo
import app.pipelines.silver.gares
import app.pipelines.silver.lignes
import app.pipelines.silver.logement
import app.pipelines.silver.zones_attraction
import app.pipelines.silver.siae_structures
import app.pipelines.silver.siae_postes

# Create FastAPI app
app = FastAPI(
    title="Odace Data Pipeline API",
    description="Platform-agnostic data pipeline for bronze/silver/gold layers",
    version="1.0.0"
)

# Add rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(bronze.router)
app.include_router(silver.router)
app.include_router(gold.router)
app.include_router(pipeline.router)
app.include_router(files.router)
app.include_router(data.router)
app.include_router(jobs.router)
app.include_router(admin.router)
app.include_router(docs.router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main UI."""
    try:
        with open("app/static/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Odace Data Pipeline API</h1><p>Visit <a href='/docs'>/docs</a> for API documentation</p>"
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    settings = get_settings()
    logger.info(f"Starting Odace Data Pipeline API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"GCS Bucket: {settings.gcs_bucket}")
    logger.info(f"Project: {settings.gcp_project_id}")
    
    # Log registered pipelines
    from app.core.pipeline_registry import get_registry
    from app.core.models import PipelineLayer
    registry = get_registry()
    
    bronze_pipelines = registry.list_pipelines(layer=PipelineLayer.BRONZE)
    silver_pipelines = registry.list_pipelines(layer=PipelineLayer.SILVER)
    
    logger.info(f"Registered {len(bronze_pipelines)} bronze pipelines")
    logger.info(f"Registered {len(silver_pipelines)} silver pipelines")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Shutting down Odace Data Pipeline API")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

