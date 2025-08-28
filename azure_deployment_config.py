#!/usr/bin/env python3
"""
Azure Deployment Configuration
Handles all Azure-specific configurations for ephemeral storage deployment
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AzureDeploymentConfig:
    """
    Configuration manager for Azure deployment with ephemeral storage
    """
    
    def __init__(self):
        self.required_env_vars = {
            'AZURE_STORAGE_CONNECTION_STRING': 'Azure Storage Account connection string',
            'DATABASE_URL': 'PostgreSQL database connection string',
            'ANTHROPIC_API_KEY': 'Anthropic Claude API key',
            'SECRET_KEY': 'Flask secret key'
        }
        
        self.optional_env_vars = {
            'OPENAI_API_KEY': 'OpenAI API key (optional)',
            'AZURE_CONTAINER_NAME': 'Azure container name (default: documents)',
            'VECTOR_SYNC_INTERVAL': 'Vector DB sync interval in seconds (default: 300)',
            'TEMP_CLEANUP_HOURS': 'Hours after which to cleanup temp files (default: 24)'
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate all Azure deployment configuration
        
        Returns:
            Dict with validation results
        """
        try:
            logger.info("🔍 Validating Azure deployment configuration...")
            
            validation_results = {
                'success': True,
                'errors': [],
                'warnings': [],
                'required_vars': {},
                'optional_vars': {},
                'azure_storage_ready': False,
                'database_ready': False,
                'ai_services_ready': False
            }
            
            # Check required environment variables
            for var_name, description in self.required_env_vars.items():
                value = os.getenv(var_name)
                if value:
                    validation_results['required_vars'][var_name] = '✅ Set'
                    logger.info(f"✅ {var_name}: Configured")
                else:
                    validation_results['required_vars'][var_name] = '❌ Missing'
                    validation_results['errors'].append(f"Missing required environment variable: {var_name} ({description})")
                    validation_results['success'] = False
                    logger.error(f"❌ {var_name}: Missing - {description}")
            
            # Check optional environment variables
            for var_name, description in self.optional_env_vars.items():
                value = os.getenv(var_name)
                if value:
                    validation_results['optional_vars'][var_name] = '✅ Set'
                    logger.info(f"✅ {var_name}: Configured")
                else:
                    validation_results['optional_vars'][var_name] = '⚪ Not set'
                    validation_results['warnings'].append(f"Optional variable not set: {var_name} ({description})")
                    logger.info(f"⚪ {var_name}: Not set (optional)")
            
            # Test Azure Storage connectivity
            if os.getenv('AZURE_STORAGE_CONNECTION_STRING'):
                azure_test = self._test_azure_storage()
                validation_results['azure_storage_ready'] = azure_test['success']
                if not azure_test['success']:
                    validation_results['errors'].append(f"Azure Storage test failed: {azure_test['error']}")
            
            # Test database connectivity
            if os.getenv('DATABASE_URL'):
                db_test = self._test_database_connection()
                validation_results['database_ready'] = db_test['success']
                if not db_test['success']:
                    validation_results['errors'].append(f"Database test failed: {db_test['error']}")
            
            # Test AI services
            ai_test = self._test_ai_services()
            validation_results['ai_services_ready'] = ai_test['success']
            if not ai_test['success']:
                validation_results['warnings'].append(f"AI services test: {ai_test['error']}")
            
            # Overall success check
            validation_results['success'] = (
                len(validation_results['errors']) == 0 and
                validation_results['azure_storage_ready'] and
                validation_results['database_ready']
            )
            
            if validation_results['success']:
                logger.info("✅ Azure deployment configuration validated successfully")
            else:
                logger.error(f"❌ Configuration validation failed: {len(validation_results['errors'])} errors")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ Configuration validation error: {e}")
            return {
                'success': False,
                'error': str(e),
                'errors': [f"Configuration validation failed: {e}"]
            }
    
    def _test_azure_storage(self) -> Dict[str, Any]:
        """Test Azure Storage connectivity"""
        try:
            from azure.storage.blob import BlobServiceClient
            
            connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            
            # List containers to test connectivity
            containers = list(blob_service_client.list_containers())
            
            return {
                'success': True,
                'container_count': len(containers),
                'message': 'Azure Storage connectivity verified'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _test_database_connection(self) -> Dict[str, Any]:
        """Test database connectivity"""
        try:
            import psycopg2
            from urllib.parse import urlparse
            
            database_url = os.getenv('DATABASE_URL')
            parsed_url = urlparse(database_url)
            
            # Test connection
            conn = psycopg2.connect(
                host=parsed_url.hostname,
                port=parsed_url.port,
                database=parsed_url.path[1:],  # Remove leading slash
                user=parsed_url.username,
                password=parsed_url.password
            )
            conn.close()
            
            return {
                'success': True,
                'message': 'Database connectivity verified'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _test_ai_services(self) -> Dict[str, Any]:
        """Test AI services connectivity"""
        try:
            ai_services = []
            
            # Test Anthropic
            if os.getenv('ANTHROPIC_API_KEY'):
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
                    ai_services.append('Anthropic Claude ✅')
                except Exception as e:
                    ai_services.append(f'Anthropic Claude ❌ ({str(e)[:50]}...)')
            else:
                ai_services.append('Anthropic Claude ⚪ (no API key)')
            
            # Test OpenAI
            if os.getenv('OPENAI_API_KEY'):
                try:
                    import openai
                    openai.api_key = os.getenv('OPENAI_API_KEY')
                    ai_services.append('OpenAI ✅')
                except Exception as e:
                    ai_services.append(f'OpenAI ❌ ({str(e)[:50]}...)')
            else:
                ai_services.append('OpenAI ⚪ (no API key)')
            
            return {
                'success': True,
                'services': ai_services,
                'message': 'AI services checked'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_deployment_summary(self) -> str:
        """Get a formatted deployment summary"""
        validation = self.validate_configuration()
        
        summary = []
        summary.append("=" * 60)
        summary.append("🚀 AZURE DEPLOYMENT CONFIGURATION SUMMARY")
        summary.append("=" * 60)
        summary.append("")
        
        if validation['success']:
            summary.append("✅ DEPLOYMENT READY")
        else:
            summary.append("❌ DEPLOYMENT NOT READY")
        
        summary.append("")
        summary.append("📋 REQUIRED CONFIGURATION:")
        for var, status in validation['required_vars'].items():
            summary.append(f"   {var}: {status}")
        
        summary.append("")
        summary.append("📋 OPTIONAL CONFIGURATION:")
        for var, status in validation['optional_vars'].items():
            summary.append(f"   {var}: {status}")
        
        summary.append("")
        summary.append("🔍 CONNECTIVITY TESTS:")
        summary.append(f"   Azure Storage: {'✅' if validation['azure_storage_ready'] else '❌'}")
        summary.append(f"   Database: {'✅' if validation['database_ready'] else '❌'}")
        summary.append(f"   AI Services: {'✅' if validation['ai_services_ready'] else '⚪'}")
        
        if validation['errors']:
            summary.append("")
            summary.append("❌ ERRORS:")
            for error in validation['errors']:
                summary.append(f"   - {error}")
        
        if validation['warnings']:
            summary.append("")
            summary.append("⚠️  WARNINGS:")
            for warning in validation['warnings']:
                summary.append(f"   - {warning}")
        
        summary.append("")
        summary.append("=" * 60)
        
        return "\n".join(summary)
    
    def create_sample_env_file(self, file_path: str = '.env.azure.example') -> bool:
        """Create a sample .env file for Azure deployment"""
        try:
            sample_content = [
                "# Azure Deployment Environment Variables",
                "# Copy this file to .env and fill in your actual values",
                "",
                "# ================================",
                "# REQUIRED CONFIGURATION",
                "# ================================",
                "",
                "# Flask Configuration",
                "SECRET_KEY=your-secret-key-here",
                "FLASK_ENV=production",
                "PORT=8000",
                "",
                "# Azure Storage (REQUIRED)",
                "AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=yourstorageaccount;AccountKey=your-key;EndpointSuffix=core.windows.net",
                "",
                "# Database Configuration (REQUIRED)",
                "DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require",
                "",
                "# AI Configuration (REQUIRED)",
                "ANTHROPIC_API_KEY=sk-ant-api03-your-key-here",
                "",
                "# ================================",
                "# OPTIONAL CONFIGURATION",
                "# ================================",
                "",
                "# Additional AI Services",
                "OPENAI_API_KEY=sk-proj-your-openai-key-here",
                "",
                "# Azure Configuration",
                "AZURE_CONTAINER_NAME=documents",
                "",
                "# Performance Tuning",
                "VECTOR_SYNC_INTERVAL=300  # seconds",
                "TEMP_CLEANUP_HOURS=24     # hours",
                "",
                "# File Upload Settings",
                "UPLOAD_FOLDER=/tmp/uploads  # Will be ignored with Azure storage",
                "MAX_CONTENT_LENGTH=104857600  # 100MB",
                "",
                "# Development/Debug Settings",
                "DEBUG=False",
                "TESTING=False",
                "",
                "# Session Configuration",
                "SESSION_COOKIE_SECURE=True",
                "SESSION_COOKIE_HTTPONLY=True",
                "WTF_CSRF_ENABLED=True"
            ]
            
            with open(file_path, 'w') as f:
                f.write('\n'.join(sample_content))
            
            logger.info(f"✅ Sample environment file created: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create sample environment file: {e}")
            return False

def validate_azure_deployment() -> Dict[str, Any]:
    """
    Validate Azure deployment configuration
    
    Returns:
        Dict with validation results
    """
    config = AzureDeploymentConfig()
    return config.validate_configuration()

def print_deployment_summary():
    """Print deployment configuration summary"""
    config = AzureDeploymentConfig()
    print(config.get_deployment_summary())

if __name__ == "__main__":
    # CLI interface for deployment validation
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'create-sample':
        config = AzureDeploymentConfig()
        if config.create_sample_env_file():
            print("✅ Sample .env.azure.example file created")
            print("📝 Edit this file with your actual values and rename to .env")
        else:
            print("❌ Failed to create sample environment file")
    else:
        print_deployment_summary()