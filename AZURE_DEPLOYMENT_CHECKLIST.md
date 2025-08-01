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
