#!/usr/bin/env python3
"""
Azure File Manager
Provides transparent file operations with Azure Blob Storage
Replaces local file operations for ephemeral deployments
"""

import os
import logging
from typing import Dict, Any, Optional, BinaryIO
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

from azure_blob_storage_manager import get_blob_storage_manager

logger = logging.getLogger(__name__)

class AzureFileManager:
    """
    File manager that transparently handles Azure Blob Storage operations
    Maintains compatibility with existing Flask file upload patterns
    """
    
    def __init__(self):
        self.blob_manager = get_blob_storage_manager()
    
    def save_uploaded_file(self, 
                          file: FileStorage, 
                          container_type: str = 'uploads',
                          custom_filename: str = None,
                          add_timestamp: bool = True,
                          add_uuid: bool = True) -> Dict[str, Any]:
        """
        Save uploaded file to Azure Blob Storage
        
        Args:
            file: Werkzeug FileStorage object from Flask request
            container_type: Container type ('uploads', 'templates', etc.)
            custom_filename: Custom filename (if None, uses original)
            add_timestamp: Add timestamp to filename
            add_uuid: Add UUID to filename for uniqueness
            
        Returns:
            Dict with file save results including blob info
        """
        try:
            if not file or file.filename == '':
                return {
                    'success': False,
                    'error': 'No file provided or empty filename'
                }
            
            # Generate secure filename
            original_filename = secure_filename(file.filename)
            base_name, extension = os.path.splitext(original_filename)
            
            # Build filename with optional components
            filename_parts = []
            
            if add_uuid:
                filename_parts.append(str(uuid.uuid4())[:8])
            
            if add_timestamp:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename_parts.append(timestamp)
            
            if custom_filename:
                filename_parts.append(secure_filename(custom_filename))
            else:
                filename_parts.append(base_name)
            
            # Construct final filename
            final_filename = '_'.join(filename_parts) + extension
            
            # Save to temporary file first
            temp_file_path = self.blob_manager.get_temp_file_path(container_type, final_filename)
            file.save(temp_file_path)
            
            # Get file info
            file_size = os.path.getsize(temp_file_path)
            content_type = file.content_type or 'application/octet-stream'
            
            # Upload to blob storage
            upload_result = self.blob_manager.upload_file(
                local_file_path=temp_file_path,
                container_type=container_type,
                blob_name=final_filename,
                overwrite=True,
                content_type=content_type
            )
            
            if upload_result['success']:
                logger.info(f"✅ File uploaded successfully: {final_filename} ({file_size} bytes)")
                
                return {
                    'success': True,
                    'original_filename': original_filename,
                    'saved_filename': final_filename,
                    'blob_name': final_filename,
                    'container_type': container_type,
                    'file_size': file_size,
                    'content_type': content_type,
                    'blob_url': upload_result['blob_url'],
                    'local_temp_path': temp_file_path,  # For immediate processing
                    'uploaded_at': upload_result['uploaded_at']
                }
            else:
                # Clean up temp file on failure
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                
                return {
                    'success': False,
                    'error': f"Upload to blob storage failed: {upload_result['error']}",
                    'original_filename': original_filename
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to save uploaded file: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_filename': file.filename if file else 'unknown'
            }
    
    def get_file_for_processing(self, 
                               container_type: str, 
                               blob_name: str,
                               keep_local: bool = False) -> Dict[str, Any]:
        """
        Download file from blob storage for local processing
        
        Args:
            container_type: Container type ('uploads', 'templates', etc.)
            blob_name: Name of blob to download
            keep_local: Keep local copy after processing
            
        Returns:
            Dict with local file path and metadata
        """
        try:
            download_result = self.blob_manager.download_file(
                container_type=container_type,
                blob_name=blob_name,
                use_temp=True
            )
            
            if download_result['success']:
                local_path = download_result['local_file_path']
                
                # Set cleanup if not keeping local
                cleanup_path = None if keep_local else local_path
                
                return {
                    'success': True,
                    'local_file_path': local_path,
                    'blob_name': blob_name,
                    'container_type': container_type,
                    'file_size': download_result['file_size'],
                    'cleanup_path': cleanup_path
                }
            else:
                return download_result
                
        except Exception as e:
            logger.error(f"❌ Failed to get file for processing: {e}")
            return {
                'success': False,
                'error': str(e),
                'blob_name': blob_name,
                'container_type': container_type
            }
    
    def cleanup_local_file(self, file_path: str):
        """Clean up local temporary file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up local file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup local file {file_path}: {e}")
    
    def save_generated_file(self, 
                           local_file_path: str, 
                           filename: str,
                           container_type: str = 'generated',
                           content_type: str = None) -> Dict[str, Any]:
        """
        Save generated file (proposals, reports) to blob storage
        
        Args:
            local_file_path: Path to local generated file
            filename: Desired filename in blob storage
            container_type: Container type (default: 'generated')
            content_type: MIME type
            
        Returns:
            Dict with save results
        """
        try:
            if not os.path.exists(local_file_path):
                return {
                    'success': False,
                    'error': f'Local file not found: {local_file_path}'
                }
            
            # Add timestamp to filename for uniqueness
            base_name, extension = os.path.splitext(filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            final_filename = f"{base_name}_{timestamp}{extension}"
            
            # Upload to blob storage
            upload_result = self.blob_manager.upload_file(
                local_file_path=local_file_path,
                container_type=container_type,
                blob_name=final_filename,
                overwrite=True,
                content_type=content_type
            )
            
            if upload_result['success']:
                logger.info(f"✅ Generated file saved: {final_filename}")
                
                return {
                    'success': True,
                    'filename': final_filename,
                    'blob_url': upload_result['blob_url'],
                    'container_type': container_type,
                    'file_size': upload_result['file_size']
                }
            else:
                return upload_result
                
        except Exception as e:
            logger.error(f"❌ Failed to save generated file: {e}")
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }
    
    def get_file_url(self, container_type: str, blob_name: str) -> str:
        """
        Get public URL for a blob (if container allows public access)
        
        Args:
            container_type: Container type
            blob_name: Blob name
            
        Returns:
            Blob URL string
        """
        try:
            container_name = self.blob_manager.containers[container_type]
            blob_client = self.blob_manager.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            return blob_client.url
        except Exception as e:
            logger.error(f"❌ Failed to get file URL: {e}")
            return ""
    
    def delete_file(self, container_type: str, blob_name: str) -> Dict[str, Any]:
        """
        Delete file from blob storage
        
        Args:
            container_type: Container type
            blob_name: Blob name to delete
            
        Returns:
            Dict with deletion results
        """
        return self.blob_manager.delete_blob(container_type, blob_name)
    
    def list_files(self, 
                   container_type: str, 
                   prefix: str = None,
                   include_metadata: bool = False) -> Dict[str, Any]:
        """
        List files in container
        
        Args:
            container_type: Container type
            prefix: Filter by filename prefix
            include_metadata: Include file metadata
            
        Returns:
            Dict with file list
        """
        return self.blob_manager.list_blobs(
            container_type=container_type,
            name_starts_with=prefix,
            include_metadata=include_metadata
        )
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics across all containers"""
        try:
            stats = {
                'containers': {},
                'total_files': 0,
                'total_size': 0
            }
            
            for container_type in self.blob_manager.containers.keys():
                container_stats = self.list_files(container_type)
                
                if container_stats['success']:
                    files = container_stats['blobs']
                    container_size = sum(file['size'] for file in files)
                    
                    stats['containers'][container_type] = {
                        'file_count': len(files),
                        'total_size': container_size,
                        'container_name': self.blob_manager.containers[container_type]
                    }
                    
                    stats['total_files'] += len(files)
                    stats['total_size'] += container_size
            
            return {
                'success': True,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get storage stats: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
_azure_file_manager = None

def get_azure_file_manager() -> AzureFileManager:
    """Get or create global Azure File Manager instance"""
    global _azure_file_manager
    if _azure_file_manager is None:
        _azure_file_manager = AzureFileManager()
    return _azure_file_manager

def init_azure_file_system() -> Dict[str, Any]:
    """
    Initialize Azure File System
    
    Returns:
        Dict with initialization results
    """
    try:
        logger.info("🚀 Initializing Azure File System...")
        
        file_manager = get_azure_file_manager()
        
        # Get storage stats to verify connectivity
        stats_result = file_manager.get_storage_stats()
        
        if stats_result['success']:
            stats = stats_result['stats']
            logger.info(f"✅ Azure File System initialized - {stats['total_files']} files across {len(stats['containers'])} containers")
            
            return {
                'success': True,
                'message': 'Azure File System initialized successfully',
                'storage_stats': stats
            }
        else:
            return {
                'success': False,
                'error': stats_result['error']
            }
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize Azure File System: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to initialize Azure File System'
        }