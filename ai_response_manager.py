"""
AI Response Manager
Handles storage, retrieval, and management of all AI interactions
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from models import db, AIResponse, Project

class AIResponseManager:
    """Manages AI responses with storage, history, and rerun functionality"""
    
    @staticmethod
    def create_response(
        project_id: str,
        request_type: str,
        prompt: str,
        ai_provider: str,
        ai_model: str,
        context_data: Dict = None,
        parent_response_id: str = None,
        rerun_reason: str = None
    ) -> AIResponse:
        """Create a new AI response record"""
        
        try:
            response = AIResponse(
                project_id=project_id,
                request_type=request_type,
                prompt_used=prompt,
                context_data=context_data or {},
                ai_provider=ai_provider,
                ai_model=ai_model,
                parent_response_id=parent_response_id,
                rerun_reason=rerun_reason,
                status='processing'
            )
            
            db.session.add(response)
            db.session.commit()
            
            return response
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def complete_response(
        response: AIResponse,
        raw_response: str,
        parsed_response: Dict = None,
        confidence_score: float = None,
        metadata: Dict = None
    ) -> AIResponse:
        """Mark response as completed and store results"""
        
        try:
            response.raw_response = raw_response
            response.parsed_response = parsed_response
            response.confidence_score = confidence_score
            response.response_metadata = metadata or {}
            response.status = 'completed'
            response.updated_at = datetime.utcnow()
            
            db.session.commit()
            return response
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def fail_response(
        response: AIResponse,
        error_message: str,
        partial_response: str = None
    ) -> AIResponse:
        """Mark response as failed with error details"""
        
        try:
            response.status = 'failed'
            response.error_message = error_message
            if partial_response:
                response.raw_response = partial_response
                response.status = 'partial'
            response.updated_at = datetime.utcnow()
            
            db.session.commit()
            return response
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_project_responses(
        project_id: str,
        request_type: str = None,
        include_archived: bool = False,
        limit: int = None
    ) -> List[AIResponse]:
        """Get AI responses for a project"""
        
        query = AIResponse.query.filter_by(project_id=project_id)
        
        if request_type:
            query = query.filter_by(request_type=request_type)
        
        if not include_archived:
            query = query.filter_by(is_archived=False)
        
        query = query.order_by(AIResponse.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_response_by_id(response_id: str) -> Optional[AIResponse]:
        """Get a specific response by ID"""
        return AIResponse.query.filter_by(response_id=response_id).first()
    
    @staticmethod
    def get_latest_response(
        project_id: str,
        request_type: str,
        status: str = 'completed'
    ) -> Optional[AIResponse]:
        """Get the most recent response of a specific type"""
        
        return AIResponse.query.filter_by(
            project_id=project_id,
            request_type=request_type,
            status=status
        ).order_by(AIResponse.created_at.desc()).first()
    
    @staticmethod
    def create_rerun(
        original_response_id: str,
        reason: str = None
    ) -> Optional[AIResponse]:
        """Create a rerun of an existing response"""
        
        original = AIResponseManager.get_response_by_id(original_response_id)
        if not original:
            return None
        
        rerun = original.create_rerun(reason)
        db.session.add(rerun)
        db.session.commit()
        
        return rerun
    
    @staticmethod
    def get_response_history(
        project_id: str,
        request_type: str = None,
        group_by_family: bool = True
    ) -> List[Dict[str, Any]]:
        """Get response history with family grouping"""
        
        responses = AIResponseManager.get_project_responses(project_id, request_type)
        
        if not group_by_family:
            return [r.to_dict() for r in responses]
        
        # Group responses into families (parent + children)
        families = {}
        orphans = []
        
        for response in responses:
            if response.parent_response_id:
                # This is a child response
                if response.parent_response_id not in families:
                    families[response.parent_response_id] = {
                        'parent': None,
                        'children': []
                    }
                families[response.parent_response_id]['children'].append(response.to_dict())
            else:
                # This is a parent or standalone response
                if response.response_id not in families:
                    families[response.response_id] = {
                        'parent': response.to_dict(),
                        'children': []
                    }
                else:
                    families[response.response_id]['parent'] = response.to_dict()
                    
                # Check if this is truly standalone
                children = response.get_child_responses()
                if not children:
                    orphans.append(response.to_dict())
        
        # Convert families to list format
        family_list = []
        for family_id, family in families.items():
            if family['parent']:  # Only include families with parents
                family_list.append(family)
        
        return family_list + [{'parent': r, 'children': []} for r in orphans]
    
    @staticmethod
    def get_response_stats(project_id: str) -> Dict[str, Any]:
        """Get statistics about AI responses for a project"""
        
        responses = AIResponse.query.filter_by(project_id=project_id).all()
        
        if not responses:
            return {
                'total_responses': 0,
                'by_type': {},
                'by_provider': {},
                'by_status': {},
                'average_rating': None,
                'total_views': 0,
                'favorites': 0
            }
        
        stats = {
            'total_responses': len(responses),
            'by_type': {},
            'by_provider': {},
            'by_status': {},
            'total_views': sum(r.view_count for r in responses),
            'favorites': sum(1 for r in responses if r.is_favorite)
        }
        
        # Count by request type
        for response in responses:
            stats['by_type'][response.request_type] = stats['by_type'].get(response.request_type, 0) + 1
            stats['by_provider'][response.ai_provider] = stats['by_provider'].get(response.ai_provider, 0) + 1
            stats['by_status'][response.status] = stats['by_status'].get(response.status, 0) + 1
        
        # Calculate average rating
        rated_responses = [r for r in responses if r.human_rating]
        if rated_responses:
            stats['average_rating'] = sum(r.human_rating for r in rated_responses) / len(rated_responses)
        else:
            stats['average_rating'] = None
        
        return stats

    @staticmethod
    def archive_response(response_id: str, archive: bool = True) -> bool:
        """Archive or unarchive a response"""
        response = AIResponseManager.get_response_by_id(response_id)
        if not response:
            return False
            
        response.is_archived = archive
        response.updated_at = datetime.utcnow()
        db.session.commit()
        
        return True
    
    @staticmethod
    def toggle_favorite(response_id: str) -> bool:
        """Toggle favorite status of a response"""
        response = AIResponseManager.get_response_by_id(response_id)
        if not response:
            return False
            
        response.is_favorite = not response.is_favorite
        response.updated_at = datetime.utcnow()
        db.session.commit()
        
        return response.is_favorite

# Helper function for AI providers to use
def store_ai_response(
    project_id: str,
    request_type: str,
    prompt: str,
    ai_provider: str,
    ai_model: str,
    raw_response: str,
    parsed_response: Dict = None,
    context_data: Dict = None,
    confidence_score: float = None,
    metadata: Dict = None,
    parent_response_id: str = None,
    rerun_reason: str = None
) -> AIResponse:
    """Convenience function to store a complete AI response in one call"""
    
    # Create response record
    response = AIResponseManager.create_response(
        project_id=project_id,
        request_type=request_type,
        prompt=prompt,
        ai_provider=ai_provider,
        ai_model=ai_model,
        context_data=context_data,
        parent_response_id=parent_response_id,
        rerun_reason=rerun_reason
    )
    
    # Complete it with results
    return AIResponseManager.complete_response(
        response=response,
        raw_response=raw_response,
        parsed_response=parsed_response,
        confidence_score=confidence_score,
        metadata=metadata
    )