#!/usr/bin/env python3
"""
Quick script to check if checklist tables exist in PostgreSQL
"""

import os
import sys

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def check_tables():
    """Check if checklist tables exist"""
    try:
        from main import app
        from models import db
        
        with app.app_context():
            print("🔍 Checking PostgreSQL checklist tables...")
            
            # List of expected tables
            expected_tables = [
                'rfp_checklist_templates',
                'checklist_items',
                'rfp_checklist_validations', 
                'checklist_item_validations',
                'clarification_requests',
                'past_proposals'
            ]
            
            existing_tables = []
            missing_tables = []
            
            for table_name in expected_tables:
                try:
                    # Try to query the table
                    result = db.engine.execute(db.text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.fetchone()[0]
                    existing_tables.append((table_name, count))
                    print(f"✅ {table_name}: {count} records")
                except Exception as e:
                    missing_tables.append(table_name)
                    print(f"❌ {table_name}: NOT FOUND ({str(e)[:50]}...)")
            
            print(f"\n📊 SUMMARY:")
            print(f"✅ Existing tables: {len(existing_tables)}/{len(expected_tables)}")
            print(f"❌ Missing tables: {len(missing_tables)}")
            
            if missing_tables:
                print(f"\n🔧 MISSING TABLES:")
                for table in missing_tables:
                    print(f"   - {table}")
                print(f"\n💡 TO FIX: Run the migration script:")
                print(f"   python3 migrate_checklist_tables.py")
                return False
            else:
                print(f"\n🎉 All checklist tables exist in PostgreSQL!")
                
                # Check if there are any templates
                from models import RFPChecklistTemplate
                template_count = RFPChecklistTemplate.query.count()
                print(f"📋 Total checklist templates: {template_count}")
                
                if template_count == 0:
                    print(f"ℹ️  No templates uploaded yet. Upload via:")
                    print(f"   /admin/checklist-templates")
                
                return True
                
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("CHECKLIST TABLES CHECK")
    print("=" * 50)
    
    success = check_tables()
    
    if success:
        print("\n✅ Database check completed successfully!")
    else:
        print("\n⚠️  Issues found - see above for fixes")
    
    sys.exit(0 if success else 1)