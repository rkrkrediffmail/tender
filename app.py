import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Configure the database
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is not set")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

@app.route('/')
def dashboard():
    """Main dashboard with agent ecosystem overview"""
    # Get real data from database
    agents = db.session.query(Agent).all()
    projects = db.session.query(Project).filter_by(status='active').all()
    recent_tasks = db.session.query(AgentTask).order_by(AgentTask.updated_at.desc()).limit(5).all()
    
    # Calculate some metrics
    total_agents = len(agents)
    active_agents = len([a for a in agents if a.status == 'online'])
    total_projects = len(projects)
    
    return render_template('dashboard.html', 
                         agents=agents, 
                         projects=projects,
                         recent_tasks=recent_tasks,
                         total_agents=total_agents,
                         active_agents=active_agents,
                         total_projects=total_projects)

@app.route('/document-upload')
def document_upload():
    """Document upload and analysis interface"""
    projects = db.session.query(Project).filter_by(status='active').all()
    documents = db.session.query(Document).order_by(Document.created_at.desc()).limit(10).all()
    return render_template('document_upload.html', projects=projects, documents=documents)

@app.route('/agent-workflow')
def agent_workflow():
    """Multi-agent workflow visualization"""
    return render_template('agent_workflow.html')

@app.route('/agent-communication')
def agent_communication():
    """Real-time agent communication display"""
    messages = db.session.query(AgentMessage).order_by(AgentMessage.created_at.desc()).limit(20).all()
    agents = db.session.query(Agent).all()
    return render_template('agent_communication.html', messages=messages, agents=agents)

@app.route('/requirements-analysis')
def requirements_analysis():
    """Requirements analysis screens"""
    requirements = db.session.query(Requirement).order_by(Requirement.priority, Requirement.requirement_id).all()
    projects = db.session.query(Project).filter_by(status='active').all()
    return render_template('requirements_analysis.html', requirements=requirements, projects=projects)

@app.route('/solution-architecture')
def solution_architecture():
    """Solution architecture presentation"""
    agents = db.session.query(Agent).filter_by(agent_type='solution').all()
    projects = db.session.query(Project).filter_by(status='active').all()
    return render_template('solution_architecture.html', agents=agents, projects=projects)

@app.route('/project-planning')
def project_planning():
    """Project planning timeline view"""
    projects = db.session.query(Project).filter_by(status='active').all()
    tasks = db.session.query(AgentTask).order_by(AgentTask.created_at.desc()).limit(15).all()
    return render_template('project_planning.html', projects=projects, tasks=tasks)

@app.route('/proposal-generation')
def proposal_generation():
    """Proposal generation interface"""
    proposals = db.session.query(Proposal).order_by(Proposal.created_at.desc()).all()
    projects = db.session.query(Project).filter_by(status='active').all()
    return render_template('proposal_generation.html', proposals=proposals, projects=projects)

@app.route('/quality-assurance')
def quality_assurance():
    """Quality assurance dashboard"""
    agents = db.session.query(Agent).all()
    tasks = db.session.query(AgentTask).filter(AgentTask.status.in_(['completed', 'failed'])).order_by(AgentTask.completed_at.desc()).limit(10).all()
    return render_template('quality_assurance.html', agents=agents, tasks=tasks)

@app.route('/agent-monitoring')
def agent_monitoring():
    """Agent performance monitoring"""
    agents = db.session.query(Agent).all()
    recent_logs = db.session.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(20).all()
    return render_template('agent_monitoring.html', agents=agents, recent_logs=recent_logs)

@app.route('/api/agents/status')
def api_agents_status():
    """API endpoint for real-time agent status updates"""
    agents = db.session.query(Agent).all()
    agent_data = []
    for agent in agents:
        agent_data.append({
            'id': agent.id,
            'name': agent.name,
            'type': agent.agent_type,
            'status': agent.status,
            'performance_metrics': agent.performance_metrics or {},
            'last_updated': agent.updated_at.isoformat() if agent.updated_at else None
        })
    return jsonify({'agents': agent_data, 'timestamp': datetime.utcnow().isoformat()})

@app.route('/api/tasks/recent')
def api_recent_tasks():
    """API endpoint for recent task updates"""
    tasks = db.session.query(AgentTask).order_by(AgentTask.updated_at.desc()).limit(10).all()
    task_data = []
    for task in tasks:
        task_data.append({
            'id': task.id,
            'type': task.task_type,
            'status': task.status,
            'progress': task.progress_percentage,
            'agent_name': task.agent.name if task.agent else 'Unknown',
            'project_name': task.project.name if task.project else 'Unknown',
            'updated_at': task.updated_at.isoformat() if task.updated_at else None
        })
    return jsonify({'tasks': task_data})

# Import models to ensure they're registered with the app
from models import Agent, Project, Document, Requirement, AgentTask, AgentMessage, SystemLog, Proposal, ProjectMetrics

# Create database tables
with app.app_context():
    db.create_all()
    logging.info("Database tables created successfully")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
