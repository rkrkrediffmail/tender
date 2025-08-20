from pathlib import Path

home_dir = Path.home()
print(f"User's home directory: {home_dir}")
#!/usr/bin/env python3
"""
Database migration script to add missing columns to documents table
Run this script to update your existing database
"""

import os
import sys
from datetime import datetime

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def migrate_database():
    """Add missing columns to documents table"""
    try:
        from main import create_app
        from models import db
        
        app = create_app()
        
        with app.app_context():
            # Check if we can connect to database
            db.session.execute(db.text('SELECT 1'))
            print("✅ Database connection successful")
            
            # Add missing columns using raw SQL
            migration_sql = """
            -- Add extracted_content column if it doesn't exist
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='documents' AND column_name='extracted_content') THEN
                    ALTER TABLE documents ADD COLUMN extracted_content TEXT;
                    PRINT '✅ Added extracted_content column';
                END IF;
            END $$;
            
            -- Add processing_status column if it doesn't exist
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='documents' AND column_name='processing_status') THEN
                    ALTER TABLE documents ADD COLUMN processing_status VARCHAR(50) DEFAULT 'uploaded';
                    PRINT '✅ Added processing_status column';
                END IF;
            END $$;
            
            -- Add error_message column if it doesn't exist
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='documents' AND column_name='error_message') THEN
                    ALTER TABLE documents ADD COLUMN error_message TEXT;
                    PRINT '✅ Added error_message column';
                END IF;
            END $$;
            
            -- Add processed_at column if it doesn't exist
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='documents' AND column_name='processed_at') THEN
                    ALTER TABLE documents ADD COLUMN processed_at TIMESTAMP;
                    PRINT '✅ Added processed_at column';
                END IF;
            END $$;
            
            -- Add task_id column if it doesn't exist
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='documents' AND column_name='task_id') THEN
                    ALTER TABLE documents ADD COLUMN task_id VARCHAR(255);
                    PRINT '✅ Added task_id column';
                END IF;
            END $$;
            """
            
            # Execute migration
            db.session.execute(db.text(migration_sql))
            db.session.commit()
            
            print("✅ Database migration completed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def simple_migrate():
    """Simple migration using SQLAlchemy"""
    try:
        from main import create_app
        from models import db
        
        app = create_app()
        
        with app.app_context():
            # Drop and recreate all tables (USE WITH CAUTION!)
            print("⚠️ WARNING: This will recreate all tables and lose existing data!")
            confirm = input("Type 'yes' to continue: ")
            
            if confirm.lower() == 'yes':
                db.drop_all()
                db.create_all()
                print("✅ Database recreated with updated schema")
                return True
            else:
                print("❌ Migration cancelled")
                return False
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == '__main__':
    print("🔄 Starting database migration...")
    print("Choose migration option:")
    print("1. Add missing columns (safe - preserves data)")
    print("2. Recreate tables (WARNING - loses all data)")
    
    choice = input("Enter choice (1 or 2): ")
    
    if choice == "1":
        migrate_database()
    elif choice == "2":
        simple_migrate()
    else:
        print("❌ Invalid choice")
        sys.exit(1)
