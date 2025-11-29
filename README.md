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
