#!/usr/bin/env python3
"""
Complete main.py with full functionality - CLEANED VERSION
"""

import os
import sys
import uuid
from flask import Flask, jsonify, render_template_string, request, redirect, url_for, session, flash, send_file, make_response
from werkzeug.utils import secure_filename
from datetime import datetime
from dotenv import load_dotenv
from real_analysis_system import get_real_analysis_results, get_real_document_analysis
from models import Partner, PartnerProduct, PartnerRecommendation
from agents.partner_recommendation_agent import PartnerRecommendationAgent


# Load environment variables
load_dotenv()

# Ensure current directory is in Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import our modules
from models import db
from document_processor import DocumentProcessor

# File upload configuration
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'xlsx', 'xls'}

def login_required(f):
    """Simple login requirement decorator"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:password@db:5432/tender_system')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 52428800))  # 50MB

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize database
    db.init_app(app)

    # Initialize document processor
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_api_key:
        document_processor = DocumentProcessor(anthropic_api_key, app.config['UPLOAD_FOLDER'])
        app.config['DOCUMENT_PROCESSOR'] = document_processor
    else:
        print("⚠️ ANTHROPIC_API_KEY not configured")
        app.config['DOCUMENT_PROCESSOR'] = None

    # Create tables
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Database error: {e}")

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
            from models import User, Project, Document
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
            redis_url = app.config.get('REDIS_URL') or os.getenv('REDIS_URL')
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

    # ========================================
    # AUTHENTICATION ROUTES
    # ========================================

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
                    /*background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);*/
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
                db.session.commit()

                return redirect('/')
            else:
                flash('Invalid username or password')
                return redirect('/login')

        except Exception as e:
            flash(f'Login error: {str(e)}')
            return redirect('/login')

    @app.route('/logout')
    def logout():
        """Logout user"""
        session.clear()
        return redirect('/login')

    # ========================================
    # MAIN DASHBOARD
    # ========================================

    @app.route('/')
    def index():
        """Main dashboard"""
        if 'username' not in session:
            return redirect('/login')

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
                    /*background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);*/
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
                .nav a.active { background: #667eea; color: white; }
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
                        <p>AI-Powered Multi-Document Analysis & Proposal Generation</p>
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
                    <a href="/settings/partners">🤝 Partner Management</a>
                    <a href="/health">🔍 System Health</a>
                </div>
                <div class="content">
                    {% if system_status.ready_for_upload %}
                    <!--div style="background: #d4edda; padding: 20px; border-radius: 8px; border-left: 5px solid #28a745; margin-bottom: 20px;">
                        <h2>🎉 System Ready!</h2>
                        <p>All components are working. You can start uploading and analyzing documents!</p>
                        <a href="/projects" class="btn btn-success">📁 Go to Projects</a>
                        <a href="/upload" class="btn btn-success">📄 Upload Documents</a>
                    </div-->
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

    # ========================================
    # PROJECT MANAGEMENT
    # ========================================

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

    @app.route('/debug-routes')
    def debug_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': rule.rule
            })
        return jsonify(routes)

    @app.route('/project/<project_id>')
    @app.route('/projects/<project_id>/details')
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
                                <strong>{{ doc.original_filename or doc.filename }}</strong>
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


# ========================================
# PARTNER MANAGEMENT ROUTES
# ========================================

    @app.route('/settings/partners')
    @login_required
    def partner_settings():
        """Partner management settings page"""
        try:
            from models import Partner
            partners = Partner.query.order_by(Partner.name).all()
        except Exception as e:
            partners = []
            flash(f"Error loading partners: {e}")

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Partner Management - Tender Analysis System</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .header { display: flex; justify-content: between; align-items: center; margin-bottom: 30px; }
                .btn { padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; border: none; cursor: pointer; }
                .btn:hover { background: #5a6fd8; }
                .btn-success { background: #28a745; } .btn-success:hover { background: #218838; }
                .partner-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin: 20px 0; }
                .partner-card {
                    background: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 8px;
                    padding: 20px;
                    transition: transform 0.2s;
                }
                .partner-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
                .partner-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
                .status-badge { padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }
                .status-active { background: #d4edda; color: #155724; }
                .status-preferred { background: #cce5ff; color: #004085; }
                .status-inactive { background: #f8d7da; color: #721c24; }
                .partner-stats { display: flex; justify-content: space-around; margin: 15px 0; }
                .stat { text-align: center; }
                .stat-number { font-size: 1.5em; font-weight: bold; color: #667eea; }
                .partner-actions { display: flex; gap: 10px; margin-top: 15px; }
                .no-partners { text-align: center; padding: 60px; color: #6c757d; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>🤝 Partner Management</h1>
                        <p style="color: #6c757d;">Manage partner companies and their products for cross-sell opportunities</p>
                    </div>
                    <div>
                        <a href="/" class="btn">← Dashboard</a>
                        <a href="/settings/partners/add" class="btn btn-success">+ Add Partner</a>
                    </div>
                </div>

                {% if partners %}
                <div class="partner-grid">
                    {% for partner in partners %}
                    <div class="partner-card">
                        <div class="partner-header">
                            <h4 style="margin: 0;">{{ partner.name }}</h4>
                            <span class="status-badge status-{{ partner.status.lower() }}">
                                {{ partner.status }}
                            </span>
                        </div>

                        <p style="color: #6c757d; margin: 10px 0;">
                            {{ partner.description or 'No description available' }}
                        </p>

                        <div class="partner-stats">
                            <div class="stat">
                                <div class="stat-number">{{ partner.products|length }}</div>
                                <small>Products</small>
                            </div>
                            <div class="stat">
                                <div class="stat-number">{{ partner.company_type }}</div>
                                <small>Type</small>
                            </div>
                        </div>

                        {% if partner.contact_email %}
                        <p style="font-size: 14px; margin: 10px 0;">
                            <i>📧</i> {{ partner.contact_email }}
                        </p>
                        {% endif %}

                        {% if partner.website %}
                        <p style="font-size: 14px; margin: 10px 0;">
                            <i>🌐</i> <a href="{{ partner.website }}" target="_blank">{{ partner.website }}</a>
                        </p>
                        {% endif %}

                        <div class="partner-actions">
                            <a href="/settings/partners/{{ partner.id }}/products" class="btn" style="flex: 1; text-align: center;">
                                📦 Products ({{ partner.products|length }})
                            </a>
                            <button class="btn" style="background: #6c757d;">
                                ✏️ Edit
                            </button>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div class="no-partners">
                    <h3>🤝 No Partners Yet</h3>
                    <p>Start building your partner ecosystem by adding your first technology partner.</p>
                    <a href="/settings/partners/add" class="btn btn-success">+ Add First Partner</a>
                </div>
                {% endif %}

                <div style="margin-top: 40px; padding: 20px; background: #e3f2fd; border-radius: 8px;">
                    <h4>ℹ️ About Partner Management</h4>
                    <p>Partner management enables AI-powered cross-sell recommendations during proposal generation. The system analyzes project requirements and suggests relevant partner products that complement your solutions.</p>
                </div>
            </div>
        </body>
        </html>
        ''', partners=partners)

    @app.route('/settings/partners/add', methods=['GET', 'POST'])
    @login_required
    def add_partner():
        """Add new partner"""
        if request.method == 'POST':
            try:
                from models import Partner

                partner = Partner(
                    name=request.form['name'],
                    company_type=request.form['company_type'],
                    status=request.form['status'],
                    description=request.form.get('description'),
                    website=request.form.get('website'),
                    primary_contact=request.form.get('primary_contact'),
                    contact_email=request.form.get('contact_email'),
                    contact_phone=request.form.get('contact_phone'),
                    revenue_share_percentage=float(request.form.get('revenue_share', 0) or 0),
                    discount_level=float(request.form.get('discount_level', 0) or 0),
                    support_level=request.form['support_level']
                )

                db.session.add(partner)
                db.session.commit()

                flash('Partner added successfully!', 'success')
                return redirect('/settings/partners')

            except Exception as e:
                db.session.rollback()
                flash(f'Error adding partner: {str(e)}', 'error')

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Add Partner - Tender Analysis System</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
                .btn { padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; border: none; cursor: pointer; }
                .btn:hover { background: #5a6fd8; }
                .btn-success { background: #28a745; } .btn-success:hover { background: #218838; }
                .form-group { margin: 20px 0; }
                .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input, select, textarea {
                    width: 100%;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    box-sizing: border-box;
                }
                .help-card { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>➕ Add New Partner</h1>
                        <p style="color: #6c757d;">Add a technology partner to your ecosystem</p>
                    </div>
                    <a href="/settings/partners" class="btn">← Back to Partners</a>
                </div>

                <form method="POST">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="name">Company Name *</label>
                            <input type="text" id="name" name="name" required>
                        </div>
                        <div class="form-group">
                            <label for="company_type">Partner Type *</label>
                            <select id="company_type" name="company_type" required>
                                <option value="">Select Type</option>
                                <option value="STRATEGIC">Strategic Partner</option>
                                <option value="TECHNOLOGY">Technology Partner</option>
                                <option value="VENDOR">Vendor</option>
                                <option value="INTEGRATION">Integration Partner</option>
                            </select>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="status">Status *</label>
                            <select id="status" name="status" required>
                                <option value="ACTIVE">Active</option>
                                <option value="PREFERRED">Preferred</option>
                                <option value="INACTIVE">Inactive</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="website">Website</label>
                            <input type="url" id="website" name="website" placeholder="https://example.com">
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="description">Description</label>
                        <textarea id="description" name="description" rows="3" placeholder="Brief description of the partner company"></textarea>
                    </div>

                    <h4 style="margin-top: 30px;">Contact Information</h4>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="primary_contact">Primary Contact</label>
                            <input type="text" id="primary_contact" name="primary_contact">
                        </div>
                        <div class="form-group">
                            <label for="contact_email">Email</label>
                            <input type="email" id="contact_email" name="contact_email">
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="contact_phone">Phone</label>
                        <input type="tel" id="contact_phone" name="contact_phone">
                    </div>

                    <h4 style="margin-top: 30px;">Business Terms</h4>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="revenue_share">Revenue Share (%)</label>
                            <input type="number" id="revenue_share" name="revenue_share" min="0" max="100" step="0.1">
                        </div>
                        <div class="form-group">
                            <label for="discount_level">Discount Level (%)</label>
                            <input type="number" id="discount_level" name="discount_level" min="0" max="100" step="0.1">
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="support_level">Support Level</label>
                        <select id="support_level" name="support_level">
                            <option value="BASIC">Basic</option>
                            <option value="PREMIUM">Premium</option>
                            <option value="ENTERPRISE">Enterprise</option>
                        </select>
                    </div>

                    <div style="display: flex; gap: 10px; margin-top: 30px;">
                        <a href="/settings/partners" class="btn" style="background: #6c757d;">Cancel</a>
                        <button type="submit" class="btn btn-success" style="flex: 1;">💾 Add Partner</button>
                    </div>
                </form>

                <div class="help-card">
                    <h4>💡 Partner Types</h4>
                    <ul>
                        <li><strong>Strategic:</strong> Long-term partnerships with shared goals</li>
                        <li><strong>Technology:</strong> Software/hardware solution providers</li>
                        <li><strong>Vendor:</strong> Service or product suppliers</li>
                        <li><strong>Integration:</strong> System integration specialists</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        ''')

    @app.route('/settings/partners/<int:partner_id>/products')
    @login_required
    def partner_products(partner_id):
        """Manage products for a specific partner"""
        try:
            from models import Partner
            partner = Partner.query.get_or_404(partner_id)
        except Exception as e:
            flash(f"Error loading partner: {e}")
            return redirect('/settings/partners')

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ partner.name }} Products - Tender Analysis System</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
                .btn { padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; border: none; cursor: pointer; }
                .btn:hover { background: #5a6fd8; }
                .btn-success { background: #28a745; } .btn-success:hover { background: #218838; }
                .partner-info { background: #e3f2fd; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
                .product-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
                .product-card {
                    background: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 8px;
                    padding: 20px;
                    transition: transform 0.2s;
                }
                .product-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
                .product-header { display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px; }
                .category-badge { padding: 4px 8px; background: #1f4397; color: white; border-radius: 12px; font-size: 12px; }
                .complexity-badge { padding: 2px 6px; border-radius: 8px; font-size: 11px; font-weight: bold; }
                .complexity-low { background: #d4edda; color: #155724; }
                .complexity-medium { background: #fff3cd; color: #856404; }
                .complexity-high { background: #f8d7da; color: #721c24; }
                .product-tags { margin: 10px 0; }
                .tag { display: inline-block; background: #e9ecef; color: #495057; padding: 2px 8px; margin: 2px; border-radius: 10px; font-size: 12px; }
                .product-actions { display: flex; gap: 10px; margin-top: 15px; }
                .no-products { text-align: center; padding: 60px; color: #6c757d; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>📦 {{ partner.name }} Products</h1>
                        <p style="color: #6c757d;">Manage products and services for {{ partner.name }}</p>
                    </div>
                    <div>
                        <a href="/settings/partners" class="btn">← Back to Partners</a>
                        <a href="/settings/partners/{{ partner.id }}/products/add" class="btn btn-success">+ Add Product</a>
                    </div>
                </div>

                <div class="partner-info">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0;">{{ partner.name }}</h4>
                            <p style="margin: 5px 0; color: #666;">{{ partner.description or 'No description available' }}</p>
                        </div>
                        <div>
                            <span class="category-badge">{{ partner.company_type }}</span>
                            <span style="margin-left: 10px; color: #28a745; font-weight: bold;">{{ partner.status }}</span>
                        </div>
                    </div>
                </div>

                {% if partner.products %}
                <div class="product-grid">
                    {% for product in partner.products %}
                    <div class="product-card">
                        <div class="product-header">
                            <h5 style="margin: 0;">{{ product.product_name }}</h5>
                            <span class="category-badge">{{ product.category }}</span>
                        </div>

                        <p style="color: #6c757d; font-size: 14px; margin: 10px 0;">
                            {{ product.functionality[:120] }}{% if product.functionality|length > 120 %}...{% endif %}
                        </p>

                        <div style="margin: 15px 0;">
                            <span class="complexity-badge complexity-{{ product.integration_complexity.lower() }}">
                                {{ product.integration_complexity }} Integration
                            </span>
                            <span style="margin-left: 10px; font-size: 12px; color: #666;">
                                {% if product.api_available %}✅ API{% else %}❌ No API{% endif %}
                                {% if product.cloud_native %}| ☁️ Cloud{% endif %}
                            </span>
                        </div>

                        {% if product.technical_keywords %}
                        <div class="product-tags">
                            {% for keyword in product.technical_keywords[:4] %}
                            <span class="tag">{{ keyword }}</span>
                            {% endfor %}
                            {% if product.technical_keywords|length > 4 %}
                            <span style="font-size: 12px; color: #666;">+{{ product.technical_keywords|length - 4 }} more</span>
                            {% endif %}
                        </div>
                        {% endif %}

                        <div style="font-size: 12px; color: #666; margin: 10px 0;">
                            <strong>Implementation:</strong> {{ product.implementation_time or 'TBD' }}
                            <br><strong>Pricing:</strong> {{ product.pricing_type }}
                        </div>

                        <div class="product-actions">
                            <button class="btn" style="flex: 1;">👁️ View Details</button>
                            <button class="btn" style="background: #6c757d;">✏️ Edit</button>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div class="no-products">
                    <h3>📦 No Products Yet</h3>
                    <p>Add the first product for {{ partner.name }} to enable AI recommendations.</p>
                    <a href="/settings/partners/{{ partner.id }}/products/add" class="btn btn-success">+ Add First Product</a>
                </div>
                {% endif %}
            </div>
        </body>
        </html>
        ''', partner=partner)

    @app.route('/settings/partners/<int:partner_id>/products/add', methods=['GET', 'POST'])
    @login_required
    def add_partner_product(partner_id):
        """Add product to partner"""
        try:
            from models import Partner
            partner = Partner.query.get_or_404(partner_id)
        except Exception as e:
            flash(f"Error loading partner: {e}")
            return redirect('/settings/partners')

        if request.method == 'POST':
            try:
                from models import PartnerProduct

                # Parse JSON fields
                supported_platforms = [p.strip() for p in request.form.get('supported_platforms', '').split(',') if p.strip()]
                security_certs = [c.strip() for c in request.form.get('security_certifications', '').split(',') if c.strip()]
                tech_keywords = [k.strip() for k in request.form.get('technical_keywords', '').split(',') if k.strip()]
                industry_fit = [i.strip() for i in request.form.get('industry_fit', '').split(',') if i.strip()]

                product = PartnerProduct(
                    partner_id=partner_id,
                    product_name=request.form['product_name'],
                    category=request.form['category'],
                    functionality=request.form['functionality'],
                    integration_complexity=request.form['integration_complexity'],
                    api_available=bool(request.form.get('api_available')),
                    cloud_native=bool(request.form.get('cloud_native')),
                    supported_platforms=supported_platforms,
                    security_certifications=security_certs,
                    pricing_type=request.form['pricing_type'],
                    implementation_time=request.form.get('implementation_time'),
                    maintenance_required=bool(request.form.get('maintenance_required')),
                    technical_keywords=tech_keywords,
                    industry_fit=industry_fit
                )

                db.session.add(product)
                db.session.commit()

                flash('Product added successfully!', 'success')
                return redirect(f'/settings/partners/{partner_id}/products')

            except Exception as e:
                db.session.rollback()
                flash(f'Error adding product: {str(e)}', 'error')

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Add Product - {{ partner.name }} - Tender Analysis System</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
                .btn { padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; border: none; cursor: pointer; }
                .btn:hover { background: #5a6fd8; }
                .btn-success { background: #28a745; } .btn-success:hover { background: #218838; }
                .form-section { margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; }
                .form-group { margin: 15px 0; }
                .form-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input, select, textarea {
                    width: 100%;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    box-sizing: border-box;
                }
                .checkbox-group { display: flex; gap: 20px; }
                .checkbox-item { display: flex; align-items: center; }
                .checkbox-item input { width: auto; margin-right: 8px; }
                .help-text { font-size: 12px; color: #6c757d; margin-top: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>➕ Add Product to {{ partner.name }}</h1>
                        <p style="color: #6c757d;">Define a new product or service offering</p>
                    </div>
                    <a href="/settings/partners/{{ partner.id }}/products" class="btn">← Back to Products</a>
                </div>

                <form method="POST">
                    <div class="form-section">
                        <h4>Basic Information</h4>

                        <div class="form-row">
                            <div class="form-group">
                                <label for="product_name">Product Name *</label>
                                <input type="text" id="product_name" name="product_name" required>
                            </div>
                            <div class="form-group">
                                <label for="category">Category *</label>
                                <select id="category" name="category" required>
                                    <option value="">Select Category</option>
                                    <option value="AUTHENTICATION">Authentication & Security</option>
                                    <option value="PAYMENT">Payment Processing</option>
                                    <option value="ANALYTICS">Analytics & Reporting</option>
                                    <option value="MESSAGING">Messaging & Communication</option>
                                    <option value="STORAGE">Data Storage</option>
                                    <option value="AI_ML">AI & Machine Learning</option>
                                    <option value="INTEGRATION">Integration & APIs</option>
                                    <option value="MONITORING">Monitoring & Logging</option>
                                    <option value="CRM">Customer Relationship Management</option>
                                    <option value="ERP">Enterprise Resource Planning</option>
                                    <option value="OTHER">Other</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="pricing_type">Pricing Model</label>
                                <select id="pricing_type" name="pricing_type">
                                    <option value="SUBSCRIPTION">Subscription</option>
                                    <option value="LICENSE">License</option>
                                    <option value="TRANSACTION">Per Transaction</option>
                                    <option value="USAGE">Usage-based</option>
                                </select>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="functionality">Functionality Description *</label>
                            <textarea id="functionality" name="functionality" rows="3" required placeholder="Describe what this product does and its key capabilities"></textarea>
                        </div>
                    </div>

                    <div class="form-section">
                        <h4>Technical Specifications</h4>

                        <div class="form-row">
                            <div class="form-group">
                                <label for="integration_complexity">Integration Complexity</label>
                                <select id="integration_complexity" name="integration_complexity">
                                    <option value="LOW">Low - Simple configuration</option>
                                    <option value="MEDIUM" selected>Medium - Moderate setup</option>
                                    <option value="HIGH">High - Complex integration</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="implementation_time">Implementation Time</label>
                                <input type="text" id="implementation_time" name="implementation_time" placeholder="e.g., 2-4 weeks">
                            </div>
                            <div class="form-group">
                                <label>Features</label>
                                <div class="checkbox-group">
                                    <div class="checkbox-item">
                                        <input type="checkbox" id="api_available" name="api_available" checked>
                                        <label for="api_available">API Available</label>
                                    </div>
                                    <div class="checkbox-item">
                                        <input type="checkbox" id="cloud_native" name="cloud_native" checked>
                                        <label for="cloud_native">Cloud Native</label>
                                    </div>
                                    <div class="checkbox-item">
                                        <input type="checkbox" id="maintenance_required" name="maintenance_required" checked>
                                        <label for="maintenance_required">Maintenance Required</label>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="form-row">
                            <div class="form-group">
                                <label for="supported_platforms">Supported Platforms</label>
                                <input type="text" id="supported_platforms" name="supported_platforms" placeholder="web, mobile, api, desktop">
                                <div class="help-text">Enter platforms separated by commas</div>
                            </div>
                            <div class="form-group">
                                <label for="security_certifications">Security Certifications</label>
                                <input type="text" id="security_certifications" name="security_certifications" placeholder="SO
                               <div class="help-text">Enter certifications separated by commas</div>
                           </div>
                       </div>
                   </div>

                   <div class="form-section">
                       <h4>AI Matching Configuration</h4>

                       <div class="form-group">
                           <label for="technical_keywords">Technical Keywords</label>
                           <input type="text" id="technical_keywords" name="technical_keywords" placeholder="authentication, oauth, sso, security">
                           <div class="help-text">Keywords that help AI match this product to project requirements</div>
                       </div>

                       <div class="form-group">
                           <label for="industry_fit">Industry Fit</label>
                           <input type="text" id="industry_fit" name="industry_fit" placeholder="healthcare, banking, retail, fintech">
                           <div class="help-text">Industries where this product is commonly used</div>
                       </div>
                   </div>

                   <div style="display: flex; gap: 10px; margin-top: 30px;">
                       <a href="/settings/partners/{{ partner.id }}/products" class="btn" style="background: #6c757d;">Cancel</a>
                       <button type="submit" class="btn btn-success" style="flex: 1;">💾 Add Product</button>
                   </div>
               </form>
           </div>
       </body>
       </html>
       ''', partner=partner)

   # Add navigation link to partner management in the main navigation
   # You'll need to modify your dashboard template to include a link to /settings/partners

    # ========================================
    # DOCUMENT UPLOAD & PROCESSING
    # ========================================

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

            // Fix drag and drop functionality
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadArea.classList.add('dragover');
            });

            uploadArea.addEventListener('dragleave', (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadArea.classList.remove('dragover');
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadArea.classList.remove('dragover');
                handleFiles(e.dataTransfer.files);
            });

            // Fix click to upload
            uploadArea.addEventListener('click', (e) => {
                if (e.target.tagName !== 'BUTTON') {
                    fileInput.click();
                }
            });

            fileInput.addEventListener('change', (e) => {
                handleFiles(e.target.files);
            });

            function handleFiles(files) {
                selectedFiles = Array.from(files);
                updateFileList();
                updateUploadButton();
                console.log('Files selected:', selectedFiles.map(f => `${f.name} (${f.size} bytes)`));
            }

            function updateFileList() {
                fileList.innerHTML = '';
                selectedFiles.forEach((file, index) => {
                    // Fix file size calculation - ensure it's not showing 0.00
                    const fileSizeMB = file.size > 0 ? (file.size / 1024 / 1024).toFixed(2) : '0.00';

                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    fileItem.innerHTML = `
                        <div>
                            <strong>${file.name}</strong> (${fileSizeMB} MB)
                            <br><small style="color: #666;">Type: ${file.type || 'unknown'} | Size: ${file.size} bytes</small>
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

            // Fixed form submission with proper error handling
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

                const uploadedDocuments = [];
                let hasErrors = false;

                for (let i = 0; i < selectedFiles.length; i++) {
                    const file = selectedFiles[i];
                    console.log(`Uploading file ${i + 1}/${selectedFiles.length}: ${file.name} (${file.size} bytes)`);

                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('project_id', projectId);

                    try {
                        // Add headers to fix potential CORS/HTTP2 issues
                        const response = await fetch('/api/upload', {
                            method: 'POST',
                            body: formData,
                            // Remove any Content-Type header to let browser set it with boundary
                            headers: {
                                'Accept': 'application/json',
                            },
                            // Add these options to handle connection issues
                            credentials: 'same-origin',
                            cache: 'no-cache'
                        });

                        console.log(`Response for ${file.name}:`, response.status, response.statusText);

                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                        }

                        const result = await response.json();
                        console.log(`Result for ${file.name}:`, result);

                        if (result.success) {
                            progressBar.style.width = ((i + 1) / selectedFiles.length * 100) + '%';
                            console.log(`✅ File ${file.name} uploaded successfully`);

                            // Store document info for tracking
                            uploadedDocuments.push({
                                documentId: result.document_id,
                                filename: result.filename,
                                taskId: result.task_id
                            });
                        } else {
                            console.error(`❌ Error uploading ${file.name}:`, result.error);
                            alert(`Error uploading ${file.name}: ${result.error}`);
                            hasErrors = true;
                        }
                    } catch (error) {
                        console.error(`❌ Network error uploading ${file.name}:`, error);
                        alert(`Network error uploading ${file.name}: ${error.message}`);
                        hasErrors = true;
                    }
                }

                // Continue with tracking if we have successful uploads
                if (uploadedDocuments.length > 0) {
                    uploadBtn.textContent = '📄 Extracting Content...';
                    startTrackingProcessing(uploadedDocuments, projectId);
                } else {
                    uploadBtn.textContent = '🚀 Start AI Analysis';
                    uploadBtn.disabled = false;
                    progress.style.display = 'none';

                    if (hasErrors) {
                        alert('All uploads failed. Please check the console for details.');
                    }
                }
            });

            // Enhanced processing tracking with better error handling
            function startTrackingProcessing(documents, projectId) {
                console.log('Starting to track processing for documents:', documents);

                const resultsDiv = document.getElementById('results');
                resultsDiv.innerHTML = `
                    <div style="background: #e3f2fd; padding: 20px; border-radius: 8px; margin-top: 20px;">
                        <h3>📄 Processing Documents</h3>
                        <p>Extracting content from your documents. Once complete, you can view AI analysis results.</p>
                        <div id="processingStatus"></div>
                    </div>
                `;

                const statusDiv = document.getElementById('processingStatus');
                let completedCount = 0;

                documents.forEach((doc, index) => {
                    const docStatus = document.createElement('div');
                    docStatus.id = `doc-status-${doc.documentId}`;
                    docStatus.style.cssText = 'margin: 10px 0; padding: 10px; background: white; border-radius: 4px;';
                    docStatus.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span><strong>${doc.filename}</strong></span>
                            <span id="status-${doc.documentId}" style="color: #ffa500;">⏳ Processing...</span>
                        </div>
                    `;
                    statusDiv.appendChild(docStatus);
                });

                // Check processing status periodically with better error handling
                const checkStatus = async () => {
                    console.log('Checking status for documents...');

                    for (const doc of documents) {
                        try {
                            const response = await fetch(`/api/document-status/${doc.documentId}`, {
                                method: 'GET',
                                headers: {
                                    'Accept': 'application/json',
                                },
                                credentials: 'same-origin',
                                cache: 'no-cache'
                            });

                            if (!response.ok) {
                                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                            }

                            const status = await response.json();
                            console.log(`Status for document ${doc.documentId}:`, status);

                            const statusElement = document.getElementById(`status-${doc.documentId}`);
                            if (!statusElement) continue;

                            if (status.processing_status === 'completed') {
                                statusElement.innerHTML = '✅ Content Extracted';
                                statusElement.style.color = '#28a745';
                                completedCount++;
                            } else if (status.processing_status === 'failed') {
                                statusElement.innerHTML = '❌ Extraction Failed';
                                statusElement.style.color = '#dc3545';
                                completedCount++;
                            } else if (status.processing_status === 'in_progress') {
                                statusElement.innerHTML = '🔄 Extracting...';
                                statusElement.style.color = '#17a2b8';
                            }

                            // Show when content is ready for analysis
                            if (status.processing_status === 'completed') {
                                const docStatusDiv = document.getElementById(`doc-status-${doc.documentId}`);
                                if (docStatusDiv && !docStatusDiv.querySelector('.ready-notice')) {
                                    const readyNotice = document.createElement('div');
                                    readyNotice.className = 'ready-notice';
                                    readyNotice.style.cssText = 'margin-top: 10px; padding: 10px; background: #d4edda; border-radius: 4px; font-size: 14px; color: #155724;';
                                    readyNotice.innerHTML = `✅ Ready for AI analysis via your RealAnalysisEngine`;
                                    docStatusDiv.appendChild(readyNotice);
                                }
                            }
                        } catch (error) {
                            console.error(`Error checking status for ${doc.filename}:`, error);
                            const statusElement = document.getElementById(`status-${doc.documentId}`);
                            if (statusElement) {
                                statusElement.innerHTML = '⚠️ Status Check Failed';
                                statusElement.style.color = '#ffc107';
                            }
                        }
                    }

                    // Check if all documents are processed
                    if (completedCount >= documents.length) {
                        uploadBtn.textContent = '✅ Upload Complete';
                        uploadBtn.style.background = '#28a745';

                        // Show final success message
                        resultsDiv.innerHTML += `
                            <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin-top: 20px; border: 1px solid #c3e6cb;">
                                <h4 style="color: #155724;">🎉 Documents Ready for Analysis!</h4>
                                <p style="color: #155724;">Your documents have been processed and are ready for AI analysis using your RealAnalysisEngine.</p>
                                <div style="margin-top: 15px;">
                                    <button onclick="window.location.href='/projects'" style="background: #28a745; color: white; border: none; padding: 12px 24px; border-radius: 5px; margin-right: 10px; cursor: pointer;">
                                        📊 View Project Dashboard
                                    </button>
                                    <button onclick="window.location.href='/analysis/${projectId}'" style="background: #1f4397; color: white; border: none; padding: 12px 24px; border-radius: 5px; cursor: pointer;">
                                        🤖 Run AI Analysis
                                    </button>
                                </div>
                            </div>
                        `;

                    } else {
                        // Continue checking every 3 seconds
                        setTimeout(checkStatus, 3000);
                    }
                };

                // Start checking after 2 seconds
                setTimeout(checkStatus, 2000);
            }

            // Add this function to view individual document details
            function viewDocumentDetails(documentId) {
                window.location.href = `/document/${documentId}`;
            }

            // Add some debugging info
            console.log('Upload page JavaScript loaded');
            console.log('Browser info:', {
                userAgent: navigator.userAgent,
                onLine: navigator.onLine,
                cookieEnabled: navigator.cookieEnabled
            });
            </script>
        </body>
        </html>
        ''', user_projects=user_projects, project_id=project_id)

    # ========================================
    # API ENDPOINTS
    # ========================================

    # Add a new route to check task status
    @app.route('/api/task-status/<task_id>')
    def get_task_status(task_id):
        """Get status of a background task"""
        if 'username' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        try:
            if celery:
                from celery.result import AsyncResult
                task = AsyncResult(task_id, app=celery)

                if task.state == 'PENDING':
                    response = {
                        'state': task.state,
                        'status': 'Task is waiting to be processed'
                    }
                elif task.state == 'PROGRESS':
                    response = {
                        'state': task.state,
                        'status': task.info.get('status', 'Processing...'),
                        'progress': task.info.get('progress', 0)
                    }
                elif task.state == 'SUCCESS':
                    response = {
                        'state': task.state,
                        'result': task.result
                    }
                else:  # FAILURE
                    response = {
                        'state': task.state,
                        'error': str(task.info)
                    }
                return jsonify(response)
            else:
                return jsonify({'error': 'Celery not available'}), 503

        except Exception as e:
            return jsonify({'error': f'Failed to get task status: {str(e)}'}), 500


    @app.route('/api/projects', methods=['POST'])
    def create_project():
        """Create new project API"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401

        try:
            data = request.get_json()

            from models import User, Project
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

    @app.route('/api/upload-test', methods=['GET', 'POST'])
    def test_upload():
        """Test upload functionality"""
        if request.method == 'GET':
            return jsonify({
                'status': 'Upload test endpoint ready',
                'max_content_length': app.config.get('MAX_CONTENT_LENGTH'),
                'upload_folder': app.config.get('UPLOAD_FOLDER'),
                'upload_folder_exists': os.path.exists(app.config.get('UPLOAD_FOLDER', '')),
                'allowed_extensions': list(ALLOWED_EXTENSIONS),
                'session_active': 'username' in session,
                'username': session.get('username', 'Not logged in')
            })

        if request.method == 'POST':
            return jsonify({
                'files_received': list(request.files.keys()),
                'form_data': dict(request.form),
                'content_length': request.content_length,
                'session_user': session.get('username', 'Not logged in')
            })

    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        """Handle file upload API - Enhanced with better error handling"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401

        try:
            print(f"📤 Upload request received from user: {session['username']}")
            print(f"📋 Request files: {list(request.files.keys())}")
            print(f"📋 Request form: {dict(request.form)}")

            if 'file' not in request.files:
                print("❌ No file in request")
                return jsonify({'success': False, 'error': 'No file provided'}), 400

            file = request.files['file']
            project_id = request.form.get('project_id')

            print(f"📄 File details: name='{file.filename}', size={file.content_length}, content_type='{file.content_type}'")
            print(f"📁 Project ID: {project_id}")

            if file.filename == '':
                print("❌ Empty filename")
                return jsonify({'success': False, 'error': 'No file selected'}), 400

            if not allowed_file(file.filename):
                print(f"❌ File type not allowed: {file.filename}")
                return jsonify({'success': False, 'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

            if not project_id:
                print("❌ No project ID provided")
                return jsonify({'success': False, 'error': 'Project ID is required'}), 400

            from models import User, Project, Document
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                print("❌ User not found")
                return jsonify({'success': False, 'error': 'User not found'}), 404

            # Verify project ownership
            project = Project.query.filter_by(id=project_id, user_id=user.id).first()
            if not project:
                print(f"❌ Project {project_id} not found for user {user.id}")
                return jsonify({'success': False, 'error': 'Project not found or access denied'}), 404

            # Check file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning

            print(f"📏 Actual file size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")

            if file_size == 0:
                print("❌ File is empty")
                return jsonify({'success': False, 'error': 'File is empty (0 bytes)'}), 400

            if file_size > app.config['MAX_CONTENT_LENGTH']:
                max_mb = app.config['MAX_CONTENT_LENGTH'] / 1024 / 1024
                print(f"❌ File too large: {file_size} > {app.config['MAX_CONTENT_LENGTH']}")
                return jsonify({'success': False, 'error': f'File too large. Maximum size: {max_mb:.1f} MB'}), 400

            # Save file
            original_filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{original_filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

            print(f"💾 Saving file to: {file_path}")

            # Ensure upload directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            # Save the file
            file.save(file_path)

            # Verify file was saved correctly
            if not os.path.exists(file_path):
                print(f"❌ File was not saved: {file_path}")
                return jsonify({'success': False, 'error': 'File save failed'}), 500

            saved_size = os.path.getsize(file_path)
            print(f"✅ File saved successfully: {saved_size} bytes")

            if saved_size != file_size:
                print(f"⚠️ Size mismatch: uploaded={file_size}, saved={saved_size}")

            # Create document record
            try:
                document = Document(
                    filename=unique_filename,
                    original_filename=original_filename,
                    file_path=file_path,
                    file_size=saved_size,  # Use actual saved size
                    project_id=project_id,
                    uploaded_by=user.id,
                    uploaded_at=datetime.utcnow()
                )

                # Add processing status and other fields if they exist in your model
                if hasattr(document, 'processing_status'):
                    document.processing_status = 'pending'
                if hasattr(document, 'created_at'):
                    document.created_at = datetime.utcnow()

                db.session.add(document)
                db.session.commit()

                print(f"✅ Document record created: ID={document.id}")

            except Exception as e:
                print(f"❌ Database error: {e}")
                # Clean up file if database insert failed
                try:
                    os.remove(file_path)
                except:
                    pass
                return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500

            # Start background processing if Celery is available
            task_id = None
            try:
                if celery:
                    # Import the task function directly
                    from tasks import process_document_task

                    # Start the task
                    task = process_document_task.delay(document.id)
                    task_id = task.id

                    # Store task ID if the column exists
                    if hasattr(document, 'task_id'):
                        document.task_id = task_id
                        db.session.commit()

                    print(f"✅ Started background task: {task_id} for document {document.id}")

            except Exception as e:
                print(f"⚠️ Background task failed to start: {e}")
                # Update document status if task couldn't start
                if hasattr(document, 'processing_status'):
                    document.processing_status = 'failed'
                if hasattr(document, 'error_message'):
                    document.error_message = f"Task start failed: {str(e)}"
                db.session.commit()

            response_data = {
                'success': True,
                'document_id': document.id,
                'filename': original_filename,
                'file_size': saved_size,
                'task_id': task_id,
                'message': 'File uploaded successfully and AI analysis started!' if task_id else 'File uploaded successfully'
            }

            print(f"✅ Upload successful: {response_data}")
            return jsonify(response_data)

        except Exception as e:
            print(f"❌ Upload error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'Upload failed: {str(e)}'}), 500

    @app.route('/api/document-status/<int:document_id>')
    def get_document_status(document_id):
        """Get document processing status - Compatible with RealAnalysisEngine"""
        if 'username' not in session:
            return jsonify({'error': 'Not logged in'}), 401

        try:
            from models import User, Document, Project
            user = User.query.filter_by(username=session['username']).first()

            # Get document and verify ownership through project
            document = Document.query.get_or_404(document_id)
            project = Project.query.filter_by(id=document.project_id, user_id=user.id).first()
            if not project:
                return jsonify({'error': 'Access denied'}), 403

            # Get task status if available
            task_status = None
            if hasattr(document, 'task_id') and document.task_id and celery:
                try:
                    from celery.result import AsyncResult
                    task = AsyncResult(document.task_id, app=celery)
                    task_status = {
                        'state': task.state,
                        'info': task.info if task.state != 'PENDING' else None
                    }
                except Exception as e:
                    print(f"⚠️ Could not get task status: {e}")

            # Check if we have real analysis available using your RealAnalysisEngine
            analysis_preview = None
            try:
                real_analysis = get_real_document_analysis(document_id)
                if real_analysis and real_analysis.get('extracted_requirements'):
                    analysis_preview = f"Found {len(real_analysis['extracted_requirements'])} requirements"
            except Exception as e:
                print(f"⚠️ Could not get real analysis preview: {e}")

            return jsonify({
                'document_id': document.id,
                'filename': getattr(document, 'original_filename', None) or document.filename,
                'processing_status': getattr(document, 'processing_status', 'unknown'),
                'error_message': getattr(document, 'error_message', None),
                'processed_at': getattr(document, 'processed_at', None),
                'upload_date': getattr(document, 'uploaded_at', None),
                'analysis_preview': analysis_preview,
                'task_status': task_status,
                'has_real_analysis': analysis_preview is not None
            })

        except Exception as e:
            print(f"❌ Status check error: {e}")
            return jsonify({'error': f'Status check failed: {str(e)}'}), 500

    # ========================================
    # ANALYSIS & DOCUMENT VIEWS
    # ========================================

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

            ai_analysis = get_real_document_analysis(document_id)

            doc_analysis = {
                'filename': document.original_filename or document.filename,
                'file_size': f"{document.file_size / 1024 / 1024:.1f} MB" if document.file_size else "Unknown",
                'upload_date': document.uploaded_at.strftime('%Y-%m-%d %H:%M') if document.uploaded_at else 'Unknown',
                'analysis_confidence': ai_analysis.get('analysis_confidence', 'Unknown') if ai_analysis else 'No analysis available',
                # Use real AI results
                'extracted_requirements': ai_analysis.get('extracted_requirements', []) if ai_analysis else [],
                'key_terms': ai_analysis.get('key_terms', []) if ai_analysis else [],
                'compliance_items': ai_analysis.get('compliance_items', []) if ai_analysis else [],
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

    @app.route('/analysis/<project_id>')
    def analysis_view(project_id):
        """Analysis results page for a project"""
        if 'username' not in session:
            return redirect('/login')

        try:
            from models import User, Project, Document
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            documents = Document.query.filter_by(project_id=project_id).all()
            analysis_results = get_real_analysis_results(project_id)

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

                 <div style="text-align: center; margin-top: 30px;">
                 <a href="/projects/{{ project.id }}/partner-recommendations" class="btn" style="background: #1f4397; padding: 15px 30px; font-size: 16px; margin-right: 10px;">
                    🤝 Select Partner Products
                </a>
                <a href="/generate-proposal/{{ project.id }}" class="btn" style="background: #28a745; padding: 15px 30px; font-size: 16px;">
                    📝 Generate Proposal Document
                </a>
            </div>
        </div>

        <script>
        // Check if proposals exist for this project and show appropriate buttons
        async function checkProposals() {
            try {
                const projectId = {{ project.id }};
                const response = await fetch(`/api/check-proposals/${projectId}`);
                const data = await response.json();

                // Find the proposal generation button area
                const buttonArea = document.querySelector('div[style*="text-align: center"]');

                if (data.has_proposals && data.count > 0) {
                    // Add view proposals button if proposals exist
                    buttonArea.innerHTML = `
                        <a href="/proposals/${projectId}" class="btn" style="background: #17a2b8; margin-right: 10px;">
                            📄 View Generated Proposals (${data.count})
                        </a>
                        <a href="/generate-proposal/${projectId}" class="btn" style="background: #28a745;">
                            📝 Generate More Documents
                        </a>
                    `;
                } else {
                    // Keep original generate button if no proposals exist
                    buttonArea.innerHTML = `
                        <a href="/generate-proposal/${projectId}" class="btn" style="background: #28a745; padding: 15px 30px; font-size: 16px;">
                            📝 Generate Proposal Document
                        </a>
                    `;
                }

            } catch (error) {
                console.log('Could not check proposals:', error);
                // Keep original button if check fails
            }
        }

        // Run check when page loads
        document.addEventListener('DOMContentLoaded', checkProposals);
        </script>
    </body>
    </html>
        ''', project=project, documents=documents, analysis_results=analysis_results)


    # Add these routes to your main.py file

    @app.route('/generate-proposal/<project_id>')
    def generate_proposal_page(project_id):
        """Proposal generation page with multiple deliverable options"""
        if 'username' not in session:
            return redirect('/login')

        try:
            from models import User, Project, Document
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            documents = Document.query.filter_by(project_id=project_id).all()

            # Get analysis results for the project
            analysis_results = get_real_analysis_results(project_id)

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
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
                .btn { padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; border: none; cursor: pointer; }
                .btn:hover { background: #5a6fd8; }
                .btn-success { background: #28a745; } .btn-success:hover { background: #218838; }
                .btn-primary { background: #1f4397; } .btn-primary:hover { background: #0056b3; }
                .btn-warning { background: #ffc107; color: #212529; } .btn-warning:hover { background: #e0a800; }
                .deliverable-card {
                    background: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 15px 0;
                    transition: all 0.3s;
                }
                .deliverable-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
                .deliverable-card.selected { border-color: #1f4397; background: #e3f2fd; }
                .deliverable-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
                .checkbox-container { display: flex; align-items: center; margin-bottom: 15px; }
                .checkbox-container input[type="checkbox"] { margin-right: 10px; transform: scale(1.2); }
                .progress-section { background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; display: none; }
                .progress-bar { width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px; overflow: hidden; }
                .progress-fill { height: 100%; background: #1f4397; width: 0%; transition: width 0.5s; }
                .download-section { background: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0; display: none; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>📝 Generate Proposal Documents</h1>
                        <p style="color: #6c757d;">Project: {{ project.name }}</p>
                    </div>
                    <div>
                        <a href="/analysis/{{ project.id }}" class="btn">← Back to Analysis</a>
                    </div>
                </div>

                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #ffc107;">
                    <h4>📊 Analysis Summary</h4>
                    <p>Based on analysis of {{ documents|length }} document(s), we can generate the following deliverables:</p>
                    <ul>
                        <li><strong>{{ analysis_results.must_have_requirements|length }}</strong> must-have requirements identified</li>
                        <li><strong>{{ analysis_results.good_to_have_requirements|length }}</strong> good-to-have requirements found</li>
                        <li><strong>{{ analysis_results.technical_specifications|length }}</strong> technical specifications extracted</li>
                    </ul>
                </div>

                <form id="proposalForm">
                    <h3>📋 Select Deliverables to Generate</h3>

                    <div class="deliverable-grid">
                        <!-- Technical Proposal -->
                        <div class="deliverable-card" onclick="toggleDeliverable('technical')">
                            <div class="checkbox-container">
                                <input type="checkbox" id="technical" name="deliverables" value="technical" checked>
                                <h4>📄 Technical Proposal</h4>
                            </div>
                            <p><strong>Comprehensive technical response covering:</strong></p>
                            <ul>
                                <li>Executive Summary</li>
                                <li>Solution Architecture & Technology Stack</li>
                                <li>Implementation Methodology</li>
                                <li>Technical Specifications Compliance</li>
                                <li>System Integration Approach</li>
                                <li>Performance & Scalability</li>
                                <li>Security Framework</li>
                            </ul>
                            <p><em>~15-25 pages | Professional format</em></p>
                        </div>

                        <!-- Commercial Proposal -->
                        <div class="deliverable-card" onclick="toggleDeliverable('commercial')">
                            <div class="checkbox-container">
                                <input type="checkbox" id="commercial" name="deliverables" value="commercial" checked>
                                <h4>💰 Commercial Proposal</h4>
                            </div>
                            <p><strong>Detailed commercial response including:</strong></p>
                            <ul>
                                <li>Cost Breakdown Structure</li>
                                <li>Pricing Model & Payment Terms</li>
                                <li>Resource Allocation & Team Structure</li>
                                <li>Project Timeline & Milestones</li>
                                <li>Return on Investment Analysis</li>
                                <li>Risk Assessment & Mitigation</li>
                                <li>Commercial Terms & Conditions</li>
                            </ul>
                            <p><em>~10-15 pages | Business focused</em></p>
                        </div>

                        <!-- Implementation Plan -->
                        <div class="deliverable-card" onclick="toggleDeliverable('implementation')">
                            <div class="checkbox-container">
                                <input type="checkbox" id="implementation" name="deliverables" value="implementation">
                                <h4>🚀 Implementation Plan</h4>
                            </div>
                            <p><strong>Detailed project execution plan:</strong></p>
                            <ul>
                                <li>Work Breakdown Structure (WBS)</li>
                                <li>Project Timeline with Gantt Chart</li>
                                <li>Resource Planning & Allocation</li>
                                <li>Risk Management Strategy</li>
                                <li>Quality Assurance Framework</li>
                                <li>Change Management Process</li>
                                <li>Communication Plan</li>
                            </ul>
                            <p><em>~8-12 pages | Project management focus</em></p>
                        </div>

                        <!-- Technical Architecture -->
                        <div class="deliverable-card" onclick="toggleDeliverable('architecture')">
                            <div class="checkbox-container">
                                <input type="checkbox" id="architecture" name="deliverables" value="architecture">
                                <h4>🏗️ Technical Architecture Document</h4>
                            </div>
                            <p><strong>Deep technical architecture design:</strong></p>
                            <ul>
                                <li>System Architecture Diagrams</li>
                                <li>Technology Stack Justification</li>
                                <li>Data Flow & Integration Patterns</li>
                                <li>Security Architecture</li>
                                <li>Scalability & Performance Design</li>
                                <li>Infrastructure Requirements</li>
                                <li>API Design & Documentation</li>
                            </ul>
                            <p><em>~12-18 pages | Technical deep dive</em></p>
                        </div>

                        <!-- Company Profile -->
                        <div class="deliverable-card" onclick="toggleDeliverable('company')">
                            <div class="checkbox-container">
                                <input type="checkbox" id="company" name="deliverables" value="company">
                                <h4>🏢 Company Profile & Credentials</h4>
                            </div>
                            <p><strong>Professional company presentation:</strong></p>
                            <ul>
                                <li>Company Overview & History</li>
                                <li>Core Competencies & Services</li>
                                <li>Relevant Project Case Studies</li>
                                <li>Team Profiles & Certifications</li>
                                <li>Client Testimonials</li>
                                <li>Awards & Recognition</li>
                                <li>Financial Stability & References</li>
                            </ul>
                            <p><em>~6-10 pages | Company credentials</em></p>
                        </div>

                        <!-- Compliance Matrix -->
                        <div class="deliverable-card" onclick="toggleDeliverable('compliance')">
                            <div class="checkbox-container">
                                <input type="checkbox" id="compliance" name="deliverables" value="compliance">
                                <h4>✅ Compliance & Requirements Matrix</h4>
                            </div>
                            <p><strong>Detailed compliance documentation:</strong></p>
                            <ul>
                                <li>Requirements Traceability Matrix</li>
                                <li>Compliance Checklist</li>
                                <li>Regulatory Requirements Coverage</li>
                                <li>Standards & Certifications</li>
                                <li>Gap Analysis (if any)</li>
                                <li>Remediation Plans</li>
                                <li>Testing & Validation Approach</li>
                            </ul>
                            <p><em>~5-8 pages | Compliance focused</em></p>
                        </div>
                    </div>

                    <div style="margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                        <h4>⚙️ Generation Options</h4>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                            <div>
                                <label><strong>Output Format:</strong></label><br>
                                <select id="outputFormat" style="width: 100%; padding: 8px; margin-top: 5px;">
                                    <option value="pdf">PDF Document</option>
                                    <option value="docx">Word Document (.docx)</option>
                                    <option value="html">HTML Report</option>
                                    <option value="markdown">Markdown Format</option>
                                </select>
                            </div>
                            <div>
                                <label><strong>Detail Level:</strong></label><br>
                                <select id="detailLevel" style="width: 100%; padding: 8px; margin-top: 5px;">
                                    <option value="comprehensive">Comprehensive (Detailed)</option>
                                    <option value="standard" selected>Standard (Balanced)</option>
                                    <option value="executive">Executive (Summary)</option>
                                </select>
                            </div>
                        </div>

                        <div style="margin-top: 15px;">
                            <label><strong>Company Information:</strong></label><br>
                            <input type="text" id="companyName" placeholder="Your company name" style="width: 48%; padding: 8px; margin: 5px 1% 5px 0;">
                            <input type="text" id="contactPerson" placeholder="Contact person" style="width: 48%; padding: 8px; margin: 5px 0 5px 1%;">
                        </div>
                    </div>

                    <div style="text-align: center; margin: 30px 0;">
                        <button type="submit" class="btn btn-success" style="padding: 15px 40px; font-size: 18px;">
                            🚀 Generate Selected Documents
                        </button>
                    </div>
                </form>

                <div id="progressSection" class="progress-section">
                    <h4>🔄 Generating Documents...</h4>
                    <div class="progress-bar">
                        <div id="progressFill" class="progress-fill"></div>
                    </div>
                    <p id="progressText">Starting generation process...</p>
                </div>

                <div id="downloadSection" class="download-section">
                    <h4>✅ Documents Generated Successfully!</h4>
                    <p>Your proposal documents are ready for download:</p>
                    <div id="downloadLinks"></div>
                </div>
            </div>

            <script>
            function toggleDeliverable(id) {
                const checkbox = document.getElementById(id);
                const card = checkbox.closest('.deliverable-card');

                checkbox.checked = !checkbox.checked;

                if (checkbox.checked) {
                    card.classList.add('selected');
                } else {
                    card.classList.remove('selected');
                }
            }

            // Initialize selected cards
            document.addEventListener('DOMContentLoaded', function() {
                document.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
                    checkbox.closest('.deliverable-card').classList.add('selected');
                });
            });

            document.getElementById('proposalForm').addEventListener('submit', async function(e) {
                e.preventDefault();

                const selectedDeliverables = Array.from(document.querySelectorAll('input[name="deliverables"]:checked'))
                    .map(cb => cb.value);

                if (selectedDeliverables.length === 0) {
                    alert('Please select at least one deliverable to generate.');
                    return;
                }

                const formData = {
                    deliverables: selectedDeliverables,
                    output_format: document.getElementById('outputFormat').value,
                    detail_level: document.getElementById('detailLevel').value,
                    company_name: document.getElementById('companyName').value || 'Your Company',
                    contact_person: document.getElementById('contactPerson').value || 'Project Manager'
                };

                console.log('Generating documents with options:', formData);

                // Show progress
                document.getElementById('progressSection').style.display = 'block';
                this.style.display = 'none';

                try {
                    const response = await fetch('/api/generate-proposal/{{ project.id }}', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(formData)
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }

                    const result = await response.json();

                    if (result.success) {
                        showDownloadSection(result.documents);
                    } else {
                        throw new Error(result.error || 'Generation failed');
                    }

                } catch (error) {
                    alert('Error generating documents: ' + error.message);
                    console.error('Generation error:', error);

                    // Reset form
                    document.getElementById('progressSection').style.display = 'none';
                    this.style.display = 'block';
                }
            });

            function showDownloadSection(documents) {
                document.getElementById('progressSection').style.display = 'none';

                const downloadSection = document.getElementById('downloadSection');
                const downloadLinks = document.getElementById('downloadLinks');

                downloadLinks.innerHTML = documents.map(doc => `
                    <div style="margin: 10px 0; padding: 15px; background: white; border-radius: 5px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>${doc.title}</strong><br>
                            <small style="color: #666;">${doc.description} | ${doc.format.toUpperCase()} | ${doc.size}</small>
                        </div>
                        <a href="${doc.download_url}" class="btn btn-primary" download="${doc.filename}">
                            📥 Download
                        </a>
                    </div>
                `).join('');

                downloadSection.style.display = 'block';
            }

            // Simulate progress updates
            function updateProgress(documents) {
                const progressFill = document.getElementById('progressFill');
                const progressText = document.getElementById('progressText');

                let progress = 0;
                const increment = 100 / documents.length;

                documents.forEach((doc, index) => {
                    setTimeout(() => {
                        progress += increment;
                        progressFill.style.width = progress + '%';
                        progressText.textContent = `Generating ${doc}... (${Math.round(progress)}%)`;
                    }, (index + 1) * 2000);
                });
            }
            </script>
        </body>
        </html>
        ''', project=project, documents=documents, analysis_results=analysis_results)

    @app.route('/api/generate-proposal/<project_id>', methods=['POST'])
    def api_generate_proposal(project_id):
        """API endpoint to generate proposal documents"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401

        try:
            from models import User, Project
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first()

            if not project:
                return jsonify({'success': False, 'error': 'Project not found'}), 404

            data = request.get_json()
            deliverables = data.get('deliverables', [])
            output_format = data.get('output_format', 'pdf')
            detail_level = data.get('detail_level', 'standard')
            company_name = data.get('company_name', 'Your Company')
            contact_person = data.get('contact_person', 'Project Manager')

            print(f"📝 Generating proposal for project {project_id}")
            print(f"📋 Deliverables: {deliverables}")
            print(f"📄 Format: {output_format}, Level: {detail_level}")

            # Get analysis results
            analysis_results = get_real_analysis_results(project_id)

            # Import the proposal generator
            from proposal_generator import ProposalGenerator

            generator = ProposalGenerator(
                project=project,
                analysis_results=analysis_results,
                company_name=company_name,
                contact_person=contact_person
            )

            # Generate documents
            generated_docs = []

            for deliverable in deliverables:
                try:
                    doc_result = generator.generate_document(
                        deliverable_type=deliverable,
                        output_format=output_format,
                        detail_level=detail_level
                    )
                    generated_docs.append(doc_result)
                    print(f"✅ Generated {deliverable} document")

                except Exception as e:
                    print(f"❌ Failed to generate {deliverable}: {e}")
                    continue

            if not generated_docs:
                return jsonify({
                    'success': False,
                    'error': 'No documents were generated successfully'
                }), 500

            return jsonify({
                'success': True,
                'documents': generated_docs,
                'message': f'Successfully generated {len(generated_docs)} documents'
            })

        except Exception as e:
            print(f"❌ Proposal generation error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/download-proposal/<filename>')
    def download_proposal(filename):
        """Download generated proposal document"""
        if 'username' not in session:
            return redirect('/login')

        try:
            # Security: ensure filename is safe and user has access
            import os
            from werkzeug.utils import secure_filename

            safe_filename = secure_filename(filename)
            file_path = os.path.join('generated_proposals', safe_filename)

            if not os.path.exists(file_path):
                flash('File not found')
                return redirect('/projects')

            return send_file(
                file_path,
                as_attachment=True,
                download_name=safe_filename
            )

        except Exception as e:
            flash(f'Download error: {e}')
            return redirect('/projects')

    @app.route('/api/proposal-status/<project_id>')
    def get_proposal_status(project_id):
        """Get status of proposal generation"""
        if 'username' not in session:
            return jsonify({'error': 'Not logged in'}), 401

        try:
            # Check if there are any generated proposals for this project
            proposal_dir = 'generated_proposals'
            if not os.path.exists(proposal_dir):
                return jsonify({'status': 'no_proposals', 'proposals': []})

            # Find proposals for this project
            project_proposals = []
            project_name = None

            try:
                from models import Project, User
                user = User.query.filter_by(username=session['username']).first()
                project = Project.query.filter_by(id=project_id, user_id=user.id).first()
                if project:
                    project_name = project.name.replace(' ', '_')
            except:
                pass

            if project_name:
                for filename in os.listdir(proposal_dir):
                    if filename.startswith(project_name):
                        filepath = os.path.join(proposal_dir, filename)
                        stat = os.stat(filepath)

                        # Parse document type from filename
                        doc_type = 'unknown'
                        if '_technical_' in filename:
                            doc_type = 'technical'
                        elif '_commercial_' in filename:
                            doc_type = 'commercial'
                        elif '_implementation_' in filename:
                            doc_type = 'implementation'
                        elif '_architecture_' in filename:
                            doc_type = 'architecture'
                        elif '_company_' in filename:
                            doc_type = 'company'
                        elif '_compliance_' in filename:
                            doc_type = 'compliance'

                        project_proposals.append({
                            'filename': filename,
                            'type': doc_type,
                            'size': f"{stat.st_size / 1024:.1f} KB",
                            'created': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                            'download_url': f'/download-proposal/{filename}'
                        })

            return jsonify({
                'status': 'success',
                'proposal_count': len(project_proposals),
                'proposals': project_proposals
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/delete-proposal/<filename>')
    def delete_proposal(filename):
        """Delete a generated proposal"""
        if 'username' not in session:
            return jsonify({'error': 'Not logged in'}), 401

        try:
            from werkzeug.utils import secure_filename
            safe_filename = secure_filename(filename)
            filepath = os.path.join('generated_proposals', safe_filename)

            if os.path.exists(filepath):
                os.remove(filepath)
                return jsonify({'success': True, 'message': 'Proposal deleted successfully'})
            else:
                return jsonify({'success': False, 'error': 'File not found'}), 404

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/proposals/<project_id>')
    def view_proposals(project_id):
        """View all generated proposals for a project"""
        if 'username' not in session:
            return redirect('/login')

        try:
            from models import User, Project
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()

            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Generated Proposals - {{ project.name }}</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                    .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
                    .btn { padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; border: none; cursor: pointer; }
                    .btn:hover { background: #5a6fd8; }
                    .btn-success { background: #28a745; } .btn-success:hover { background: #218838; }
                    .btn-danger { background: #dc3545; } .btn-danger:hover { background: #c82333; }
                    .proposal-card {
                        background: #f8f9fa;
                        border: 1px solid #e9ecef;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 15px 0;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }
                    .proposal-info h4 { margin: 0 0 10px 0; color: #495057; }
                    .proposal-info p { margin: 5px 0; color: #6c757d; }
                    .proposal-actions { display: flex; gap: 10px; }
                    .loading { text-align: center; padding: 40px; color: #6c757d; }
                    .no-proposals { text-align: center; padding: 40px; background: #fff3cd; border-radius: 8px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div>
                            <h1>📄 Generated Proposals</h1>
                            <p style="color: #6c757d;">Project: {{ project.name }}</p>
                        </div>
                        <div>
                            <a href="/analysis/{{ project.id }}" class="btn">← Back to Analysis</a>
                            <a href="/generate-proposal/{{ project.id }}" class="btn btn-success">+ Generate New</a>
                        </div>
                    </div>

                    <div id="proposalsList" class="loading">
                        <h3>📋 Loading proposals...</h3>
                    </div>
                </div>

                <script>
                async function loadProposals() {
                    try {
                        const response = await fetch('/api/proposal-status/{{ project.id }}');
                        const data = await response.json();

                        const proposalsList = document.getElementById('proposalsList');

                        if (data.proposal_count === 0) {
                            proposalsList.innerHTML = `
                                <div class="no-proposals">
                                    <h3>📄 No Proposals Generated Yet</h3>
                                    <p>Generate your first proposal documents to get started.</p>
                                    <a href="/generate-proposal/{{ project.id }}" class="btn btn-success">Generate Proposals</a>
                                </div>
                            `;
                            return;
                        }

                        const proposalsHtml = data.proposals.map(proposal => {
                            const typeNames = {
                                'technical': 'Technical Proposal',
                                'commercial': 'Commercial Proposal',
                                'implementation': 'Implementation Plan',
                                'architecture': 'Technical Architecture',
                                'company': 'Company Profile',
                                'compliance': 'Compliance Matrix',
                                'unknown': 'Proposal Document'
                            };

                            const typeIcons = {
                                'technical': '⚙️',
                                'commercial': '💰',
                                'implementation': '🚀',
                                'architecture': '🏗️',
                                'company': '🏢',
                                'compliance': '✅',
                                'unknown': '📄'
                            };

                            return `
                                <div class="proposal-card">
                                    <div class="proposal-info">
                                        <h4>${typeIcons[proposal.type] || '📄'} ${typeNames[proposal.type] || 'Proposal Document'}</h4>
                                        <p><strong>File:</strong> ${proposal.filename}</p>
                                        <p><strong>Size:</strong> ${proposal.size} | <strong>Created:</strong> ${proposal.created}</p>
                                    </div>
                                    <div class="proposal-actions">
                                        <a href="${proposal.download_url}" class="btn btn-success" download>
                                            📥 Download
                                        </a>
                                        <button onclick="deleteProposal('${proposal.filename}')" class="btn btn-danger">
                                            🗑️ Delete
                                        </button>
                                    </div>
                                </div>
                            `;
                        }).join('');

                        proposalsList.innerHTML = `
                            <h3>📋 Generated Proposals (${data.proposal_count})</h3>
                            ${proposalsHtml}
                        `;

                    } catch (error) {
                        document.getElementById('proposalsList').innerHTML = `
                            <div style="text-align: center; padding: 40px; color: #dc3545;">
                                <h3>❌ Error Loading Proposals</h3>
                                <p>${error.message}</p>
                                <button onclick="loadProposals()" class="btn">Try Again</button>
                            </div>
                        `;
                    }
                }

                async function deleteProposal(filename) {
                    if (!confirm('Are you sure you want to delete this proposal?')) {
                        return;
                    }

                    try {
                        const response = await fetch(`/api/delete-proposal/${filename}`, {
                            method: 'DELETE'
                        });

                        const result = await response.json();

                        if (result.success) {
                            alert('Proposal deleted successfully');
                            loadProposals(); // Reload the list
                        } else {
                            alert('Error deleting proposal: ' + result.error);
                        }

                    } catch (error) {
                        alert('Error deleting proposal: ' + error.message);
                    }
                }

                // Load proposals when page loads
                document.addEventListener('DOMContentLoaded', loadProposals);
                </script>
            </body>
            </html>
            ''', project=project)

        except Exception as e:
            flash(f'Error loading proposals: {e}')
            return redirect('/projects')

    # Add this route to make the proposals accessible from the analysis page
    @app.route('/api/check-proposals/<project_id>')
    def check_proposals_exist(project_id):
        """Quick check if proposals exist for a project"""
        if 'username' not in session:
            return jsonify({'error': 'Not logged in'}), 401

        try:
            proposal_dir = 'generated_proposals'
            if not os.path.exists(proposal_dir):
                return jsonify({'has_proposals': False, 'count': 0})

            # Get project name for file matching
            from models import Project, User
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first()

            if not project:
                return jsonify({'has_proposals': False, 'count': 0})

            project_name = project.name.replace(' ', '_')
            proposal_count = sum(1 for f in os.listdir(proposal_dir) if f.startswith(project_name))

            return jsonify({
                'has_proposals': proposal_count > 0,
                'count': proposal_count
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ========================================
    # PARTNER RECOMMENDATION & SELECTION
    # ========================================

    @app.route('/projects/<project_id>/partner-recommendations')
    @login_required
    def view_partner_recommendations(project_id):
        """View and select partner recommendations for a project"""
        try:
            from models import User, Project, Partner, PartnerProduct
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()

            # Get analysis results for intelligent matching
            analysis_results = get_real_analysis_results(project_id)

            # Get all active partner products
            partner_products = db.session.query(PartnerProduct).join(Partner).filter(
                Partner.status == 'ACTIVE'
            ).all()

            # Simple keyword matching for recommendations
            recommendations = []
            for product in partner_products:
                fit_score = calculate_simple_fit_score(analysis_results, product)
                if fit_score > 30:  # Show products with some relevance
                    recommendations.append({
                        'product': product,
                        'partner': product.partner,
                        'fit_score': fit_score,
                        'reasoning': generate_fit_reasoning(analysis_results, product),
                        'estimated_cost': estimate_product_cost(product),
                        'integration_scope': determine_integration_scope(fit_score)
                    })

            # Sort by fit score
            recommendations.sort(key=lambda x: x['fit_score'], reverse=True)

        except Exception as e:
            flash(f"Error loading recommendations: {e}")
            return redirect('/projects')

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Partner Recommendations - {{ project.name }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
                .btn { padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; border: none; cursor: pointer; }
                .btn:hover { background: #5a6fd8; }
                .btn-success { background: #28a745; } .btn-success:hover { background: #218838; }
                .btn-warning { background: #ffc107; color: #212529; } .btn-warning:hover { background: #e0a800; }
                .recommendations-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
                .recommendation-card {
                    background: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 8px;
                    padding: 20px;
                    transition: all 0.3s;
                    position: relative;
                }
                .recommendation-card.selected { border-color: #28a745; background: #d4edda; }
                .recommendation-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
                .fit-score { position: absolute; top: 15px; right: 15px; background: #1f4397; color: white; padding: 5px 10px; border-radius: 15px; font-weight: bold; }
                .fit-score.high { background: #28a745; }
                .fit-score.medium { background: #ffc107; color: #212529; }
                .fit-score.low { background: #dc3545; }
                .product-header { margin-bottom: 15px; }
                .product-header h5 { margin: 0; color: #495057; }
                .product-header small { color: #6c757d; }
                .integration-badge { padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; margin: 5px 0; }
                .integration-core { background: #dc3545; color: white; }
                .integration-addon { background: #1f4397; color: white; }
                .integration-optional { background: #6c757d; color: white; }
                .cost-info { background: white; padding: 10px; border-radius: 5px; margin: 10px 0; }
                .reasoning-box { background: #e3f2fd; padding: 10px; border-radius: 5px; margin: 10px 0; font-size: 14px; }
                .selection-controls { margin-top: 15px; display: flex; gap: 10px; align-items: center; }
                .checkbox-large { transform: scale(1.5); margin-right: 10px; }
                .no-recommendations { text-align: center; padding: 60px; color: #6c757d; }
                .summary-panel { background: #fff3cd; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
                .selected-count { background: #28a745; color: white; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center; display: none; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>🤝 Partner Recommendations</h1>
                        <p style="color: #6c757d;">AI-powered partner product suggestions for {{ project.name }}</p>
                    </div>
                    <div>
                        <a href="/analysis/{{ project.id }}" class="btn">← Back to Analysis</a>
                        <button id="proceedBtn" class="btn btn-success" onclick="proceedToProposal()" disabled>
                            📝 Proceed to Proposal Generation
                        </button>
                    </div>
                </div>

                <div class="summary-panel">
                    <h4>📊 Project Analysis Summary</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                        <div><strong>Must-Have:</strong> {{ analysis_results.must_have_requirements|length }} requirements</div>
                        <div><strong>Good-to-Have:</strong> {{ analysis_results.good_to_have_requirements|length }} requirements</div>
                        <div><strong>Technical Specs:</strong> {{ analysis_results.technical_specifications|length }} specifications</div>
                        <div><strong>Available Partners:</strong> {{ recommendations|length }} products found</div>
                    </div>
                </div>

                <div id="selectedCount" class="selected-count">
                    <strong>🎯 <span id="countText">0</span> partner products selected for proposal</strong>
                </div>

                {% if recommendations %}
                <div class="recommendations-grid">
                    {% for rec in recommendations %}
                    <div class="recommendation-card" data-product-id="{{ rec.product.id }}">
                        <div class="fit-score {{ 'high' if rec.fit_score >= 80 else 'medium' if rec.fit_score >= 60 else 'low' }}">
                            {{ "%.0f"|format(rec.fit_score) }}%
                        </div>

                        <div class="product-header">
                            <h5>{{ rec.product.product_name }}</h5>
                            <small>by {{ rec.partner.name }} | {{ rec.product.category }}</small>
                        </div>

                        <p style="color: #6c757d; font-size: 14px; margin: 10px 0;">
                            {{ rec.product.functionality[:150] }}{% if rec.product.functionality|length > 150 %}...{% endif %}
                        </p>

                        <div>
                            <span class="integration-badge integration-{{ rec.integration_scope.lower() }}">
                                {{ rec.integration_scope }} Integration
                            </span>
                            {% if rec.product.api_available %}
                            <span style="color: #28a745; font-size: 12px;">✅ API Available</span>
                            {% endif %}
                            {% if rec.product.cloud_native %}
                            <span style="color: #1f4397; font-size: 12px;">☁️ Cloud Native</span>
                            {% endif %}
                        </div>

                        <div class="cost-info">
                            <strong>Estimated Cost:</strong> ${{ "{:,.0f}"|format(rec.estimated_cost) }}
                            <br><strong>Implementation:</strong> {{ rec.product.implementation_time or 'TBD' }}
                            <br><strong>Pricing:</strong> {{ rec.product.pricing_type }}
                        </div>

                        <div class="reasoning-box">
                            <strong>🤖 AI Analysis:</strong><br>
                            {{ rec.reasoning }}
                        </div>

                        <div class="selection-controls">
                            <input type="checkbox" class="checkbox-large product-checkbox"
                                   data-product-id="{{ rec.product.id }}"
                                   data-partner-name="{{ rec.partner.name }}"
                                   data-product-name="{{ rec.product.product_name }}"
                                   data-cost="{{ rec.estimated_cost }}"
                                   data-scope="{{ rec.integration_scope }}"
                                   onchange="updateSelection()">
                            <label><strong>Include in Proposal</strong></label>
                            <button class="btn" style="margin-left: auto; padding: 5px 10px;" onclick="showDetails({{ rec.product.id }})">
                                📋 View Details
                            </button>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div class="no-recommendations">
                    <h3>🔍 No Partner Recommendations Found</h3>
                    <p>No partner products match your current project requirements.</p>
                    <div style="margin-top: 20px;">
                        <a href="/settings/partners" class="btn">🤝 Add More Partners</a>
                        <a href="/analysis/{{ project.id }}" class="btn btn-warning">📊 Back to Analysis</a>
                    </div>
                </div>
                {% endif %}

                <div style="margin-top: 40px; padding: 20px; background: #e3f2fd; border-radius: 8px;">
                    <h4>ℹ️ How Partner Recommendations Work</h4>
                    <ul>
                        <li><strong>AI Analysis:</strong> System analyzes your project requirements against partner product capabilities</li>
                        <li><strong>Fit Scoring:</strong> Each product gets a compatibility score (0-100%) based on technical and business fit</li>
                        <li><strong>Integration Scope:</strong> Core (essential), Add-on (valuable), Optional (nice-to-have)</li>
                        <li><strong>Cost Integration:</strong> Selected partner costs are included in final proposal pricing</li>
                    </ul>
                </div>
            </div>

            <script>
            let selectedProducts = [];

            function updateSelection() {
                const checkboxes = document.querySelectorAll('.product-checkbox:checked');
                selectedProducts = Array.from(checkboxes).map(cb => ({
                    productId: cb.dataset.productId,
                    partnerName: cb.dataset.partnerName,
                    productName: cb.dataset.productName,
                    cost: parseFloat(cb.dataset.cost),
                    scope: cb.dataset.scope
                }));

                // Update selected count display
                const countDisplay = document.getElementById('selectedCount');
                const countText = document.getElementById('countText');
                const proceedBtn = document.getElementById('proceedBtn');

                if (selectedProducts.length > 0) {
                    countText.textContent = selectedProducts.length;
                    countDisplay.style.display = 'block';
                    proceedBtn.disabled = false;
                    proceedBtn.textContent = `📝 Generate Proposal with ${selectedProducts.length} Partner Products`;
                } else {
                    countDisplay.style.display = 'none';
                    proceedBtn.disabled = false; // Allow proceeding without partners
                    proceedBtn.textContent = '📝 Proceed to Proposal Generation';
                }

                // Update card styling
                document.querySelectorAll('.recommendation-card').forEach(card => {
                    const checkbox = card.querySelector('.product-checkbox');
                    if (checkbox.checked) {
                        card.classList.add('selected');
                    } else {
                        card.classList.remove('selected');
                    }
                });

                console.log('Selected products:', selectedProducts);
            }

            function proceedToProposal() {
                // Store selected partner products in session/localStorage for proposal generation
                sessionStorage.setItem('selectedPartnerProducts', JSON.stringify(selectedProducts));

                // Proceed to proposal generation with partner data
                window.location.href = `/generate-proposal/{{ project.id }}?partners=${selectedProducts.length}`;
            }

            function showDetails(productId) {
                // You can implement a modal or redirect to product details
                alert(`Product details for ID: ${productId}`);
            }

            // Auto-select high-scoring products (optional)
            document.addEventListener('DOMContentLoaded', function() {
                const highScoreProducts = document.querySelectorAll('.fit-score.high');
                highScoreProducts.forEach(scoreElement => {
                    const card = scoreElement.closest('.recommendation-card');
                    const checkbox = card.querySelector('.product-checkbox');
                    if (checkbox) {
                        checkbox.checked = true;
                    }
                });
                updateSelection();
            });
            </script>
        </body>
        </html>
        ''', project=project, analysis_results=analysis_results, recommendations=recommendations)

    # Helper functions for partner recommendations
    def calculate_simple_fit_score(analysis_results, product):
        """Calculate a simple fit score based on keyword matching"""
        score = 0

        # Combine all requirements text
        all_requirements = []
        all_requirements.extend(analysis_results.get('must_have_requirements', []))
        all_requirements.extend(analysis_results.get('good_to_have_requirements', []))
        all_requirements.extend(analysis_results.get('technical_specifications', []))

        combined_text = ' '.join(all_requirements).lower()

        # Check technical keywords
        if product.technical_keywords:
            for keyword in product.technical_keywords:
                if keyword.lower() in combined_text:
                    score += 15

        # Check category relevance
        category_keywords = {
            'AUTHENTICATION': ['auth', 'login', 'security', 'user', 'identity'],
            'PAYMENT': ['payment', 'billing', 'transaction', 'financial'],
            'ANALYTICS': ['analytics', 'reporting', 'dashboard', 'data'],
            'INTEGRATION': ['integration', 'api', 'connect', 'interface'],
            'STORAGE': ['storage', 'database', 'data', 'backup'],
            'AI_ML': ['ai', 'machine learning', 'artificial intelligence', 'ml']
        }

        if product.category in category_keywords:
            for keyword in category_keywords[product.category]:
                if keyword in combined_text:
                    score += 10

        # Bonus for API availability and cloud native
        if product.api_available:
            score += 5
        if product.cloud_native:
            score += 5

        # Integration complexity penalty
        if product.integration_complexity == 'HIGH':
            score -= 10
        elif product.integration_complexity == 'LOW':
            score += 5

        return min(score, 100)  # Cap at 100%

    def generate_fit_reasoning(analysis_results, product):
        """Generate reasoning for why this product fits"""
        reasons = []

        if product.technical_keywords:
            matching_keywords = []
            all_text = ' '.join(analysis_results.get('must_have_requirements', [])).lower()
            for keyword in product.technical_keywords[:3]:
                if keyword.lower() in all_text:
                    matching_keywords.append(keyword)

            if matching_keywords:
                reasons.append(f"Matches key requirements: {', '.join(matching_keywords)}")

        if product.api_available:
            reasons.append("API integration enables seamless connectivity")

        if product.cloud_native:
            reasons.append("Cloud-native architecture aligns with modern infrastructure")

        if product.integration_complexity == 'LOW':
            reasons.append("Low integration complexity reduces implementation risk")

        return '. '.join(reasons) if reasons else "General compatibility with project requirements"

    def estimate_product_cost(product):
        """Estimate integration cost for a product"""
        base_costs = {
            'LOW': 5000,
            'MEDIUM': 15000,
            'HIGH': 35000
        }

        base_cost = base_costs.get(product.integration_complexity, 15000)

        # Adjust based on features
        if not product.api_available:
            base_cost *= 1.5
        if product.maintenance_required:
            base_cost *= 1.2

        return base_cost

    def determine_integration_scope(fit_score):
        """Determine integration scope based on fit score"""
        if fit_score >= 80:
            return 'CORE'
        elif fit_score >= 60:
            return 'ADDON'
        else:
            return 'OPTIONAL'

    # ========================================
    # HEALTH & STATUS ENDPOINTS
    # ========================================

    @app.route('/health')
    def health_check():
        """Health check endpoint with system status"""
        system_status = get_system_status()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'tender-analysis-system',
            'version': '2.0.0',
            'system_status': system_status
        })

    @app.route('/test-db')
    def test_database():
        """Test database connection"""
        system_status = get_system_status()
        return jsonify(system_status)

    @app.route('/debug-users')
    def debug_users():
        try:
            from models import User
            users = User.query.all()
            return jsonify({
                'user_count': len(users),
                'users': [{'id': u.id, 'username': u.username, 'email': u.email} for u in users]
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/create-admin')
    def force_create_admin():
        try:
            from models import User, db

            # Check if admin exists
            admin = User.query.filter_by(username='admin').first()
            if admin:
                return jsonify({'status': 'Admin already exists', 'username': 'admin'})

            # Create admin user
            admin = User(
                username='admin',
                email='admin@tenderanalysis.com',
                full_name='System Administrator',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

            return jsonify({
                'status': 'Admin user created successfully',
                'username': 'admin',
                'password': 'admin123'
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/test-redis')
    def test_redis():
        """Test Redis connection"""
        try:
            import redis
            redis_url = app.config.get('REDIS_URL') or os.getenv('REDIS_URL')
            if redis_url:
                r = redis.from_url(redis_url)
                r.ping()
                return jsonify({'redis': 'connected', 'url': redis_url, 'status': 'success'})
            else:
                return jsonify({'redis': 'not_configured', 'status': 'warning'})
        except Exception as e:
            return jsonify({'redis': 'error', 'message': str(e), 'status': 'failed'}), 500

    # Register enhanced routes if available
    try:
        from app import create_enhanced_routes
        create_enhanced_routes(app, db, app.config.get('DOCUMENT_PROCESSOR'))
        print("✅ Enhanced multi-document routes registered")
    except Exception as e:
        print(f"⚠️ Enhanced routes not available: {e}")

    return app

def create_celery():
    """Create Celery instance for background tasks"""
    try:
        from celery import Celery

        redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
        print(f"🔗 Connecting to Redis: {redis_url}")

        celery = Celery(
            'tender_system',
            broker=redis_url,
            backend=redis_url
        )

        # Configure Celery
        celery.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            result_expires=3600,
            imports=['tasks'],  # Import tasks module
            include=['tasks'],  # Include tasks module
        )

        @celery.task
        def test_task():
            return "Celery is working!"

        print("✅ Celery configured successfully")
        return celery

    except ImportError:
        print("⚠️ Celery not available - background tasks disabled")
        return None
    except Exception as e:
        print(f"❌ Celery configuration error: {e}")
        return None

# Create application and celery instances
app = create_app()
celery = create_celery()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'

    print("\n" + "="*60)
    print("🚀 TENDER ANALYSIS SYSTEM - FULL FUNCTIONALITY")
    print("="*60)
    print(f"📊 Dashboard: http://localhost:{port}")
    print(f"🔐 Login: admin / admin123")
    print(f"🔍 Health Check: http://localhost:{port}/health")
    print(f"🔧 Debug Mode: {'ON' if debug else 'OFF'}")
    print(f"💾 Database: {os.getenv('DATABASE_URL', 'Local PostgreSQL')}")
    print(f"🔴 Redis: {os.getenv('REDIS_URL', 'Local Redis')}")
    print(f"🤖 AI Processing: {'ENABLED' if os.getenv('ANTHROPIC_API_KEY') else 'DISABLED'}")
    print("="*60)
    print("✅ Available Features:")
    print("  🔐 User Authentication & Session Management")
    print("  📁 Project Management with Multi-Document Support")
    print("  📄 Document Upload with Drag & Drop")
    print("  🤖 AI-Powered Document Analysis")
    print("  📊 Requirements Extraction & Analysis")
    print("  📋 Project Dashboards & Detailed Views")
    print("  🔍 Document-Level Analysis & Insights")
    print("  📝 Proposal Generation Interface")
    print("="*60)

    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)
