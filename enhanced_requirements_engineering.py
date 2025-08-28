# Enhanced Requirements Engineering Agent with Claude Vector Intelligence
import json
from typing import Dict, Any, List
from datetime import datetime

from claude_vector_intelligence import get_claude_vector_intelligence

class EnhancedRequirementsEngineeringAgent:
    """Enhanced Requirements Engineering Agent with Claude Vector Intelligence Integration"""

    def __init__(self):
        self.claude_vector_intelligence = get_claude_vector_intelligence()
        self.anthropic_client = self.claude_vector_intelligence.anthropic_client

    def analyze_requirements_with_intelligence(self, requirements: List[str], project_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive requirements analysis enhanced with past proposal intelligence"""

        try:
            # Get intelligent context from past proposals
            past_context = self.claude_vector_intelligence.get_intelligent_context_for_agents(
                requirements=requirements,
                project_metadata=project_metadata
            )
            
            # Enhanced requirements categorization with past intelligence
            categorized_requirements = self._claude_intelligent_requirement_categorization(
                requirements, past_context
            )
            
            # Generate implementation strategy based on past success
            implementation_strategy = self._generate_implementation_strategy(
                categorized_requirements, past_context
            )
            
            # Risk analysis with past proposal lessons
            risk_analysis = self._analyze_risks_with_past_intelligence(
                requirements, past_context
            )
            
            # Generate competitive positioning
            competitive_positioning = self._generate_competitive_positioning(
                requirements, past_context
            )

            return {
                'past_proposal_context': past_context,
                'categorized_requirements': categorized_requirements,
                'implementation_strategy': implementation_strategy,
                'risk_analysis': risk_analysis,
                'competitive_positioning': competitive_positioning,
                'intelligence_score': past_context.get('executive_intelligence', {}).get('confidence_level', 0.5),
                'processing_timestamp': datetime.now().isoformat(),
                'agent': 'enhanced_requirements_engineering'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'agent': 'enhanced_requirements_engineering'
            }

    def generate_solution_architecture(self, requirements: Dict[str, Any], past_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate solution architecture leveraging past proposal patterns"""
        
        if not self.anthropic_client:
            return {'error': 'Claude not available'}

        try:
            reusable_content = past_context.get('reusable_content_sections', {})
            solution_architecture = reusable_content.get('solution_architecture', {})
            
            prompt = f"""You are ITSS Global's solution architect creating architecture for a new proposal using past proposal intelligence.

CURRENT REQUIREMENTS:
{json.dumps(requirements, indent=2)}

PAST PROPOSAL INTELLIGENCE:
Available Solution Architecture Content: {solution_architecture.get('content', 'None available')}
Proven Technologies: {past_context.get('capability_intelligence', {}).get('technology_expertise', [])}
Past Solution Approaches: {past_context.get('capability_intelligence', {}).get('proven_capabilities', [])}

ARCHITECTURE TASK:
Design optimal solution architecture leveraging past success:

{{
  "solution_architecture": {{
    "high_level_architecture": {{
      "architectural_pattern": "microservices|monolithic|hybrid|cloud_native",
      "core_components": ["component1", "component2"],
      "integration_patterns": ["pattern1", "pattern2"],
      "data_flow": "description of data flow",
      "security_architecture": "security approach"
    }},
    
    "technology_stack": {{
      "proven_technologies": [
        // Technologies from past successful proposals
      ],
      "new_technologies": [
        // New technologies needed for this project
      ],
      "integration_technologies": ["tech1", "tech2"],
      "database_technologies": ["db1", "db2"],
      "cloud_platforms": ["platform1"]
    }},
    
    "implementation_approach": {{
      "phases": [
        {{
          "phase_name": "Phase 1",
          "duration": "X weeks",
          "deliverables": ["deliverable1"],
          "based_on_past_experience": "reference to past approach"
        }}
      ],
      "risk_mitigation": [
        // Risk mitigation strategies from past projects
      ],
      "quality_assurance": [
        // QA approaches from past success
      ]
    }},
    
    "competitive_differentiators": {{
      "unique_approaches": [
        // What makes our approach unique based on experience
      ],
      "proven_benefits": [
        // Benefits we've delivered in past projects
      ],
      "case_studies": [
        // References to past success stories
      ]
    }},
    
    "reuse_opportunities": {{
      "reusable_components": [
        // Components/modules we can reuse from past projects
      ],
      "accelerators": [
        // Tools/frameworks we've developed
      ],
      "templates": [
        // Document templates and methodologies we can reuse
      ]
    }}
  }}
}}

FOCUS: Create winning architecture leveraging ITSS Global's proven experience and past proposal success."""

            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(response.content[0].text)
            result['generation_timestamp'] = datetime.now().isoformat()
            result['based_on_past_proposals'] = past_context.get('sources_analyzed', 0)
            
            return result

        except Exception as e:
            return {
                'error': str(e),
                'fallback_architecture': 'Basic cloud-native microservices architecture'
            }

    def _claude_intelligent_requirement_categorization(self, requirements: List[str], past_context: Dict) -> Dict[str, Any]:
        """Intelligent requirement categorization using past proposal intelligence"""
        
        if not self.anthropic_client:
            return {'requirements': requirements}

        try:
            # Extract past intelligence
            proven_capabilities = past_context.get('capability_intelligence', {}).get('proven_capabilities', [])
            missing_capabilities = past_context.get('gap_analysis', {}).get('missing_capabilities', [])
            
            prompt = f"""You are categorizing requirements for ITSS Global using past proposal intelligence.

REQUIREMENTS TO CATEGORIZE:
{json.dumps(requirements, indent=2)}

PAST PROPOSAL INTELLIGENCE:
Proven Capabilities: {proven_capabilities}
Missing/New Capabilities: {missing_capabilities}
Technology Expertise: {past_context.get('capability_intelligence', {}).get('technology_expertise', [])}

INTELLIGENT CATEGORIZATION:
{{
  "critical_requirements": {{
    "must_have_functional": [
      // Critical functional requirements
    ],
    "must_have_non_functional": [
      // Critical non-functional requirements (performance, security, etc.)
    ],
    "compliance_mandatory": [
      // Mandatory regulatory/compliance requirements
    ]
  }},
  
  "experience_based_categorization": {{
    "requirements_we_excel_at": [
      // Requirements matching our proven capabilities
    ],
    "requirements_we_have_done_before": [
      // Requirements from past projects but not core strengths
    ],
    "new_requirements_for_us": [
      // Requirements we haven't handled before
    ],
    "challenging_requirements": [
      // Requirements that will be difficult/risky
    ]
  }},
  
  "implementation_complexity": {{
    "low_complexity": [
      // Requirements we can deliver easily based on experience
    ],
    "medium_complexity": [
      // Requirements needing moderate effort
    ],
    "high_complexity": [
      // Requirements needing significant effort/research
    ]
  }},
  
  "competitive_positioning": {{
    "differentiator_requirements": [
      // Requirements where we can differentiate vs competitors
    ],
    "table_stakes": [
      // Standard requirements everyone can meet
    ],
    "potential_weaknesses": [
      // Requirements where competitors might be stronger
    ]
  }},
  
  "proposal_strategy_impact": {{
    "emphasize_heavily": [
      // Requirements to emphasize in proposal (our strengths)
    ],
    "address_thoroughly": [
      // Requirements to address but not emphasize
    ],
    "mitigate_risks": [
      // Requirements where we need to address perceived weaknesses
    ]
  }}
}}

FOCUS: Strategic categorization for competitive advantage."""

            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(response.content[0].text)
            result['categorization_timestamp'] = datetime.now().isoformat()
            result['based_on_past_intelligence'] = True
            
            return result

        except Exception as e:
            return {
                'error': str(e),
                'critical_requirements': {'must_have_functional': requirements}
            }

    def _generate_implementation_strategy(self, categorized_requirements: Dict, past_context: Dict) -> Dict[str, Any]:
        """Generate implementation strategy based on past proposal success"""
        
        if not self.anthropic_client:
            return {'strategy': 'Standard implementation approach'}

        try:
            reusable_content = past_context.get('reusable_content_sections', {})
            implementation_content = reusable_content.get('implementation_methodology', {})
            
            prompt = f"""Generate implementation strategy for ITSS Global using past proposal intelligence.

CATEGORIZED REQUIREMENTS:
{json.dumps(categorized_requirements, indent=2)}

PAST IMPLEMENTATION INTELLIGENCE:
Available Content: {implementation_content.get('content', 'None')[:500]}
Confidence: {implementation_content.get('confidence', 0.0)}
Proven Approaches: {past_context.get('capability_intelligence', {}).get('proven_capabilities', [])}

STRATEGY GENERATION:
{{
  "implementation_methodology": {{
    "overall_approach": "agile|waterfall|hybrid|custom",
    "phases": [
      {{
        "name": "Phase name",
        "duration": "X weeks", 
        "key_activities": ["activity1"],
        "deliverables": ["deliverable1"],
        "success_criteria": ["criteria1"],
        "based_on_past_project": "reference if available"
      }}
    ],
    "risk_mitigation_strategy": [
      // Risk mitigation based on past experience
    ],
    "quality_assurance_approach": [
      // QA approaches from past success
    ]
  }},
  
  "team_structure": {{
    "recommended_roles": [
      // Roles based on past successful team structures
    ],
    "key_skills_needed": [
      // Skills based on requirements and past experience
    ],
    "external_expertise": [
      // Where we might need external help
    ]
  }},
  
  "timeline_strategy": {{
    "aggressive_timeline": "X months",
    "realistic_timeline": "Y months", 
    "conservative_timeline": "Z months",
    "critical_path_items": [
      // Items that could delay the project
    ]
  }},
  
  "success_factors": {{
    "key_success_factors": [
      // What made past projects successful
    ],
    "potential_pitfalls": [
      // What to avoid based on past experience
    ],
    "client_engagement_strategy": [
      // How to engage client based on past success
    ]
  }}
}}

FOCUS: Winning implementation strategy leveraging ITSS Global's proven methodologies."""

            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(response.content[0].text)
            result['strategy_timestamp'] = datetime.now().isoformat()
            
            return result

        except Exception as e:
            return {
                'error': str(e),
                'fallback_strategy': 'Agile implementation with iterative delivery'
            }

    def _analyze_risks_with_past_intelligence(self, requirements: List[str], past_context: Dict) -> Dict[str, Any]:
        """Analyze risks using past proposal intelligence and lessons learned"""
        
        if not self.anthropic_client:
            return {'risks': ['Standard implementation risks']}

        try:
            gap_analysis = past_context.get('gap_analysis', {})
            
            prompt = f"""Analyze risks for ITSS Global using past proposal intelligence and lessons learned.

REQUIREMENTS:
{json.dumps(requirements, indent=2)}

PAST INTELLIGENCE:
Missing Capabilities: {gap_analysis.get('missing_capabilities', [])}
New Requirements: {gap_analysis.get('new_requirements', [])}
Research Needed: {gap_analysis.get('research_needed', [])}

RISK ANALYSIS:
{{
  "technical_risks": [
    {{
      "risk": "Risk description",
      "probability": "high|medium|low",
      "impact": "high|medium|low", 
      "mitigation": "How to mitigate based on experience",
      "lessons_from_past": "What we learned before"
    }}
  ],
  
  "commercial_risks": [
    {{
      "risk": "Commercial risk",
      "probability": "high|medium|low",
      "impact": "high|medium|low",
      "mitigation": "Mitigation strategy",
      "past_experience": "How we handled similar risks before"
    }}
  ],
  
  "execution_risks": [
    {{
      "risk": "Execution risk",
      "probability": "high|medium|low", 
      "impact": "high|medium|low",
      "mitigation": "How to mitigate",
      "success_factors": "What ensures success"
    }}
  ],
  
  "competitive_risks": [
    {{
      "risk": "Competitive disadvantage",
      "mitigation": "How to address",
      "differentiation_opportunity": "How to turn into advantage"
    }}
  ],
  
  "overall_risk_assessment": {{
    "risk_level": "high|medium|low",
    "confidence_in_delivery": 0.0-1.0,
    "key_risk_factors": ["factor1", "factor2"],
    "success_probability": 0.0-1.0
  }}
}}

FOCUS: Comprehensive risk analysis leveraging ITSS Global's past project experience."""

            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(response.content[0].text)
            result['risk_analysis_timestamp'] = datetime.now().isoformat()
            
            return result

        except Exception as e:
            return {
                'error': str(e),
                'overall_risk_assessment': {'risk_level': 'medium', 'confidence_in_delivery': 0.7}
            }

    def _generate_competitive_positioning(self, requirements: List[str], past_context: Dict) -> Dict[str, Any]:
        """Generate competitive positioning based on past proposal success"""
        
        if not self.anthropic_client:
            return {'positioning': 'Standard competitive positioning'}

        try:
            capability_intelligence = past_context.get('capability_intelligence', {})
            
            prompt = f"""Generate competitive positioning for ITSS Global using past proposal intelligence.

REQUIREMENTS:
{json.dumps(requirements, indent=2)}

PAST SUCCESS INTELLIGENCE:
Proven Capabilities: {capability_intelligence.get('proven_capabilities', [])}
Technology Expertise: {capability_intelligence.get('technology_expertise', [])}
Competitive Differentiators: {capability_intelligence.get('competitive_differentiators', [])}
Industry Experience: {capability_intelligence.get('industry_experience', [])}

COMPETITIVE POSITIONING:
{{
  "key_differentiators": [
    {{
      "differentiator": "What makes us unique",
      "evidence": "Past proposal/project evidence",
      "client_benefit": "Benefit to client",
      "competitive_advantage": "Why competitors can't match this"
    }}
  ],
  
  "strength_areas": [
    {{
      "strength": "Our core strength",
      "supporting_evidence": ["evidence1", "evidence2"],
      "requirements_where_this_helps": ["requirement1"],
      "messaging": "How to position this strength"
    }}
  ],
  
  "competitive_strategy": {{
    "primary_positioning": "How to position ITSS vs competitors",
    "secondary_messaging": ["supporting message1", "supporting message2"],
    "proof_points": ["proof1", "proof2"],
    "case_study_references": ["case1", "case2"]
  }},
  
  "addressing_weaknesses": [
    {{
      "potential_weakness": "Where competitors might be stronger",
      "mitigation_strategy": "How to address this",
      "alternative_positioning": "How to reframe this"
    }}
  ],
  
  "win_themes": [
    {{
      "theme": "Key win theme",
      "supporting_capabilities": ["capability1"],
      "client_value_proposition": "Value to client",
      "differentiation": "Why us vs competition"
    }}
  ]
}}

FOCUS: Winning competitive positioning leveraging ITSS Global's proven track record."""

            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(response.content[0].text)
            result['positioning_timestamp'] = datetime.now().isoformat()
            
            return result

        except Exception as e:
            return {
                'error': str(e),
                'fallback_positioning': 'ITSS Global - Proven Temenos implementation partner'
            }

# Helper function for integration
def get_enhanced_requirements_engineering_agent():
    """Get enhanced requirements engineering agent instance"""
    return EnhancedRequirementsEngineeringAgent()