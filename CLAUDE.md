# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Tender Analysis System** - a Flask-based web application that helps users analyze RFP (Request for Proposal) documents, extract requirements, identify conflicts, and generate proposals. The system uses AI (Anthropic Claude) for document analysis and includes multi-agent architecture for different analysis tasks.

## Common Development Commands

### Running the Application
```bash
# Development mode
python main.py

# Using Docker Compose (recommended)
docker-compose up

# Individual services
docker-compose up web        # Main application
docker-compose up celery     # Background worker
docker-compose up redis      # Cache/message broker
```

### Database Operations
```bash
# Initialize database and create admin user
python database_init.py

# Create admin user manually (if needed)
python -c "from main import create_app; from models import init_db; app = create_app(); init_db(app)"

# Database migrations (if Flask-Migrate is set up)
flask db migrate -m "description"
flask db upgrade
```

### Testing
```bash
# Run tests (check if pytest is configured)
pytest

# Health check
curl http://localhost:5000/health
```

## High-Level Architecture

### Core Application Structure
- **main.py**: Primary Flask application entry point with comprehensive route definitions
- **app.py**: Alternative/legacy Flask app setup with original functionality  
- **models.py**: SQLAlchemy database models for all entities
- **real_analysis_system.py**: AI-powered analysis using Anthropic Claude API

### Multi-Agent System
Located in `/agents/` directory:
- **base_agent.py**: Abstract base class for all agents
- **document_intelligence.py**: Document parsing and content extraction
- **requirements_engineering.py**: Requirements analysis and extraction
- **partner_recommendation_agent.py**: Partner/vendor recommendation system
- **orchestrator.py**: Coordinates multiple agents for complex workflows

### Database Models Architecture
The system uses a comprehensive database schema with these key models:
- **User/Project Management**: User, Project, Document
- **Enhanced RFP Processing**: RFPDocument, KeyPoint, ConsolidatedKeyPoint, Conflict, MissingInformation
- **Agent System**: Agent, AgentTask, AgentMessage
- **Partner Management**: Partner, PartnerProduct, PartnerRecommendation
- **Requirements**: Requirement (legacy and enhanced)

### Document Processing Pipeline
1. **Upload**: Files uploaded via `/api/upload` endpoint
2. **Text Extraction**: DocumentProcessor extracts content from PDFs/DOCX
3. **AI Analysis**: RealAnalysisSystem analyzes content using Claude API
4. **Key Point Extraction**: Identifies requirements, constraints, deadlines
5. **Conflict Detection**: Finds contradictory requirements across documents
6. **Missing Information**: Identifies gaps that need clarification

### Background Processing
- **Celery**: Used for asynchronous document processing
- **Redis**: Message broker and caching layer
- **Tasks**: Document analysis, requirement extraction, conflict detection

## Key Configuration

### Environment Variables Required
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db_name
REDIS_URL=redis://redis:6379/0
ANTHROPIC_API_KEY=your_api_key
OPENAI_API_KEY=your_openai_key  # Optional
SECRET_KEY=your_secret_key
FLASK_ENV=development  # or production
```

### Default Admin Credentials
- Username: `admin`
- Password: `admin123`

## Important Development Notes

### Database Initialization
The application automatically creates database tables and an admin user on startup. If database issues occur, run `database_init.py` manually.

### AI Integration
The system heavily relies on Anthropic Claude for document analysis. Ensure ANTHROPIC_API_KEY is properly configured. The system includes fallback responses when AI is unavailable.

### File Upload Handling
- Supports: PDF, DOC, DOCX, TXT, XLSX, XLS
- Max file size: 50MB (configurable)
- Files stored in `/uploads` directory
- Unique filenames generated to prevent conflicts

### Multi-Document Processing
The system can process multiple RFP documents simultaneously and:
- Consolidates key points across documents
- Detects conflicts between requirements
- Identifies missing information that needs clarification
- Generates comprehensive analysis reports

### Agent Communication
Agents communicate through:
- Database task queues (AgentTask model)
- JSON message passing for complex workflows
- Event-driven processing for document updates

### Testing Approach
When testing, use the health check endpoint `/health` to verify system status including database connectivity, Redis connection, and API key configuration.

## Deployment Notes

### Docker Deployment
The application is containerized with:
- Multi-stage Dockerfile for optimized builds
- Docker Compose for complete stack deployment
- Health checks for service monitoring
- Volume mounts for persistent file storage

### Production Considerations
- Configure proper PostgreSQL database (not SQLite)
- Set up Redis for production workloads
- Ensure proper SSL/HTTPS termination
- Configure file storage (local or cloud)
- Set appropriate memory limits for AI processing

## Integration Points

### API Endpoints
- `/api/upload`: File upload and processing
- `/api/projects`: Project management
- `/api/post_upload_analysis/<project_id>`: Trigger AI analysis
- `/api/generate-proposal/<project_id>`: Generate proposal documents
- `/health`: System health and status

### Template Structure
Templates are organized in `/templates/` with:
- Authentication: `/templates/auth/`
- Partner management: `/templates/partners/`
- Project views: Main template directory
- Reusable components across different views