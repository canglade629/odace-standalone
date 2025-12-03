"""Documentation endpoints."""
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from app.core.auth import verify_api_key
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/docs", tags=["documentation"])


@router.get("/data-model", response_class=PlainTextResponse)
async def get_data_model_doc(api_key: str = Depends(verify_api_key)):
    """
    Get the DATA_MODEL.md documentation content.
    
    Returns the markdown content with diagrams for the data model.
    """
    try:
        # Calculate path relative to project root
        # In development: /path/to/project/app/api/routes/docs.py -> /path/to/project/DATA_MODEL.md
        # In Docker: /app/app/api/routes/docs.py -> /app/DATA_MODEL.md
        project_root = Path(__file__).parent.parent.parent.parent
        doc_path = project_root / "DATA_MODEL.md"
        
        logger.info(f"Looking for DATA_MODEL.md at: {doc_path}")
        logger.info(f"__file__ is: {__file__}")
        logger.info(f"Absolute doc_path: {doc_path.absolute()}")
        logger.info(f"File exists: {doc_path.exists()}")
        logger.info(f"Current working directory: {os.getcwd()}")
        
        # Try multiple potential locations
        potential_paths = [
            doc_path,  # Calculated path
            Path("/app/DATA_MODEL.md"),  # Docker absolute path
            Path(os.getcwd()) / "DATA_MODEL.md",  # CWD relative
        ]
        
        for path in potential_paths:
            logger.info(f"Trying path: {path} (exists: {path.exists()})")
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    logger.info(f"Successfully loaded DATA_MODEL.md from {path} ({len(content)} characters)")
                    return PlainTextResponse(content=content)
        
        # None of the paths worked
        error_msg = f"# Documentation Not Found\n\nTried paths:\n"
        for path in potential_paths:
            error_msg += f"- {path} (exists: {path.exists()})\n"
        
        logger.error(f"DATA_MODEL.md not found in any location")
        return PlainTextResponse(
            content=error_msg,
            status_code=404
        )
    except Exception as e:
        logger.error(f"Error reading DATA_MODEL.md: {e}", exc_info=True)
        return PlainTextResponse(
            content=f"# Error Loading Documentation\n\n{str(e)}",
            status_code=500
        )

