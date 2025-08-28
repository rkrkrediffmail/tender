#!/usr/bin/env python3
"""
Database migration script to add RFP checklist system tables
"""

import os
import sys

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def migrate_checklist_tables():
    """Create RFP checklist system tables"""
    print("🔄 Creating RFP checklist system tables...")
    
    try:
        from main import app
        from models import db
        
        with app.app_context():
            print("   Creating checklist system tables...")
            
            migration_sql = """
            -- RFP Checklist Templates table
            CREATE TABLE IF NOT EXISTS rfp_checklist_templates (
                id SERIAL PRIMARY KEY,
                checklist_id VARCHAR(100) UNIQUE NOT NULL,
                rfp_type VARCHAR(100) NOT NULL,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                version VARCHAR(50) DEFAULT '1.0',
                original_filename VARCHAR(500),
                file_path VARCHAR(1000),
                file_size INTEGER,
                file_hash VARCHAR(64),
                sheets_config JSON,
                checklist_structure JSON,
                total_questions INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                is_default BOOLEAN DEFAULT FALSE,
                parsing_status VARCHAR(50) DEFAULT 'pending',
                parsing_errors JSON,
                created_by INTEGER NOT NULL REFERENCES users(id),
                updated_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );

            -- Checklist Items table
            CREATE TABLE IF NOT EXISTS checklist_items (
                id SERIAL PRIMARY KEY,
                item_id VARCHAR(100) UNIQUE NOT NULL,
                checklist_id VARCHAR(100) NOT NULL REFERENCES rfp_checklist_templates(checklist_id),
                sheet_name VARCHAR(255),
                row_number INTEGER,
                excel_reference VARCHAR(50),
                section VARCHAR(255),
                category VARCHAR(255),
                question_text TEXT NOT NULL,
                requirement_type VARCHAR(100),
                priority VARCHAR(50),
                mandatory BOOLEAN DEFAULT FALSE,
                expected_response_type VARCHAR(100),
                validation_criteria TEXT,
                keywords JSON,
                ai_analysis_prompt TEXT,
                context_requirements JSON,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );

            -- RFP Checklist Validations table
            CREATE TABLE IF NOT EXISTS rfp_checklist_validations (
                id SERIAL PRIMARY KEY,
                validation_id VARCHAR(100) UNIQUE NOT NULL,
                project_id VARCHAR(255) NOT NULL REFERENCES projects(id),
                checklist_id VARCHAR(100) NOT NULL REFERENCES rfp_checklist_templates(checklist_id),
                total_items INTEGER DEFAULT 0,
                addressed_items INTEGER DEFAULT 0,
                missing_items INTEGER DEFAULT 0,
                partial_items INTEGER DEFAULT 0,
                unclear_items INTEGER DEFAULT 0,
                overall_completion_percentage FLOAT DEFAULT 0.0,
                high_priority_completion FLOAT DEFAULT 0.0,
                mandatory_completion FLOAT DEFAULT 0.0,
                ai_model_used VARCHAR(100),
                processing_time_seconds FLOAT,
                total_tokens_used INTEGER,
                status VARCHAR(50) DEFAULT 'pending',
                error_message TEXT,
                validation_summary JSON,
                excel_export_path VARCHAR(1000),
                clarification_export_path VARCHAR(1000),
                validated_by INTEGER NOT NULL REFERENCES users(id),
                validation_date TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );

            -- Checklist Item Validations table
            CREATE TABLE IF NOT EXISTS checklist_item_validations (
                id SERIAL PRIMARY KEY,
                item_validation_id VARCHAR(100) UNIQUE NOT NULL,
                validation_id VARCHAR(100) NOT NULL REFERENCES rfp_checklist_validations(validation_id),
                item_id VARCHAR(100) NOT NULL REFERENCES checklist_items(item_id),
                project_id VARCHAR(255) NOT NULL REFERENCES projects(id),
                status VARCHAR(50) NOT NULL,
                confidence_score FLOAT DEFAULT 0.0,
                extracted_content TEXT,
                ai_analysis JSON,
                ai_reasoning TEXT,
                source_documents JSON,
                source_sections JSON,
                relevant_excerpts JSON,
                needs_clarification BOOLEAN DEFAULT FALSE,
                clarification_reason TEXT,
                suggested_question TEXT,
                processing_time_seconds FLOAT,
                tokens_used INTEGER,
                analyzed_at TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );

            -- Clarification Requests table
            CREATE TABLE IF NOT EXISTS clarification_requests (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(100) UNIQUE NOT NULL,
                project_id VARCHAR(255) NOT NULL REFERENCES projects(id),
                validation_id VARCHAR(100) NOT NULL REFERENCES rfp_checklist_validations(validation_id),
                item_id VARCHAR(100) NOT NULL REFERENCES checklist_items(item_id),
                question_text TEXT NOT NULL,
                category VARCHAR(255),
                section VARCHAR(255),
                priority VARCHAR(50),
                reason TEXT,
                relevant_rfp_sections JSON,
                impact_if_not_clarified TEXT,
                status VARCHAR(50) DEFAULT 'PENDING',
                internal_notes TEXT,
                sent_date TIMESTAMP,
                response_received_date TIMESTAMP,
                response_content TEXT,
                resolution_status VARCHAR(50),
                resolution_notes TEXT,
                follow_up_required BOOLEAN DEFAULT FALSE,
                included_in_export BOOLEAN DEFAULT FALSE,
                export_reference VARCHAR(100),
                created_by INTEGER NOT NULL REFERENCES users(id),
                updated_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );

            -- Create indexes for performance
            CREATE INDEX IF NOT EXISTS idx_checklist_templates_rfp_type ON rfp_checklist_templates(rfp_type);
            CREATE INDEX IF NOT EXISTS idx_checklist_templates_active ON rfp_checklist_templates(is_active);
            CREATE INDEX IF NOT EXISTS idx_checklist_items_checklist ON checklist_items(checklist_id);
            CREATE INDEX IF NOT EXISTS idx_checklist_validations_project ON rfp_checklist_validations(project_id);
            CREATE INDEX IF NOT EXISTS idx_item_validations_validation ON checklist_item_validations(validation_id);
            CREATE INDEX IF NOT EXISTS idx_clarification_requests_project ON clarification_requests(project_id);
            CREATE INDEX IF NOT EXISTS idx_clarification_requests_status ON clarification_requests(status);

            -- Past Proposals table (enhanced with Claude analysis fields)
            CREATE TABLE IF NOT EXISTS past_proposals (
                id SERIAL PRIMARY KEY,
                proposal_id VARCHAR(100) UNIQUE NOT NULL,
                title VARCHAR(500) NOT NULL,
                client_name VARCHAR(255) NOT NULL,
                project_type VARCHAR(100),
                proposal_type VARCHAR(50) NOT NULL,
                filename VARCHAR(500) NOT NULL,
                original_filename VARCHAR(500) NOT NULL,
                file_path VARCHAR(1000),
                file_size INTEGER,
                extracted_content TEXT,
                submission_year INTEGER,
                proposal_value FLOAT,
                currency VARCHAR(10) DEFAULT 'USD',
                status VARCHAR(50),
                win_probability FLOAT,
                technologies_used JSON DEFAULT '[]'::json,
                industry_sector VARCHAR(100),
                project_duration VARCHAR(50),
                team_size INTEGER,
                actual_value FLOAT,
                lessons_learned TEXT,
                key_success_factors JSON DEFAULT '[]'::json,
                key_challenges JSON DEFAULT '[]'::json,
                processing_status VARCHAR(50) DEFAULT 'pending',
                claude_analyzed BOOLEAN DEFAULT FALSE,
                vector_stored BOOLEAN DEFAULT FALSE,
                error_message TEXT,
                extracted_capabilities JSON DEFAULT '[]'::json,
                extracted_technologies JSON DEFAULT '[]'::json,
                company_experience JSON DEFAULT '[]'::json,
                solution_approaches JSON DEFAULT '[]'::json,
                uploaded_at TIMESTAMP DEFAULT NOW(),
                processed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                uploaded_by INTEGER REFERENCES users(id)
            );

            -- Indexes for past proposals
            CREATE INDEX IF NOT EXISTS idx_past_proposals_status ON past_proposals(status);
            CREATE INDEX IF NOT EXISTS idx_past_proposals_industry ON past_proposals(industry_sector);
            CREATE INDEX IF NOT EXISTS idx_past_proposals_type ON past_proposals(project_type);
            CREATE INDEX IF NOT EXISTS idx_past_proposals_claude ON past_proposals(claude_analyzed);
            CREATE INDEX IF NOT EXISTS idx_past_proposals_vector ON past_proposals(vector_stored);
            CREATE INDEX IF NOT EXISTS idx_past_proposals_uploaded_at ON past_proposals(uploaded_at);
            """
            
            # Execute the migration
            with db.engine.connect() as conn:
                for statement in migration_sql.split(';'):
                    statement = statement.strip()
                    if statement:
                        try:
                            conn.execute(db.text(statement))
                        except Exception as e:
                            print(f"   Warning: {e}")
                conn.commit()
            
            print("✅ RFP checklist system tables created successfully")
            
            # Verify the migration
            print("   Verifying migration...")
            
            verify_sql = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN (
                'rfp_checklist_templates', 'checklist_items', 
                'rfp_checklist_validations', 'checklist_item_validations', 
                'clarification_requests', 'past_proposals'
            )
            ORDER BY table_name;
            """
            
            with db.engine.connect() as conn:
                result = conn.execute(db.text(verify_sql))
                tables = [row[0] for row in result.fetchall()]
                
                expected_tables = [
                    'checklist_item_validations', 'checklist_items',
                    'clarification_requests', 'past_proposals', 'rfp_checklist_templates',
                    'rfp_checklist_validations'
                ]
                
                if len(tables) >= 6:
                    print(f"✅ Migration verified: {len(tables)} tables found")
                    for table in tables:
                        print(f"   - {table}")
                else:
                    print(f"⚠️  Migration incomplete: Only {len(tables)} tables found")
                    return False
            
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def main():
    """Main migration function"""
    print("=" * 60)
    print("🚀 RFP CHECKLIST SYSTEM MIGRATION")
    print("=" * 60)
    
    if migrate_checklist_tables():
        print("\n" + "=" * 60)
        print("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\n🔗 Next steps:")
        print("   1. Restart the application: docker-compose restart web")
        print("   2. Access Admin > Checklist Templates to upload your first template")
        print("   3. Create a project and run checklist validation")
        print("   4. Test the full workflow with a sample RFP")
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