# Database Update Guide for Docker

Since the application runs in Docker, here are several ways to update the database with the new AI analysis features:

## 🚀 **Option 1: Automatic Update (Recommended)**

The application now automatically updates the database on startup. Simply restart your Docker containers:

```bash
# Stop the application
docker-compose down

# Start it again (will auto-update database)
docker-compose up
```

The application will automatically:
- Create the new `ai_analysis_results` table
- Verify all tables exist
- Initialize the admin user
- Display confirmation messages in the logs

## 🔧 **Option 2: Web-Based Update**

Visit the update endpoint in your browser or use curl:

```bash
# Via browser - visit:
http://localhost:5001/update-database

# Via curl:
curl http://localhost:5001/update-database
```

This will return a JSON response confirming the database update.

## 🐳 **Option 3: Docker Exec Command**

Run the update script inside the Docker container:

```bash
# Get the container name
docker-compose ps

# Run the update script inside the container
docker-compose exec web python update_database.py

# Alternative: run directly with docker exec
docker exec -it tender_web_1 python update_database.py
```

## 🔍 **Option 4: Manual Docker Shell**

Access the container shell and run commands manually:

```bash
# Enter the container
docker-compose exec web bash

# Inside the container, run:
python update_database.py

# Or run Python commands directly:
python -c "
from main import create_app
from models import db, init_db
app = create_app()
with app.app_context():
    db.create_all()
    init_db(app)
    print('Database updated successfully!')
"

# Exit the container
exit
```

## ✅ **Verification**

After running any of the above methods, verify the update worked:

1. **Check the logs** for confirmation messages:
   ```bash
   docker-compose logs web | grep -i "analysis"
   ```

2. **Visit the health endpoint**:
   ```bash
   curl http://localhost:5001/health
   ```

3. **Try accessing a project** and look for the new "Analysis History" buttons

4. **Run a new analysis** - it should now be stored in the database

## 🎯 **What Gets Added**

The database update adds:

- **New Table**: `ai_analysis_results` for storing AI analysis results
- **Columns**: analysis_id, project_id, results (JSON), processing_time, etc.
- **Indexes**: For faster querying of analysis history
- **Relationships**: Links to existing projects table

## 🐛 **Troubleshooting**

### Database Connection Issues
```bash
# Check if database is accessible
docker-compose exec web python -c "
from main import create_app
from models import db
app = create_app()
with app.app_context():
    db.session.execute(db.text('SELECT 1'))
    print('Database connection OK')
"
```

### Table Creation Issues
```bash
# Force recreation of all tables
docker-compose exec web python -c "
from main import create_app
from models import db
app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()
    print('All tables recreated')
"
```

### Permission Issues
If you get permission errors, try:
```bash
# Run with sudo if needed
sudo docker-compose exec web python update_database.py

# Or check container permissions
docker-compose exec web ls -la /app/
```

## 📊 **Testing the New Features**

After successful update:

1. **Upload documents** to a project
2. **Run AI analysis** - should see processing messages
3. **Visit project details** - should see "Analysis History" button
4. **Check analysis history** - should show stored results
5. **Re-run analysis** - should create new entry in history

## 🔄 **Rollback (if needed)**

If something goes wrong, you can restore from backup:

```bash
# Stop containers
docker-compose down

# Restore database from backup (if you have one)
# Then restart
docker-compose up
```

## 💡 **Pro Tips**

- **Always backup** your database before major updates
- **Check logs** regularly: `docker-compose logs -f web`
- **Use health endpoint** to monitor system status
- **Test in development** before updating production

The new AI analysis storage feature will greatly improve user experience by eliminating the need to re-run analyses every time!