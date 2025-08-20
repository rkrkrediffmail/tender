#!/usr/bin/env python3
"""
Simple database fix script
Recreates all tables to match current models
"""

from main import create_app
from models import db, init_db

def main():
    """Recreate database tables"""
    print("🔧 Fixing Database Schema")
    print("=" * 30)
    
    app = create_app()
    
    with app.app_context():
        try:
            print("1. Dropping all tables...")
            db.drop_all()
            print("✅ Tables dropped")
            
            print("2. Creating all tables...")
            db.create_all()
            print("✅ Tables created")
            
            print("3. Initializing data...")
            init_success = init_db(app)
            
            if init_success:
                print("✅ Database initialization successful")
                return 0
            else:
                print("❌ Database initialization failed")
                return 1
                
        except Exception as e:
            print(f"❌ Database fix failed: {e}")
            return 1

if __name__ == '__main__':
    exit(main())