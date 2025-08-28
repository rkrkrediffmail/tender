# stealth - Complete User Guide

**AI-Powered RFP Analysis & Proposal Generation Platform**


## 📋 Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Setup & Installation](#3-setup--installation)
4. [Administrative Setup](#4-administrative-setup)
5. [User Management](#5-user-management)
6. [Project Management](#6-project-management)
7. [Document Processing](#7-document-processing)
8. [AI Analysis Features](#8-ai-analysis-features)
9. [Proposal Generation](#9-proposal-generation)
10. [Partner Management](#10-partner-management)
11. [System Monitoring](#11-system-monitoring)
12. [Troubleshooting](#12-troubleshooting)
13. [API Reference](#13-api-reference)
14. [Security & Best Practices](#14-security--best-practices)
15. [Appendices](#15-appendices)


---

## 1. Introduction

### 1.1 What is stealth?

stealth is an AI-powered platform designed to streamline the Request for Proposal (RFP) analysis and response process. Built by company Global, it combines document intelligence, requirements analysis, and automated proposal generation to help organizations respond to RFPs more efficiently and effectively.

### 1.2 Key Features

- **🤖 AI-Powered Analysis**: Automatic extraction and analysis of RFP requirements
- **📄 Multi-Format Support**: Process PDF, DOCX, Excel, and text documents
- **🔍 Requirements Engineering**: Intelligent categorization and conflict detection
- **📝 Proposal Generation**: Automated proposal creation with customizable templates
- **🤝 Partner Recommendations**: Smart partner matching based on requirements
- **📊 Project Management**: Complete project lifecycle tracking
- **⚡ Real-time Processing**: Immediate document analysis and feedback

### 1.3 Who Should Use This Guide

- **System Administrators**: Setup, configuration, and maintenance
- **Project Managers**: Daily operations and project management
- **Business Users**: RFP analysis and proposal creation
- **IT Support**: Troubleshooting and technical support
- **Developers**: API integration and customization

### 1.4 Prerequisites

- Basic understanding of web applications
- Familiarity with RFP processes
- Administrative access for setup tasks
- Modern web browser (Chrome, Firefox, Safari, Edge)

---

## 2. System Overview

### 2.1 Architecture

stealth uses a simplified, single-container architecture for easy deployment and maintenance:

```
┌─────────────────────────────────────────┐
│              stealth               │
├─────────────────────────────────────────┤
│  Web Application (Flask)                │
│  ├── Document Processing                │
│  ├── AI Analysis Engine                 │
│  ├── Proposal Generator                 │
│  └── Partner Management                 │
├─────────────────────────────────────────┤
│  Database (PostgreSQL)                  │
│  ├── Projects & Documents               │
│  ├── Users & Authentication             │
│  ├── Analysis Results                   │
│  └── Generated Proposals                │
├─────────────────────────────────────────┤
│  AI Services                            │
│  ├── Anthropic Claude API               │
│  └── OpenAI API (Optional)              │
└─────────────────────────────────────────┘
```

### 2.2 Technology Stack

- **Backend**: Python Flask, SQLAlchemy
- **Database**: PostgreSQL
- **AI Integration**: Anthropic Claude, OpenAI
- **Document Processing**: PyPDF2, python-docx, openpyxl
- **Frontend**: Bootstrap 5, company Custom Theme
- **Deployment**: Docker, Gunicorn

### 2.3 User Roles

- **Administrator**: Full system access, user management, configuration
- **Project Manager**: Create projects, manage teams, generate proposals
- **Analyst**: Upload documents, review analysis, create requirements
- **Viewer**: Read-only access to projects and analysis

### 2.4 Workflow Overview

```
1. Project Creation → 2. Document Upload → 3. AI Analysis → 
4. Requirements Review → 5. Partner Recommendations → 6. Proposal Generation
```

---

## 3. Setup & Installation

### 3.1 System Requirements

#### Minimum Requirements:
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB
- **Network**: Internet connection for AI services

#### Recommended Requirements:
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 50GB+ SSD
- **Network**: High-speed internet

### 3.2 Quick Start (Docker)

#### Prerequisites:
- Docker and Docker Compose installed
- PostgreSQL database available
- AI API keys (Anthropic Claude required)

#### Step 1: Clone and Configure
```bash
# Clone the repository
git clone <repository-url>
cd tender

# Copy environment template
cp .env.example .env
```

#### Step 2: Configure Environment Variables
Edit `.env` file:
```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@host:5432/database_name

# AI Service Keys
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key  # Optional

# Security
SECRET_KEY=your_super_secure_secret_key

# Application Settings
FLASK_ENV=production
PORT=5000
```

#### Step 3: Deploy
```bash
# Build and start the application
docker-compose up --build

# The application will be available at http://localhost:5001
```

### 3.3 Manual Installation

#### Step 1: Install Python Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 2: Database Setup
```bash
# Initialize database
python database_init.py

# Or manually create admin user
python -c "
from main import create_app
from models import init_db
app = create_app()
init_db(app)
"
```

#### Step 3: Start Application
```bash
# Development mode
python main.py

# Production mode
./start.sh
```

### 3.4 Database Configuration

#### PostgreSQL Setup
```sql
-- Create database
CREATE DATABASE tender_system;

-- Create user
CREATE USER tender_user WITH PASSWORD 'secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE tender_system TO tender_user;
```

#### Connection String Format
```
postgresql://username:password@hostname:port/database_name?sslmode=require
```

### 3.5 SSL/HTTPS Configuration

For production deployments, configure HTTPS:

```nginx
# Nginx configuration example
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/certificate.pem;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 4. Administrative Setup

### 4.1 First-Time Setup

#### Access Admin Panel
1. Navigate to `http://your-domain.com:5001`
2. Login with default credentials:
   - **Username**: `admin`
   - **Password**: `admin123`
3. **⚠️ Change default password immediately**

#### Initial Configuration Steps
1. **Change Admin Password**
   - Go to User Profile → Change Password
   - Use strong password (12+ characters, mixed case, numbers, symbols)

2. **Configure AI Services**
   - Navigate to Settings → AI Settings
   - Enter Anthropic API key
   - Test connection
   - Optionally configure OpenAI integration

3. **Setup System Settings**
   - Configure file upload limits
   - Set default project templates
   - Configure email notifications (if available)

### 4.2 AI Provider Configuration

#### Anthropic Claude Setup
1. Go to **AI Settings** page
2. Enter your Anthropic API key
3. Select preferred model:
   - `claude-3-sonnet` (Recommended for accuracy)
   - `claude-3-haiku` (Faster, lower cost)
4. Test connection
5. Save configuration

#### OpenAI Setup (Optional)
1. Enter OpenAI API key
2. Select model:
   - `gpt-4` (Best quality)
   - `gpt-3.5-turbo` (Faster, lower cost)
3. Configure usage limits
4. Save configuration

### 4.3 System Configuration

#### File Upload Settings
```python
# Maximum file size (default: 50MB)
MAX_CONTENT_LENGTH = 52428800

# Allowed file types
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'xlsx', 'xls'}

# Upload directory
UPLOAD_FOLDER = 'uploads'
```

#### Security Settings
- Enable HTTPS in production
- Configure session timeout
- Set up backup procedures
- Configure logging levels

### 4.4 Backup and Maintenance

#### Database Backup
```bash
# Create backup
pg_dump -h hostname -U username -d database_name > backup_$(date +%Y%m%d).sql

# Restore backup
psql -h hostname -U username -d database_name < backup_file.sql
```

#### File System Backup
```bash
# Backup uploads and logs
tar -czf backup_files_$(date +%Y%m%d).tar.gz uploads/ logs/
```

#### Health Monitoring
- Monitor `/health` endpoint
- Check disk space regularly
- Monitor API usage and costs
- Review system logs

---

## 5. User Management

### 5.1 Creating Users

#### Admin User Creation
1. Navigate to **Admin Panel** → **User Management**
2. Click **Add New User**
3. Fill in user details:
   - **Username**: Unique identifier
   - **Email**: Valid email address
   - **Full Name**: Display name
   - **Role**: Select appropriate role
   - **Password**: Temporary password (user should change)
4. Click **Create User**
5. Notify user of their credentials

#### User Roles and Permissions

| Role | Projects | Documents | Analysis | Proposals | Admin |
|------|----------|-----------|----------|-----------|-------|
| **Administrator** | ✅ All | ✅ All | ✅ All | ✅ All | ✅ Yes |
| **Project Manager** | ✅ Own + Assigned | ✅ Project docs | ✅ Review | ✅ Generate | ❌ No |
| **Analyst** | ✅ Assigned | ✅ Upload/View | ✅ Create | ✅ View | ❌ No |
| **Viewer** | ✅ Assigned | ❌ View only | ❌ View only | ❌ View only | ❌ No |

### 5.2 User Profile Management

#### User Self-Service
Users can manage their own:
- Profile information
- Password changes
- Notification preferences
- Project assignments (view only)

#### Admin User Management
Administrators can:
- Reset user passwords
- Change user roles
- Deactivate/activate accounts
- View user activity logs
- Assign projects to users

### 5.3 Authentication and Security

#### Password Policy
- Minimum 8 characters
- Must include letters and numbers
- Special characters recommended
- Password expiry: 90 days (configurable)

#### Session Management
- Session timeout: 8 hours (configurable)
- Automatic logout on browser close
- Concurrent session limits

---

## 6. Project Management

### 6.1 Creating a New Project

#### Step-by-Step Project Creation
1. **Navigate to Projects**
   - Click **Projects** in main navigation
   - Click **Create New Project**

2. **Project Information**
   - **Project Name**: Descriptive name for the RFP
   - **Client Name**: Organization issuing the RFP
   - **RFP Type**: Select from predefined types
   - **Deadline**: Submission deadline
   - **Description**: Brief project overview
   - **Budget Range**: Estimated project value

3. **Project Settings**
   - **Team Members**: Assign users to project
   - **Workflow Type**: Choose analysis workflow
   - **Priority Level**: High/Medium/Low
   - **Notification Settings**: Configure alerts

4. **Save and Continue**
   - Click **Create Project**
   - Project dashboard opens automatically

### 6.2 Project Dashboard

The project dashboard provides a comprehensive overview:

#### Key Metrics Section
- **Documents Uploaded**: Count and processing status
- **Requirements Identified**: Total extracted requirements
- **Conflicts Detected**: Number of conflicting requirements
- **Completion Progress**: Overall project progress percentage

#### Recent Activity Feed
- Document uploads and processing
- Analysis completion notifications
- Team member actions
- System-generated insights

#### Quick Actions Panel
- **Upload Documents**: Direct access to upload
- **View Analysis**: Jump to analysis results
- **Generate Proposal**: Start proposal creation
- **Partner Recommendations**: View suggested partners

### 6.3 Project Lifecycle

#### Phase 1: Document Collection
```
Upload RFP Documents → Processing → Content Extraction → Initial Analysis
```

#### Phase 2: Requirements Analysis
```
AI Analysis → Requirements Extraction → Categorization → Conflict Detection
```

#### Phase 3: Solution Design
```
Requirements Review → Partner Matching → Solution Architecture → Cost Estimation
```

#### Phase 4: Proposal Generation
```
Template Selection → Content Generation → Review & Edit → Final Proposal
```

### 6.4 Project Collaboration

#### Team Management
- **Project Owner**: Full project control
- **Team Members**: Assigned roles and permissions
- **Stakeholders**: View-only access
- **External Reviewers**: Limited access for feedback

#### Communication Features
- **Project Comments**: Team discussion threads
- **Document Annotations**: Collaborative document review
- **Status Updates**: Automated progress notifications
- **Activity Timeline**: Complete project history

---

## 7. Document Processing

### 7.1 Supported File Formats

#### Primary Formats
- **PDF**: Most common RFP format
- **Microsoft Word** (.docx, .doc): Editable documents
- **Excel** (.xlsx, .xls): Spreadsheet requirements
- **Plain Text** (.txt): Simple text documents

#### File Size Limits
- **Maximum file size**: 50MB per file
- **Total project limit**: 500MB
- **Concurrent uploads**: 5 files simultaneously

### 7.2 Document Upload Process

#### Upload Methods
1. **Drag and Drop**
   - Drag files directly onto upload area
   - Multiple files supported
   - Real-time progress indicators

2. **File Browser**
   - Click "Choose Files" button
   - Standard file browser interface
   - Multi-select enabled

3. **Bulk Upload**
   - Zip file upload (extracts automatically)
   - Folder structure preserved
   - Batch processing

#### Upload Workflow
```
1. File Selection → 2. Validation → 3. Upload → 4. Processing → 5. Analysis
```

### 7.3 Document Processing Pipeline

#### Stage 1: File Validation
- File format verification
- Size limit checking
- Virus scanning (if configured)
- Duplicate detection

#### Stage 2: Content Extraction
- **PDF Processing**: Text extraction with OCR fallback
- **Word Documents**: Full text and formatting extraction
- **Excel Files**: Data table extraction and structure preservation
- **Text Files**: Encoding detection and content reading

#### Stage 3: Content Analysis
- Language detection
- Document structure analysis
- Metadata extraction
- Initial content categorization

#### Stage 4: AI Processing
- Requirements identification
- Section classification
- Key information extraction
- Preliminary analysis

### 7.4 Document Management

#### Document Library
- **Organized by Project**: All documents grouped by project
- **Version Control**: Track document versions and changes
- **Search and Filter**: Find documents by name, type, or content
- **Download Options**: Original files and processed content

#### Document Status Indicators
- 🟢 **Processed Successfully**: Ready for analysis
- 🟡 **Processing**: Currently being analyzed
- 🔴 **Processing Failed**: Error occurred, requires attention
- 🔵 **Queued**: Waiting for processing

#### Document Actions
- **View**: Display processed content
- **Download**: Get original file
- **Reprocess**: Run analysis again
- **Delete**: Remove from project (admin only)

---

## 8. AI Analysis Features

### 8.1 Automatic Requirements Extraction

#### How It Works
The AI system automatically identifies and extracts requirements from RFP documents using advanced natural language processing:

1. **Document Parsing**: Breaks down documents into logical sections
2. **Requirement Identification**: Finds mandatory, optional, and preferred requirements
3. **Categorization**: Groups requirements by type and importance
4. **Validation**: Cross-references requirements across documents

#### Requirement Types
- **Functional Requirements**: What the system must do
- **Technical Requirements**: Technology specifications and constraints
- **Compliance Requirements**: Regulatory and legal obligations
- **Commercial Requirements**: Pricing, terms, and business conditions

#### Example Output
```
Functional Requirement: "The system must support 1000+ concurrent users"
├── Type: Performance
├── Priority: Mandatory
├── Source: Section 3.2.1
└── Related: Database scaling requirements
```

### 8.2 Conflict Detection

#### Automatic Conflict Identification
The system automatically detects conflicting requirements across documents:

#### Types of Conflicts
- **Technical Conflicts**: Incompatible technology requirements
- **Timeline Conflicts**: Contradictory delivery dates
- **Budget Conflicts**: Inconsistent cost expectations
- **Scope Conflicts**: Overlapping or contradictory features

#### Conflict Resolution Workflow
1. **Detection**: AI identifies potential conflicts
2. **Notification**: Team alerted to conflicts
3. **Analysis**: Manual review and assessment
4. **Resolution**: Document clarifications or assumptions
5. **Tracking**: Monitor resolution status

### 8.3 Missing Information Detection

#### Gap Analysis
The system identifies missing critical information:

- **Incomplete Specifications**: Technical details not provided
- **Missing Deadlines**: Unclear timeline information
- **Budget Gaps**: Unclear cost expectations
- **Undefined Requirements**: Vague or ambiguous specifications

#### Information Request Generation
Automatically generates clarification questions:
```
Suggested Questions:
1. "Section 2.3 mentions 'high availability' - what specific uptime percentage is required?"
2. "The integration requirements reference 'existing systems' - can you provide API documentation?"
3. "Budget section is unclear - what is the total project budget range?"
```

### 8.4 Analysis Dashboard

#### Analysis Overview
- **Requirements Summary**: Total counts by category
- **Compliance Status**: Requirements coverage assessment
- **Risk Assessment**: Identified risks and mitigation suggestions
- **Complexity Score**: Overall project difficulty rating

#### Detailed Analysis Views
1. **Requirements Matrix**: Tabular view of all requirements
2. **Conflict Report**: Detailed conflict analysis
3. **Gap Analysis**: Missing information summary
4. **Risk Assessment**: Comprehensive risk evaluation

---

## 9. Proposal Generation

### 9.1 Proposal Templates

#### Built-in Templates
- **Technical Proposal**: Focus on solution architecture and implementation
- **Commercial Proposal**: Emphasis on pricing and business terms
- **Compliance Proposal**: Detailed compliance and regulatory coverage
- **Implementation Proposal**: Project timeline and delivery approach

#### Template Structure
```
1. Executive Summary
2. Understanding of Requirements
3. Proposed Solution
4. Implementation Approach
5. Timeline and Milestones
6. Team and Resources
7. Pricing and Commercial Terms
8. Risk Management
9. Appendices
```

### 9.2 Automated Content Generation

#### AI-Powered Writing
The system generates proposal content based on:
- **RFP Requirements**: Direct response to identified requirements
- **Company Capabilities**: Pre-configured company information
- **Best Practices**: Industry-standard proposal approaches
- **Previous Proposals**: Learning from past successful submissions

#### Content Sections
1. **Executive Summary**: High-level overview and value proposition
2. **Requirements Response**: Point-by-point requirement addressing
3. **Solution Architecture**: Technical approach and design
4. **Implementation Plan**: Detailed project timeline and approach
5. **Team Profiles**: Relevant team member qualifications
6. **Risk Mitigation**: Identified risks and mitigation strategies

### 9.3 Proposal Customization

#### Manual Editing
- **Rich Text Editor**: Full formatting capabilities
- **Section Management**: Add, remove, or reorder sections
- **Template Customization**: Modify templates for future use
- **Collaborative Editing**: Multiple team members can contribute

#### Company Information Integration
- **Company Profile**: Automatic insertion of company details
- **Capability Statements**: Pre-written capability descriptions
- **Case Studies**: Relevant project examples
- **Team Bios**: Staff profiles and qualifications

### 9.4 Proposal Export and Delivery

#### Export Formats
- **Microsoft Word**: Editable .docx format
- **PDF**: Professional presentation format
- **HTML**: Web-based viewing
- **Custom Formats**: Configurable output options

#### Proposal Package Generation
The system can generate complete proposal packages including:
- **Main Proposal Document**
- **Executive Summary** (separate document)
- **Technical Appendices**
- **Pricing Schedules**
- **Company Credentials**
- **Cover Letter Template**

#### Version Control
- **Draft Management**: Save and track proposal drafts
- **Version History**: Complete edit history
- **Collaboration Tracking**: See who made what changes
- **Final Version Lock**: Protect submitted proposals

---

## 10. Partner Management

### 10.1 Partner Database

#### Partner Information
- **Company Profile**: Name, description, size, location
- **Capabilities**: Services and technical expertise
- **Certifications**: Industry certifications and accreditations
- **Past Performance**: Previous project success rates
- **Contact Information**: Key personnel and contact details

#### Partner Categories
- **Technology Partners**: Software and hardware vendors
- **Service Partners**: Implementation and consulting firms
- **Industry Partners**: Domain-specific expertise providers
- **Regional Partners**: Local market specialists

### 10.2 Automated Partner Recommendations

#### Matching Algorithm
The system automatically recommends partners based on:
- **Requirement Matching**: Technical and functional requirements
- **Geographic Preferences**: Location-based matching
- **Past Performance**: Success rates and client satisfaction
- **Availability**: Current capacity and timeline fit
- **Cost Considerations**: Budget and pricing alignment

#### Recommendation Scoring
```
Partner Recommendation: TechCorp Solutions
├── Capability Match: 95%
├── Geographic Fit: 100% (Local)
├── Past Performance: 4.8/5.0
├── Availability: Available
└── Overall Score: 92%
```

### 10.3 Partner Collaboration

#### Partner Communication
- **Direct Messaging**: Secure communication channels
- **Document Sharing**: Share RFP documents and requirements
- **Proposal Collaboration**: Joint proposal development
- **Status Updates**: Real-time project status sharing

#### Partner Onboarding
1. **Registration**: Partner creates account
2. **Verification**: Admin approves partner credentials
3. **Profile Setup**: Complete partner information
4. **Capability Assessment**: Define areas of expertise
5. **Integration**: Access to relevant projects

---

## 11. System Monitoring

### 11.1 Health Monitoring

#### System Health Dashboard
Access the health dashboard at `/health`:

```json
{
  "web_running": true,
  "database_status": "connected",
  "processing_mode": "synchronous - documents processed immediately",
  "api_keys_configured": true,
  "projects_count": 15,
  "documents_count": 147,
  "ready_for_upload": true
}
```

#### Key Metrics to Monitor
- **Application Status**: Web server availability
- **Database Connectivity**: PostgreSQL connection status
- **AI Service Status**: API key validation and connectivity
- **File System Health**: Storage space and permissions
- **Processing Performance**: Document processing times

### 11.2 Usage Analytics

#### Project Analytics
- **Project Creation Trends**: Projects created over time
- **Document Volume**: Documents processed by period
- **User Activity**: Most active users and features
- **Success Metrics**: Proposal win rates and client satisfaction

#### System Performance
- **Response Times**: API and page load performance
- **Resource Usage**: CPU, memory, and storage utilization
- **Error Rates**: Application errors and failure rates
- **AI Usage**: API calls and token consumption

### 11.3 Logging and Troubleshooting

#### Log Files Location
```
logs/
├── application.log      # Main application events
├── error.log           # Error messages and stack traces
├── access.log          # Web server access logs
├── ai_usage.log        # AI API usage tracking
└── security.log        # Authentication and security events
```

#### Log Levels
- **DEBUG**: Detailed debugging information
- **INFO**: General information about system operation
- **WARNING**: Warning messages about potential issues
- **ERROR**: Error conditions that need attention
- **CRITICAL**: Critical errors that may cause system failure

#### Monitoring Best Practices
1. **Regular Health Checks**: Monitor `/health` endpoint
2. **Log Review**: Check logs daily for errors
3. **Performance Monitoring**: Track response times
4. **Storage Monitoring**: Ensure adequate disk space
5. **Backup Verification**: Test backup procedures regularly

---

## 12. Troubleshooting

### 12.1 Common Issues

#### Document Processing Problems

**Issue**: Documents fail to process
```
Symptoms: 
- Upload completes but processing status shows "failed"
- Error message: "Document processing failed"

Solutions:
1. Check file format (must be PDF, DOCX, Excel, or TXT)
2. Verify file size (must be under 50MB)
3. Ensure file is not corrupted
4. Check application logs for specific error
```

**Issue**: Slow document processing
```
Symptoms:
- Documents take longer than 2-3 minutes to process
- Browser timeout errors

Solutions:
1. Check system resources (CPU, memory)
2. Reduce file size if possible
3. Process documents individually rather than in bulk
4. Check AI API response times
```

#### AI Analysis Issues

**Issue**: AI analysis not working
```
Symptoms:
- Requirements not being extracted
- Empty analysis results
- "AI service unavailable" errors

Solutions:
1. Verify API keys in AI Settings
2. Check internet connectivity
3. Verify API key permissions and usage limits
4. Test AI connection in settings
```

**Issue**: Poor analysis quality
```
Symptoms:
- Incorrect requirements extraction
- Missing important information
- Irrelevant recommendations

Solutions:
1. Check document quality and formatting
2. Ensure documents are in English (or supported language)
3. Try different AI model if available
4. Provide feedback to improve future analysis
```

#### Authentication Problems

**Issue**: Cannot login
```
Symptoms:
- "Invalid credentials" error
- Account locked messages

Solutions:
1. Verify username and password
2. Check if account is active
3. Reset password if necessary
4. Contact administrator for account issues
```

**Issue**: Session timeout errors
```
Symptoms:
- Randomly redirected to login page
- "Session expired" messages

Solutions:
1. Check session timeout settings
2. Ensure cookies are enabled
3. Clear browser cache and cookies
4. Contact admin to adjust session duration
```

### 12.2 Error Messages and Solutions

#### Database Errors
```
Error: "Database connection failed"
Solution: 
1. Check DATABASE_URL configuration
2. Verify database server is running
3. Check network connectivity
4. Verify database credentials
```

#### File Upload Errors
```
Error: "File too large"
Solution: 
1. Reduce file size (max 50MB)
2. Compress PDF files
3. Split large documents
4. Contact admin to increase limits
```

#### AI Service Errors
```
Error: "API key invalid"
Solution:
1. Verify API key in settings
2. Check key permissions
3. Ensure sufficient API credits
4. Contact AI service provider
```

### 12.3 Performance Optimization

#### Slow Performance Issues
1. **Database Optimization**
   - Regular database maintenance
   - Index optimization
   - Query performance review

2. **File System Optimization**
   - Regular cleanup of old files
   - Adequate storage space
   - Fast storage (SSD recommended)

3. **Application Optimization**
   - Monitor memory usage
   - Optimize AI API calls
   - Cache frequently accessed data

#### Scaling Considerations
- **Horizontal Scaling**: Multiple application instances
- **Database Scaling**: Read replicas, connection pooling
- **Storage Scaling**: Network attached storage, cloud storage
- **CDN Integration**: Static file delivery optimization

---

## 13. API Reference

### 13.1 Authentication

All API endpoints require authentication. Include the session cookie or API token in requests.

#### Login Endpoint
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

#### Response
```json
{
  "success": true,
  "user_id": 123,
  "username": "your_username",
  "role": "project_manager"
}
```

### 13.2 Project Management API

#### Create Project
```http
POST /api/projects
Content-Type: application/json

{
  "name": "Project Name",
  "client_name": "Client Organization",
  "description": "Project description",
  "deadline": "2024-12-31",
  "rfp_type": "technical"
}
```

#### Get Project Details
```http
GET /api/projects/{project_id}
```

#### List Projects
```http
GET /api/projects?limit=10&offset=0
```

### 13.3 Document Management API

#### Upload Document
```http
POST /api/upload
Content-Type: multipart/form-data

project_id: 123
file: [binary file data]
```

#### Response
```json
{
  "success": true,
  "document_id": 456,
  "filename": "rfp_document.pdf",
  "file_size": 2048576,
  "processing_result": {
    "success": true,
    "content_length": 15234,
    "message": "Document processed successfully"
  }
}
```

#### Get Document Status
```http
GET /api/documents/{document_id}/status
```

### 13.4 Analysis API

#### Trigger Analysis
```http
POST /api/projects/{project_id}/analyze
```

#### Get Analysis Results
```http
GET /api/projects/{project_id}/analysis
```

#### Response
```json
{
  "requirements": [
    {
      "id": 1,
      "text": "System must support 1000+ concurrent users",
      "type": "functional",
      "priority": "mandatory",
      "source": "Section 3.2.1"
    }
  ],
  "conflicts": [
    {
      "description": "Conflicting timeline requirements",
      "documents": ["doc1.pdf", "doc2.pdf"],
      "severity": "high"
    }
  ],
  "missing_info": [
    {
      "category": "technical",
      "description": "Database performance requirements not specified"
    }
  ]
}
```

### 13.5 Proposal Generation API

#### Generate Proposal
```http
POST /api/projects/{project_id}/generate-proposal
Content-Type: application/json

{
  "template_type": "technical",
  "sections": ["executive_summary", "technical_approach", "timeline"],
  "include_pricing": true
}
```

#### Get Proposal Status
```http
GET /api/proposals/{proposal_id}/status
```

#### Download Proposal
```http
GET /api/proposals/{proposal_id}/download?format=docx
```

### 13.6 Error Handling

#### Standard Error Response
```json
{
  "success": false,
  "error": "Error description",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "field": "Additional error details"
  }
}
```

#### HTTP Status Codes
- `200 OK`: Request successful
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

---

## 14. Security & Best Practices

### 14.1 Security Configuration

#### HTTPS Configuration
Always use HTTPS in production:
```nginx
# Nginx SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
ssl_prefer_server_ciphers off;
```

#### Password Security
- **Minimum Length**: 8 characters
- **Complexity**: Letters, numbers, symbols
- **Expiration**: 90 days (configurable)
- **History**: Prevent reuse of last 5 passwords

#### Session Security
- **Secure Cookies**: HTTPS-only cookies
- **Session Timeout**: 8 hours maximum
- **CSRF Protection**: Anti-CSRF tokens on forms
- **Same-Site Cookies**: Prevent cross-site attacks

### 14.2 Data Protection

#### File Security
- **Upload Validation**: File type and size restrictions
- **Virus Scanning**: Integrate antivirus scanning if required
- **Access Control**: Project-based file access restrictions
- **Encryption**: Encrypt sensitive files at rest

#### Database Security
- **Connection Encryption**: Use SSL for database connections
- **Access Control**: Principle of least privilege
- **Regular Backups**: Automated encrypted backups
- **Data Retention**: Configure data retention policies

#### API Security
- **Rate Limiting**: Prevent API abuse
- **Input Validation**: Validate all input data
- **Output Sanitization**: Prevent XSS attacks
- **API Keys**: Secure storage of AI service keys

### 14.3 Privacy Considerations

#### Data Handling
- **Minimal Collection**: Only collect necessary data
- **Purpose Limitation**: Use data only for stated purposes
- **Data Retention**: Delete data when no longer needed
- **User Rights**: Provide data access and deletion capabilities

#### AI Service Integration
- **Data Sharing**: Understand what data is sent to AI services
- **Data Location**: Know where your data is processed
- **Service Terms**: Review AI service terms and conditions
- **Compliance**: Ensure AI usage meets regulatory requirements

### 14.4 Operational Security

#### Access Management
- **Role-Based Access**: Implement principle of least privilege
- **Regular Reviews**: Periodic access reviews and cleanup
- **Offboarding**: Immediate access revocation for departing users
- **Administrative Access**: Separate admin accounts for privileged operations

#### Monitoring and Auditing
- **Activity Logging**: Log all user actions and system events
- **Failed Login Monitoring**: Track and alert on failed attempts
- **Unusual Activity**: Monitor for abnormal usage patterns
- **Regular Audits**: Periodic security assessments

#### Incident Response
- **Response Plan**: Documented security incident procedures
- **Contact Information**: Emergency contacts and escalation procedures
- **Backup Systems**: Maintain offline backups for disaster recovery
- **Communication Plan**: Internal and external communication procedures

---

## 15. Appendices

### Appendix A: Configuration Reference

#### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# AI Services
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key

# Application
SECRET_KEY=your_secret_key
FLASK_ENV=production
PORT=5000
MAX_CONTENT_LENGTH=52428800

# Optional
DEBUG=false
LOG_LEVEL=INFO
SESSION_TIMEOUT=28800
```

#### File Structure
```
/app/
├── main.py                    # Main application
├── sync_processor.py          # Document processing
├── models.py                  # Database models
├── document_processor.py      # Document handling
├── real_analysis_system.py    # AI analysis
├── requirements.txt           # Dependencies
├── Dockerfile                 # Container configuration
├── docker-compose.yml         # Deployment configuration
├── static/                    # Static assets
│   ├── css/company-theme.css    # company branding
│   ├── img/                  # Images and logos
│   └── js/                   # JavaScript files
├── templates/                 # HTML templates
│   ├── dashboard.html        # Main dashboard
│   ├── projects.html         # Project listing
│   ├── upload.html           # File upload
│   └── ...                   # Other templates
├── uploads/                   # Uploaded files
├── logs/                      # Application logs
└── generated_proposals/       # Output proposals
```

### Appendix B: Troubleshooting Checklist

#### Pre-Deployment Checklist
- [ ] Database connection configured and tested
- [ ] AI API keys configured and validated
- [ ] Environment variables set correctly
- [ ] File upload directory permissions correct
- [ ] SSL certificate configured (production)
- [ ] Firewall rules configured
- [ ] Backup procedures tested
- [ ] Admin password changed from default

#### Daily Operations Checklist
- [ ] Check application health endpoint
- [ ] Review error logs for issues
- [ ] Monitor disk space usage
- [ ] Verify backup completion
- [ ] Check AI API usage and costs
- [ ] Review user activity for anomalies

#### Performance Monitoring
- [ ] Application response times < 2 seconds
- [ ] Database connection pool healthy
- [ ] Document processing completing within 5 minutes
- [ ] Memory usage stable
- [ ] No critical errors in logs

### Appendix C: Support and Resources

#### Getting Help
- **Documentation**: This user guide
- **Health Check**: `/health` endpoint for system status
- **Log Files**: Check application logs for detailed error information
- **company Support**: Contact company Global support team

#### Useful Commands
```bash
# Check application status
curl http://localhost:5001/health

# View recent logs
tail -f logs/application.log

# Database backup
pg_dump -h hostname -U username database_name > backup.sql

# Restart application
docker-compose restart web

# Check disk space
df -h

# Monitor system resources
top -p $(pgrep python)
```

#### Common File Locations
- **Configuration**: `.env` file
- **Logs**: `logs/` directory
- **Uploads**: `uploads/` directory
- **Generated Proposals**: `generated_proposals/` directory
- **Database Backups**: `backups/` directory (if configured)

---

## Quick Reference Card

### Essential URLs
- **Application**: `http://localhost:5001`
- **Health Check**: `http://localhost:5001/health`
- **Admin Login**: Username: `admin`, Password: `admin123` (change immediately)

### Key Features
- 📄 **Upload**: Drag and drop RFP documents
- 🤖 **AI Analysis**: Automatic requirements extraction
- 📊 **Dashboard**: Project overview and status
- 📝 **Proposals**: Generate professional proposals
- 🤝 **Partners**: Smart partner recommendations

### Emergency Contacts
- **Technical Support**: [Your Support Contact]
- **System Administrator**: [Admin Contact]
- **company Global**: [company Support Contact]

---

*This guide covers stealth version 1.0. For the latest updates and additional resources, visit the company Global support portal.*
