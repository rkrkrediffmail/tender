# routes.py - Flask Route Definitions
import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash

from models import db, User, Project, Document, Agent, Requirement, AgentTask
from tasks import process_document_task, analyze_requirements_task

# Create Blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
api_bp = Blueprint('api', __name__)

# File upload configuration
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Main Routes
@main_bp.route('/')
def index():
    """Dashboard - main page"""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    # Get user's projects and recent activity
    user_projects = Project.query.filter_by(user_id=current_user.id).limit(5).all()
    recent_tasks = AgentTask.query.join(Project).filter(
        Project.user_id == current_user.id
    ).order_by(AgentTask.created_at.desc()).limit(10).all()

    return render_template('dashboard.html',
                         projects=user_projects,
                         recent_tasks=recent_tasks)

@main_bp.route('/projects')
@login_required
def projects():
    """Projects listing page"""
    user_projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('projects.html', projects=user_projects)

@main_bp.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    """Project detail page"""
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    return render_template('project_detail.html', project=project)

@main_bp.route('/upload')
@login_required
def upload_page():
    """Document upload page"""
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('upload.html', projects=projects)

# Authentication Routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')

        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('auth/register.html')

        # Create new user
        user = User(
            username=username,
            email=email,
            full_name=full_name
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    return redirect(url_for('auth.login'))

# API Routes
@api_bp.route('/projects', methods=['POST'])
@login_required
def create_project():
    """Create new project"""
    try:
        data = request.get_json()

        project = Project(
            name=data.get('name'),
            description=data.get('description'),
            rfp_title=data.get('rfp_title'),
            client_name=data.get('client_name'),
            submission_deadline=datetime.fromisoformat(data.get('submission_deadline')) if data.get('submission_deadline') else None,
            estimated_value=data.get('estimated_value'),
            currency=data.get('currency', 'USD'),
            priority=data.get('priority', 'medium'),
            user_id=current_user.id
        )

        db.session.add(project)
        db.session.commit()

        return jsonify({
            'success': True,
            'project_id': project.id,
            'message': 'Project created successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@api_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Handle file upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['file']
        project_id = request.form.get('project_id')

        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'File type not allowed'}), 400

        # Verify project ownership
        project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        # Save file
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)

        # Create document record
        document = Document(
            filename=filename,
            original_filename=filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            mime_type=file.content_type,
            project_id=project_id,
            uploaded_by=current_user.id
        )

        db.session.add(document)
        db.session.commit()

        # Start background processing
        process_document_task.delay(document.id)

        return jsonify({
            'success': True,
            'document_id': document.id,
            'message': 'File uploaded successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/project/<int:project_id>/analyze', methods=['POST'])
@login_required
def analyze_project_requirements(project_id):
    """Start requirements analysis for a project"""
    try:
        project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()

        # Start background analysis
        task = analyze_requirements_task.delay(project_id)

        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Requirements analysis started'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/task/<task_id>/status')
@login_required
def get_task_status(task_id):
    """Get status of background task"""
    try:
        from main import celery
        task = celery.AsyncResult(task_id)

        return jsonify({
            'task_id': task_id,
            'status': task.status,
            'result': task.result if task.status == 'SUCCESS' else None,
            'error': str(task.result) if task.status == 'FAILURE' else None
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/health')
def health_check():
    """API health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'tender-analysis-api'
    })
