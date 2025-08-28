#!/usr/bin/env python3
"""
Azure Vector Database Manager
Manages ChromaDB persistence with Azure Blob Storage for ephemeral deployments
"""

import os
import logging
import tempfile
import atexit
import threading
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from azure_blob_storage_manager import get_blob_storage_manager

logger = logging.getLogger(__name__)

class AzureVectorDBManager:
    """
    ChromaDB Manager with Azure Blob Storage persistence
    Handles automatic sync, backup, and restore operations
    """
    
    def __init__(self, auto_sync_interval: int = 300):
        """
        Initialize Azure Vector DB Manager
        
        Args:
            auto_sync_interval: Auto-sync interval in seconds (default: 5 minutes)
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB not available. Install with: pip install chromadb")
        
        self.blob_manager = get_blob_storage_manager()
        self.auto_sync_interval = auto_sync_interval
        
        # Local vector database path (temporary)
        self.local_vector_db_path = os.path.join(
            self.blob_manager.temp_dir, 
            'vector_db'
        )
        
        # ChromaDB client
        self.chroma_client = None
        
        # Auto-sync control
        self._sync_thread = None
        self._stop_sync = threading.Event()
        self._last_sync = None
        self._sync_lock = threading.Lock()
        
        # Initialize
        self._init_vector_db()
        self._start_auto_sync()
        
        # Register cleanup on exit
        atexit.register(self._cleanup_on_exit)
        
        logger.info(f"Azure Vector DB Manager initialized with local path: {self.local_vector_db_path}")
    
    def _init_vector_db(self):
        """Initialize ChromaDB with Azure Blob Storage restore"""
        try:
            logger.info("🔄 Initializing ChromaDB with Azure Blob Storage...")
            
            # Ensure local directory exists
            os.makedirs(self.local_vector_db_path, exist_ok=True)
            
            # Try to restore from Azure Blob Storage
            restore_result = self.blob_manager.restore_vector_db_from_blob(
                self.local_vector_db_path, 
                use_latest=True
            )
            
            if restore_result['success']:
                if restore_result.get('fresh_start'):
                    logger.info("📦 Starting with fresh vector database")
                else:
                    logger.info(f"✅ Restored vector database from Azure Blob Storage")
            else:
                logger.warning(f"⚠️ Could not restore vector DB: {restore_result['error']}")
            
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path=self.local_vector_db_path,
                settings=Settings(
                    allow_reset=True,
                    anonymized_telemetry=False
                )
            )
            
            logger.info("✅ ChromaDB client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize vector DB: {e}")
            raise
    
    def get_client(self) -> chromadb.PersistentClient:
        """Get ChromaDB client"""
        if self.chroma_client is None:
            self._init_vector_db()
        return self.chroma_client
    
    def get_or_create_collection(self, name: str, **kwargs) -> chromadb.Collection:
        """
        Get or create a ChromaDB collection
        
        Args:
            name: Collection name
            **kwargs: Additional arguments for collection creation
            
        Returns:
            ChromaDB Collection object
        """
        try:
            client = self.get_client()
            collection = client.get_or_create_collection(name=name, **kwargs)
            logger.info(f"✅ Got/created collection: {name}")
            return collection
        except Exception as e:
            logger.error(f"❌ Failed to get/create collection {name}: {e}")
            raise
    
    def sync_to_blob_storage(self, force: bool = False) -> Dict[str, Any]:
        """
        Sync local vector database to Azure Blob Storage
        
        Args:
            force: Force sync even if recently synced
            
        Returns:
            Dict with sync results
        """
        with self._sync_lock:
            try:
                # Check if sync is needed
                if not force and self._last_sync:
                    time_since_sync = datetime.utcnow() - self._last_sync
                    if time_since_sync.total_seconds() < 60:  # Don't sync more than once per minute
                        return {
                            'success': True,
                            'skipped': True,
                            'message': 'Sync skipped - too recent'
                        }
                
                logger.info("🔄 Syncing vector database to Azure Blob Storage...")
                
                # Perform sync
                sync_result = self.blob_manager.sync_vector_db_to_blob(self.local_vector_db_path)
                
                if sync_result['success']:
                    self._last_sync = datetime.utcnow()
                    logger.info(f"✅ Vector DB synced successfully: {sync_result['blob_name']}")
                else:
                    logger.error(f"❌ Vector DB sync failed: {sync_result['error']}")
                
                return sync_result
                
            except Exception as e:
                logger.error(f"❌ Unexpected error during sync: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    def restore_from_blob_storage(self, backup_name: str = None) -> Dict[str, Any]:
        """
        Restore vector database from Azure Blob Storage
        
        Args:
            backup_name: Specific backup to restore (None for latest)
            
        Returns:
            Dict with restore results
        """
        try:
            logger.info("🔄 Restoring vector database from Azure Blob Storage...")
            
            # Stop auto-sync during restore
            was_syncing = not self._stop_sync.is_set()
            if was_syncing:
                self._stop_auto_sync()
            
            # Close current client
            if self.chroma_client:
                del self.chroma_client
                self.chroma_client = None
            
            # Restore from blob
            restore_result = self.blob_manager.restore_vector_db_from_blob(
                self.local_vector_db_path, 
                use_latest=(backup_name is None)
            )
            
            if restore_result['success']:
                # Reinitialize client
                self._init_vector_db()
                
                # Restart auto-sync if it was running
                if was_syncing:
                    self._start_auto_sync()
                
                logger.info("✅ Vector database restored successfully")
            else:
                logger.error(f"❌ Vector DB restore failed: {restore_result['error']}")
            
            return restore_result
            
        except Exception as e:
            logger.error(f"❌ Unexpected error during restore: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _start_auto_sync(self):
        """Start automatic sync thread"""
        if self._sync_thread is not None and self._sync_thread.is_alive():
            return
        
        self._stop_sync.clear()
        self._sync_thread = threading.Thread(target=self._auto_sync_worker, daemon=True)
        self._sync_thread.start()
        
        logger.info(f"🔄 Auto-sync started (interval: {self.auto_sync_interval}s)")
    
    def _stop_auto_sync(self):
        """Stop automatic sync thread"""
        self._stop_sync.set()
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=30)
        
        logger.info("⏹️ Auto-sync stopped")
    
    def _auto_sync_worker(self):
        """Auto-sync worker thread"""
        while not self._stop_sync.wait(self.auto_sync_interval):
            try:
                # Check if vector DB has data before syncing
                if os.path.exists(self.local_vector_db_path) and os.listdir(self.local_vector_db_path):
                    result = self.sync_to_blob_storage(force=False)
                    if result['success'] and not result.get('skipped'):
                        logger.debug("🔄 Auto-sync completed successfully")
                    elif not result['success']:
                        logger.warning(f"⚠️ Auto-sync failed: {result['error']}")
            except Exception as e:
                logger.error(f"❌ Auto-sync worker error: {e}")
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        return {
            'auto_sync_running': not self._stop_sync.is_set(),
            'auto_sync_interval': self.auto_sync_interval,
            'last_sync': self._last_sync.isoformat() if self._last_sync else None,
            'local_vector_db_path': self.local_vector_db_path,
            'vector_db_exists': os.path.exists(self.local_vector_db_path),
            'vector_db_size': self._get_directory_size(self.local_vector_db_path)
        }
    
    def _get_directory_size(self, path: str) -> int:
        """Get total size of directory in bytes"""
        try:
            if not os.path.exists(path):
                return 0
            
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            return total_size
        except Exception:
            return 0
    
    def force_backup_now(self, backup_name: str = None) -> Dict[str, Any]:
        """
        Force immediate backup to blob storage
        
        Args:
            backup_name: Custom backup name (optional)
            
        Returns:
            Dict with backup results
        """
        try:
            logger.info("🔄 Creating immediate backup...")
            
            result = self.sync_to_blob_storage(force=True)
            
            if result['success']:
                logger.info(f"✅ Immediate backup created: {result.get('blob_name')}")
            else:
                logger.error(f"❌ Immediate backup failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to create immediate backup: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_available_backups(self) -> Dict[str, Any]:
        """List all available backups in blob storage"""
        try:
            backups_result = self.blob_manager.list_blobs(
                'vector-db', 
                name_starts_with='vector_db_',
                include_metadata=True
            )
            
            if backups_result['success']:
                # Sort by last modified (newest first)
                backups = sorted(
                    backups_result['blobs'], 
                    key=lambda x: x['last_modified'], 
                    reverse=True
                )
                
                return {
                    'success': True,
                    'backups': backups,
                    'count': len(backups)
                }
            else:
                return backups_result
                
        except Exception as e:
            logger.error(f"❌ Failed to list backups: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _cleanup_on_exit(self):
        """Cleanup operations on exit"""
        try:
            logger.info("🧹 Cleaning up Azure Vector DB Manager...")
            
            # Stop auto-sync
            self._stop_auto_sync()
            
            # Final sync if there's data
            if (os.path.exists(self.local_vector_db_path) and 
                os.listdir(self.local_vector_db_path)):
                logger.info("🔄 Final sync to Azure Blob Storage...")
                sync_result = self.sync_to_blob_storage(force=True)
                if sync_result['success']:
                    logger.info("✅ Final sync completed")
                else:
                    logger.warning(f"⚠️ Final sync failed: {sync_result['error']}")
            
            # Close ChromaDB client
            if self.chroma_client:
                del self.chroma_client
                self.chroma_client = None
            
            logger.info("✅ Azure Vector DB Manager cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")

# Global instance
_azure_vector_db_manager = None

def get_azure_vector_db_manager() -> AzureVectorDBManager:
    """Get or create global Azure Vector DB Manager instance"""
    global _azure_vector_db_manager
    if _azure_vector_db_manager is None:
        _azure_vector_db_manager = AzureVectorDBManager()
    return _azure_vector_db_manager

def init_azure_vector_db() -> Dict[str, Any]:
    """
    Initialize Azure Vector DB system
    
    Returns:
        Dict with initialization results
    """
    try:
        logger.info("🚀 Initializing Azure Vector Database system...")
        
        vector_db_manager = get_azure_vector_db_manager()
        
        # Test ChromaDB connectivity
        client = vector_db_manager.get_client()
        collections = client.list_collections()
        
        sync_status = vector_db_manager.get_sync_status()
        
        logger.info("✅ Azure Vector Database system initialized successfully")
        
        return {
            'success': True,
            'message': 'Azure Vector Database initialized successfully',
            'collections_count': len(collections),
            'sync_status': sync_status,
            'local_path': vector_db_manager.local_vector_db_path
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Azure Vector Database: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to initialize Azure Vector Database'
        }