# models/post_analysis_models.py
from datetime import datetime
from models import db

class ClarificationItem(db.Model):
    """Items that need clarification from RFP documents"""
    __tablename__ = 'clarification_items'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(255), db.ForeignKey('projects.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # UNCLEAR_REQUIREMENTS, MISSING_INFO, etc.
    description = db.Column(db.Text, nullable=False)
    impact_level = db.Column(db.String(20), nullable=False)  # High, Medium, Low
    suggested_questions = db.Column(db.JSON, default=[])
    status = db.Column(db.String(20), default='pending')  # pending, clarified, not_needed
    clarification_received = db.Column(db.Text)
    clarified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to project
    project = db.relationship('Project', backref='clarification_items')

    def __repr__(self):
        return f'<ClarificationItem {self.category}: {self.description[:50]}>'

class RiskAssessment(db.Model):
    """Risk analysis for tender acceptance"""
    __tablename__ = 'risk_assessments'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(255), db.ForeignKey('projects.id'), nullable=False)
    risk_type = db.Column(db.String(100), nullable=False)  # GUARANTEE, PRE_CONDITION, CASHFLOW, etc.
    description = db.Column(db.Text, nullable=False)
    cashflow_impact = db.Column(db.String(20))  # Positive, Negative, Neutral
    severity_level = db.Column(db.String(20), nullable=False)  # High, Medium, Low
    mitigation_strategy = db.Column(db.Text)
    financial_impact = db.Column(db.String(100))  # Estimated cost or impact
    probability = db.Column(db.String(20))  # High, Medium, Low
    status = db.Column(db.String(20), default='identified')  # identified, mitigated, accepted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to project
    project = db.relationship('Project', backref='risk_assessments')

    def __repr__(self):
        return f'<RiskAssessment {self.risk_type}: {self.severity_level}>'

class ProjectDeadline(db.Model):
    """Deadlines, milestones, penalties, and guarantees"""
    __tablename__ = 'project_deadlines'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(255), db.ForeignKey('projects.id'), nullable=False)
    deadline_type = db.Column(db.String(50), nullable=False)  # SUBMISSION, MILESTONE, PENALTY, GUARANTEE, BID_BOND
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.DateTime)
    due_date_text = db.Column(db.String(200))  # When exact date isn't parseable
    penalty_amount = db.Column(db.String(100))
    penalty_description = db.Column(db.Text)
    critical_level = db.Column(db.String(20), nullable=False)  # Critical, Important, Standard
    status = db.Column(db.String(20), default='active')  # active, completed, missed
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to project
    project = db.relationship('Project', backref='project_deadlines')

    def __repr__(self):
        return f'<ProjectDeadline {self.deadline_type}: {self.title}>'

class GoNoGoAnalysis(db.Model):
    """Overall go/no-go recommendation"""
    __tablename__ = 'go_no_go_analysis'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(255), db.ForeignKey('projects.id'), nullable=False, unique=True)
    recommendation = db.Column(db.String(20), nullable=False)  # GO, NO_GO, CONDITIONAL
    confidence_score = db.Column(db.Integer)  # 1-100
    reasoning = db.Column(db.Text)
    key_concerns = db.Column(db.JSON, default=[])
    success_factors = db.Column(db.JSON, default=[])
    conditions_for_go = db.Column(db.JSON, default=[])
    financial_viability = db.Column(db.String(20))  # High, Medium, Low
    technical_feasibility = db.Column(db.String(20))  # High, Medium, Low
    risk_tolerance = db.Column(db.String(20))  # Acceptable, Moderate, High
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to project
    project = db.relationship('Project', backref='go_no_go_analysis', uselist=False)

    def __repr__(self):
        return f'<GoNoGoAnalysis {self.recommendation}: {self.confidence_score}%>'