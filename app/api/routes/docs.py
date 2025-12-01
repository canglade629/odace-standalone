"""Documentation endpoints."""
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from app.core.auth import verify_api_key
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
        doc_path = "DATA_MODEL.md"
        
        # Try to read from workspace root
        if os.path.exists(doc_path):
            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()
                return PlainTextResponse(content=content)
        else:
            logger.error(f"DATA_MODEL.md not found at {doc_path}")
            return PlainTextResponse(
                content="# Documentation Not Found\n\nThe DATA_MODEL.md file could not be loaded.",
                status_code=404
            )
    except Exception as e:
        logger.error(f"Error reading DATA_MODEL.md: {e}")
        return PlainTextResponse(
            content=f"# Error Loading Documentation\n\n{str(e)}",
            status_code=500
        )

