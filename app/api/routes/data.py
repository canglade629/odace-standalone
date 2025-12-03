"""Data catalog API routes."""
import logging
import time
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.core.auth import verify_api_key
from app.core.config import get_settings
from app.utils.delta_ops import DeltaOperations
from app.utils.sql_executor import SQLExecutor
from app.core.rate_limiter import limiter
from app.core.pipeline_registry import get_registry
from app.core.models import PipelineLayer
from fastapi import Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data", tags=["data"])


class TableInfo(BaseModel):
    """Table information."""
    name: str
    path: str
    version: int


class SchemaField(BaseModel):
    """Schema field information."""
    name: str
    type: str
    nullable: bool


class TableSchema(BaseModel):
    """Table schema information."""
    fields: List[SchemaField]
    version: int
    row_count: Optional[int]
    num_fields: int


class PreviewFilter(BaseModel):
    """Filter specification for table preview."""
    column: str
    operator: str = "="  # =, !=, contains, >, <, >=, <=
    value: str


class PreviewRequest(BaseModel):
    """Request for table preview."""
    limit: int = 100
    filters: Optional[List[PreviewFilter]] = None
    sort_by: Optional[str] = None
    sort_order: str = "asc"  # asc or desc


class PreviewResponse(BaseModel):
    """Table preview response."""
    columns: List[str]
    data: List[Dict[str, Any]]
    total_rows: int
    filtered_rows: int
    preview_rows: int


class CatalogResponse(BaseModel):
    """Catalog response with all schemas and tables."""
    schemas: Dict[str, List[TableInfo]]


class QueryRequest(BaseModel):
    """Request for SQL query execution."""
    sql: str
    limit: int = 1000


class QueryResponse(BaseModel):
    """SQL query execution response."""
    columns: List[str]
    data: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float


class SilverTableInfo(BaseModel):
    """Silver table information with French description."""
    name: str
    description_fr: str
    dependencies: List[str]
    version: int
    row_count: Optional[int]


class SilverCatalogResponse(BaseModel):
    """Catalog response for silver tables only."""
    tables: List[SilverTableInfo]


class SilverTableDetail(BaseModel):
    """Detailed information about a silver table."""
    name: str
    description_fr: str
    dependencies: List[str]
    schema: TableSchema
    preview: List[Dict[str, Any]]


@router.get("/catalog", response_model=CatalogResponse)
@limiter.limit("30/minute")
async def get_catalog(request: Request, api_key: str = Depends(verify_api_key)):
    """
    Get the complete data catalog with all schemas and tables.
    
    Scans GCS for Delta tables in bronze, silver, silver_v2, and gold layers.
    """
    logger.info("Fetching data catalog")
    settings = get_settings()
    
    try:
        schemas = {}
        
        # Scan each layer (including silver_v2)
        for layer in ["bronze", "silver", "silver_v2", "gold"]:
            layer_path = f"{settings.delta_path}/{layer}"
            try:
                tables = DeltaOperations.list_delta_tables(layer_path)
                schemas[layer] = [
                    TableInfo(
                        name=table["name"],
                        path=table["path"],
                        version=table["version"]
                    )
                    for table in tables
                ]
            except Exception as e:
                logger.warning(f"Could not list tables in {layer}: {e}")
                schemas[layer] = []
        
        return CatalogResponse(schemas=schemas)
    
    except Exception as e:
        logger.error(f"Error fetching catalog: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch catalog: {str(e)}")


@router.get("/catalog/silver", response_model=SilverCatalogResponse)
@limiter.limit("30/minute")
async def get_silver_catalog(request: Request, api_key: str = Depends(verify_api_key)):
    """
    Get catalog of silver tables with French descriptions.
    
    Returns all silver layer tables with their French descriptions, dependencies,
    and basic metadata.
    """
    logger.info("Fetching silver catalog with French descriptions")
    settings = get_settings()
    registry = get_registry()
    
    try:
        # Get all silver pipelines from registry
        silver_pipelines = registry.list_pipelines(layer=PipelineLayer.SILVER)
        
        # Get Delta table information
        layer_path = f"{settings.delta_path}/silver"
        delta_tables = {t["name"]: t for t in DeltaOperations.list_delta_tables(layer_path)}
        
        tables = []
        for pipeline in silver_pipelines:
            table_name = pipeline.name
            delta_info = delta_tables.get(table_name, {})
            
            # Get row count if available
            row_count = None
            try:
                table_path = f"{layer_path}/{table_name}"
                schema_info = DeltaOperations.get_table_schema(table_path)
                row_count = schema_info.get("row_count")
            except Exception as e:
                logger.warning(f"Could not get row count for {table_name}: {e}")
            
            tables.append(SilverTableInfo(
                name=table_name,
                description_fr=pipeline.description_fr or "Description non disponible",
                dependencies=pipeline.dependencies,
                version=delta_info.get("version", 0),
                row_count=row_count
            ))
        
        return SilverCatalogResponse(tables=tables)
    
    except Exception as e:
        logger.error(f"Error fetching silver catalog: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch silver catalog: {str(e)}")


@router.get("/catalog/silver/{table_name}", response_model=SilverTableDetail)
@limiter.limit("30/minute")
async def get_silver_table_detail(
    request: Request,
    table_name: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get detailed information about a specific silver table.
    
    Returns table metadata, schema, French description, dependencies,
    and first 10 rows of data.
    
    Args:
        table_name: Name of the silver table
    """
    logger.info(f"Fetching details for silver.{table_name}")
    settings = get_settings()
    registry = get_registry()
    
    try:
        # Get pipeline info from registry
        silver_pipelines = registry.list_pipelines(layer=PipelineLayer.SILVER)
        pipeline_info = next((p for p in silver_pipelines if p.name == table_name), None)
        
        if not pipeline_info:
            raise HTTPException(status_code=404, detail=f"Table {table_name} not found in registry")
        
        # Get table schema
        table_path = f"{settings.delta_path}/silver/{table_name}"
        schema_info = DeltaOperations.get_table_schema(table_path)
        
        table_schema = TableSchema(
            fields=[
                SchemaField(
                    name=field["name"],
                    type=field["type"],
                    nullable=field["nullable"]
                )
                for field in schema_info["fields"]
            ],
            version=schema_info["version"],
            row_count=schema_info["row_count"],
            num_fields=schema_info["num_fields"]
        )
        
        # Get first 10 rows
        preview_data = DeltaOperations.preview_table(
            table_path=table_path,
            limit=10,
            filters=None,
            sort_by=None,
            sort_order="asc"
        )
        
        return SilverTableDetail(
            name=table_name,
            description_fr=pipeline_info.description_fr or "Description non disponible",
            dependencies=pipeline_info.dependencies,
            schema=table_schema,
            preview=preview_data["data"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching table detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch table detail: {str(e)}")


@router.get("/table/{layer}/{table}", response_model=TableSchema)
@limiter.limit("60/minute")
async def get_table_metadata(
    request: Request,
    layer: str,
    table: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get metadata for a specific table including schema and row count.
    
    Args:
        layer: Layer name (bronze, silver, silver_v2, gold)
        table: Table name
    """
    logger.info(f"Fetching metadata for {layer}.{table}")
    settings = get_settings()
    
    # Validate layer (including silver_v2)
    if layer not in ["bronze", "silver", "silver_v2", "gold"]:
        raise HTTPException(status_code=400, detail="Layer must be bronze, silver, silver_v2, or gold")
    
    # Construct table path
    table_path = f"{settings.delta_path}/{layer}/{table}"
    
    try:
        schema_info = DeltaOperations.get_table_schema(table_path)
        
        return TableSchema(
            fields=[
                SchemaField(
                    name=field["name"],
                    type=field["type"],
                    nullable=field["nullable"]
                )
                for field in schema_info["fields"]
            ],
            version=schema_info["version"],
            row_count=schema_info["row_count"],
            num_fields=schema_info["num_fields"]
        )
    
    except Exception as e:
        logger.error(f"Error fetching table metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch table metadata: {str(e)}")


@router.post("/preview/{layer}/{table}", response_model=PreviewResponse)
@limiter.limit("60/minute")
async def preview_table(
    request: Request,
    layer: str,
    table: str,
    preview_req: PreviewRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Get a preview of table data with optional filtering and sorting.
    
    Args:
        layer: Layer name (bronze, silver, silver_v2, gold)
        table: Table name
        preview_req: Preview request with filters and sort options
    """
    logger.info(f"Previewing {layer}.{table} with filters={preview_req.filters}, sort={preview_req.sort_by}")
    settings = get_settings()
    
    # Validate layer (including silver_v2)
    if layer not in ["bronze", "silver", "silver_v2", "gold"]:
        raise HTTPException(status_code=400, detail="Layer must be bronze, silver, silver_v2, or gold")
    
    # Construct table path
    table_path = f"{settings.delta_path}/{layer}/{table}"
    
    try:
        # Convert Pydantic models to dicts
        filters_dict = None
        if preview_req.filters:
            filters_dict = [f.dict() for f in preview_req.filters]
        
        preview_data = DeltaOperations.preview_table(
            table_path=table_path,
            limit=preview_req.limit,
            filters=filters_dict,
            sort_by=preview_req.sort_by,
            sort_order=preview_req.sort_order
        )
        
        return PreviewResponse(
            columns=preview_data["columns"],
            data=preview_data["data"],
            total_rows=preview_data["total_rows"],
            filtered_rows=preview_data["filtered_rows"],
            preview_rows=preview_data["preview_rows"]
        )
    
    except Exception as e:
        logger.error(f"Error previewing table: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to preview table: {str(e)}")


@router.post("/query", response_model=QueryResponse)
@limiter.limit("60/minute")
async def execute_sql_query(
    request: Request,
    query_req: QueryRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Execute a SQL query against Delta tables.
    
    Tables should be referenced as layer_table_name (e.g., bronze_accueillants, silver_geo).
    All available Delta tables are automatically registered.
    
    Args:
        query_req: SQL query request with query string and optional limit
    """
    logger.info(f"Executing SQL query (limit={query_req.limit})")
    logger.debug(f"SQL: {query_req.sql}")
    
    settings = get_settings()
    sql_executor = SQLExecutor()
    
    try:
        start_time = time.time()
        
        # Register all Delta tables from all layers (including silver_v2)
        registered_tables = []
        registration_errors = []
        
        for layer in ["bronze", "silver", "silver_v2", "gold"]:
            layer_path = f"{settings.delta_path}/{layer}"
            try:
                tables = DeltaOperations.list_delta_tables(layer_path)
                logger.info(f"Found {len(tables)} tables in {layer}")
                for table in tables:
                    # Use underscore instead of dot for SQL compatibility
                    table_name = f"{layer}_{table['name']}"
                    table_path = table['path']
                    try:
                        sql_executor.register_delta_table(table_name, table_path)
                        registered_tables.append(table_name)
                        logger.info(f"Successfully registered table {table_name}")
                    except Exception as e:
                        error_msg = f"Failed to register {table_name}: {str(e)}"
                        logger.error(error_msg)
                        registration_errors.append(error_msg)
            except Exception as e:
                error_msg = f"Failed to list tables in {layer}: {str(e)}"
                logger.error(error_msg)
                registration_errors.append(error_msg)
        
        logger.info(f"Registered {len(registered_tables)} tables: {registered_tables}")
        
        if not registered_tables:
            error_details = "; ".join(registration_errors) if registration_errors else "No tables found"
            raise HTTPException(
                status_code=500, 
                detail=f"No tables could be registered. {error_details}"
            )
        
        # Execute the query
        result_df = sql_executor.execute_query(query_req.sql)
        
        # Apply limit
        limited_df = result_df.head(query_req.limit)
        
        # Convert to response format
        columns = limited_df.columns.tolist()
        data = limited_df.to_dict('records')
        
        # Convert any NaN or None to null properly
        for row in data:
            for key, value in row.items():
                if value is None or (isinstance(value, float) and str(value) == 'nan'):
                    row[key] = None
        
        execution_time = (time.time() - start_time) * 1000  # ms
        
        logger.info(f"Query executed successfully, returned {len(data)} rows in {execution_time:.2f}ms")
        
        return QueryResponse(
            columns=columns,
            data=data,
            row_count=len(result_df),
            execution_time_ms=round(execution_time, 2)
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error executing SQL query: {e}", exc_info=True)
        error_msg = str(e)
        # Make error messages more user-friendly
        if "Catalog Error" in error_msg or "not found" in error_msg.lower():
            available_tables = ", ".join(registered_tables) if registered_tables else "none"
            raise HTTPException(
                status_code=400, 
                detail=f"Table not found. Available tables: {available_tables}. Use format: layer_table_name (e.g., bronze_accueillants, silver_geo)"
            )
        elif "Parser Error" in error_msg or "syntax" in error_msg.lower():
            raise HTTPException(status_code=400, detail=f"SQL syntax error: {error_msg}")
        else:
            raise HTTPException(status_code=500, detail=f"Query execution failed: {error_msg}")
    finally:
        sql_executor.close()

