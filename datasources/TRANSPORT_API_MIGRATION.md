# Transport Data Migration to Open Data API

## Overview
The transport pipelines (`BronzeGaresPipeline` and `BronzeLignesPipeline`) have been migrated from file-based ingestion to API-based ingestion using the data.gouv.fr Open Data API.

## Changes Made

### 1. Updated Transport Pipelines

**File:** `app/pipelines/bronze/transport.py`

Both pipelines have been updated to:
- Extend `BaseAPIBronzePipeline` instead of `BaseBronzePipeline`
- Fetch data from Open Data API instead of reading files from GCS
- Use resource IDs directly embedded in the pipeline classes

### Pipeline Details

#### BronzeGaresPipeline (Railway Stations)
- **Resource ID:** `d22ba593-90a4-4725-977c-095d1f654d28`
- **Source:** SNCF Open Data API via data.gouv.fr
- **Records:** ~3,884 railway stations
- **Target Table:** `delta/bronze/gares` (unchanged)
- **Key Fields:** CODE_UIC, LIBELLE, COMMUNE, DEPARTEMEN, coordinates

#### BronzeLignesPipeline (Railway Lines)
- **Resource ID:** `2f204d3f-4274-42fb-934f-4a73954e0c4e`
- **Source:** SNCF Open Data API via data.gouv.fr
- **Records:** ~1,069 railway lines
- **Target Table:** `delta/bronze/lignes` (unchanged)
- **Key Fields:** CODE_LIGNE, LIB_LIGNE, CATLIG, PKD, PKF, coordinates

## Key Improvements

### ✅ Advantages

1. **Always Up-to-Date**
   - Data is fetched directly from the source API
   - No need to manually upload files to GCS
   - Automatic updates when SNCF updates their data

2. **Consistent with Other Pipelines**
   - Uses the same `BaseAPIBronzePipeline` architecture
   - Follows the same patterns as other API-based ingestion (SIAE, Open Data)

3. **Better Rate Limiting**
   - Uses Open Data API rate limit: 100 requests/second
   - Significantly faster than file-based processing

4. **Simplified Workflow**
   - No manual file uploads required
   - Single source of truth (API)
   - Reduced maintenance overhead

5. **Backward Compatible**
   - Target tables remain the same (`gares` and `lignes`)
   - Column normalization logic preserved
   - Existing silver/gold pipelines work without changes

## Implementation Details

### Base Class Change
```python
# Before
from app.pipelines.base import BaseBronzePipeline
class BronzeGaresPipeline(BaseBronzePipeline):
    ...

# After
from app.pipelines.base_api import BaseAPIBronzePipeline
class BronzeGaresPipeline(BaseAPIBronzePipeline):
    ...
```

### Resource ID Configuration
Each pipeline now has a hardcoded resource ID:
```python
class BronzeGaresPipeline(BaseAPIBronzePipeline):
    RESOURCE_ID = "d22ba593-90a4-4725-977c-095d1f654d28"
```

### API Configuration
- **Base URL:** `https://tabular-api.data.gouv.fr/api`
- **Endpoint Pattern:** `/resources/{resource_id}/data/`
- **Page Size:** 100 records per request
- **Rate Limit:** 100 requests per second

### Data Transformation
All existing transformations are preserved:
- Column name normalization (lowercase, underscores)
- Type conversions (CODE_UIC, CODE_LIGNE to string)
- Ingestion timestamp addition

### Raw Data Persistence
**New Feature:** API responses are now automatically saved to the raw layer:
- **Location:** `gs://jaccueille/raw/api/{table_name}/`
- **Format:** JSON with timestamped filenames
- **Example:** `raw/api/gares/gares_20251202_153045.json`
- **Purpose:** Audit trail and ability to reprocess historical data
- **Benefit:** Complete data lineage from source to bronze layer

## Usage

### Running the Pipelines

**Same as before - no changes to the API:**

```python
from app.core.pipeline_registry import get_pipeline

# Run gares pipeline
gares_pipeline = get_pipeline("bronze", "gares")
result = gares_pipeline.run(force=True)

# Run lignes pipeline
lignes_pipeline = get_pipeline("bronze", "lignes")
result = lignes_pipeline.run(force=True)
```

### Via API Endpoints

If you have API routes configured:
```bash
# Trigger gares ingestion
POST /api/jobs/run
{
  "pipeline_type": "bronze",
  "pipeline_name": "gares",
  "force": true
}

# Trigger lignes ingestion
POST /api/jobs/run
{
  "pipeline_type": "bronze",
  "pipeline_name": "lignes",
  "force": true
}
```

## Migration Path

### What Changed
- ✅ Transport pipelines now use API instead of files
- ✅ Resource IDs embedded in pipeline code
- ✅ Rate limiting updated to Open Data API limits
- ✅ Documentation updated

### What Stayed the Same
- ✅ Pipeline names (`bronze_gares`, `bronze_lignes`)
- ✅ Target table names (`gares`, `lignes`)
- ✅ Column schemas and transformations
- ✅ Pipeline registry integration
- ✅ Downstream silver/gold pipelines

### What to Remove
- ❌ No longer need to upload SNCF files to `gs://jaccueille/raw/transport/gares/`
- ❌ No longer need to upload SNCF files to `gs://jaccueille/raw/transport/lignes/`
- ❌ Can clean up old files from GCS (optional, for cost savings)

## Testing

To verify the migration worked:

```python
# Test gares pipeline
from app.pipelines.bronze.transport import BronzeGaresPipeline
pipeline = BronzeGaresPipeline()
result = pipeline.run(force=True)

print(f"Status: {result['status']}")
print(f"Rows processed: {result['rows_processed']}")

# Expected: ~3,884 rows for gares
# Expected: ~1,069 rows for lignes
```

## Rollback Plan

If needed, you can rollback by:
1. Reverting `app/pipelines/bronze/transport.py` to the previous version
2. Re-uploading files to GCS raw paths
3. Running pipelines as before

However, this should not be necessary as the API-based approach is more reliable.

## Benefits Summary

| Aspect | File-Based (Old) | API-Based (New) |
|--------|------------------|-----------------|
| Data Source | Manual GCS upload | Automatic API fetch |
| Freshness | Manual update required | Always current |
| Maintenance | High (file management) | Low (automated) |
| Rate Limiting | N/A | 100 req/sec |
| Consistency | Manual process | Automated |
| Reliability | Depends on files | Direct from source |
| Architecture | Mixed (file + API) | Unified (all API) |

## Next Steps

1. ✅ Transport pipelines migrated to API
2. ✅ Documentation updated
3. 🔄 Test pipelines in production
4. 🔄 Monitor pipeline execution
5. 🔄 Clean up old files from GCS (optional)
6. 🔄 Update any deployment scripts if needed

