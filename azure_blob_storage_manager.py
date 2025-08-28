#!/usr/bin/env python3
"""
Azure Blob Storage Manager
Comprehensive storage solution for ephemeral deployment environments
Handles all file operations, vector database persistence, and temporary file management
"""

import os
import tempfile
import shutil
import logging
from typing import Dict, List, Any, Optional, Union, BinaryIO
from datetime import datetime, timedelta
import threading
from pathlib import Path
import json
import zipfile
import io

try:
    from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, ContentSettings
    from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

logger = logging.getLogger(__name__)

class AzureBlobStorageManager:
    """
    Comprehensive Azure Blob Storage Manager
    Provides transparent file operations with local caching for performance
    """
    
    def __init__(self):
        """Initialize Azure Blob Storage with multiple containers"""
        self.blob_service_client = None
        self.containers = {
            'uploads': 'uploads',              # Document uploads, past proposals
            'vector-db': 'vector-db',         # ChromaDB vector database files
            'generated': 'generated',          # Generated proposals, reports
            'templates': 'templates',          # Template files
            'cache': 'cache',                 # Temporary cache files
            'logs': 'logs'                    # Application logs (if needed)
        }
        
        # Local temporary directory for processing
        self.temp_dir = tempfile.mkdtemp(prefix="tender_app_")
        
        # Thread locks for concurrent operations
        self._locks = {container: threading.Lock() for container in self.containers.keys()}
        
        # Initialize Azure connection
        self._init_azure_client()
        self._ensure_containers_exist()
        
        logger.info(f"Azure Blob Storage Manager initialized with temp dir: {self.temp_dir}")
    
    def _init_azure_client(self):
        """Initialize Azure Blob Service Client"""
        if not AZURE_AVAILABLE:
            raise ImportError("Azure Storage SDK not available. Install with: pip install azure-storage-blob")
        
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable not set")
        
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            logger.info("✅ Azure Blob Storage client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Azure Blob Storage client: {e}")
            raise
    
    def _ensure_containers_exist(self):
        """Ensure all required containers exist"""
        for container_name, container_key in self.containers.items():
            try:
                container_client = self.blob_service_client.get_container_client(container_key)
                container_client.create_container()
                logger.info(f"✅ Container created: {container_key}")
            except ResourceExistsError:
                logger.info(f"✅ Container exists: {container_key}")
            except Exception as e:
                logger.error(f"❌ Failed to create container {container_key}: {e}")
                raise
    
    def upload_file(self, 
                   local_file_path: str, 
                   container_type: str, 
                   blob_name: str = None,
                   overwrite: bool = True,
                   content_type: str = None) -> Dict[str, Any]:
        """
        Upload file to Azure Blob Storage
        
        Args:
            local_file_path: Path to local file
            container_type: Container type ('uploads', 'vector-db', etc.)
            blob_name: Name for blob (if None, uses filename)
            overwrite: Whether to overwrite existing blob
            content_type: MIME type for the blob
            
        Returns:
            Dict with upload results
        """
        try:
            if container_type not in self.containers:
                raise ValueError(f"Invalid container type: {container_type}")
            
            if not os.path.exists(local_file_path):
                raise FileNotFoundError(f"Local file not found: {local_file_path}")
            
            # Generate blob name if not provided
            if blob_name is None:
                blob_name = os.path.basename(local_file_path)
            
            container_name = self.containers[container_type]
            
            with self._locks[container_type]:
                # Get blob client
                blob_client = self.blob_service_client.get_blob_client(
                    container=container_name, 
                    blob=blob_name
                )
                
                # Set content settings
                content_settings = None
                if content_type:
                    content_settings = ContentSettings(content_type=content_type)
                
                # Upload file
                with open(local_file_path, 'rb') as data:
                    blob_client.upload_blob(
                        data, 
                        overwrite=overwrite,
                        content_settings=content_settings
                    )
                
                # Get file info
                file_size = os.path.getsize(local_file_path)
                
                logger.info(f"✅ Uploaded {blob_name} to {container_name} ({file_size} bytes)")
                
                return {
                    'success': True,
                    'container': container_name,
                    'blob_name': blob_name,
                    'blob_url': blob_client.url,
                    'file_size': file_size,
                    'uploaded_at': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to upload {local_file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'local_file_path': local_file_path,
                'container_type': container_type
            }
    
    def download_file(self, 
                     container_type: str, 
                     blob_name: str, 
                     local_file_path: str = None,
                     use_temp: bool = False) -> Dict[str, Any]:
        """
        Download file from Azure Blob Storage
        
        Args:
            container_type: Container type ('uploads', 'vector-db', etc.)
            blob_name: Name of blob to download
            local_file_path: Local path to save file (if None, uses temp)
            use_temp: Force use of temporary directory
            
        Returns:
            Dict with download results including local file path
        """
        try:
            if container_type not in self.containers:
                raise ValueError(f"Invalid container type: {container_type}")
            
            container_name = self.containers[container_type]
            
            # Generate local file path if not provided
            if local_file_path is None or use_temp:
                temp_subdir = os.path.join(self.temp_dir, container_type)
                os.makedirs(temp_subdir, exist_ok=True)
                local_file_path = os.path.join(temp_subdir, blob_name)
            
            with self._locks[container_type]:
                # Get blob client
                blob_client = self.blob_service_client.get_blob_client(
                    container=container_name, 
                    blob=blob_name
                )
                
                # Ensure local directory exists
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                
                # Download file
                with open(local_file_path, 'wb') as download_file:
                    download_data = blob_client.download_blob()
                    download_file.write(download_data.readall())
                
                file_size = os.path.getsize(local_file_path)
                
                logger.info(f"✅ Downloaded {blob_name} from {container_name} to {local_file_path}")
                
                return {
                    'success': True,
                    'container': container_name,
                    'blob_name': blob_name,
                    'local_file_path': local_file_path,
                    'file_size': file_size,
                    'downloaded_at': datetime.utcnow().isoformat()
                }
                
        except ResourceNotFoundError:
            error_msg = f"Blob not found: {blob_name} in {container_type}"
            logger.warning(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'blob_name': blob_name,
                'container_type': container_type
            }
        except Exception as e:
            logger.error(f"❌ Failed to download {blob_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'blob_name': blob_name,
                'container_type': container_type
            }
    
    def list_blobs(self, 
                   container_type: str, 
                   name_starts_with: str = None,
                   include_metadata: bool = False) -> Dict[str, Any]:
        """
        List blobs in container
        
        Args:
            container_type: Container type ('uploads', 'vector-db', etc.)
            name_starts_with: Filter blobs by name prefix
            include_metadata: Include blob metadata
            
        Returns:
            Dict with blob list
        """
        try:
            if container_type not in self.containers:
                raise ValueError(f"Invalid container type: {container_type}")
            
            container_name = self.containers[container_type]
            
            container_client = self.blob_service_client.get_container_client(container_name)
            
            blobs = []
            blob_iter = container_client.list_blobs(
                name_starts_with=name_starts_with,
                include=['metadata'] if include_metadata else None
            )
            
            for blob in blob_iter:
                blob_info = {
                    'name': blob.name,
                    'size': blob.size,
                    'last_modified': blob.last_modified.isoformat() if blob.last_modified else None,
                    'content_type': blob.content_settings.content_type if blob.content_settings else None
                }
                
                if include_metadata and hasattr(blob, 'metadata'):
                    blob_info['metadata'] = blob.metadata
                
                blobs.append(blob_info)
            
            logger.info(f"✅ Listed {len(blobs)} blobs from {container_name}")
            
            return {
                'success': True,
                'container': container_name,
                'blobs': blobs,
                'count': len(blobs)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to list blobs in {container_type}: {e}")
            return {
                'success': False,
                'error': str(e),
                'container_type': container_type
            }
    
    def delete_blob(self, container_type: str, blob_name: str) -> Dict[str, Any]:
        """
        Delete blob from Azure Blob Storage
        
        Args:
            container_type: Container type ('uploads', 'vector-db', etc.)
            blob_name: Name of blob to delete
            
        Returns:
            Dict with deletion results
        """
        try:
            if container_type not in self.containers:
                raise ValueError(f"Invalid container type: {container_type}")
            
            container_name = self.containers[container_type]
            
            with self._locks[container_type]:
                blob_client = self.blob_service_client.get_blob_client(
                    container=container_name, 
                    blob=blob_name
                )
                
                blob_client.delete_blob()
                
                logger.info(f"✅ Deleted {blob_name} from {container_name}")
                
                return {
                    'success': True,
                    'container': container_name,
                    'blob_name': blob_name,
                    'deleted_at': datetime.utcnow().isoformat()
                }
                
        except ResourceNotFoundError:
            error_msg = f"Blob not found for deletion: {blob_name}"
            logger.warning(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'blob_name': blob_name,
                'container_type': container_type
            }
        except Exception as e:
            logger.error(f"❌ Failed to delete {blob_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'blob_name': blob_name,
                'container_type': container_type
            }
    
    def sync_vector_db_to_blob(self, local_vector_db_path: str) -> Dict[str, Any]:
        """
        Sync local ChromaDB vector database to Azure Blob Storage
        
        Args:
            local_vector_db_path: Path to local vector database directory
            
        Returns:
            Dict with sync results
        """
        try:
            if not os.path.exists(local_vector_db_path):
                return {
                    'success': False,
                    'error': f'Vector DB path not found: {local_vector_db_path}'
                }
            
            logger.info(f"🔄 Syncing vector DB to blob storage: {local_vector_db_path}")
            
            # Create zip archive of vector database
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for root, dirs, files in os.walk(local_vector_db_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, local_vector_db_path)
                        zip_file.write(file_path, arc_name)
            
            # Upload zip to blob storage
            zip_buffer.seek(0)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            blob_name = f"vector_db_backup_{timestamp}.zip"
            
            container_name = self.containers['vector-db']
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            blob_client.upload_blob(
                zip_buffer.getvalue(), 
                overwrite=True,
                content_settings=ContentSettings(content_type='application/zip')
            )
            
            # Also upload as "latest" for easy access
            latest_blob_name = "vector_db_latest.zip"
            latest_blob_client = self.blob_service_client.get_blob_client(
                container=container_name, 
                blob=latest_blob_name
            )
            zip_buffer.seek(0)
            latest_blob_client.upload_blob(
                zip_buffer.getvalue(), 
                overwrite=True,
                content_settings=ContentSettings(content_type='application/zip')
            )
            
            logger.info(f"✅ Vector DB synced to blob storage as {blob_name}")
            
            return {
                'success': True,
                'container': container_name,
                'blob_name': blob_name,
                'latest_blob_name': latest_blob_name,
                'sync_timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to sync vector DB to blob: {e}")
            return {
                'success': False,
                'error': str(e),
                'local_vector_db_path': local_vector_db_path
            }
    
    def restore_vector_db_from_blob(self, local_vector_db_path: str, use_latest: bool = True) -> Dict[str, Any]:
        """
        Restore ChromaDB vector database from Azure Blob Storage
        
        Args:
            local_vector_db_path: Path where to restore vector database
            use_latest: Use latest backup or list all available
            
        Returns:
            Dict with restore results
        """
        try:
            container_name = self.containers['vector-db']
            
            # Determine which backup to restore
            blob_name = "vector_db_latest.zip" if use_latest else None
            
            if not blob_name:
                # List available backups
                blob_list = self.list_blobs('vector-db', name_starts_with='vector_db_backup_')
                if not blob_list['success'] or not blob_list['blobs']:
                    return {
                        'success': False,
                        'error': 'No vector DB backups found in blob storage'
                    }
                
                # Use most recent backup
                blob_name = sorted(blob_list['blobs'], key=lambda x: x['last_modified'])[-1]['name']
            
            logger.info(f"🔄 Restoring vector DB from blob: {blob_name}")
            
            # Download and extract
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            # Download blob data
            download_data = blob_client.download_blob()
            zip_buffer = io.BytesIO(download_data.readall())
            
            # Ensure target directory exists
            os.makedirs(local_vector_db_path, exist_ok=True)
            
            # Extract zip archive
            with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                zip_file.extractall(local_vector_db_path)
            
            logger.info(f"✅ Vector DB restored to {local_vector_db_path}")
            
            return {
                'success': True,
                'container': container_name,
                'blob_name': blob_name,
                'local_vector_db_path': local_vector_db_path,
                'restored_at': datetime.utcnow().isoformat()
            }
            
        except ResourceNotFoundError:
            logger.warning("Vector DB backup not found in blob storage, starting fresh")
            return {
                'success': True,
                'fresh_start': True,
                'message': 'No backup found, starting with fresh vector database'
            }
        except Exception as e:
            logger.error(f"❌ Failed to restore vector DB from blob: {e}")
            return {
                'success': False,
                'error': str(e),
                'local_vector_db_path': local_vector_db_path
            }
    
    def get_temp_file_path(self, container_type: str, filename: str) -> str:
        """
        Get temporary file path for local processing
        
        Args:
            container_type: Container type for organization
            filename: Name of the file
            
        Returns:
            Full path to temporary file
        """
        temp_subdir = os.path.join(self.temp_dir, container_type)
        os.makedirs(temp_subdir, exist_ok=True)
        return os.path.join(temp_subdir, filename)
    
    def cleanup_temp_files(self, older_than_hours: int = 24):
        """
        Clean up temporary files older than specified hours
        
        Args:
            older_than_hours: Remove files older than this many hours
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        logger.debug(f"Removed old temp file: {file_path}")
            
            logger.info(f"✅ Cleaned up temp files older than {older_than_hours} hours")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup temp files: {e}")
    
    def __del__(self):
        """Cleanup temporary directory on destruction"""
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.info(f"✅ Cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Failed to cleanup temp directory: {e}")

# Global instance
_blob_storage_manager = None

def get_blob_storage_manager() -> AzureBlobStorageManager:
    """Get or create global blob storage manager instance"""
    global _blob_storage_manager
    if _blob_storage_manager is None:
        _blob_storage_manager = AzureBlobStorageManager()
    return _blob_storage_manager

def init_blob_storage() -> Dict[str, Any]:
    """
    Initialize blob storage system and test connectivity
    
    Returns:
        Dict with initialization results
    """
    try:
        logger.info("🚀 Initializing Azure Blob Storage system...")
        
        blob_manager = get_blob_storage_manager()
        
        # Test connectivity by listing uploads container
        test_result = blob_manager.list_blobs('uploads')
        
        if test_result['success']:
            logger.info("✅ Azure Blob Storage system initialized successfully")
            return {
                'success': True,
                'message': 'Azure Blob Storage initialized successfully',
                'containers': list(blob_manager.containers.keys()),
                'temp_dir': blob_manager.temp_dir
            }
        else:
            raise Exception(f"Connectivity test failed: {test_result['error']}")
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize Azure Blob Storage: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to initialize Azure Blob Storage'
        }