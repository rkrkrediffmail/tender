# agents/requirements_engineering.py
import re
import json
from typing import Dict, Any, List, Tuple
from agents.base_agent import BaseAgent
from models import AgentTask, Document, Requirement, db

class RequirementsEngineeringAgent(BaseAgent):
    """Specialized agent for requirement extraction and analysis"""

    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute requirements engineering tasks"""

        task_type = task.task_type
        input_data = task.input_data

        if task_type == 'requirement_extraction':
            return await self._extract_requirements(input_data['project_id'], input_data.get('document_ids', []))
        elif task_type == 'requirement_analysis':
            return await self._analyze_requirements(input_data['project_id'])
        elif task_type == 'dependency_mapping':
            return await self._map_dependencies(input_data['project_id'])
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _extract_requirements(self, project_id: int, document_ids: List[int] = None) -> Dict[str, Any]:
        """Extract requirements from project documents"""

        # Get documents to analyze
        if document_ids:
            documents = Document.query.filter(Document.id.in_(document_ids)).all()
        else:
            documents = Document.query.filter_by(project_id=project_id).all()

        extracted_requirements = []

        for document in documents:
            if not document.extracted_text:
                continue

            # Use Claude to extract requirements from document text
            extraction_prompt = f"""
            Analyze this RFP document and extract ALL requirements. Pay special attention to:

            Document: {document.original_filename}
            Content: {document.extracted_text}

            Extract requirements in the following categories:
            1. FUNCTIONAL REQUIREMENTS (what the system must do)
            2. NON-FUNCTIONAL REQUIREMENTS (performance, security, usability)
            3. TECHNICAL REQUIREMENTS (platforms, technologies, standards)
            4. BUSINESS REQUIREMENTS (business rules, compliance, processes)
            5. INTEGRATION REQUIREMENTS (APIs, data exchange, third-party systems)

            For each requirement, provide:
            - Unique ID (REQ-001, REQ-002, etc.)
            - Title (brief summary)
            - Description (detailed requirement)
            - Category (functional/non_functional/technical/business/integration)
            - Priority (must_have/should_have/could_have/wont_have)
            - Complexity (low/medium/high)
            - Source page/section
            - Acceptance criteria (how to verify completion)

            Return as JSON array with this structure:
            [{{
                "requirement_id": "REQ-001",
                "title": "User Authentication",
                "description": "The system must provide secure user authentication...",
                "category": "functional",
                "priority": "must_have",
                "complexity": "medium",
                "source_page": "Page 15",
                "acceptance_criteria": ["Users can log in with username/password", "Failed login attempts are logged"]
            }}]

            IMPORTANT: Extract EVERY requirement mentioned in the document. Be comprehensive.
            """

            requirements_json = await self.call_claude(extraction_prompt, max_tokens=8000)

            try:
                document_requirements = json.loads(requirements_json)

                # Save requirements to database
                for req_data in document_requirements:
                    requirement = Requirement(
                        requirement_id=req_data['requirement_id'],
                        title=req_data['title'],
                        description=req_data['description'],
                        requirement_type=req_data['category'],
                        priority=req_data['priority'],
                        complexity=req_data['complexity'],
                        source_document_id=document.id,
                        source_page=req_data.get('source_page', ''),
                        acceptance_criteria=req_data.get('acceptance_criteria', []),
                        project_id=project_id,
                        status='identified'
                    )
                    db.session.add(requirement)
                    extracted_requirements.append(req_data)

                db.session.commit()

            except json.JSONDecodeError as e:
                self._log_event('ERROR', 'json_parse_failed', f"Failed to parse requirements JSON: {str(e)}")

        return {
            'project_id': project_id,
            'total_requirements': len(extracted_requirements),
            'requirements': extracted_requirements,
            'categories': self._categorize_requirements(extracted_requirements),
            'status': 'completed'
        }

    async def _analyze_requirements(self, project_id: int) -> Dict[str, Any]:
        """Analyze extracted requirements for conflicts, gaps, and priorities"""

        requirements = Requirement.query.filter_by(project_id=project_id).all()

        if not requirements:
            return {'error': 'No requirements found for analysis'}

        # Prepare requirements data for analysis
        req_data = []
        for req in requirements:
            req_data.append({
                'id': req.requirement_id,
                'title': req.title,
                'description': req.description,
                'type': req.requirement_type,
                'priority': req.priority,
                'complexity': req.complexity
            })

        analysis_prompt = f"""
        Analyze these requirements for a software project and identify:

        Requirements: {json.dumps(req_data, indent=2)}

        Please provide:

        1. CONFLICT ANALYSIS:
           - Identify requirements that conflict with each other
           - Explain the nature of each conflict
           - Suggest resolution approaches

        2. DEPENDENCY ANALYSIS:
           - Identify requirements that depend on others
           - Create a dependency graph
           - Highlight critical path requirements

        3. GAP ANALYSIS:
           - Identify missing requirements in common areas:
             * Security and authentication
             * Data backup and recovery
             * Performance and scalability
             * Integration points
             * User management
             * Audit and logging
             * Error handling

        4. PRIORITY VALIDATION:
           - Review MoSCoW prioritization
           - Suggest priority adjustments based on dependencies
           - Identify quick wins vs. complex requirements

        5. EFFORT ESTIMATION:
           - Provide rough effort estimates (person-hours) for each requirement
           - Identify requirements that need further breakdown

        Return as structured JSON with sections for conflicts, dependencies, gaps, priorities, and estimates.
        """

        analysis_result = await self.call_claude(analysis_prompt, max_tokens=8000)

        try:
            analysis_data = json.loads(analysis_result)

            # Update requirements with analysis results
            for req in requirements:
                # Update conflicts
                conflicts = analysis_data.get('conflicts', {}).get(req.requirement_id, [])
                if conflicts:
                    req.conflicts_with = conflicts

                # Update dependencies
                dependencies = analysis_data.get('dependencies', {}).get(req.requirement_id, [])
                if dependencies:
                    req.dependencies = dependencies

                # Update effort estimate
                effort = analysis_data.get('estimates', {}).get(req.requirement_id, 0)
                if effort:
                    req.estimated_effort = effort

                req.status = 'analyzed'

            db.session.commit()

            return {
                'project_id': project_id,
                'analysis': analysis_data,
                'total_conflicts': len(analysis_data.get('conflicts', {})),
                'total_dependencies': len(analysis_data.get('dependencies', {})),
                'identified_gaps': len(analysis_data.get('gaps', [])),
                'status': 'completed'
            }

        except json.JSONDecodeError as e:
            self._log_event('ERROR', 'analysis_parse_failed', f"Failed to parse analysis JSON: {str(e)}")
            return {'error': 'Failed to parse analysis results'}

    def _categorize_requirements(self, requirements: List[Dict]) -> Dict[str, int]:
        """Categorize requirements by type and priority"""

        categories = {
            'functional': 0,
            'non_functional': 0,
            'technical': 0,
            'business': 0,
            'integration': 0
        }

        priorities = {
            'must_have': 0,
            'should_have': 0,
            'could_have': 0,
            'wont_have': 0
        }

        for req in requirements:
            categories[req.get('category', 'functional')] += 1
            priorities[req.get('priority', 'should_have')] += 1

        return {
            'by_type': categories,
            'by_priority': priorities
        }
