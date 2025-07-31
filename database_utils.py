"""Database utilities and data initialization for AI Tender Analysis System"""

from datetime import datetime, timedelta
import json
from app import app, db
from models import Agent, Project, Document, Requirement, AgentTask, AgentMessage, SystemLog


def initialize_agents():
    """Create the 9 specialized AI agents"""
    
    agents_data = [
        {
            'name': 'Agent Orchestrator',
            'agent_type': 'orchestrator',
            'description': 'Master AI that coordinates all specialized agents, manages communication, and ensures quality',
            'model_name': 'claude-sonnet-4',
            'status': 'online',
            'specialties': ['coordination', 'conflict_resolution', 'quality_assurance'],
            'performance_metrics': {'efficiency': 95, 'response_time': 1.2, 'tasks_completed': 245}
        },
        {
            'name': 'Document Intelligence',
            'agent_type': 'analysis',
            'description': 'Specialized in document parsing, OCR, structure extraction, and content analysis',
            'model_name': 'claude-sonnet-4-vision',
            'status': 'online',
            'specialties': ['document_parsing', 'ocr', 'structure_extraction', 'metadata_analysis'],
            'performance_metrics': {'efficiency': 92, 'response_time': 2.1, 'tasks_completed': 156}
        },
        {
            'name': 'Requirements Engineering',
            'agent_type': 'analysis',
            'description': 'Expert in requirement extraction, classification, and dependency analysis',
            'model_name': 'claude-sonnet-4',
            'status': 'processing',
            'specialties': ['requirement_extraction', 'moscow_prioritization', 'dependency_mapping'],
            'performance_metrics': {'efficiency': 88, 'response_time': 3.2, 'tasks_completed': 134}
        },
        {
            'name': 'Risk Assessment',
            'agent_type': 'analysis',
            'description': 'Specialized in risk identification, analysis, and mitigation strategy development',
            'model_name': 'o1-reasoning',
            'status': 'online',
            'specialties': ['risk_identification', 'probability_modeling', 'scenario_analysis'],
            'performance_metrics': {'efficiency': 91, 'response_time': 4.5, 'tasks_completed': 89}
        },
        {
            'name': 'Solution Architecture',
            'agent_type': 'solution',
            'description': 'Technical architect for system design, technology selection, and integration planning',
            'model_name': 'claude-sonnet-4',
            'status': 'online',
            'specialties': ['system_design', 'technology_selection', 'integration_planning'],
            'performance_metrics': {'efficiency': 94, 'response_time': 2.8, 'tasks_completed': 78}
        },
        {
            'name': 'Cost Estimation',
            'agent_type': 'solution',
            'description': 'Commercial analyst for resource estimation, cost modeling, and pricing optimization',
            'model_name': 'claude-sonnet-4',
            'status': 'waiting',
            'specialties': ['cost_modeling', 'resource_estimation', 'roi_calculation'],
            'performance_metrics': {'efficiency': 87, 'response_time': 2.3, 'tasks_completed': 67}
        },
        {
            'name': 'Project Planning',
            'agent_type': 'delivery',
            'description': 'Project manager for timeline creation, resource allocation, and critical path analysis',
            'model_name': 'o1-reasoning',
            'status': 'online',
            'specialties': ['timeline_planning', 'resource_allocation', 'critical_path_analysis'],
            'performance_metrics': {'efficiency': 93, 'response_time': 3.7, 'tasks_completed': 92}
        },
        {
            'name': 'Proposal Generation',
            'agent_type': 'delivery',
            'description': 'Content synthesis expert for proposal creation and professional formatting',
            'model_name': 'claude-sonnet-4',
            'status': 'online',
            'specialties': ['content_synthesis', 'document_formatting', 'persuasive_writing'],
            'performance_metrics': {'efficiency': 96, 'response_time': 1.9, 'tasks_completed': 45}
        },
        {
            'name': 'Quality Assurance',
            'agent_type': 'delivery',
            'description': 'Quality manager for validation, consistency checking, and final review',
            'model_name': 'claude-sonnet-4',
            'status': 'online',
            'specialties': ['validation', 'consistency_checking', 'quality_scoring'],
            'performance_metrics': {'efficiency': 98, 'response_time': 1.5, 'tasks_completed': 123}
        }
    ]
    
    for agent_data in agents_data:
        # Check if agent already exists
        existing_agent = Agent.query.filter_by(name=agent_data['name']).first()
        if not existing_agent:
            agent = Agent(
                name=agent_data['name'],
                agent_type=agent_data['agent_type'],
                description=agent_data['description'],
                model_name=agent_data['model_name'],
                status=agent_data['status'],
                specialties=agent_data['specialties'],
                performance_metrics=agent_data['performance_metrics'],
                config={'temperature': 0.7, 'max_tokens': 4000}
            )
            db.session.add(agent)
    
    db.session.commit()
    print(f"Initialized {len(agents_data)} AI agents")


def create_sample_project():
    """Create a sample project with documents and requirements"""
    
    # Check if sample project already exists
    existing_project = Project.query.filter_by(name='Enterprise Banking Platform Modernization').first()
    if existing_project:
        return existing_project
    
    project = Project(
        name='Enterprise Banking Platform Modernization',
        description='Modernization of legacy core banking system with cloud-native architecture, real-time processing, and enhanced security features.',
        status='active',
        client_name='National Bank of Innovation',
        submission_deadline=datetime.utcnow() + timedelta(days=30),
        estimated_value=2500000.00
    )
    db.session.add(project)
    db.session.flush()  # Get the project ID
    
    # Add sample documents
    documents_data = [
        {
            'filename': 'tender_requirements_v2.pdf',
            'original_filename': 'Banking_System_Tender_Requirements_v2.1.pdf',
            'file_size': 2456789,
            'file_type': 'application/pdf',
            'analysis_status': 'completed',
            'extracted_text': 'Core banking system requirements including real-time transaction processing, regulatory compliance (Basel III, PCI DSS), multi-currency support...'
        },
        {
            'filename': 'technical_specifications.docx',
            'original_filename': 'Technical_Architecture_Specifications.docx',
            'file_size': 1234567,
            'file_type': 'application/docx',
            'analysis_status': 'in_progress',
            'extracted_text': 'System architecture must support microservices, API-first design, cloud deployment (AWS/Azure), containerization...'
        }
    ]
    
    for doc_data in documents_data:
        document = Document(
            project_id=project.id,
            filename=doc_data['filename'],
            original_filename=doc_data['original_filename'],
            file_size=doc_data['file_size'],
            file_type=doc_data['file_type'],
            analysis_status=doc_data['analysis_status'],
            extracted_text=doc_data['extracted_text'],
            document_metadata={'pages': 45, 'language': 'en', 'confidence': 0.95}
        )
        db.session.add(document)
    
    db.session.flush()  # Get document IDs
    
    # Add sample requirements
    requirements_data = [
        {
            'requirement_id': 'REQ-001',
            'title': 'Real-time Transaction Processing',
            'description': 'System must process financial transactions in real-time with sub-second response times for standard operations.',
            'requirement_type': 'functional',
            'priority': 'must_have',
            'complexity': 'high',
            'estimated_effort': 480,
            'acceptance_criteria': ['Response time < 500ms for 95% of transactions', 'Support 10,000 concurrent users', 'Zero data loss guarantee']
        },
        {
            'requirement_id': 'REQ-002',
            'title': 'Multi-Currency Support',
            'description': 'Support for 50+ international currencies with real-time exchange rate integration.',
            'requirement_type': 'functional',
            'priority': 'must_have',
            'complexity': 'medium',
            'estimated_effort': 240,
            'acceptance_criteria': ['Support minimum 50 currencies', 'Real-time rate updates', 'Currency conversion accuracy 99.99%']
        },
        {
            'requirement_id': 'REQ-003',
            'title': 'Regulatory Compliance',
            'description': 'Full compliance with Basel III, PCI DSS, and local banking regulations.',
            'requirement_type': 'non_functional',
            'priority': 'must_have',
            'complexity': 'high',
            'estimated_effort': 360,
            'acceptance_criteria': ['Basel III capital adequacy reporting', 'PCI DSS Level 1 certification', 'Audit trail completeness']
        }
    ]
    
    for req_data in requirements_data:
        requirement = Requirement(
            project_id=project.id,
            requirement_id=req_data['requirement_id'],
            title=req_data['title'],
            description=req_data['description'],
            requirement_type=req_data['requirement_type'],
            priority=req_data['priority'],
            complexity=req_data['complexity'],
            estimated_effort=req_data['estimated_effort'],
            acceptance_criteria=req_data['acceptance_criteria'],
            status='analyzed'
        )
        db.session.add(requirement)
    
    db.session.commit()
    print(f"Created sample project: {project.name}")
    return project


def create_sample_agent_tasks():
    """Create sample agent tasks for demonstration"""
    
    project = Project.query.filter_by(name='Enterprise Banking Platform Modernization').first()
    if not project:
        return
    
    # Get some agents
    doc_agent = Agent.query.filter_by(name='Document Intelligence').first()
    req_agent = Agent.query.filter_by(name='Requirements Engineering').first()
    arch_agent = Agent.query.filter_by(name='Solution Architecture').first()
    
    tasks_data = [
        {
            'agent': doc_agent,
            'task_type': 'document_analysis',
            'priority': 'high',
            'status': 'completed',
            'progress_percentage': 100,
            'estimated_duration': 45,
            'actual_duration': 42,
            'input_data': {'document_ids': [1, 2], 'analysis_depth': 'comprehensive'},
            'output_data': {'requirements_extracted': 25, 'entities_identified': 45, 'confidence_score': 0.92}
        },
        {
            'agent': req_agent,
            'task_type': 'requirement_extraction',
            'priority': 'high',
            'status': 'in_progress',
            'progress_percentage': 75,
            'estimated_duration': 90,
            'input_data': {'document_text': 'extracted_content', 'classification_rules': 'moscow'},
            'output_data': {'requirements_identified': 18, 'conflicts_detected': 2}
        },
        {
            'agent': arch_agent,
            'task_type': 'architecture_design',
            'priority': 'medium',
            'status': 'pending',
            'progress_percentage': 0,
            'estimated_duration': 120,
            'input_data': {'requirements': ['REQ-001', 'REQ-002'], 'constraints': ['cloud_native', 'microservices']}
        }
    ]
    
    for task_data in tasks_data:
        # Check if task already exists
        existing_task = AgentTask.query.filter_by(
            project_id=project.id,
            agent_id=task_data['agent'].id,
            task_type=task_data['task_type']
        ).first()
        
        if not existing_task:
            task = AgentTask(
                project_id=project.id,
                agent_id=task_data['agent'].id,
                task_type=task_data['task_type'],
                priority=task_data['priority'],
                status=task_data['status'],
                progress_percentage=task_data['progress_percentage'],
                estimated_duration=task_data['estimated_duration'],
                actual_duration=task_data.get('actual_duration'),
                input_data=task_data['input_data'],
                output_data=task_data.get('output_data', {}),
                started_at=datetime.utcnow() - timedelta(hours=2) if task_data['status'] != 'pending' else None,
                completed_at=datetime.utcnow() - timedelta(minutes=30) if task_data['status'] == 'completed' else None
            )
            db.session.add(task)
    
    db.session.commit()
    print("Created sample agent tasks")


def create_sample_messages():
    """Create sample inter-agent communication messages"""
    
    project = Project.query.filter_by(name='Enterprise Banking Platform Modernization').first()
    if not project:
        return
    
    orchestrator = Agent.query.filter_by(name='Agent Orchestrator').first()
    doc_agent = Agent.query.filter_by(name='Document Intelligence').first()
    req_agent = Agent.query.filter_by(name='Requirements Engineering').first()
    
    messages_data = [
        {
            'agent': orchestrator,
            'recipient': doc_agent,
            'message_type': 'REQUEST',
            'priority': 'high',
            'subject': 'Document Analysis Request',
            'content': 'Please analyze the uploaded tender documents and extract all functional and non-functional requirements.',
            'conversation_id': 'conv_001'
        },
        {
            'agent': doc_agent,
            'recipient': orchestrator,
            'message_type': 'RESPONSE',
            'priority': 'high',
            'subject': 'Document Analysis Complete',
            'content': 'Analysis completed. Extracted 25 requirements, identified 12 key entities, and detected 2 potential conflicts.',
            'conversation_id': 'conv_001'
        },
        {
            'agent': orchestrator,
            'recipient': req_agent,
            'message_type': 'REQUEST',
            'priority': 'medium',
            'subject': 'Requirements Classification',
            'content': 'Please classify the extracted requirements using MoSCoW prioritization and identify dependencies.',
            'conversation_id': 'conv_002'
        }
    ]
    
    for msg_data in messages_data:
        # Check if message already exists
        existing_msg = AgentMessage.query.filter_by(
            agent_id=msg_data['agent'].id,
            subject=msg_data['subject']
        ).first()
        
        if not existing_msg:
            message = AgentMessage(
                agent_id=msg_data['agent'].id,
                recipient_agent_id=msg_data['recipient'].id if msg_data['recipient'] else None,
                project_id=project.id,
                message_type=msg_data['message_type'],
                priority=msg_data['priority'],
                subject=msg_data['subject'],
                content=msg_data['content'],
                conversation_id=msg_data['conversation_id'],
                status='processed' if msg_data['message_type'] == 'RESPONSE' else 'delivered',
                created_at=datetime.utcnow() - timedelta(minutes=30)
            )
            db.session.add(message)
    
    db.session.commit()
    print("Created sample inter-agent messages")


def log_system_event(level, source, event_type, message, details=None, project_id=None, agent_id=None):
    """Helper function to log system events"""
    log_entry = SystemLog(
        level=level,
        source=source,
        event_type=event_type,
        message=message,
        log_details=details or {},
        project_id=project_id,
        agent_id=agent_id
    )
    db.session.add(log_entry)
    db.session.commit()


def initialize_database():
    """Initialize the database with sample data"""
    with app.app_context():
        print("Initializing database with sample data...")
        
        # Initialize agents
        initialize_agents()
        
        # Create sample project
        project = create_sample_project()
        
        # Create sample tasks
        create_sample_agent_tasks()
        
        # Create sample messages
        create_sample_messages()
        
        # Log initialization
        log_system_event(
            level='INFO',
            source='system',
            event_type='database_initialized',
            message='Database initialized with sample data',
            details={'timestamp': datetime.utcnow().isoformat()}
        )
        
        print("Database initialization completed successfully!")


if __name__ == '__main__':
    initialize_database()