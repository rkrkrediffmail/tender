# models.py - Complete Implementation
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON, Text, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(db.Model):
    """User management and authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    role = db.Column(db.String(50), default='user')  # admin, manager, user
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    projects = db.relationship('Project', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Project(db.Model):
    """Tender/RFP projects"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    rfp_title = db.Column(db.String(500))
    client_name = db.Column(db.String(255))
    submission_deadline = db.Column(db.DateTime)
    estimated_value = db.Column(db.Float)
    currency = db.Column(db.String(10), default='USD')
    status = db.Column(db.String(50), default='active')  # active, completed, cancelled, submitted
    priority = db.Column(db.String(20), default='medium')  # high, medium, low
    completion_percentage = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = db.relationship('Document', backref='project', lazy=True, cascade='all, delete-orphan')
    requirements = db.relationship('Requirement', backref='project', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('AgentTask', backref='project', lazy=True, cascade='all, delete-orphan')

class Agent(db.Model):
    """AI Agents in the system"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    agent_type = db.Column(db.String(100), nullable=False)  # orchestrator, analysis, solution, delivery
    description = db.Column(db.Text)
    model_name = db.Column(db.String(100))  # claude-sonnet-4, gpt-4, etc.
    status = db.Column(db.String(50), default='offline')  # online, offline, busy, error
    specialties = db.Column(JSON)  # List of specialties
    performance_metrics = db.Column(JSON)  # Performance data
    configuration = db.Column(JSON)  # Agent-specific config
    system_prompt = db.Column(db.Text)  # AI system prompt
    max_tokens = db.Column(db.Integer, default=4000)
    temperature = db.Column(db.Float, default=0.3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tasks = db.relationship('AgentTask', backref='agent', lazy=True)
    sent_messages = db.relationship('AgentMessage', foreign_keys='AgentMessage.agent_id', backref='sender', lazy=True)

class Document(db.Model):
    """Uploaded tender documents"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    file_hash = db.Column(db.String(64))  # SHA-256 hash
    document_type = db.Column(db.String(100))  # rfp, technical_spec, legal, financial
    processing_status = db.Column(db.String(50), default='uploaded')  # uploaded, processing, completed, failed
    extracted_text = db.Column(db.Text)
    extracted_metadata = db.Column(JSON)
    page_count = db.Column(db.Integer)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    requirements = db.relationship('Requirement', backref='source_document', lazy=True)

class Requirement(db.Model):
    """Extracted requirements from documents"""
    id = db.Column(db.Integer, primary_key=True)
    requirement_id = db.Column(db.String(50), nullable=False)  # REQ-001, etc.
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirement_type = db.Column(db.String(50))  # functional, non_functional, business, technical
    priority = db.Column(db.String(20))  # must_have, should_have, could_have, wont_have
    complexity = db.Column(db.String(20))  # low, medium, high
    estimated_effort = db.Column(db.Integer)  # in hours
    source_document_id = db.Column(db.Integer, db.ForeignKey('document.id'))
    source_page = db.Column(db.String(20))
    status = db.Column(db.String(50), default='identified')  # identified, analyzed, designed, implemented
    conflicts_with = db.Column(JSON)  # List of conflicting requirement IDs
    dependencies = db.Column(JSON)  # List of dependent requirement IDs
    acceptance_criteria = db.Column(JSON)  # List of acceptance criteria
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AgentTask(db.Model):
    """Tasks assigned to agents"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    task_type = db.Column(db.String(100), nullable=False)  # document_analysis, requirement_extraction, etc.
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')  # pending, in_progress, completed, failed, cancelled
    priority = db.Column(db.String(20), default='medium')  # high, medium, low
    progress_percentage = db.Column(db.Integer, default=0)
    input_data = db.Column(JSON)  # Task input parameters
    output_data = db.Column(JSON)  # Task results
    error_message = db.Column(db.Text)
    estimated_duration = db.Column(db.Integer)  # in minutes
    actual_duration = db.Column(db.Integer)  # in minutes
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    parent_task_id = db.Column(db.Integer, db.ForeignKey('agent_task.id'))  # For subtasks
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subtasks = db.relationship('AgentTask', remote_side=[id], backref='parent_task')

class AgentMessage(db.Model):
    """Inter-agent communication"""
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'), nullable=False)
    recipient_agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'))  # None for broadcast
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    conversation_id = db.Column(db.String(100))  # For grouping related messages
    message_type = db.Column(db.String(50), nullable=False)  # REQUEST, RESPONSE, NOTIFICATION, QUERY
    priority = db.Column(db.String(20), default='medium')  # high, medium, low
    subject = db.Column(db.String(500))
    content = db.Column(db.Text, nullable=False)
    payload = db.Column(JSON)  # Additional structured data
    response_to_id = db.Column(db.Integer, db.ForeignKey('agent_message.id'))  # For threading
    status = db.Column(db.String(50), default='sent')  # sent, delivered, read, processed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    processed_at = db.Column(db.DateTime)

    # Relationships
    recipient = db.relationship('Agent', foreign_keys=[recipient_agent_id])
    response_to = db.relationship('AgentMessage', remote_side=[id], backref='responses')

class Proposal(db.Model):
    """Generated proposals"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    version = db.Column(db.String(20), nullable=False)  # 1.0, 1.1, 2.0
    title = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(50), default='draft')  # draft, review, approved, submitted
    content_sections = db.Column(JSON)  # Structured proposal content
    generated_content = db.Column(db.Text)  # Full generated text
    executive_summary = db.Column(db.Text)
    technical_approach = db.Column(db.Text)
    project_timeline = db.Column(JSON)
    cost_breakdown = db.Column(JSON)
    team_composition = db.Column(JSON)
    risk_assessment = db.Column(JSON)
    file_path = db.Column(db.String(500))  # Path to generated PDF/Word file
    word_count = db.Column(db.Integer)
    confidence_score = db.Column(db.Float)  # AI confidence in proposal quality
    created_by_agent = db.Column(db.Integer, db.ForeignKey('agent.id'))
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = db.relationship('Project', backref='proposals')

class SystemLog(db.Model):
    """System logs and audit trail"""
    id = db.Column(db.Integer, primary_key=True)
    log_level = db.Column(db.String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    component = db.Column(db.String(100), nullable=False)  # agent_name, system, api, etc.
    event_type = db.Column(db.String(100), nullable=False)  # task_started, document_processed, error_occurred
    message = db.Column(db.Text, nullable=False)
    details = db.Column(JSON)  # Additional structured data
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'))
    task_id = db.Column(db.String(100))  # Reference to AgentTask
    ip_address = db.Column(db.String(45))  # Support IPv6
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='logs')
    agent = db.relationship('Agent', backref='logs')
