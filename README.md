# Odace Data Pipeline

A cloud-based data pipeline platform built with FastAPI and Delta Lake. The Odace Data Pipeline provides a REST API for managing data ingestion, transformation, and processing across bronze, silver, and gold data layers.

## What is Odace?

Odace is a data pipeline platform that:
- Ingests raw data files into structured Delta Lake tables (Bronze layer)
- Transforms and cleans data (Silver layer)
- Provides aggregated business metrics (Gold layer)
- Offers a REST API for pipeline orchestration
- Includes a web UI for monitoring and management

## For API Users

If you've received an API key, you can use the Odace API to trigger data pipelines, upload files, and monitor processing status.

### Prerequisites

- An API key (format: `sk_live_...`)
- HTTP client (curl, Postman, Python requests, etc.)
- API endpoint URL (provided by your administrator)

### Authentication

All API requests require your API key in the `Authorization` header using Bearer token format:

```bash
Authorization: Bearer sk_live_YOUR_API_KEY
```

### Quick Start

1. **Test your API key**:
   ```bash
   curl -H "Authorization: Bearer sk_live_YOUR_API_KEY" \
        https://your-service.run.app/api/pipeline/list
   ```

2. **View available pipelines**:
   ```bash
   curl -H "Authorization: Bearer sk_live_YOUR_API_KEY" \
        https://your-service.run.app/api/pipeline/list?layer=bronze
   ```

3. **Run a pipeline**:
   ```bash
   curl -X POST \
        -H "Authorization: Bearer sk_live_YOUR_API_KEY" \
        https://your-service.run.app/api/bronze/geo
   ```

## Core API Endpoints

### Pipeline Management

**List available pipelines**:
```bash
GET /api/pipeline/list?layer=bronze|silver|gold
```

**Run a bronze pipeline** (ingestion):
```bash
POST /api/bronze/{pipeline_name}?force=false
```

**Run a silver pipeline** (transformation):
```bash
POST /api/silver/{pipeline_name}?force=false
```

**Run full pipeline** (bronze + silver):
```bash
POST /api/pipeline/run
Content-Type: application/json

{
  "bronze_only": false,
  "silver_only": false,
  "force": false
}
```

### Running the Full Pipeline - Detailed Guide

The full pipeline endpoint (`/api/pipeline/run`) orchestrates the complete data processing workflow from raw data to cleaned, transformed tables.

#### Basic Full Pipeline Run

**Run the complete pipeline** (Bronze → Silver):
```bash
curl -X POST \
  -H "Authorization: Bearer sk_live_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"force": true}' \
  https://your-service.run.app/api/pipeline/run
```

**Expected Response**:
```json
{
  "job_id": "3c8f78d2-671a-4565-806a-b77e614f5868",
  "status": "success",
  "total_pipelines": 12,
  "succeeded": 12,
  "failed": 0,
  "pipelines": [
    {
      "run_id": "uuid",
      "pipeline_name": "geo",
      "layer": "bronze",
      "status": "success",
      "started_at": "2025-11-29T12:18:42.731198",
      "completed_at": "2025-11-29T12:18:49.615840",
      "duration_seconds": 6.88,
      "message": "Successfully processed 1 file(s), 34935 rows"
    },
    ...
  ]
}
```

#### Pipeline Run Options

**1. Full Pipeline (Recommended)**
Runs all bronze pipelines first, then all silver pipelines:
```bash
curl -X POST \
  -H "Authorization: Bearer sk_live_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "bronze_only": false,
    "silver_only": false,
    "force": true
  }' \
  https://your-service.run.app/api/pipeline/run
```
- **Executes**: 6 bronze + 6 silver = 12 total pipelines
- **Duration**: ~2-3 minutes
- **Use when**: Running a complete data refresh

**2. Bronze Layer Only**
Only ingests raw data into bronze tables:
```bash
curl -X POST \
  -H "Authorization: Bearer sk_live_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "bronze_only": true,
    "force": true
  }' \
  https://your-service.run.app/api/pipeline/run
```
- **Executes**: 6 bronze pipelines
- **Duration**: ~1-2 minutes
- **Use when**: Only new raw files need to be ingested

**3. Silver Layer Only**
Only transforms bronze data into silver tables:
```bash
curl -X POST \
  -H "Authorization: Bearer sk_live_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "silver_only": true,
    "force": true
  }' \
  https://your-service.run.app/api/pipeline/run
```
- **Executes**: 6 silver pipelines
- **Duration**: ~1 minute
- **Use when**: Bronze data exists and only transformations need updating

**4. Incremental Run**
Only processes new files (uses checkpoints):
```bash
curl -X POST \
  -H "Authorization: Bearer sk_live_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "force": false
  }' \
  https://your-service.run.app/api/pipeline/run
```
- **Executes**: Only pipelines with new data
- **Duration**: Varies (only processes changes)
- **Use when**: Running scheduled incremental updates

#### Understanding `force` Parameter

| `force` | Behavior | Checkpoints | Use Case |
|---------|----------|-------------|----------|
| `true` | Reprocess ALL files | Cleared | Complete refresh, ensure idempotency |
| `false` | Process NEW files only | Preserved | Incremental updates, daily runs |

**Idempotency**: With `force=true`, running the pipeline multiple times produces identical results (no data duplication).

#### Monitoring Pipeline Execution

**1. Check job status**:
```bash
curl -H "Authorization: Bearer sk_live_YOUR_API_KEY" \
  https://your-service.run.app/api/jobs/{job_id}
```

**2. List recent jobs**:
```bash
curl -H "Authorization: Bearer sk_live_YOUR_API_KEY" \
  https://your-service.run.app/api/jobs?limit=10
```

**3. View task details**:
```json
{
  "job_id": "uuid",
  "status": "success",
  "job_name": "Full Pipeline - Bronze → Silver",
  "total_tasks": 12,
  "completed_tasks": 12,
  "failed_tasks": 0,
  "started_at": "2025-11-29T12:18:42Z",
  "completed_at": "2025-11-29T12:21:03Z",
  "tasks": [
    {
      "task_id": "uuid",
      "pipeline_name": "geo",
      "layer": "bronze",
      "status": "success",
      "duration_seconds": 6.88,
      "message": "Successfully processed 1 file(s), 34935 rows"
    },
    ...
  ]
}
```

#### Expected Results

After a successful full pipeline run, you should have:

**Bronze Tables** (raw ingested data):
- `bronze.accueillants`: ~1,634 rows
- `bronze.geo`: ~34,935 rows
- `bronze.gares`: ~3,884 rows
- `bronze.lignes`: ~1,069 rows
- `bronze.logement`: ~279,760 rows
- `bronze.zones_attraction`: ~34,875 rows

**Silver Tables** (cleaned & transformed):
- `silver.accueillants`: ~1,634 rows
- `silver.geo`: ~34,935 rows
- `silver.gares`: ~2,974 rows (deduplicated)
- `silver.lignes`: ~933 rows (deduplicated)
- `silver.logement`: ~34,928 rows (deduplicated)
- `silver.zones_attraction`: ~28,377 rows

#### Error Handling

**If a pipeline fails**:
```json
{
  "job_id": "uuid",
  "status": "failed",
  "total_pipelines": 12,
  "succeeded": 5,
  "failed": 1,
  "pipelines": [
    ...
    {
      "pipeline_name": "logement",
      "layer": "bronze",
      "status": "failed",
      "error": "Error message here"
    }
  ]
}
```

**Recovery**: Simply re-run with `force=true` to retry:
```bash
curl -X POST \
  -H "Authorization: Bearer sk_live_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"force": true}' \
  https://your-service.run.app/api/pipeline/run
```

The pipeline is **idempotent**, so re-running will clear the error and produce correct results.

#### Best Practices

1. **Use `force=true` for manual runs** - Ensures clean, consistent results
2. **Use `force=false` for scheduled runs** - Efficient incremental processing
3. **Monitor job status** - Check `/api/jobs/{job_id}` for detailed progress
4. **Verify results** - Query data tables after pipeline completion
5. **Re-run on failures** - Safe to retry with `force=true`

**Check pipeline status**:
```bash
GET /api/pipeline/status/{run_id}
```

**View execution history**:
```bash
GET /api/pipeline/history
```

### File Upload

**Upload a file for processing**:
```bash
POST /api/files/upload?domain=logement
Content-Type: multipart/form-data
```

Example with curl:
```bash
curl -X POST \
     -H "Authorization: Bearer sk_live_YOUR_API_KEY" \
     -F "file=@myfile.csv" \
     "https://your-service.run.app/api/files/upload?domain=logement"
```

### API Documentation

Visit the interactive API documentation at:
```
https://your-service.run.app/docs
```

## Available Pipelines

### Bronze Layer (Data Ingestion)
- `accueillants` - Host locations
- `geo` - French commune geographic data
- `logement` - Housing prices and statistics
- `gares` - Train station data
- `lignes` - Train line data
- `zones_attraction` - Urban attraction zones

### Silver Layer (Data Transformation)
- `accueillants` - Cleaned host data
- `geo` - Normalized commune data
- `gares` - Deduplicated station data
- `lignes` - Deduplicated line data
- `logement` - Standardized housing data
- `zones_attraction` - Processed attraction zones

## Response Formats

### Success Response
```json
{
  "status": "success",
  "run_id": "uuid-here",
  "message": "Pipeline started successfully"
}
```

### Error Response
```json
{
  "detail": "Error message here"
}
```

## Rate Limits

- Standard users: Consult your API key documentation
- Contact your administrator for rate limit increases

## Support

For questions or issues:
- Check the [API Key Usage Guide](docs/API_KEY_USAGE.md)
- Review the interactive API docs at `/docs`
- Contact your data team administrator

## Additional Documentation

For developers and administrators:
- [API Key Management](docs/API_KEY_USAGE.md) - Complete guide to API key creation and management
- [Implementation Details](docs/IMPLEMENTATION_SUMMARY.md) - Technical architecture and design
- [Pipeline Fixes](docs/PIPELINE_FIXES_SUMMARY.md) - Pipeline development notes
- [Test Reports](docs/END_TO_END_TEST_REPORT.md) - Testing documentation

## Local Development

For developers setting up the project locally:

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd odace_backend
   cp env.template .env
   # Edit .env with your GCP credentials
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run locally**:
   ```bash
   ./scripts/run_local.sh
   ```

4. **Access locally**:
   - UI: http://localhost:8080
   - API Docs: http://localhost:8080/docs

See [Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md) for detailed deployment instructions.

## License

Internal use only - Odace project.
