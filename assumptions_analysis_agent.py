# assumptions_analysis_agent.py
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    from agents.base_agent import BaseAgent
    from models import db, AgentTask, Project, Document, KeyPoint, ConsolidatedKeyPoint
except ImportError:
    # Handle import without agents package structure
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from base_agent import BaseAgent
    from models import db, AgentTask, Project, Document, KeyPoint, ConsolidatedKeyPoint

class AssumptionsAnalysisAgent(BaseAgent):
    """
    Agent responsible for identifying project assumptions and providing AI analysis & recommendations.
    
    This agent:
    1. Analyzes RFP documents to identify implicit assumptions
    2. Highlights preconditions and constraints
    3. Provides strategic recommendations
    4. Identifies risks and mitigation strategies
    5. Suggests alternative approaches and solutions
    """

    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute assumptions analysis task"""
        
        task_data = task.input_data
        project_id = task_data.get('project_id')
        analysis_type = task_data.get('analysis_type', 'full')
        
        if not project_id:
            raise ValueError("project_id is required for assumptions analysis")
        
        # Load project data
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Get all available data for analysis
        documents = Document.query.filter_by(project_id=project_id).all()
        key_points = KeyPoint.query.filter_by(project_id=project_id).all()
        consolidated_points = ConsolidatedKeyPoint.query.filter_by(project_id=project_id).all()
        
        # Build context for analysis
        context = self._build_analysis_context(project, documents, key_points, consolidated_points)
        
        # Perform different types of analysis based on request
        if analysis_type == 'assumptions_only':
            result = await self._analyze_assumptions(context)
        elif analysis_type == 'recommendations_only':
            result = await self._generate_recommendations(context)
        else:
            result = await self._full_assumptions_analysis(context)
        
        # Store results in database
        await self._store_analysis_results(project_id, result)
        
        return result

    def _build_analysis_context(self, project: Project, documents: List[Document], 
                               key_points: List[KeyPoint], consolidated_points: List[ConsolidatedKeyPoint]) -> Dict[str, Any]:
        """Build comprehensive context for assumptions analysis"""
        
        context = {
            'project': {
                'name': project.name,
                'description': project.description,
                'created_at': project.created_at.isoformat() if project.created_at else None,
                'budget_estimate': getattr(project, 'budget_estimate', None),
                'timeline_estimate': getattr(project, 'timeline_estimate', None)
            },
            'documents': [],
            'requirements': [],
            'constraints': [],
            'deadlines': [],
            'technical_specs': [],
            'business_objectives': []
        }
        
        # Add document content
        for doc in documents:
            if doc.extracted_content:
                context['documents'].append({
                    'filename': doc.filename,
                    'content_preview': doc.extracted_content[:2000],  # First 2000 chars
                    'file_type': doc.filename.split('.')[-1] if '.' in doc.filename else 'unknown'
                })
        
        # Categorize key points
        for kp in key_points:
            category = kp.key_point_type.lower() if kp.key_point_type else 'general'
            content = {
                'id': kp.id,
                'content': kp.key_point,
                'category': kp.key_point_type,
                'confidence': kp.confidence_score,
                'source_document': kp.source_document
            }
            
            if 'requirement' in category or 'functional' in category:
                context['requirements'].append(content)
            elif 'constraint' in category or 'limitation' in category:
                context['constraints'].append(content)
            elif 'deadline' in category or 'timeline' in category:
                context['deadlines'].append(content)
            elif 'technical' in category:
                context['technical_specs'].append(content)
            elif 'business' in category or 'objective' in category:
                context['business_objectives'].append(content)
        
        # Add consolidated key points
        for cp in consolidated_points:
            context[cp.category.lower().replace(' ', '_') + '_consolidated'] = {
                'summary': cp.summary,
                'details': cp.details,
                'priority': cp.priority_level,
                'impact': cp.business_impact
            }
        
        return context

    async def _full_assumptions_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive assumptions analysis"""
        
        system_prompt = """
        You are an expert project assumptions analyst and strategic advisor. Your role is to:
        1. Identify explicit and implicit assumptions in project requirements
        2. Highlight preconditions and dependencies
        3. Provide strategic AI-powered analysis and recommendations
        4. Identify potential risks and mitigation strategies
        5. Suggest alternative approaches and innovative solutions
        
        Be thorough, analytical, and provide actionable insights.
        """
        
        prompt = f"""
        Analyze the following tender/RFP project data and provide comprehensive assumptions analysis and recommendations.

        PROJECT CONTEXT:
        {json.dumps(context['project'], indent=2)}

        REQUIREMENTS IDENTIFIED:
        {json.dumps(context['requirements'], indent=2)}

        CONSTRAINTS IDENTIFIED:
        {json.dumps(context['constraints'], indent=2)}

        TECHNICAL SPECIFICATIONS:
        {json.dumps(context['technical_specs'], indent=2)}

        BUSINESS OBJECTIVES:
        {json.dumps(context['business_objectives'], indent=2)}

        DEADLINES & TIMELINE:
        {json.dumps(context['deadlines'], indent=2)}

        Please provide a comprehensive analysis with the following sections:

        1. **PROJECT ASSUMPTIONS**
           - Explicit assumptions stated in the documents
           - Implicit assumptions we must make based on the requirements
           - Technical assumptions about infrastructure, platforms, integrations
           - Business assumptions about user behavior, adoption, scaling
           - Timeline and resource assumptions

        2. **PRECONDITIONS & DEPENDENCIES**
           - What must be in place before project can begin
           - External dependencies (third-party systems, approvals, etc.)
           - Internal dependencies (resources, skills, infrastructure)
           - Stakeholder availability and commitment assumptions

        3. **RISK ANALYSIS**
           - High-risk assumptions that could derail the project
           - Technical risks and their likelihood
           - Business and operational risks
           - Timeline and budget risks
           - Mitigation strategies for each identified risk

        4. **STRATEGIC RECOMMENDATIONS**
           - Recommended approach based on the requirements
           - Technology stack recommendations with justification
           - Project methodology and delivery approach
           - Team structure and skill requirements
           - Phase-wise implementation strategy

        5. **ALTERNATIVE SOLUTIONS**
           - Different ways to achieve the same business objectives
           - Trade-offs between different approaches
           - Innovative solutions using emerging technologies
           - Cost-effective alternatives for budget-conscious scenarios

        6. **CLARIFICATION NEEDED**
           - Questions that should be asked to the client
           - Assumptions that need validation
           - Missing information that could impact delivery
           - Scope clarifications recommended

        Format your response as structured JSON with clear sections and actionable insights.
        Each assumption should have a confidence level (high/medium/low) and potential impact (high/medium/low).
        """
        
        try:
            response = await self.call_claude(prompt, system_prompt, max_tokens=4000)
            
            # Try to parse as JSON first
            try:
                analysis_result = json.loads(response)
            except json.JSONDecodeError:
                # Fallback: structure the response manually
                analysis_result = self._parse_unstructured_response(response)
            
            # Add metadata
            analysis_result['analysis_metadata'] = {
                'generated_at': datetime.utcnow().isoformat(),
                'agent_type': 'assumptions_analysis',
                'analysis_version': '1.0',
                'confidence_score': self._calculate_overall_confidence(analysis_result)
            }
            
            return analysis_result
            
        except Exception as e:
            self._log_event('ERROR', 'analysis_failed', f"Assumptions analysis failed: {str(e)}")
            raise

    async def _analyze_assumptions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Focus only on identifying assumptions"""
        
        system_prompt = """
        You are an expert at identifying project assumptions. Focus solely on uncovering explicit and implicit assumptions in project requirements and documentation.
        """
        
        prompt = f"""
        Analyze this project data and identify all assumptions:

        {json.dumps(context, indent=2)}

        Return a JSON structure with:
        {{
            "explicit_assumptions": [
                {{"assumption": "text", "source": "document/section", "confidence": "high/medium/low", "impact": "high/medium/low"}}
            ],
            "implicit_assumptions": [
                {{"assumption": "text", "rationale": "why we assume this", "confidence": "high/medium/low", "impact": "high/medium/low"}}
            ],
            "technical_assumptions": [],
            "business_assumptions": [],
            "timeline_assumptions": [],
            "resource_assumptions": []
        }}
        """
        
        response = await self.call_claude(prompt, system_prompt, max_tokens=3000)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return self._parse_assumptions_response(response)

    async def _generate_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Focus only on generating strategic recommendations"""
        
        system_prompt = """
        You are a strategic technology consultant. Provide actionable recommendations for project success based on the given requirements and constraints.
        """
        
        prompt = f"""
        Based on this project context, provide strategic recommendations:

        {json.dumps(context, indent=2)}

        Return recommendations in this JSON format:
        {{
            "strategic_recommendations": [
                {{"category": "approach/technology/methodology", "recommendation": "text", "justification": "text", "priority": "high/medium/low"}}
            ],
            "technology_stack": {{"component": "recommendation with rationale"}},
            "implementation_approach": {{"phase": "description"}},
            "risk_mitigation": [
                {{"risk": "description", "mitigation": "strategy", "priority": "high/medium/low"}}
            ],
            "success_factors": ["factor1", "factor2"],
            "alternative_approaches": [
                {{"approach": "description", "pros": ["pro1"], "cons": ["con1"], "best_for": "scenario"}}
            ]
        }}
        """
        
        response = await self.call_claude(prompt, system_prompt, max_tokens=3000)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return self._parse_recommendations_response(response)

    def _calculate_overall_confidence(self, analysis_result: Dict[str, Any]) -> float:
        """Calculate overall confidence score for the analysis"""
        
        try:
            confidence_scores = []
            
            # Extract confidence scores from different sections
            for section in ['project_assumptions', 'preconditions_dependencies', 'risk_analysis']:
                if section in analysis_result and isinstance(analysis_result[section], list):
                    for item in analysis_result[section]:
                        if isinstance(item, dict) and 'confidence' in item:
                            conf = item['confidence'].lower()
                            if conf == 'high':
                                confidence_scores.append(0.9)
                            elif conf == 'medium':
                                confidence_scores.append(0.7)
                            elif conf == 'low':
                                confidence_scores.append(0.5)
            
            if confidence_scores:
                return sum(confidence_scores) / len(confidence_scores)
            else:
                return 0.7  # Default medium confidence
                
        except Exception:
            return 0.7

    async def _store_analysis_results(self, project_id: int, result: Dict[str, Any]) -> None:
        """Store analysis results in database"""
        
        try:
            # Import here to avoid circular imports
            from models import AssumptionAnalysis, ProjectAssumption, AIRecommendation
            
            # Store main analysis record
            analysis = AssumptionAnalysis(
                project_id=project_id,
                analysis_type='full_assumptions',
                raw_analysis=result,
                confidence_score=result.get('analysis_metadata', {}).get('confidence_score', 0.7),
                generated_at=datetime.utcnow(),
                agent_id=self.agent_id
            )
            
            db.session.add(analysis)
            db.session.flush()  # Get the ID
            
            # Store individual assumptions
            assumptions = []
            if 'project_assumptions' in result:
                assumptions.extend(result['project_assumptions'])
            if 'explicit_assumptions' in result:
                assumptions.extend(result['explicit_assumptions'])
            if 'implicit_assumptions' in result:
                assumptions.extend(result['implicit_assumptions'])
            
            for assumption_data in assumptions:
                if isinstance(assumption_data, dict) and 'assumption' in assumption_data:
                    assumption = ProjectAssumption(
                        project_id=project_id,
                        analysis_id=analysis.id,
                        assumption_text=assumption_data['assumption'],
                        assumption_type=assumption_data.get('category', 'general'),
                        confidence_level=assumption_data.get('confidence', 'medium'),
                        impact_level=assumption_data.get('impact', 'medium'),
                        source_reference=assumption_data.get('source', 'analysis'),
                        validation_status='pending'
                    )
                    db.session.add(assumption)
            
            # Store recommendations
            recommendations = result.get('strategic_recommendations', [])
            for rec_data in recommendations:
                if isinstance(rec_data, dict) and 'recommendation' in rec_data:
                    recommendation = AIRecommendation(
                        project_id=project_id,
                        analysis_id=analysis.id,
                        recommendation_type=rec_data.get('category', 'general'),
                        recommendation_text=rec_data['recommendation'],
                        justification=rec_data.get('justification', ''),
                        priority_level=rec_data.get('priority', 'medium'),
                        implementation_effort=rec_data.get('effort', 'medium'),
                        expected_impact=rec_data.get('impact', 'medium'),
                        status='pending_review'
                    )
                    db.session.add(recommendation)
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            self._log_event('ERROR', 'storage_failed', f"Failed to store analysis results: {str(e)}")
            # Don't raise - analysis was successful even if storage failed

    def _parse_unstructured_response(self, response: str) -> Dict[str, Any]:
        """Fallback parser for unstructured AI response"""
        
        # Basic structure for unstructured response
        return {
            'analysis_text': response,
            'structured_data': {
                'assumptions': self._extract_assumptions_from_text(response),
                'recommendations': self._extract_recommendations_from_text(response)
            },
            'analysis_metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'parsing_method': 'fallback_unstructured',
                'confidence_score': 0.6
            }
        }

    def _extract_assumptions_from_text(self, text: str) -> List[Dict[str, str]]:
        """Extract assumptions from unstructured text"""
        
        assumptions = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['assume', 'assumption', 'presume', 'expect']):
                assumptions.append({
                    'assumption': line,
                    'confidence': 'medium',
                    'source': 'text_extraction'
                })
        
        return assumptions

    def _extract_recommendations_from_text(self, text: str) -> List[Dict[str, str]]:
        """Extract recommendations from unstructured text"""
        
        recommendations = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['recommend', 'suggest', 'should', 'advise']):
                recommendations.append({
                    'recommendation': line,
                    'priority': 'medium',
                    'source': 'text_extraction'
                })
        
        return recommendations

    def _parse_assumptions_response(self, response: str) -> Dict[str, Any]:
        """Parse assumptions-focused response"""
        return self._parse_unstructured_response(response)

    def _parse_recommendations_response(self, response: str) -> Dict[str, Any]:
        """Parse recommendations-focused response"""
        return self._parse_unstructured_response(response)