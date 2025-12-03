# Testing the Stop Button Feature

## Quick Deployment & Testing Guide

### Step 1: Restart Your Server

If running locally:
```bash
# Kill the current server
pkill -f uvicorn

# Restart
cd /Users/christophe.anglade/Documents/odace_backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Clear Browser Cache

**Option A: Hard Refresh**
- Chrome/Firefox/Edge (Mac): `Cmd + Shift + R`
- Chrome/Firefox/Edge (Windows): `Ctrl + Shift + R`

**Option B: Clear Cache via DevTools**
1. Open DevTools (F12 or Cmd+Option+I)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### Step 3: Test the Feature

1. **Open the application** in your browser
2. **Navigate to the "Pipelines" tab**
3. **Start a pipeline** (e.g., "Run Full Pipeline")
4. **Immediately switch to the "History" tab**
5. **Look for the running job** - it should have:
   - Status badge showing "running" (blue)
   - A red "Stop" button next to "View Details"

### Step 4: Debug (If Button Still Not Showing)

#### Check Browser Console
1. Open DevTools (F12)
2. Go to Console tab
3. Look for logs like:
   ```
   Job <job_id>: status=running, shouldShowStop=true
   ```
4. If you see `shouldShowStop=false`, the job status might not be "running"

#### Check Job Status in Console
In the browser console, type:
```javascript
fetch('/api/jobs?limit=5', {
    headers: {'Authorization': 'Bearer ' + localStorage.getItem('apiKey')}
})
.then(r => r.json())
.then(d => console.table(d.jobs.map(j => ({
    name: j.job_name,
    status: j.status,
    tasks: `${j.completed_tasks}/${j.total_tasks}`
}))))
```

This will show you the actual status of your jobs.

#### Verify Static Files Are Loading
1. Open DevTools → Network tab
2. Refresh the page
3. Look for `index.html` and `style.css`
4. Check their timestamps to ensure they're the latest versions

### Step 5: Deploy to Cloud Run (if needed)

If running on Cloud Run:

```bash
cd /Users/christophe.anglade/Documents/odace_backend

# Build and push Docker image
./deploy-cloudrun.sh
```

Or manually:
```bash
# Build
docker build -t gcr.io/icc-project-472009/odace-backend:latest .

# Push
docker push gcr.io/icc-project-472009/odace-backend:latest

# Deploy
gcloud run deploy odace-backend \
  --image gcr.io/icc-project-472009/odace-backend:latest \
  --platform managed \
  --region us-central1 \
  --project icc-project-472009
```

## Expected Behavior

### With Running/Pending Jobs
```
┌─────────────────────────────────────────────────┐
│ Job History                                   🔄 │
├─────────────────────────────────────────────────┤
│                                                  │
│  Full Pipeline - Bronze → Silver                │
│  [running]                                       │
│  user@example.com  |  Dec 3, 2:30 PM  |  2/10   │
│                                      [Stop] [View]│
│                                                  │
└─────────────────────────────────────────────────┘
```

### With Completed Jobs
```
┌─────────────────────────────────────────────────┐
│ Job History                                   🔄 │
├─────────────────────────────────────────────────┤
│                                                  │
│  Full Pipeline - Bronze → Silver                │
│  [success]                                       │
│  user@example.com  |  Dec 3, 2:30 PM  |  10/10  │
│                                           [View] │
│                                                  │
└─────────────────────────────────────────────────┘
```

## Troubleshooting

### Issue: Button Never Shows

**Cause**: Jobs complete too quickly

**Solution**: 
- Run a slower pipeline (Full Pipeline with all bronze + silver)
- Add a delay in your test pipeline
- Check immediately after starting

### Issue: Button Shows But Doesn't Work

**Check**:
1. Browser console for errors
2. Network tab for failed API calls
3. Backend logs for error messages

**Test API Directly**:
```bash
# Get a running job ID
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://your-domain.com/api/jobs?limit=1

# Try to cancel it
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  https://your-domain.com/api/jobs/JOB_ID/cancel
```

### Issue: Changes Not Reflecting

**Try**:
1. Force refresh (Cmd+Shift+R)
2. Clear all browser cache
3. Try incognito/private window
4. Restart server
5. Rebuild Docker image (if on Cloud Run)

## Verification Checklist

- [ ] Server restarted
- [ ] Browser cache cleared
- [ ] Can see console log: "Job XXX: status=running, shouldShowStop=true"
- [ ] Red "Stop" button visible on running jobs
- [ ] Button has square icon and "Stop" text
- [ ] Clicking button shows confirmation dialog
- [ ] After confirmation, job status changes to "cancelled"
- [ ] Cancelled jobs show grey badge

## Additional Debug Commands

### Check if files were modified
```bash
cd /Users/christophe.anglade/Documents/odace_backend
git diff app/static/index.html | grep -i stop
git diff app/static/style.css | grep -i danger
```

### Check file contents directly
```bash
grep -n "stopJob" app/static/index.html
grep -n "btn-danger" app/static/style.css
```

### View recent jobs directly from Firestore (if you have access)
```bash
gcloud firestore databases documents list jobs \
  --project icc-project-472009 \
  --limit 5
```

