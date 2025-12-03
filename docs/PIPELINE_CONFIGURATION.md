# Pipeline Configuration Guide

## Overview

The Odace pipeline system uses YAML configuration files for automatic pipeline discovery and management. This makes it easy to add new data sources or modify the data lakehouse modeling without changing application code.

## Configuration Files

Pipeline configurations are stored in `config/pipelines/`:

- **`bronze.yaml`** - Raw data ingestion pipelines
- **`silver.yaml`** - Cleaned dimension and fact tables  
- **`gold.yaml`** - Business aggregations and metrics

## Architecture

### Automatic Discovery

At application startup, the system:
1. Reads YAML configuration files
2. Validates pipeline dependencies
3. Dynamically imports pipeline classes
4. Registers pipelines in the global registry
5. Makes them available via REST API

No manual imports needed in `main.py`!

### Naming Convention

**Important**: Pipeline names MUST match table names. There is no separate mapping.

- Bronze pipelines: Use source names (e.g., `geo`, `accueillants`, `logement`)
- Silver pipelines: Use `dim_*` or `fact_*` (e.g., `dim_commune`, `fact_logement`)
- Gold pipelines: Business-specific names

## Configuration Format

### Bronze Layer

```yaml
pipelines:
  - name: "geo"                    # Pipeline name (also table name)
    target_table: "geo"            # Target Delta table
    source_path: "raw/geo"         # GCS path to source files
    pipeline_class: "app.pipelines.bronze.geo.BronzeGeoPipeline"
    description: "Raw geographic data"
```

**Fields:**
- `name`: Unique pipeline identifier (must match table name)
- `target_table`: Name of the Delta table to create
- `source_path`: GCS path or API endpoint (supports `raw/*`, `api://open_data/*`, `api://siae/*`)
- `pipeline_class`: Full Python import path to pipeline class
- `description`: Brief English description

### Silver Layer

```yaml
pipelines:
  - name: "dim_commune"            # Pipeline name (dim_* or fact_*)
    target_table: "dim_commune"    # Target Delta table
    dependencies:                  # Prerequisites (layer.name format)
      - "bronze.geo"
    pipeline_class: "app.pipelines.silver.dim_commune.DimCommunePipeline"
    description_fr: "Table de dimension des communes françaises avec codes INSEE, départements et régions."
```

**Fields:**
- `name`: Pipeline identifier following `dim_*` or `fact_*` convention
- `target_table`: Name of the Delta table (should match name)
- `dependencies`: List of required pipelines in `layer.name` format
- `pipeline_class`: Full Python import path
- `description_fr`: Detailed French description (displayed in API catalog)

### Gold Layer

```yaml
pipelines: []
# Future business metrics and aggregations
```

## Adding a New Data Source

### Step 1: Create Bronze Pipeline

Create `app/pipelines/bronze/my_source.py`:

```python
"""Bronze pipeline for my data source."""
import pandas as pd
from app.pipelines.base import BaseBronzePipeline

class BronzeMySourcePipeline(BaseBronzePipeline):
    """Ingests my source data into bronze layer."""
    
    def get_name(self) -> str:
        return "my_source"
    
    def get_source_path(self) -> str:
        return self.settings.get_raw_path("my_source")
    
    def get_target_table(self) -> str:
        return "my_source"
    
    def read_source_file(self, file_path: str) -> pd.DataFrame:
        """Read CSV/JSON/etc from GCS."""
        file_content = self.gcs.download_file(file_path)
        df = pd.read_csv(pd.io.common.BytesIO(file_content))
        return df
```

### Step 2: Add to bronze.yaml

```yaml
  - name: "my_source"
    target_table: "my_source"
    source_path: "raw/my_source"
    pipeline_class: "app.pipelines.bronze.my_source.BronzeMySourcePipeline"
    description: "My new data source"
```

### Step 3: Create Silver Pipeline

Create `app/pipelines/silver/dim_my_entity.py`:

```python
"""Silver pipeline for dim_my_entity."""
from app.pipelines.silver.base_v2 import SQLSilverV2Pipeline

class DimMyEntityPipeline(SQLSilverV2Pipeline):
    """Transform my_source into dim_my_entity dimension table."""
    
    def get_name(self) -> str:
        return "dim_my_entity"
    
    def get_target_table(self) -> str:
        return "dim_my_entity"
    
    def get_sql_query(self) -> str:
        """SQL transformation using DuckDB."""
        return """
            SELECT 
                MD5(id) as my_entity_sk,
                id as entity_id,
                name as entity_name,
                CASE 
                    WHEN status = 'active' THEN TRUE
                    ELSE FALSE
                END as is_active,
                'dim_my_entity' AS job_insert_id,
                CURRENT_TIMESTAMP AS job_insert_date_utc,
                'dim_my_entity' AS job_modify_id,
                CURRENT_TIMESTAMP AS job_modify_date_utc
            FROM bronze_my_source
            WHERE id IS NOT NULL
        """
```

### Step 4: Add to silver.yaml

```yaml
  - name: "dim_my_entity"
    target_table: "dim_my_entity"
    dependencies: ["bronze.my_source"]
    pipeline_class: "app.pipelines.silver.dim_my_entity.DimMyEntityPipeline"
    description_fr: "Table de dimension de mon entité avec identifiants et statuts."
```

### Step 5: Deploy

No code changes to `main.py` needed! Just:

```bash
# Deploy the updated configuration
./deploy.sh
```

The pipeline will be automatically discovered and available via:
- `GET /api/pipeline/list?layer=bronze`
- `POST /api/bronze/my_source`
- `POST /api/silver/dim_my_entity`

## Silver Layer Requirements

All silver pipelines must include:

### Surrogate Keys
- Format: `{entity}_sk` (e.g., `commune_sk`, `logement_sk`)
- Generated using `MD5()` of business key(s)
- Used for all joins

### Metadata Columns
Every silver table must have:
```sql
'pipeline_name' AS job_insert_id,
CURRENT_TIMESTAMP AS job_insert_date_utc,
'pipeline_name' AS job_modify_id,
CURRENT_TIMESTAMP AS job_modify_date_utc
```

### Naming Conventions
- **Dimensions**: `dim_*` (e.g., `dim_commune`, `dim_gare`)
  - Master data, slowly changing
  - Referenced by facts via foreign keys
  
- **Facts**: `fact_*` (e.g., `fact_logement`, `fact_siae_poste`)
  - Transactional/measurement data
  - Contains foreign keys to dimensions

## SQL Transformations

Silver pipelines use DuckDB for SQL-based transformations:

### Table References
In your SQL queries, reference tables as:
- Bronze: `bronze_table_name`
- Silver: `silver_table_name`

Example:
```sql
SELECT 
    MD5(b.id) as entity_sk,
    d.commune_sk,  -- Foreign key to dimension
    b.value
FROM bronze_my_source b
JOIN silver_dim_commune d ON b.insee_code = d.commune_code
```

### Available SQL Functions
DuckDB supports:
- Standard SQL: `SELECT`, `JOIN`, `WHERE`, `GROUP BY`, etc.
- Window functions: `ROW_NUMBER()`, `RANK()`, etc.
- String functions: `UPPER()`, `TRIM()`, `REGEXP_REPLACE()`, etc.
- Date functions: `CURRENT_TIMESTAMP`, date arithmetic
- Aggregations: `COUNT()`, `SUM()`, `AVG()`, etc.

## Validation

The configuration loader validates:
1. **YAML syntax** - Files must parse correctly
2. **Required fields** - All mandatory fields present
3. **Dependencies** - Referenced pipelines exist
4. **Class imports** - Pipeline classes can be imported

Validation errors are logged at startup and prevent registration.

## Best Practices

### 1. Consistent Naming
- Use lowercase with underscores
- Follow `dim_*` / `fact_*` convention for silver
- Keep names descriptive but concise

### 2. Clear Dependencies
- List all prerequisite pipelines
- Use format: `"layer.pipeline_name"`
- Ensure dependency graph has no cycles

### 3. Descriptive Documentation
- Bronze: Brief English description of source
- Silver: Detailed French description explaining business purpose
- Include key fields and relationships

### 4. SQL Best Practices
- Deduplicate using `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)`
- Filter invalid/null records early
- Use explicit column names (avoid `SELECT *`)
- Comment complex logic

### 5. Metadata Standards
- Always include the 4 required metadata columns
- Use pipeline name as job_insert_id/job_modify_id
- Use `CURRENT_TIMESTAMP` for dates

## Troubleshooting

### Pipeline Not Appearing
1. Check YAML syntax is valid
2. Verify pipeline_class import path is correct
3. Look for errors in application logs at startup
4. Ensure dependencies are defined correctly

### Import Errors
```
Error importing pipeline class app.pipelines.bronze.my_source.MyPipeline
```
- Check the file exists at correct path
- Verify class name matches exactly
- Ensure no syntax errors in pipeline file

### Dependency Errors
```
Pipeline silver.my_pipeline depends on bronze.missing, but bronze.missing is not found
```
- Check dependency is registered in YAML
- Verify layer.name format
- Ensure dependency pipeline loads first

### SQL Errors
- Check table references use correct prefix (`bronze_*`, `silver_*`)
- Verify source tables exist before running pipeline
- Review DuckDB error messages for syntax issues

## Migration from Old System

The old system used:
- Manual imports in `main.py`
- Decorator-based registration (`@register_pipeline`)
- Hardcoded table name mappings

The new YAML system:
- ✅ No manual imports needed
- ✅ Configuration-driven
- ✅ Direct name mapping (pipeline = table)
- ✅ Easy to add new sources
- ✅ Clear dependency management

Old pipelines are automatically compatible if:
1. Pipeline class has correct methods
2. Added to appropriate YAML file
3. Name follows conventions

## Examples

See existing configurations:
- [`config/pipelines/bronze.yaml`](../config/pipelines/bronze.yaml) - 8 bronze pipelines
- [`config/pipelines/silver.yaml`](../config/pipelines/silver.yaml) - 8 silver pipelines (5 dims, 3 facts)
- Pipeline implementations in [`app/pipelines/`](../app/pipelines/)

## Summary

The YAML configuration system provides:
- **Simplicity**: Add pipelines by editing YAML
- **Clarity**: Configuration is documentation
- **Maintainability**: No scattered imports
- **Flexibility**: Easy to reorganize or add sources
- **Validation**: Catch errors early at startup

For questions or issues, check application logs or refer to existing pipeline examples.

