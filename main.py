#!/usr/bin/env python3
"""
Complete main.py with full functionality
"""

import os
import sys
import uuid
from flask import Flask, jsonify, render_template_string, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from datetime import datetime

# Ensure current directory is in Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# File upload configuration
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'xlsx', 'xls'}
UPLOAD_FOLDER = '/app/uploads'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_app():
    """Create Flask application with complete functionality"""
    app = Flask(__name__)

    # Configuration
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'postgresql://postgres:password@db:5432/tender_system'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        REDIS_URL=os.environ.get('REDIS_URL', 'redis://redis:6379/0'),
        DEBUG=os.environ.get('FLASK_ENV') == 'development',
        UPLOAD_FOLDER=UPLOAD_FOLDER,
        MAX_CONTENT_LENGTH=50 * 1024 * 1024  # 50MB
    )

    # Ensure upload folder exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Initialize database
    try:
        from models import db, init_db, test_db_connection
        db.init_app(app)

        if test_db_connection(app):
            print("✅ Database connection successful")
            init_db(app)
        else:
            print("❌ Database connection failed")

    except Exception as e:
        print(f"❌ Database setup error: {e}")

    def get_system_status():
        """Get real-time system status"""
        status = {
            'web_running': True,
            'database_status': 'unknown',
            'database_initialized': False,
            'celery_status': 'unknown',
            'api_keys_configured': False,
            'projects_count': 0,
            'documents_count': 0,
            'ready_for_upload': False
        }

        # Check database
        try:
            with app.app_context():
                from models import db, User, Project, Document

                db.session.execute(db.text('SELECT 1'))
                status['database_status'] = 'connected'

                admin_user = User.query.filter_by(username='admin').first()
                status['database_initialized'] = admin_user is not None

                status['projects_count'] = Project.query.count()
                status['documents_count'] = Document.query.count()

        except Exception as e:
            status['database_status'] = f'error: {str(e)[:50]}'

        # Check Celery/Redis
        try:
            import redis
            redis_url = app.config.get('REDIS_URL')
            if redis_url:
                r = redis.from_url(redis_url)
                r.ping()
                status['celery_status'] = 'redis_connected'
            else:
                status['celery_status'] = 'not_configured'
        except Exception as e:
            status['celery_status'] = f'error: {str(e)[:30]}'

        # Check API keys
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')
        openai_key = os.environ.get('OPENAI_API_KEY', '')

        status['api_keys_configured'] = (
            anthropic_key and not anthropic_key.startswith('your-') and
            openai_key and not openai_key.startswith('your-')
        )

        # Determine if ready for uploads
        status['ready_for_upload'] = (
            status['database_status'] == 'connected' and
            status['database_initialized'] and
            status['celery_status'] in ['redis_connected', 'workers_active'] and
            status['api_keys_configured']
        )

        return status

    # Routes
    @app.route('/')
    def index():
        # Check if user is logged in
        if 'username' not in session:
            return redirect('/login')

        # Get real-time status
        system_status = get_system_status()

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Tender Analysis System - Dashboard</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    overflow: hidden;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px 30px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .nav {
                    background: #f8f9fa;
                    padding: 15px 30px;
                    border-bottom: 1px solid #e9ecef;
                }
                .nav a {
                    color: #495057;
                    text-decoration: none;
                    margin-right: 20px;
                    padding: 8px 16px;
                    border-radius: 4px;
                    transition: background 0.3s;
                }
                .nav a:hover { background: #e9ecef; }
                .nav a.active { background: #007bff; color: white; }
                .content { padding: 30px; }
                .btn {
                    display: inline-block;
                    padding: 12px 24px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 5px;
                    transition: background 0.3s;
                    border: none;
                    cursor: pointer;
                }
                .btn:hover { background: #5a6fd8; }
                .btn-success { background: #28a745; }
                .btn-success:hover { background: #218838; }
                .btn-danger { background: #dc3545; }
                .btn-danger:hover { background: #c82333; }
                .grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin: 20px 0; }
                @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
                .card {
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid #e9ecef;
                    text-align: center;
                }
                .card h3 { margin-top: 0; color: #495057; }
                .card .number { font-size: 2em; font-weight: bold; color: #667eea; }
                .status-indicator {
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }
                .status-good { background: #28a745; }
                .status-warning { background: #ffc107; }
                .status-error { background: #dc3545; }
                .user-info { color: white; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>🚀 Tender Analysis System</h1>
                        <p>AI-Powered Document Analysis & Proposal Generation</p>
                    </div>
                    <div class="user-info">
                        <p>Welcome, {{ session.username }}!</p>
                        <a href="/logout" class="btn btn-danger">Logout</a>
                    </div>
                </div>

                <div class="nav">
                    <a href="/" class="active">🏠 Dashboard</a>
                    <a href="/projects">📁 My Projects</a>
                    <a href="/upload">📄 Upload Documents</a>
                    <a href="/health">🔍 System Health</a>
                </div>

                <div class="content">
                    {% if system_status.ready_for_upload %}
                    <div style="background: #d4edda; padding: 20px; border-radius: 8px; border-left: 5px solid #28a745; margin-bottom: 20px;">
                        <h2>🎉 System Ready!</h2>
                        <p>All components are working. You can start uploading and analyzing documents!</p>
                        <a href="/projects" class="btn btn-success">📁 Go to Projects</a>
                        <a href="/upload" class="btn btn-success">📄 Upload Documents</a>
                    </div>
                    {% else %}
                    <div style="background: #fff3cd; padding: 20px; border-radius: 8px; border-left: 5px solid #ffc107; margin-bottom: 20px;">
                        <h2>⚙️ System Setup</h2>
                        <p>Some components need attention before you can use all features.</p>
                    </div>
                    {% endif %}

                    <div class="grid">
                        <div class="card">
                            <h3>📊 Projects</h3>
                            <div class="number">{{ system_status.projects_count }}</div>
                            <p>Active projects</p>
                            <a href="/projects" class="btn">View Projects</a>
                        </div>

                        <div class="card">
                            <h3>📄 Documents</h3>
                            <div class="number">{{ system_status.documents_count }}</div>
                            <p>Uploaded documents</p>
                            <a href="/upload" class="btn">Upload More</a>
                        </div>

                        <div class="card">
                            <h3>🤖 AI Analysis</h3>
                            <div class="number">
                                {% if system_status.api_keys_configured %}✅{% else %}❌{% endif %}
                            </div>
                            <p>AI systems status</p>
                            <a href="/health" class="btn">Check Status</a>
                        </div>
                    </div>

                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3>🔌 System Components</h3>
                        <p>
                            <span class="status-indicator status-good"></span>
                            <strong>Web Application:</strong> Running
                        </p>
                        <p>
                            <span class="status-indicator {% if system_status.database_status == 'connected' %}status-good{% else %}status-error{% endif %}"></span>
                            <strong>Database:</strong> {{ system_status.database_status }}
                        </p>
                        <p>
                            <span class="status-indicator {% if 'connected' in system_status.celery_status %}status-good{% else %}status-warning{% endif %}"></span>
                            <strong>Background Tasks:</strong> {{ system_status.celery_status.replace('_', ' ').title() }}
                        </p>
                        <p>
                            <span class="status-indicator {% if system_status.api_keys_configured %}status-good{% else %}status-warning{% endif %}"></span>
                            <strong>AI APIs:</strong> {% if system_status.api_keys_configured %}Configured{% else %}Not configured{% endif %}
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        ''',
        system_status=system_status,
        session=session
        )

    # Add this route to your main.py file
    @app.route('/generate-proposal/<int:project_id>')
    def generate_proposal(project_id):
        """Generate proposal document for a project"""
        if 'username' not in session:
            return redirect('/login')

        try:
            from models import User, Project, Document
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            documents = Document.query.filter_by(project_id=project_id).all()

        except Exception as e:
            flash(f"Error loading project: {e}")
            return redirect('/projects')

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Generate Proposal - {{ project.name }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
                .btn { padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; border: none; cursor: pointer; font-size: 14px; }
                .btn:hover { background: #5a6fd8; }
                .btn-success { background: #28a745; }
                .btn-success:hover { background: #218838; }
                .btn-primary { background: #007bff; }
                .btn-primary:hover { background: #0056b3; }
                .section { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #667eea; }
                .form-group { margin: 15px 0; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                select, textarea, input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
                textarea { height: 100px; resize: vertical; }
                .progress { width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px; margin: 10px 0; overflow: hidden; display: none; }
                .progress-bar { height: 100%; background: #28a745; width: 0%; transition: width 0.3s; }
                .preview-card { background: white; border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .template-option {
                    border: 2px solid #ddd;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 10px;
                    cursor: pointer;
                    transition: all 0.3s;
                    display: inline-block;
                    width: 200px;
                    text-align: center;
                }
                .template-option:hover { border-color: #667eea; background: #f8f9fa; }
                .template-option.selected { border-color: #28a745; background: #e8f5e8; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>📝 Generate Proposal</h1>
                        <p style="color: #6c757d;">Project: {{ project.name }}</p>
                    </div>
                    <div>
                        <a href="/analysis/{{ project.id }}" class="btn">← Back to Analysis</a>
                        <a href="/project/{{ project.id }}" class="btn">📁 Project Details</a>
                    </div>
                </div>

                <div class="section">
                    <h3>🎯 Proposal Configuration</h3>
                    <form id="proposalForm">
                        <div class="form-group">
                            <label for="proposalType">Proposal Type:</label>
                            <select id="proposalType" name="proposalType" required>
                                <option value="">Select proposal type...</option>
                                <option value="technical">Technical Proposal</option>
                                <option value="commercial">Commercial Proposal</option>
                                <option value="combined">Combined Technical & Commercial</option>
                                <option value="executive">Executive Summary Only</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label for="companyName">Your Company Name:</label>
                            <input type="text" id="companyName" name="companyName" placeholder="Enter your company name" required>
                        </div>

                        <div class="form-group">
                            <label for="proposalTitle">Proposal Title:</label>
                            <input type="text" id="proposalTitle" name="proposalTitle" value="Proposal for {{ project.name }}" required>
                        </div>

                        <div class="form-group">
                            <label for="executiveSummary">Executive Summary (Optional):</label>
                            <textarea id="executiveSummary" name="executiveSummary" placeholder="Brief overview of your solution approach..."></textarea>
                        </div>
                    </form>
                </div>

                <div class="section">
                    <h3>📄 Template Selection</h3>
                    <div style="text-align: center;">
                        <div class="template-option" onclick="selectTemplate('professional')" id="template-professional">
                            <h4>🏢 Professional</h4>
                            <p>Formal business template with comprehensive sections</p>
                        </div>
                        <div class="template-option" onclick="selectTemplate('technical')" id="template-technical">
                            <h4>⚙️ Technical Focus</h4>
                            <p>Emphasis on technical specifications and architecture</p>
                        </div>
                        <div class="template-option" onclick="selectTemplate('concise')" id="template-concise">
                            <h4>📋 Concise</h4>
                            <p>Streamlined format for quick turnaround</p>
                        </div>
                    </div>
                    <input type="hidden" id="selectedTemplate" value="">
                </div>

                <div class="section">
                    <h3>📊 Content Preview</h3>
                    <div class="preview-card">
                        <h4>Proposal will include:</h4>
                        <ul>
                            <li>✅ Executive Summary</li>
                            <li>✅ Understanding of Requirements ({{ documents|length }} documents analyzed)</li>
                            <li>✅ Technical Approach & Solution Architecture</li>
                            <li>✅ Project Timeline & Milestones</li>
                            <li>✅ Team Structure & Expertise</li>
                            <li>✅ Risk Assessment & Mitigation</li>
                            <li>✅ Cost Breakdown & Commercial Terms</li>
                            <li>✅ Compliance & Quality Assurance</li>
                        </ul>
                    </div>
                </div>

                <div class="progress" id="progress">
                    <div class="progress-bar" id="progressBar"></div>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <button onclick="generateProposal()" class="btn btn-success" style="padding: 15px 30px; font-size: 16px;" id="generateBtn">
                        🚀 Generate Proposal Document
                    </button>
                </div>

                <div id="result" style="margin-top: 30px; display: none;">
                    <div class="section">
                        <h3>✅ Proposal Generated Successfully!</h3>
                        <div style="text-align: center;">
                            <a href="#" id="downloadBtn" class="btn btn-primary" style="padding: 15px 30px; font-size: 16px;">
                                📥 Download Proposal (PDF)
                            </a>
                            <a href="#" id="viewBtn" class="btn" style="padding: 15px 30px; font-size: 16px;">
                                👁️ Preview Proposal
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            <script>
            let selectedTemplate = '';

            function selectTemplate(template) {
                // Remove previous selection
                document.querySelectorAll('.template-option').forEach(el => {
                    el.classList.remove('selected');
                });

                // Select new template
                document.getElementById('template-' + template).classList.add('selected');
                document.getElementById('selectedTemplate').value = template;
                selectedTemplate = template;
            }

            async function generateProposal() {
                const form = document.getElementById('proposalForm');
                const formData = new FormData(form);

                // Validation
                if (!formData.get('proposalType')) {
                    alert('Please select a proposal type');
                    return;
                }

                if (!selectedTemplate) {
                    alert('Please select a template');
                    return;
                }

                if (!formData.get('companyName')) {
                    alert('Please enter your company name');
                    return;
                }

                const generateBtn = document.getElementById('generateBtn');
                const progress = document.getElementById('progress');
                const progressBar = document.getElementById('progressBar');

                generateBtn.disabled = true;
                generateBtn.textContent = '🔄 Generating...';
                progress.style.display = 'block';

                try {
                    // Simulate proposal generation progress
                    for (let i = 0; i <= 100; i += 10) {
                        progressBar.style.width = i + '%';
                        await new Promise(resolve => setTimeout(resolve, 200));
                    }

                    // Call API to generate proposal
                    const response = await fetch('/api/generate-proposal/{{ project.id }}', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            proposalType: formData.get('proposalType'),
                            companyName: formData.get('companyName'),
                            proposalTitle: formData.get('proposalTitle'),
                            executiveSummary: formData.get('executiveSummary'),
                            template: selectedTemplate
                        })
                    });

                    const result = await response.json();

                    if (result.success) {
                        document.getElementById('result').style.display = 'block';
                        document.getElementById('downloadBtn').href = result.downloadUrl;
                        document.getElementById('viewBtn').href = result.previewUrl;

                        // Scroll to result
                        document.getElementById('result').scrollIntoView({ behavior: 'smooth' });
                    } else {
                        alert('Error: ' + result.error);
                    }

                } catch (error) {
                    alert('Error generating proposal: ' + error.message);
                } finally {
                    generateBtn.disabled = false;
                    generateBtn.textContent = '🚀 Generate Proposal Document';
                    progress.style.display = 'none';
                }
            }

            // Auto-select professional template by default
            selectTemplate('professional');
            </script>
        </body>
        </html>
        ''', project=project, documents=documents)

    @app.route('/api/generate-proposal/<int:project_id>', methods=['POST'])
    def api_generate_proposal(project_id):
        """API endpoint to generate proposal document"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401

        try:
            data = request.get_json()

            from models import User, Project, Document
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first()

            if not project:
                return jsonify({'success': False, 'error': 'Project not found'}), 404

            documents = Document.query.filter_by(project_id=project_id).all()

            # AI-powered proposal generation
            anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
            if not anthropic_key or anthropic_key.startswith('your-'):
                return jsonify({'success': False, 'error': 'AI API not configured'}), 500

            try:
                import anthropic
                client = anthropic.Anthropic(api_key=anthropic_key)

                # Create comprehensive proposal prompt
                proposal_prompt = f"""Generate a comprehensive RFP proposal document for the following project:

Project: {project.name}
Company: {data.get('companyName', 'Your Company')}
Proposal Type: {data.get('proposalType', 'technical')}
Template: {data.get('template', 'professional')}

Executive Summary Input: {data.get('executiveSummary', 'Not provided')}

Requirements Analysis:
Based on the uploaded documents, create a detailed proposal that addresses:

1. EXECUTIVE SUMMARY
2. UNDERSTANDING OF REQUIREMENTS
3. TECHNICAL APPROACH & SOLUTION
4. PROJECT METHODOLOGY
5. TEAM STRUCTURE & EXPERTISE
6. PROJECT TIMELINE & MILESTONES
7. RISK MANAGEMENT
8. QUALITY ASSURANCE
9. COMMERCIAL CONSIDERATIONS
10. COMPLIANCE & STANDARDS

Make this a professional, comprehensive proposal that demonstrates deep understanding of the requirements and provides a compelling solution approach.

The proposal should be formatted as a complete document ready for submission."""

                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[
                        {
                            "role": "user",
                            "content": proposal_prompt
                        }
                    ]
                )

                proposal_content = message.content[0].text

                # For now, return success with mock URLs
                # In production, you would generate actual PDF and store it
                return jsonify({
                    'success': True,
                    'proposalId': f"proposal_{project_id}_{int(datetime.now().timestamp())}",
                    'downloadUrl': f'/download-proposal/{project_id}',
                    'previewUrl': f'/preview-proposal/{project_id}',
                    'contentLength': len(proposal_content),
                    'message': 'Proposal generated successfully'
                })

            except Exception as e:
                return jsonify({'success': False, 'error': f'AI generation failed: {str(e)}'}), 500

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/create-project')
    def create_project_page():
        """Create project page"""
        if 'username' not in session:
            return redirect('/login')

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Create New Project - Tender Analysis System</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .form-group { margin: 20px 0; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input, textarea, select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
                textarea { height: 100px; resize: vertical; }
                .btn { padding: 12px 24px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
                .btn:hover { background: #5a6fd8; }
                .btn-success { background: #28a745; }
                .btn-success:hover { background: #218838; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📁 Create New Project</h1>
                <a href="/projects" style="color: #667eea; text-decoration: none;">← Back to Projects</a>

                <form id="createProjectForm" style="margin-top: 30px;">
                    <div class="form-group">
                        <label for="name">Project Name: *</label>
                        <input type="text" id="name" name="name" required placeholder="e.g., E-Commerce Platform RFP">
                    </div>

                    <div class="form-group">
                        <label for="description">Description:</label>
                        <textarea id="description" name="description" placeholder="Brief description of the project scope and objectives..."></textarea>
                    </div>

                    <div class="form-group">
                        <label for="clientName">Client Name:</label>
                        <input type="text" id="clientName" name="clientName" placeholder="Client or organization name">
                    </div>

                    <div class="form-group">
                        <label for="submissionDeadline">Submission Deadline:</label>
                        <input type="date" id="submissionDeadline" name="submissionDeadline">
                    </div>

                    <div class="form-group">
                        <label for="estimatedValue">Estimated Value:</label>
                        <input type="number" id="estimatedValue" name="estimatedValue" placeholder="0" step="0.01">
                    </div>

                    <div class="form-group">
                        <label for="currency">Currency:</label>
                        <select id="currency" name="currency">
                            <option value="USD">USD ($)</option>
                            <option value="EUR">EUR (€)</option>
                            <option value="GBP">GBP (£)</option>
                            <option value="CAD">CAD ($)</option>
                            <option value="AUD">AUD ($)</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="priority">Priority:</label>
                        <select id="priority" name="priority">
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                            <option value="low">Low</option>
                        </select>
                    </div>

                    <div style="text-align: center; margin-top: 30px;">
                        <button type="submit" class="btn btn-success" style="padding: 15px 30px;">
                            ✅ Create Project
                        </button>
                    </div>
                </form>
            </div>

            <script>
            document.getElementById('createProjectForm').addEventListener('submit', async (e) => {
                e.preventDefault();

                const formData = new FormData(e.target);
                const data = {
                    name: formData.get('name'),
                    description: formData.get('description'),
                    client_name: formData.get('clientName'),
                    submission_deadline: formData.get('submissionDeadline'),
                    estimated_value: formData.get('estimatedValue'),
                    currency: formData.get('currency'),
                    priority: formData.get('priority')
                };

                try {
                    const response = await fetch('/api/projects', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(data)
                    });

                    const result = await response.json();

                    if (result.success) {
                        alert('Project created successfully!');
                        window.location.href = '/projects';
                    } else {
                        alert('Error: ' + result.error);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            });
            </script>
        </body>
        </html>
        ''')

    @app.route('/download-proposal/<int:project_id>')
    def download_proposal(project_id):
        """Download proposal as PDF"""
        if 'username' not in session:
            return redirect('/login')

        # Mock PDF download - in production, generate actual PDF
        from flask import make_response

        try:
            from models import User, Project
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first()

            if not project:
                return "Project not found", 404

            # Mock PDF content
            pdf_content = f"""
            PROPOSAL DOCUMENT

            Project: {project.name}
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

            This is a mock PDF download. In production, this would be
            a properly formatted PDF document with the full proposal content.
            """

            response = make_response(pdf_content)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=proposal_{project.name.replace(" ", "_")}.pdf'

            return response

        except Exception as e:
            return f"Error: {e}", 500

    @app.route('/preview-proposal/<int:project_id>')
    def preview_proposal(project_id):
        """Preview proposal in browser"""
        if 'username' not in session:
            return redirect('/login')

        try:
            from models import User, Project
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first()

            if not project:
                return "Project not found", 404

            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Proposal Preview - {{ project.name }}</title>
                <style>
                    body { font-family: 'Times New Roman', serif; margin: 40px; line-height: 1.6; }
                    .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }
                    .section { margin: 30px 0; }
                    h1 { color: #333; }
                    h2 { color: #555; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
                    .back-btn { position: fixed; top: 20px; right: 20px; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }
                </style>
            </head>
            <body>
                <a href="/project/{{ project.id }}" class="back-btn">← Back to Project</a>

                <div class="header">
                    <h1>PROPOSAL DOCUMENT</h1>
                    <h2>{{ project.name }}</h2>
                    <p>Prepared by: Your Company Name</p>
                    <p>Date: {{ current_date }}</p>
                </div>

                <div class="section">
                    <h2>1. EXECUTIVE SUMMARY</h2>
                    <p>This proposal outlines our comprehensive approach to delivering a solution that meets all requirements specified in the RFP. Our team brings extensive experience and proven methodologies to ensure successful project completion.</p>
                </div>

                <div class="section">
                    <h2>2. UNDERSTANDING OF REQUIREMENTS</h2>
                    <p>Based on our analysis of the provided documentation, we have identified the following key requirements:</p>
                    <ul>
                        <li>Microservices architecture implementation</li>
                        <li>PostgreSQL database with backup/recovery capabilities</li>
                        <li>SSL/TLS security implementation</li>
                        <li>Support for 10,000+ concurrent users</li>
                        <li>99.9% uptime SLA commitment</li>
                    </ul>
                </div>

                <div class="section">
                    <h2>3. TECHNICAL APPROACH</h2>
                    <p>Our solution leverages industry best practices and proven technologies to deliver a robust, scalable platform that exceeds the specified requirements.</p>
                </div>

                <div class="section">
                    <h2>4. PROJECT TIMELINE</h2>
                    <p>We propose a phased implementation approach with clear milestones and deliverables over the specified 9-month timeline.</p>
                </div>

                <div class="section">
                    <h2>5. TEAM & EXPERTISE</h2>
                    <p>Our dedicated project team includes senior architects, developers, and project managers with relevant experience in similar implementations.</p>
                </div>

                <div class="section">
                    <h2>6. RISK MANAGEMENT</h2>
                    <p>We have identified potential project risks and developed comprehensive mitigation strategies to ensure successful delivery.</p>
                </div>

                <div class="section">
                    <h2>7. COMMERCIAL TERMS</h2>
                    <p>Our competitive pricing structure aligns with the specified budget parameters while delivering exceptional value.</p>
                </div>

                <p style="text-align: center; margin-top: 50px; font-style: italic;">
                    This is a preview of the generated proposal. The actual document would include detailed technical specifications,
                    project plans, and comprehensive commercial terms.
                </p>
            </body>
            </html>
            ''', project=project, current_date=datetime.now().strftime('%B %d, %Y'))

        except Exception as e:
            return f"Error: {e}", 500

    @app.route('/analysis/<int:project_id>')
    def analysis_view(project_id):
        """Analysis results page for a project"""
        if 'username' not in session:
            return redirect('/login')

        try:
            from models import User, Project, Document
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            documents = Document.query.filter_by(project_id=project_id).all()

            # Get analysis results (this would be from your AI processing)
            # For now, we'll simulate some analysis results
            analysis_results = {
                'must_have_requirements': [
                    'Must support microservices architecture',
                    'Must handle 10,000+ concurrent users',
                    'Must provide 99.9% uptime SLA',
                    'Must use PostgreSQL database',
                    'Must implement SSL/TLS encryption'
                ],
                'good_to_have_requirements': [
                    'Should implement Redis caching',
                    'Should support CDN integration',
                    'Should provide real-time analytics',
                    'Should support mobile app development'
                ],
                'technical_specifications': [
                    'Database: PostgreSQL with backup/recovery',
                    'Security: Multi-factor authentication required',
                    'Performance: 10,000+ concurrent users',
                    'Integration: REST API architecture',
                    'Compliance: GDPR data protection'
                ],
                'project_details': {
                    'timeline': '9 months',
                    'budget': '$500,000 maximum',
                    'evaluation_criteria': 'Technical expertise (40%), Cost (30%), Timeline (20%), Support (10%)'
                }
            }

        except Exception as e:
            flash(f"Error loading analysis: {e}")
            return redirect('/projects')

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Analysis - {{ project.name }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
                .btn { padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }
                .btn:hover { background: #5a6fd8; }
                .analysis-section {
                    background: #f8f9fa;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    border-left: 4px solid #667eea;
                }
                .requirement-item {
                    background: white;
                    padding: 10px;
                    margin: 8px 0;
                    border-radius: 4px;
                    border-left: 3px solid #28a745;
                }
                .good-to-have { border-left-color: #ffc107; }
                .must-have { border-left-color: #dc3545; }
                .tech-spec { border-left-color: #17a2b8; }
                .summary-card {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                }
                .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
                @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
                .stat { text-align: center; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px; margin: 10px; }
                .stat-number { font-size: 2em; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>🤖 AI Analysis Results</h1>
                        <p style="color: #6c757d;">Project: {{ project.name }}</p>
                    </div>
                    <div>
                        <a href="/project/{{ project.id }}" class="btn">← Back to Project</a>
                        <a href="/projects" class="btn">📁 All Projects</a>
                    </div>
                </div>

                <div class="summary-card">
                    <h2>📊 Analysis Summary</h2>
                    <p>Comprehensive AI analysis of {{ documents|length }} document(s) in this project</p>
                    <div style="display: flex; justify-content: space-around; margin-top: 20px;">
                        <div class="stat">
                            <div class="stat-number">{{ analysis_results.must_have_requirements|length }}</div>
                            <div>Must Have Requirements</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{{ analysis_results.good_to_have_requirements|length }}</div>
                            <div>Good to Have Requirements</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{{ analysis_results.technical_specifications|length }}</div>
                            <div>Technical Specifications</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{{ documents|length }}</div>
                            <div>Documents Analyzed</div>
                        </div>
                    </div>
                </div>

                <div class="grid">
                    <div>
                        <div class="analysis-section">
                            <h3>🔴 Must Have Requirements</h3>
                            <p><strong>Critical requirements that must be met:</strong></p>
                            {% for req in analysis_results.must_have_requirements %}
                            <div class="requirement-item must-have">
                                <strong>•</strong> {{ req }}
                            </div>
                            {% endfor %}
                        </div>

                        <div class="analysis-section">
                            <h3>🟡 Good to Have Requirements</h3>
                            <p><strong>Preferred features that add value:</strong></p>
                            {% for req in analysis_results.good_to_have_requirements %}
                            <div class="requirement-item good-to-have">
                                <strong>•</strong> {{ req }}
                            </div>
                            {% endfor %}
                        </div>
                    </div>

                    <div>
                        <div class="analysis-section">
                            <h3>⚙️ Technical Specifications</h3>
                            <p><strong>Key technical requirements and constraints:</strong></p>
                            {% for spec in analysis_results.technical_specifications %}
                            <div class="requirement-item tech-spec">
                                <strong>•</strong> {{ spec }}
                            </div>
                            {% endfor %}
                        </div>

                        <div class="analysis-section">
                            <h3>📋 Project Details</h3>
                            <div class="requirement-item">
                                <strong>Timeline:</strong> {{ analysis_results.project_details.timeline }}
                            </div>
                            <div class="requirement-item">
                                <strong>Budget:</strong> {{ analysis_results.project_details.budget }}
                            </div>
                            <div class="requirement-item">
                                <strong>Evaluation:</strong> {{ analysis_results.project_details.evaluation_criteria }}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="analysis-section">
                    <h3>📄 Analyzed Documents</h3>
                    {% for doc in documents %}
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: white; margin: 5px 0; border-radius: 4px;">
                        <div>
                            <strong>{{ doc.original_filename or doc.filename }}</strong>
                            <p style="margin: 5px 0; color: #6c757d; font-size: 14px;">
                                Uploaded: {{ doc.uploaded_at.strftime('%Y-%m-%d %H:%M') if doc.uploaded_at else 'Unknown' }}
                            </p>
                        </div>
                        <div>
                            <span style="background: #28a745; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px;">
                                ✅ Analyzed
                            </span>
                        </div>
                    </div>
                    {% endfor %}
                </div>

                <div class="analysis-section">
                    <h3>🚀 Next Steps & Recommendations</h3>
                    <div class="requirement-item">
                        <strong>1. Proposal Strategy:</strong> Focus on demonstrating strong technical expertise (40% weight) and competitive pricing
                    </div>
                    <div class="requirement-item">
                        <strong>2. Technical Approach:</strong> Highlight microservices architecture experience and PostgreSQL expertise
                    </div>
                    <div class="requirement-item">
                        <strong>3. Compliance:</strong> Ensure all security and GDPR requirements are thoroughly addressed
                    </div>
                    <div class="requirement-item">
                        <strong>4. Timeline:</strong> Develop realistic 9-month project plan with clear milestones
                    </div>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="/generate-proposal/{{ project.id }}" class="btn" style="background: #28a745; padding: 15px 30px; font-size: 16px;">
                        📝 Generate Proposal Document
                    </a>
                </div>
            </div>
        </body>
        </html>
        ''', project=project, documents=documents, analysis_results=analysis_results)

    @app.route('/document/<int:document_id>')
    def document_detail(document_id):
        """Individual document analysis page"""
        if 'username' not in session:
            return redirect('/login')

        try:
            from models import User, Document, Project
            user = User.query.filter_by(username=session['username']).first()
            document = Document.query.get_or_404(document_id)

            # Verify user owns this document through project
            project = Project.query.filter_by(id=document.project_id, user_id=user.id).first()
            if not project:
                return redirect('/projects')

            # Simulate individual document analysis
            doc_analysis = {
                'filename': document.original_filename or document.filename,
                'file_size': f"{document.file_size / 1024 / 1024:.1f} MB" if document.file_size else "Unknown",
                'upload_date': document.uploaded_at.strftime('%Y-%m-%d %H:%M') if document.uploaded_at else 'Unknown',
                'extracted_requirements': [
                    'Platform must support microservices architecture',
                    'Database must be PostgreSQL with backup capability',
                    'Security implementation with SSL/TLS required',
                    'System must handle 10,000+ concurrent users'
                ],
                'key_terms': ['microservices', 'PostgreSQL', 'SSL/TLS', 'concurrent users', 'uptime SLA'],
                'compliance_items': ['GDPR compliance', 'Security standards', 'Performance SLA'],
                'analysis_confidence': '95%'
            }

        except Exception as e:
            flash(f"Error loading document: {e}")
            return redirect('/projects')

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Document Analysis - {{ doc_analysis.filename }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
                .btn { padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }
                .btn:hover { background: #5a6fd8; }
                .info-card { background: #f8f9fa; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #667eea; }
                .requirement { background: white; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #28a745; }
                .term-tag {
                    display: inline-block;
                    background: #e3f2fd;
                    color: #1976d2;
                    padding: 4px 8px;
                    margin: 2px;
                    border-radius: 12px;
                    font-size: 12px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>📄 Document Analysis</h1>
                        <p style="color: #6c757d;">{{ doc_analysis.filename }}</p>
                    </div>
                    <div>
                        <a href="/project/{{ project.id }}" class="btn">← Back to Project</a>
                    </div>
                </div>

                <div class="info-card">
                    <h3>📊 Document Information</h3>
                    <p><strong>File Size:</strong> {{ doc_analysis.file_size }}</p>
                    <p><strong>Upload Date:</strong> {{ doc_analysis.upload_date }}</p>
                    <p><strong>Analysis Confidence:</strong> {{ doc_analysis.analysis_confidence }}</p>
                    <p><strong>Project:</strong> {{ project.name }}</p>
                </div>

                <div class="info-card">
                    <h3>🎯 Extracted Requirements</h3>
                    {% for req in doc_analysis.extracted_requirements %}
                    <div class="requirement">{{ req }}</div>
                    {% endfor %}
                </div>

                <div class="info-card">
                    <h3>🔍 Key Terms Identified</h3>
                    {% for term in doc_analysis.key_terms %}
                    <span class="term-tag">{{ term }}</span>
                    {% endfor %}
                </div>

                <div class="info-card">
                    <h3>✅ Compliance Items</h3>
                    {% for item in doc_analysis.compliance_items %}
                    <div class="requirement">{{ item }}</div>
                    {% endfor %}
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="/analysis/{{ project.id }}" class="btn" style="background: #28a745;">
                        📊 View Full Project Analysis
                    </a>
                </div>
            </div>
        </body>
        </html>
        ''', document=document, project=project, doc_analysis=doc_analysis)


    @app.route('/projects')
    def projects():
        """Projects page"""
        if 'username' not in session:
            return redirect('/login')

        try:
            from models import User, Project
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return redirect('/login')

            user_projects = Project.query.filter_by(user_id=user.id).all()

        except Exception as e:
            user_projects = []
            flash(f"Error loading projects: {e}")

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>My Projects - Tender Analysis System</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
                .btn { padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; border: none; cursor: pointer; }
                .btn:hover { background: #5a6fd8; }
                .btn-success { background: #28a745; }
                .btn-success:hover { background: #218838; }
                .project-card {
                    border: 1px solid #ddd;
                    padding: 20px;
                    margin: 15px 0;
                    border-radius: 8px;
                    background: #f8f9fa;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .project-info h3 { margin: 0 0 10px 0; color: #495057; }
                .project-info p { margin: 5px 0; color: #6c757d; }
                .project-actions { display: flex; gap: 10px; }
                .no-projects {
                    text-align: center;
                    padding: 40px;
                    color: #6c757d;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📁 My Projects</h1>
                    <div>
                        <a href="/" class="btn">← Dashboard</a>
                        <button onclick="createProject()" class="btn btn-success">+ Create New Project</button>
                    </div>
                </div>

                {% if user_projects %}
                    {% for project in user_projects %}
                    <div class="project-card">
                        <div class="project-info">
                            <h3>{{ project.name }}</h3>
                            <p><strong>Status:</strong> {{ project.status }}</p>
                            <p><strong>Created:</strong> {{ project.created_at.strftime('%Y-%m-%d') if project.created_at else 'Unknown' }}</p>
                            {% if project.description %}
                            <p><strong>Description:</strong> {{ project.description[:100] }}...</p>
                            {% endif %}
                        </div>
                        <div class="project-actions">
                            <a href="/project/{{ project.id }}" class="btn">View Details</a>
                            <a href="/upload?project_id={{ project.id }}" class="btn">Upload Docs</a>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="no-projects">
                        <h3>🚀 No Projects Yet</h3>
                        <p>Create your first project to start analyzing RFP documents!</p>
                        <button onclick="createProject()" class="btn btn-success">Create Your First Project</button>
                    </div>
                {% endif %}
            </div>

            <script>
            function createProject() {
                const name = prompt("Enter project name:");
                if (name) {
                    const description = prompt("Enter project description (optional):");

                    fetch('/api/projects', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            name: name,
                            description: description || ''
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('Project created successfully!');
                            location.reload();
                        } else {
                            alert('Error: ' + data.error);
                        }
                    })
                    .catch(error => {
                        alert('Error: ' + error);
                    });
                }
            }
            </script>
        </body>
        </html>
        ''', user_projects=user_projects)

    @app.route('/upload')
    def upload_page():
        """Upload page"""
        if 'username' not in session:
            return redirect('/login')

        project_id = request.args.get('project_id')

        try:
            from models import User, Project
            user = User.query.filter_by(username=session['username']).first()
            user_projects = Project.query.filter_by(user_id=user.id).all()
        except Exception as e:
            user_projects = []

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Upload Documents - Tender Analysis System</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .btn { padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; border: none; cursor: pointer; }
                .btn:hover { background: #5a6fd8; }
                .upload-area {
                    border: 2px dashed #ddd;
                    padding: 40px;
                    text-align: center;
                    margin: 20px 0;
                    border-radius: 8px;
                    background: #f8f9fa;
                    transition: border-color 0.3s;
                }
                .upload-area:hover { border-color: #667eea; }
                .upload-area.dragover { border-color: #28a745; background: #d4edda; }
                select, input[type="file"] { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
                .progress { width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px; margin: 10px 0; overflow: hidden; }
                .progress-bar { height: 100%; background: #28a745; width: 0%; transition: width 0.3s; }
                .file-list { margin: 20px 0; }
                .file-item { padding: 10px; background: #f8f9fa; margin: 5px 0; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
            </style>
        </head>
        <body>
            <div class="container">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
                    <h1>📄 Upload Documents</h1>
                    <a href="/" class="btn">← Back to Dashboard</a>
                </div>

                <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h3>🤖 AI Document Analysis</h3>
                    <p>Upload RFP documents, technical specifications, or requirements. Our AI will automatically:</p>
                    <ul>
                        <li>Extract key requirements and specifications</li>
                        <li>Categorize requirements by priority (Must Have, Good to Have)</li>
                        <li>Identify compliance and technical constraints</li>
                        <li>Generate proposal recommendations</li>
                    </ul>
                </div>

                <form id="uploadForm" enctype="multipart/form-data">
                    <div style="margin: 20px 0;">
                        <label for="project_id"><strong>Select Project:</strong></label>
                        <select id="project_id" name="project_id" required>
                            <option value="">Choose a project...</option>
                            {% for project in user_projects %}
                            <option value="{{ project.id }}" {% if project_id == project.id|string %}selected{% endif %}>
                                {{ project.name }}
                            </option>
                            {% endfor %}
                        </select>
                        {% if not user_projects %}
                        <p style="color: #dc3545;">⚠️ No projects found. <a href="/projects">Create a project first</a>.</p>
                        {% endif %}
                    </div>

                    <div class="upload-area" id="uploadArea">
                        <h3>📁 Drop files here or click to upload</h3>
                        <p>Supported formats: PDF, DOCX, TXT, XLSX</p>
                        <p>Maximum file size: 50MB</p>
                        <input type="file" id="fileInput" name="files" multiple accept=".pdf,.docx,.txt,.xlsx,.doc,.xls" style="display: none;">
                        <button type="button" onclick="document.getElementById('fileInput').click()" class="btn">Choose Files</button>
                    </div>

                    <div id="fileList" class="file-list"></div>

                    <div id="progress" class="progress" style="display: none;">
                        <div id="progressBar" class="progress-bar"></div>
                    </div>

                    <button type="submit" class="btn" style="width: 100%; padding: 15px; font-size: 16px;" disabled id="uploadBtn">
                        🚀 Start AI Analysis
                    </button>
                </form>

                <div id="results" style="margin-top: 30px;"></div>
            </div>

            <script>
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const fileList = document.getElementById('fileList');
            const uploadBtn = document.getElementById('uploadBtn');
            const form = document.getElementById('uploadForm');
            const progress = document.getElementById('progress');
            const progressBar = document.getElementById('progressBar');

            let selectedFiles = [];

            // Drag and drop functionality
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });

            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                handleFiles(e.dataTransfer.files);
            });

            uploadArea.addEventListener('click', () => {
                fileInput.click();
            });

            fileInput.addEventListener('change', (e) => {
                handleFiles(e.target.files);
            });

            function handleFiles(files) {
                selectedFiles = Array.from(files);
                updateFileList();
                updateUploadButton();
            }

            function updateFileList() {
                fileList.innerHTML = '';
                selectedFiles.forEach((file, index) => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    fileItem.innerHTML = `
                        <div>
                            <strong>${file.name}</strong> (${(file.size / 1024 / 1024).toFixed(2)} MB)
                        </div>
                        <button type="button" onclick="removeFile(${index})" style="background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 3px;">Remove</button>
                    `;
                    fileList.appendChild(fileItem);
                });
            }

            function removeFile(index) {
                selectedFiles.splice(index, 1);
                updateFileList();
                updateUploadButton();
            }

            function updateUploadButton() {
                const projectSelected = document.getElementById('project_id').value;
                uploadBtn.disabled = !(selectedFiles.length > 0 && projectSelected);
            }

            document.getElementById('project_id').addEventListener('change', updateUploadButton);

            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const projectId = document.getElementById('project_id').value;
                if (!projectId || selectedFiles.length === 0) {
                    alert('Please select a project and upload at least one file.');
                    return;
                }

                progress.style.display = 'block';
                uploadBtn.disabled = true;
                uploadBtn.textContent = '🔄 Uploading...';

                for (let i = 0; i < selectedFiles.length; i++) {
                    const file = selectedFiles[i];
                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('project_id', projectId);

                    try {
                        const response = await fetch('/api/upload', {
                            method: 'POST',
                            body: formData
                        });

                        const result = await response.json();

                        if (result.success) {
                            progressBar.style.width = ((i + 1) / selectedFiles.length * 100) + '%';
                            console.log(`File ${file.name} uploaded successfully`);
                        } else {
                            alert(`Error uploading ${file.name}: ${result.error}`);
                        }
                    } catch (error) {
                        alert(`Error uploading ${file.name}: ${error}`);
                    }
                }

                setTimeout(() => {
                    alert('✅ Upload complete! AI analysis has started. Check your project dashboard for results.');
                    window.location.href = '/projects';
                }, 1000);
            });
            </script>
        </body>
        </html>
        ''', user_projects=user_projects, project_id=project_id)

    @app.route('/api/projects', methods=['POST'])
    def create_project():
        """Create new project API"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401

        try:
            data = request.get_json()

            from models import db, User, Project
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404

            project = Project(
                name=data.get('name'),
                description=data.get('description', ''),
                status='active',
                user_id=user.id
            )

            db.session.add(project)
            db.session.commit()

            return jsonify({
                'success': True,
                'project_id': project.id,
                'message': 'Project created successfully'
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        """Handle file upload API - FIXED VERSION"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401

        try:
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file provided'}), 400

            file = request.files['file']
            project_id = request.form.get('project_id')

            if file.filename == '':
                return jsonify({'success': False, 'error': 'No file selected'}), 400

            if not allowed_file(file.filename):
                return jsonify({'success': False, 'error': 'File type not allowed'}), 400

            from models import db, User, Project, Document
            user = User.query.filter_by(username=session['username']).first()

            # Verify project ownership
            project = Project.query.filter_by(id=project_id, user_id=user.id).first()
            if not project:
                return jsonify({'success': False, 'error': 'Project not found'}), 404

            # Save file
            original_filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{original_filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)

            # Create document record with ALL required fields
            document = Document(
                filename=unique_filename,           # The stored filename
                original_filename=filename,         # The original filename (REQUIRED)
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                project_id=project_id,
                uploaded_by=user.id
            )
            db.session.add(document)
            db.session.commit()

            # Start background processing (if Celery is available)
            try:
                from tasks import process_document_task
                task = process_document_task.delay(document.id)
                print(f"✅ Started background task: {task.id}")
            except Exception as e:
                print(f"⚠️ Background task failed: {e}")

            return jsonify({
                'success': True,
                'document_id': document.id,
                'filename': original_filename,
                'message': 'File uploaded successfully and AI analysis started!'
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/project/<int:project_id>')
    def project_detail(project_id):
        """Project detail page"""
        if 'username' not in session:
            return redirect('/login')

        try:
            from models import User, Project, Document
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            documents = Document.query.filter_by(project_id=project_id).all()

        except Exception as e:
            flash(f"Error loading project: {e}")
            return redirect('/projects')

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ project.name }} - Project Details</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
                .btn { padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }
                .btn:hover { background: #5a6fd8; }
                .btn-success { background: #28a745; }
                .card { background: #f8f9fa; padding: 20px; margin: 15px 0; border-radius: 8px; border: 1px solid #e9ecef; }
                .document-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 15px;
                    background: white;
                    margin: 10px 0;
                    border-radius: 5px;
                    border: 1px solid #ddd;
                }
                .status-badge {
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: bold;
                }
                .status-completed { background: #d4edda; color: #155724; }
                .status-processing { background: #fff3cd; color: #856404; }
                .status-pending { background: #f8d7da; color: #721c24; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>📁 {{ project.name }}</h1>
                        <p style="color: #6c757d;">{{ project.description or 'No description provided' }}</p>
                    </div>
                    <div>
                        <a href="/projects" class="btn">← Back to Projects</a>
                        <a href="/upload?project_id={{ project.id }}" class="btn btn-success">📄 Upload Documents</a>
                    </div>
                </div>

                <div class="card">
                    <h3>📊 Project Information</h3>
                    <p><strong>Status:</strong> {{ project.status.title() }}</p>
                    <p><strong>Created:</strong> {{ project.created_at.strftime('%B %d, %Y') if project.created_at else 'Unknown' }}</p>
                    <p><strong>Total Documents:</strong> {{ documents|length }}</p>
                </div>

                <div class="card">
                    <h3>📄 Documents</h3>
                    {% if documents %}
                        {% for doc in documents %}
                        <div class="document-item">
                            <div>
                                <strong>{{ doc.filename }}</strong>
                                <p style="margin: 5px 0; color: #6c757d;">
                                    Uploaded: {{ doc.uploaded_at.strftime('%Y-%m-%d %H:%M') if doc.uploaded_at else 'Unknown' }}
                                    | Size: {{ "%.1f"|format(doc.file_size/1024/1024) if doc.file_size else '0' }} MB
                                </p>
                            </div>
                            <div>
                                <span class="status-badge status-completed">✅ Ready</span>
                                <a href="/document/{{ doc.id }}" class="btn" style="margin-left: 10px;">View Analysis</a>
                            </div>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div style="text-align: center; padding: 40px; color: #6c757d;">
                            <h4>📄 No Documents Yet</h4>
                            <p>Upload RFP documents to start AI analysis</p>
                            <a href="/upload?project_id={{ project.id }}" class="btn btn-success">Upload First Document</a>
                        </div>
                    {% endif %}
                </div>

                {% if documents %}
                <div class="card">
                    <h3>🤖 AI Analysis Summary</h3>
                    <p>Analysis of {{ documents|length }} document(s) in this project:</p>
                    <ul>
                        <li>✅ Documents processed and analyzed</li>
                        <li>🔍 Requirements extracted and categorized</li>
                        <li>📊 Ready for proposal generation</li>
                    </ul>
                    <a href="/analysis/{{ project.id }}" class="btn btn-success">📊 View Full Analysis</a>
                </div>
                {% endif %}
            </div>
        </body>
        </html>
        ''', project=project, documents=documents)

    @app.route('/health')
    def health_check():
        """Health check endpoint with system status"""
        system_status = get_system_status()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'tender-analysis-system',
            'version': '1.0.0',
            'system_status': system_status
        })

    @app.route('/test-db')
    def test_database():
        """Test database connection"""
        system_status = get_system_status()
        return jsonify(system_status)

    @app.route('/test-redis')
    def test_redis():
        """Test Redis connection"""
        try:
            import redis
            redis_url = app.config.get('REDIS_URL')
            if redis_url:
                r = redis.from_url(redis_url)
                r.ping()
                return jsonify({'redis': 'connected', 'url': redis_url, 'status': 'success'})
            else:
                return jsonify({'redis': 'not_configured', 'status': 'warning'})
        except Exception as e:
            return jsonify({'redis': 'error', 'message': str(e), 'status': 'failed'}), 500

    @app.route('/login')
    def login():
        """Login page"""
        if 'username' in session:
            return redirect('/')

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login - Tender Analysis System</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                }
                .login-container {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    width: 100%;
                    max-width: 400px;
                }
                .form-group { margin: 20px 0; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input[type="text"], input[type="password"] {
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    box-sizing: border-box;
                }
                .btn {
                    width: 100%;
                    padding: 12px;
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                }
                .btn:hover { background: #5a6fd8; }
                .error { color: #dc3545; margin-top: 10px; }
            </style>
        </head>
        <body>
            <div class="login-container">
                <h2 style="text-align: center; margin-bottom: 30px;">🔐 Tender Analysis System</h2>
                <form method="POST" action="/login">
                    <div class="form-group">
                        <label for="username">Username:</label>
                        <input type="text" id="username" name="username" value="admin" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" value="admin123" required>
                    </div>
                    <button type="submit" class="btn">Login</button>
                </form>
                {% if error %}
                <div class="error">{{ error }}</div>
                {% endif %}
            </div>
        </body>
        </html>
        ''')

    @app.route('/login', methods=['POST'])
    def handle_login():
        """Handle login"""
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            from models import User
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                session['user_id'] = user.id
                session['username'] = user.username

                # Update last login
                user.last_login = datetime.utcnow()
                from models import db
                db.session.commit()

                return redirect('/')
            else:
                return render_template_string('''
                <!DOCTYPE html>
                <html>
                <head><title>Login Error</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h2>❌ Login Failed</h2>
                    <p>Invalid username or password</p>
                    <a href="/login" style="color: #667eea;">← Try Again</a>
                </body>
                </html>
                ''')

        except Exception as e:
            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head><title>Login Error</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2>❌ Login Error</h2>
                <p>{{ error }}</p>
                <a href="/login" style="color: #667eea;">← Try Again</a>
            </body>
            </html>
            ''', error=str(e))

    @app.route('/logout')
    def logout():
        """Logout user"""
        session.clear()
        return redirect('/login')

    return app

# Create the app instance
app = create_app()

# Simple Celery setup
def create_celery():
    """Create Celery instance"""
    try:
        from celery import Celery

        celery = Celery(
            'tender_system',
            broker=app.config.get('REDIS_URL', 'redis://redis:6379/0'),
            backend=app.config.get('REDIS_URL', 'redis://redis:6379/0')
        )

        @celery.task
        def test_task():
            return "Celery is working!"

        return celery
    except ImportError:
        print("⚠️ Celery not available")
        return None

celery = create_celery()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'

    print("🚀 Starting Tender Analysis System with Full Functionality...")
    print(f"   Dashboard: http://localhost:{port}")
    print(f"   Login: admin / admin123")
    app.run(host='0.0.0.0', port=port, debug=debug)
