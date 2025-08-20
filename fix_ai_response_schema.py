#!/usr/bin/env python3
"""
Fix AIResponse schema - make raw_response nullable
This script updates the existing database constraint
"""

import os
import sys
from sqlalchemy import create_engine, text

def fix_ai_response_schema():
    """Fix the raw_response column to allow null values"""
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found in environment")
            return False
        
        # Create engine
        engine = create_engine(database_url)
        
        print("🔧 Fixing AIResponse schema...")
        
        with engine.connect() as conn:
            # Check if the table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'ai_responses'
                );
            """))
            
            table_exists = result.fetchone()[0]
            
            if not table_exists:
                print("ℹ️  ai_responses table doesn't exist yet - no migration needed")
                return True
            
            # Alter the column to allow null values
            conn.execute(text("""
                ALTER TABLE ai_responses 
                ALTER COLUMN raw_response DROP NOT NULL;
            """))
            
            conn.commit()
            print("✅ Successfully updated ai_responses.raw_response to allow null values")
            return True
            
    except Exception as e:
        print(f"❌ Schema fix failed: {e}")
        return False

if __name__ == "__main__":
    success = fix_ai_response_schema()
    sys.exit(0 if success else 1)