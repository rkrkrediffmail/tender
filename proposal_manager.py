"""
Proposal Manager Service
Handles uploading, processing, and managing past tender proposals
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from models import db
from claude_proposal_analyzer import ClaudeProposalAnalyzer
from claude_vector_intelligence import get_claude_vector_intelligence
from document_processor import DocumentProcessor
import uuid

logger = logging.getLogger(__name__)

# Database model for past proposals metadata
class PastProposal(db.Model):
    """Model for storing past proposal metadata"""
    __tablename__ = 'past_proposals'
    
    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Basic Information
    title = db.Column(db.String(500), nullable=False)
    client_name = db.Column(db.String(255), nullable=False)
    project_type = db.Column(db.String(100))  # infrastructure, software, consulting, etc.
    proposal_type = db.Column(db.String(50), nullable=False)  # technical, commercial, combined
    
    # File Information
    filename = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(500), nullable=False)
    file_path = db.Column(db.String(1000))
    file_size = db.Column(db.Integer)
    extracted_content = db.Column(db.Text)
    
    # Proposal Details
    submission_year = db.Column(db.Integer)
    proposal_value = db.Column(db.Float)  # In USD
    currency = db.Column(db.String(10), default='USD')
    status = db.Column(db.String(50))  # won, lost, pending, cancelled
    win_probability = db.Column(db.Float)  # 0.0 to 1.0
    
    # Technical Information
    technologies_used = db.Column(db.JSON, default=[])  # List of technologies
    industry_sector = db.Column(db.String(100))  # healthcare, finance, government, etc.
    project_duration = db.Column(db.String(50))  # "6 months", "2 years", etc.
    team_size = db.Column(db.Integer)
    
    # Outcome Information
    actual_value = db.Column(db.Float)  # Actual contract value if won
    lessons_learned = db.Column(db.Text)
    key_success_factors = db.Column(db.JSON, default=[])
    key_challenges = db.Column(db.JSON, default=[])
    
    # Processing Information
    processing_status = db.Column(db.String(50), default='pending')  # pending, processed, failed
    claude_analyzed = db.Column(db.Boolean, default=False)
    vector_stored = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
    
    # Claude Analysis Results
    extracted_capabilities = db.Column(db.JSON, default=list)
    extracted_technologies = db.Column(db.JSON, default=list)
    company_experience = db.Column(db.JSON, default=list)
    solution_approaches = db.Column(db.JSON, default=list)
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'proposal_id': self.proposal_id,
            'title': self.title,
            'client_name': self.client_name,
            'project_type': self.project_type,
            'proposal_type': self.proposal_type,
            'submission_year': self.submission_year,
            'proposal_value': self.proposal_value,
            'currency': self.currency,
            'status': self.status,
            'technologies_used': self.technologies_used,
            'industry_sector': self.industry_sector,
            'processing_status': self.processing_status,
            'claude_analyzed': self.claude_analyzed,
            'vector_stored': self.vector_stored,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }

class ProposalManager:
    """Service for managing past proposals"""
    
    def __init__(self):
        self.claude_analyzer = ClaudeProposalAnalyzer()
        self.claude_vector_intelligence = get_claude_vector_intelligence()
        self.document_processor = None
        self._init_document_processor()
    
    def _init_document_processor(self):
        """Initialize document processor"""
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.document_processor = DocumentProcessor(api_key)
                logger.info("Document processor initialized for proposal manager")
            else:
                logger.warning("No API key available for document processor")
        except Exception as e:
            logger.error(f"Failed to initialize document processor: {e}")
    
    def upload_past_proposal(self, 
                           file_path: str,
                           filename: str,
                           metadata: Dict[str, Any],
                           user_id: int) -> Dict[str, Any]:
        """
        Upload and process a past proposal document
        
        Args:
            file_path: Path to uploaded file
            filename: Original filename
            metadata: Proposal metadata
            user_id: User who uploaded the proposal
        
        Returns:
            Dict with processing results
        """
        try:
            # Extract text content
            extracted_content = ""
            extraction_error = None
            
            if self.document_processor:
                try:
                    # Determine file type and extract
                    file_extension = filename.lower().split('.')[-1]
                    if file_extension == 'pdf':
                        extracted_content = self.document_processor.extract_text_from_pdf(file_path)
                    elif file_extension in ['docx', 'doc']:
                        extracted_content = self.document_processor.extract_text_from_docx(file_path)
                    elif file_extension == 'txt':
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            extracted_content = f.read()
                    else:
                        extraction_error = f"Unsupported file type: {file_extension}"
                        
                except Exception as e:
                    extraction_error = f"Text extraction failed: {str(e)}"
            else:
                extraction_error = "Document processor not available"
            
            # Full Claude + Vector Intelligence Processing
            intelligence_results = {}
            if extracted_content:
                try:
                    # Use the advanced Claude Vector Intelligence system
                    intelligence_results = self.claude_vector_intelligence.process_past_proposal(
                        content=extracted_content, 
                        metadata=metadata
                    )
                    print(f"Claude Vector Intelligence processing: {intelligence_results.get('chunks_stored', 0)} chunks stored")
                except Exception as e:
                    print(f"Claude Vector Intelligence failed: {e}")
                    # Fallback to basic Claude analysis
                    try:
                        claude_analysis = self.claude_analyzer.analyze_proposal(extracted_content, metadata)
                        intelligence_results = {
                            'success': bool(claude_analysis),
                            'claude_analysis': claude_analysis,
                            'vector_storage_success': False,
                            'chunks_stored': 0
                        }
                    except Exception as e2:
                        print(f"Fallback Claude analysis also failed: {e2}")
                        intelligence_results = {'success': False, 'error': str(e2)}
            
            # Create database record
            proposal = PastProposal(
                title=metadata.get('title', filename),
                client_name=metadata.get('client_name', 'Unknown'),
                project_type=metadata.get('project_type', 'unknown'),
                proposal_type=metadata.get('proposal_type', 'technical'),
                filename=os.path.basename(file_path),
                original_filename=filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                extracted_content=extracted_content,
                submission_year=metadata.get('submission_year'),
                proposal_value=metadata.get('proposal_value'),
                currency=metadata.get('currency', 'USD'),
                status=metadata.get('status', 'unknown'),
                win_probability=metadata.get('win_probability'),
                technologies_used=claude_analysis.get('technologies', metadata.get('technologies_used', [])),
                industry_sector=metadata.get('industry_sector'),
                project_duration=metadata.get('project_duration'),
                team_size=metadata.get('team_size'),
                actual_value=metadata.get('actual_value'),
                lessons_learned=metadata.get('lessons_learned'),
                key_success_factors=metadata.get('key_success_factors', []),
                key_challenges=metadata.get('key_challenges', []),
                processing_status='processed' if extracted_content else 'failed',
                error_message=extraction_error,
                uploaded_by=user_id,
                claude_analyzed=intelligence_results.get('success', False),
                extracted_capabilities=intelligence_results.get('claude_analysis', {}).get('core_capabilities_demonstrated', []),
                extracted_technologies=intelligence_results.get('claude_analysis', {}).get('technologies_and_platforms', []),
                company_experience=intelligence_results.get('claude_analysis', {}).get('industry_specific_expertise', []),
                solution_approaches=intelligence_results.get('claude_analysis', {}).get('solution_architecture_patterns', [])
            )
            
            db.session.add(proposal)
            db.session.commit()
            
            # Store vector storage success info
            proposal.vector_stored = intelligence_results.get('vector_storage_success', False)
            
            # Commit the proposal to database
            if proposal.claude_analyzed:
                proposal.processed_at = datetime.utcnow()
            db.session.commit()
            
            result = {
                'success': True,
                'proposal_id': proposal.proposal_id,
                'extracted_length': len(extracted_content) if extracted_content else 0,
                'claude_analyzed': proposal.claude_analyzed,
                'vector_stored': intelligence_results.get('vector_storage_success', False),
                'processing_status': proposal.processing_status,
                'chunks_stored': intelligence_results.get('chunks_stored', 0),
                'capabilities_found': len(intelligence_results.get('claude_analysis', {}).get('core_capabilities_demonstrated', [])),
                'intelligence_score': intelligence_results.get('claude_analysis', {}).get('intelligence_score', 0.0),
                'message': f'Proposal uploaded, analyzed, and {intelligence_results.get("chunks_stored", 0)} chunks stored in vector DB' if extracted_content else f'Proposal uploaded but processing failed: {extraction_error}'
            }
            
            logger.info(f"Uploaded proposal: {filename} - {result['message']}")
            return result
            
        except Exception as e:
            logger.error(f"Error uploading proposal {filename}: {e}")
            db.session.rollback()
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to upload proposal: {str(e)}'
            }
    
    def get_proposals_by_similarity(self, 
                                  query: str, 
                                  limit: int = 10,
                                  filters: Optional[Dict] = None) -> List[Dict]:
        """Get proposals similar to query using Claude Vector Intelligence"""
        try:
            # Use the advanced Claude Vector Intelligence system
            results = self.claude_vector_intelligence.intelligent_similarity_search(
                query=query,
                filters=filters,
                limit=limit
            )
            
            # Convert vector results to proposal format
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'title': result.get('metadata', {}).get('title', ''),
                    'client_name': result.get('metadata', {}).get('client_name', ''),
                    'project_type': result.get('metadata', {}).get('project_type', ''),
                    'industry_sector': result.get('metadata', {}).get('industry_sector', ''),
                    'submission_year': result.get('metadata', {}).get('submission_year'),
                    'status': result.get('metadata', {}).get('status', ''),
                    'similarity_score': result.get('similarity_score', 0),
                    'intelligence_score': result.get('intelligence_score', 0),
                    'matching_content': result.get('content', '')[:300] + '...' if len(result.get('content', '')) > 300 else result.get('content', ''),
                    'relevance_explanation': result.get('relevance_explanation', ''),
                    'recommended_usage': result.get('recommended_usage', ''),
                    'key_insights': result.get('key_insights', []),
                    'chunk_type': result.get('metadata', {}).get('chunk_type', ''),
                    'proposal_id': result.get('metadata', {}).get('proposal_id', '')
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error getting similar proposals: {e}")
            return []
    
    def get_context_for_new_proposal(self, 
                                   requirements: List[str],
                                   project_metadata: Dict = None) -> Dict[str, Any]:
        """
        Get intelligent context from past proposals using Claude Vector Intelligence
        
        Args:
            requirements: Requirements from new RFP
            project_metadata: Current project information
        
        Returns:
            Context dictionary with intelligent past proposal insights
        """
        try:
            # Use the advanced Claude Vector Intelligence system
            context = self.claude_vector_intelligence.get_intelligent_context_for_agents(
                requirements=requirements,
                project_metadata=project_metadata or {}
            )
            
            # Add database statistics for additional context
            if project_metadata and project_metadata.get('industry_sector'):
                industry_proposals = PastProposal.query.filter(
                    PastProposal.industry_sector == project_metadata['industry_sector'],
                    PastProposal.status == 'won'
                ).limit(5).all()
                
                context['database_insights'] = {
                    'similar_industry_wins': len(industry_proposals),
                    'common_technologies': self._extract_common_technologies(industry_proposals),
                    'typical_duration': self._get_typical_duration(industry_proposals),
                    'average_team_size': sum(p.team_size or 0 for p in industry_proposals) / len(industry_proposals) if industry_proposals else 0
                }
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting context for new proposal: {e}")
            return {"error": str(e)}
    
    def _extract_common_technologies(self, proposals: List[PastProposal]) -> List[str]:
        """Extract commonly used technologies from proposals"""
        try:
            tech_count = {}
            for proposal in proposals:
                if proposal.technologies_used:
                    for tech in proposal.technologies_used:
                        tech_count[tech] = tech_count.get(tech, 0) + 1
            
            # Return top 5 most common technologies
            return sorted(tech_count.items(), key=lambda x: x[1], reverse=True)[:5]
        except:
            return []
    
    def _get_typical_duration(self, proposals: List[PastProposal]) -> str:
        """Get typical project duration"""
        try:
            durations = [p.project_duration for p in proposals if p.project_duration]
            if durations:
                # Simple mode calculation
                duration_count = {}
                for duration in durations:
                    duration_count[duration] = duration_count.get(duration, 0) + 1
                return max(duration_count.items(), key=lambda x: x[1])[0]
            return "Unknown"
        except:
            return "Unknown"
    
    def get_all_proposals(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get all past proposals with pagination"""
        try:
            proposals = PastProposal.query.order_by(
                PastProposal.uploaded_at.desc()
            ).limit(limit).offset(offset).all()
            
            return [p.to_dict() for p in proposals]
            
        except Exception as e:
            logger.error(f"Error getting all proposals: {e}")
            return []
    
    def get_proposal_statistics(self) -> Dict[str, Any]:
        """Get statistics about past proposals"""
        try:
            total_proposals = PastProposal.query.count()
            processed_proposals = PastProposal.query.filter(
                PastProposal.processing_status == 'processed'
            ).count()
            claude_analyzed = PastProposal.query.filter(
                PastProposal.claude_analyzed == True
            ).count()
            
            vector_stored = PastProposal.query.filter(
                PastProposal.vector_stored == True
            ).count()
            
            won_proposals = PastProposal.query.filter(
                PastProposal.status == 'won'
            ).count()
            
            # Get capabilities stats
            capabilities_extracted = PastProposal.query.filter(
                PastProposal.extracted_capabilities != None,
                PastProposal.extracted_capabilities != []
            ).count()
            
            return {
                'total_proposals': total_proposals,
                'processed_proposals': processed_proposals,
                'claude_analyzed': claude_analyzed,
                'vector_stored': vector_stored,
                'capabilities_extracted': capabilities_extracted,
                'won_proposals': won_proposals,
                'win_rate': won_proposals / total_proposals if total_proposals > 0 else 0,
                'processing_success_rate': processed_proposals / total_proposals if total_proposals > 0 else 0,
                'analysis_success_rate': claude_analyzed / total_proposals if total_proposals > 0 else 0,
                'vector_storage_rate': vector_stored / total_proposals if total_proposals > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting proposal statistics: {e}")
            return {"error": str(e)}
    
    def get_relevant_past_proposals(self, analysis_results: Dict[str, Any], proposal_type: str = "technical", limit: int = 10) -> Dict[str, Any]:
        """
        Automatically retrieve relevant past proposals using Claude Vector Intelligence
        This is the main intelligence function for agent-driven proposal generation
        """
        try:
            logger.info(f"Getting relevant past proposals for {proposal_type} proposal using Claude Vector Intelligence")
            
            # Extract requirements from analysis results for intelligent search
            requirements = []
            if isinstance(analysis_results, dict):
                requirements.extend(analysis_results.get('must_have_requirements', []))
                requirements.extend(analysis_results.get('technical_specifications', []))
                requirements.extend(analysis_results.get('good_to_have_requirements', []))
            
            # Project metadata for context
            project_metadata = {
                'project_type': analysis_results.get('project_type', proposal_type),
                'industry_sector': analysis_results.get('industry_sector', 'bfsi')
            }
            
            # Use Claude Vector Intelligence to get comprehensive context
            intelligence_context = self.claude_vector_intelligence.get_intelligent_context_for_agents(
                requirements=requirements[:10],  # Limit for performance
                project_metadata=project_metadata
            )
            
            # Transform into expected format for proposal generation
            if intelligence_context.get('success'):
                return {
                    'success': True,
                    'found_proposals': intelligence_context.get('sources_analyzed', 0),
                    'reusable_content': intelligence_context.get('reusable_content_sections', {}),
                    'capability_intelligence': intelligence_context.get('capability_intelligence', {}),
                    'generation_guidance': intelligence_context.get('generation_guidance', {}),
                    'confidence_score': intelligence_context.get('executive_intelligence', {}).get('confidence_level', 0.5),
                    'agent_instructions': intelligence_context.get('usage_instructions_for_agents', {}),
                    'gap_analysis': intelligence_context.get('gap_analysis', {}),
                    'intelligence_timestamp': intelligence_context.get('synthesis_timestamp')
                }
            else:
                return {'success': False, 'error': intelligence_context.get('error', 'Unknown error')}
            
        except Exception as e:
            logger.error(f"Error getting relevant past proposals: {e}")
            return {'success': False, 'error': str(e)}
    
    # Helper methods that are no longer needed with Claude analyzer
    # Kept for backward compatibility if any routes still call them

# Singleton instance
proposal_manager_instance = None

def get_proposal_manager() -> ProposalManager:
    """Get or create proposal manager instance"""
    global proposal_manager_instance
    if proposal_manager_instance is None:
        proposal_manager_instance = ProposalManager()
    return proposal_manager_instance