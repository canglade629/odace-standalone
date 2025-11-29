# User Tracking Feature for Job History

**Date**: November 29, 2025  
**Status**: ✅ Deployed and Verified

## Overview

Added user tracking to the job history system. Now the job history page displays which user (via their API key) triggered each pipeline run.

## Changes Made

### Backend Changes

#### 1. Job Model (`app/core/job_manager.py`)
- Added `user_id` field to the `Job` class
- Updated `create_job()` method to accept and store `user_id` parameter
- Updated `to_dict()` and `from_dict()` methods to include `user_id`

#### 2. Pipeline Executor (`app/core/pipeline_executor.py`)
- Updated `execute_full_pipeline()` method to accept `user_id` parameter
- Pass `user_id` to job creation

#### 3. API Route (`app/api/routes/pipeline.py`)
- Renamed `api_key` parameter to `user_id` in `/api/pipeline/run` endpoint (since `verify_api_key` returns the user_id)
- Pass `user_id` to pipeline executor

### Frontend Changes

#### 1. Job List Display (`app/static/index.html`)
- Updated `createJobItem()` function to display user information
- Added user icon (👤) and user email/ID in job metadata
- Shows "System" for jobs without a user_id (legacy jobs)

#### 2. Job Detail Modal (`app/static/index.html`)
- Added job metadata section at top of modal
- Displays:
  - Triggered by: [user email]
  - Started: [timestamp]
  - Status: [badge]

#### 3. Styling (`app/static/style.css`)
- Added `.job-user` class for user display in job list
- Added `.job-modal-meta` class for metadata section in modal
- Styled metadata items for consistent appearance

## Deployment

**Service**: odace-pipeline  
**Revision**: odace-pipeline-00051-26v  
**Region**: europe-west1  
**URL**: https://odace-pipeline-588398598428.europe-west1.run.app

## Testing Results

### Test 1: Create Job with User
```bash
API Key: odace_example_test_key_9876543210fedcba
User: test-pipeline-verification@odace.com
```

**Result**: ✅ Job created successfully with user_id

### Test 2: Verify Job Details
```json
{
  "job_id": "b6d37fb5-8a11-4dee-8b80-d6e495ac7d64",
  "job_name": "Full Pipeline - Bronze → Silver",
  "user_id": "test-pipeline-verification@odace.com",
  "status": "success"
}
```

**Result**: ✅ User ID properly stored in Firestore

### Test 3: Job List Display
```
Recent Jobs:
1. Full Pipeline - Bronze → Silver
   User: test-pipeline-verification@odace.com (NEW)
   Status: success

2. Full Pipeline - Bronze → Silver
   User: System (LEGACY)
   Status: success
```

**Result**: ✅ User information displayed correctly in job list

## Features

### 1. User Identification
- Each job tracks which user triggered it via their API key
- User ID is the email address associated with the API key
- Legacy jobs (created before this feature) show "System"

### 2. Visual Indicators
- **Job List**: Shows user with 👤 icon in job metadata
- **Job Modal**: Displays "Triggered by: [user]" at top of details
- **Hover Tooltip**: Full user email visible on hover

### 3. Backward Compatibility
- Existing jobs without `user_id` gracefully handled
- Displayed as "System" instead of showing null/undefined
- No database migration required (Firestore is schema-less)

## UI Mockup

### Job List View
```
┌─────────────────────────────────────────────────────┐
│ Full Pipeline - Bronze → Silver          ✅ success│
│ 👤 test-pipeline-verification@odace.com            │
│ 📅 Nov 29, 2025 10:42 AM   📊 12/12 tasks         │
│                              [View Details]         │
└─────────────────────────────────────────────────────┘
```

### Job Detail Modal
```
┌───────────────────────────────────────────────────┐
│ Full Pipeline - Bronze → Silver              [×] │
├───────────────────────────────────────────────────┤
│ Triggered by: test-pipeline-verification@odace.com│
│ Started: Nov 29, 2025 10:42 AM                    │
│ Status: ✅ success                                │
├───────────────────────────────────────────────────┤
│ Bronze Pipelines                                   │
│ ┌─────────────────────────────────────────┐      │
│ │ Pipeline │ Status │ Duration │ Message  │      │
│ └─────────────────────────────────────────┘      │
└───────────────────────────────────────────────────┘
```

## Benefits

1. **Accountability**: Track who triggered each pipeline run
2. **Auditing**: Full audit trail of pipeline executions
3. **Debugging**: Easier to identify who to contact about job issues
4. **Multi-User Support**: Essential for team environments
5. **Security**: Compliance with audit requirements

## API Response Examples

### GET /api/jobs
```json
{
  "jobs": [
    {
      "job_id": "b6d37fb5-8a11-4dee-8b80-d6e495ac7d64",
      "job_name": "Full Pipeline - Bronze → Silver",
      "user_id": "test-pipeline-verification@odace.com",
      "status": "success",
      "started_at": "2025-11-29T10:42:22.409971Z",
      "completed_at": "2025-11-29T10:42:58.141327Z",
      "total_tasks": 12,
      "completed_tasks": 12,
      "failed_tasks": 0,
      "progress_percent": 100.0
    }
  ]
}
```

### GET /api/jobs/{job_id}
```json
{
  "job_id": "b6d37fb5-8a11-4dee-8b80-d6e495ac7d64",
  "job_name": "Full Pipeline - Bronze → Silver",
  "user_id": "test-pipeline-verification@odace.com",
  "status": "success",
  "tasks": [...]
}
```

## Future Enhancements

Potential improvements:
1. Filter jobs by user in UI
2. User statistics (total jobs, success rate)
3. Email notifications to job owner on completion
4. User permissions (restrict viewing others' jobs)
5. User activity dashboard

## Files Modified

1. `app/core/job_manager.py` - Added user_id to Job model
2. `app/core/pipeline_executor.py` - Pass user_id through execution chain
3. `app/api/routes/pipeline.py` - Capture user_id from auth
4. `app/static/index.html` - Display user in UI
5. `app/static/style.css` - Style user display elements

---

**Feature Status**: ✅ **PRODUCTION READY**

All changes have been deployed and tested successfully. User tracking is now active for all new pipeline runs.

