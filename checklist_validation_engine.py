#!/usr/bin/env python3
"""
Checklist Validation Engine - AI-powered RFP validation against checklist templates
"""

import os
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from models import (
    db, Project, Document, RFPChecklistTemplate, ChecklistItem,
    RFPChecklistValidation, ChecklistItemValidation, ClarificationRequest
)

logger = logging.getLogger(__name__)

class ChecklistValidationEngine:
    """
    AI-powered engine to validate RFP documents against checklist templates
    """
    
    def __init__(self):
        """Initialize the validation engine"""
        self.anthropic_client = None
        
        # Initialize Anthropic client if available
        if ANTHROPIC_AVAILABLE:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.anthropic_client = anthropic.Anthropic(api_key=api_key)
                logger.info("Anthropic client initialized for checklist validation")
            else:
                logger.warning("ANTHROPIC_API_KEY not found - AI validation disabled")
        else:
            logger.warning("Anthropic library not available - AI validation disabled")
        
        # Validation parameters
        self.batch_size = 10  # Process items in batches
        self.timeout_seconds = 300  # 5 minutes per batch
        self.max_content_length = 50000  # Maximum content length per analysis
    
    def validate_rfp_against_checklist(self, 
                                     project_id: str, 
                                     checklist_template_id: str,
                                     user_id: int) -> Dict[str, Any]:
        """
        Main validation function - validate an RFP project against a checklist template
        
        Args:
            project_id: ID of the project to validate
            checklist_template_id: ID of the checklist template
            user_id: ID of user performing validation
            
        Returns:
            Dict with validation results
        """
        start_time = time.time()
        
        try:
            # Load project and documents
            project = Project.query.get(project_id)
            if not project:
                return {'success': False, 'error': 'Project not found'}
            
            documents = Document.query.filter_by(project_id=project_id).all()
            if not documents:
                return {'success': False, 'error': 'No documents found in project'}
            
            # Load checklist template
            template = RFPChecklistTemplate.query.filter_by(checklist_id=checklist_template_id).first()
            if not template:
                return {'success': False, 'error': 'Checklist template not found'}
            
            # Load checklist items
            checklist_items = ChecklistItem.query.filter_by(checklist_id=checklist_template_id, is_active=True).all()
            if not checklist_items:
                return {'success': False, 'error': 'No active checklist items found'}
            
            # Combine all document content
            combined_content = self._combine_document_content(documents)
            if not combined_content.strip():
                return {'success': False, 'error': 'No content extracted from documents'}
            
            # Create validation record
            validation = RFPChecklistValidation(
                project_id=project_id,
                checklist_id=checklist_template_id,
                total_items=len(checklist_items),
                status='processing',
                validated_by=user_id,
                ai_model_used='claude-sonnet-4-20250514'
            )
            
            db.session.add(validation)
            db.session.commit()
            
            logger.info(f"Starting validation for project {project_id} with {len(checklist_items)} items")
            
            # Process checklist items in batches
            validation_results = []
            clarifications_needed = []
            total_tokens = 0
            
            for batch_start in range(0, len(checklist_items), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(checklist_items))
                batch_items = checklist_items[batch_start:batch_end]
                
                logger.info(f"Processing batch {batch_start // self.batch_size + 1}: items {batch_start + 1}-{batch_end}")
                
                # Validate batch
                batch_results = self._validate_item_batch(
                    batch_items, combined_content, validation.validation_id, project_id
                )
                
                validation_results.extend(batch_results['results'])
                clarifications_needed.extend(batch_results['clarifications'])
                total_tokens += batch_results.get('tokens_used', 0)
                
                # Small delay between batches to avoid rate limits
                time.sleep(1)
            
            # Calculate overall statistics
            stats = self._calculate_validation_stats(validation_results)
            
            # Update validation record
            validation.addressed_items = stats['addressed']
            validation.missing_items = stats['missing']
            validation.partial_items = stats['partial']
            validation.unclear_items = stats['unclear']
            validation.overall_completion_percentage = stats['completion_percentage']
            validation.high_priority_completion = stats['high_priority_completion']
            validation.mandatory_completion = stats['mandatory_completion']
            validation.processing_time_seconds = time.time() - start_time
            validation.total_tokens_used = total_tokens
            validation.status = 'completed'
            validation.validation_summary = self._generate_validation_summary(validation_results)
            
            db.session.commit()
            
            # Create clarification requests
            if clarifications_needed:
                self._create_clarification_requests(clarifications_needed, validation.validation_id, user_id)
            
            logger.info(f"Validation completed in {validation.processing_time_seconds:.2f}s: {stats}")
            
            return {
                'success': True,
                'validation_id': validation.validation_id,
                'stats': stats,
                'clarifications_count': len(clarifications_needed),
                'processing_time': validation.processing_time_seconds,
                'total_tokens': total_tokens
            }
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            
            # Update validation record as failed if it exists
            try:
                if 'validation' in locals():
                    validation.status = 'failed'
                    validation.error_message = str(e)
                    validation.processing_time_seconds = time.time() - start_time
                    db.session.commit()
            except:
                pass
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def _combine_document_content(self, documents: List[Document]) -> str:
        """Combine content from all documents"""
        combined = []
        
        for doc in documents:
            if doc.extracted_content:
                combined.append(f"\n=== {doc.original_filename or doc.filename} ===\n")
                combined.append(doc.extracted_content)
        
        full_content = '\n'.join(combined)
        
        # Limit content size for AI processing
        if len(full_content) > self.max_content_length:
            logger.warning(f"Content truncated from {len(full_content)} to {self.max_content_length} characters")
            full_content = full_content[:self.max_content_length]
        
        return full_content
    
    def _validate_item_batch(self, 
                           batch_items: List[ChecklistItem], 
                           rfp_content: str,
                           validation_id: str,
                           project_id: str) -> Dict[str, Any]:
        """
        Validate a batch of checklist items against RFP content
        
        Args:
            batch_items: List of checklist items to validate
            rfp_content: Combined RFP document content
            validation_id: ID of the validation session
            project_id: ID of the project
            
        Returns:
            Dict with batch validation results
        """
        results = []
        clarifications = []
        tokens_used = 0
        
        if not self.anthropic_client:
            # Fallback: create placeholder results without AI
            return self._create_fallback_results(batch_items, validation_id, project_id)
        
        try:
            # Prepare batch analysis prompt
            prompt = self._create_batch_analysis_prompt(batch_items, rfp_content)
            
            # Call Anthropic API
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            # Parse AI response
            ai_results = self._parse_ai_batch_response(response.content[0].text)
            
            # Create validation records
            for i, item in enumerate(batch_items):
                ai_result = ai_results.get(str(i), {})
                
                # Create item validation record
                item_validation = ChecklistItemValidation(
                    validation_id=validation_id,
                    item_id=item.item_id,
                    project_id=project_id,
                    status=ai_result.get('status', 'UNCLEAR'),
                    confidence_score=ai_result.get('confidence', 0.0),
                    extracted_content=ai_result.get('extracted_content', ''),
                    ai_analysis=ai_result,
                    ai_reasoning=ai_result.get('reasoning', ''),
                    needs_clarification=ai_result.get('needs_clarification', False),
                    clarification_reason=ai_result.get('clarification_reason', ''),
                    suggested_question=ai_result.get('suggested_question', ''),
                    processing_time_seconds=0.1,  # Approximate per-item time
                    tokens_used=tokens_used // len(batch_items)  # Distribute tokens
                )
                
                db.session.add(item_validation)
                results.append(item_validation)
                
                # Prepare clarification if needed
                if ai_result.get('needs_clarification', False):
                    clarification_data = {
                        'item': item,
                        'ai_result': ai_result,
                        'validation_id': validation_id,
                        'project_id': project_id
                    }
                    clarifications.append(clarification_data)
            
            db.session.commit()
            
            return {
                'results': results,
                'clarifications': clarifications,
                'tokens_used': tokens_used
            }
            
        except Exception as e:
            logger.error(f"Batch validation failed: {e}")
            
            # Create error results
            for item in batch_items:
                item_validation = ChecklistItemValidation(
                    validation_id=validation_id,
                    item_id=item.item_id,
                    project_id=project_id,
                    status='UNCLEAR',
                    confidence_score=0.0,
                    extracted_content='',
                    ai_analysis={'error': str(e)},
                    ai_reasoning=f'Analysis failed: {str(e)}',
                    needs_clarification=True,
                    clarification_reason=f'Unable to analyze due to error: {str(e)}',
                    suggested_question=item.question_text
                )
                
                db.session.add(item_validation)
                results.append(item_validation)
            
            db.session.commit()
            
            return {
                'results': results,
                'clarifications': [],
                'tokens_used': 0
            }
    
    def _create_batch_analysis_prompt(self, items: List[ChecklistItem], rfp_content: str) -> str:
        """Create AI prompt for batch analysis"""
        
        # Prepare items for analysis
        items_text = []
        for i, item in enumerate(items):
            items_text.append(f"""
Item {i}:
- Question: {item.question_text}
- Section: {item.section or 'N/A'}
- Category: {item.category or 'N/A'}
- Priority: {item.priority or 'medium'}
- Mandatory: {'Yes' if item.mandatory else 'No'}
- Keywords: {', '.join(item.keywords or [])}
""")
        
        prompt = f"""
You are analyzing an RFP document against a checklist of requirements for ITSS Global, a Temenos implementation partner specializing in BFSI solutions.

For each checklist item, analyze the RFP content and determine:
1. STATUS: ADDRESSED (fully covered), PARTIAL (partially covered), MISSING (not mentioned), UNCLEAR (ambiguous)
2. CONFIDENCE: Score from 0.0 to 1.0 indicating how confident you are in the assessment
3. EXTRACTED_CONTENT: Relevant text from RFP that addresses this item (or empty if missing)
4. REASONING: Brief explanation of your assessment
5. NEEDS_CLARIFICATION: true/false - whether this requires clarification from the client
6. CLARIFICATION_REASON: Why clarification is needed (if applicable)
7. SUGGESTED_QUESTION: Specific question to ask the client (if clarification needed)

CHECKLIST ITEMS TO ANALYZE:
{chr(10).join(items_text)}

RFP DOCUMENT CONTENT:
{rfp_content[:30000]}  

Please respond with a JSON object where each key is the item number (0, 1, 2, etc.) and the value contains your analysis:

{{
  "0": {{
    "status": "ADDRESSED|PARTIAL|MISSING|UNCLEAR",
    "confidence": 0.85,
    "extracted_content": "relevant text from RFP",
    "reasoning": "explanation of assessment",
    "needs_clarification": false,
    "clarification_reason": "",
    "suggested_question": ""
  }},
  "1": {{
    ...
  }}
}}

Focus on BFSI and Temenos-related requirements. Be thorough but practical in your assessment.
"""
        
        return prompt
    
    def _parse_ai_batch_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response into structured data"""
        try:
            # Try to extract JSON from response
            response_text = response_text.strip()
            
            # Find JSON block
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_text = response_text[start_idx:end_idx]
                return json.loads(json_text)
            else:
                logger.error("No JSON block found in AI response")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return {}
    
    def _create_fallback_results(self, batch_items: List[ChecklistItem], validation_id: str, project_id: str) -> Dict[str, Any]:
        """Create fallback results when AI is not available"""
        results = []
        
        for item in batch_items:
            item_validation = ChecklistItemValidation(
                validation_id=validation_id,
                item_id=item.item_id,
                project_id=project_id,
                status='UNCLEAR',
                confidence_score=0.0,
                extracted_content='',
                ai_analysis={'fallback': True, 'reason': 'AI service unavailable'},
                ai_reasoning='AI service unavailable - manual review required',
                needs_clarification=True,
                clarification_reason='Unable to analyze automatically - manual review required',
                suggested_question=item.question_text
            )
            
            db.session.add(item_validation)
            results.append(item_validation)
        
        db.session.commit()
        
        return {
            'results': results,
            'clarifications': [],
            'tokens_used': 0
        }
    
    def _calculate_validation_stats(self, results: List[ChecklistItemValidation]) -> Dict[str, Any]:
        """Calculate validation statistics"""
        total = len(results)
        
        if total == 0:
            return {
                'addressed': 0, 'missing': 0, 'partial': 0, 'unclear': 0,
                'completion_percentage': 0.0, 'high_priority_completion': 0.0, 'mandatory_completion': 0.0
            }
        
        # Count by status
        addressed = sum(1 for r in results if r.status == 'ADDRESSED')
        missing = sum(1 for r in results if r.status == 'MISSING')
        partial = sum(1 for r in results if r.status == 'PARTIAL')
        unclear = sum(1 for r in results if r.status == 'UNCLEAR')
        
        # Calculate completion percentage (addressed + partial = completed)
        completed = addressed + partial
        completion_percentage = (completed / total) * 100
        
        # Calculate priority-based completion (would need item data for accurate calculation)
        # For now, use overall completion as approximation
        high_priority_completion = completion_percentage
        mandatory_completion = completion_percentage
        
        return {
            'addressed': addressed,
            'missing': missing,
            'partial': partial,
            'unclear': unclear,
            'completion_percentage': completion_percentage,
            'high_priority_completion': high_priority_completion,
            'mandatory_completion': mandatory_completion
        }
    
    def _generate_validation_summary(self, results: List[ChecklistItemValidation]) -> Dict[str, Any]:
        """Generate validation summary by category/section"""
        summary = {}
        
        # Group results by section/category (would need item data for accurate grouping)
        # For now, create basic summary
        summary['overall'] = {
            'total_items': len(results),
            'avg_confidence': sum(r.confidence_score for r in results) / len(results) if results else 0.0,
            'needs_clarification_count': sum(1 for r in results if r.needs_clarification)
        }
        
        return summary
    
    def _create_clarification_requests(self, clarifications_data: List[Dict], validation_id: str, user_id: int):
        """Create clarification request records"""
        try:
            for clarification in clarifications_data:
                item = clarification['item']
                ai_result = clarification['ai_result']
                
                clarification_request = ClarificationRequest(
                    project_id=clarification['project_id'],
                    validation_id=validation_id,
                    item_id=item.item_id,
                    question_text=ai_result.get('suggested_question', item.question_text),
                    category=item.category,
                    section=item.section,
                    priority=self._map_priority(item.priority),
                    reason=ai_result.get('clarification_reason', 'Information not found in RFP'),
                    relevant_rfp_sections=[],  # Could be enhanced with source tracking
                    impact_if_not_clarified=f"Unable to assess compliance for: {item.question_text}",
                    created_by=user_id
                )
                
                db.session.add(clarification_request)
            
            db.session.commit()
            logger.info(f"Created {len(clarifications_data)} clarification requests")
            
        except Exception as e:
            logger.error(f"Failed to create clarification requests: {e}")
            db.session.rollback()
    
    def _map_priority(self, item_priority: str) -> str:
        """Map item priority to clarification priority"""
        mapping = {
            'critical': 'critical',
            'high': 'high', 
            'medium': 'medium',
            'low': 'low'
        }
        return mapping.get(item_priority, 'medium')

def create_validation_engine() -> ChecklistValidationEngine:
    """Factory function to create validation engine"""
    return ChecklistValidationEngine()

# Export main class and factory
__all__ = ['ChecklistValidationEngine', 'create_validation_engine']