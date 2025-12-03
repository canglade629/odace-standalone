# Open Data API Integration - Implementation Summary

## Overview
Successfully implemented integration with data.gouv.fr tabular API as a new data source for the ODACE backend.

## Files Created

### 1. datasources/open_data_sources.yaml
Configuration file containing the list of Open Data resources to ingest:
- **Rental Data:** 2 resources for apartment rental prices (2023 and 2018) - ~35,000 communes each
- **Transport Data:** 2 SNCF resources for railway stations (~3,884) and lines (~1,069)
- All resources include resource_id, name, description, and data_type fields

### 2. app/pipelines/bronze/open_data.py
Generic bronze pipeline for Open Data API ingestion with the following features:
- Extends `BaseAPIBronzePipeline`
- Configurable via YAML for multiple resources
- Rate limiting: 100 requests per second (as per API documentation)
- Handles pagination following data.gouv.fr API structure
- Full refresh mode (overwrite) for data consistency
- Class method `run_all_resources()` to process all configured resources

## Files Modified

### 1. app/core/config.py
Added configuration settings for Open Data API:
- `open_data_api_base_url`: https://tabular-api.data.gouv.fr/api
- `open_data_api_rate_limit`: 100 requests per second
- `open_data_sources_config`: Path to YAML config file
- `load_open_data_sources()`: Method to load resource configurations from YAML

### 2. app/pipelines/bronze/__init__.py
Added import for `BronzeOpenDataPipeline` to register it with the pipeline registry

### 3. requirements.txt
Added PyYAML==6.0.1 for YAML configuration parsing

## Technical Implementation Details

### API Integration
- Base URL: `https://tabular-api.data.gouv.fr/api`
- Endpoint pattern: `/resources/{resource_id}/data/`
- Response structure:
  ```json
  {
    "data": [...],
    "links": {"next": "...", "prev": "..."},
    "meta": {"page": 1, "page_size": 20, "total": N}
  }
  ```

### Rate Limiting
- Configured for 100 requests per second (vs 12/minute for SIAE API)
- Uses 1-second time window instead of 60-second window
- Respects API limits documented at data.gouv.fr

### Data Processing
- Page size: 100 records per request (optimized from default 20)
- Write mode: Overwrite (full refresh) for data consistency
- Automatic handling of quoted column names
- Preserves __id field from API response
- **Raw data persistence**: All API responses are saved to GCS raw layer with timestamp

### Target Tables
- Naming convention: `open_data_{resource_name}`
- Examples: 
  - `open_data_loyers_appartements_2023` (rental prices 2023)
  - `open_data_loyers_appartements_2018` (rental prices 2018)
  - `open_data_sncf_gares` (SNCF railway stations)
  - `open_data_sncf_lignes` (SNCF railway lines)
- Location: bronze layer in Delta Lake format

### Raw Data Layer
All API responses are automatically persisted to the raw layer:
- **Location:** `gs://jaccueille/raw/api/{table_name}/`
- **Format:** JSON files with timestamped names
- **Naming:** `{table_name}_{YYYYMMDD_HHMMSS}.json`
- **Purpose:** Historical record of all API fetches for audit and reprocessing
- **Example:** `gs://jaccueille/raw/api/gares/gares_20251202_153045.json`

## Usage

### Running a specific resource:
```python
from app.pipelines.bronze.open_data import BronzeOpenDataPipeline

pipeline = BronzeOpenDataPipeline(resource_id="43618998-3b37-4a69-bb25-f321f1a93ed1")
result = pipeline.run(force=True)
```

### Running all configured resources:
```python
from app.pipelines.bronze.open_data import BronzeOpenDataPipeline

results = BronzeOpenDataPipeline.run_all_resources(force=True)
```

### Via pipeline registry:
```python
from app.core.pipeline_registry import get_pipeline

pipeline = get_pipeline("bronze", "open_data")
result = pipeline.run()
```

## Adding New Resources

To add additional Open Data resources, simply update `datasources/open_data_sources.yaml`:

```yaml
resources:
  # Rental price data
  - resource_id: "43618998-3b37-4a69-bb25-f321f1a93ed1"
    name: "loyers_appartements_2023"
    description: "Carte des loyers - indicateurs de loyers d'annonce pour appartements par commune en 2023"
    data_type: "csv"
  
  - resource_id: "8fac6fb7-cd07-4747-8e0b-b101c476f0da"
    name: "loyers_appartements_2018"
    description: "Carte des loyers - indicateurs de loyers d'annonce pour appartements par commune en 2018"
    data_type: "csv"
  
  # SNCF transport data
  - resource_id: "d22ba593-90a4-4725-977c-095d1f654d28"
    name: "sncf_gares"
    description: "SNCF - Liste des gares ferroviaires françaises"
    data_type: "csv"
  
  - resource_id: "2f204d3f-4274-42fb-934f-4a73954e0c4e"
    name: "sncf_lignes"
    description: "SNCF - Lignes ferroviaires (LGV et par écartement)"
    data_type: "csv"
  
  # Add new resources here
  - resource_id: "new-resource-id-here"
    name: "resource_name"
    description: "Resource description"
    data_type: "csv"  # or xlsx, xls, etc.
```

### Supported Data Types
The data.gouv.fr API supports the following file formats:
- `csv` (up to 100 MB)
- `csv.gz` (up to 100 MB)
- `xlsx` (up to 12.5 MB)
- `xls` (up to 50 MB)

The `data_type` field helps document the original file format, though all data is served via the API in JSON format.

## Resource Details

**Resource 1: Apartment Rental Price Indicators 2023 (Loyers Appartements)**
- **ID:** 43618998-3b37-4a69-bb25-f321f1a93ed1
- **Records:** ~35,000 communes
- **Data Type:** CSV
- **Target Table:** `open_data_loyers_appartements_2023`
- **Key fields:**
  - INSEE_C: INSEE commune code
  - LIBGEO: Commune name
  - DEP: Department code
  - REG: Region code
  - loypredm2: Predicted rent per m² for apartments
  - lwr.IPm2, upr.IPm2: Confidence intervals

**Resource 2: Apartment Rental Price Indicators 2018 (Loyers Appartements)**
- **ID:** 8fac6fb7-cd07-4747-8e0b-b101c476f0da
- **Records:** ~35,441 communes
- **Data Type:** CSV
- **Target Table:** `open_data_loyers_appartements_2018`
- **Key fields:**
  - INSEE: INSEE commune code
  - LIBGEO: Commune name
  - DEP: Department code
  - REG: Region code
  - loypredm2: Predicted rent per m² for apartments
  - lwr.IPm2, upr.IPm2: Confidence intervals
  - NBobs_maille, NBobs_commune: Number of observations

**Resource 3: SNCF Railway Stations (Gares)**
- **ID:** d22ba593-90a4-4725-977c-095d1f654d28
- **Records:** ~3,884 stations
- **Data Type:** CSV
- **Target Table:** `open_data_sncf_gares`
- **Key fields:**
  - CODE_UIC: UIC station code
  - LIBELLE: Station name
  - FRET: Freight indicator (boolean)
  - VOYAGEURS: Passenger indicator (boolean)
  - CODE_LIGNE: Line code
  - COMMUNE: Municipality name
  - DEPARTEMEN: Department name
  - X_L93, Y_L93: Lambert 93 coordinates
  - X_WGS84, Y_WGS84: WGS84 coordinates

**Resource 4: SNCF Railway Lines (Lignes)**
- **ID:** 2f204d3f-4274-42fb-934f-4a73954e0c4e
- **Records:** ~1,069 lines
- **Data Type:** CSV
- **Target Table:** `open_data_sncf_lignes`
- **Key fields:**
  - CODE_LIGNE: Line code
  - LIB_LIGNE: Line name
  - CATLIG: Line category (conventional network, LGV, etc.)
  - RG_TRONCON: Section number
  - PKD, PKF: Start and end kilometric points
  - X_D_L93, Y_D_L93: Start coordinates (Lambert 93)
  - X_F_L93, Y_F_L93: End coordinates (Lambert 93)
  - X_D_WGS84, Y_D_WGS84: Start coordinates (WGS84)
  - X_F_WGS84, Y_F_WGS84: End coordinates (WGS84)

## Benefits

1. **Scalability:** Easy to add new Open Data resources via YAML
2. **Maintainability:** Generic pipeline handles all resources
3. **Reliability:** Rate limiting and retry logic built-in
4. **Consistency:** Full refresh mode ensures data accuracy
5. **Observability:** Comprehensive logging throughout

## Next Steps

1. Deploy to Cloud Run (Terraform already configured)
2. Test the pipeline with actual GCS bucket and Delta Lake
3. Add API routes to trigger Open Data pipeline jobs
4. Monitor pipeline execution and performance
5. Add more data.gouv.fr resources as needed

