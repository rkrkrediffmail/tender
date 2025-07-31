from datetime import datetime
from app import db
from sqlalchemy import JSON


class Project(db.Model):
    """Main project/tender entity"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='active')  # active, completed, paused
    client_name = db.Column(db.String(255))
    submission_deadline = db.Column(db.DateTime)
    estimated_value = db.Column(db.Numeric(15, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = db.relationship('Document', backref='project', lazy=True, cascade='all, delete-orphan')
    requirements = db.relationship('Requirement', backref='project', lazy=True, cascade='all, delete-orphan')
    agent_tasks = db.relationship('AgentTask', backref='project', lazy=True, cascade='all, delete-orphan')
    proposals = db.relationship('Proposal', backref='project', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Project {self.name}>'


class Document(db.Model):
    """Uploaded tender documents"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(50))
    upload_status = db.Column(db.String(50), default='uploaded')  # uploaded, processing, analyzed, error
    analysis_status = db.Column(db.String(50), default='pending')  # pending, in_progress, completed, failed
    extracted_text = db.Column(db.Text)
    document_metadata = db.Column(JSON)  # Store extracted metadata as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Document {self.original_filename}>'


class Agent(db.Model):
    """AI Agent definitions and status"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    agent_type = db.Column(db.String(50), nullable=False)  # analysis, solution, delivery, orchestrator
    description = db.Column(db.Text)
    model_name = db.Column(db.String(100))  # claude-sonnet-4, o1-reasoning, etc.
    status = db.Column(db.String(50), default='online')  # online, offline, processing, error
    specialties = db.Column(JSON)  # List of specialties
    performance_metrics = db.Column(JSON)  # Store performance data
    config = db.Column(JSON)  # Agent-specific configuration
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tasks = db.relationship('AgentTask', backref='agent', lazy=True)
    sent_messages = db.relationship('AgentMessage', foreign_keys='AgentMessage.agent_id', backref='sender_agent', lazy=True)
    received_messages = db.relationship('AgentMessage', foreign_keys='AgentMessage.recipient_agent_id', backref='recipient_agent', lazy=True)

    def __repr__(self):
        return f'<Agent {self.name}>'


class AgentTask(db.Model):
    """Tasks assigned to agents"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'), nullable=False)
    task_type = db.Column(db.String(100), nullable=False)  # document_analysis, risk_assessment, etc.
    priority = db.Column(db.String(20), default='medium')  # high, medium, low
    status = db.Column(db.String(50), default='pending')  # pending, in_progress, completed, failed
    input_data = db.Column(JSON)  # Task input parameters
    output_data = db.Column(JSON)  # Task results
    progress_percentage = db.Column(db.Integer, default=0)
    estimated_duration = db.Column(db.Integer)  # in minutes
    actual_duration = db.Column(db.Integer)  # in minutes
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AgentTask {self.task_type} - {self.status}>'


class Requirement(db.Model):
    """Extracted and analyzed requirements"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    requirement_id = db.Column(db.String(50))  # REQ-001, REQ-002, etc.
    title = db.Column(db.String(255), nullable=False)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    source_document = db.relationship('Document', backref='extracted_requirements')

    def __repr__(self):
        return f'<Requirement {self.requirement_id}: {self.title}>'


class AgentMessage(db.Model):
    """Inter-agent communication messages"""
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'), nullable=False)
    recipient_agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'))  # None for broadcast
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    message_type = db.Column(db.String(50), nullable=False)  # REQUEST, RESPONSE, NOTIFICATION, QUERY
    priority = db.Column(db.String(20), default='medium')  # high, medium, low
    subject = db.Column(db.String(255))
    content = db.Column(db.Text, nullable=False)
    payload = db.Column(JSON)  # Additional structured data
    conversation_id = db.Column(db.String(100))  # For grouping related messages
    response_to_id = db.Column(db.Integer, db.ForeignKey('agent_message.id'))  # For threading
    status = db.Column(db.String(50), default='sent')  # sent, delivered, read, processed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    processed_at = db.Column(db.DateTime)

    # Relationships  
    response_to = db.relationship('AgentMessage', remote_side=[id], backref='responses')

    def __repr__(self):
        return f'<AgentMessage {self.message_type}: {self.subject}>'


class Proposal(db.Model):
    """Generated proposals"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    version = db.Column(db.String(20), default='1.0')
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default='draft')  # draft, review, final, submitted
    content = db.Column(db.Text)  # Main proposal content
    executive_summary = db.Column(db.Text)
    technical_approach = db.Column(db.Text)
    project_timeline = db.Column(JSON)  # Timeline data
    cost_breakdown = db.Column(JSON)  # Cost analysis
    risk_assessment = db.Column(JSON)  # Risk analysis
    quality_score = db.Column(db.Float)  # Overall quality score (0-100)
    proposal_metadata = db.Column(JSON)  # Additional proposal metadata
    file_path = db.Column(db.String(500))  # Generated document path
    created_by_agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    created_by_agent = db.relationship('Agent', backref='proposals')

    def __repr__(self):
        return f'<Proposal {self.title} v{self.version}>'


class SystemLog(db.Model):
    """System activity and audit logs"""
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), nullable=False)  # INFO, WARNING, ERROR, DEBUG
    source = db.Column(db.String(100))  # agent name, system component, etc.
    event_type = db.Column(db.String(100))  # task_started, document_uploaded, etc.
    message = db.Column(db.Text, nullable=False)
    log_details = db.Column(JSON)  # Additional structured log data
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'))
    user_id = db.Column(db.String(100))  # For future user management
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SystemLog {self.level}: {self.event_type}>'


class ProjectMetrics(db.Model):
    """Project performance and analytics"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Float)
    metric_unit = db.Column(db.String(50))
    measurement_date = db.Column(db.DateTime, default=datetime.utcnow)
    metric_metadata = db.Column(JSON)  # Additional metric context

    def __repr__(self):
        return f'<ProjectMetrics {self.metric_name}: {self.metric_value}>'