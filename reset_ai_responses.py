#!/usr/bin/env python3
"""
Reset AIResponse table with correct schema
Run this script to fix the database constraint issue
"""

from main import create_app
from models import db, AIResponse

def reset_ai_responses_table():
    """Drop and recreate ai_responses table with correct schema"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 Resetting ai_responses table...")
            
            # Drop the table if it exists
            AIResponse.__table__.drop(db.engine, checkfirst=True)
            print("📦 Dropped existing ai_responses table")
            
            # Recreate with correct schema
            AIResponse.__table__.create(db.engine)
            print("✅ Created ai_responses table with correct schema")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to reset table: {e}")
            return False

if __name__ == "__main__":
    success = reset_ai_responses_table()
    if success:
        print("\n🎉 Database schema fixed! You can now run the analysis again.")
    else:
        print("\n❌ Failed to fix schema. Please check the error above.")