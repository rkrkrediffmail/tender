#!/usr/bin/env python3
"""
Claude-Powered Past Proposals Analyzer
Simple, reliable approach to extract and store company capabilities from past proposals
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from models import db

logger = logging.getLogger(__name__)

class ClaudeProposalAnalyzer:
    """
    Analyze past proposals using Claude to extract company capabilities and experience
    """
    
    def __init__(self):
        """Initialize Claude client with proper error handling"""
        self.anthropic_client = None
        
        if ANTHROPIC_AVAILABLE:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                try:
                    self.anthropic_client = anthropic.Anthropic(api_key=api_key)
                    logger.info("Claude client initialized for proposal analysis")
                except Exception as e:
                    logger.error(f"Failed to initialize Anthropic client: {e}")
                    logger.info("Proposal analysis will be disabled due to client initialization failure")
                    self.anthropic_client = None
            else:
                logger.warning("ANTHROPIC_API_KEY not found - analysis disabled")
        else:
            logger.warning("Anthropic library not available - analysis disabled")
    
    def analyze_past_proposal(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze past proposal content to extract company capabilities and experience
        
        Args:
            content: Full text content of the proposal
            metadata: Basic metadata (client, year, etc.)
            
        Returns:
            Dict with extracted capabilities, technologies, and experience
        """
        if not self.anthropic_client:
            return self._create_fallback_analysis(content, metadata)
        
        try:
            analysis_prompt = self._create_analysis_prompt(content, metadata)
            
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            # Parse Claude's structured response
            analysis_text = response.content[0].text
            analysis_data = self._parse_claude_response(analysis_text)
            
            return {
                'success': True,
                'analysis': analysis_data,
                'ai_model': 'claude-3-sonnet-20240229',
                'tokens_used': response.usage.input_tokens + response.usage.output_tokens,
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return self._create_fallback_analysis(content, metadata, error=str(e))
    
    def _create_analysis_prompt(self, content: str, metadata: Dict[str, Any]) -> str:
        """Create analysis prompt for Claude"""
        
        # Truncate content if too long
        max_content_length = 15000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "...[truncated]"
        
        prompt = f"""
You are analyzing a past proposal from ITSS Global, a Temenos implementation partner specializing in BFSI solutions.

PROPOSAL METADATA:
- Client: {metadata.get('client_name', 'Unknown')}
- Project Type: {metadata.get('project_type', 'Unknown')}
- Year: {metadata.get('submission_year', 'Unknown')}
- Proposal Type: {metadata.get('proposal_type', 'Unknown')}

PROPOSAL CONTENT:
{content}

Please extract and analyze the following information about ITSS Global's capabilities and experience demonstrated in this proposal:

1. TECHNICAL CAPABILITIES
   - Technologies used/mentioned (databases, programming languages, frameworks)
   - Temenos products and versions (T24, Infinity, etc.)
   - Integration approaches (APIs, middleware, etc.)
   - Infrastructure and platforms

2. FUNCTIONAL EXPERTISE  
   - Banking domains covered (core banking, payments, loans, etc.)
   - Industry-specific solutions
   - Regulatory compliance experience
   - Business processes automated

3. IMPLEMENTATION EXPERIENCE
   - Project methodologies used
   - Team size and roles mentioned  
   - Timeline and phases described
   - Risk management approaches

4. CLIENT SOLUTIONS
   - Specific problems solved
   - Business value delivered
   - Innovation or unique approaches
   - Success metrics mentioned

5. COMPANY STRENGTHS
   - Certifications and partnerships mentioned
   - Years of experience in specific areas
   - Notable achievements or case studies
   - Competitive advantages highlighted

Please respond in this JSON format:
{{
  "technical_capabilities": {{
    "technologies": ["PostgreSQL", "Java", "REST APIs", "..."],
    "temenos_products": ["T24 R19", "Infinity", "..."],
    "integration_methods": ["API Gateway", "ESB", "..."],
    "platforms": ["Linux", "Oracle", "AWS", "..."]
  }},
  "functional_expertise": {{
    "banking_domains": ["Core Banking", "Payments", "Loans", "..."],
    "industry_solutions": ["Retail Banking", "Corporate Banking", "..."],
    "compliance_areas": ["AML", "KYC", "Basel III", "..."],
    "business_processes": ["Account Opening", "Trade Finance", "..."]
  }},
  "implementation_experience": {{
    "methodologies": ["Agile", "Waterfall", "..."],
    "team_capabilities": ["Solution Architecture", "Data Migration", "..."],
    "project_phases": ["Analysis", "Development", "Testing", "..."],
    "risk_mitigation": ["Pilot Implementation", "Rollback Plans", "..."]
  }},
  "client_solutions": {{
    "problems_solved": ["Legacy System Replacement", "Digital Transformation", "..."],
    "business_value": ["Cost Reduction", "Process Automation", "..."],
    "innovations": ["Mobile Banking", "Real-time Processing", "..."],
    "success_metrics": ["99.9% Uptime", "50% Faster Processing", "..."]
  }},
  "company_strengths": {{
    "certifications": ["Temenos Certified", "ISO 27001", "..."],
    "experience_years": {{"core_banking": 10, "temenos": 8, "bfsi": 12}},
    "achievements": ["100+ Implementations", "Zero Downtime Migrations", "..."],
    "competitive_advantages": ["24/7 Support", "Local Presence", "..."]
  }},
  "key_differentiators": ["Temenos Gold Partner", "BFSI Specialization", "Proven Track Record"],
  "project_complexity": "High|Medium|Low",
  "confidence_score": 0.85
}}

Focus on extracting concrete, specific information that demonstrates ITSS Global's capabilities. If information is not clearly stated, don't make assumptions.
"""
        return prompt
    
    def _parse_claude_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's JSON response"""
        try:
            # Find JSON block in response
            response_text = response_text.strip()
            
            # Look for JSON structure
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_text = response_text[start_idx:end_idx]
                return json.loads(json_text)
            else:
                logger.warning("No JSON found in Claude response")
                return self._create_minimal_analysis(response_text)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude JSON response: {e}")
            return self._create_minimal_analysis(response_text)
    
    def _create_fallback_analysis(self, content: str, metadata: Dict[str, Any], error: str = None) -> Dict[str, Any]:
        """Create basic analysis when Claude is unavailable"""
        
        # Simple keyword extraction as fallback
        bfsi_keywords = ['banking', 'finance', 'loan', 'payment', 'account', 'transaction']
        temenos_keywords = ['temenos', 't24', 'infinity', 'transact']
        tech_keywords = ['java', 'sql', 'api', 'rest', 'database', 'oracle', 'postgresql']
        
        content_lower = content.lower()
        
        found_bfsi = [kw for kw in bfsi_keywords if kw in content_lower]
        found_temenos = [kw for kw in temenos_keywords if kw in content_lower] 
        found_tech = [kw for kw in tech_keywords if kw in content_lower]
        
        return {
            'success': False,
            'analysis': {
                'technical_capabilities': {
                    'technologies': found_tech,
                    'temenos_products': found_temenos,
                    'integration_methods': [],
                    'platforms': []
                },
                'functional_expertise': {
                    'banking_domains': found_bfsi,
                    'industry_solutions': [],
                    'compliance_areas': [],
                    'business_processes': []
                },
                'key_differentiators': ['Temenos Partner', 'BFSI Focus'],
                'project_complexity': 'Medium',
                'confidence_score': 0.3
            },
            'fallback_reason': error or 'Claude unavailable',
            'analyzed_at': datetime.utcnow().isoformat()
        }
    
    def _create_minimal_analysis(self, response_text: str) -> Dict[str, Any]:
        """Create minimal analysis when JSON parsing fails"""
        return {
            'technical_capabilities': {
                'technologies': [],
                'temenos_products': [],
                'integration_methods': [],
                'platforms': []
            },
            'functional_expertise': {
                'banking_domains': [],
                'industry_solutions': [],
                'compliance_areas': [],
                'business_processes': []
            },
            'implementation_experience': {
                'methodologies': [],
                'team_capabilities': [],
                'project_phases': [],
                'risk_mitigation': []
            },
            'client_solutions': {
                'problems_solved': [],
                'business_value': [],
                'innovations': [],
                'success_metrics': []
            },
            'company_strengths': {
                'certifications': [],
                'experience_years': {},
                'achievements': [],
                'competitive_advantages': []
            },
            'key_differentiators': ['ITSS Global - Temenos Partner'],
            'project_complexity': 'Unknown',
            'confidence_score': 0.1,
            'raw_response': response_text[:500]  # Store first 500 chars for debugging
        }
    
    def find_matching_capabilities(self, rfp_requirements: List[str], filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Find past proposals that match RFP requirements
        
        Args:
            rfp_requirements: List of requirement strings from new RFP
            filters: Optional filters (client_name, project_type, etc.)
            
        Returns:
            List of matching proposals with relevance scores
        """
        try:
            from models import PastProposal
            
            # Get all processed proposals
            proposals_query = PastProposal.query.filter(
                PastProposal.processing_status == 'processed'
            )
            
            # Apply filters
            if filters:
                if filters.get('project_type'):
                    proposals_query = proposals_query.filter(
                        PastProposal.project_type == filters['project_type']
                    )
                if filters.get('industry_sector'):
                    proposals_query = proposals_query.filter(
                        PastProposal.industry_sector == filters['industry_sector']
                    )
            
            proposals = proposals_query.all()
            
            if not self.anthropic_client or not proposals:
                return []
            
            # Use Claude to analyze matches
            return self._analyze_matches_with_claude(rfp_requirements, proposals)
            
        except Exception as e:
            logger.error(f"Error finding matching capabilities: {e}")
            return []
    
    def _analyze_matches_with_claude(self, requirements: List[str], proposals: List) -> List[Dict[str, Any]]:
        """Use Claude to analyze which proposals match the requirements"""
        
        try:
            # Prepare proposal summaries for Claude
            proposal_summaries = []
            for proposal in proposals[:10]:  # Limit to top 10 for token efficiency
                summary = {
                    'id': proposal.proposal_id,
                    'title': proposal.title,
                    'client': proposal.client_name,
                    'type': proposal.project_type,
                    'year': proposal.submission_year,
                    'capabilities': proposal.capabilities_extracted
                }
                proposal_summaries.append(summary)
            
            match_prompt = f"""
Analyze which of these past ITSS Global proposals are most relevant to the new RFP requirements:

NEW RFP REQUIREMENTS:
{chr(10).join(f"- {req}" for req in requirements)}

PAST PROPOSALS:
{json.dumps(proposal_summaries, indent=2)}

For each proposal, provide:
1. Relevance score (0.0 to 1.0)
2. Matching capabilities 
3. Specific experience that applies
4. Recommended content to reuse

Respond in JSON format:
{{
  "matches": [
    {{
      "proposal_id": "uuid",
      "relevance_score": 0.85,
      "matching_capabilities": ["Core Banking", "API Integration"],
      "relevant_experience": ["T24 R19 upgrade for similar bank"],
      "reusable_content": ["Technical architecture section", "Risk mitigation approach"],
      "reasoning": "Strong match because..."
    }}
  ]
}}
"""
            
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1500,
                messages=[{"role": "user", "content": match_prompt}]
            )
            
            matches_data = self._parse_claude_response(response.content[0].text)
            return matches_data.get('matches', [])
            
        except Exception as e:
            logger.error(f"Error analyzing matches with Claude: {e}")
            return []

def create_claude_analyzer() -> ClaudeProposalAnalyzer:
    """Factory function to create Claude analyzer"""
    return ClaudeProposalAnalyzer()

# Export main class
__all__ = ['ClaudeProposalAnalyzer', 'create_claude_analyzer']