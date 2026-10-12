# Stratos Integration Documentation

## Overview

The Stratos integration provides AI-powered job recommendations for users based on their skill profiles. The system automatically syncs eligible jobs for all users with skill profiles on server startup.

## Architecture

### Components

1. **StratosService** (`app/services/stratos_service.py`)
   - HTTP client for Stratos API
   - Handles job recommendation queries
   - Paginates through results

2. **Startup Task** (`app/services/startup_tasks.py`)
   - `sync_user_eligible_jobs()` - Main sync function
   - Runs on server startup (configurable)
   - Can be triggered manually via API

3. **API Endpoint** (`app/api/v1/jobs.py`)
   - `POST /admin/jobs/sync-eligible-jobs` - Manual sync trigger

## Configuration

Add to your `.env` file:

```env
# Stratos API Configuration
STRATOS_API_URL=http://10.118.77.232:8000
STRATOS_API_KEY=sk_live_576308ef_yz7Mo966u9ov6ayiCZ_yd55hqR6aG-nE
STRATOS_SYNC_ON_STARTUP=true
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `STRATOS_API_URL` | Base URL of Stratos API | `http://10.118.77.232:8000` |
| `STRATOS_API_KEY` | API key for authentication | Required |
| `STRATOS_SYNC_ON_STARTUP` | Enable automatic sync on startup | `true` |

## How It Works

### Automatic Sync (On Startup)

1. Server starts up
2. Database initializes
3. If `STRATOS_SYNC_ON_STARTUP=true`:
   - Fetches all users with `UserSkillProfile` records
   - For each user:
     - Extracts `skills` and `description`
     - Calls Stratos API with this data
     - Receives job recommendations (up to 100)
     - Clears old `UserEligibleJob` entries for that user
     - Inserts new job recommendations

### Stratos API Request

```json
{
  "q": "Recommend jobs for the following user",
  "top_k": 100,
  "user_context": {
    "skills": [
      "Python",
      "Machine Learning",
      "Data Analysis"
    ],
    "description": "Experienced ML engineer with focus on NLP..."
  }
}
```

### Response Processing

The service extracts job IDs from the response:

```json
{
  "hits": [
    {
      "id": "2356e097-117f-4c5c-a5dc-421c84e27674",
      "score": 0.34696576,
      "fields": {
        "title": "Full Stack Developer",
        ...
      }
    }
  ]
}
```

Only the `id` field is used to populate `UserEligibleJob` table.

## Database Schema

### UserEligibleJob Table

```sql
CREATE TABLE user_eligible_jobs (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    match_score INTEGER,  -- Future: store Stratos score
    matched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_user_job UNIQUE (user_id, job_id)
);
```

## API Usage

### Manual Sync

Trigger sync manually (useful for testing or scheduled updates):

```bash
curl -X POST http://localhost:8000/api/v1/admin/jobs/sync-eligible-jobs
```

Response:
```json
{
  "status": "success",
  "message": "Eligible jobs sync completed successfully"
}
```

### Get Eligible Jobs for User

```bash
curl http://localhost:8000/api/v1/users/{user_id}/eligible-jobs
```

## Logging

The sync process logs:

```
INFO  - Starting user eligible jobs sync...
INFO  - Found 15 users with skill profiles
INFO  - Processing user a1b2c3d4-... with 9 skills
INFO  - Found 47 job recommendations for user a1b2c3d4-...
INFO  - Successfully assigned 47 jobs to user a1b2c3d4-...
INFO  - User eligible jobs sync complete. Processed 15/15 users, assigned 623 total job matches
```

## Error Handling

- **HTTP Errors**: Logged and returned as empty list
- **Invalid Job IDs**: Skipped with warning
- **User Processing Errors**: Logged, transaction rolled back, continues to next user
- **Decryption Errors**: Handled gracefully in token decryption

## Performance Considerations

- **Pagination**: Fetches 10 jobs per page, up to 100 total per user
- **Async Processing**: Uses async/await for concurrent HTTP requests
- **Database Transactions**: Each user is a separate transaction
- **Timeout**: 30-second timeout for Stratos API calls

## Future Enhancements

1. **Store Match Scores**: Stratos returns scores, can be stored in `match_score` field
2. **Scheduled Updates**: Run sync daily/weekly via scheduler
3. **Incremental Updates**: Only update changed profiles
4. **Caching**: Cache Stratos responses to reduce API calls
5. **Webhooks**: Real-time updates when new jobs are added

## Troubleshooting

### Sync Not Running on Startup

Check logs for:
```
Stratos sync on startup is disabled
```

Ensure `STRATOS_SYNC_ON_STARTUP=true` in `.env`

### No Job Recommendations

- Verify user has `UserSkillProfile` with skills
- Check Stratos API is accessible
- Verify API key is valid
- Check logs for HTTP errors

### Slow Startup

If sync takes too long:
- Reduce number of users
- Set `STRATOS_SYNC_ON_STARTUP=false`
- Use manual endpoint instead
- Consider scheduled background job

## Development

### Testing

```python
# Test Stratos service
from app.services.stratos_service import get_stratos_service

service = get_stratos_service()
job_ids = await service.get_job_recommendations(
    skills=["Python", "FastAPI"],
    description="Backend developer"
)
```

### Running Sync Manually

```python
from app.services.startup_tasks import sync_user_eligible_jobs

await sync_user_eligible_jobs()
```
