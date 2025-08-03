# Real AI-Powered Analysis System
# Replace the hardcoded analysis_results in main.py with this

import anthropic
import json
import os
from datetime import datetime

class RealAnalysisEngine:
    """Real AI-powered analysis engine using Claude"""

    def __init__(self, anthropic_api_key=None):
        self.api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None
            print("⚠️ ANTHROPIC_API_KEY not configured - using fallback analysis")

    def analyze_project_documents(self, project_id):
        """Analyze all documents in a project and generate real insights"""
        try:
            from models import Project, Document, RFPDocument

            # Get project and documents
            project = Project.query.get(project_id)
            if not project:
                return self._fallback_analysis()

            # Get all documents (both old and new format)
            old_documents = Document.query.filter_by(project_id=project_id).all()
            rfp_documents = RFPDocument.query.filter_by(project_id=project_id).all()

            # Collect all document content
            all_content = []
            document_info = []

            # Process old format documents
            for doc in old_documents:
                if doc.content:
                    all_content.append(doc.content)
                    document_info.append({
                        'filename': doc.original_filename or doc.filename,
                        'type': 'legacy_document',
                        'size': doc.file_size or 0
                    })

            # Process new RFP documents
            for doc in rfp_documents:
                if doc.extracted_text:
                    all_content.append(doc.extracted_text)
                    document_info.append({
                        'filename': doc.original_name,
                        'type': doc.document_type,
                        'size': doc.file_size or 0
                    })

            if not all_content:
                return self._empty_analysis(document_info)

            # Generate real AI analysis
            return self._generate_ai_analysis(project, all_content, document_info)

        except Exception as e:
            print(f"Error in analysis: {e}")
            return self._fallback_analysis()

    def _generate_ai_analysis(self, project, documents_content, document_info):
        """Generate real analysis using Claude AI"""
        if not self.client:
            return self._fallback_analysis()

        try:
            # Combine all document content
            combined_content = "\n\n--- DOCUMENT SEPARATOR ---\n\n".join(documents_content)

            # Create comprehensive analysis prompt
            analysis_prompt = f"""
            You are an expert RFP analyst. Analyze the following RFP documents for project "{project.name}" and extract comprehensive insights.

            PROJECT CONTEXT:
            - Project Name: {project.name}
            - Client: {project.client_name or 'Not specified'}
            - Description: {project.description or 'Not provided'}
            - Documents to analyze: {len(documents_content)}

            DOCUMENT CONTENT:
            {combined_content[:20000]}  # Limit content to stay within token limits

            ANALYSIS INSTRUCTIONS:
            Please provide a comprehensive analysis in the following JSON format:

            {{
                "must_have_requirements": [
                    "List of critical requirements that are explicitly marked as mandatory, must-have, or required"
                ],
                "good_to_have_requirements": [
                    "List of preferred, optional, or nice-to-have requirements"
                ],
                "technical_specifications": [
                    "List of specific technical requirements, technologies, performance metrics"
                ],
                "project_details": {{
                    "timeline": "Project timeline or deadline information",
                    "budget": "Budget constraints or cost information mentioned",
                    "evaluation_criteria": "How proposals will be evaluated"
                }},
                "compliance_requirements": [
                    "Regulatory, legal, or compliance requirements"
                ],
                "key_constraints": [
                    "Important limitations, restrictions, or constraints"
                ],
                "submission_requirements": [
                    "Format, deadline, and submission process requirements"
                ],
                "analysis_confidence": "High/Medium/Low - your confidence in this analysis",
                "key_insights": [
                    "Important insights or observations about this RFP"
                ],
                "risk_factors": [
                    "Potential risks or challenges identified"
                ],
                "opportunities": [
                    "Business opportunities or advantages identified"
                ]
            }}

            IMPORTANT:
            - Extract ONLY information that is actually present in the documents
            - If information is not found, use empty arrays or "Not specified"
            - Be precise and quote specific requirements when possible
            - Focus on actionable intelligence for proposal writing
            """

            # Call Claude API
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": analysis_prompt}]
            )

            # Parse response
            response_text = message.content[0].text.strip()

            # Clean up response to extract JSON
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            analysis_data = json.loads(response_text)

            # Add metadata
            analysis_data['analysis_metadata'] = {
                'generated_at': datetime.now().isoformat(),
                'documents_analyzed': len(documents_content),
                'document_info': document_info,
                'total_content_length': sum(len(content) for content in documents_content),
                'ai_model': 'claude-sonnet-4-20250514'
            }

            print(f"✅ Real AI analysis completed for project {project.name}")
            return analysis_data

        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            return self._fallback_analysis()
        except Exception as e:
            print(f"❌ AI analysis error: {e}")
            return self._fallback_analysis()

    def _fallback_analysis(self):
        """Fallback analysis when AI is not available"""
        return {
            'must_have_requirements': [
                'Analysis unavailable - AI service not configured'
            ],
            'good_to_have_requirements': [
                'Configure ANTHROPIC_API_KEY for real-time analysis'
            ],
            'technical_specifications': [
                'Real-time analysis requires Claude AI integration'
            ],
            'project_details': {
                'timeline': 'Not analyzed - AI service unavailable',
                'budget': 'Not analyzed - AI service unavailable',
                'evaluation_criteria': 'Configure AI service for detailed analysis'
            },
            'compliance_requirements': [],
            'key_constraints': [],
            'submission_requirements': [],
            'analysis_confidence': 'Low',
            'key_insights': [
                'Configure ANTHROPIC_API_KEY environment variable to enable real AI analysis'
            ],
            'risk_factors': [
                'AI analysis service not available'
            ],
            'opportunities': [
                'Enable AI analysis for comprehensive insights'
            ],
            'analysis_metadata': {
                'generated_at': datetime.now().isoformat(),
                'documents_analyzed': 0,
                'ai_model': 'fallback',
                'status': 'AI service not configured'
            }
        }

    def _empty_analysis(self, document_info):
        """Analysis for projects with no document content"""
        return {
            'must_have_requirements': [
                'No document content available for analysis'
            ],
            'good_to_have_requirements': [
                'Upload RFP documents to get AI-powered analysis'
            ],
            'technical_specifications': [
                'Upload documents with technical requirements'
            ],
            'project_details': {
                'timeline': 'No timeline information in documents',
                'budget': 'No budget information in documents',
                'evaluation_criteria': 'No evaluation criteria found in documents'
            },
            'compliance_requirements': [],
            'key_constraints': [],
            'submission_requirements': [],
            'analysis_confidence': 'Low',
            'key_insights': [
                'Upload and process RFP documents to get detailed insights'
            ],
            'risk_factors': [
                'No document content to analyze'
            ],
            'opportunities': [
                'Upload RFP documents to unlock AI-powered analysis'
            ],
            'analysis_metadata': {
                'generated_at': datetime.now().isoformat(),
                'documents_analyzed': len(document_info),
                'document_info': document_info,
                'ai_model': 'none',
                'status': 'No document content available'
            }
        }

    def analyze_individual_document(self, document_id):
        """Analyze a single document in detail"""
        try:
            from models import Document, RFPDocument

            # Try to find document in either table
            document = Document.query.get(document_id) or RFPDocument.query.get(document_id)
            if not document:
                return None

            # Get document content
            content = getattr(document, 'content', None) or getattr(document, 'extracted_text', None)
            if not content:
                return self._empty_document_analysis(document)

            return self._generate_document_analysis(document, content)

        except Exception as e:
            print(f"Error analyzing document {document_id}: {e}")
            return None

    def _generate_document_analysis(self, document, content):
        """Generate detailed analysis for a single document"""
        if not self.client:
            return self._fallback_document_analysis(document)

        try:
            filename = getattr(document, 'original_filename', None) or getattr(document, 'original_name', None) or getattr(document, 'filename', 'Unknown')

            analysis_prompt = f"""
            Analyze this individual document in detail:

            DOCUMENT: {filename}
            CONTENT: {content[:15000]}

            Provide detailed analysis in JSON format:
            {{
                "extracted_requirements": [
                    "List each specific requirement found in this document"
                ],
                "key_terms": [
                    "Important technical terms, technologies, or concepts mentioned"
                ],
                "compliance_items": [
                    "Compliance, regulatory, or legal requirements"
                ],
                "deadlines_and_dates": [
                    "All dates, deadlines, or timeline information"
                ],
                "evaluation_criteria": [
                    "How this document says proposals will be evaluated"
                ],
                "technical_constraints": [
                    "Technical limitations or constraints specified"
                ],
                "budget_information": [
                    "Any cost, budget, or financial information"
                ],
                "contact_information": [
                    "Contact details for questions or submissions"
                ],
                "document_type_assessment": "What type of document this appears to be",
                "key_sections": [
                    "Main sections or topics covered in this document"
                ],
                "analysis_confidence": "High/Medium/Low confidence in this analysis"
            }}

            Extract only information actually present in the document.
            """

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                messages=[{"role": "user", "content": analysis_prompt}]
            )

            response_text = message.content[0].text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            analysis_data = json.loads(response_text)

            # Add metadata
            analysis_data['document_metadata'] = {
                'filename': filename,
                'analyzed_at': datetime.now().isoformat(),
                'content_length': len(content),
                'ai_model': 'claude-sonnet-4-20250514'
            }

            return analysis_data

        except Exception as e:
            print(f"Document analysis error: {e}")
            return self._fallback_document_analysis(document)

    def _fallback_document_analysis(self, document):
        """Fallback for individual document analysis"""
        filename = getattr(document, 'original_filename', None) or getattr(document, 'original_name', None) or getattr(document, 'filename', 'Unknown')

        return {
            'extracted_requirements': ['AI analysis unavailable - configure ANTHROPIC_API_KEY'],
            'key_terms': ['AI', 'analysis', 'configuration', 'required'],
            'compliance_items': ['Configure AI service for compliance analysis'],
            'deadlines_and_dates': [],
            'evaluation_criteria': [],
            'technical_constraints': [],
            'budget_information': [],
            'contact_information': [],
            'document_type_assessment': 'Cannot determine without AI analysis',
            'key_sections': ['AI analysis required'],
            'analysis_confidence': 'Low - AI service not available',
            'document_metadata': {
                'filename': filename,
                'analyzed_at': datetime.now().isoformat(),
                'ai_model': 'fallback',
                'status': 'AI service not configured'
            }
        }

    def _empty_document_analysis(self, document):
        """Analysis for documents with no content"""
        filename = getattr(document, 'original_filename', None) or getattr(document, 'original_name', None) or getattr(document, 'filename', 'Unknown')

        return {
            'extracted_requirements': ['No content available in this document'],
            'key_terms': [],
            'compliance_items': [],
            'deadlines_and_dates': [],
            'evaluation_criteria': [],
            'technical_constraints': [],
            'budget_information': [],
            'contact_information': [],
            'document_type_assessment': 'Document uploaded but no content extracted',
            'key_sections': [],
            'analysis_confidence': 'Low - no content to analyze',
            'document_metadata': {
                'filename': filename,
                'analyzed_at': datetime.now().isoformat(),
                'ai_model': 'none',
                'status': 'No content available'
            }
        }

# Create global analysis engine instance
analysis_engine = RealAnalysisEngine()

# Updated route functions to use in main.py

def get_real_analysis_results(project_id):
    """Get real AI-powered analysis results for a project"""
    return analysis_engine.analyze_project_documents(project_id)

def get_real_document_analysis(document_id):
    """Get real AI-powered analysis for a single document"""
    return analysis_engine.analyze_individual_document(document_id)
