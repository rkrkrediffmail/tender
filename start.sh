#!/bin/bash
# ITSS RFPplus - Production Start Script

echo "🚀 Starting ITSS RFPplus..."

# Set production environment
export FLASK_ENV=production

# Ensure required directories exist
mkdir -p uploads logs

# Check if database connection works
echo "🔍 Checking database connection..."
python -c "
try:
    from main import create_app
    app = create_app()
    with app.app_context():
        from models import db
        db.engine.execute('SELECT 1')
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "🎉 Starting ITSS RFPplus server..."
    if [ "$FLASK_ENV" = "development" ]; then
        python main.py
    else
        # Production mode with Gunicorn
        gunicorn -w 2 -b 0.0.0.0:5000 main:app --timeout 300 --keep-alive 2 --max-requests 1000
    fi
else
    echo "💥 Failed to start - database connection failed"
    exit 1
fi