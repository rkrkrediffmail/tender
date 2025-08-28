#!/usr/bin/env python3
"""
Installation and Setup Script for Claude Vector Intelligence System
Full Vector + Claude Architecture Implementation
"""

import os
import sys
import subprocess
import json
from datetime import datetime

def print_banner():
    """Print installation banner"""
    print("=" * 80)
    print("🚀 CLAUDE VECTOR INTELLIGENCE SYSTEM INSTALLATION")
    print("=" * 80)
    print("Full Vector + Claude Architecture for ITSS Global")
    print("Maximum AI Intelligence for Proposal Generation")
    print("=" * 80)
    print()

def install_dependencies():
    """Install required Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    dependencies = [
        "chromadb>=0.4.0",
        "anthropic>=0.8.0", 
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "scikit-learn>=1.3.0",
        "sentence-transformers>=2.2.0"
    ]
    
    for dep in dependencies:
        try:
            print(f"   Installing {dep}...")
            subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                         check=True, capture_output=True)
            print(f"   ✅ {dep} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Warning: Could not install {dep}: {e}")
            print(f"      You may need to install this manually")
    
    print("   ✅ Dependencies installation completed\n")

def verify_environment():
    """Verify environment setup"""
    print("🔍 Verifying environment setup...")
    
    # Check API keys
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_key:
        print("   ✅ ANTHROPIC_API_KEY found")
    else:
        print("   ❌ ANTHROPIC_API_KEY not found")
        print("      Please set your Anthropic API key:")
        print("      export ANTHROPIC_API_KEY='your_api_key_here'")
    
    # Check database URL
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        print("   ✅ DATABASE_URL found")
    else:
        print("   ⚠️  DATABASE_URL not set - will use SQLite default")
    
    # Check directory structure
    required_dirs = ['uploads', 'vector_db', 'templates', 'agents']
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"   ✅ {dir_name}/ directory exists")
        else:
            try:
                os.makedirs(dir_name, exist_ok=True)
                print(f"   ✅ Created {dir_name}/ directory")
            except Exception as e:
                print(f"   ⚠️  Could not create {dir_name}/: {e}")
    
    print("   ✅ Environment verification completed\n")

def test_claude_connection():
    """Test Claude API connection"""
    print("🧠 Testing Claude API connection...")
    
    try:
        import anthropic
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not api_key:
            print("   ❌ No API key available for testing")
            return False
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Simple test message
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[{"role": "user", "content": "Hello Claude! Please respond with 'Claude Vector Intelligence System Ready'"}]
        )
        
        response_text = response.content[0].text
        if "Claude Vector Intelligence System Ready" in response_text:
            print("   ✅ Claude API connection successful")
            return True
        else:
            print("   ⚠️  Claude API responded but with unexpected content")
            return False
            
    except Exception as e:
        print(f"   ❌ Claude API connection failed: {e}")
        return False

def test_vector_store():
    """Test vector store setup"""
    print("🗂️  Testing vector store setup...")
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        # Create test client
        client = chromadb.PersistentClient(
            path="./vector_db_test",
            settings=Settings(
                allow_reset=True,
                anonymized_telemetry=False
            )
        )
        
        # Create test collection
        collection = client.create_collection(name="test_collection")
        
        # Add test document
        collection.add(
            documents=["This is a test document for ITSS Global vector intelligence"],
            metadatas=[{"test": True, "timestamp": datetime.now().isoformat()}],
            ids=["test_doc_1"]
        )
        
        # Query test
        results = collection.query(
            query_texts=["test document ITSS"],
            n_results=1
        )
        
        if results['documents'] and results['documents'][0]:
            print("   ✅ Vector store setup successful")
            
            # Cleanup test collection
            client.delete_collection("test_collection")
            import shutil
            shutil.rmtree("./vector_db_test", ignore_errors=True)
            
            return True
        else:
            print("   ❌ Vector store query returned no results")
            return False
            
    except Exception as e:
        print(f"   ❌ Vector store setup failed: {e}")
        return False

def test_claude_vector_intelligence():
    """Test the complete Claude Vector Intelligence system"""
    print("🎯 Testing Claude Vector Intelligence system...")
    
    try:
        from claude_vector_intelligence import get_claude_vector_intelligence
        
        # Initialize system
        cvi = get_claude_vector_intelligence()
        
        # Test system components
        test_results = cvi.test_intelligence_system()
        
        if test_results.get('overall_success'):
            print("   ✅ Claude Vector Intelligence system operational")
            print(f"   📊 System Status:")
            print(f"      - Claude Available: {'✅' if test_results.get('claude_available') else '❌'}")
            print(f"      - Vector Store Available: {'✅' if test_results.get('vector_store_available') else '❌'}")
            print(f"      - Embedding Model Available: {'✅' if test_results.get('embedding_model_available') else '❌'}")
            
            if test_results.get('claude_analysis_success'):
                print(f"      - Claude Analysis Test: ✅")
            
            if test_results.get('vector_collections_count') is not None:
                print(f"      - Vector Collections: {test_results.get('vector_collections_count')}")
            
            return True
        else:
            print(f"   ❌ System test failed: {test_results.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Claude Vector Intelligence test failed: {e}")
        return False

def test_enhanced_agents():
    """Test enhanced agents"""
    print("🤖 Testing enhanced agents...")
    
    try:
        # Test Document Intelligence Agent
        from enhanced_document_intelligence import get_enhanced_document_intelligence_agent
        doc_agent = get_enhanced_document_intelligence_agent()
        print("   ✅ Enhanced Document Intelligence Agent loaded")
        
        # Test Requirements Engineering Agent
        from enhanced_requirements_engineering import get_enhanced_requirements_engineering_agent
        req_agent = get_enhanced_requirements_engineering_agent()
        print("   ✅ Enhanced Requirements Engineering Agent loaded")
        
        # Test basic functionality
        test_requirements = [
            "Core banking system integration",
            "API gateway implementation", 
            "Regulatory compliance framework"
        ]
        
        test_metadata = {
            'project_type': 'bfsi',
            'industry_sector': 'banking'
        }
        
        # Test requirements analysis
        result = req_agent.analyze_requirements_with_intelligence(test_requirements, test_metadata)
        
        if result.get('agent') == 'enhanced_requirements_engineering':
            print("   ✅ Requirements Engineering Agent functional")
            return True
        else:
            print("   ❌ Requirements Engineering Agent test failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Enhanced agents test failed: {e}")
        return False

def run_database_migration():
    """Run database migration"""
    print("🗄️  Running database migration...")
    
    try:
        # Import and run migration
        import migrate_checklist_tables
        success = migrate_checklist_tables.main()
        
        if success:
            print("   ✅ Database migration completed successfully")
            return True
        else:
            print("   ❌ Database migration failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Database migration error: {e}")
        print("   You may need to run migration manually:")
        print("   python3 migrate_checklist_tables.py")
        return False

def create_test_configuration():
    """Create test configuration file"""
    print("⚙️  Creating test configuration...")
    
    config = {
        "claude_vector_intelligence": {
            "enabled": True,
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 4000,
            "temperature": 0.2,
            "vector_store_path": "./vector_db",
            "embedding_model": "claude-embeddings"
        },
        "enhanced_agents": {
            "document_intelligence": {
                "enabled": True,
                "use_vector_context": True
            },
            "requirements_engineering": {
                "enabled": True,
                "use_past_intelligence": True
            }
        },
        "proposal_generation": {
            "use_vector_intelligence": True,
            "include_capability_analysis": True,
            "include_gap_analysis": True,
            "include_competitive_positioning": True
        },
        "installation": {
            "date": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    }
    
    try:
        with open("claude_vector_config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        print("   ✅ Configuration file created: claude_vector_config.json")
        return True
    except Exception as e:
        print(f"   ❌ Could not create configuration file: {e}")
        return False

def print_usage_instructions():
    """Print usage instructions"""
    print("\n" + "=" * 80)
    print("🎉 INSTALLATION COMPLETED!")
    print("=" * 80)
    print()
    print("🚀 CLAUDE VECTOR INTELLIGENCE SYSTEM READY")
    print()
    print("📋 Next Steps:")
    print("1. Start your application: python3 main.py")
    print("2. Navigate to /past-proposals to upload past proposal documents")
    print("3. Upload a few past proposals to build the intelligence database")
    print("4. Test the 'Claude Analysis' button to verify functionality")
    print("5. Create a new project and run analysis to see Vector + Claude intelligence")
    print()
    print("🔧 Key Features Now Available:")
    print("• Claude + Vector dual storage for maximum intelligence")
    print("• Enhanced agents with past proposal context")
    print("• Intelligent similarity search across proposals")
    print("• Automated capability extraction and gap analysis") 
    print("• Competitive positioning based on past success")
    print("• Proposal generation with reusable content")
    print()
    print("📊 Monitoring:")
    print("• Check /past-proposals for processing statistics")
    print("• View 'Full Intelligence' status for uploaded proposals")
    print("• Monitor Claude analysis and vector storage success rates")
    print()
    print("🐛 Troubleshooting:")
    print("• Check ANTHROPIC_API_KEY is set correctly")
    print("• Ensure sufficient disk space for vector database")
    print("• Check application logs for detailed error messages")
    print("• Vector DB stored in: ./vector_db/")
    print()
    print("=" * 80)

def main():
    """Main installation function"""
    print_banner()
    
    # Installation steps
    steps = [
        ("Installing Dependencies", install_dependencies),
        ("Verifying Environment", verify_environment),
        ("Testing Claude Connection", test_claude_connection),
        ("Testing Vector Store", test_vector_store),
        ("Running Database Migration", run_database_migration),
        ("Testing Claude Vector Intelligence", test_claude_vector_intelligence),
        ("Testing Enhanced Agents", test_enhanced_agents),
        ("Creating Configuration", create_test_configuration)
    ]
    
    success_count = 0
    for step_name, step_function in steps:
        print(f"🔄 {step_name}...")
        try:
            if step_function():
                success_count += 1
        except Exception as e:
            print(f"   ❌ {step_name} failed with error: {e}")
    
    print(f"\n📊 Installation Summary: {success_count}/{len(steps)} steps completed successfully")
    
    if success_count >= len(steps) - 1:  # Allow for one optional failure
        print_usage_instructions()
        return True
    else:
        print("\n⚠️  Installation completed with some issues.")
        print("Please review the error messages above and resolve any problems.")
        print("You may need to install dependencies manually or check your environment configuration.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Installation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected installation error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)