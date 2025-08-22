#!/usr/bin/env python3
"""
Database migration script to add partner intelligence fields
"""

import os
import sys

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def migrate_partner_fields():
    """Add new partner intelligence fields to the database"""
    print("🔄 Starting partner intelligence fields migration...")
    
    try:
        from main import app
        from models import db
        
        with app.app_context():
            # Add the missing columns to the partners table
            print("   Adding new columns to partners table...")
            
            migration_sql = """
            ALTER TABLE partners 
            ADD COLUMN IF NOT EXISTS website_content TEXT,
            ADD COLUMN IF NOT EXISTS scraped_offerings JSON,
            ADD COLUMN IF NOT EXISTS capabilities_summary TEXT,
            ADD COLUMN IF NOT EXISTS solution_categories JSON,
            ADD COLUMN IF NOT EXISTS technology_stack JSON,
            ADD COLUMN IF NOT EXISTS industry_focus JSON,
            ADD COLUMN IF NOT EXISTS competitive_advantages JSON,
            ADD COLUMN IF NOT EXISTS partnership_level VARCHAR(50) DEFAULT 'STANDARD',
            ADD COLUMN IF NOT EXISTS revenue_share_percentage FLOAT DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS discount_level FLOAT DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS support_level VARCHAR(50) DEFAULT 'BASIC',
            ADD COLUMN IF NOT EXISTS scrape_status VARCHAR(50) DEFAULT 'PENDING';
            """
            
            # Execute the migration
            with db.engine.connect() as conn:
                conn.execute(db.text(migration_sql))
                conn.commit()
            
            print("✅ Partner intelligence fields added successfully")
            
            # Update existing partners to set default values
            print("   Setting default values for existing partners...")
            
            update_sql = """
            UPDATE partners 
            SET 
                partnership_level = COALESCE(partnership_level, 'VENDOR'),
                revenue_share_percentage = COALESCE(revenue_share_percentage, 0.0),
                discount_level = COALESCE(discount_level, 0.0),
                support_level = COALESCE(support_level, 'BASIC'),
                scrape_status = COALESCE(scrape_status, 'PENDING')
            WHERE 
                partnership_level IS NULL 
                OR revenue_share_percentage IS NULL 
                OR discount_level IS NULL 
                OR support_level IS NULL 
                OR scrape_status IS NULL;
            """
            
            with db.engine.connect() as conn:
                conn.execute(db.text(update_sql))
                conn.commit()
            
            print("✅ Default values set for existing partners")
            
            # Verify the migration
            print("   Verifying migration...")
            
            verify_sql = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'partners' 
            AND column_name IN (
                'website_content', 'scraped_offerings', 'capabilities_summary',
                'solution_categories', 'technology_stack', 'industry_focus',
                'competitive_advantages', 'partnership_level', 'revenue_share_percentage',
                'discount_level', 'support_level', 'scrape_status'
            )
            ORDER BY column_name;
            """
            
            with db.engine.connect() as conn:
                result = conn.execute(db.text(verify_sql))
                columns = result.fetchall()
                
                if len(columns) >= 12:  # Should have at least 12 new columns
                    print(f"✅ Migration verified: {len(columns)} new columns found")
                    for col in columns:
                        print(f"   - {col[0]} ({col[1]})")
                else:
                    print(f"⚠️  Migration incomplete: Only {len(columns)} columns found")
                    return False
            
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def main():
    """Main migration function"""
    print("=" * 60)
    print("🚀 PARTNER INTELLIGENCE FIELDS MIGRATION")
    print("=" * 60)
    
    if migrate_partner_fields():
        print("\n" + "=" * 60)
        print("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\n🔗 Next steps:")
        print("   1. Restart the application: docker-compose restart web")
        print("   2. Test partner creation and website scraping")
        print("   3. Verify partner intelligence features work correctly")
        return True
    else:
        print("\n❌ MIGRATION FAILED!")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)