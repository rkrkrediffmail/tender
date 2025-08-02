#!/bin/bash
# Azure Deployment Quick Start Script
# Run this script to prepare your project for Azure deployment

echo "🚀 Setting up Tender Analysis System for Azure deployment..."

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p agents logs migrations/versions tests static/uploads

# Create empty __init__.py files
touch agents/__init__.py
touch migrations/__init__.py
touch tests/__init__.py

# Create Azure-specific environment file
echo "📝 Creating environment configuration..."
cat > .env.example << 'EOF'
# Azure App Service Environment Variables
# Copy these to Azure App Service Configuration

# Flask Configuration
SECRET_KEY=your-super-secret-key-change-in-production
FLASK_ENV=production
PORT=8000

# Azure PostgreSQL Database
DATABASE_URL=postgresql://username%40servername:password@servername.postgres.database.azure.com:5432/tender_system?sslmode=require

# AI API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=yourstorageaccount;AccountKey=your-key;EndpointSuffix=core.windows.net
AZURE_CONTAINER_NAME=documents

# Optional: Azure Redis Cache
REDIS_URL=rediss://your-redis.redis.cache.windows.net:6380

# Optional: Application Insights
APPINSIGHTS_INSTRUMENTATIONKEY=your-app-insights-key

# File Upload Settings
UPLOAD_FOLDER=/tmp/uploads
MAX_CONTENT_LENGTH=104857600
EOF

# Create requirements.txt with Azure optimizations
echo "📦 Creating requirements.txt..."
cat > requirements.txt << 'EOF'
# Core Flask framework
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Flask-WTF==1.1.1
Flask-Migrate==4.0.5
Flask-CORS==4.0.0
WTForms==3.0.1
Jinja2==3.1.2

# WSGI server for production
gunicorn==21.2.0

# Database drivers
psycopg2-binary==2.9.7
SQLAlchemy==2.0.23

# AI APIs
anthropic==0.7.7
openai==1.3.5

# Document processing
PyPDF2==3.0.1
python-docx==0.8.11
pytesseract==0.3.10
Pillow==10.0.1
openpyxl==3.1.2
python-magic==0.4.27

# Security and authentication
Werkzeug==2.3.7
bcrypt==4.0.1
cryptography==41.0.7
PyJWT==2.8.0

# HTTP requests and utilities
requests==2.31.0
urllib3==2.0.7
python-dateutil==2.8.2
python-dotenv==1.0.0

# File handling
filetype==1.2.0

# Azure integration
azure-identity==1.15.0
azure-storage-blob==12.19.0
azure-keyvault-secrets==4.7.0

# Caching and background tasks
redis==5.0.1
celery==5.3.4
flask-caching==2.1.0

# Monitoring and health checks
flask-healthz==0.0.3
flask-limiter==3.5.0

# Input validation
marshmallow==3.20.1

# Development and testing
pytest==7.4.3
pytest-flask==1.3.0
EOF

# Create the complete Dockerfile
echo "🐳 Creating Dockerfile..."
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    g++ \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ara \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    poppler-utils \
    libmagic1 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads logs /tmp/uploads

# Set permissions
RUN chmod +x *.py

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port for Azure App Service
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--keep-alive", "2", "main:app"]
EOF

# Create GitHub Actions workflow
echo "⚙️ Creating GitHub Actions workflow..."
mkdir -p .github/workflows
cat > .github/workflows/azure-deploy.yml << 'EOF'
name: Deploy to Azure App Service

on:
  push:
    branches: [ main ]
  workflow_dispatch:

env:
  AZURE_WEBAPP_NAME: 'tender-analysis-system'
  PYTHON_VERSION: '3.11'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python ${{ env.PYTHON_VERSION }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Create and activate virtual environment
      run: |
        python -m venv venv
        source venv/bin/activate
        pip install --upgrade pip

    - name: Install dependencies
      run: |
        source venv/bin/activate
        pip install -r requirements.txt

    - name: Run basic tests
      run: |
        source venv/bin/activate
        python -c "import flask; print('Flask import successful')"
        python -c "import anthropic; print('Anthropic import successful')" || true
        python -c "import openai; print('OpenAI import successful')" || true

    - name: Deploy to Azure Web App
      uses: azure/webapps-deploy@v2
      with:
        app-name: ${{ env.AZURE_WEBAPP_NAME }}
        publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
        package: .
EOF

# Create deployment configuration
echo "🔧 Creating deployment configuration..."
cat > azure-deploy.json << 'EOF'
{
  "name": "tender-analysis-system",
  "runtime": "python|3.11",
  "startup_command": "gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 main:app",
  "environment_variables": {
    "FLASK_ENV": "production",
    "PORT": "8000",
    "PYTHONPATH": "/home/site/wwwroot"
  },
  "required_azure_services": [
    "App Service (Linux, Python 3.11)",
    "Azure Database for PostgreSQL",
    "Azure Storage Account",
    "Azure Redis Cache (optional)",
    "Application Insights (optional)"
  ]
}
EOF

# Create basic health check endpoint
echo "🏥 Creating health check module..."
cat > health_check.py << 'EOF'
"""Health check module for Azure App Service"""
from flask import jsonify
import os
import psycopg2
from datetime import datetime

def register_health_routes(app):
    """Register health check routes"""

    @app.route('/health')
    def health_check():
        """Basic health check"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'tender-analysis-system',
            'version': '1.0.0'
        }), 200

    @app.route('/health/detailed')
    def detailed_health_check():
        """Detailed health check with dependencies"""

        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }

        # Check database connectivity
        try:
            database_url = os.environ.get('DATABASE_URL')
            if database_url:
                conn = psycopg2.connect(database_url)
                conn.close()
                health_status['checks']['database'] = 'healthy'
            else:
                health_status['checks']['database'] = 'not_configured'
        except Exception as e:
            health_status['checks']['database'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'

        # Check AI API keys
        health_status['checks']['anthropic_api'] = 'configured' if os.environ.get('ANTHROPIC_API_KEY') else 'not_configured'
        health_status['checks']['openai_api'] = 'configured' if os.environ.get('OPENAI_API_KEY') else 'not_configured'

        # Check storage
        health_status['checks']['azure_storage'] = 'configured' if os.environ.get('AZURE_STORAGE_CONNECTION_STRING') else 'not_configured'

        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
EOF

# Create Azure-optimized app.py modifications
echo "📱 Creating Azure app initialization..."
cat > azure_app.py << 'EOF'
"""Azure-optimized Flask application initialization"""
import os
import logging
from flask import Flask
from flask_migrate import Migrate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_azure_app():
    """Create Flask app optimized for Azure App Service"""

    app = Flask(__name__)

    # Azure-specific configuration
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(32)),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_size": 20,
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "max_overflow": 40,
            "connect_args": {"sslmode": "require"} if "postgres" in os.environ.get('DATABASE_URL', '') else {}
        },
        UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER', '/tmp/uploads'),
        MAX_CONTENT_LENGTH=100 * 1024 * 1024,  # 100MB
        AZURE_STORAGE_CONNECTION_STRING=os.environ.get('AZURE_STORAGE_CONNECTION_STRING'),
        AZURE_CONTAINER_NAME=os.environ.get('AZURE_CONTAINER_NAME', 'documents'),
        ANTHROPIC_API_KEY=os.environ.get('ANTHROPIC_API_KEY'),
        OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY'),
        REDIS_URL=os.environ.get('REDIS_URL'),
    )

    # Configure logging for Azure
    if not app.debug and os.environ.get('WEBSITE_HOSTNAME'):
        # Running in Azure App Service
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        )
        app.logger.info('Tender Analysis System starting on Azure')

    # Initialize database
    try:
        from models import db
        db.init_app(app)

        # Initialize Flask-Migrate
        migrate = Migrate(app, db)

        with app.app_context():
            db.create_all()
            app.logger.info('Database tables created/verified')

    except Exception as e:
        app.logger.error(f'Database initialization failed: {str(e)}')

    # Register health check routes
    from health_check import register_health_routes
    register_health_routes(app)

    # Import and register main application routes
    try:
        from app import register_routes
        register_routes(app)
        app.logger.info('Application routes registered')
    except ImportError as e:
        app.logger.warning(f'Could not import main app routes: {str(e)}')
        # Create a basic route as fallback
        @app.route('/')
        def index():
            return {'message': 'Tender Analysis System - Setup in Progress'}, 200

    return app

# Create the app instance
app = create_azure_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
EOF

# Create Azure deployment checklist
echo "✅ Creating deployment checklist..."
cat > AZURE_DEPLOYMENT_CHECKLIST.md << 'EOF'
# Azure Deployment Checklist

## Pre-Deployment Setup

### 1. Azure Resources (Create in Azure Portal)
- [ ] **Resource Group**: Create a new resource group for your project
- [ ] **App Service Plan**: Linux, Basic B2 or higher (for production)
- [ ] **App Service**: Python 3.11, Linux
- [ ] **Azure Database for PostgreSQL**: Flexible Server recommended
- [ ] **Storage Account**: For document uploads (Blob Storage)
- [ ] **Redis Cache**: Optional, for performance (Basic C1 minimum)
- [ ] **Application Insights**: Optional, for monitoring

### 2. Database Configuration
- [ ] Create PostgreSQL database named `tender_system`
- [ ] Configure firewall to allow Azure services
- [ ] Note connection string format:
  ```
  postgresql://username%40servername:password@servername.postgres.database.azure.com:5432/tender_system?sslmode=require
  ```

### 3. Storage Account Configuration
- [ ] Create storage account
- [ ] Create blob container named `documents`
- [ ] Set container access level to "Private"
- [ ] Get connection string from Access Keys

### 4. App Service Configuration
Navigate to: App Service → Configuration → Application settings

Add these environment variables:
```bash
DATABASE_URL=your-postgres-connection-string
SECRET_KEY=generate-a-secure-key
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection-string
AZURE_CONTAINER_NAME=documents
FLASK_ENV=production
PORT=8000
WEBSITE_VNET_ROUTE_ALL=1
```

### 5. App Service Settings
- [ ] Set **Startup Command**: `gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 main:app`
- [ ] Enable **HTTPS Only**
- [ ] Set **Python Version** to 3.11
- [ ] Enable **Always On** (prevents cold starts)

## Deployment Methods

### Method 1: GitHub Actions (Recommended)
1. Fork/clone your repository
2. In Azure Portal → App Service → Deployment Center:
   - Choose GitHub
   - Authorize and select repository
   - GitHub Actions will be configured automatically
3. Push to main branch triggers deployment

### Method 2: Direct Git Deployment
1. In Azure Portal → App Service → Deployment Center:
   - Choose Local Git
   - Note the Git URL
2. Add Azure remote:
   ```bash
   git remote add azure <your-git-url>
   git push azure main
   ```

### Method 3: ZIP Deployment
1. Create deployment ZIP:
   ```bash
   zip -r deployment.zip . -x "*.git*" "__pycache__*" "*.pyc" "venv/*"
   ```
2. Use Azure CLI:
   ```bash
   az webapp deployment source config-zip --resource-group myResourceGroup --name myAppService --src deployment.zip
   ```

## Post-Deployment Tasks

### 1. Verify Health Endpoints
- [ ] Test: `https://your-app.azurewebsites.net/health`
- [ ] Test: `https://your-app.azurewebsites.net/health/detailed`

### 2. Initialize Database
Access the Kudu console (https://your-app.scm.azurewebsites.net) and run:
```bash
cd /home/site/wwwroot
python database_init.py
```

### 3. Test Core Functionality
- [ ] User registration/login
- [ ] File upload
- [ ] Document processing
- [ ] Requirements extraction

### 4. Configure Custom Domain (Optional)
- [ ] Add custom domain in App Service
- [ ] Configure SSL certificate
- [ ] Update DNS records

## Monitoring and Maintenance

### 1. Enable Application Insights
- [ ] Create Application Insights resource
- [ ] Add `APPINSIGHTS_INSTRUMENTATIONKEY` to app settings
- [ ] Monitor performance and errors

### 2. Set Up Alerts
- [ ] CPU usage > 80%
- [ ] Memory usage > 80%
- [ ] HTTP 5xx errors
- [ ] Response time > 30 seconds

### 3. Backup Strategy
- [ ] Enable automatic database backups
- [ ] Configure blob storage backup
- [ ] Test restore procedures

## Security Checklist

- [ ] All secrets stored in App Service Configuration (not in code)
- [ ] HTTPS Only enabled
- [ ] Latest TLS version configured
- [ ] Database firewall configured
- [ ] Storage account access keys rotated
- [ ] Application Insights data retention configured

## Performance Optimization

- [ ] Enable Redis caching if using high traffic
- [ ] Configure CDN for static files
- [ ] Optimize database queries
- [ ] Implement proper logging levels
- [ ] Monitor AI API usage and costs

## Troubleshooting

### Common Issues:
1. **App won't start**: Check logs in App Service → Log stream
2. **Database connection fails**: Verify connection string format
3. **File uploads fail**: Check storage account permissions
4. **AI APIs not working**: Verify API keys in configuration

### Useful Azure CLI Commands:
```bash
# View app logs
az webapp log tail --name your-app --resource-group your-rg

# Restart app
az webapp restart --name your-app --resource-group your-rg

# Update app settings
az webapp config appsettings set --name your-app --resource-group your-rg --settings KEY=VALUE
```
EOF

echo ""
echo "🎉 Azure deployment setup complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Review and customize .env.example with your Azure resource details"
echo "2. Create Azure resources (App Service, PostgreSQL, Storage Account)"
echo "3. Configure environment variables in Azure App Service"
echo "4. Push to GitHub (if using GitHub Actions) or deploy directly"
echo "5. Follow AZURE_DEPLOYMENT_CHECKLIST.md for detailed steps"
echo ""
echo "📁 Files created:"
echo "  ✓ Dockerfile (production-ready)"
echo "  ✓ requirements.txt (with Azure dependencies)"
echo "  ✓ .env.example (environment variables template)"
echo "  ✓ .github/workflows/azure-deploy.yml (GitHub Actions)"
echo "  ✓ health_check.py (health monitoring)"
echo "  ✓ azure_app.py (Azure-optimized app initialization)"
echo "  ✓ AZURE_DEPLOYMENT_CHECKLIST.md (step-by-step guide)"
echo ""
echo "🚀 Your project is now ready for Azure App Service deployment!"
