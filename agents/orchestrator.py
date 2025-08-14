# agents/orchestrator.py - Integration with existing workflow
from agents.partner_recommendation_agent import PartnerRecommendationAgent
from models import db, AgentTask, Agent
import asyncio

class AgentOrchestrator:
    """Enhanced orchestrator with partner recommendations"""

    def __init__(self):
        # Get agent IDs from database
        self.partner_agent_id = self._get_agent_id('PARTNER_RECOMMENDATION')

    def _get_agent_id(self, agent_type: str) -> int:
        """Get agent ID by type"""
        agent = Agent.query.filter_by(agent_type=agent_type).first()
        if not agent:
            # Create the agent if it doesn't exist
            agent = Agent(
                name='Partner Recommendation Agent',
                agent_type='PARTNER_RECOMMENDATION',
                description='AI agent that analyzes requirements and recommends partner products',
                model_name='claude-sonnet-4',
                temperature=0.3,
                is_active=True
            )
            db.session.add(agent)
            db.session.commit()
        return agent.id

    async def process_rfp_with_partners(self, project_id: int, requirements_data: list,
                                      architecture_data: dict) -> dict:
        """
        Enhanced RFP processing that includes partner recommendations
        """
        try:
            # 1. Create partner recommendation task
            partner_task = AgentTask(
                agent_id=self.partner_agent_id,
                task_type='ANALYZE_PARTNER_OPPORTUNITIES',
                title=f'Generate Partner Recommendations for Project {project_id}',
                description='Analyze project requirements and recommend suitable partner products',
                input_data={
                    'project_id': project_id,
                    'requirements': requirements_data,
                    'solution_architecture': architecture_data
                },
                project_id=project_id,
                priority='MEDIUM'
            )

            db.session.add(partner_task)
            db.session.commit()

            # 2. Process the task
            partner_agent = PartnerRecommendationAgent(
                agent_id=self.partner_agent_id,
                config={
                    'anthropic_api_key': 'your-api-key',  # From environment
                    'openai_api_key': 'your-openai-key'   # From environment
                }
            )

            partner_result = await partner_agent.process_task(partner_task.task_id)

            return {
                'success': True,
                'partner_recommendations': partner_result.get('recommendations', []),
                'recommendation_count': partner_result.get('count', 0),
                'task_id': partner_task.task_id
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'partner_recommendations': []
            }

    def trigger_partner_analysis(self, project_id: int) -> str:
        """
        Trigger partner analysis as a standalone task (for API endpoint)
        """
        try:
            # Get project requirements and architecture from database
            # You'll need to adapt this based on your data structure
            from models import Requirement, Project

            project = Project.query.get(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            requirements = Requirement.query.filter_by(project_id=project_id).all()
            requirements_data = [
                {
                    'title': req.title,
                    'description': req.description,
                    'type': req.requirement_type,
                    'priority': req.priority
                }
                for req in requirements
            ]

            # Mock architecture data for now - replace with actual architecture retrieval
            architecture_data = {
                'technologies': ['Python', 'PostgreSQL', 'React'],
                'components': ['API Gateway', 'Database', 'Frontend'],
                'integration_patterns': ['REST API', 'Microservices'],
                'security_requirements': ['Authentication', 'Authorization']
            }

            # Create and queue the task
            partner_task = AgentTask(
                agent_id=self.partner_agent_id,
                task_type='ANALYZE_PARTNER_OPPORTUNITIES',
                title=f'Generate Partner Recommendations for Project {project_id}',
                input_data={
                    'project_id': project_id,
                    'requirements': requirements_data,
                    'solution_architecture': architecture_data
                },
                project_id=project_id,
                priority='HIGH'
            )

            db.session.add(partner_task)
            db.session.commit()

            return partner_task.task_id

        except Exception as e:
            raise Exception(f"Failed to trigger partner analysis: {str(e)}")
