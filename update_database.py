#!/usr/bin/env python3
"""
Database update script to add AI analysis results table
Run this after updating models.py to ensure the new table is created
"""

import os
import sys
from datetime import datetime

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def update_database():
    """Update database with new AI analysis results table"""
    try:
        # Import after adding to path
        from main import create_app
        from models import db, AIAnalysisResult, init_db
        
        # Create Flask app
        app = create_app()
        
        with app.app_context():
            print("🔄 Updating database schema...")
            
            # Create all tables (including new ones)
            db.create_all()
            print("✅ Database tables created/updated successfully")
            
            # Verify the new table exists
            try:
                # Try to query the new table
                count = AIAnalysisResult.query.count()
                print(f"✅ AIAnalysisResult table verified - {count} existing records")
            except Exception as e:
                print(f"⚠️ Could not verify AIAnalysisResult table: {e}")
            
            # Re-run full database initialization to ensure everything is set up
            init_db(app)
            
            print("✅ Database update completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Database update failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🚀 Starting database update...")
    print("="*50)
    
    success = update_database()
    
    print("="*50)
    if success:
        print("✅ Database update completed successfully!")
        print("📊 AI analysis results will now be stored and can be viewed in the UI")
    else:
        print("❌ Database update failed - please check the error messages above")
        sys.exit(1)