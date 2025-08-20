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
from vector_store import get_vector_store
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
    vector_stored = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
    
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
            'vector_stored': self.vector_stored,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }

class ProposalManager:
    """Service for managing past proposals"""
    
    def __init__(self):
        self.vector_store = get_vector_store()
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
                technologies_used=metadata.get('technologies_used', []),
                industry_sector=metadata.get('industry_sector'),
                project_duration=metadata.get('project_duration'),
                team_size=metadata.get('team_size'),
                actual_value=metadata.get('actual_value'),
                lessons_learned=metadata.get('lessons_learned'),
                key_success_factors=metadata.get('key_success_factors', []),
                key_challenges=metadata.get('key_challenges', []),
                processing_status='processed' if extracted_content else 'failed',
                error_message=extraction_error,
                uploaded_by=user_id
            )
            
            db.session.add(proposal)
            db.session.commit()
            
            # Add to vector store if content was extracted
            vector_success = False
            if extracted_content and self.vector_store:
                vector_metadata = {
                    "proposal_id": proposal.proposal_id,
                    "title": proposal.title,
                    "client_name": proposal.client_name,
                    "project_type": proposal.project_type,
                    "submission_year": proposal.submission_year,
                    "status": proposal.status,
                    "technologies": proposal.technologies_used,
                    "industry_sector": proposal.industry_sector,
                    "proposal_value": proposal.proposal_value
                }
                
                vector_success = self.vector_store.add_proposal_document(
                    content=extracted_content,
                    metadata=vector_metadata,
                    document_type=proposal.proposal_type
                )
                
                if vector_success:
                    proposal.vector_stored = True
                    proposal.processed_at = datetime.utcnow()
                    db.session.commit()
            
            result = {
                'success': True,
                'proposal_id': proposal.proposal_id,
                'extracted_length': len(extracted_content) if extracted_content else 0,
                'vector_stored': vector_success,
                'processing_status': proposal.processing_status,
                'message': f'Proposal uploaded and processed successfully' if extracted_content else f'Proposal uploaded but processing failed: {extraction_error}'
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
        """Get proposals similar to query"""
        try:
            if not self.vector_store:
                return []
            
            # Search vector store
            similar_docs = self.vector_store.search_similar_proposals(
                query=query,
                k=limit,
                filter_metadata=filters
            )
            
            # Get proposal IDs from results
            proposal_ids = [doc['metadata'].get('proposal_id') for doc in similar_docs if doc['metadata'].get('proposal_id')]
            
            # Get full proposal data from database
            proposals = PastProposal.query.filter(PastProposal.proposal_id.in_(proposal_ids)).all()
            proposal_dict = {p.proposal_id: p for p in proposals}
            
            # Combine vector results with database data
            results = []
            for doc in similar_docs:
                proposal_id = doc['metadata'].get('proposal_id')
                if proposal_id and proposal_id in proposal_dict:
                    proposal = proposal_dict[proposal_id]
                    result = proposal.to_dict()
                    result.update({
                        'similarity_score': doc['similarity_score'],
                        'matching_content': doc['content'][:300] + '...' if len(doc['content']) > 300 else doc['content'],
                        'relevance': doc['relevance']
                    })
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting similar proposals: {e}")
            return []
    
    def get_context_for_new_proposal(self, 
                                   requirements: List[str],
                                   project_metadata: Dict = None) -> Dict[str, Any]:
        """
        Get relevant context from past proposals for a new proposal
        
        Args:
            requirements: Requirements from new RFP
            project_metadata: Current project information
        
        Returns:
            Context dictionary with relevant past proposals and insights
        """
        try:
            if not self.vector_store:
                return {"error": "Vector store not available"}
            
            # Get context from vector store
            context = self.vector_store.get_context_for_analysis(
                requirements=requirements,
                project_metadata=project_metadata
            )
            
            # Enhance with database information
            if context.get('relevant_proposals'):
                proposal_ids = [p['metadata'].get('proposal_id') for p in context['relevant_proposals']]
                proposals = PastProposal.query.filter(
                    PastProposal.proposal_id.in_(proposal_ids)
                ).all()
                
                # Add success metrics
                won_proposals = [p for p in proposals if p.status == 'won']
                if won_proposals:
                    avg_win_value = sum(p.actual_value or p.proposal_value or 0 for p in won_proposals) / len(won_proposals)
                    context['success_metrics'] = {
                        'similar_won_proposals': len(won_proposals),
                        'average_win_value': avg_win_value,
                        'win_rate': len(won_proposals) / len(proposals) if proposals else 0,
                        'key_success_factors': [factor for p in won_proposals for factor in (p.key_success_factors or [])]
                    }
            
            # Add industry insights
            if project_metadata and project_metadata.get('industry_sector'):
                industry_proposals = PastProposal.query.filter(
                    PastProposal.industry_sector == project_metadata['industry_sector'],
                    PastProposal.status == 'won'
                ).limit(5).all()
                
                context['industry_insights'] = {
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
            vector_stored = PastProposal.query.filter(
                PastProposal.vector_stored == True
            ).count()
            
            won_proposals = PastProposal.query.filter(
                PastProposal.status == 'won'
            ).count()
            
            # Get vector store stats
            vector_stats = {}
            if self.vector_store:
                vector_stats = self.vector_store.get_collection_stats()
            
            return {
                'total_proposals': total_proposals,
                'processed_proposals': processed_proposals,
                'vector_stored': vector_stored,
                'won_proposals': won_proposals,
                'win_rate': won_proposals / total_proposals if total_proposals > 0 else 0,
                'vector_store_stats': vector_stats,
                'processing_success_rate': processed_proposals / total_proposals if total_proposals > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting proposal statistics: {e}")
            return {"error": str(e)}

# Singleton instance
proposal_manager_instance = None

def get_proposal_manager() -> ProposalManager:
    """Get or create proposal manager instance"""
    global proposal_manager_instance
    if proposal_manager_instance is None:
        proposal_manager_instance = ProposalManager()
    return proposal_manager_instance