#!/usr/bin/env python3
"""
Add project purge columns to existing database
This script adds purged_at, purged_by, and purge_reason columns
"""

from main import create_app
from models import db
from sqlalchemy import text

def add_purge_columns():
    """Add purge-related columns to projects table"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 Adding project purge columns...")
            
            # Check if columns already exist
            result = db.engine.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'projects' 
                AND column_name IN ('purged_at', 'purged_by', 'purge_reason')
            """))
            
            existing_columns = [row[0] for row in result.fetchall()]
            
            columns_to_add = []
            if 'purged_at' not in existing_columns:
                columns_to_add.append("ALTER TABLE projects ADD COLUMN purged_at TIMESTAMP")
            if 'purged_by' not in existing_columns:
                columns_to_add.append("ALTER TABLE projects ADD COLUMN purged_by INTEGER REFERENCES users(id)")
            if 'purge_reason' not in existing_columns:
                columns_to_add.append("ALTER TABLE projects ADD COLUMN purge_reason TEXT")
            
            if columns_to_add:
                for sql in columns_to_add:
                    db.engine.execute(text(sql))
                    print(f"✅ Added column: {sql.split('ADD COLUMN ')[1].split(' ')[0]}")
                
                db.session.commit()
                print("✅ Successfully added all purge columns")
            else:
                print("ℹ️  All purge columns already exist")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to add purge columns: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = add_purge_columns()
    if success:
        print("\n🎉 Database schema updated! Project purging functionality is now ready.")
    else:
        print("\n❌ Failed to update schema. Please check the error above.")