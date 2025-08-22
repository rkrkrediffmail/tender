#!/usr/bin/env python3
"""
Database migration script to add new partner intelligence fields
Run this script to update the Partner table with new fields
"""

import os
import sys
from sqlalchemy import text

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def migrate_partner_fields():
    """Add new partner intelligence fields to existing Partner table"""
    try:
        from main import app
        from models import db
        
        with app.app_context():
            # List of new fields to add
            new_fields = [
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS website_content TEXT",
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS scraped_offerings JSON",
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS capabilities_summary TEXT",
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS last_scraped TIMESTAMP",
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS scrape_status VARCHAR(20) DEFAULT 'PENDING'",
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS scrape_error TEXT",
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS solution_categories JSON",
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS technology_stack JSON",
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS industry_focus JSON",
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS competitive_advantages JSON"
            ]
            
            print("🔄 Adding new partner intelligence fields...")
            
            for sql in new_fields:
                try:
                    db.session.execute(text(sql))
                    print(f"✅ Added field: {sql.split('ADD COLUMN IF NOT EXISTS')[1].split()[0]}")
                except Exception as e:
                    print(f"⚠️  Field may already exist: {e}")
            
            db.session.commit()
            print("✅ Partner table migration completed successfully!")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_partner_fields()