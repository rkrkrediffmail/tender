#!/usr/bin/env python3
"""
Azure Storage System Installation Script
Complete setup and testing for ephemeral deployment environments
"""

import os
import sys
import logging
import tempfile
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def install_dependencies():
    """Install required Azure dependencies"""
    print("\n🔧 STEP 1: Installing Azure Dependencies")
    print("=" * 50)
    
    dependencies = [
        'azure-storage-blob>=12.19.0',
        'azure-identity>=1.15.0',
        'chromadb>=1.0.0'
    ]
    
    for dep in dependencies:
        print(f"📦 Installing {dep}...")
        result = os.system(f"pip install {dep}")
        if result != 0:
            print(f"❌ Failed to install {dep}")
            return False
        else:
            print(f"✅ {dep} installed successfully")
    
    print("\n✅ All dependencies installed successfully")
    return True

def test_azure_connectivity():
    """Test Azure Storage connectivity"""
    print("\n🔗 STEP 2: Testing Azure Storage Connectivity")
    print("=" * 50)
    
    try:
        from azure_deployment_config import validate_azure_deployment
        
        validation = validate_azure_deployment()
        
        if validation['success']:
            print("✅ Azure Storage connectivity verified")
            print(f"   Azure Storage: {'✅' if validation['azure_storage_ready'] else '❌'}")
            print(f"   Database: {'✅' if validation['database_ready'] else '❌'}")
            print(f"   AI Services: {'✅' if validation['ai_services_ready'] else '⚪'}")
            return True
        else:
            print("❌ Azure connectivity test failed:")
            for error in validation['errors']:
                print(f"   - {error}")
            return False
            
    except ImportError as e:
        print(f"❌ Missing Azure dependencies: {e}")
        return False
    except Exception as e:
        print(f"❌ Connectivity test failed: {e}")
        return False

def initialize_storage_systems():
    """Initialize all storage systems"""
    print("\n🚀 STEP 3: Initializing Storage Systems")
    print("=" * 50)
    
    try:
        # Initialize Azure Blob Storage
        print("📦 Initializing Azure Blob Storage...")
        from azure_blob_storage_manager import init_blob_storage
        blob_result = init_blob_storage()
        
        if blob_result['success']:
            print(f"✅ Blob Storage: {len(blob_result['containers'])} containers ready")
        else:
            print(f"❌ Blob Storage failed: {blob_result['error']}")
            return False
        
        # Initialize Azure Vector DB
        print("🔍 Initializing Azure Vector Database...")
        from azure_vector_db_manager import init_azure_vector_db
        vector_result = init_azure_vector_db()
        
        if vector_result['success']:
            print(f"✅ Vector DB: {vector_result['collections_count']} collections")
        else:
            print(f"❌ Vector DB failed: {vector_result['error']}")
            return False
        
        # Initialize Azure File System
        print("📁 Initializing Azure File System...")
        from azure_file_manager import init_azure_file_system
        file_result = init_azure_file_system()
        
        if file_result['success']:
            print(f"✅ File System: {file_result['storage_stats']['total_files']} files")
        else:
            print(f"❌ File System failed: {file_result['error']}")
            return False
        
        print("\n✅ All storage systems initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Storage system initialization failed: {e}")
        return False

def run_functionality_tests():
    """Run comprehensive functionality tests"""
    print("\n🧪 STEP 4: Running Functionality Tests")
    print("=" * 50)
    
    test_results = {
        'file_upload_download': False,
        'vector_db_operations': False,
        'storage_cleanup': False
    }
    
    try:
        # Test 1: File Upload/Download
        print("📤 Testing file upload and download...")
        success = test_file_operations()
        test_results['file_upload_download'] = success
        print(f"   File Operations: {'✅' if success else '❌'}")
        
        # Test 2: Vector DB Operations
        print("🔍 Testing vector database operations...")
        success = test_vector_operations()
        test_results['vector_db_operations'] = success
        print(f"   Vector Operations: {'✅' if success else '❌'}")
        
        # Test 3: Storage Cleanup
        print("🧹 Testing storage cleanup...")
        success = test_cleanup_operations()
        test_results['storage_cleanup'] = success
        print(f"   Cleanup Operations: {'✅' if success else '❌'}")
        
        # Overall result
        all_passed = all(test_results.values())
        print(f"\n{'✅' if all_passed else '❌'} Functionality Tests: {sum(test_results.values())}/3 passed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Functionality tests failed: {e}")
        return False

def test_file_operations():
    """Test file upload and download operations"""
    try:
        from azure_file_manager import get_azure_file_manager
        import io
        
        file_manager = get_azure_file_manager()
        
        # Create test file
        test_content = f"Test file content - {datetime.now().isoformat()}"
        test_file = io.BytesIO(test_content.encode())
        
        # Mock FileStorage object
        class MockFileStorage:
            def __init__(self, content, filename):
                self.content = content
                self.filename = filename
                self.content_type = 'text/plain'
            
            def save(self, path):
                with open(path, 'wb') as f:
                    f.write(self.content.getvalue())
        
        mock_file = MockFileStorage(test_file, 'test_file.txt')
        
        # Test upload
        upload_result = file_manager.save_uploaded_file(
            file=mock_file,
            container_type='uploads',
            custom_filename='system_test'
        )
        
        if not upload_result['success']:
            return False
        
        # Test download
        download_result = file_manager.get_file_for_processing(
            container_type='uploads',
            blob_name=upload_result['saved_filename']
        )
        
        if not download_result['success']:
            return False
        
        # Verify content
        with open(download_result['local_file_path'], 'r') as f:
            downloaded_content = f.read()
        
        if downloaded_content != test_content:
            return False
        
        # Cleanup
        file_manager.delete_file('uploads', upload_result['saved_filename'])
        file_manager.cleanup_local_file(download_result['local_file_path'])
        
        return True
        
    except Exception as e:
        print(f"File operations test error: {e}")
        return False

def test_vector_operations():
    """Test vector database operations"""
    try:
        from azure_vector_db_manager import get_azure_vector_db_manager
        
        vector_manager = get_azure_vector_db_manager()
        client = vector_manager.get_client()
        
        # Create test collection
        collection = vector_manager.get_or_create_collection('test_system_collection')
        
        # Add test data
        test_documents = ["Test document 1", "Test document 2"]
        test_ids = ["test_1", "test_2"]
        
        collection.add(
            documents=test_documents,
            ids=test_ids
        )
        
        # Query test data
        results = collection.query(
            query_texts=["Test document"],
            n_results=2
        )
        
        if len(results['documents'][0]) != 2:
            return False
        
        # Test sync operation
        sync_result = vector_manager.sync_to_blob_storage(force=True)
        if not sync_result['success']:
            return False
        
        # Cleanup test collection
        client.delete_collection('test_system_collection')
        
        return True
        
    except Exception as e:
        print(f"Vector operations test error: {e}")
        return False

def test_cleanup_operations():
    """Test storage cleanup operations"""
    try:
        from azure_blob_storage_manager import get_blob_storage_manager
        from azure_vector_db_manager import get_azure_vector_db_manager
        
        blob_manager = get_blob_storage_manager()
        vector_manager = get_azure_vector_db_manager()
        
        # Test temp file cleanup
        blob_manager.cleanup_temp_files(older_than_hours=0)  # Clean all temp files
        
        # Test sync status
        sync_status = vector_manager.get_sync_status()
        if 'auto_sync_running' not in sync_status:
            return False
        
        return True
        
    except Exception as e:
        print(f"Cleanup operations test error: {e}")
        return False

def create_deployment_guide():
    """Create deployment guide"""
    print("\n📚 STEP 5: Creating Deployment Guide")
    print("=" * 50)
    
    try:
        guide_content = [
            "# Azure Storage System Deployment Guide",
            "",
            "## System Overview",
            "This application uses Azure Blob Storage for all persistent data in ephemeral deployments.",
            "",
            "### Storage Architecture:",
            "- **Azure Blob Storage**: All files, documents, generated content",
            "- **ChromaDB + Azure**: Vector database with automatic blob sync",
            "- **PostgreSQL**: Structured data (already on Azure)",
            "- **Local Temp**: Temporary processing files only",
            "",
            "## Deployment Checklist",
            "",
            "### 1. Environment Variables (Required)",
            "```bash",
            "# Azure Storage",
            "export AZURE_STORAGE_CONNECTION_STRING='DefaultEndpointsProtocol=https;...'",
            "",
            "# Database",
            "export DATABASE_URL='postgresql://user:pass@host:5432/db?sslmode=require'",
            "",
            "# AI Services",
            "export ANTHROPIC_API_KEY='sk-ant-api03-...'",
            "export OPENAI_API_KEY='sk-proj-...'  # Optional",
            "",
            "# Application",
            "export SECRET_KEY='your-secret-key'",
            "```",
            "",
            "### 2. Azure Storage Setup",
            "1. Create Azure Storage Account",
            "2. Note the connection string",
            "3. Containers will be auto-created:",
            "   - `uploads`: Document uploads",
            "   - `vector-db`: ChromaDB backups",
            "   - `generated`: Generated files",
            "   - `templates`: Template files",
            "   - `cache`: Temporary cache",
            "",
            "### 3. Application Startup",
            "The application will automatically:",
            "- Initialize all Azure storage systems",
            "- Restore vector database from latest backup",
            "- Start auto-sync for vector database (every 5 minutes)",
            "- Handle all file operations transparently",
            "",
            "### 4. Monitoring",
            "- Check application logs for Azure storage operations",
            "- Vector database syncs automatically every 5 minutes",
            "- Temporary files cleaned up every 24 hours",
            "- All uploads/downloads logged with success/failure status",
            "",
            "### 5. Backup & Recovery",
            "- Vector database: Automatic backups to blob storage",
            "- Files: All files immediately uploaded to blob storage",
            "- Database: Standard PostgreSQL backup procedures",
            "",
            "### 6. Troubleshooting",
            "- Run `python azure_deployment_config.py` to validate configuration",
            "- Check Azure Storage Account connectivity",
            "- Verify container permissions",
            "- Review application logs for storage errors",
            "",
            "### 7. Performance Notes",
            "- File processing uses local temp files for speed",
            "- Vector database syncs happen in background",
            "- Large file uploads may take longer (progress logged)",
            "- Automatic cleanup prevents disk space issues",
            "",
            "## Commands",
            "```bash",
            "# Validate deployment configuration",
            "python azure_deployment_config.py",
            "",
            "# Create sample environment file",
            "python azure_deployment_config.py create-sample",
            "",
            "# Test complete system",
            "python install_azure_storage_system.py",
            "",
            "# Run application",
            "python main.py",
            "```",
            "",
            f"Generated on: {datetime.now().isoformat()}",
            "System: Azure Storage for Ephemeral Deployments"
        ]
        
        with open('AZURE_DEPLOYMENT_GUIDE.md', 'w') as f:
            f.write('\n'.join(guide_content))
        
        print("✅ Deployment guide created: AZURE_DEPLOYMENT_GUIDE.md")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create deployment guide: {e}")
        return False

def main():
    """Main installation and testing process"""
    print("🚀 AZURE STORAGE SYSTEM INSTALLATION")
    print("=" * 60)
    print("Installing and testing complete Azure storage system for ephemeral deployments")
    print("=" * 60)
    
    steps = [
        ("Installing Dependencies", install_dependencies),
        ("Testing Connectivity", test_azure_connectivity),
        ("Initializing Systems", initialize_storage_systems),
        ("Running Tests", run_functionality_tests),
        ("Creating Guide", create_deployment_guide)
    ]
    
    success_count = 0
    
    for step_name, step_function in steps:
        try:
            if step_function():
                success_count += 1
            else:
                print(f"\n❌ {step_name} failed")
                break
        except KeyboardInterrupt:
            print("\n\n⚠️ Installation interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ {step_name} failed with error: {e}")
            break
    
    print(f"\n{'='*60}")
    if success_count == len(steps):
        print("🎉 AZURE STORAGE SYSTEM INSTALLATION COMPLETE!")
        print("✅ All systems ready for ephemeral deployment")
        print(f"✅ {success_count}/{len(steps)} installation steps completed")
        print("\n📋 Next Steps:")
        print("1. Review AZURE_DEPLOYMENT_GUIDE.md")
        print("2. Set up your environment variables")
        print("3. Deploy to your ephemeral environment")
        print("4. Monitor logs for any storage issues")
        return True
    else:
        print("❌ AZURE STORAGE SYSTEM INSTALLATION INCOMPLETE")
        print(f"⚠️  {success_count}/{len(steps)} installation steps completed")
        print("\n🔧 Troubleshooting:")
        print("1. Check your environment variables")
        print("2. Verify Azure Storage Account access")
        print("3. Review error messages above")
        print("4. Run: python azure_deployment_config.py")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Installation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected installation error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)