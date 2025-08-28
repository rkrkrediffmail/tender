#!/usr/bin/env python3
"""
Comprehensive fix script for checklist templates issues:
1. Templates not loading on initial page load
2. Delete button not working
"""

import os
import sys

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def check_and_create_tables():
    """Check if tables exist and create them if missing"""
    print("🔍 1. Checking PostgreSQL tables...")
    
    try:
        from main import app
        from models import db
        
        with app.app_context():
            # List of expected tables
            expected_tables = [
                'rfp_checklist_templates',
                'checklist_items', 
                'rfp_checklist_validations',
                'checklist_item_validations',
                'clarification_requests'
            ]
            
            missing_tables = []
            
            for table_name in expected_tables:
                try:
                    result = db.engine.execute(db.text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.fetchone()[0]
                    print(f"   ✅ {table_name}: {count} records")
                except Exception:
                    missing_tables.append(table_name)
                    print(f"   ❌ {table_name}: NOT FOUND")
            
            if missing_tables:
                print(f"\n🔧 Creating missing tables...")
                # Run migration
                import migrate_checklist_tables
                success = migrate_checklist_tables.migrate_checklist_tables()
                
                if success:
                    print(f"   ✅ Tables created successfully")
                    return True
                else:
                    print(f"   ❌ Failed to create tables")
                    return False
            else:
                print(f"   ✅ All tables exist")
                return True
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_template_loading():
    """Test if templates can be loaded"""
    print("\n🔍 2. Testing template loading...")
    
    try:
        from main import app
        from models import RFPChecklistTemplate
        
        with app.app_context():
            template_count = RFPChecklistTemplate.query.count()
            print(f"   📋 Total templates in database: {template_count}")
            
            if template_count > 0:
                templates = RFPChecklistTemplate.query.all()
                print(f"   Templates:")
                for template in templates:
                    print(f"     - {template.name} ({template.rfp_type}) - {template.parsing_status}")
                
                print(f"   ✅ Template loading should work")
                return True
            else:
                print(f"   ℹ️  No templates uploaded yet")
                print(f"      This is why the page appears empty initially")
                print(f"      Upload templates via /admin/checklist-templates")
                return True
                
    except Exception as e:
        print(f"   ❌ Error testing templates: {e}")
        return False

def test_delete_endpoint():
    """Test if delete endpoint exists"""
    print("\n🔍 3. Testing delete API endpoint...")
    
    try:
        from main import app
        
        with app.test_client() as client:
            # Test if the endpoint exists (it will return 401 without auth, but that means it exists)
            response = client.delete('/api/checklist-templates/test-id/delete')
            
            if response.status_code == 401 or response.status_code == 403:
                print(f"   ✅ Delete endpoint exists (requires authentication)")
                return True
            elif response.status_code == 404:
                print(f"   ❌ Delete endpoint NOT FOUND")
                return False
            else:
                print(f"   ✅ Delete endpoint exists (status: {response.status_code})")
                return True
                
    except Exception as e:
        print(f"   ❌ Error testing delete endpoint: {e}")
        return False

def test_javascript_functionality():
    """Check if JavaScript function exists in template"""
    print("\n🔍 4. Checking JavaScript delete function...")
    
    try:
        template_path = "templates/admin/checklist_templates.html"
        
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                content = f.read()
                
            if 'function deleteTemplate' in content:
                print(f"   ✅ deleteTemplate JavaScript function exists")
                
                if '/api/checklist-templates/' in content and '/delete' in content:
                    print(f"   ✅ JavaScript calls correct API endpoint")
                    return True
                else:
                    print(f"   ❌ JavaScript calls wrong API endpoint")
                    return False
            else:
                print(f"   ❌ deleteTemplate JavaScript function missing")
                return False
        else:
            print(f"   ❌ Template file not found: {template_path}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error checking JavaScript: {e}")
        return False

def provide_troubleshooting_guide():
    """Provide troubleshooting steps"""
    print(f"\n" + "=" * 60)
    print("🔧 TROUBLESHOOTING GUIDE")
    print("=" * 60)
    
    print(f"\n📋 ISSUE 1: Templates not showing initially")
    print(f"CAUSE: Either tables don't exist or no templates uploaded")
    print(f"SOLUTION:")
    print(f"  1. Ensure tables exist: python3 migrate_checklist_tables.py")
    print(f"  2. Upload templates via /admin/checklist-templates")
    print(f"  3. Check server logs for any errors")
    
    print(f"\n🗑️ ISSUE 2: Delete button not working")
    print(f"CAUSE: Missing API endpoint")
    print(f"SOLUTION:")
    print(f"  1. Delete API endpoint has been added to main.py")
    print(f"  2. Restart your application: python3 main.py")
    print(f"  3. JavaScript should now work")
    
    print(f"\n🐛 DEBUGGING STEPS:")
    print(f"  1. Check database tables: python3 check_checklist_tables.py")
    print(f"  2. Check server console for debug messages when loading page")
    print(f"  3. Check browser console for JavaScript errors")
    print(f"  4. Test delete with browser developer tools -> Network tab")

def main():
    """Main fix function"""
    print("=" * 60)
    print("🔧 CHECKLIST TEMPLATES ISSUES FIX")
    print("=" * 60)
    
    success_count = 0
    total_checks = 4
    
    # Run all checks
    if check_and_create_tables():
        success_count += 1
    
    if test_template_loading():
        success_count += 1
    
    if test_delete_endpoint():
        success_count += 1
        
    if test_javascript_functionality():
        success_count += 1
    
    print(f"\n📊 RESULTS: {success_count}/{total_checks} checks passed")
    
    if success_count == total_checks:
        print(f"\n🎉 ALL ISSUES SHOULD BE FIXED!")
        print(f"\nNext steps:")
        print(f"1. Restart your application: python3 main.py")
        print(f"2. Navigate to /admin/checklist-templates")
        print(f"3. Upload some templates to see them appear")
        print(f"4. Test the delete functionality")
        return True
    else:
        print(f"\n⚠️  Some issues remain")
        provide_troubleshooting_guide()
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Fix interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)