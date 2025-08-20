# enhanced_proposal_generator.py
"""
Enhanced proposal generation engine with support for DOCX/PPTX templates and AI-only generation
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import anthropic

# Import existing components
from proposal_generator import ProposalGenerator
from template_processor import get_template_processor
from real_analysis_system import get_real_analysis_results
from models import db, ProposalTemplate, TemplateBookmark, GeneratedProposal

logger = logging.getLogger(__name__)

class EnhancedProposalGenerator(ProposalGenerator):
    """
    Enhanced proposal generator with template support and AI integration
    """
    
    def __init__(self, project, analysis_results, company_name="Your Company", contact_person="Project Manager"):
        super().__init__(project, analysis_results, company_name, contact_person)
        self.template_processor = get_template_processor()
        
        # Enhanced company information
        self.company_info = {
            'name': company_name,
            'contact_person': contact_person,
            'address': '',
            'phone': '',
            'email': '',
            'website': '',
            'established_year': '',
            'expertise_areas': [],
            'certifications': [],
            'team_size': '',
            'project_experience': ''
        }
    
    def generate_with_template(self,
                             template_id: int,
                             deliverable_type: str,
                             custom_content: Dict[str, Any] = None,
                             detail_level: str = 'standard') -> Dict[str, Any]:
        """
        Generate proposal using a DOCX/PPTX template
        
        Args:
            template_id: ID of the template to use
            deliverable_type: Type of deliverable ('technical', 'commercial', etc.)
            custom_content: Custom content for specific bookmarks
            detail_level: Level of detail for AI-generated content
            
        Returns:
            Dict with generation results and file information
        """
        try:
            # Load template from database
            template = ProposalTemplate.query.get(template_id)
            if not template:
                return {
                    'success': False,
                    'error': 'Template not found',
                    'template_id': template_id
                }
            
            # Prepare project data
            project_data = {
                'id': self.project.id,
                'name': self.project.name,
                'description': getattr(self.project, 'description', ''),
                'client_name': self.client_name,
                'created_at': self.project.created_at.isoformat() if hasattr(self.project, 'created_at') and self.project.created_at else datetime.now().isoformat()
            }
            
            # Generate AI content for bookmarks
            bookmark_content = self._generate_all_bookmark_content(
                template, deliverable_type, custom_content or {}, detail_level
            )
            
            # Merge with company info and custom content
            all_content = {
                **self.company_info,
                **bookmark_content,
                **(custom_content or {})
            }
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"{self.project.name}_{deliverable_type}_{timestamp}.{template.template_type}"
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Process template with content
            result = self.template_processor.generate_proposal_from_template(
                template_id=template_id,
                project_data=project_data,
                content_data=all_content,
                output_path=output_path
            )
            
            if result.get('success'):
                # Create database record
                generated_proposal = GeneratedProposal(
                    project_id=str(self.project.id),
                    template_id=template_id,
                    deliverable_type=deliverable_type,
                    output_format=template.template_type,
                    generation_method='template',
                    output_filename=output_filename,
                    output_filepath=output_path,
                    file_size=result.get('file_size', 0),
                    bookmark_content=result.get('bookmark_content', {}),
                    generation_metadata={
                        'detail_level': detail_level,
                        'ai_model': 'claude-3-sonnet-20240229',
                        'bookmarks_processed': result.get('bookmarks_processed', 0),
                        'generation_time': datetime.now().isoformat()
                    },
                    status='completed'
                )
                
                db.session.add(generated_proposal)
                db.session.commit()
                
                return {
                    'success': True,
                    'title': f"{deliverable_type.title()} Proposal - {self.project.name}",
                    'filename': output_filename,
                    'filepath': output_path,
                    'format': template.template_type,
                    'size': result.get('file_size', 0),
                    'download_url': f'/download-proposal/{output_filename}',
                    'template_used': template.name,
                    'bookmarks_processed': result.get('bookmarks_processed', 0),
                    'generation_method': 'template',
                    'proposal_id': generated_proposal.proposal_id,
                    'generated_at': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Template processing failed'),
                    'template_id': template_id
                }
                
        except Exception as e:
            logger.error(f"Error generating proposal with template {template_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'template_id': template_id
            }
    
    def generate_without_template(self,
                                deliverable_type: str,
                                output_format: str = 'html',
                                detail_level: str = 'standard',
                                include_company_info: bool = True) -> Dict[str, Any]:
        """
        Generate proposal using AI only (existing functionality)
        
        Args:
            deliverable_type: Type of deliverable
            output_format: Output format ('html', 'pdf')
            detail_level: Level of detail
            include_company_info: Whether to include company information
            
        Returns:
            Dict with generation results
        """
        try:
            # Use existing functionality from parent class
            result = super().generate_document(deliverable_type, output_format, detail_level)
            
            # Create database record
            if result:
                generated_proposal = GeneratedProposal(
                    project_id=str(self.project.id),
                    template_id=None,  # No template used
                    deliverable_type=deliverable_type,
                    output_format=output_format,
                    generation_method='ai_only',
                    output_filename=result['filename'],
                    output_filepath=result['filepath'],
                    file_size=result.get('size', 0),
                    bookmark_content={},
                    generation_metadata={
                        'detail_level': detail_level,
                        'ai_model': 'claude-3-sonnet-20240229',
                        'include_company_info': include_company_info,
                        'generation_time': datetime.now().isoformat()
                    },
                    status='completed'
                )
                
                db.session.add(generated_proposal)
                db.session.commit()
                
                # Add additional metadata
                result.update({
                    'generation_method': 'ai_only',
                    'proposal_id': generated_proposal.proposal_id,
                    'template_used': None
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating AI-only proposal: {e}")
            return {
                'success': False,
                'error': str(e),
                'deliverable_type': deliverable_type
            }
    
    def generate_proposal_package(self,
                                deliverable_types: List[str],
                                template_preferences: Dict[str, int] = None,
                                output_format: str = 'docx',
                                detail_level: str = 'standard') -> Dict[str, Any]:
        """
        Generate multiple proposal documents as a package
        
        Args:
            deliverable_types: List of deliverable types to generate
            template_preferences: Template ID preferences for each deliverable type
            output_format: Default output format
            detail_level: Level of detail
            
        Returns:
            Dict with package generation results
        """
        try:
            package_results = {
                'success': True,
                'package_id': str(uuid.uuid4()),
                'documents': [],
                'errors': [],
                'total_documents': len(deliverable_types),
                'successful_documents': 0,
                'failed_documents': 0
            }
            
            for deliverable_type in deliverable_types:
                try:
                    # Check if template preference exists
                    template_id = None
                    if template_preferences and deliverable_type in template_preferences:
                        template_id = template_preferences[deliverable_type]
                    
                    # Generate document
                    if template_id:
                        result = self.generate_with_template(
                            template_id=template_id,
                            deliverable_type=deliverable_type,
                            detail_level=detail_level
                        )
                    else:
                        result = self.generate_without_template(
                            deliverable_type=deliverable_type,
                            output_format=output_format,
                            detail_level=detail_level
                        )
                    
                    if result.get('success'):
                        package_results['documents'].append({
                            'deliverable_type': deliverable_type,
                            'filename': result['filename'],
                            'size': result.get('size', 0),
                            'download_url': result.get('download_url'),
                            'generation_method': result.get('generation_method'),
                            'template_used': result.get('template_used')
                        })
                        package_results['successful_documents'] += 1
                    else:
                        package_results['errors'].append({
                            'deliverable_type': deliverable_type,
                            'error': result.get('error', 'Generation failed')
                        })
                        package_results['failed_documents'] += 1
                        
                except Exception as e:
                    package_results['errors'].append({
                        'deliverable_type': deliverable_type,
                        'error': str(e)
                    })
                    package_results['failed_documents'] += 1
            
            # Create package zip if multiple documents
            if len(package_results['documents']) > 1:
                package_results['package_zip'] = self._create_package_zip(
                    package_results['documents'], 
                    package_results['package_id']
                )
            
            # Overall success if at least one document was generated
            package_results['success'] = package_results['successful_documents'] > 0
            
            return package_results
            
        except Exception as e:
            logger.error(f"Error generating proposal package: {e}")
            return {
                'success': False,
                'error': str(e),
                'deliverable_types': deliverable_types
            }
    
    def _generate_all_bookmark_content(self,
                                     template: ProposalTemplate,
                                     deliverable_type: str,
                                     custom_content: Dict[str, Any],
                                     detail_level: str) -> Dict[str, Any]:
        """Generate AI content for all bookmarks in template"""
        
        bookmark_content = {}
        bookmarks = TemplateBookmark.query.filter_by(template_id=template.id).all()
        
        for bookmark in bookmarks:
            try:
                # Skip if custom content provided
                if bookmark.bookmark_name in custom_content:
                    continue
                
                # Generate content based on bookmark type
                if bookmark.content_type == 'ai_generated':
                    content = self._generate_ai_bookmark_content(bookmark, deliverable_type, detail_level)
                elif bookmark.content_type == 'dynamic':
                    content = self._generate_dynamic_bookmark_content(bookmark, deliverable_type)
                else:
                    content = bookmark.default_content or ''
                
                bookmark_content[bookmark.bookmark_name] = content
                
            except Exception as e:
                logger.error(f"Error generating content for bookmark {bookmark.bookmark_name}: {e}")
                bookmark_content[bookmark.bookmark_name] = bookmark.default_content or f'[{bookmark.display_name}]'
        
        return bookmark_content
    
    def _generate_ai_bookmark_content(self,
                                    bookmark: TemplateBookmark,
                                    deliverable_type: str,
                                    detail_level: str) -> str:
        """Generate AI content for a specific bookmark"""
        
        if not self.client:
            return bookmark.default_content or f'[AI content for {bookmark.display_name}]'
        
        try:
            # Use custom prompt if available, otherwise generate based on bookmark name
            if bookmark.ai_prompt_template:
                prompt_template = bookmark.ai_prompt_template
            else:
                prompt_template = self._generate_default_prompt_for_bookmark(bookmark, deliverable_type)
            
            # Format prompt with project data
            formatted_prompt = self._format_prompt_with_data(prompt_template, deliverable_type, detail_level)
            
            # Generate content with AI
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[{"role": "user", "content": formatted_prompt}]
            )
            
            content = response.content[0].text.strip()
            
            # Apply length limits if specified
            if bookmark.max_length and len(content) > bookmark.max_length:
                content = content[:bookmark.max_length] + '...'
            
            return content
            
        except Exception as e:
            logger.error(f"Error generating AI content for bookmark {bookmark.bookmark_name}: {e}")
            return bookmark.default_content or f'[AI content for {bookmark.display_name}]'
    
    def _generate_dynamic_bookmark_content(self,
                                         bookmark: TemplateBookmark,
                                         deliverable_type: str) -> str:
        """Generate dynamic content based on project and analysis data"""
        
        source = bookmark.content_source
        
        # Enhanced content mapping
        content_mapping = {
            'project_name': self.project.name,
            'project_description': getattr(self.project, 'description', ''),
            'client_name': self.client_name,
            'company_name': self.company_name,
            'contact_person': self.contact_person,
            'project_date': datetime.now().strftime('%B %d, %Y'),
            'current_date': datetime.now().strftime('%B %d, %Y'),
            'current_year': str(datetime.now().year),
            'deliverable_type': deliverable_type.title(),
            'requirements_summary': self._format_requirements_summary(),
            'technical_approach': self._format_technical_approach(),
            'project_timeline': self._format_project_timeline(),
            'cost_estimate': self._format_cost_estimate()
        }
        
        # Add company information from template
        if template.company_info:
            content_mapping.update(template.company_info)
        
        return content_mapping.get(source, bookmark.default_content or f'[{source}]')
    
    def _generate_default_prompt_for_bookmark(self, bookmark: TemplateBookmark, deliverable_type: str) -> str:
        """Generate default AI prompt based on bookmark name and context"""
        
        bookmark_name = bookmark.bookmark_name.lower()
        project_context = f"Project: {self.project.name} for client {self.client_name}"
        
        # Generate prompt based on common bookmark patterns
        if 'executive_summary' in bookmark_name or 'summary' in bookmark_name:
            return f"""Write an executive summary for a {deliverable_type} proposal.
            {project_context}
            
            Include: project overview, key benefits, recommended approach, and expected outcomes.
            Keep it concise and compelling for executive audience."""
        
        elif 'technical_approach' in bookmark_name or 'solution' in bookmark_name:
            return f"""Describe the technical approach and solution for a {deliverable_type} proposal.
            {project_context}
            
            Include: methodology, technologies, architecture, and implementation strategy.
            Be specific and demonstrate technical expertise."""
        
        elif 'timeline' in bookmark_name or 'schedule' in bookmark_name:
            return f"""Create a project timeline and schedule for a {deliverable_type} proposal.
            {project_context}
            
            Include: project phases, key milestones, deliverables, and estimated duration.
            Present in a clear, structured format."""
        
        elif 'team' in bookmark_name or 'resource' in bookmark_name:
            return f"""Describe the project team and resources for a {deliverable_type} proposal.
            {project_context}
            
            Include: team composition, key roles, expertise areas, and resource allocation.
            Highlight relevant experience and qualifications."""
        
        elif 'risk' in bookmark_name or 'mitigation' in bookmark_name:
            return f"""Identify risks and mitigation strategies for a {deliverable_type} proposal.
            {project_context}
            
            Include: potential risks, impact assessment, mitigation strategies, and contingency plans.
            Be realistic and demonstrate proactive planning."""
        
        else:
            return f"""Generate professional content for '{bookmark.display_name}' section of a {deliverable_type} proposal.
            {project_context}
            
            Provide relevant, specific, and well-structured content appropriate for this section."""
    
    def _format_prompt_with_data(self, prompt_template: str, deliverable_type: str, detail_level: str) -> str:
        """Format prompt template with project and analysis data"""
        
        # Prepare data for template substitution
        template_data = {
            'project_name': self.project.name,
            'client_name': self.client_name,
            'company_name': self.company_name,
            'deliverable_type': deliverable_type,
            'detail_level': detail_level,
            'requirements': self._format_requirements(),
            'analysis_summary': self._format_analysis_summary(),
            'constraints': self._format_constraints()
        }
        
        # Replace placeholders in template
        formatted_prompt = prompt_template
        for key, value in template_data.items():
            placeholder = '{' + key + '}'
            if placeholder in formatted_prompt:
                formatted_prompt = formatted_prompt.replace(placeholder, str(value))
        
        return formatted_prompt
    
    def _format_requirements_summary(self) -> str:
        """Format project requirements summary"""
        try:
            if hasattr(self.analysis_results, 'get'):
                requirements = self.analysis_results.get('must_have_requirements', [])
                if requirements:
                    return '\n'.join([f"• {req}" for req in requirements[:5]])
            return "Requirements analysis available in project documentation."
        except:
            return "Requirements to be defined during project initiation."
    
    def _format_technical_approach(self) -> str:
        """Format technical approach summary"""
        try:
            if hasattr(self.analysis_results, 'get'):
                approach = self.analysis_results.get('recommended_approach', '')
                if approach:
                    return approach
            return "Technical approach will be tailored based on detailed requirements analysis."
        except:
            return "Technical approach to be developed during project planning phase."
    
    def _format_project_timeline(self) -> str:
        """Format project timeline estimate"""
        return """
        Phase 1: Requirements Analysis & Planning (2-3 weeks)
        Phase 2: Design & Architecture (3-4 weeks)  
        Phase 3: Development & Implementation (8-12 weeks)
        Phase 4: Testing & Quality Assurance (2-3 weeks)
        Phase 5: Deployment & Go-Live (1-2 weeks)
        """
    
    def _format_cost_estimate(self) -> str:
        """Format cost estimate"""
        return "Cost estimate to be provided based on detailed requirements and scope definition."
    
    def _create_package_zip(self, documents: List[Dict], package_id: str) -> Dict[str, Any]:
        """Create ZIP package of multiple documents"""
        try:
            import zipfile
            
            zip_filename = f"proposal_package_{package_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            zip_path = os.path.join(self.output_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for doc in documents:
                    file_path = os.path.join(self.output_dir, doc['filename'])
                    if os.path.exists(file_path):
                        zip_file.write(file_path, doc['filename'])
            
            return {
                'filename': zip_filename,
                'filepath': zip_path,
                'size': os.path.getsize(zip_path),
                'download_url': f'/download-proposal/{zip_filename}'
            }
            
        except Exception as e:
            logger.error(f"Error creating package ZIP: {e}")
            return None
    
    def update_company_info(self, company_info: Dict[str, Any]):
        """Update company information for proposal generation"""
        self.company_info.update(company_info)
    
    def get_available_templates(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available templates for proposal generation"""
        try:
            query = ProposalTemplate.query.filter_by(is_active=True)
            if category:
                query = query.filter_by(category=category)
            
            templates = query.all()
            return [template.to_dict() for template in templates]
            
        except Exception as e:
            logger.error(f"Error getting available templates: {e}")
            return []

# Factory function
def create_enhanced_proposal_generator(project, analysis_results=None, company_name="Your Company", contact_person="Project Manager") -> EnhancedProposalGenerator:
    """Create an enhanced proposal generator instance"""
    
    # Get analysis results if not provided
    if analysis_results is None:
        try:
            analysis_results = get_real_analysis_results(project.id)
        except Exception as e:
            logger.warning(f"Could not load analysis results for project {project.id}: {e}")
            analysis_results = {}
    
    return EnhancedProposalGenerator(project, analysis_results, company_name, contact_person)