# Database Schema Fix for AI Responses

## Problem
The error indicates that the `raw_response` column in the `ai_responses` table has a NOT NULL constraint, but our code tries to create records with NULL values during processing.

## Solution Options

### Option 1: Reset AIResponse Table (Recommended)
This will drop and recreate the table with the correct schema:

```bash
# Run this in your project directory
python3 reset_ai_responses.py
```

### Option 2: Manual Database Fix
If you prefer to manually update the database:

```sql
-- Connect to your PostgreSQL database and run:
ALTER TABLE ai_responses ALTER COLUMN raw_response DROP NOT NULL;
```

### Option 3: Using Docker (if running in containers)
```bash
# Connect to your database container and run the SQL command
docker-compose exec db psql -U your_username -d your_database_name -c "ALTER TABLE ai_responses ALTER COLUMN raw_response DROP NOT NULL;"
```

## What Was Fixed

1. **Database Model**: Updated `models.py` to make `raw_response` nullable during processing
2. **Error Handling**: Added proper session rollback in `ai_response_manager.py`
3. **Content Storage**: Enhanced to store document content for rerun functionality

## After Running the Fix

Once you've applied the database fix using any of the above methods, the AI analysis should work correctly and store all responses with full rerun capability.

## Test the Fix

After applying the fix, try running the analysis again. You should now be able to:
- View all AI responses in the project detail page
- Rate and favorite responses
- Rerun any previous analysis
- View response history with parent-child relationships

## Verification

Check that the table was created correctly:
```sql
\d ai_responses
```

The `raw_response` column should show as nullable.