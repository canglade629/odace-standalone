# Job Cancellation Feature

## Overview

This feature allows users to stop running pipeline jobs from the job history interface. When a job is stopped, all running and pending tasks are cancelled, and the job status is updated to `cancelled`.

## Implementation Details

### Backend Changes

#### 1. Job and Task Status Enums

Added `CANCELLED` status to both `JobStatus` and `TaskStatus` enums in `app/core/job_manager.py`:

```python
class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"  # New status

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"  # New status
```

#### 2. Pipeline Executor Cancellation Mechanism

**File**: `app/core/pipeline_executor.py`

- Added `cancelled_jobs: Set[str]` to track cancelled job IDs
- Modified `execute_pipeline()` to check for cancellation before and during execution
- Modified `execute_with_dependencies()` to check for cancellation between pipeline executions
- Modified `execute_full_pipeline()` to check for cancellation between bronze and silver layers
- Added `cancel_job()` method to mark jobs for cancellation

**Cancellation Logic**:
1. When a job is cancelled, its ID is added to the `cancelled_jobs` set
2. Before starting each pipeline task, the executor checks if the job is in the cancelled set
3. If cancelled, the task is marked with `CANCELLED` status and skipped
4. The job's final status is set to `CANCELLED`
5. The job ID is removed from the cancelled set after completion

#### 3. API Endpoint

**Endpoint**: `POST /api/jobs/{job_id}/cancel`

**File**: `app/api/routes/jobs.py`

Allows authenticated users to cancel a running job:

```python
@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, api_key: str = Depends(verify_api_key)):
    """Cancel a running job."""
    executor = get_pipeline_executor()
    success = executor.cancel_job(job_id)
    
    if not success:
        raise HTTPException(400, "Could not cancel job")
    
    return {"message": f"Job {job_id} has been cancelled", "status": "cancelled"}
```

**Response**:
```json
{
    "message": "Job <job_id> has been cancelled",
    "job_id": "<job_id>",
    "status": "cancelled"
}
```

**Error Cases**:
- 400: Job doesn't exist or is not running
- 500: Server error

### Frontend Changes

#### 1. UI Components

**File**: `app/static/index.html`

**Stop Button**:
- Added a red "Stop" button next to the "View Details" button for running/pending jobs
- Button only appears when job status is `running` or `pending`
- Includes a square icon (SVG) to indicate stop action

**JavaScript Functions**:

```javascript
async function stopJob(jobId, event) {
    // Stops event propagation to prevent opening modal
    // Shows confirmation dialog
    // Calls the cancel API endpoint
    // Refreshes job history on success
}
```

**Updated Functions**:
- `createJobItem()`: Conditionally renders stop button based on job status
- `getStatusClass()`: Added mapping for 'cancelled' status

#### 2. Styling

**File**: `app/static/style.css`

Added styles for:
- `.btn-danger`: Red button for destructive actions (stop)
- `.badge-cancelled`: Grey badge for cancelled status
- `.job-actions`: Container for multiple action buttons

## User Experience

### Stopping a Job

1. Navigate to the **History** tab
2. Find a job with status `running` or `pending`
3. Click the red **Stop** button
4. Confirm the action in the dialog
5. The job status updates to `cancelled`
6. Currently running tasks will complete their current operation and then stop
7. Pending tasks will not be started

### Status Display

Jobs and tasks can have the following statuses:
- **Pending**: Queued but not yet started
- **Running**: Currently executing
- **Success**: Completed successfully
- **Failed**: Completed with errors
- **Cancelled**: Stopped by user

### Limitations

- Cancellation is cooperative: tasks must check for cancellation between operations
- A task that's currently executing (e.g., uploading data) will complete that operation before stopping
- Cancelled jobs cannot be restarted; you must create a new job

## Technical Considerations

### Race Conditions

The cancellation mechanism handles race conditions by:
1. Checking cancellation status before starting each task
2. Checking cancellation status after completing each task
3. Using a set to track cancelled jobs atomically

### Cleanup

The `cancelled_jobs` set is cleaned up when:
- A job completes (success/failure/cancellation)
- The final job status is written to Firestore

### Firestore Updates

When a job is cancelled:
1. Job status is immediately updated to `CANCELLED` in Firestore
2. Running tasks are marked as `CANCELLED` when they complete
3. Pending tasks are skipped and not added to Firestore

## API Integration

### Example: Cancel a Job

```bash
curl -X POST "https://your-api.com/api/jobs/{job_id}/cancel" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Example Response

```json
{
    "message": "Job 123e4567-e89b-12d3-a456-426614174000 has been cancelled",
    "job_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "cancelled"
}
```

## Future Enhancements

Potential improvements for the cancellation feature:

1. **Force Kill**: Add ability to forcefully terminate tasks
2. **Resume Capability**: Allow cancelled jobs to be resumed from where they stopped
3. **Partial Completion**: Show which tasks completed before cancellation
4. **Cancellation Logs**: Add specific log entries for cancellation events
5. **Bulk Cancellation**: Cancel multiple jobs at once
6. **Auto-cancellation**: Automatically cancel jobs that exceed a timeout

## Testing

To test the cancellation feature:

1. Start a long-running pipeline (e.g., full pipeline with bronze + silver)
2. Navigate to the History tab while it's running
3. Click the Stop button on the running job
4. Verify the job status changes to "cancelled"
5. Check that no new tasks are started after cancellation
6. Verify that the job's completed_at timestamp is set

## Monitoring

Jobs with `cancelled` status can be monitored through:
- The History tab in the web UI
- The `/api/jobs` endpoint (lists all jobs with their statuses)
- Firestore console (jobs collection, filter by status: "cancelled")

