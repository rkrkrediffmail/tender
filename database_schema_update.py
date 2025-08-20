#!/usr/bin/env python3
"""
Database Schema Update Script
Ensures database schema matches current models
"""

import sys
import os
from sqlalchemy import text, inspect
from main import create_app
from models import db

def check_and_add_missing_columns():
    """Check for missing columns and add them"""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Check projects table columns
        existing_columns = [col['name'] for col in inspector.get_columns('projects')]
        print(f"Existing projects columns: {existing_columns}")
        
        # Expected columns from model
        expected_columns = [
            'id', 'name', 'description', 'client_name', 'rfp_title', 
            'estimated_value', 'currency', 'priority', 'completion_percentage',
            'status', 'rfp_type', 'workflow_stage', 'workflow_notes',
            'submitted_by', 'current_approver_email', 'due_date',
            'user_id', 'created_at', 'updated_at', 'meta_data'
        ]
        
        missing_columns = [col for col in expected_columns if col not in existing_columns]
        
        if missing_columns:
            print(f"Missing columns: {missing_columns}")
            
            # Add missing columns
            alter_statements = []
            
            for col in missing_columns:
                if col == 'client_name':
                    alter_statements.append("ALTER TABLE projects ADD COLUMN client_name VARCHAR(255);")
                elif col == 'rfp_title':
                    alter_statements.append("ALTER TABLE projects ADD COLUMN rfp_title VARCHAR(500);")
                elif col == 'estimated_value':
                    alter_statements.append("ALTER TABLE projects ADD COLUMN estimated_value NUMERIC(15,2);")
                elif col == 'currency':
                    alter_statements.append("ALTER TABLE projects ADD COLUMN currency VARCHAR(10) DEFAULT 'USD';")
                elif col == 'priority':
                    alter_statements.append("ALTER TABLE projects ADD COLUMN priority VARCHAR(50) DEFAULT 'medium';")
                elif col == 'completion_percentage':
                    alter_statements.append("ALTER TABLE projects ADD COLUMN completion_percentage INTEGER DEFAULT 0;")
                elif col == 'rfp_type':
                    alter_statements.append("ALTER TABLE projects ADD COLUMN rfp_type VARCHAR(50) DEFAULT 'implementation';")
                elif col == 'workflow_stage':
                    alter_statements.append("ALTER TABLE projects ADD COLUMN workflow_stage VARCHAR(50) DEFAULT 'created';")
                elif col == 'workflow_notes':
                    alter_statements.append("ALTER TABLE projects ADD COLUMN workflow_notes TEXT;")
                elif col == 'current_approver_email':
                    alter_statements.append("ALTER TABLE projects ADD COLUMN current_approver_email VARCHAR(255);")
                elif col == 'due_date':
                    alter_statements.append("ALTER TABLE projects ADD COLUMN due_date TIMESTAMP;")
                elif col == 'updated_at':
                    alter_statements.append("ALTER TABLE projects ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
                elif col == 'meta_data':
                    alter_statements.append("ALTER TABLE projects ADD COLUMN meta_data JSONB DEFAULT '{}';")
            
            # Execute the alter statements
            for statement in alter_statements:
                try:
                    print(f"Executing: {statement}")
                    db.session.execute(text(statement))
                    db.session.commit()
                    print("✅ Success")
                except Exception as e:
                    print(f"❌ Error: {e}")
                    db.session.rollback()
        else:
            print("✅ All expected columns exist")

def verify_foreign_keys():
    """Verify foreign key constraints"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if user_id and submitted_by foreign keys exist
            inspector = inspect(db.engine)
            fks = inspector.get_foreign_keys('projects')
            
            print(f"Existing foreign keys on projects table:")
            for fk in fks:
                print(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
                
            # Ensure foreign keys exist
            expected_fks = ['user_id', 'submitted_by']
            existing_fk_columns = [fk['constrained_columns'][0] for fk in fks if fk['referred_table'] == 'users']
            
            for fk_col in expected_fks:
                if fk_col not in existing_fk_columns:
                    print(f"Adding foreign key: {fk_col}")
                    if fk_col == 'user_id':
                        db.session.execute(text("ALTER TABLE projects ADD CONSTRAINT fk_projects_user_id FOREIGN KEY (user_id) REFERENCES users(id);"))
                    elif fk_col == 'submitted_by':
                        db.session.execute(text("ALTER TABLE projects ADD CONSTRAINT fk_projects_submitted_by FOREIGN KEY (submitted_by) REFERENCES users(id);"))
                    db.session.commit()
                    
        except Exception as e:
            print(f"Foreign key check error: {e}")
            db.session.rollback()

def main():
    """Main function"""
    print("🔧 Database Schema Update Tool")
    print("=" * 50)
    
    try:
        print("1. Checking and adding missing columns...")
        check_and_add_missing_columns()
        
        print("\n2. Verifying foreign keys...")
        verify_foreign_keys()
        
        print("\n✅ Schema update completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Schema update failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())