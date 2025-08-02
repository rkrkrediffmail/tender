# app.py - Enhanced with file processing and API endpoints
import os
import uuid
import hashlib
import mimetypes
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash

# Import enhanced models and agents
from models import *
from agents.document_intelligence import DocumentIntelligenceAgent
from agents.requirements_engineering import RequirementsEngineeringAgent

# Configure file uploads
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'}

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Enhanced file upload endpoint
@app.route('/api/upload', methods=['POST'])
@login_required
def upload_files():
    """Handle file uploads with processing"""

    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    project_id = request.form.get('project_id')

    if not project_id:
        return jsonify({'error': 'Project ID required'}), 400

    # Verify project exists and user has access
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        return jsonify({'error': 'Project not found or access denied'}), 404

    uploaded_files = []

    for file in files:
        if file and file.filename and allowed_file(file.filename):
            # Generate unique filename
            filename = str(uuid.uuid4()) + '_' + secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Ensure upload directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            # Save file
            file.save(file_path)

            # Calculate file hash and get metadata
            file_hash = calculate_file_hash(file_path)
            file_size = os.path.getsize(file_path)
            mime_type = mimetypes.guess_type(file_path)[0]

            # Save to database
            document = Document(
                filename=filename,
                original_filename=file.filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                file_hash=file_hash,
                project_id=project_id,
                uploaded_by=current_user.id,
                processing_status='uploaded'
            )

            db.session.add(document)
            db.session.commit()

            # Create document analysis task
            doc_agent = Agent.query.filter_by(name='Document Intelligence').first()
            if doc_agent:
                analysis_task = AgentTask(
                    task_type='document_analysis',
                    title=f'Analyze {file.filename}',
                    description=f'Extract and analyze content from {file.filename}',
                    agent_id=doc_agent.id,
                    project_id=project_id,
                    input_data={'document_id': document.id},
                    status='pending'
                )
                db.session.add(analysis_task)
                db.session.commit()

            uploaded_files.append({
                'id': document.id,
                'filename': file.filename,
                'size': file_size,
                'status': 'uploaded',
                'task_id': analysis_task.task_id if doc_agent else None
            })

    return jsonify({
        'message': f'Successfully uploaded {len(uploaded_files)} files',
        'files': uploaded_files
    })

# Enhanced project management
@app.route('/api/projects', methods=['GET', 'POST'])
@login_required
def manage_projects():
    """Get user projects or create new project"""

    if request.method == 'POST':
        data = request.get_json()

        project = Project(
            name=data['name'],
            description=data.get('description', ''),
            rfp_title=data.get('rfp_title', ''),
            client_name=data.get('client_name', ''),
            estimated_value=data.get('estimated_value'),
            currency=data.get('currency', 'USD'),
            priority=data.get('priority', 'medium'),
            user_id=current_user.id
        )

        db.session.add(project)
        db.session.commit()

        return jsonify({
            'id': project.id,
            'name': project.name,
            'status': project.status,
            'created_at': project.created_at.isoformat()
        })

    else:
        projects = Project.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'status': p.status,
            'priority': p.priority,
            'completion_percentage': p.completion_percentage,
            'created_at': p.created_at.isoformat()
        } for p in projects])

# Task management and processing
@app.route('/api/tasks/create', methods=['POST'])
@login_required
def create_task():
    """Create new agent task"""

    data = request.get_json()

    # Verify agent exists
    agent = Agent.query.get(data['agent_id'])
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404

    # Verify project access
    project = Project.query.filter_by(id=data['project_id'], user_id=current_user.id).first()
    if not project:
        return jsonify({'error': 'Project not found or access denied'}), 404

    task = AgentTask(
        task_type=data['task_type'],
        title=data['title'],
        description=data.get('description', ''),
        priority=data.get('priority', 'medium'),
        input_data=data.get('input_data', {}),
        agent_id=data['agent_id'],
        project_id=data['project_id'],
        status='pending'
    )

    db.session.add(task)
    db.session.commit()

    return jsonify({
        'task_id': task.task_id,
        'status': task.status,
        'created_at': task.created_at.isoformat()
    })

@app.route('/api/tasks/<task_id>/process', methods=['POST'])
@login_required
def process_task(task_id):
    """Process a specific task"""

    task = AgentTask.query.filter_by(task_id=task_id).first()
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    # Verify user has access to the project
    if task.project.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    try:
        # Initialize appropriate agent based on task type
        if task.agent.name == 'Document Intelligence':
            agent = DocumentIntelligenceAgent(task.agent_id)
        elif task.agent.name == 'Requirements Engineering':
            agent = RequirementsEngineeringAgent(task.agent_id)
        else:
            return jsonify({'error': f'Agent {task.agent.name} not implemented yet'}), 501

        # Process task asynchronously (in a real app, use Celery or similar)
        import asyncio
        result = asyncio.run(agent.process_task(task_id))

        return jsonify({
            'task_id': task_id,
            'status': 'completed',
            'result': result
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Requirements management
@app.route('/api/projects/<int:project_id>/requirements', methods=['GET'])
@login_required
def get_requirements(project_id):
    """Get requirements for a project"""

    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        return jsonify({'error': 'Project not found or access denied'}), 404

    requirements = Requirement.query.filter_by(project_id=project_id).all()

    return jsonify([{
        'id': req.id,
        'requirement_id': req.requirement_id,
        'title': req.title,
        'description': req.description,
        'type': req.requirement_type,
        'priority': req.priority,
        'complexity': req.complexity,
        'status': req.status,
        'estimated_effort': req.estimated_effort,
        'dependencies': req.dependencies,
        'conflicts_with': req.conflicts_with,
        'acceptance_criteria': req.acceptance_criteria
    } for req in requirements])

@app.route('/api/projects/<int:project_id>/extract-requirements', methods=['POST'])
@login_required
def extract_requirements(project_id):
    """Extract requirements from project documents"""

    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        return jsonify({'error': 'Project not found or access denied'}), 404

    # Get requirements engineering agent
    req_agent = Agent.query.filter_by(name='Requirements Engineering').first()
    if not req_agent:
        return jsonify({'error': 'Requirements Engineering agent not found'}), 500

    # Create extraction task
    task = AgentTask(
        task_type='requirement_extraction',
        title=f'Extract requirements for {project.name}',
        description='Extract and analyze requirements from project documents',
        agent_id=req_agent.id,
        project_id=project_id,
        input_data={'project_id': project_id},
        status='pending'
    )

    db.session.add(task)
    db.session.commit()

    return jsonify({
        'task_id': task.task_id,
        'message': 'Requirements extraction task created',
        'status': 'pending'
    })

# Document download endpoint
@app.route('/api/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    """Download uploaded document"""

    document = Document.query.get(document_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # Verify user has access
    if document.project.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    return send_file(document.file_path, as_attachment=True,
                     download_name=document.original_filename)

# System monitoring endpoints
@app.route('/api/system/status')
@login_required
def system_status():
    """Get overall system status"""

    agents = Agent.query.all()
    active_tasks = AgentTask.query.filter_by(status='in_progress').count()
    pending_tasks = AgentTask.query.filter_by(status='pending').count()
    total_projects = Project.query.filter_by(user_id=current_user.id).count()

    return jsonify({
        'agents': {
            'total': len(agents),
            'online': len([a for a in agents if a.status == 'online']),
            'offline': len([a for a in agents if a.status == 'offline'])
        },
        'tasks': {
            'active': active_tasks,
            'pending': pending_tasks
        },
        'projects': {
            'total': total_projects
        },
        'system_health': 'healthy'
    })
