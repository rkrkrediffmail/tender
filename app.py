# app.py - Complete functionality with duplicates removed
import os
import uuid
import hashlib
import mimetypes
import logging
import tempfile
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
import json


# Import models and utilities
from models import *

# File upload configuration
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'}

# Initialize Flask-Login (but don't initialize app here)
login_manager = LoginManager()

def configure_app(app):
    """Configure app settings"""
    app.config.setdefault('UPLOAD_FOLDER', 'uploads')
    app.config.setdefault('MAX_CONTENT_LENGTH', 50 * 1024 * 1024)  # 50MB max file size

    # Initialize Flask-Login
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

# ========================================
# AUTHENTICATION ROUTES (Original)
# ========================================

def register_auth_routes(app, db):
    """Register authentication routes"""

    @app.route('/auth/login', methods=['GET', 'POST'])
    def auth_login():
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

    @app.route('/auth/logout')
    @login_required
    def auth_logout():
        logout_user()
        return redirect(url_for('auth_login'))

# ========================================
# ORIGINAL FILE UPLOAD & PROJECT ROUTES
# ========================================

def register_original_routes(app, db):
    """Register original file upload and project management routes"""

    @app.route('/api/upload', methods=['POST'])
    @login_required
    def api_upload_files():
        """Enhanced file uploads with processing"""
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
                try:
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

                except Exception as e:
                    logging.error(f"Error processing file {file.filename}: {e}")
                    return jsonify({'error': f'Error processing {file.filename}'}), 500

        return jsonify({
            'message': f'Successfully uploaded {len(uploaded_files)} files',
            'files': uploaded_files
        })

    @app.route('/api/projects', methods=['GET', 'POST'])
    @login_required
    def api_manage_projects():
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

    @app.route('/api/tasks/create', methods=['POST'])
    @login_required
    def api_create_task():
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
    def api_process_task(task_id):
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
                from agents.document_intelligence import DocumentIntelligenceAgent
                agent = DocumentIntelligenceAgent(task.agent_id)
            elif task.agent.name == 'Requirements Engineering':
                from agents.requirements_engineering import RequirementsEngineeringAgent
                agent = RequirementsEngineeringAgent(task.agent_id)
            else:
                return jsonify({'error': f'Agent {task.agent.name} not implemented yet'}), 501

            # Process task
            import asyncio
            result = asyncio.run(agent.process_task(task_id))

            return jsonify({
                'task_id': task_id,
                'status': 'completed',
                'result': result
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/projects/<project_id>/requirements', methods=['GET'])
    @login_required
    def api_get_requirements(project_id):
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

    @app.route('/api/projects/<project_id>/extract-requirements', methods=['POST'])
    @login_required
    def api_extract_requirements(project_id):
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

    @app.route('/api/documents/<int:document_id>/download')
    @login_required
    def api_download_document(document_id):
        """Download uploaded document"""
        document = Document.query.get(document_id)
        if not document:
            return jsonify({'error': 'Document not found'}), 404

        # Verify user has access
        if document.project.user_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403

        return send_file(document.file_path, as_attachment=True,
                         download_name=document.original_filename)

    @app.route('/api/system/status')
    @login_required
    def api_system_status():
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

# ========================================
# ENHANCED MULTI-DOCUMENT ROUTES (New)
# ========================================

def register_enhanced_routes(app, db, document_processor):
    """Register enhanced multi-document processing routes"""

    @app.route('/projects/create', methods=['GET', 'POST'])
    def create_project():
        if request.method == 'POST':
            project_name = request.form.get('project_name')
            description = request.form.get('description')
            client_name = request.form.get('client_name')

            project = Project(
                name=project_name,
                description=description,
                client_name=client_name
            )

            db.session.add(project)
            db.session.commit()

            flash('Project created successfully!', 'success')
            return redirect(url_for('project_dashboard', project_id=project.id))

        return render_template('create_project.html')

    @app.route('/projects/<project_id>/dashboard')
    def project_dashboard(project_id):
        project = Project.query.get_or_404(project_id)

        # Get project statistics
        documents_count = RFPDocument.query.filter_by(project_id=project_id).count()
        key_points_count = ConsolidatedKeyPoint.query.filter_by(project_id=project_id).count()
        conflicts_count = Conflict.query.filter_by(project_id=project_id, status='pending').count()
        missing_info_count = MissingInformation.query.filter_by(project_id=project_id, status='pending').count()

        recent_documents = RFPDocument.query.filter_by(project_id=project_id)\
                                          .order_by(RFPDocument.uploaded_at.desc())\
                                          .limit(5).all()

        return render_template('project_dashboard.html',
                             project=project,
                             documents_count=documents_count,
                             key_points_count=key_points_count,
                             conflicts_count=conflicts_count,
                             missing_info_count=missing_info_count,
                             recent_documents=recent_documents)

    @app.route('/projects/<project_id>/upload', methods=['GET', 'POST'])
    def upload_documents(project_id):
        project = Project.query.get_or_404(project_id)

        if request.method == 'POST':
            uploaded_files = request.files.getlist('documents')

            if not uploaded_files or uploaded_files[0].filename == '':
                flash('No files selected', 'error')
                return redirect(request.url)

            processed_files = []
            errors = []

            for file in uploaded_files:
                if file and document_processor and document_processor.allowed_file(file.filename):
                    try:
                        # Save file
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_filename = f"{timestamp}_{filename}"
                        file_path = os.path.join(document_processor.upload_folder, unique_filename)
                        file.save(file_path)

                        # Extract text
                        extracted_text = document_processor.extract_text_from_file(file_path, file.content_type)

                        # Classify document
                        doc_type = document_processor.classify_document(filename, extracted_text)

                        # Create document record
                        rfp_doc = RFPDocument(
                            project_id=project_id,
                            filename=unique_filename,
                            original_name=filename,
                            document_type=doc_type,
                            mime_type=file.content_type,
                            file_size=os.path.getsize(file_path),
                            file_path=file_path,
                            extracted_text=extracted_text,
                            processing_status='processing'
                        )

                        db.session.add(rfp_doc)
                        db.session.commit()

                        # Extract key points
                        key_points_data = document_processor.extract_key_points(extracted_text, rfp_doc.id)

                        # Save key points
                        for kp_data in key_points_data:
                            key_point = KeyPoint(
                                document_id=rfp_doc.id,
                                project_id=project_id,
                                content=kp_data['content'],
                                type=kp_data['type'],
                                priority=kp_data['priority'],
                                page=kp_data.get('page'),
                                section=kp_data.get('section'),
                                confidence=kp_data.get('confidence', 0.8),
                                tags=kp_data.get('tags', [])
                            )
                            db.session.add(key_point)

                        # Update document status
                        rfp_doc.processing_status = 'completed'
                        rfp_doc.processed_at = datetime.utcnow()

                        processed_files.append(filename)

                    except Exception as e:
                        errors.append(f"Error processing {filename}: {str(e)}")
                        logging.error(f"Error processing file {filename}: {e}")
                else:
                    errors.append(f"Invalid file type: {file.filename}")

            db.session.commit()

            # If multiple documents, run consolidation
            if len(processed_files) > 0:
                try:
                    from utils import consolidate_project_key_points, detect_project_conflicts, identify_project_missing_info
                    consolidate_project_key_points(project_id)
                    detect_project_conflicts(project_id)
                    identify_project_missing_info(project_id)
                except Exception as e:
                    logging.error(f"Error in post-processing: {e}")

            if processed_files:
                flash(f'Successfully processed {len(processed_files)} documents', 'success')
            if errors:
                for error in errors:
                    flash(error, 'error')

            return redirect(url_for('project_dashboard', project_id=project_id))

        return render_template('upload_documents.html', project=project)

    @app.route('/projects/<project_id>/key-points')
    def view_key_points(project_id):
        project = Project.query.get_or_404(project_id)

        # Get filter parameters
        point_type = request.args.get('type', 'all')
        priority = request.args.get('priority', 'all')
        search = request.args.get('search', '')

        # Build query
        query = ConsolidatedKeyPoint.query.filter_by(project_id=project_id)

        if point_type != 'all':
            query = query.filter(ConsolidatedKeyPoint.type == point_type)

        if priority != 'all':
            query = query.filter(ConsolidatedKeyPoint.priority == priority)

        if search:
            query = query.filter(ConsolidatedKeyPoint.content.contains(search))

        key_points = query.order_by(
            db.case(
                (ConsolidatedKeyPoint.priority == 'critical', 1),
                (ConsolidatedKeyPoint.priority == 'high', 2),
                (ConsolidatedKeyPoint.priority == 'medium', 3),
                (ConsolidatedKeyPoint.priority == 'low', 4)
            )
        ).all()

        # Get available types and priorities for filters
        available_types = db.session.query(ConsolidatedKeyPoint.type.distinct())\
                                   .filter_by(project_id=project_id).all()
        available_types = [t[0] for t in available_types]

        return render_template('key_points.html',
                             project=project,
                             key_points=key_points,
                             available_types=available_types,
                             current_type=point_type,
                             current_priority=priority,
                             search_term=search)

    @app.route('/projects/<project_id>/conflicts')
    def view_conflicts(project_id):
        project = Project.query.get_or_404(project_id)

        status_filter = request.args.get('status', 'all')

        query = Conflict.query.filter_by(project_id=project_id)
        if status_filter != 'all':
            query = query.filter(Conflict.status == status_filter)

        conflicts = query.order_by(Conflict.created_at.desc()).all()

        return render_template('conflicts.html',
                             project=project,
                             conflicts=conflicts,
                             current_status=status_filter)

    @app.route('/projects/<project_id>/missing-info')
    def view_missing_info(project_id):
        project = Project.query.get_or_404(project_id)

        importance_filter = request.args.get('importance', 'all')
        status_filter = request.args.get('status', 'pending')

        query = MissingInformation.query.filter_by(project_id=project_id)

        if importance_filter != 'all':
            query = query.filter(MissingInformation.importance == importance_filter)

        if status_filter != 'all':
            query = query.filter(MissingInformation.status == status_filter)

        missing_info = query.order_by(
            db.case(
                (MissingInformation.importance == 'critical', 1),
                (MissingInformation.importance == 'high', 2),
                (MissingInformation.importance == 'medium', 3),
                (MissingInformation.importance == 'low', 4)
            )
        ).all()

        return render_template('missing_info.html',
                             project=project,
                             missing_info=missing_info,
                             current_importance=importance_filter,
                             current_status=status_filter)

    @app.route('/projects/<project_id>/export/markdown')
    def export_markdown(project_id):
        project = Project.query.get_or_404(project_id)

        # Generate comprehensive markdown report
        from utils import generate_project_markdown_report
        markdown_content = generate_project_markdown_report(project_id)

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(markdown_content)
            temp_path = f.name

        return send_file(temp_path,
                        as_attachment=True,
                        download_name=f"{project.name}_analysis_report.md",
                        mimetype='text/markdown')

    @app.route('/api/projects/<project_id>/summary')
    def api_project_summary(project_id):
        project = Project.query.get_or_404(project_id)

        documents_count = RFPDocument.query.filter_by(project_id=project_id).count()
        key_points_count = ConsolidatedKeyPoint.query.filter_by(project_id=project_id).count()
        conflicts_count = Conflict.query.filter_by(project_id=project_id, status='pending').count()
        missing_info_count = MissingInformation.query.filter_by(project_id=project_id, status='pending').count()

        return jsonify({
            'project': {
                'id': project.id,
                'name': project.name,
                'status': project.status,
                'created_at': project.created_at.isoformat()
            },
            'summary': {
                'documents_count': documents_count,
                'key_points_count': key_points_count,
                'conflicts_count': conflicts_count,
                'missing_info_count': missing_info_count
            }
        })

    @app.route('/api/projects/<project_id>/reprocess')
    def reprocess_project(project_id):
        """Reprocess all documents in a project"""
        try:
            from utils import consolidate_project_key_points, detect_project_conflicts, identify_project_missing_info
            consolidate_project_key_points(project_id)
            detect_project_conflicts(project_id)
            identify_project_missing_info(project_id)

            return jsonify({'status': 'success', 'message': 'Project reprocessed successfully'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

# ========================================
# MAIN FUNCTION TO CREATE ALL ROUTES
# ========================================

def create_enhanced_routes(app, db, document_processor):
    """Main function to register all routes without duplicates"""

    # Configure the app
    configure_app(app)

    # Register all route groups
    register_auth_routes(app, db)
    register_original_routes(app, db)
    register_enhanced_routes(app, db, document_processor)

    # Basic health check route
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'tender-analysis-system',
            'features': ['original-upload', 'multi-document', 'ai-processing']
        })

    # Basic dashboard route (fallback)
    @app.route('/dashboard')
    def fallback_dashboard():
        return jsonify({
            'message': 'Tender Analysis System Dashboard',
            'status': 'operational',
            'routes': ['auth', 'projects', 'upload', 'analysis']
        })

    return app
