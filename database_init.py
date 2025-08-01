# database_init.py
from app import app, db
from models import User, Agent, Project
from werkzeug.security import generate_password_hash
import json

def initialize_database():
    """Initialize database with sample data"""

    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created successfully")

        # Create default admin user
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@tender-system.com',
                full_name='System Administrator',
                role='admin'
            )
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
            print("✅ Default admin user created")

        # Initialize AI agents
        initialize_agents()

        # Create sample project
        create_sample_project()

        db.session.commit()
        print("✅ Database initialization completed")

def initialize_agents():
    """Create the 9 specialized AI agents"""

    agents_data = [
        {
            'name': 'Agent Orchestrator',
            'agent_type': 'orchestrator',
            'description': 'Master AI coordinator for all specialized agents',
            'model_name': 'claude-sonnet-4',
            'status': 'online',
            'specialties': ['coordination', 'conflict_resolution', 'quality_assurance'],
            'system_prompt': '''You are the Agent Orchestrator, responsible for coordinating all AI agents in the tender analysis system. Your role is to:
1. Manage task distribution among specialized agents
2. Resolve conflicts between agents
3. Ensure quality and consistency across all outputs
4. Maintain overall project timeline and priorities
5. Communicate status updates to users''',
            'performance_metrics': {'efficiency': 95, 'response_time': 1.2, 'tasks_completed': 0}
        },
        {
            'name': 'Document Intelligence',
            'agent_type': 'analysis',
            'description': 'Specialized in document parsing and content extraction',
            'model_name': 'claude-sonnet-4-vision',
            'status': 'online',
            'specialties': ['document_parsing', 'ocr', 'structure_extraction', 'metadata_analysis'],
            'system_prompt': '''You are the Document Intelligence Agent. Your expertise includes:
1. Parsing PDF, Word, and other document formats
2. Extracting structured information from unstructured text
3. Identifying document sections, tables, and key information
4. Performing OCR on scanned documents
5. Creating metadata and document summaries''',
            'performance_metrics': {'efficiency': 92, 'response_time': 2.1, 'tasks_completed': 0}
        },
        {
            'name': 'Requirements Engineering',
            'agent_type': 'analysis',
            'description': 'Expert in requirement extraction and analysis',
            'model_name': 'claude-sonnet-4',
            'status': 'online',
            'specialties': ['requirement_extraction', 'moscow_prioritization', 'dependency_mapping', 'conflict_detection'],
            'system_prompt': '''You are the Requirements Engineering Agent. Your responsibilities include:
1. Extracting functional and non-functional requirements from RFP documents
2. Categorizing requirements using MoSCoW prioritization
3. Identifying dependencies and conflicts between requirements
4. Creating acceptance criteria and test conditions
5. Ensuring requirement completeness and clarity''',
            'performance_metrics': {'efficiency': 89, 'response_time': 2.8, 'tasks_completed': 0}
        }
        # Add remaining 6 agents...
    ]

    for agent_data in agents_data:
        if not Agent.query.filter_by(name=agent_data['name']).first():
            agent = Agent(**agent_data)
            db.session.add(agent)
            print(f"✅ Created agent: {agent_data['name']}")

def create_sample_project():
    """Create sample project using the Saudi Home Loans RFP"""

    admin_user = User.query.filter_by(username='admin').first()
    if admin_user and not Project.query.filter_by(name='Saudi Home Loans Platform').first():
        project = Project(
            name='Saudi Home Loans Platform',
            description='AI-powered digital lending platform for Saudi Home Loans',
            rfp_title='Request for Proposal - Digital Lending Platform',
            client_name='Saudi Home Loans (SHL)',
            estimated_value=250000.0,
            currency='USD',
            status='active',
            priority='high',
            user_id=admin_user.id
        )
        db.session.add(project)
        print("✅ Created sample project: Saudi Home Loans Platform")

if __name__ == '__main__':
    initialize_database()
