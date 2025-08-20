#!/usr/bin/env python3
"""
Vector Database Setup Script
Sets up PostgreSQL with pgvector extension and creates necessary tables
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import datetime

def setup_vector_database():
    """Set up PostgreSQL with pgvector extension"""
    try:
        # Get database connection details from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL environment variable not set")
            return False
        
        # Parse database URL
        import urllib.parse
        parsed = urllib.parse.urlparse(database_url)
        
        db_config = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:],  # Remove leading slash
            'user': parsed.username,
            'password': parsed.password
        }
        
        print("🔧 Setting up PostgreSQL vector database...")
        print(f"📊 Connecting to: {db_config['host']}:{db_config['port']}/{db_config['database']}")
        
        # Connect to PostgreSQL
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Create pgvector extension if it doesn't exist
        print("📦 Installing pgvector extension...")
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("✅ pgvector extension installed successfully")
        except psycopg2.Error as e:
            print(f"⚠️ Could not create pgvector extension: {e}")
            print("   This might require superuser privileges or the extension might not be available")
            print("   The system will still work but without vector similarity search")
        
        # Verify extension installation
        cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
        vector_installed = cursor.fetchone()[0]
        
        if vector_installed:
            print("✅ pgvector extension is available")
        else:
            print("⚠️ pgvector extension is not installed")
        
        # Create LangChain tables if they don't exist
        print("📋 Creating LangChain vector tables...")
        
        # Create collection table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS langchain_pg_collection (
                uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL UNIQUE,
                cmetadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create embedding table with vector column if pgvector is available
        if vector_installed:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
                    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    collection_id UUID NOT NULL REFERENCES langchain_pg_collection(uuid) ON DELETE CASCADE,
                    embedding vector(1536),  -- OpenAI ada-002 dimension
                    document TEXT NOT NULL,
                    cmetadata JSONB,
                    custom_id VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS langchain_pg_embedding_collection_id_idx 
                ON langchain_pg_embedding (collection_id);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS langchain_pg_embedding_vector_idx 
                ON langchain_pg_embedding USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            
        else:
            # Create without vector column as fallback
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
                    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    collection_id UUID NOT NULL REFERENCES langchain_pg_collection(uuid) ON DELETE CASCADE,
                    embedding TEXT,  -- Store as JSON text fallback
                    document TEXT NOT NULL,
                    cmetadata JSONB,
                    custom_id VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
        
        print("✅ LangChain vector tables created successfully")
        
        # Create tender proposals collection if it doesn't exist
        cursor.execute("""
            INSERT INTO langchain_pg_collection (name, cmetadata)
            VALUES ('tender_proposals', '{"description": "Past tender proposals and RFP responses"}')
            ON CONFLICT (name) DO NOTHING;
        """)
        
        # Check table status
        cursor.execute("""
            SELECT 
                c.name,
                COUNT(e.uuid) as document_count
            FROM langchain_pg_collection c
            LEFT JOIN langchain_pg_embedding e ON c.uuid = e.collection_id
            GROUP BY c.uuid, c.name;
        """)
        
        collections = cursor.fetchall()
        print(f"📊 Collections status:")
        for name, count in collections:
            print(f"   {name}: {count} documents")
        
        cursor.close()
        conn.close()
        
        print("✅ Vector database setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Vector database setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vector_operations():
    """Test basic vector operations"""
    try:
        print("🧪 Testing vector database operations...")
        
        # Import after setup
        from vector_store import get_vector_store
        
        # Get vector store instance
        vs = get_vector_store()
        if not vs or not vs.vector_store:
            print("❌ Vector store not available")
            return False
        
        # Test adding a document
        test_doc = {
            'content': 'This is a test proposal for cloud infrastructure using AWS services including EC2, S3, and Lambda functions for a healthcare client.',
            'metadata': {
                'title': 'Test Healthcare Cloud Proposal',
                'client_name': 'Test Healthcare Corp',
                'project_type': 'infrastructure',
                'submission_year': 2024,
                'status': 'test'
            }
        }
        
        success = vs.add_proposal_document(
            content=test_doc['content'],
            metadata=test_doc['metadata'],
            document_type='test'
        )
        
        if success:
            print("✅ Test document added successfully")
            
            # Test searching
            results = vs.search_similar_proposals('cloud healthcare AWS', k=1)
            if results:
                print(f"✅ Search test successful - found {len(results)} results")
                print(f"   Best match: {results[0]['similarity_score']:.3f} similarity")
            else:
                print("⚠️ Search test returned no results")
        else:
            print("❌ Failed to add test document")
            return False
        
        # Get statistics
        stats = vs.get_collection_stats()
        print(f"📊 Collection stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Vector operations test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Starting Vector Database Setup")
    print("=" * 50)
    
    # Step 1: Set up database and tables
    db_success = setup_vector_database()
    
    if not db_success:
        print("❌ Database setup failed - exiting")
        sys.exit(1)
    
    # Step 2: Initialize Flask app and create tables
    print("\n🔧 Initializing application database...")
    try:
        # Add current directory to Python path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        from main import create_app
        from models import db, init_db
        from proposal_manager import PastProposal
        
        app = create_app()
        with app.app_context():
            # Create all tables including PastProposal
            db.create_all()
            
            # Run full database initialization
            init_db(app)
            
            print("✅ Application database tables created")
    
    except Exception as e:
        print(f"❌ Application database setup failed: {e}")
        sys.exit(1)
    
    # Step 3: Test vector operations
    print("\n🧪 Testing vector operations...")
    test_success = test_vector_operations()
    
    if test_success:
        print("\n✅ Vector database setup and testing completed successfully!")
        print("\n📋 Next steps:")
        print("1. Upload past proposals via /past-proposals page")
        print("2. Test AI analysis with vector context")
        print("3. Monitor vector search performance")
    else:
        print("\n⚠️ Vector database setup completed but testing failed")
        print("   You can still use the system, but vector search may not work optimally")
    
    print("=" * 50)

if __name__ == "__main__":
    main()