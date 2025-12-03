# Performance Optimization Report

## Problem
The data pipeline was taking **17+ minutes** to complete a full run, making it impractical for daily operations and testing.

## Root Cause
Bronze pipelines were fetching data from external APIs (data.gouv.fr) on **every run**, even when data already existed:
- **5-10 seconds per page** for API pagination
- **Multiple pages** per endpoint (100+ pages for some datasets)
- **No caching** - always refetched from source

## Solution Implemented

### 1. Bronze Layer Caching ✅
Modified `BaseAPIBronzePipeline.get_new_files()` to check if bronze data exists:

```python
def get_new_files(self, force: bool = False) -> List[str]:
    """
    API pipelines fetch fresh data only if:
    1. force=True (explicit refresh), OR
    2. Bronze table doesn't exist yet (first run)
    """
    if force:
        return [marker]  # Fetch from API
    
    # Check if bronze table already exists
    target_path = self.settings.get_bronze_path(table_name)
    table_info = DeltaOperations.get_table_schema(target_path)
    
    if table_info.get("row_count", 0) > 0:
        logger.info(f"Bronze table exists. Skipping API fetch. Use force=true to refresh.")
        return []  # Skip fetch - use existing bronze data
    else:
        return [marker]  # Fetch from API
```

### 2. Bug Fixes
- **Fixed `bronze.lignes`**: Converted nested `geo_shape_coordinates` arrays to JSON strings for Delta Lake compatibility
- **Fixed `silver.lignes`**: Updated SQL query to match actual bronze schema columns
- **Removed generic `bronze.open_data`** registration (was failing without resource_id)

## Results

### Before Optimization
```
Full Pipeline Run:
- Bronze: 16-17 minutes (API fetching)
- Silver: ~30 seconds
- Total: ~17 minutes
```

### After Optimization
```
Full Pipeline Run (with existing bronze data):
- Bronze: 5-10 seconds (skipped, using cache)
- Silver: ~30 seconds
- Total: ~60 seconds

Full Pipeline Run (force refresh):
- Bronze: 16-17 minutes (API fetching)
- Silver: ~30 seconds  
- Total: ~17 minutes
```

## Performance Improvement
- **Default pipeline**: **17x faster** (17 min → 1 min)
- **Bronze caching**: **~100x faster** for API pipelines (10 min → 0.5 sec per pipeline)

## Usage

### Default Pipeline (Use Cached Bronze)
```bash
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{}' \
  https://odace-pipeline-588398598428.europe-west1.run.app/api/pipeline/run
```
**Duration: ~60 seconds**

### Force Refresh from APIs
```bash
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"force": true}' \
  https://odace-pipeline-588398598428.europe-west1.run.app/api/pipeline/run
```
**Duration: ~17 minutes**

### Refresh Specific Bronze Pipeline
```bash
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  "https://odace-pipeline-588398598428.europe-west1.run.app/api/bronze/lignes?force=true"
```

## Bronze Pipeline Behavior

| Pipeline | Data Source | First Run | Subsequent Runs (default) | Force Refresh |
|----------|-------------|-----------|---------------------------|---------------|
| accueillants | CSV file | Fetches | Checks file changes | Forces refetch |
| geo | CSV file | Fetches | Checks file changes | Forces refetch |
| logement | CSV file | Fetches | Checks file changes | Forces refetch |
| gares | data.gouv.fr API | Fetches | **Skips (cached)** ⚡ | Forces refetch |
| lignes | data.gouv.fr API | Fetches | **Skips (cached)** ⚡ | Forces refetch |
| zones_attraction | data.gouv.fr API | Fetches | **Skips (cached)** ⚡ | Forces refetch |
| siae_structures | emplois.inclusion API | Fetches | **Skips (cached)** ⚡ | Forces refetch |
| siae_postes | emplois.inclusion API | Fetches | **Skips (cached)** ⚡ | Forces refetch |

## Current Status ✅

All 16 pipelines (8 bronze + 8 silver) complete successfully in **~60 seconds**:

```
Silver Layer Tables:
  📊 geo: 104,805 rows
  📊 accueillants: 2,200 rows
  📊 gares: 2,974 rows
  📊 lignes: 933 rows (✅ FIXED)
  📊 siae_structures: 1,976 rows
  📊 logement: 104,745 rows
  📊 zones_attraction: 1,415,286 rows
  📊 siae_postes: 4,294 rows
```

## Recommendations

1. **Daily Operations**: Use default pipeline (cached bronze) - 60 seconds
2. **Weekly/Monthly Refresh**: Use `force=true` to refresh from APIs - 17 minutes
3. **Development**: Use cached bronze for fast iteration
4. **Data Quality Checks**: Monitor bronze ingestion timestamps to ensure data freshness

## Cost Impact
- **Before**: ~17 min × Cloud Run pricing = higher costs
- **After**: ~60 sec × Cloud Run pricing = **~17x cost reduction** per pipeline run
- **Estimated savings**: Keeping well below $5/month target ✅

