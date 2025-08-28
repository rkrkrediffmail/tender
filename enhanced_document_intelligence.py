# Enhanced Document Intelligence Agent with Claude Vector Intelligence
import json
import os
from typing import Dict, Any, List
from datetime import datetime

from claude_vector_intelligence import get_claude_vector_intelligence

class EnhancedDocumentIntelligenceAgent:
    """Enhanced Document Intelligence Agent with Claude Vector Intelligence Integration"""

    def __init__(self):
        self.claude_vector_intelligence = get_claude_vector_intelligence()
        self.anthropic_client = self.claude_vector_intelligence.anthropic_client

    def analyze_document_with_intelligence(self, document_text: str, document_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive document analysis enhanced with past proposal intelligence"""

        try:
            # Basic document structure analysis
            structure_analysis = self._claude_structure_analysis(document_text, document_metadata)
            
            # Enhanced intelligence: Find similar documents from past proposals
            similar_content = self._find_similar_past_content(document_text, structure_analysis)
            
            # Intelligent document classification with past proposal context
            enhanced_classification = self._intelligent_document_classification(
                document_text, structure_analysis, similar_content
            )

            return {
                'document_text': document_text[:1000],  # Sample for response
                'structure_analysis': structure_analysis,
                'similar_past_content': similar_content,
                'intelligent_classification': enhanced_classification,
                'processing_timestamp': datetime.now().isoformat(),
                'agent': 'enhanced_document_intelligence'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'agent': 'enhanced_document_intelligence'
            }

    def extract_requirements_with_past_context(self, document_text: str) -> Dict[str, Any]:
        """Extract requirements with intelligent context from past proposals"""
        
        try:
            # Extract initial requirements using Claude
            initial_requirements = self._claude_requirement_extraction(document_text)
            
            # Get intelligent context from past proposals
            past_context = self._get_intelligent_past_context(
                initial_requirements.get('must_have_requirements', []) + 
                initial_requirements.get('technical_specifications', [])
            )
            
            # Enhanced requirement analysis with past proposal intelligence
            enhanced_requirements = self._claude_enhanced_requirement_analysis(
                document_text, initial_requirements, past_context
            )

            return {
                'initial_requirements': initial_requirements,
                'past_proposal_context': past_context,
                'enhanced_requirements': enhanced_requirements,
                'intelligence_score': past_context.get('executive_intelligence', {}).get('confidence_level', 0.5),
                'agent': 'enhanced_document_intelligence'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'agent': 'enhanced_document_intelligence'
            }

    def _find_similar_past_content(self, document_text: str, structure_analysis: Dict) -> Dict[str, Any]:
        """Find similar content from past proposals using Claude Vector Intelligence"""
        
        try:
            # Extract key concepts for similarity search
            search_queries = []
            
            # Use document structure to create targeted searches
            if structure_analysis.get('document_type') == 'RFP':
                search_queries.extend([
                    "technical requirements specifications",
                    "commercial terms and conditions", 
                    "project implementation methodology",
                    "team qualifications and experience"
                ])
            elif structure_analysis.get('document_type') == 'technical_specification':
                search_queries.extend([
                    "technical architecture and design",
                    "system integration requirements",
                    "performance and scalability requirements"
                ])
            
            # Add document-specific concepts
            if structure_analysis.get('key_topics'):
                search_queries.extend(structure_analysis['key_topics'][:3])

            # Perform intelligent similarity searches
            all_similar_content = []
            for query in search_queries[:5]:  # Limit for performance
                similar_results = self.claude_vector_intelligence.intelligent_similarity_search(
                    query=query,
                    filters={'project_type': 'bfsi'}, 
                    limit=3
                )
                all_similar_content.extend(similar_results)

            return {
                'found_similar_content': len(all_similar_content),
                'similar_content': all_similar_content[:10],  # Top 10 most relevant
                'search_queries_used': search_queries,
                'intelligence_timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Error finding similar past content: {e}")
            return {'found_similar_content': 0, 'error': str(e)}

    def _get_intelligent_past_context(self, requirements: List[str]) -> Dict[str, Any]:
        """Get intelligent context from past proposals for current requirements"""
        
        try:
            project_metadata = {
                'project_type': 'bfsi',  # Default for ITSS Global
                'industry_sector': 'banking'
            }
            
            # Use Claude Vector Intelligence to get comprehensive context
            context = self.claude_vector_intelligence.get_intelligent_context_for_agents(
                requirements=requirements,
                project_metadata=project_metadata
            )
            
            return context

        except Exception as e:
            print(f"Error getting intelligent past context: {e}")
            return {'success': False, 'error': str(e)}

    def _claude_enhanced_requirement_analysis(self, document_text: str, initial_requirements: Dict, past_context: Dict) -> Dict[str, Any]:
        """Enhanced requirement analysis using Claude with past proposal intelligence"""
        
        if not self.anthropic_client:
            return initial_requirements

        try:
            # Prepare past context summary for Claude
            context_summary = ""
            if past_context.get('success'):
                reusable_content = past_context.get('reusable_content_sections', {})
                capability_intelligence = past_context.get('capability_intelligence', {})
                
                context_summary = f"""
RELEVANT PAST PROPOSAL INTELLIGENCE:

Reusable Content Available:
- Technical Approach: {'Available' if reusable_content.get('technical_approach') else 'Not Available'}
- Implementation Methodology: {'Available' if reusable_content.get('implementation_methodology') else 'Not Available'} 
- Team Experience: {'Available' if reusable_content.get('team_experience') else 'Not Available'}

Proven Capabilities: {capability_intelligence.get('proven_capabilities', [])}
Technology Expertise: {capability_intelligence.get('technology_expertise', [])}
Competitive Differentiators: {capability_intelligence.get('competitive_differentiators', [])}

Gap Analysis:
- Missing Capabilities: {past_context.get('gap_analysis', {}).get('missing_capabilities', [])}
- New Requirements: {past_context.get('gap_analysis', {}).get('new_requirements', [])}
"""

            prompt = f"""You are ITSS Global's enhanced document intelligence agent analyzing RFP requirements with past proposal intelligence.

DOCUMENT CONTENT:
{document_text[:8000]}

INITIAL REQUIREMENT EXTRACTION:
{json.dumps(initial_requirements, indent=2)}

{context_summary}

ENHANCED ANALYSIS TASK:
Using the past proposal intelligence, provide an enhanced requirement analysis:

{{
  "enhanced_requirements": {{
    "must_have_requirements": [
      // Enhanced list with past experience context
    ],
    "good_to_have_requirements": [
      // Enhanced with past proposal insights
    ],
    "technical_specifications": [
      // Technical specs enhanced with past solution patterns
    ],
    "compliance_requirements": [
      // Regulatory requirements with past compliance experience
    ]
  }},
  
  "requirement_intelligence": {{
    "requirements_we_have_experience_with": [
      // Requirements we've handled in past proposals
    ],
    "new_requirements_needing_research": [
      // Requirements not found in past proposals
    ],
    "similar_past_solutions": [
      // Past solutions that could be adapted
    ],
    "competitive_advantages": [
      // Our proven strengths for these requirements
    ]
  }},
  
  "implementation_guidance": {{
    "reusable_approaches": [
      // Implementation approaches from past proposals
    ],
    "proven_technologies": [
      // Technologies we've successfully used before
    ],
    "risk_mitigation_strategies": [
      // Risk mitigation based on past experience
    ]
  }},
  
  "proposal_strategy": {{
    "emphasis_areas": [
      // What to emphasize based on our past success
    ],
    "differentiator_opportunities": [
      // How to differentiate based on experience
    ],
    "content_reuse_opportunities": [
      // Specific past content that can be reused
    ]
  }}
}}

FOCUS: Maximum intelligence extraction for competitive proposal generation."""

            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(response.content[0].text)
            
            # Add metadata
            result['analysis_confidence'] = past_context.get('executive_intelligence', {}).get('confidence_level', 0.5)
            result['past_sources_analyzed'] = past_context.get('sources_analyzed', 0)
            result['enhancement_timestamp'] = datetime.now().isoformat()
            
            return result

        except Exception as e:
            print(f"Enhanced requirement analysis failed: {e}")
            return {**initial_requirements, 'enhancement_error': str(e)}

    def _claude_structure_analysis(self, text: str, metadata: Dict) -> Dict[str, Any]:
        """Analyze document structure using Claude"""
        
        if not self.anthropic_client:
            return {'error': 'Claude not available'}

        prompt = f"""
        Analyze this document structure for ITSS Global's RFP processing:

        Document: {metadata.get('filename', 'Unknown')}
        Content: {text[:3000]}...

        Identify and return JSON:
        {{
          "document_type": "RFP|technical_spec|commercial|legal|proposal_response",
          "main_sections": ["section1", "section2"],
          "key_topics": ["topic1", "topic2"],
          "technical_sections": ["tech_section1"],
          "commercial_sections": ["commercial_section1"],
          "evaluation_criteria": ["criteria1"],
          "timeline_sections": ["timeline_info"],
          "complexity_level": 1-5,
          "industry_context": "banking|fintech|insurance|general",
          "document_priority": "urgent|high|normal|low"
        }}

        Focus on BFSI/banking industry context.
        """

        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            return json.loads(response.content[0].text)
        except Exception as e:
            return {
                'document_type': 'unknown',
                'complexity_level': 3,
                'key_topics': [],
                'industry_context': 'bfsi',
                'error': str(e)
            }

    def _claude_requirement_extraction(self, text: str) -> Dict[str, Any]:
        """Extract requirements using Claude"""
        
        if not self.anthropic_client:
            return {'error': 'Claude not available'}

        prompt = f"""
        Extract requirements from this RFP document for ITSS Global (Temenos partner):

        Content: {text[:6000]}...

        Extract and categorize requirements as JSON:
        {{
          "must_have_requirements": [
            "Specific mandatory requirement 1",
            "Specific mandatory requirement 2"
          ],
          "good_to_have_requirements": [
            "Nice-to-have requirement 1"
          ],
          "technical_specifications": [
            "Technical spec 1",
            "Technical spec 2"
          ],
          "compliance_requirements": [
            "Regulatory requirement 1"
          ],
          "timeline_requirements": [
            "Timeline requirement 1"
          ],
          "commercial_requirements": [
            "Commercial requirement 1"
          ],
          "integration_requirements": [
            "Integration requirement 1"
          ],
          "performance_requirements": [
            "Performance requirement 1"
          ]
        }}

        Focus on banking/financial services and Temenos-related requirements.
        """

        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            return json.loads(response.content[0].text)
        except Exception as e:
            return {
                'error': str(e),
                'must_have_requirements': [],
                'technical_specifications': []
            }

    def _intelligent_document_classification(self, text: str, structure: Dict, similar_content: Dict) -> Dict[str, Any]:
        """Intelligent document classification with past proposal context"""
        
        if not self.anthropic_client:
            return {'classification': 'unknown'}

        past_context = ""
        if similar_content.get('similar_content'):
            past_context = f"Similar past proposal content found: {len(similar_content['similar_content'])} relevant sections"

        prompt = f"""
        Classify this document with intelligence from past proposals:

        Document Structure: {json.dumps(structure, indent=2)}
        {past_context}

        Content Preview: {text[:2000]}

        Provide intelligent classification as JSON:
        {{
          "primary_classification": "rfp|technical_spec|commercial_proposal|legal_document|addendum",
          "sub_classification": "specific_type_detail",
          "industry_focus": "banking|fintech|insurance|general_bfsi",
          "complexity_assessment": "low|medium|high|expert_level",
          "processing_priority": "urgent|high|normal|low",
          "required_expertise": ["temenos", "integration", "compliance"],
          "estimated_response_effort_hours": 40,
          "competitive_assessment": "high_win_probability|medium|low|unknown",
          "past_experience_relevance": "high|medium|low|none",
          "recommended_team_composition": ["solution_architect", "technical_lead"],
          "key_differentiator_opportunities": ["opportunity1", "opportunity2"]
        }}
        """

        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            return json.loads(response.content[0].text)
        except Exception as e:
            return {
                'primary_classification': structure.get('document_type', 'unknown'),
                'complexity_assessment': 'medium',
                'processing_priority': 'normal',
                'error': str(e)
            }

# Helper function for integration with main system
def get_enhanced_document_intelligence_agent():
    """Get enhanced document intelligence agent instance"""
    return EnhancedDocumentIntelligenceAgent()