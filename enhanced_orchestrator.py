# enhanced_orchestrator.py - Enhanced orchestrator with assumptions analysis
import asyncio
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import agents
try:
    from agents.partner_recommendation_agent import PartnerRecommendationAgent
    from agents import partner_recommendation_agent
    AGENTS_AVAILABLE = True
except ImportError:
    from partner_recommendation_agent import PartnerRecommendationAgent
    AGENTS_AVAILABLE = True

# Import the assumptions analysis agent
from assumptions_analysis_agent import AssumptionsAnalysisAgent
from models import db, AgentTask, Agent, Project, Document, KeyPoint, ConsolidatedKeyPoint

class EnhancedAgentOrchestrator:
    """Enhanced orchestrator with partner recommendations and assumptions analysis"""

    def __init__(self):
        # Get or create agent IDs from database
        self.partner_agent_id = self._get_or_create_agent_id('PARTNER_RECOMMENDATION')
        self.assumptions_agent_id = self._get_or_create_agent_id('ASSUMPTIONS_ANALYSIS')

    def _get_or_create_agent_id(self, agent_type: str) -> int:
        """Get agent ID by type, create if not exists"""
        agent = Agent.query.filter_by(agent_type=agent_type).first()
        if not agent:
            # Create the agent based on type
            if agent_type == 'PARTNER_RECOMMENDATION':
                agent = Agent(
                    name='Partner Recommendation Agent',
                    agent_type='PARTNER_RECOMMENDATION',
                    description='AI agent that analyzes requirements and recommends partner products',
                    model_name='claude-sonnet-4',
                    temperature=0.3,
                    is_active=True
                )
            elif agent_type == 'ASSUMPTIONS_ANALYSIS':
                agent = Agent(
                    name='Assumptions Analysis Agent',
                    agent_type='ASSUMPTIONS_ANALYSIS',
                    description='AI agent that identifies project assumptions and provides strategic recommendations',
                    model_name='claude-sonnet-4',
                    temperature=0.2,  # Lower temperature for more consistent analysis
                    is_active=True,
                    system_prompt="""You are an expert project assumptions analyst and strategic advisor. 
                    Your role is to identify explicit and implicit assumptions, highlight preconditions, 
                    provide strategic recommendations, and identify potential risks with mitigation strategies."""
                )
            db.session.add(agent)
            db.session.commit()
        return agent.id

    async def run_complete_project_analysis(self, project_id: int) -> Dict[str, Any]:
        """
        Run complete project analysis including assumptions analysis and partner recommendations
        """
        results = {
            'project_id': project_id,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'assumptions_analysis': None,
            'partner_recommendations': None,
            'success': False,
            'errors': []
        }
        
        try:
            # 1. Run assumptions analysis first (provides foundation for other analyses)
            assumptions_result = await self.run_assumptions_analysis(project_id, 'full')
            results['assumptions_analysis'] = assumptions_result
            
            # 2. Run partner recommendations (can use assumptions analysis results)
            partner_result = await self.run_partner_analysis(project_id)
            results['partner_recommendations'] = partner_result
            
            # Check if both completed successfully
            assumptions_success = assumptions_result.get('success', False)
            partner_success = partner_result.get('success', False)
            
            results['success'] = assumptions_success and partner_success
            
            if not assumptions_success:
                results['errors'].append(f"Assumptions analysis failed: {assumptions_result.get('error', 'Unknown error')}")
            if not partner_success:
                results['errors'].append(f"Partner analysis failed: {partner_result.get('error', 'Unknown error')}")
            
            return results
            
        except Exception as e:
            results['errors'].append(f"Complete analysis failed: {str(e)}")
            return results

    async def run_assumptions_analysis(self, project_id: int, analysis_type: str = 'full') -> Dict[str, Any]:
        """
        Run assumptions analysis for a project
        
        Args:
            project_id: The project to analyze
            analysis_type: 'full', 'assumptions_only', or 'recommendations_only'
        """
        try:
            # Create assumptions analysis task
            assumptions_task = AgentTask(
                agent_id=self.assumptions_agent_id,
                task_type='ANALYZE_ASSUMPTIONS',
                title=f'Generate Assumptions Analysis for Project {project_id}',
                description=f'Analyze project assumptions and provide strategic recommendations ({analysis_type})',
                input_data={
                    'project_id': project_id,
                    'analysis_type': analysis_type
                },
                project_id=str(project_id),
                priority='HIGH',
                status='pending'
            )

            db.session.add(assumptions_task)
            db.session.commit()

            # Process the task
            assumptions_agent = AssumptionsAnalysisAgent(
                agent_id=self.assumptions_agent_id,
                config={
                    'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY'),
                    'openai_api_key': os.getenv('OPENAI_API_KEY')
                }
            )

            assumptions_result = await assumptions_agent.process_task(assumptions_task.task_id)

            return {
                'success': True,
                'analysis_data': assumptions_result,
                'task_id': assumptions_task.task_id,
                'analysis_type': analysis_type
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'analysis_data': None
            }

    async def run_partner_analysis(self, project_id: int) -> Dict[str, Any]:
        """
        Run partner recommendation analysis for a project
        """
        try:
            # Get project data for partner analysis
            requirements_data, architecture_data = self._get_project_context(project_id)

            # Create partner recommendation task
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
                project_id=str(project_id),
                priority='MEDIUM'
            )

            db.session.add(partner_task)
            db.session.commit()

            # Process the task
            partner_agent = PartnerRecommendationAgent(
                agent_id=self.partner_agent_id,
                config={
                    'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY'),
                    'openai_api_key': os.getenv('OPENAI_API_KEY')
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

    def _get_project_context(self, project_id: int) -> tuple:
        """Get project context data for analysis"""
        try:
            from models import Requirement
            
            # Get project
            project = Project.query.get(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Get requirements
            requirements = Requirement.query.filter_by(project_id=project_id).all()
            requirements_data = [
                {
                    'title': req.title,
                    'description': req.description,
                    'type': getattr(req, 'requirement_type', 'functional'),
                    'priority': getattr(req, 'priority', 'medium')
                }
                for req in requirements
            ]

            # Get key points as additional context
            key_points = KeyPoint.query.filter_by(project_id=project_id).all()
            for kp in key_points:
                if kp.key_point_type and 'requirement' in kp.key_point_type.lower():
                    requirements_data.append({
                        'title': f"Key Point: {kp.key_point_type}",
                        'description': kp.key_point,
                        'type': 'derived',
                        'priority': 'medium'
                    })

            # Build architecture data from consolidated key points
            consolidated_points = ConsolidatedKeyPoint.query.filter_by(project_id=project_id).all()
            architecture_data = {
                'technologies': [],
                'components': [],
                'integration_patterns': [],
                'security_requirements': []
            }

            for cp in consolidated_points:
                if 'technical' in cp.category.lower():
                    if 'technology' in cp.summary.lower():
                        architecture_data['technologies'].extend(
                            [tech.strip() for tech in cp.details.split(',') if tech.strip()]
                        )
                    elif 'component' in cp.summary.lower():
                        architecture_data['components'].extend(
                            [comp.strip() for comp in cp.details.split(',') if comp.strip()]
                        )
                elif 'security' in cp.category.lower():
                    architecture_data['security_requirements'].append(cp.summary)

            # Add defaults if empty
            if not architecture_data['technologies']:
                architecture_data['technologies'] = ['Web Application', 'Database', 'API']
            if not architecture_data['components']:
                architecture_data['components'] = ['Frontend', 'Backend', 'Database']
            
            return requirements_data, architecture_data

        except Exception as e:
            # Return minimal context on error
            return (
                [{'title': 'Project Analysis', 'description': f'Analysis for project {project_id}', 'type': 'general', 'priority': 'medium'}],
                {'technologies': ['Web Application'], 'components': ['Application'], 'integration_patterns': [], 'security_requirements': []}
            )

    def trigger_assumptions_analysis(self, project_id: int, analysis_type: str = 'full') -> str:
        """
        Trigger assumptions analysis as a standalone task (for API endpoint)
        """
        try:
            # Validate project exists
            project = Project.query.get(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Create and queue the task
            assumptions_task = AgentTask(
                agent_id=self.assumptions_agent_id,
                task_type='ANALYZE_ASSUMPTIONS',
                title=f'Generate Assumptions Analysis for Project {project_id}',
                description=f'Analyze project assumptions and provide strategic recommendations ({analysis_type})',
                input_data={
                    'project_id': project_id,
                    'analysis_type': analysis_type
                },
                project_id=str(project_id),
                priority='HIGH'
            )

            db.session.add(assumptions_task)
            db.session.commit()

            return assumptions_task.task_id

        except Exception as e:
            raise Exception(f"Failed to trigger assumptions analysis: {str(e)}")

    def trigger_partner_analysis(self, project_id: int) -> str:
        """
        Trigger partner analysis as a standalone task (for API endpoint)
        """
        try:
            requirements_data, architecture_data = self._get_project_context(project_id)

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
                project_id=str(project_id),
                priority='HIGH'
            )

            db.session.add(partner_task)
            db.session.commit()

            return partner_task.task_id

        except Exception as e:
            raise Exception(f"Failed to trigger partner analysis: {str(e)}")

    def get_analysis_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a specific analysis task"""
        try:
            task = AgentTask.query.filter_by(task_id=task_id).first()
            if not task:
                return {'error': 'Task not found'}

            return {
                'task_id': task_id,
                'status': task.status,
                'progress': task.progress_percentage,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'error_message': task.error_message,
                'output_available': task.output_data is not None
            }

        except Exception as e:
            return {'error': str(e)}

# Singleton instance
orchestrator_instance = None

def get_enhanced_orchestrator() -> EnhancedAgentOrchestrator:
    """Get or create enhanced orchestrator instance"""
    global orchestrator_instance
    if orchestrator_instance is None:
        orchestrator_instance = EnhancedAgentOrchestrator()
    return orchestrator_instance