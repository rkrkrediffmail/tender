#!/usr/bin/env python3
"""
Complete main.py with full functionality - PURE PYTHON VERSION
All HTML templates moved to /templates folder
"""

import os
import sys
import uuid
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash, send_file, make_response
from werkzeug.utils import secure_filename
from datetime import datetime
from dotenv import load_dotenv

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

def handle_upload_completion(project_id, uploaded_documents):
    """Handle completion of document uploads and trigger post-analysis"""
    try:
        from models import Project, Document

        # Check if all documents have been processed
        project_documents = Document.query.filter_by(project_id=project_id).all()
        all_processed = all(doc.extracted_content for doc in project_documents)

        if all_processed and len(project_documents) > 0:
            # All documents processed - redirect to post-analysis
            return {
                'success': True,
                'redirect_to': f'/post_analysis/{project_id}',
                'message': 'Documents processed successfully. Starting post-upload analysis...'
            }
        else:
            # Still processing
            return {
                'success': True,
                'status': 'processing',
                'message': 'Documents still being processed...'
            }

    except Exception as e:
        return {
            'success': False,
            'error': f'Error checking upload completion: {str(e)}'
        }

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

    # Create tables and initialize database
    with app.app_context():
        try:
            # Create all tables (including new ones)
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Verify AI analysis table exists
            try:
                from models import AIAnalysisResult
                # Test if the table exists by doing a simple query
                AIAnalysisResult.query.count()
                print("✅ AI Analysis Results table verified")
            except Exception as table_error:
                print(f"⚠️ AI Analysis table issue: {table_error}")
                # Force recreation of all tables
                db.create_all()
                print("✅ Database schema updated with AI analysis support")
            
            # Initialize workflow configuration
            try:
                from workflow_manager import setup_default_config
                setup_default_config()
                print("✅ Workflow configuration initialized")
            except Exception as wf_error:
                print(f"⚠️ Workflow setup error: {wf_error}")
                
        except Exception as e:
            print(f"❌ Database error: {e}")

    def get_system_status():
        """Get real-time system status"""
        status = {
            'web_running': True,
            'database_status': 'unknown',
            'database_initialized': False,
            'processing_mode': 'synchronous',
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

        # No background processing needed in simplified mode
        status['processing_mode'] = 'synchronous - documents processed immediately'

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
            status['processing_mode'] == 'synchronous - documents processed immediately' and
            status['api_keys_configured']
        )

        return status

    # ========================================
    # AUTHENTICATION ROUTES
    # ========================================

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Login page and handler"""
        if request.method == 'GET':
            if 'username' in session:
                return redirect('/')
            return render_template('auth/login.html')

        # POST request - handle login
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

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration"""
        if request.method == 'GET':
            return render_template('auth/register.html')

        # POST request - handle registration
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            from models import User

            # Check if user exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return render_template('auth/register.html')

            # Create new user
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            flash('Registration successful! Please log in.', 'success')
            return redirect('/login')

        except Exception as e:
            flash(f'Registration error: {e}', 'error')
            return render_template('auth/register.html')

    # ========================================
    # MAIN DASHBOARD
    # ========================================

    @app.route('/')
    @login_required
    def dashboard():
        """Main dashboard"""
        system_status = get_system_status()

        try:
            from models import User, Project
            user = User.query.filter_by(username=session['username']).first()
            # Show only active, non-purged projects on dashboard
            user_projects = Project.query.filter(
                Project.user_id == user.id,
                Project.status == 'active',
                Project.purged_at.is_(None)
            ).order_by(Project.created_at.desc()).limit(5).all()
        except Exception as e:
            user_projects = []

        return render_template('dashboard.html',
                             system_status=system_status,
                             user_projects=user_projects,
                             user=session.get('username'))

    @app.route('/api/dashboard/stats')
    @login_required
    def dashboard_stats():
        """Get real-time dashboard statistics"""
        try:
            from models import User, Project, Document
            from datetime import datetime, timedelta
            
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not found'})
            
            # Get active project statistics (excluding purged and non-active)
            active_projects_query = Project.query.filter(
                Project.user_id == user.id,
                Project.status == 'active',
                Project.purged_at.is_(None)
            )
            total_active_projects = active_projects_query.count()
            
            # Recent active projects (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_active_projects = Project.query.filter(
                Project.user_id == user.id,
                Project.status == 'active',
                Project.purged_at.is_(None),
                Project.created_at >= thirty_days_ago
            ).count()
            
            # Recent active projects list with details (last 10)
            projects_list = Project.query.filter(
                Project.user_id == user.id,
                Project.status == 'active',
                Project.purged_at.is_(None)
            ).order_by(Project.created_at.desc()).limit(10).all()
            
            # Additional innovative statistics for RFP system
            # Completed projects count
            completed_projects = Project.query.filter(
                Project.user_id == user.id,
                Project.status == 'completed',
                Project.purged_at.is_(None)
            ).count()
            
            # Projects by RFP type
            rfp_type_stats = db.session.query(
                Project.rfp_type, 
                db.func.count(Project.id).label('count')
            ).filter(
                Project.user_id == user.id,
                Project.status == 'active',
                Project.purged_at.is_(None)
            ).group_by(Project.rfp_type).all()
            
            # Average completion percentage of active projects
            avg_completion = db.session.query(
                db.func.avg(Project.completion_percentage)
            ).filter(
                Project.user_id == user.id,
                Project.status == 'active',
                Project.purged_at.is_(None)
            ).scalar() or 0
            
            projects_data = []
            for project in projects_list:
                # Get document count for each project
                doc_count = Document.query.filter_by(project_id=project.id).count()
                projects_data.append({
                    'id': project.id,
                    'name': project.name,
                    'client_name': project.client_name or 'No client specified',
                    'created_at': project.created_at.strftime('%Y-%m-%d %H:%M') if project.created_at else 'Unknown',
                    'document_count': doc_count,
                    'status': project.status,
                    'rfp_type': project.rfp_type or 'implementation',
                    'completion_percentage': project.completion_percentage or 0,
                    'estimated_value': str(project.estimated_value) if project.estimated_value else None,
                    'currency': project.currency or 'USD',
                    'priority': project.priority or 'medium'
                })
            
            # Activity count (documents uploaded in last 7 days for active projects)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_activity = Document.query.join(Project).filter(
                Project.user_id == user.id,
                Project.status == 'active',
                Project.purged_at.is_(None),
                Document.uploaded_at >= seven_days_ago
            ).count()
            
            # Convert RFP type stats to dictionary
            rfp_types = {item.rfp_type: item.count for item in rfp_type_stats}
            
            return jsonify({
                'success': True,
                'stats': {
                    'active_projects': total_active_projects,
                    'completed_projects': completed_projects,
                    'recent_active_projects': recent_active_projects,
                    'recent_activity': recent_activity,
                    'avg_completion': round(float(avg_completion), 1),
                    'rfp_types': rfp_types,
                    'projects': projects_data,
                    'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                }
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    # ========================================
    # PROJECT MANAGEMENT
    # ========================================

    @app.route('/projects')
    @login_required
    def projects():
        """Projects page"""
        try:
            from models import User, Project
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return redirect('/login')

            # Only show active projects by default (exclude purged)
            user_projects = Project.query.filter_by(user_id=user.id).filter(Project.status != 'purged').all()

        except Exception as e:
            user_projects = []
            flash(f"Error loading projects: {e}")

        return render_template('projects.html', user_projects=user_projects)

    @app.route('/create_project', methods=['GET', 'POST'])
    @login_required
    def create_project_page():
        """Create new project with workflow features"""
        if request.method == 'GET':
            # Get available RFP types for the form
            from workflow_manager import workflow_manager
            rfp_types = workflow_manager.get_available_rfp_types()
            return render_template('create_project.html', rfp_types=rfp_types)

        # POST request - handle project creation
        try:
            from models import User, Project
            from workflow_manager import workflow_manager
            
            user = User.query.filter_by(username=session['username']).first()

            project = Project(
                name=request.form.get('name'),
                description=request.form.get('description'),
                client_name=request.form.get('client_name'),
                rfp_type=request.form.get('rfp_type', 'implementation'),
                priority=request.form.get('priority', 'medium'),
                workflow_stage='created',
                submitted_by=user.id,
                user_id=user.id,
                status='active',
                created_at=datetime.utcnow()
            )

            db.session.add(project)
            db.session.commit()

            # Add stakeholders if provided
            approver_emails = request.form.getlist('approver_emails[]')
            approver_roles = request.form.getlist('approver_roles[]')
            
            for email, role in zip(approver_emails, approver_roles):
                if email.strip():  # Only add non-empty emails
                    workflow_manager.add_stakeholder(
                        project_id=project.id,
                        email=email.strip(),
                        role=role,
                        stage='authorized'  # Default to first approval stage
                    )

            flash('Project created successfully with workflow configured!', 'success')
            return redirect(f'/project/{project.id}')

        except Exception as e:
            flash(f'Error creating project: {e}', 'error')
            from workflow_manager import workflow_manager
            rfp_types = workflow_manager.get_available_rfp_types()
            return render_template('create_project.html', rfp_types=rfp_types)

    @app.route('/project/<project_id>')
    @login_required
    def project_detail(project_id):
        """Project detail page"""
        try:
            from models import User, Project, Document, RFPDocument
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            
            # Get both old documents and new RFP documents
            old_documents = Document.query.filter_by(project_id=project_id).all()
            rfp_documents = RFPDocument.query.filter_by(project_id=project_id).all()
            
            # Combine both document types
            documents = old_documents + rfp_documents

            return render_template('project_detail.html',
                                 project=project,
                                 documents=documents,
                                 documents_count=len(documents),
                                 user=user)
        except Exception as e:
            flash(f"Error loading project: {e}")
            return redirect('/projects')

    # ========================================
    # POST-UPLOAD ANALYSIS ROUTES
    # ========================================

    @app.route('/post_analysis/<project_id>')
    @login_required
    def post_analysis_page(project_id):
        """Display post-upload analysis page"""
        try:
            from models import User, Project
            
            print(f"Debug: post_analysis_page called with project_id={project_id}")
            print(f"Debug: session username={session.get('username')}")
            
            # Use session-based authentication to match the custom login_required decorator
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                flash('User session invalid', 'error')
                return redirect('/login')
                
            project = Project.query.filter_by(id=project_id, user_id=user.id).first()
            
            if not project:
                flash(f'Project {project_id} not found or access denied', 'error')
                return redirect('/projects')
            
            print(f"Debug: Found project {project.id} - {project.name}")
            return render_template('post_analysis.html', project=project)
        except Exception as e:
            print(f"Debug: Exception in post_analysis_page: {e}")
            flash(f'Error loading analysis page: {e}', 'error')
            return redirect('/projects')

    @app.route('/api/post_upload_analysis/<project_id>')
    @login_required
    def get_post_upload_analysis(project_id):
        """Get stored post-upload analysis results or indicate if fresh analysis is needed"""
        try:
            from models import User, Project, Document
            from ai_response_manager import AIResponseManager

            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            documents = Document.query.filter_by(project_id=str(project_id)).all()

            if not documents:
                return jsonify({'error': 'No documents found for analysis'}), 400

            # Check for existing stored AI responses
            clarification_response = AIResponseManager.get_latest_response(project_id, 'clarification_extraction')
            risk_response = AIResponseManager.get_latest_response(project_id, 'risk_analysis')
            deadline_response = AIResponseManager.get_latest_response(project_id, 'deadline_extraction')
            go_no_go_response = AIResponseManager.get_latest_response(project_id, 'go_no_go_recommendation')

            # If we have stored results, return them
            if clarification_response and risk_response and deadline_response and go_no_go_response:
                print("📋 Returning stored AI analysis results...")
                
                results = {
                    'clarification_items': clarification_response.parsed_response or [],
                    'risks_constraints': risk_response.parsed_response or [],
                    'deadlines_milestones': deadline_response.parsed_response or [],
                    'go_no_go_recommendation': go_no_go_response.parsed_response or {},
                    'analysis_timestamp': go_no_go_response.created_at.isoformat(),
                    'documents_analyzed': len(documents),
                    'from_stored_results': True,
                    'last_analysis_date': go_no_go_response.created_at.strftime('%B %d, %Y at %I:%M %p'),
                    'ai_provider_used': go_no_go_response.ai_provider,
                    'stored_response_ids': {
                        'clarification': clarification_response.response_id,
                        'risks': risk_response.response_id,
                        'deadlines': deadline_response.response_id,
                        'go_no_go': go_no_go_response.response_id
                    }
                }

                return jsonify({
                    'success': True,
                    'analysis_results': results,
                    'processing_time': 0.01,  # Instant since stored
                    'message': 'Displaying stored analysis results'
                })
            
            # If no complete stored results, indicate fresh analysis is available
            else:
                partial_results = {}
                missing_analyses = []
                
                if clarification_response:
                    partial_results['clarification_items'] = clarification_response.parsed_response or []
                else:
                    missing_analyses.append('clarification_extraction')
                
                if risk_response:
                    partial_results['risks_constraints'] = risk_response.parsed_response or []
                else:
                    missing_analyses.append('risk_analysis')
                
                if deadline_response:
                    partial_results['deadlines_milestones'] = deadline_response.parsed_response or []
                else:
                    missing_analyses.append('deadline_extraction')
                
                if go_no_go_response:
                    partial_results['go_no_go_recommendation'] = go_no_go_response.parsed_response or {}
                else:
                    missing_analyses.append('go_no_go_recommendation')

                return jsonify({
                    'success': False,
                    'needs_fresh_analysis': True,
                    'partial_results': partial_results,
                    'missing_analyses': missing_analyses,
                    'documents_count': len(documents),
                    'message': f'Analysis incomplete. Missing: {", ".join(missing_analyses)}'
                })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/api/post_upload_analysis/<project_id>/run-fresh', methods=['POST'])
    @login_required
    def run_fresh_post_upload_analysis(project_id):
        """Run fresh comprehensive post-upload analysis for go/no-go decision"""
        import time
        start_time = time.time()
        
        try:
            from models import User, Project, Document, AIAnalysisResult
            from real_analysis_system import RealAnalysisSystem

            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            documents = Document.query.filter_by(project_id=str(project_id)).all()

            if not documents:
                return jsonify({'error': 'No documents found for analysis'}), 400

            # Initialize analysis system
            analysis_system = RealAnalysisSystem(project)

            # Combine all document content
            combined_content = ""
            for doc in documents:
                if doc.extracted_content:
                    combined_content += f"\n\n--- {doc.filename} ---\n{doc.extracted_content}"

            if not combined_content.strip():
                return jsonify({'error': 'No content extracted from documents'}), 400

            # Perform new analyses with progress tracking
            print("🚀 Starting fresh comprehensive AI analysis...")
            clarification_items = analysis_system.extract_clarification_items(combined_content, project_id=project_id)
            risks_constraints = analysis_system.identify_risks_and_constraints(combined_content, project_id=project_id)
            deadlines_milestones = analysis_system.extract_deadlines_and_milestones(combined_content, project_id=project_id)

            # Generate go/no-go recommendation
            go_no_go_recommendation = analysis_system.generate_go_no_go_recommendation(
                clarification_items, risks_constraints, deadlines_milestones, project_id=project_id
            )
            print("✅ Fresh analysis completed successfully")

            # Prepare results
            results = {
                'clarification_items': clarification_items,
                'risks_constraints': risks_constraints,
                'deadlines_milestones': deadlines_milestones,
                'go_no_go_recommendation': go_no_go_recommendation,
                'analysis_timestamp': datetime.now().isoformat(),
                'documents_analyzed': len(documents),
                'from_stored_results': False,
                'total_content_length': len(combined_content)
            }

            # Store analysis results in database
            processing_time = time.time() - start_time
            
            try:
                from models import AIAnalysisResult
                ai_analysis = AIAnalysisResult(
                    project_id=project_id,
                    analysis_type='post_upload',
                    results=results,
                    ai_model_used='claude-sonnet-4-20250514',
                    processing_time_seconds=processing_time,
                    status='completed'
                )
                
                db.session.add(ai_analysis)
                db.session.commit()
                print(f"✅ Fresh analysis stored with ID: {ai_analysis.analysis_id}")
            except Exception as db_error:
                print(f"Warning: Could not store analysis in AIAnalysisResult: {db_error}")

            return jsonify({
                'success': True, 
                'analysis_results': results,
                'processing_time': processing_time,
                'message': 'Fresh analysis completed successfully'
            })

        except Exception as e:
            print(f"Fresh analysis error: {e}")
            # Store failed analysis
            try:
                processing_time = time.time() - start_time
                failed_analysis = AIAnalysisResult(
                    project_id=project_id,
                    analysis_type='post_upload',
                    results={},
                    status='failed',
                    error_message=str(e),
                    processing_time_seconds=processing_time
                )
                db.session.add(failed_analysis)
                db.session.commit()
            except:
                pass
                
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/debug/analysis/<project_id>', methods=['GET'])
    @login_required
    def debug_analysis(project_id):
        """Debug endpoint to test individual analysis components"""
        try:
            from models import User, Project, Document
            from real_analysis_system import RealAnalysisSystem
            
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            documents = Document.query.filter_by(project_id=str(project_id)).all()
            
            if not documents:
                return jsonify({'error': 'No documents found'}), 400
            
            # Get test content
            combined_content = ""
            for doc in documents:
                if doc.extracted_content:
                    combined_content += f"\n\n--- {doc.filename} ---\n{doc.extracted_content}"
            
            if not combined_content.strip():
                return jsonify({'error': 'No content extracted from documents'}), 400
            
            # Initialize analysis system
            analysis_system = RealAnalysisSystem(project)
            
            # Test component requested
            component = request.args.get('component', 'all')
            results = {}
            
            if component in ['all', 'clarification']:
                print("🔍 Testing clarification items extraction...")
                results['clarification_items'] = analysis_system.extract_clarification_items(combined_content[:5000])
                
            if component in ['all', 'risks']:
                print("🔍 Testing risks and constraints extraction...")
                results['risks_constraints'] = analysis_system.identify_risks_and_constraints(combined_content[:5000])
                
            if component in ['all', 'deadlines']:
                print("🔍 Testing deadlines and milestones extraction...")
                results['deadlines_milestones'] = analysis_system.extract_deadlines_and_milestones(combined_content[:5000])
            
            if component in ['all', 'recommendation']:
                print("🔍 Testing go/no-go recommendation...")
                # Use minimal test data for recommendation
                test_clarifications = [{"category": "TEST", "impact_level": "Low"}]
                test_risks = [{"risk_type": "TEST", "severity_level": "Low"}] 
                test_deadlines = [{"type": "TEST", "critical_level": "Standard"}]
                
                results['go_no_go_recommendation'] = analysis_system.generate_go_no_go_recommendation(
                    test_clarifications, test_risks, test_deadlines
                )
            
            # Add debug information
            results['debug_info'] = {
                'ai_providers_available': len(analysis_system.ai_manager.available_providers),
                'content_length': len(combined_content),
                'documents_count': len(documents),
                'component_tested': component,
                'vector_store_available': analysis_system.proposal_manager is not None
            }
            
            return jsonify(results)
            
        except Exception as e:
            return jsonify({
                'error': 'Debug analysis failed',
                'details': str(e)
            }), 500

    # ========================================
    # WORKFLOW MANAGEMENT API ENDPOINTS
    # ========================================

    @app.route('/api/workflow/transition/<project_id>', methods=['POST'])
    @login_required
    def transition_workflow(project_id):
        """Transition project to next workflow stage"""
        try:
            from workflow_manager import workflow_manager
            
            data = request.get_json()
            to_stage = data.get('to_stage')
            comments = data.get('comments', '')
            
            # Get current user email
            from models import User
            user = User.query.filter_by(username=session['username']).first()
            actor_email = user.email if user else session['username']
            actor_name = user.full_name if user and user.full_name else actor_email
            
            result = workflow_manager.transition_workflow(
                project_id=project_id,
                to_stage=to_stage,
                actor_email=actor_email,
                actor_name=actor_name,
                comments=comments
            )
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/workflow/stakeholders/<project_id>', methods=['GET', 'POST'])
    @login_required
    def manage_project_stakeholders(project_id):
        """Get or add project stakeholders"""
        from workflow_manager import workflow_manager
        
        if request.method == 'GET':
            try:
                stakeholders = workflow_manager.get_project_stakeholders(project_id)
                return jsonify({'stakeholders': stakeholders})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        elif request.method == 'POST':
            try:
                data = request.get_json()
                result = workflow_manager.add_stakeholder(
                    project_id=project_id,
                    email=data.get('email'),
                    name=data.get('name'),
                    role=data.get('role', 'approver'),
                    stage=data.get('stage', 'authorized'),
                    notification_preference=data.get('notification_preference', 'email'),
                    teams_webhook=data.get('teams_webhook')
                )
                
                if result['success']:
                    return jsonify(result)
                else:
                    return jsonify(result), 400
                    
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/workflow/history/<project_id>')
    @login_required
    def get_workflow_history(project_id):
        """Get workflow history for a project"""
        try:
            from workflow_manager import workflow_manager
            history = workflow_manager.get_workflow_history(project_id)
            return jsonify({'history': history})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/workflow/config/types')
    @login_required
    def get_rfp_types():
        """Get available RFP types"""
        try:
            from workflow_manager import workflow_manager
            types = workflow_manager.get_available_rfp_types()
            return jsonify({'rfp_types': types})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/workflow/config/stages')
    @login_required
    def get_workflow_stages():
        """Get available workflow stages"""
        try:
            from workflow_manager import workflow_manager
            stages = workflow_manager.get_workflow_stages()
            return jsonify({'workflow_stages': stages})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/project/<project_id>/workflow')
    @login_required
    def workflow_management(project_id):
        """Workflow management page for a project"""
        try:
            from models import User, Project
            
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            
            return render_template('workflow_management.html', project=project)
            
        except Exception as e:
            flash(f'Error loading workflow management: {e}', 'error')
            return redirect(f'/project/{project_id}')

    # ========================================
    # AI ANALYSIS RESULTS MANAGEMENT
    # ========================================

    @app.route('/project/<project_id>/analysis-history')
    @login_required
    def view_analysis_history(project_id):
        """View all AI analysis results for a project"""
        try:
            from models import User, Project, AIAnalysisResult
            
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            
            # Get all analysis results for this project
            analyses = AIAnalysisResult.query.filter_by(project_id=project_id)\
                                           .order_by(AIAnalysisResult.created_at.desc())\
                                           .all()
            
            return render_template('analysis_history.html', 
                                 project=project, 
                                 analyses=analyses)
        except Exception as e:
            flash(f'Error loading analysis history: {e}', 'error')
            return redirect(f'/project/{project_id}')

    @app.route('/api/analysis/<analysis_id>')
    @login_required
    def get_analysis_result(analysis_id):
        """Get specific analysis result"""
        try:
            from models import User, AIAnalysisResult
            
            user = User.query.filter_by(username=session['username']).first()
            analysis = AIAnalysisResult.query.filter_by(analysis_id=analysis_id).first_or_404()
            
            # Verify user has access to this project
            project = Project.query.filter_by(id=analysis.project_id, user_id=user.id).first()
            if not project:
                return jsonify({'error': 'Access denied'}), 403
            
            # Mark as viewed
            analysis.mark_viewed()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'analysis': {
                    'id': analysis.analysis_id,
                    'type': analysis.analysis_type,
                    'results': analysis.results,
                    'created_at': analysis.created_at.isoformat(),
                    'processing_time': analysis.processing_time_seconds,
                    'ai_model': analysis.ai_model_used,
                    'status': analysis.status,
                    'viewed_count': analysis.viewed_count
                }
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/project/<project_id>/analysis/<analysis_id>')
    @login_required
    def view_analysis_detail(project_id, analysis_id):
        """View detailed analysis result page"""
        try:
            from models import User, Project, AIAnalysisResult
            
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            analysis = AIAnalysisResult.query.filter_by(analysis_id=analysis_id, project_id=project_id).first_or_404()
            
            # Mark as viewed
            analysis.mark_viewed()
            db.session.commit()
            
            return render_template('analysis_detail.html', 
                                 project=project, 
                                 analysis=analysis)
        except Exception as e:
            flash(f'Error loading analysis: {e}', 'error')
            return redirect(f'/project/{project_id}')

    @app.route('/api/analysis/<analysis_id>/feedback', methods=['POST'])
    @login_required
    def submit_analysis_feedback(analysis_id):
        """Submit user feedback on analysis quality"""
        try:
            from models import User, AIAnalysisResult
            
            data = request.get_json()
            rating = data.get('rating')
            feedback = data.get('feedback', '')
            
            user = User.query.filter_by(username=session['username']).first()
            analysis = AIAnalysisResult.query.filter_by(analysis_id=analysis_id).first_or_404()
            
            # Verify user has access to this project
            project = Project.query.filter_by(id=analysis.project_id, user_id=user.id).first()
            if not project:
                return jsonify({'error': 'Access denied'}), 403
            
            # Update feedback
            analysis.user_rating = rating
            analysis.user_feedback = feedback
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Feedback submitted successfully'})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ========================================
    # DOCUMENT UPLOAD & PROCESSING
    # ========================================

    @app.route('/upload')
    @login_required
    def upload_page():
        """Upload page"""
        project_id = request.args.get('project_id')

        try:
            from models import User, Project
            user = User.query.filter_by(username=session['username']).first()
            user_projects = Project.query.filter_by(user_id=user.id).all()

            selected_project = None
            if project_id:
                selected_project = Project.query.filter_by(id=project_id, user_id=user.id).first()

        except Exception as e:
            user_projects = []
            selected_project = None

        return render_template('upload.html',
                             user_projects=user_projects,
                             project_id=project_id,
                             selected_project=selected_project)

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

        return render_template('partners/partner_settings.html', partners=partners)

    @app.route('/settings/partners/add', methods=['GET', 'POST'])
    @login_required
    def add_partner():
        """Add new partner"""
        if request.method == 'GET':
            return render_template('partners/add_partner.html')

        # POST request - handle partner creation
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
            return render_template('partners/add_partner.html')

    @app.route('/settings/partners/<int:partner_id>/products')
    @login_required
    def partner_products(partner_id):
        """Manage products for a specific partner"""
        try:
            from models import Partner
            partner = Partner.query.get_or_404(partner_id)
            return render_template('partners/partner_products.html', partner=partner)
        except Exception as e:
            flash(f"Error loading partner: {e}")
            return redirect('/settings/partners')

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

        if request.method == 'GET':
            return render_template('partners/add_partner_product.html', partner=partner)

        # POST request - handle product creation
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
            return render_template('partners/add_partner_product.html', partner=partner)

    # ========================================
    # ANALYSIS & DOCUMENT VIEWS
    # ========================================

    @app.route('/document/<int:document_id>')
    @login_required
    def document_detail(document_id):
        """Individual document analysis page"""
        try:
            from models import User, Document, Project
            from real_analysis_system import get_real_document_analysis

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
                'extracted_requirements': ai_analysis.get('extracted_requirements', []) if ai_analysis else [],
                'key_terms': ai_analysis.get('key_terms', []) if ai_analysis else [],
                'compliance_items': ai_analysis.get('compliance_items', []) if ai_analysis else [],
            }

            return render_template('document_detail.html',
                                 document=document,
                                 project=project,
                                 doc_analysis=doc_analysis)
        except Exception as e:
            flash(f"Error loading document: {e}")
            return redirect('/projects')

    @app.route('/analysis/<project_id>')
    @login_required
    def analysis_view(project_id):
        """Analysis results page for a project"""
        try:
            from models import User, Project, Document
            from real_analysis_system import get_real_analysis_results

            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            documents = Document.query.filter_by(project_id=project_id).all()
            analysis_results = get_real_analysis_results(project_id)

            return render_template('analysis_view.html',
                                 project=project,
                                 documents=documents,
                                 analysis_results=analysis_results)
        except Exception as e:
            flash(f"Error loading analysis: {e}")
            return redirect('/projects')

    # ========================================
    # PROPOSAL GENERATION
    # ========================================

    @app.route('/generate-proposal/<project_id>')
    @login_required
    def generate_proposal_page(project_id):
        """Proposal generation page with multiple deliverable options"""
        try:
            from models import User, Project, Document
            from real_analysis_system import get_real_analysis_results

            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            documents = Document.query.filter_by(project_id=project_id).all()

            # Get analysis results for the project
            analysis_results = get_real_analysis_results(project_id)

            return render_template('generate_proposal.html',
                                 project=project,
                                 documents=documents,
                                 analysis_results=analysis_results)
        except Exception as e:
            flash(f"Error loading project: {e}")
            return redirect('/projects')

    @app.route('/proposals/<project_id>')
    @login_required
    def view_proposals(project_id):
        """View all generated proposals for a project"""
        try:
            from models import User, Project
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()

            return render_template('view_proposals.html', project=project)
        except Exception as e:
            flash(f'Error loading proposals: {e}')
            return redirect('/projects')

    @app.route('/projects/<project_id>/partner-recommendations')
    @login_required
    def view_partner_recommendations(project_id):
        """View and select partner recommendations for a project"""
        try:
            from models import User, Project, Partner, PartnerProduct
            from real_analysis_system import get_real_analysis_results

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

            return render_template('partner_recommendations.html',
                                 project=project,
                                 analysis_results=analysis_results,
                                 recommendations=recommendations)
        except Exception as e:
            flash(f"Error loading recommendations: {e}")
            return redirect('/projects')

    # ========================================
    # API ENDPOINTS
    # ========================================

    @app.route('/api/projects', methods=['POST'])
    @login_required
    def create_project_api():
        """Create new project API"""
        try:
            data = request.get_json()

            from models import User, Project
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404

            project = Project(
                id=str(uuid.uuid4()),  # Generate UUID if your model uses string IDs
                name=data.get('name'),
                description=data.get('description', ''),
                status='active',
                user_id=user.id
            )
            """project = Project(
                name=data.get('name'),
                description=data.get('description', ''),
                status='active',
                user_id=user.id
            )"""

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
    @login_required
    def upload_file():
        """Handle file upload API - Enhanced with better error handling"""
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

            # Extract text content immediately
            extracted_content = ""
            extraction_error = None
            
            print(f"🔍 Extracting text from {original_filename}...")
            try:
                document_processor = app.config.get('DOCUMENT_PROCESSOR')
                if document_processor:
                    # Use the built-in extraction method with mime type
                    extracted_content = document_processor.extract_text_from_file(file_path, file.content_type)
                    
                    if extracted_content and extracted_content.strip():
                        print(f"✅ Extracted {len(extracted_content)} characters from {original_filename}")
                    else:
                        print(f"⚠️ No content extracted from {original_filename}")
                        extraction_error = "No text content found in document"
                else:
                    print("⚠️ Document processor not available")
                    extraction_error = "Document processor not configured"
                    
            except Exception as e:
                print(f"❌ Text extraction error: {e}")
                extraction_error = f"Text extraction failed: {str(e)}"

            # Create document record
            try:
                document = Document(
                    filename=unique_filename,
                    original_filename=original_filename,
                    file_path=file_path,
                    file_size=saved_size,
                    project_id=project_id,
                    uploaded_by=user.id,
                    uploaded_at=datetime.utcnow(),
                    extracted_content=extracted_content  # Store extracted content immediately
                )

                # Add processing status and other fields if they exist in your model
                if hasattr(document, 'processing_status'):
                    document.processing_status = 'processed' if extracted_content else 'failed'
                if hasattr(document, 'created_at'):
                    document.created_at = datetime.utcnow()
                if hasattr(document, 'error_message') and extraction_error:
                    document.error_message = extraction_error

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

            # Process document synchronously (no background queue needed)
            processing_result = None
            try:
                from sync_processor import process_document_sync
                processing_result = process_document_sync(document)
                
                if processing_result['success']:
                    print(f"✅ Document {document.id} processed successfully")
                else:
                    print(f"⚠️ Document processing had issues: {processing_result.get('message', 'Unknown error')}")

            except Exception as e:
                print(f"❌ Document processing failed: {e}")
                processing_result = {'success': False, 'error': str(e)}
                if hasattr(document, 'processing_status'):
                    document.processing_status = 'failed'
                if hasattr(document, 'error_message'):
                    document.error_message = f"Task start failed: {str(e)}"
                db.session.commit()

            # Include processing results in response
            processing_message = "and processed successfully"
            if processing_result:
                if processing_result['success']:
                    processing_message = f"and processed successfully ({processing_result.get('content_length', 0)} chars extracted)"
                else:
                    processing_message = f"but processing failed: {processing_result.get('error', 'Unknown error')}"
            
            response_data = {
                'success': True,
                'document_id': document.id,
                'filename': original_filename,
                'file_size': saved_size,
                'processing_result': processing_result,
                'extracted_content_length': len(extracted_content) if extracted_content else 0,
                'extraction_success': bool(extracted_content and extracted_content.strip()),
                'extraction_error': extraction_error,
                'message': f'File uploaded {processing_message}'
            }

            print(f"✅ Upload successful: {response_data}")
            return jsonify(response_data)

        except Exception as e:
            print(f"❌ Upload error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'Upload failed: {str(e)}'}), 500

    @app.route('/api/document-status/<int:document_id>')
    @login_required
    def get_document_status(document_id):
        """Get document processing status"""
        try:
            from models import User, Document, Project
            user = User.query.filter_by(username=session['username']).first()

            # Get document and verify ownership through project
            document = Document.query.get_or_404(document_id)
            project = Project.query.filter_by(id=document.project_id, user_id=user.id).first()
            if not project:
                return jsonify({'error': 'Access denied'}), 403

            # In synchronous mode, documents are processed immediately
            # Status is either 'completed', 'failed', or 'processing'
            task_status = None
            if hasattr(document, 'processing_status'):
                task_status = {
                    'state': document.processing_status.upper() if document.processing_status else 'COMPLETED',
                    'info': 'Document processed synchronously'
                }

            return jsonify({
                'document_id': document.id,
                'filename': getattr(document, 'original_filename', None) or document.filename,
                'processing_status': getattr(document, 'processing_status', 'unknown'),
                'error_message': getattr(document, 'error_message', None),
                'processed_at': getattr(document, 'processed_at', None),
                'upload_date': getattr(document, 'uploaded_at', None),
                'task_status': task_status
            })

        except Exception as e:
            print(f"❌ Status check error: {e}")
            return jsonify({'error': f'Status check failed: {str(e)}'}), 500

    @app.route('/api/generate-proposal/<project_id>', methods=['POST'])
    @login_required
    def api_generate_proposal(project_id):
        """API endpoint to generate proposal documents with individual/batch modes"""
        try:
            from models import User, Project, CustomDeliverable
            from real_analysis_system import get_real_analysis_results
            from proposal_generator import ProposalGenerator
            import zipfile
            import tempfile
            
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
            generation_mode = request.args.get('mode', 'standard')

            print(f"📝 Generating proposal for project {project_id}")
            print(f"📋 Deliverables: {deliverables}")
            print(f"📄 Format: {output_format}, Level: {detail_level}, Mode: {generation_mode}")

            # Get analysis results
            analysis_results = get_real_analysis_results(project_id)

            generator = ProposalGenerator(
                project=project,
                analysis_results=analysis_results,
                company_name=company_name,
                contact_person=contact_person
            )

            # Separate standard and custom deliverables
            standard_deliverables = []
            custom_deliverables = []
            
            for deliverable in deliverables:
                if deliverable.startswith('custom_'):
                    custom_id = deliverable.replace('custom_', '')
                    custom_del = CustomDeliverable.query.filter_by(id=custom_id, user_id=user.id).first()
                    if custom_del:
                        custom_deliverables.append(custom_del)
                else:
                    standard_deliverables.append(deliverable)

            # Generate documents
            generated_docs = []

            # Generate standard deliverables
            for deliverable in standard_deliverables:
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

            # Generate custom deliverables
            for custom_del in custom_deliverables:
                try:
                    doc_result = generator.generate_custom_document(
                        custom_deliverable=custom_del,
                        output_format=output_format,
                        detail_level=detail_level
                    )
                    generated_docs.append(doc_result)
                    print(f"✅ Generated custom document: {custom_del.title}")

                except Exception as e:
                    print(f"❌ Failed to generate custom document {custom_del.title}: {e}")
                    continue

            if not generated_docs:
                return jsonify({
                    'success': False,
                    'error': 'No documents were generated successfully'
                }), 500

            # Handle batch mode - create ZIP file
            if generation_mode == 'batch' and len(generated_docs) > 1:
                try:
                    zip_filename = f"proposal_package_{project.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                    zip_path = os.path.join('generated_proposals', zip_filename)
                    
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for doc in generated_docs:
                            if 'filepath' in doc and os.path.exists(doc['filepath']):
                                zipf.write(doc['filepath'], doc['filename'])
                    
                    # Add ZIP file info to response
                    zip_size = os.path.getsize(zip_path)
                    zip_doc = {
                        'title': f'Complete Proposal Package',
                        'description': f'All {len(generated_docs)} deliverables in one package',
                        'format': 'zip',
                        'size': f'{zip_size // 1024} KB',
                        'filename': zip_filename,
                        'download_url': f'/download-proposal/{zip_filename}',
                        'filepath': zip_path
                    }
                    
                    generated_docs.append(zip_doc)
                    print(f"✅ Created batch ZIP: {zip_filename}")
                    
                except Exception as e:
                    print(f"⚠️ Failed to create ZIP file: {e}")

            return jsonify({
                'success': True,
                'documents': generated_docs,
                'generation_mode': generation_mode,
                'message': f'Successfully generated {len(generated_docs) - (1 if generation_mode == "batch" and len(generated_docs) > 1 else 0)} documents'
            })

        except Exception as e:
            print(f"❌ Proposal generation error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/custom-deliverables', methods=['GET'])
    @login_required
    def get_custom_deliverables():
        """Get user's custom deliverables"""
        try:
            from models import User, CustomDeliverable
            
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            deliverables = CustomDeliverable.query.filter_by(user_id=user.id).all()
            
            deliverable_list = []
            for d in deliverables:
                deliverable_list.append({
                    'id': d.id,
                    'title': d.title,
                    'description': d.description,
                    'icon': d.icon,
                    'prompt_template': d.prompt_template,
                    'created_at': d.created_at.isoformat() if d.created_at else None
                })
            
            return jsonify({
                'success': True,
                'deliverables': deliverable_list
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/download-proposal/<filename>')
    @login_required
    def download_proposal(filename):
        """Download generated proposal document"""
        try:
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

    # ========================================
    # UTILITY ROUTES
    # ========================================

    @app.route('/debug-routes')
    def debug_routes():
        """Debug route listing"""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': rule.rule
            })
        return jsonify(routes)

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

    @app.route('/create-admin')
    def force_create_admin():
        """Force create admin user for initial setup"""
        try:
            from models import User

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

    @app.route('/update-database')
    def update_database_route():
        """Force database schema update - useful for Docker deployments"""
        try:
            from models import AIAnalysisResult, init_db
            
            # Force create all tables
            db.create_all()
            
            # Test AI analysis table
            try:
                count = AIAnalysisResult.query.count()
                ai_table_status = f"AI Analysis table working - {count} records"
            except Exception as e:
                # Try to create the table again
                db.create_all()
                count = AIAnalysisResult.query.count()
                ai_table_status = f"AI Analysis table created - {count} records"
            
            # Run full database initialization
            init_db(app)
            
            return jsonify({
                'status': 'Database updated successfully',
                'ai_analysis_table': ai_table_status,
                'timestamp': datetime.now().isoformat(),
                'message': 'All database tables verified and updated'
            })
            
        except Exception as e:
            return jsonify({
                'error': str(e),
                'message': 'Database update failed'
            }), 500

    @app.route('/debug/documents')
    @login_required 
    def debug_documents():
        """Debug route to check document extraction status"""
        try:
            from models import User, Document
            
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Get all documents for debugging
            documents = Document.query.filter_by(uploaded_by=user.id).order_by(Document.uploaded_at.desc()).limit(20).all()
            
            doc_info = []
            for doc in documents:
                doc_info.append({
                    'id': doc.id,
                    'filename': doc.original_filename or doc.filename,
                    'file_size': doc.file_size,
                    'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                    'processing_status': getattr(doc, 'processing_status', 'unknown'),
                    'has_extracted_content': bool(doc.extracted_content and doc.extracted_content.strip()),
                    'extracted_content_length': len(doc.extracted_content) if doc.extracted_content else 0,
                    'extracted_content_preview': doc.extracted_content[:200] + '...' if doc.extracted_content and len(doc.extracted_content) > 200 else doc.extracted_content,
                    'error_message': getattr(doc, 'error_message', None),
                    'project_id': doc.project_id
                })
            
            return jsonify({
                'status': 'success',
                'documents_count': len(documents),
                'documents': doc_info,
                'document_processor_available': app.config.get('DOCUMENT_PROCESSOR') is not None,
                'anthropic_api_configured': bool(os.getenv('ANTHROPIC_API_KEY'))
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/debug/extract-document/<int:document_id>')
    @login_required
    def debug_extract_document(document_id):
        """Debug route to manually extract content from a specific document"""
        try:
            from models import User, Document
            
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Get the document
            document = Document.query.filter_by(id=document_id, uploaded_by=user.id).first()
            if not document:
                return jsonify({'error': 'Document not found'}), 404
            
            # Extract content
            document_processor = app.config.get('DOCUMENT_PROCESSOR')
            if not document_processor:
                return jsonify({'error': 'Document processor not available'}), 500
            
            try:
                # Check if file exists
                if not os.path.exists(document.file_path):
                    return jsonify({'error': f'File not found: {document.file_path}'}), 404
                
                # Extract content using file extension as fallback
                original_filename = document.original_filename or document.filename
                file_extension = original_filename.lower().split('.')[-1]
                
                extracted_content = ""
                if file_extension == 'pdf':
                    extracted_content = document_processor.extract_text_from_pdf(document.file_path)
                elif file_extension in ['docx', 'doc']:
                    extracted_content = document_processor.extract_text_from_docx(document.file_path)
                elif file_extension in ['xlsx', 'xls']:
                    extracted_content = document_processor.extract_text_from_xlsx(document.file_path)
                elif file_extension == 'txt':
                    with open(document.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        extracted_content = f.read()
                else:
                    return jsonify({'error': f'Unsupported file type: {file_extension}'}), 400
                
                # Update the document
                document.extracted_content = extracted_content
                if hasattr(document, 'processing_status'):
                    document.processing_status = 'processed' if extracted_content else 'failed'
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'document_id': document_id,
                    'filename': original_filename,
                    'extracted_length': len(extracted_content) if extracted_content else 0,
                    'extracted_preview': extracted_content[:300] + '...' if extracted_content and len(extracted_content) > 300 else extracted_content,
                    'message': f'Extracted {len(extracted_content)} characters' if extracted_content else 'No content extracted'
                })
                
            except Exception as e:
                return jsonify({'error': f'Extraction failed: {str(e)}'}), 500
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ========================================
    # PAST PROPOSALS MANAGEMENT
    # ========================================

    @app.route('/past-proposals')
    @login_required
    def past_proposals_page():
        """Page for managing past proposals"""
        try:
            from proposal_manager import get_proposal_manager
            
            proposal_manager = get_proposal_manager()
            proposals = proposal_manager.get_all_proposals(limit=50)
            stats = proposal_manager.get_proposal_statistics()
            
            return render_template('past_proposals.html', 
                                 proposals=proposals,
                                 stats=stats)
        except Exception as e:
            flash(f'Error loading past proposals: {e}', 'error')
            return redirect('/')

    @app.route('/api/upload-past-proposal', methods=['POST'])
    @login_required
    def upload_past_proposal():
        """Upload a past proposal for vector storage"""
        try:
            from models import User
            from proposal_manager import get_proposal_manager
            
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # Get metadata from form
            metadata = {
                'title': request.form.get('title', file.filename),
                'client_name': request.form.get('client_name', 'Unknown'),
                'project_type': request.form.get('project_type', 'unknown'),
                'proposal_type': request.form.get('proposal_type', 'technical'),
                'submission_year': int(request.form.get('submission_year', datetime.now().year)),
                'proposal_value': float(request.form.get('proposal_value', 0)) if request.form.get('proposal_value') else None,
                'currency': request.form.get('currency', 'USD'),
                'status': request.form.get('status', 'unknown'),
                'win_probability': float(request.form.get('win_probability', 0)) if request.form.get('win_probability') else None,
                'industry_sector': request.form.get('industry_sector'),
                'project_duration': request.form.get('project_duration'),
                'team_size': int(request.form.get('team_size', 0)) if request.form.get('team_size') else None,
                'technologies_used': request.form.get('technologies_used', '').split(',') if request.form.get('technologies_used') else [],
                'lessons_learned': request.form.get('lessons_learned'),
                'key_success_factors': request.form.get('key_success_factors', '').split(',') if request.form.get('key_success_factors') else [],
                'key_challenges': request.form.get('key_challenges', '').split(',') if request.form.get('key_challenges') else []
            }
            
            # Save file
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"past_{timestamp}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Process with proposal manager
            proposal_manager = get_proposal_manager()
            result = proposal_manager.upload_past_proposal(
                file_path=file_path,
                filename=filename,
                metadata=metadata,
                user_id=user.id
            )
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/past-proposals/search', methods=['POST'])
    @login_required
    def search_past_proposals():
        """Search past proposals by similarity"""
        try:
            from proposal_manager import get_proposal_manager
            
            data = request.get_json()
            query = data.get('query', '')
            limit = data.get('limit', 10)
            filters = data.get('filters', {})
            
            if not query:
                return jsonify({'error': 'Query is required'}), 400
            
            proposal_manager = get_proposal_manager()
            results = proposal_manager.get_proposals_by_similarity(
                query=query,
                limit=limit,
                filters=filters
            )
            
            return jsonify({
                'success': True,
                'results': results,
                'count': len(results)
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/past-proposals/stats')
    @login_required
    def get_proposal_stats():
        """Get statistics about past proposals"""
        try:
            from proposal_manager import get_proposal_manager
            
            proposal_manager = get_proposal_manager()
            stats = proposal_manager.get_proposal_statistics()
            
            return jsonify(stats)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/vector-store/test')
    @login_required
    def test_vector_store():
        """Test vector store functionality"""
        try:
            from vector_store import test_vector_store
            
            success = test_vector_store()
            return jsonify({
                'success': success,
                'message': 'Vector store test completed',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

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
    # AI PROVIDER CONFIGURATION ROUTES
    # ========================================
    
    @app.route('/ai-settings')
    @login_required
    def ai_settings_page():
        """AI provider settings page"""
        return render_template('ai_settings.html')
    
    @app.route('/api/ai/providers')
    @login_required
    def get_ai_providers():
        """Get available AI providers and their status"""
        try:
            from ai_providers import get_ai_manager
            from ai_config import get_ai_config, validate_api_keys, get_available_models
            
            manager = get_ai_manager()
            config = get_ai_config()
            keys_status = validate_api_keys()
            
            return jsonify({
                'success': True,
                'providers': manager.get_provider_status(),
                'config': {
                    'preferred_provider': config['preferred_provider'],
                    'fallback_enabled': config['fallback_enabled'],
                    'current_models': {
                        'claude': config['claude']['model'],
                        'openai': config['openai']['model']
                    }
                },
                'available_models': {
                    'claude': get_available_models('claude'),
                    'openai': get_available_models('openai')
                },
                'api_keys': keys_status
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/ai/providers/switch', methods=['POST'])
    @login_required
    def switch_ai_provider():
        """Switch the preferred AI provider"""
        try:
            from ai_providers import set_preferred_provider
            
            data = request.get_json()
            provider = data.get('provider')
            
            if provider not in ['claude', 'openai']:
                return jsonify({'success': False, 'error': 'Invalid provider'})
            
            set_preferred_provider(provider)
            
            return jsonify({
                'success': True,
                'message': f'Switched to {provider}',
                'provider': provider
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/ai/models/switch', methods=['POST'])
    @login_required  
    def switch_ai_model():
        """Switch the model for a specific provider"""
        try:
            from ai_config import validate_model
            
            data = request.get_json()
            provider = data.get('provider')
            model = data.get('model')
            
            if provider not in ['claude', 'openai']:
                return jsonify({'success': False, 'error': 'Invalid provider'})
            
            if not validate_model(provider, model):
                return jsonify({'success': False, 'error': 'Invalid model for provider'})
            
            # Update environment variable for this session
            env_var = 'CLAUDE_MODEL' if provider == 'claude' else 'OPENAI_MODEL'
            os.environ[env_var] = model
            
            # Update AI manager's configuration
            from ai_providers import get_ai_manager
            manager = get_ai_manager()
            # Force reload configuration
            manager.__init__(manager.preferred_provider)
            
            return jsonify({
                'success': True,
                'message': f'Switched {provider} model to {model}',
                'provider': provider,
                'model': model
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/ai/models', methods=['GET'])
    @login_required  
    def get_ai_models():
        """Get available models for all providers"""
        try:
            from ai_config import get_available_models, get_ai_config
            
            config = get_ai_config()
            
            return jsonify({
                'success': True,
                'models': {
                    'claude': get_available_models('claude'),
                    'openai': get_available_models('openai')
                },
                'current_models': {
                    'claude': config['claude']['model'],
                    'openai': config['openai']['model']
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/ai/test', methods=['POST'])
    @login_required  
    def test_ai_provider():
        """Test AI provider with a simple request"""
        try:
            from ai_providers import get_ai_manager
            
            data = request.get_json()
            provider = data.get('provider')
            
            manager = get_ai_manager()
            
            test_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, this is a test' in exactly those words."}
            ]
            
            result = manager.chat_completion(test_messages, provider=provider, max_tokens=50)
            
            return jsonify({
                'success': result['success'],
                'response': result.get('content', 'No response'),
                'provider_used': result.get('provider'),
                'error': result.get('error')
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    # ========================================
    # AI RESPONSE MANAGEMENT ROUTES
    # ========================================
    
    @app.route('/api/ai/responses/<project_id>')
    @login_required
    def get_ai_responses(project_id):
        """Get all AI responses for a project"""
        try:
            from ai_response_manager import AIResponseManager
            
            request_type = request.args.get('type')
            include_archived = request.args.get('archived', 'false').lower() == 'true'
            limit = int(request.args.get('limit', 50))
            
            responses = AIResponseManager.get_project_responses(
                project_id=project_id,
                request_type=request_type,
                include_archived=include_archived,
                limit=limit
            )
            
            return jsonify({
                'success': True,
                'responses': [r.to_dict() for r in responses],
                'total': len(responses)
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/ai/responses/<project_id>/history')
    @login_required
    def get_ai_response_history(project_id):
        """Get AI response history with family grouping"""
        try:
            from ai_response_manager import AIResponseManager
            
            request_type = request.args.get('type')
            group_families = request.args.get('group', 'true').lower() == 'true'
            
            history = AIResponseManager.get_response_history(
                project_id=project_id,
                request_type=request_type,
                group_by_family=group_families
            )
            
            stats = AIResponseManager.get_response_stats(project_id)
            
            return jsonify({
                'success': True,
                'history': history,
                'stats': stats
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/ai/response/<response_id>')
    @login_required
    def get_ai_response_detail(response_id):
        """Get detailed view of a specific AI response"""
        try:
            from ai_response_manager import AIResponseManager
            
            response = AIResponseManager.get_response_by_id(response_id)
            if not response:
                return jsonify({'success': False, 'error': 'Response not found'}), 404
            
            # Mark as viewed
            response.mark_viewed()
            
            # Get related responses
            children = response.get_child_responses()
            parent = response.get_parent_response()
            
            return jsonify({
                'success': True,
                'response': {
                    **response.to_dict(),
                    'full_response': response.raw_response,
                    'parsed_response': response.parsed_response,
                    'metadata': response.response_metadata,
                    'prompt_used': response.prompt_used[:1000] + '...' if len(response.prompt_used) > 1000 else response.prompt_used,  # Truncate long prompts
                },
                'children': [c.to_dict() for c in children],
                'parent': parent.to_dict() if parent else None
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/ai/response/<response_id>/rerun', methods=['POST'])
    @login_required
    def rerun_ai_response(response_id):
        """Create a rerun of an existing AI response"""
        try:
            from ai_response_manager import AIResponseManager
            
            data = request.get_json() or {}
            reason = data.get('reason', 'Manual rerun')
            
            rerun_response = AIResponseManager.create_rerun(response_id, reason)
            if not rerun_response:
                return jsonify({'success': False, 'error': 'Original response not found'}), 404
            
            # Trigger actual AI rerun based on original response parameters
            original_response = AIResponseManager.get_response_by_id(response_id)
            if not original_response:
                return jsonify({'success': False, 'error': 'Original response not found'}), 404
            
            # Execute rerun in background to avoid timeout
            try:
                from real_analysis_system import RealAnalysisSystem
                from models import Project
                
                project = Project.query.get(original_response.project_id)
                if not project:
                    AIResponseManager.fail_response(rerun_response, "Project not found for rerun")
                    return jsonify({'success': False, 'error': 'Project not found'}), 404
                
                analysis_system = RealAnalysisSystem(project)
                
                # Recreate content from context_data or use fallback
                content = original_response.context_data.get('content', '') if original_response.context_data else ''
                
                # Execute the appropriate analysis method based on request_type
                result = None
                if original_response.request_type == 'clarification_extraction':
                    if content:
                        result = analysis_system.extract_clarification_items(content, project_id=project.id)
                    else:
                        raise Exception("No content available for rerun")
                elif original_response.request_type == 'risk_analysis':
                    if content:
                        result = analysis_system.identify_risks_and_constraints(content, project_id=project.id)
                    else:
                        raise Exception("No content available for rerun")
                elif original_response.request_type == 'deadline_extraction':
                    if content:
                        result = analysis_system.extract_deadlines_and_milestones(content, project_id=project.id)
                    else:
                        raise Exception("No content available for rerun")
                elif original_response.request_type == 'go_no_go_recommendation':
                    # For go/no-go, we need the other analysis results
                    # This is more complex, so for now we'll indicate it needs manual trigger
                    raise Exception("Go/no-go rerun requires manual initiation from analysis page")
                else:
                    raise Exception(f"Unsupported request type for rerun: {original_response.request_type}")
                
                # The AI response will have been stored automatically by the analysis method
                return jsonify({
                    'success': True,
                    'rerun_response_id': rerun_response.response_id,
                    'message': 'Rerun completed successfully',
                    'result_count': len(result) if isinstance(result, list) else 1
                })
                
            except Exception as e:
                # Mark the rerun as failed
                AIResponseManager.fail_response(rerun_response, str(e))
                return jsonify({
                    'success': False, 
                    'error': f'Rerun failed: {str(e)}',
                    'rerun_response_id': rerun_response.response_id
                })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/ai/response/<response_id>/rate', methods=['POST'])
    @login_required
    def rate_ai_response(response_id):
        """Rate an AI response"""
        try:
            from ai_response_manager import AIResponseManager
            
            data = request.get_json()
            rating = data.get('rating')
            feedback = data.get('feedback', '')
            
            if not rating or not (1 <= int(rating) <= 5):
                return jsonify({'success': False, 'error': 'Rating must be between 1 and 5'}), 400
            
            response = AIResponseManager.get_response_by_id(response_id)
            if not response:
                return jsonify({'success': False, 'error': 'Response not found'}), 404
            
            response.rate_response(int(rating), feedback)
            
            return jsonify({
                'success': True,
                'message': 'Response rated successfully'
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/ai/response/<response_id>/favorite', methods=['POST'])
    @login_required
    def toggle_ai_response_favorite(response_id):
        """Toggle favorite status of an AI response"""
        try:
            from ai_response_manager import AIResponseManager
            
            is_favorite = AIResponseManager.toggle_favorite(response_id)
            
            return jsonify({
                'success': True,
                'is_favorite': is_favorite
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/ai-responses/<project_id>')
    @login_required
    def ai_responses_page(project_id):
        """AI responses view page"""
        try:
            from models import Project, User
            
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
            
            return render_template('ai_responses.html', project=project)
        except Exception as e:
            flash(f'Error loading AI responses: {e}')
            return redirect('/projects')

    # =============================================================================
    # ADMIN ROUTES - RFP Types and Workflow Management
    # =============================================================================
    
    @app.route('/admin/rfp-types')
    @login_required
    def admin_rfp_types():
        """RFP Types management page"""
        return render_template('admin/rfp_types.html')
    
    @app.route('/api/admin/rfp-types', methods=['GET'])
    @login_required
    def get_admin_rfp_types():
        """Get all RFP types with statistics"""
        try:
            from models import RFPTypeConfig, Project
            from sqlalchemy import func
            
            # Get all RFP types with project counts
            types = db.session.query(
                RFPTypeConfig,
                func.count(Project.id).label('project_count')
            ).outerjoin(
                Project, RFPTypeConfig.type_name == Project.rfp_type
            ).group_by(RFPTypeConfig.id).all()
            
            rfp_types = []
            for rfp_type, project_count in types:
                type_data = {
                    'id': rfp_type.id,
                    'type_name': rfp_type.type_name,
                    'display_name': rfp_type.display_name,
                    'description': rfp_type.description,
                    'default_workflow_stages': rfp_type.default_workflow_stages or [],
                    'is_active': rfp_type.is_active,
                    'project_count': project_count
                }
                rfp_types.append(type_data)
            
            # Calculate statistics
            total_types = len(rfp_types)
            active_types = sum(1 for t in rfp_types if t['is_active'])
            total_projects_using = sum(t['project_count'] for t in rfp_types)
            
            stats = {
                'total': total_types,
                'active': active_types,
                'projects_using': total_projects_using
            }
            
            return jsonify({
                'success': True,
                'rfp_types': rfp_types,
                'stats': stats
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/admin/rfp-types', methods=['POST'])
    @login_required
    def create_rfp_type():
        """Create a new RFP type"""
        try:
            from models import RFPTypeConfig
            
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['type_name', 'display_name']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'success': False, 'error': f'{field} is required'}), 400
            
            # Check if type_name already exists
            existing = RFPTypeConfig.query.filter_by(type_name=data['type_name']).first()
            if existing:
                return jsonify({'success': False, 'error': 'Type name already exists'}), 400
            
            # Create new RFP type
            rfp_type = RFPTypeConfig(
                type_name=data['type_name'],
                display_name=data['display_name'],
                description=data.get('description', ''),
                default_workflow_stages=data.get('default_workflow_stages', ['created', 'approved']),
                is_active=data.get('is_active', True)
            )
            
            db.session.add(rfp_type)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'RFP type created successfully',
                'rfp_type_id': rfp_type.id
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/admin/rfp-types/<int:type_id>', methods=['PUT'])
    @login_required
    def update_rfp_type(type_id):
        """Update an existing RFP type"""
        try:
            from models import RFPTypeConfig
            
            rfp_type = RFPTypeConfig.query.get(type_id)
            if not rfp_type:
                return jsonify({'success': False, 'error': 'RFP type not found'}), 404
            
            data = request.get_json()
            
            # Update fields
            if 'display_name' in data:
                rfp_type.display_name = data['display_name']
            if 'description' in data:
                rfp_type.description = data['description']
            if 'default_workflow_stages' in data:
                rfp_type.default_workflow_stages = data['default_workflow_stages']
            if 'is_active' in data:
                rfp_type.is_active = data['is_active']
            
            # Don't allow changing type_name after creation to avoid breaking existing projects
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'RFP type updated successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/admin/rfp-types/<int:type_id>', methods=['DELETE'])
    @login_required
    def delete_rfp_type(type_id):
        """Delete an RFP type (only if no projects are using it)"""
        try:
            from models import RFPTypeConfig, Project
            
            rfp_type = RFPTypeConfig.query.get(type_id)
            if not rfp_type:
                return jsonify({'success': False, 'error': 'RFP type not found'}), 404
            
            # Check if any projects are using this type
            project_count = Project.query.filter_by(rfp_type=rfp_type.type_name).count()
            if project_count > 0:
                return jsonify({
                    'success': False, 
                    'error': f'Cannot delete RFP type. {project_count} project(s) are using it.'
                }), 400
            
            db.session.delete(rfp_type)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'RFP type deleted successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    # ========================================
    # CUSTOM DELIVERABLE ADMIN ROUTES  
    # ========================================

    @app.route('/admin/custom-deliverables')
    @login_required
    def admin_custom_deliverables():
        """Custom deliverables management page"""
        from models import User, CustomDeliverable
        
        user = User.query.filter_by(username=session['username']).first()
        deliverables = CustomDeliverable.query.filter_by(user_id=user.id).all()
        
        return render_template('admin/custom_deliverables.html', 
                               user=user,
                               deliverables=deliverables)

    @app.route('/api/admin/custom-deliverables', methods=['POST'])
    @login_required
    def create_custom_deliverable():
        """Create a new custom deliverable"""
        try:
            from models import User, CustomDeliverable
            
            user = User.query.filter_by(username=session['username']).first()
            data = request.get_json()
            
            deliverable = CustomDeliverable(
                title=data.get('title'),
                description=data.get('description'),
                icon=data.get('icon', 'fas fa-file-alt'),
                prompt_template=data.get('prompt_template'),
                user_id=user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(deliverable)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Custom deliverable created successfully',
                'id': deliverable.id
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/api/admin/custom-deliverables/<int:deliverable_id>', methods=['PUT'])
    @login_required
    def update_custom_deliverable(deliverable_id):
        """Update a custom deliverable"""
        try:
            from models import User, CustomDeliverable
            
            user = User.query.filter_by(username=session['username']).first()
            deliverable = CustomDeliverable.query.filter_by(id=deliverable_id, user_id=user.id).first()
            
            if not deliverable:
                return jsonify({'success': False, 'error': 'Deliverable not found'}), 404
            
            data = request.get_json()
            
            # Update fields
            if 'title' in data:
                deliverable.title = data['title']
            if 'description' in data:
                deliverable.description = data['description']
            if 'icon' in data:
                deliverable.icon = data['icon']
            if 'prompt_template' in data:
                deliverable.prompt_template = data['prompt_template']
            
            deliverable.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Custom deliverable updated successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/api/admin/custom-deliverables/<int:deliverable_id>', methods=['DELETE'])
    @login_required
    def delete_custom_deliverable(deliverable_id):
        """Delete a custom deliverable"""
        try:
            from models import User, CustomDeliverable
            
            user = User.query.filter_by(username=session['username']).first()
            deliverable = CustomDeliverable.query.filter_by(id=deliverable_id, user_id=user.id).first()
            
            if not deliverable:
                return jsonify({'success': False, 'error': 'Deliverable not found'}), 404
            
            db.session.delete(deliverable)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Custom deliverable deleted successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/admin/workflows')
    @login_required
    def admin_workflows():
        """Workflows management page"""
        return render_template('admin/workflows.html')

    @app.route('/admin/partners')
    @login_required
    def admin_partners():
        """Partners management page"""
        try:
            from models import Partner
            partners = Partner.query.all()
            return render_template('admin/partners.html', partners=partners)
        except Exception as e:
            flash(f'Error loading partners: {e}')
            return redirect('/projects')

    # =============================================================================
    # PROJECT LIFECYCLE MANAGEMENT - Purge/Restore Functionality
    # =============================================================================
    
    @app.route('/projects/purged')
    @login_required
    def purged_projects():
        """View purged projects"""
        try:
            from models import User, Project
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return redirect('/login')

            # Get only purged projects
            purged_projects = Project.query.filter_by(user_id=user.id, status='purged').order_by(Project.purged_at.desc()).all()
            
            return render_template('projects_purged.html', purged_projects=purged_projects)
        except Exception as e:
            flash(f'Error loading purged projects: {e}')
            return redirect('/projects')

    @app.route('/api/project/<project_id>/purge', methods=['POST'])
    @login_required
    def purge_project(project_id):
        """Purge a project to archive section"""
        try:
            from models import User, Project
            
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401

            project = Project.query.filter_by(id=project_id, user_id=user.id).first()
            if not project:
                return jsonify({'success': False, 'error': 'Project not found'}), 404
            
            if project.status == 'purged':
                return jsonify({'success': False, 'error': 'Project is already purged'}), 400

            data = request.get_json() or {}
            reason = data.get('reason', 'Project lifecycle completed')
            
            # Purge the project
            project.purge(user.id, reason)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Project "{project.name}" has been purged',
                'project_id': project_id,
                'purged_at': project.purged_at.isoformat()
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/api/project/<project_id>/restore', methods=['POST'])
    @login_required
    def restore_project(project_id):
        """Restore a project from purged state"""
        try:
            from models import User, Project
            
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401

            project = Project.query.filter_by(id=project_id, user_id=user.id).first()
            if not project:
                return jsonify({'success': False, 'error': 'Project not found'}), 404
            
            if project.status != 'purged':
                return jsonify({'success': False, 'error': 'Project is not purged'}), 400
            
            # Restore the project
            project.restore_from_purge()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Project "{project.name}" has been restored',
                'project_id': project_id
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/api/project/<project_id>/delete-permanently', methods=['DELETE'])
    @login_required
    def delete_project_permanently(project_id):
        """Permanently delete a purged project"""
        try:
            from models import User, Project
            
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401

            project = Project.query.filter_by(id=project_id, user_id=user.id).first()
            if not project:
                return jsonify({'success': False, 'error': 'Project not found'}), 404
            
            if project.status != 'purged':
                return jsonify({'success': False, 'error': 'Only purged projects can be permanently deleted'}), 400
            
            project_name = project.name
            
            # Permanently delete the project (cascade will handle related records)
            db.session.delete(project)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Project "{project_name}" has been permanently deleted',
                'project_id': project_id
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    # ========================================
    # ASSUMPTIONS ANALYSIS API ENDPOINTS
    # ========================================

    @app.route('/api/project/<project_id>/assumptions-analysis', methods=['POST'])
    @login_required
    def trigger_assumptions_analysis(project_id):
        """Trigger assumptions analysis for a project"""
        try:
            from enhanced_orchestrator import get_enhanced_orchestrator
            
            # Get analysis type from request
            data = request.get_json() or {}
            analysis_type = data.get('analysis_type', 'full')  # 'full', 'assumptions_only', 'recommendations_only'
            
            # Validate project exists and user has access
            from models import User, Project
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401

            project = Project.query.filter_by(id=project_id, user_id=user.id).first()
            if not project:
                return jsonify({'success': False, 'error': 'Project not found or access denied'}), 404
            
            # Trigger assumptions analysis
            orchestrator = get_enhanced_orchestrator()
            task_id = orchestrator.trigger_assumptions_analysis(int(project_id), analysis_type)
            
            return jsonify({
                'success': True,
                'message': f'Assumptions analysis started for project {project_id}',
                'task_id': task_id,
                'analysis_type': analysis_type,
                'project_id': project_id
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/project/<project_id>/assumptions-analysis/results')
    @login_required
    def get_assumptions_analysis_results(project_id):
        """Get assumptions analysis results for a project"""
        try:
            from models import User, AssumptionAnalysis
            
            # Validate project access
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401

            project = Project.query.filter_by(id=project_id, user_id=user.id).first()
            if not project:
                return jsonify({'success': False, 'error': 'Project not found or access denied'}), 404
            
            # Get latest analysis results
            latest_analysis = AssumptionAnalysis.query.filter_by(
                project_id=project_id
            ).order_by(AssumptionAnalysis.generated_at.desc()).first()
            
            if not latest_analysis:
                return jsonify({
                    'success': False,
                    'error': 'No assumptions analysis found for this project'
                }), 404
            
            # Mark as viewed
            latest_analysis.mark_viewed()
            db.session.commit()
            
            # Get related assumptions and recommendations
            assumptions = [assumption.to_dict() for assumption in latest_analysis.assumptions]
            recommendations = [rec.to_dict() for rec in latest_analysis.recommendations]
            
            return jsonify({
                'success': True,
                'analysis': latest_analysis.to_dict(),
                'raw_analysis': latest_analysis.raw_analysis,
                'assumptions': assumptions,
                'recommendations': recommendations,
                'summary': {
                    'total_assumptions': len(assumptions),
                    'total_recommendations': len(recommendations),
                    'high_impact_assumptions': len([a for a in assumptions if a.get('impact_level') == 'high']),
                    'high_priority_recommendations': len([r for r in recommendations if r.get('priority_level') == 'high'])
                }
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/assumptions/<assumption_id>/update', methods=['PUT'])
    @login_required
    def update_assumption(assumption_id):
        """Update an assumption (validation status, user notes, etc.)"""
        try:
            from models import ProjectAssumption
            
            assumption = ProjectAssumption.query.get(assumption_id)
            if not assumption:
                return jsonify({'success': False, 'error': 'Assumption not found'}), 404
            
            # Validate user has access to project
            from models import User
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=assumption.project_id, user_id=user.id).first()
            if not project:
                return jsonify({'success': False, 'error': 'Access denied'}), 403
            
            data = request.get_json()
            
            # Update allowed fields
            if 'validation_status' in data:
                assumption.validation_status = data['validation_status']
            if 'validation_notes' in data:
                assumption.validation_notes = data['validation_notes']
            if 'user_notes' in data:
                assumption.user_notes = data['user_notes']
            if 'user_priority' in data:
                assumption.user_priority = data['user_priority']
            if 'status' in data:
                assumption.status = data['status']
                if data['status'] == 'resolved':
                    assumption.resolved_at = datetime.utcnow()
                    assumption.resolved_by = user.id
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Assumption updated successfully',
                'assumption': assumption.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/recommendations/<recommendation_id>/update', methods=['PUT'])
    @login_required
    def update_recommendation(recommendation_id):
        """Update a recommendation (decision, status, etc.)"""
        try:
            from models import AIRecommendation
            
            recommendation = AIRecommendation.query.get(recommendation_id)
            if not recommendation:
                return jsonify({'success': False, 'error': 'Recommendation not found'}), 404
            
            # Validate user has access to project
            from models import User
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=recommendation.project_id, user_id=user.id).first()
            if not project:
                return jsonify({'success': False, 'error': 'Access denied'}), 403
            
            data = request.get_json()
            
            # Update allowed fields
            if 'status' in data:
                recommendation.status = data['status']
                if data['status'] in ['accepted', 'rejected']:
                    recommendation.decision_maker = user.id
                    recommendation.decision_date = datetime.utcnow()
            if 'decision_notes' in data:
                recommendation.decision_notes = data['decision_notes']
            if 'implementation_status' in data:
                recommendation.implementation_status = data['implementation_status']
                if data['implementation_status'] == 'completed':
                    recommendation.completion_date = datetime.utcnow()
            if 'implementation_notes' in data:
                recommendation.implementation_notes = data['implementation_notes']
            if 'user_rating' in data:
                recommendation.user_rating = data['user_rating']
            if 'user_feedback' in data:
                recommendation.user_feedback = data['user_feedback']
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Recommendation updated successfully',
                'recommendation': recommendation.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/task/<task_id>/status')
    @login_required
    def get_analysis_task_status(task_id):
        """Get status of an analysis task"""
        try:
            from enhanced_orchestrator import get_enhanced_orchestrator
            
            orchestrator = get_enhanced_orchestrator()
            status = orchestrator.get_analysis_status(task_id)
            
            return jsonify(status)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/assumptions')
    @login_required
    def assumptions_page():
        """Page for viewing project assumptions analysis"""
        try:
            # Get project_id from query params
            project_id = request.args.get('project_id')
            if not project_id:
                flash('Project ID is required', 'error')
                return redirect('/projects')
            
            # Validate project access
            from models import User
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first()
            if not project:
                flash('Project not found or access denied', 'error')
                return redirect('/projects')
            
            return render_template('assumptions_analysis.html', 
                                 project=project,
                                 project_id=project_id)
                                 
        except Exception as e:
            flash(f'Error loading assumptions page: {e}', 'error')
            return redirect('/projects')

    # ========================================
    # PROPOSAL TEMPLATE MANAGEMENT API ENDPOINTS
    # ========================================

    @app.route('/api/templates/upload', methods=['POST'])
    @login_required
    def upload_proposal_template():
        """Upload a DOCX/PPTX proposal template"""
        try:
            from template_processor import get_template_processor
            from models import User
            
            # Validate user
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            # Check file upload
            if 'template_file' not in request.files:
                return jsonify({'success': False, 'error': 'No file uploaded'}), 400
            
            file = request.files['template_file']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'No file selected'}), 400
            
            # Validate file type
            allowed_extensions = {'.docx', '.pptx'}
            file_extension = os.path.splitext(file.filename.lower())[1]
            if file_extension not in allowed_extensions:
                return jsonify({
                    'success': False, 
                    'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
                }), 400
            
            # Get template metadata
            template_info = {
                'name': request.form.get('name', file.filename),
                'description': request.form.get('description', ''),
                'category': request.form.get('category', 'general'),
                'is_default': request.form.get('is_default', 'false').lower() == 'true'
            }
            
            # Save uploaded file
            upload_dir = os.path.join('uploads', 'templates')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"{timestamp}_{file.filename}"
            file_path = os.path.join(upload_dir, safe_filename)
            file.save(file_path)
            
            # Process template
            template_processor = get_template_processor()
            result = template_processor.process_template_upload(
                file_path=file_path,
                original_filename=file.filename,
                template_info=template_info,
                user_id=user.id
            )
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'template_id': result['template_id'],
                    'bookmarks_found': result['bookmarks_found'],
                    'bookmarks': result['bookmarks']
                })
            else:
                # Clean up file if processing failed
                if os.path.exists(file_path):
                    os.remove(file_path)
                return jsonify({
                    'success': False,
                    'error': result['error']
                }), 400
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/templates')
    @login_required
    def get_proposal_templates():
        """Get all available proposal templates"""
        try:
            from models import ProposalTemplate
            
            category = request.args.get('category')
            template_type = request.args.get('type')  # 'docx', 'pptx'
            
            query = ProposalTemplate.query.filter_by(is_active=True)
            
            if category:
                query = query.filter_by(category=category)
            if template_type:
                query = query.filter_by(template_type=template_type)
            
            templates = query.order_by(ProposalTemplate.usage_count.desc()).all()
            
            return jsonify({
                'success': True,
                'templates': [template.to_dict() for template in templates],
                'count': len(templates)
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/templates/<template_id>')
    @login_required
    def get_template_details(template_id):
        """Get detailed information about a specific template"""
        try:
            from models import ProposalTemplate, TemplateBookmark
            
            template = ProposalTemplate.query.filter_by(template_id=template_id).first()
            if not template:
                return jsonify({'success': False, 'error': 'Template not found'}), 404
            
            bookmarks = TemplateBookmark.query.filter_by(template_id=template.id).all()
            
            return jsonify({
                'success': True,
                'template': template.to_dict(),
                'bookmarks': [bookmark.to_dict() for bookmark in bookmarks]
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/templates/<template_id>/bookmarks/<bookmark_id>', methods=['PUT'])
    @login_required
    def update_template_bookmark(template_id, bookmark_id):
        """Update template bookmark configuration"""
        try:
            from models import TemplateBookmark
            
            bookmark = TemplateBookmark.query.filter_by(bookmark_id=bookmark_id).first()
            if not bookmark:
                return jsonify({'success': False, 'error': 'Bookmark not found'}), 404
            
            data = request.get_json()
            
            # Update allowed fields
            if 'display_name' in data:
                bookmark.display_name = data['display_name']
            if 'description' in data:
                bookmark.description = data['description']
            if 'content_type' in data:
                bookmark.content_type = data['content_type']
            if 'content_source' in data:
                bookmark.content_source = data['content_source']
            if 'default_content' in data:
                bookmark.default_content = data['default_content']
            if 'ai_prompt_template' in data:
                bookmark.ai_prompt_template = data['ai_prompt_template']
            if 'is_required' in data:
                bookmark.is_required = data['is_required']
            if 'max_length' in data:
                bookmark.max_length = data['max_length']
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Bookmark updated successfully',
                'bookmark': bookmark.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/project/<project_id>/proposal/generate', methods=['POST'])
    @login_required
    def generate_project_proposal():
        """Generate proposal for project using template or AI-only"""
        try:
            from enhanced_proposal_generator import create_enhanced_proposal_generator
            from models import User
            
            # Validate user and project
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401

            project = Project.query.filter_by(id=project_id, user_id=user.id).first()
            if not project:
                return jsonify({'success': False, 'error': 'Project not found or access denied'}), 404
            
            data = request.get_json() or {}
            
            # Extract generation parameters
            deliverable_type = data.get('deliverable_type', 'technical')
            template_id = data.get('template_id')  # None for AI-only generation
            output_format = data.get('output_format', 'docx')
            detail_level = data.get('detail_level', 'standard')
            custom_content = data.get('custom_content', {})
            
            # Company information
            company_info = data.get('company_info', {
                'name': data.get('company_name', 'Your Company'),
                'contact_person': data.get('contact_person', 'Project Manager'),
                'address': data.get('company_address', ''),
                'phone': data.get('company_phone', ''),
                'email': data.get('company_email', ''),
                'website': data.get('company_website', '')
            })
            
            # Create enhanced proposal generator
            generator = create_enhanced_proposal_generator(
                project=project,
                company_name=company_info.get('name', 'Your Company'),
                contact_person=company_info.get('contact_person', 'Project Manager')
            )
            
            # Update company information
            generator.update_company_info(company_info)
            
            # Generate proposal
            if template_id:
                # Template-based generation
                result = generator.generate_with_template(
                    template_id=int(template_id),
                    deliverable_type=deliverable_type,
                    custom_content=custom_content,
                    detail_level=detail_level
                )
            else:
                # AI-only generation
                result = generator.generate_without_template(
                    deliverable_type=deliverable_type,
                    output_format=output_format,
                    detail_level=detail_level
                )
            
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Proposal generated successfully',
                    **result
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Generation failed')
                }), 500
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/project/<project_id>/proposal/package', methods=['POST'])
    @login_required
    def generate_proposal_package():
        """Generate multiple proposal documents as a package"""
        try:
            from enhanced_proposal_generator import create_enhanced_proposal_generator
            from models import User
            
            # Validate user and project
            user = User.query.filter_by(username=session['username']).first()
            project = Project.query.filter_by(id=project_id, user_id=user.id).first()
            if not project:
                return jsonify({'success': False, 'error': 'Project not found'}), 404
            
            data = request.get_json() or {}
            
            # Extract parameters
            deliverable_types = data.get('deliverable_types', ['technical', 'commercial'])
            template_preferences = data.get('template_preferences', {})
            output_format = data.get('output_format', 'docx')
            detail_level = data.get('detail_level', 'standard')
            company_info = data.get('company_info', {})
            
            # Create generator
            generator = create_enhanced_proposal_generator(project=project)
            if company_info:
                generator.update_company_info(company_info)
            
            # Generate package
            result = generator.generate_proposal_package(
                deliverable_types=deliverable_types,
                template_preferences=template_preferences,
                output_format=output_format,
                detail_level=detail_level
            )
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/proposal-templates')
    @login_required
    def proposal_templates_page():
        """Template management page"""
        try:
            return render_template('proposal_templates.html')
        except Exception as e:
            flash(f'Error loading templates page: {e}', 'error')
            return redirect('/')

    @app.route('/api/templates/<template_id>/delete', methods=['DELETE'])
    @login_required
    def delete_proposal_template(template_id):
        """Delete a proposal template"""
        try:
            from models import ProposalTemplate, User
            
            user = User.query.filter_by(username=session['username']).first()
            template = ProposalTemplate.query.filter_by(template_id=template_id).first()
            
            if not template:
                return jsonify({'success': False, 'error': 'Template not found'}), 404
            
            # Check if user has permission (owner or admin)
            if template.uploaded_by != user.id and user.role != 'admin':
                return jsonify({'success': False, 'error': 'Access denied'}), 403
            
            # Delete file
            if os.path.exists(template.file_path):
                os.remove(template.file_path)
            
            # Delete from database (cascade will handle bookmarks)
            db.session.delete(template)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Template deleted successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    return app

# Create application instance (simplified - no background task queue)
app = create_app()
print("✅ ITSS RFPplus started without background task queue (simplified deployment)")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'

    print("\n" + "="*60)
    print("🚀 TENDER ANALYSIS SYSTEM - PURE PYTHON VERSION")
    print("="*60)
    print(f"📊 Dashboard: http://localhost:{port}")
    print(f"🔐 Login: admin / admin123")
    print(f"🔍 Health Check: http://localhost:{port}/health")
    print(f"🔧 Debug Mode: {'ON' if debug else 'OFF'}")
    print(f"💾 Database: {os.getenv('DATABASE_URL', 'Local PostgreSQL')}")
    print(f"🔴 Redis: {os.getenv('REDIS_URL', 'Local Redis')}")
    print(f"🤖 AI Processing: {'ENABLED' if os.getenv('ANTHROPIC_API_KEY') or os.getenv('OPENAI_API_KEY') else 'DISABLED'}")
    print("="*60)

    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)
