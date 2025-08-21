# Real AI-Powered Analysis System
# Supports multiple AI providers (Claude, OpenAI) with fallback

import json
import os
from datetime import datetime
import re
from typing import List, Dict, Any
from ai_providers import get_ai_manager, AIProviderManager
from ai_response_manager import AIResponseManager

class RealAnalysisSystem:
    def __init__(self, project, ai_provider: str = None):
        self.project = project
        self.ai_manager = get_ai_manager()
        self.preferred_provider = ai_provider
        self.proposal_manager = self._get_proposal_manager()
    
    def _get_proposal_manager(self):
        """Initialize proposal manager for vector search"""
        try:
            from proposal_manager import get_proposal_manager
            return get_proposal_manager()
        except Exception as e:
            print(f"Warning: Could not initialize proposal manager: {e}")
            return None
    
    def _call_ai_api(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Call AI API with provider fallback"""
        result = self.ai_manager.chat_completion(
            messages, 
            provider=self.preferred_provider,
            **kwargs
        )
        
        if result['success']:
            return result['content']
        else:
            raise Exception(f"AI API error: {result['error']}")
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get current AI provider status"""
        return self.ai_manager.get_provider_status()
    
    def extract_clarification_items(self, content: str, max_retries: int = 2, project_id: str = None) -> List[Dict]:
        """Extract items that need clarification from RFP content"""
        if not self.ai_manager.available_providers:
            return self._fallback_clarification_items("No AI providers available")
        
        # Get context from past proposals
        context_info = self._get_vector_context(content)
        context_prompt = self._format_context_for_prompt(context_info, "clarification")
        
        prompt = f"""
        Analyze this RFP content and identify items that are unclear, ambiguous, or missing important details:
        
        {content[:15000]}
        
        {context_prompt}
        
        Find and categorize clarification items into these categories:
        1. UNCLEAR_REQUIREMENTS - vague or ambiguous specifications
        2. MISSING_INFORMATION - referenced but not provided details
        3. CONTRADICTORY_STATEMENTS - conflicting requirements
        4. INCOMPLETE_SPECIFICATIONS - partial technical details
        5. UNDEFINED_TERMS - technical terms without clear definitions
        6. MISSING_DEADLINES - referenced dates without specifics
        7. UNCLEAR_EVALUATION - evaluation criteria not well defined
        
        For each item, provide:
        - category: One of the categories above
        - description: Clear description of what needs clarification
        - impact_level: High/Medium/Low based on potential project impact
        - suggested_questions: Array of 2-3 specific questions to ask
        - past_experience: If available from context, note how similar issues were handled in past proposals
        
        Return ONLY a JSON array of clarification items. Example:
        [
            {{
                "category": "UNCLEAR_REQUIREMENTS",
                "description": "Performance requirements mention 'high availability' but don't specify uptime percentage",
                "impact_level": "High",
                "suggested_questions": [
                    "What specific uptime percentage is required (99.9%, 99.99%)?",
                    "Are there specific maintenance windows allowed?",
                    "What are the penalties for not meeting availability targets?"
                ],
                "past_experience": "In similar projects, we typically delivered 99.95% uptime with 4-hour maintenance windows"
            }}
        ]
        
        Focus on items that could significantly impact project success, timeline, or cost.
        """
        
        for attempt in range(max_retries + 1):
            try:
                print(f"❓ Extracting clarification items (attempt {attempt + 1})")
                
                # Store AI interaction if project_id provided
                ai_response = None
                if project_id:
                    from ai_response_manager import AIResponseManager
                    ai_response = AIResponseManager.create_response(
                        project_id=project_id,
                        request_type='clarification_extraction',
                        prompt=prompt,
                        ai_provider=self.preferred_provider or 'auto',
                        ai_model='auto',
                        context_data={'content': content[:10000], 'content_length': len(content), 'attempt': attempt + 1}
                    )
                
                response_content = self._call_ai_api(
                    messages=[
                        {"role": "system", "content": "You are an expert RFP analyst who identifies unclear or missing information in tender documents."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=3000
                )
                
                response_text = response_content.strip()
                # Clean up any markdown formatting
                response_text = re.sub(r'```json\n?', '', response_text)
                response_text = re.sub(r'```\n?', '', response_text)
                
                parsed_result = json.loads(response_text)
                print(f"✅ Successfully extracted {len(parsed_result)} clarification items")
                
                # Complete AI response storage
                if ai_response:
                    AIResponseManager.complete_response(
                        response=ai_response,
                        raw_response=response_content,
                        parsed_response=parsed_result,
                        confidence_score=0.8,  # Default confidence
                        metadata={'items_extracted': len(parsed_result), 'attempt': attempt + 1}
                    )
                
                return parsed_result
                
            except json.JSONDecodeError as e:
                error_msg = f"JSON parsing error on attempt {attempt + 1}: {e}"
                print(error_msg)
                
                # Mark AI response as failed
                if ai_response:
                    AIResponseManager.fail_response(
                        response=ai_response,
                        error_message=error_msg,
                        partial_response=response_content
                    )
                    
                if attempt == max_retries:
                    return self._fallback_clarification_items(error_msg)
                
            except Exception as e:
                error_msg = f"API error on attempt {attempt + 1}: {e}"
                print(error_msg)
                
                # Mark AI response as failed
                if ai_response:
                    AIResponseManager.fail_response(
                        response=ai_response,
                        error_message=error_msg
                    )
                    
                if attempt == max_retries:
                    return self._fallback_clarification_items(error_msg)
        
        return self._fallback_clarification_items("Maximum retries exceeded")
    
    def identify_risks_and_constraints(self, content: str, max_retries: int = 2, project_id: str = None) -> List[Dict]:
        """Identify risks, guarantees, pre-conditions, and cashflow impacts"""
        if not self.ai_manager.available_providers:
            return self._fallback_risks_constraints("No AI providers available")
        
        # Get context from past proposals
        context_info = self._get_vector_context(content)
        context_prompt = self._format_context_for_prompt(context_info, "risks")
        
        prompt = f"""
        Analyze this RFP for risks and constraints that could affect project execution and cashflow:
        
        {content[:15000]}
        
        {context_prompt}
        
        Identify and categorize risks into these types:
        1. GUARANTEE_REQUIRED - performance bonds, warranties, liability coverage
        2. PRE_CONDITION - requirements that must be met before project start
        3. PAYMENT_TERMS - cashflow impact from payment schedules
        4. PENALTY_RISK - late delivery, performance penalties
        5. COMPLIANCE_RISK - regulatory or legal requirements
        6. TECHNICAL_RISK - challenging technical requirements
        7. OPERATIONAL_RISK - resource, timeline, or scope risks
        8. FINANCIAL_RISK - cost overruns, currency, budget constraints
        
        For each risk, specify:
        - risk_type: One of the categories above
        - description: Clear description of the risk
        - cashflow_impact: Positive/Negative/Neutral impact on cashflow
        - severity_level: High/Medium/Low based on potential impact
        - mitigation_strategy: Suggested approach to mitigate the risk
        - financial_impact: Estimated cost impact if known
        - past_experience: If available from context, how similar risks were handled
        
        Return ONLY a JSON array of risk assessments. Example:
        [
            {{
                "risk_type": "GUARANTEE_REQUIRED",
                "description": "Performance bond of 10% of contract value required",
                "cashflow_impact": "Negative",
                "severity_level": "Medium",
                "mitigation_strategy": "Secure bank guarantee or insurance bond",
                "financial_impact": "10% of contract value locked up",
                "past_experience": "Successfully managed similar bonds in 3 previous projects"
            }}
        ]
        
        Focus on risks that could significantly impact project viability or profitability.
        """
        
        for attempt in range(max_retries + 1):
            try:
                print(f"🔍 Analyzing risks and constraints (attempt {attempt + 1})")
                
                # Store AI interaction if project_id provided
                ai_response = None
                if project_id:
                    from ai_response_manager import AIResponseManager
                    ai_response = AIResponseManager.create_response(
                        project_id=project_id,
                        request_type='risk_analysis',
                        prompt=prompt,
                        ai_provider=self.preferred_provider or 'auto',
                        ai_model='auto',
                        context_data={'content': content[:10000], 'content_length': len(content), 'attempt': attempt + 1}
                    )
                
                response_content = self._call_ai_api(
                    messages=[
                        {"role": "system", "content": "You are an expert risk analyst specialized in evaluating RFP documents for potential risks, constraints, and financial impacts."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=3000
                )
                
                response_text = response_content.strip()
                response_text = re.sub(r'```json\n?', '', response_text)
                response_text = re.sub(r'```\n?', '', response_text)
                
                parsed_result = json.loads(response_text)
                print(f"✅ Successfully analyzed {len(parsed_result)} risks and constraints")
                
                # Complete AI response storage
                if ai_response:
                    AIResponseManager.complete_response(
                        response=ai_response,
                        raw_response=response_content,
                        parsed_response=parsed_result,
                        confidence_score=0.8,  # Default confidence
                        metadata={'risks_identified': len(parsed_result), 'attempt': attempt + 1}
                    )
                
                return parsed_result
                
            except json.JSONDecodeError as e:
                error_msg = f"JSON parsing error on attempt {attempt + 1}: {e}"
                print(error_msg)
                
                # Mark AI response as failed
                if ai_response:
                    AIResponseManager.fail_response(
                        response=ai_response,
                        error_message=error_msg,
                        partial_response=response_content
                    )
                    
                if attempt == max_retries:
                    return self._fallback_risks_constraints(error_msg)
                
            except Exception as e:
                error_msg = f"API error on attempt {attempt + 1}: {e}"
                print(error_msg)
                
                # Mark AI response as failed
                if ai_response:
                    AIResponseManager.fail_response(
                        response=ai_response,
                        error_message=error_msg
                    )
                    
                if attempt == max_retries:
                    return self._fallback_risks_constraints(error_msg)
        
        return self._fallback_risks_constraints("Maximum retries exceeded")
    
    def extract_deadlines_and_milestones(self, content: str, max_retries: int = 2, project_id: str = None) -> List[Dict]:
        """Extract all deadlines, milestones, penalties, and guarantees"""
        if not self.ai_manager.available_providers:
            return self._fallback_deadlines_milestones("No AI providers available")
        
        # Get context from past proposals
        context_info = self._get_vector_context(content)
        context_prompt = self._format_context_for_prompt(context_info, "deadlines")
        
        prompt = f"""
        Extract all time-sensitive information from this RFP content:
        
        {content[:15000]}
        
        {context_prompt}
        
        Find and categorize into these types:
        1. SUBMISSION_DEADLINE - proposal submission dates
        2. PROJECT_MILESTONE - key delivery dates and milestones
        3. PENALTY - late delivery or performance penalties
        4. PERFORMANCE_GUARANTEE - SLAs, uptime requirements, KPIs
        5. BID_BOND - required bonds and amounts
        6. CONTRACT_TERM - notice periods, contract duration, renewal terms
        7. PAYMENT_SCHEDULE - payment milestones and terms
        
        For each item, extract:
        - type: One of the categories above
        - title: Brief title or name
        - description: Full description of the requirement
        - date_text: Exact date/timeframe text from document
        - penalty_amount: Penalty cost if applicable
        - critical_level: Critical/Important/Standard based on impact
        - past_experience: If available from context, how similar deadlines were managed
        
        Return ONLY a JSON array of deadline items. Example:
        [
            {{
                "type": "SUBMISSION_DEADLINE",
                "title": "Technical Proposal Submission",
                "description": "All technical proposals must be submitted by 5:00 PM local time",
                "date_text": "March 15, 2025 at 5:00 PM",
                "penalty_amount": null,
                "critical_level": "Critical",
                "past_experience": "Successfully met similar deadlines in 5 previous projects"
            }},
            {{
                "type": "PENALTY",
                "title": "Late Delivery Penalty",
                "description": "Penalty for late delivery of software modules",
                "date_text": "After agreed delivery date",
                "penalty_amount": "1% of contract value per week",
                "critical_level": "High"
            }}
        ]
        
        Focus on items that have specific dates, deadlines, or financial implications.
        """
        
        for attempt in range(max_retries + 1):
            try:
                print(f"📅 Extracting deadlines and milestones (attempt {attempt + 1})")
                
                # Store AI interaction if project_id provided
                ai_response = None
                if project_id:
                    from ai_response_manager import AIResponseManager
                    ai_response = AIResponseManager.create_response(
                        project_id=project_id,
                        request_type='deadline_extraction',
                        prompt=prompt,
                        ai_provider=self.preferred_provider or 'auto',
                        ai_model='auto',
                        context_data={'content': content[:10000], 'content_length': len(content), 'attempt': attempt + 1}
                    )
                
                response_content = self._call_ai_api(
                    messages=[
                        {"role": "system", "content": "You are an expert project manager specialized in identifying critical deadlines, milestones, and penalties in RFP documents."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=3000
                )
                
                response_text = response_content.strip()
                response_text = re.sub(r'```json\n?', '', response_text)
                response_text = re.sub(r'```\n?', '', response_text)
                
                parsed_result = json.loads(response_text)
                print(f"✅ Successfully extracted {len(parsed_result)} deadlines and milestones")
                
                # Complete AI response storage
                if ai_response:
                    AIResponseManager.complete_response(
                        response=ai_response,
                        raw_response=response_content,
                        parsed_response=parsed_result,
                        confidence_score=0.8,  # Default confidence
                        metadata={'deadlines_extracted': len(parsed_result), 'attempt': attempt + 1}
                    )
                
                return parsed_result
                
            except json.JSONDecodeError as e:
                error_msg = f"JSON parsing error on attempt {attempt + 1}: {e}"
                print(error_msg)
                
                # Mark AI response as failed
                if ai_response:
                    AIResponseManager.fail_response(
                        response=ai_response,
                        error_message=error_msg,
                        partial_response=response_content
                    )
                    
                if attempt == max_retries:
                    return self._fallback_deadlines_milestones(error_msg)
                
            except Exception as e:
                error_msg = f"API error on attempt {attempt + 1}: {e}"
                print(error_msg)
                
                # Mark AI response as failed
                if ai_response:
                    AIResponseManager.fail_response(
                        response=ai_response,
                        error_message=error_msg
                    )
                    
                if attempt == max_retries:
                    return self._fallback_deadlines_milestones(error_msg)
        
        return self._fallback_deadlines_milestones("Maximum retries exceeded")
    
    def generate_go_no_go_recommendation(self, clarification_items, risks_constraints, deadlines_milestones, max_retries: int = 2, project_id: str = None) -> Dict:
        """Generate overall go/no-go recommendation based on analysis"""
        if not self.ai_manager.available_providers:
            return self._fallback_go_no_go("No AI providers available")
        
        analysis_summary = {
            "clarification_count": len(clarification_items),
            "high_impact_clarifications": len([item for item in clarification_items if item.get('impact_level') == 'High']),
            "risk_count": len(risks_constraints),
            "high_severity_risks": len([risk for risk in risks_constraints if risk.get('severity_level') == 'High']),
            "critical_deadlines": len([dl for dl in deadlines_milestones if dl.get('critical_level') == 'Critical']),
            "penalty_items": len([dl for dl in deadlines_milestones if dl.get('type') == 'PENALTY'])
        }
        
        prompt = f"""
        Based on the following analysis of an RFP, provide a go/no-go recommendation:
        
        ANALYSIS SUMMARY:
        - Total clarification items: {analysis_summary['clarification_count']}
        - High-impact clarifications: {analysis_summary['high_impact_clarifications']}
        - Total risks identified: {analysis_summary['risk_count']}
        - High-severity risks: {analysis_summary['high_severity_risks']}
        - Critical deadlines: {analysis_summary['critical_deadlines']}
        - Penalty clauses: {analysis_summary['penalty_items']}
        
        KEY CLARIFICATION ITEMS:
        {json.dumps(clarification_items[:5], indent=2)}
        
        KEY RISKS:
        {json.dumps(risks_constraints[:5], indent=2)}
        
        CRITICAL DEADLINES:
        {json.dumps([dl for dl in deadlines_milestones if dl.get('critical_level') == 'Critical'][:3], indent=2)}
        
        Provide a recommendation as JSON with these fields:
        - recommendation: "GO", "NO_GO", or "CONDITIONAL"
        - confidence_score: Integer from 1-100
        - reasoning: Detailed explanation of recommendation
        - key_concerns: Array of main concerns
        - success_factors: Array of factors supporting success
        - conditions_for_go: Array of conditions that must be met (if CONDITIONAL)
        
        Consider:
        - Number and severity of risks
        - Clarity of requirements
        - Feasibility of deadlines
        - Financial viability
        - Technical complexity
        - Compliance requirements
        
        Return ONLY valid JSON.
        """
        
        for attempt in range(max_retries + 1):
            try:
                print(f"🎯 Generating go/no-go recommendation (attempt {attempt + 1})")
                
                # Store AI interaction if project_id provided
                ai_response = None
                if project_id:
                    from ai_response_manager import AIResponseManager
                    ai_response = AIResponseManager.create_response(
                        project_id=project_id,
                        request_type='go_no_go_recommendation',
                        prompt=prompt,
                        ai_provider=self.preferred_provider or 'auto',
                        ai_model='auto',
                        context_data={
                            'clarifications': len(clarification_items),
                            'risks': len(risks_constraints),
                            'deadlines': len(deadlines_milestones),
                            'attempt': attempt + 1
                        }
                    )
                
                response_content = self._call_ai_api(
                    messages=[
                        {"role": "system", "content": "You are an expert business analyst who provides go/no-go recommendations for RFP opportunities based on risk analysis, feasibility, and strategic fit."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000
                )
                
                response_text = response_content.strip()
                response_text = re.sub(r'```json\n?', '', response_text)
                response_text = re.sub(r'```\n?', '', response_text)
                
                parsed_result = json.loads(response_text)
                print(f"✅ Successfully generated {parsed_result.get('recommendation', 'Unknown')} recommendation")
                
                # Complete AI response storage
                if ai_response:
                    AIResponseManager.complete_response(
                        response=ai_response,
                        raw_response=response_content,
                        parsed_response=parsed_result,
                        confidence_score=parsed_result.get('confidence_score', 50) / 100.0,  # Convert to 0-1 scale
                        metadata={
                            'recommendation': parsed_result.get('recommendation'),
                            'confidence': parsed_result.get('confidence_score'),
                            'attempt': attempt + 1
                        }
                    )
                
                return parsed_result
                
            except json.JSONDecodeError as e:
                error_msg = f"JSON parsing error on attempt {attempt + 1}: {e}"
                print(error_msg)
                
                # Mark AI response as failed
                if ai_response:
                    AIResponseManager.fail_response(
                        response=ai_response,
                        error_message=error_msg,
                        partial_response=response_content
                    )
                    
                if attempt == max_retries:
                    return self._fallback_go_no_go(error_msg)
                
            except Exception as e:
                error_msg = f"API error on attempt {attempt + 1}: {e}"
                print(error_msg)
                
                # Mark AI response as failed
                if ai_response:
                    AIResponseManager.fail_response(
                        response=ai_response,
                        error_message=error_msg
                    )
                    
                if attempt == max_retries:
                    return self._fallback_go_no_go(error_msg)
        
        return self._fallback_go_no_go("Maximum retries exceeded")

    def generate_detailed_analysis(self, content: str, max_retries: int = 2, project_id: str = None) -> Dict:
        """Generate detailed project analysis and executive summary"""
        if not self.ai_manager.available_providers:
            return self._fallback_detailed_analysis("No AI providers available")
        
        prompt = f"""
        You are an AI Response Manager providing an executive summary and project assessment for TOP MANAGEMENT. 
        Analyze the following RFP/tender documents and provide a comprehensive overview that executives can use to make strategic decisions.

        DOCUMENTS TO ANALYZE:
        {content[:8000]}

        Provide a management-focused analysis with the following structure:

        {{
            "executive_summary": "EXECUTIVE SUMMARY FOR TOP MANAGEMENT: A concise 2-3 paragraph overview that captures the essence of this opportunity, its strategic value, key challenges, and business impact. Write this as if briefing the CEO/Board on whether we should pursue this project.",
            "business_case": {{
                "strategic_value": "Why this project matters strategically to our organization",
                "market_opportunity": "Market size, competitive advantage, or strategic positioning benefits",
                "revenue_potential": "Expected financial benefits, contract value, or revenue impact",
                "risk_vs_reward": "High-level assessment of opportunity vs. risks"
            }},
            "project_overview": {{
                "what_we_are_building": "In plain business terms, what exactly are we being asked to deliver",
                "timeline_overview": "Key phases and overall project duration",
                "client_profile": "Who is the client and why this relationship matters",
                "success_metrics": "How success will be measured"
            }},
            "key_requirements": [
                "Top 5-7 most critical requirements that define project success",
                "Focus on business-critical items, not technical details"
            ],
            "technical_complexity": {{
                "complexity_level": "Low/Medium/High with clear reasoning",
                "key_technologies": "Main technical platforms/technologies required",
                "integration_challenges": "Major technical integration or compatibility issues",
                "our_capability_fit": "How well this aligns with our current technical capabilities"
            }},
            "management_considerations": {{
                "resource_requirements": "High-level view of team size, skillsets, and duration needed",
                "budget_implications": "Estimated investment required (development, infrastructure, etc.)",
                "timeline_pressure": "Any time constraints or deadline pressure factors",
                "competitive_landscape": "Are we competing against major players?"
            }},
            "go_no_go_factors": {{
                "pros": ["Top reasons why this is a good opportunity"],
                "cons": ["Main concerns or red flags to consider"],
                "critical_success_factors": ["What must go right for this project to succeed"]
            }}
        }}

        Focus on providing ACTIONABLE INTELLIGENCE for executive decision-making:
        1. Strategic business value and competitive positioning
        2. Financial opportunity and resource requirements  
        3. Risk assessment and mitigation needs
        4. Alignment with organizational capabilities
        5. Market timing and competitive factors

        Write in executive language - clear, concise, focused on business impact.
        Respond only with valid JSON matching the structure above.
        """

        for attempt in range(max_retries + 1):
            ai_response = None
            try:
                # Create AI response record
                if project_id:
                    ai_response = AIResponseManager.create_response(
                        project_id=project_id,
                        request_type='detailed_analysis',
                        prompt=prompt[:1000] + "..." if len(prompt) > 1000 else prompt,
                        ai_provider=self.ai_manager.preferred_provider,
                        ai_model='claude-sonnet-4',
                        context_data={'analysis_type': 'comprehensive_executive_summary'}
                    )

                response_content = self._call_ai_api(
                    messages=[
                        {"role": "system", "content": "You are an AI Response Manager providing executive analysis for top management. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=4000
                )
                
                response = response_content.strip()
                # Clean up any markdown formatting
                response = re.sub(r'```json\n?', '', response)
                response = re.sub(r'```\n?', '', response)
                
                try:
                    # Parse JSON response
                    detailed_analysis = json.loads(response)
                    
                    # Validate required fields
                    required_fields = ['executive_summary', 'business_case', 'project_overview', 'key_requirements']
                    if all(field in detailed_analysis for field in required_fields):
                        print(f"✅ Detailed analysis generated successfully")
                        
                        # Complete AI response storage
                        if ai_response:
                            AIResponseManager.complete_response(
                                response=ai_response,
                                raw_response=response,
                                parsed_response=detailed_analysis,
                                metadata={
                                    'requirements_count': len(detailed_analysis.get('key_requirements', [])),
                                    'business_case_fields': len([k for k in detailed_analysis.get('business_case', {}).keys()]),
                                    'complexity': detailed_analysis.get('technical_complexity', {}).get('complexity_level', 'Not specified'),
                                    'analysis_scope': 'comprehensive_executive_summary'
                                }
                            )
                        
                        return detailed_analysis
                    else:
                        continue
                        
                except (json.JSONDecodeError, KeyError):
                    continue

            except Exception as e:
                error_msg = f"API error on attempt {attempt + 1}: {e}"
                print(error_msg)
                
                # Mark AI response as failed
                if ai_response:
                    AIResponseManager.fail_response(
                        response=ai_response,
                        error_message=error_msg
                    )
                    
                if attempt == max_retries:
                    return self._fallback_detailed_analysis(error_msg)
        
        return self._fallback_detailed_analysis("Maximum retries exceeded")

    def generate_assumptions_analysis(self, content: str, max_retries: int = 2, project_id: str = None) -> Dict:
        """Generate comprehensive assumptions analysis"""
        if not self.ai_manager.available_providers:
            return self._fallback_assumptions_analysis("No AI providers available")
        
        prompt = f"""
        Analyze the following RFP/tender documents and identify key assumptions, strategic insights, and recommendations:

        DOCUMENTS TO ANALYZE:
        {content[:8000]}

        Please provide a comprehensive assumptions analysis with the following structure:

        {{
            "key_assumptions": [
                {{
                    "category": "Technical|Business|Resource|Timeline|External",
                    "description": "Clear description of the assumption",
                    "impact": "Low|Medium|High",
                    "risk_if_wrong": "What happens if this assumption is incorrect"
                }}
            ],
            "strategic_recommendations": [
                "Key strategic recommendations for this project",
                "Important considerations for decision-making",
                "Recommended approaches or strategies"
            ],
            "risk_factors": [
                "Implicit risks based on document analysis",
                "Assumptions that could become major risks",
                "Dependencies that may impact success"
            ],
            "clarification_needs": [
                "Questions that should be asked to validate assumptions",
                "Areas where more information is needed"
            ],
            "success_factors": [
                "Critical factors for project success",
                "Key capabilities or resources needed"
            ]
        }}

        Focus on:
        1. Implicit assumptions not explicitly stated in documents
        2. Strategic insights about project approach
        3. Risk factors that may not be obvious
        4. Recommendations for improving chances of success
        5. Questions that should be asked to clarify ambiguities

        Respond only with valid JSON matching the structure above.
        """

        for attempt in range(max_retries + 1):
            ai_response = None
            try:
                # Create AI response record
                if project_id:
                    ai_response = AIResponseManager.create_response(
                        project_id=project_id,
                        request_type='assumptions_analysis',
                        prompt=prompt[:1000] + "..." if len(prompt) > 1000 else prompt,
                        ai_provider=self.ai_manager.preferred_provider,
                        ai_model='claude-sonnet-4',
                        context_data={'analysis_type': 'strategic_assumptions_analysis'}
                    )

                response_content = self._call_ai_api(
                    messages=[
                        {"role": "system", "content": "You are an expert project assumptions analyst. Always respond with valid JSON matching the requested structure."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=4000
                )
                
                response = response_content.strip()
                # Clean up any markdown formatting
                response = re.sub(r'```json\n?', '', response)
                response = re.sub(r'```\n?', '', response)
                
                try:
                    # Parse JSON response
                    assumptions_analysis = json.loads(response)
                    
                    # Validate required fields
                    required_fields = ['key_assumptions', 'strategic_recommendations', 'risk_factors']
                    if all(field in assumptions_analysis for field in required_fields):
                        print(f"✅ Assumptions analysis generated successfully")
                        
                        # Complete AI response storage
                        if ai_response:
                            AIResponseManager.complete_response(
                                response=ai_response,
                                raw_response=response,
                                parsed_response=assumptions_analysis,
                                metadata={
                                    'assumptions_count': len(assumptions_analysis.get('key_assumptions', [])),
                                    'recommendations_count': len(assumptions_analysis.get('strategic_recommendations', [])),
                                    'risk_factors_count': len(assumptions_analysis.get('risk_factors', [])),
                                    'success_factors_count': len(assumptions_analysis.get('success_factors', [])),
                                    'analysis_scope': 'strategic_assumptions_analysis'
                                }
                            )
                        
                        return assumptions_analysis
                    else:
                        continue
                        
                except (json.JSONDecodeError, KeyError):
                    continue

            except Exception as e:
                error_msg = f"API error on attempt {attempt + 1}: {e}"
                print(error_msg)
                
                # Mark AI response as failed
                if ai_response:
                    AIResponseManager.fail_response(
                        response=ai_response,
                        error_message=error_msg
                    )
                    
                if attempt == max_retries:
                    return self._fallback_assumptions_analysis(error_msg)
        
        return self._fallback_assumptions_analysis("Maximum retries exceeded")
    
    # Fallback methods for when AI is not available
    def _fallback_clarification_items(self, reason: str = "AI analysis not available") -> List[Dict]:
        """Fallback clarification items when AI is not available"""
        return [
            {
                "category": "ANALYSIS_FAILURE",
                "description": f"AI analysis failed: {reason}. Manual review required.",
                "impact_level": "High",
                "suggested_questions": [
                    "Please review the RFP manually for unclear requirements",
                    "Identify any missing technical specifications",
                    "Check for undefined terms or ambiguous language",
                    "Investigate why AI analysis failed and consider retry"
                ],
                "failure_reason": reason
            }
        ]
    
    def _fallback_risks_constraints(self, reason: str = "AI analysis not available") -> List[Dict]:
        """Fallback risk assessment when AI is not available"""
        return [
            {
                "risk_type": "ANALYSIS_FAILURE",
                "description": f"AI risk analysis failed: {reason}. Manual assessment required.",
                "cashflow_impact": "Unknown",
                "severity_level": "High",
                "mitigation_strategy": "Conduct thorough manual review of all contract terms, penalties, and requirements",
                "financial_impact": "To be determined through manual analysis",
                "failure_reason": reason
            }
        ]
    
    def _fallback_deadlines_milestones(self, reason: str = "AI analysis not available") -> List[Dict]:
        """Fallback deadline extraction when AI is not available"""
        return [
            {
                "type": "ANALYSIS_FAILURE",
                "title": "Deadline Analysis Failed",
                "description": f"AI deadline extraction failed: {reason}. Please extract deadlines manually.",
                "date_text": "See RFP documents - manual extraction required",
                "penalty_amount": "Unknown - manual review required",
                "critical_level": "Critical",
                "failure_reason": reason
            }
        ]
    
    def _fallback_go_no_go(self, reason: str = "AI analysis not available") -> Dict:
        """Fallback go/no-go recommendation when AI is not available"""
        return {
            "recommendation": "CONDITIONAL",
            "confidence_score": 30,
            "reasoning": f"AI analysis failed ({reason}). Manual review is required to make an informed go/no-go decision.",
            "key_concerns": [
                f"AI analysis failure: {reason}",
                "Unable to perform automated risk assessment", 
                "Manual review required for all contract terms",
                "Consider retrying AI analysis or checking configuration"
            ],
            "success_factors": [
                "Documents uploaded successfully",
                "Project structure in place",
                "Manual analysis capability available"
            ],
            "conditions_for_go": [
                "Resolve AI analysis issues and retry if possible",
                "Complete comprehensive manual review of all RFP documents", 
                "Manually assess technical feasibility and risks",
                "Review financial terms and timeline constraints",
                "Evaluate compliance requirements manually"
            ],
            "failure_reason": reason
        }

    def _fallback_detailed_analysis(self, reason: str = "AI analysis not available") -> Dict:
        """Fallback detailed analysis when AI is not available"""
        return {
            "executive_summary": f"EXECUTIVE SUMMARY FOR TOP MANAGEMENT: AI-powered strategic analysis is currently unavailable ({reason}). This project requires manual executive assessment to determine strategic value, business impact, and go/no-go decision. Immediate action required: engage senior analysts to review RFP documents and provide strategic recommendation within 24-48 hours.",
            "business_case": {
                "strategic_value": f"Strategic assessment unavailable due to: {reason}. Manual evaluation required.",
                "market_opportunity": "Market analysis requires manual competitive intelligence gathering.",
                "revenue_potential": "Financial impact assessment pending manual review of contract terms.",
                "risk_vs_reward": "Risk-reward analysis requires immediate manual assessment by leadership team."
            },
            "project_overview": {
                "what_we_are_building": "Project deliverables require manual analysis of RFP requirements and specifications.",
                "timeline_overview": "Timeline assessment pending manual review of project phases and deadlines.",
                "client_profile": "Client assessment requires manual research and relationship analysis.",
                "success_metrics": "Success criteria need manual identification from contract terms."
            },
            "key_requirements": [
                "Manual review of ALL RFP documents by senior analysts",
                "Strategic assessment by executive team within 48 hours",
                "Technical feasibility review by architecture team",
                "Financial analysis of contract terms and profitability",
                "Risk assessment and mitigation strategy development",
                "Resource planning and capability gap analysis",
                "Competitive positioning and win probability assessment"
            ],
            "technical_complexity": {
                "complexity_level": "Unknown - Immediate Assessment Required",
                "key_technologies": "Technology stack requires manual identification and assessment.",
                "integration_challenges": "Integration complexity requires technical team evaluation.",
                "our_capability_fit": "Capability assessment requires immediate internal review."
            },
            "management_considerations": {
                "resource_requirements": "Resource planning requires immediate management attention and assessment.",
                "budget_implications": "Budget analysis requires manual financial review of contract terms and delivery requirements.",
                "timeline_pressure": "Timeline constraints require immediate project management assessment.",
                "competitive_landscape": "Competitive analysis requires manual market intelligence gathering."
            },
            "go_no_go_factors": {
                "pros": [
                    "Project documents successfully uploaded and accessible for manual review",
                    "Executive team can conduct manual strategic assessment",
                    "Opportunity to demonstrate manual analysis capabilities"
                ],
                "cons": [
                    f"AI analysis system failure: {reason}",
                    "Increased time required for manual assessment (24-48 hours)",
                    "Higher risk of missing critical insights without AI analysis",
                    "Resource intensive manual review process required"
                ],
                "critical_success_factors": [
                    "Immediate engagement of senior analysts for manual review",
                    "Executive team availability for strategic assessment",
                    "Technical team capacity for feasibility analysis",
                    "Resolve AI system issues for future opportunities"
                ]
            },
            "failure_reason": reason,
            "manual_action_required": True,
            "urgency_level": "HIGH - Executive Action Required Within 48 Hours"
        }

    def _fallback_assumptions_analysis(self, reason: str = "AI analysis not available") -> Dict:
        """Fallback assumptions analysis when AI is not available"""
        return {
            "key_assumptions": [
                {
                    "category": "Technical",
                    "description": f"AI assumptions analysis failed ({reason}). Manual identification of technical assumptions required.",
                    "impact": "High",
                    "risk_if_wrong": "Critical project assumptions may be missed without proper analysis"
                },
                {
                    "category": "Business",
                    "description": "Business context and requirements assumptions need manual evaluation",
                    "impact": "High", 
                    "risk_if_wrong": "Misaligned business expectations and project delivery"
                }
            ],
            "strategic_recommendations": [
                "Conduct manual review of all project documentation",
                "Engage with stakeholders to validate assumptions",
                "Perform risk assessment with subject matter experts",
                "Review similar past projects for lessons learned",
                "Consider external consultation for complex requirements"
            ],
            "risk_factors": [
                f"AI analysis capability unavailable: {reason}",
                "Potential blind spots in assumption identification",
                "Increased reliance on manual review processes",
                "Higher risk of missing critical project assumptions",
                "Need for additional validation steps"
            ],
            "clarification_needs": [
                "Verify AI analysis system configuration and connectivity",
                "Review and validate all project assumptions manually",
                "Confirm technical requirements with stakeholders",
                "Validate business objectives and success criteria"
            ],
            "success_factors": [
                "Thorough manual document review process",
                "Stakeholder engagement and validation",
                "Expert review of technical requirements",
                "Systematic assumption documentation",
                "Risk mitigation planning"
            ],
            "failure_reason": reason,
            "manual_action_required": True
        }
    
class RealAnalysisEngine:
    """Real AI-powered analysis engine using multiple providers"""

    def __init__(self, ai_provider=None):
        from ai_providers import get_ai_manager
        self.ai_manager = get_ai_manager()
        self.preferred_provider = ai_provider
        print(f"🤖 Analysis engine initialized with {len(self.ai_manager.available_providers)} AI provider(s)")
        
        if not self.ai_manager.available_providers:
            print("⚠️ No AI providers configured - using fallback analysis")

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
        """Generate real analysis using AI providers"""
        if not self.ai_manager.available_providers:
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

            # Call AI API using new provider system
            messages = [
                {"role": "system", "content": "You are an expert RFP analyst specialized in comprehensive document analysis and proposal generation insights."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            result = self.ai_manager.chat_completion(
                messages, 
                provider=self.preferred_provider,
                max_tokens=4000
            )
            
            if not result['success']:
                print(f"AI analysis failed: {result['error']}")
                return self._fallback_analysis()

            # Parse response
            response_text = result['content'].strip()

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
        if not self.ai_manager.available_providers:
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

            messages = [
                {"role": "system", "content": "You are an expert document analyzer specialized in extracting structured information from RFP and tender documents."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            result = self.ai_manager.chat_completion(
                messages,
                provider=self.preferred_provider,
                max_tokens=3000
            )
            
            if not result['success']:
                print(f"Document analysis failed: {result['error']}")
                return self._fallback_document_analysis(document)

            response_text = result['content'].strip()
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

def get_real_analysis_results(project_id, force_refresh=False):
    """Get AI analysis results for a project - from cache or fresh analysis"""
    try:
        # Import here to avoid circular imports
        from models import AIAnalysisResult
        
        # If not forcing refresh, try to get the latest stored analysis
        if not force_refresh:
            latest_analysis = AIAnalysisResult.query.filter_by(
                project_id=str(project_id),
                analysis_type='post_upload',
                status='completed'
            ).order_by(AIAnalysisResult.created_at.desc()).first()
            
            if latest_analysis:
                print(f"📋 Using cached analysis from {latest_analysis.created_at}")
                return latest_analysis.results
        
        # No cached results or force refresh - generate new analysis
        print(f"🔄 Generating fresh analysis for project {project_id}")
        return analysis_engine.analyze_project_documents(project_id)
        
    except Exception as e:
        print(f"Error getting analysis results: {e}")
        # Fallback to fresh analysis
        return analysis_engine.analyze_project_documents(project_id)

def get_real_document_analysis(document_id):
    """Get real AI-powered analysis for a single document"""
    return analysis_engine.analyze_individual_document(document_id)

# Enhanced methods for RealAnalysisSystem class
def add_vector_context_methods():
    """Add vector context methods to RealAnalysisSystem class"""
    
    def _get_vector_context(self, content: str) -> Dict[str, Any]:
        """Get relevant context from past proposals"""
        try:
            if not self.proposal_manager:
                return {}
            
            # Extract key requirements from content for vector search
            requirements = self._extract_key_requirements(content)
            
            # Get context from past proposals
            context = self.proposal_manager.get_context_for_new_proposal(
                requirements=requirements,
                project_metadata={
                    'project_name': getattr(self.project, 'name', 'Unknown'),
                    'industry_sector': getattr(self.project, 'industry_sector', None)
                }
            )
            
            return context
            
        except Exception as e:
            print(f"Warning: Could not get vector context: {e}")
            return {}
    
    def _extract_key_requirements(self, content: str) -> List[str]:
        """Extract key requirements from RFP content for vector search"""
        try:
            # Simple extraction - look for requirement-like patterns
            requirements = []
            
            # Split into sentences and look for requirement indicators
            sentences = content.split('.')
            
            for sentence in sentences[:50]:  # Limit to avoid too many
                sentence = sentence.strip()
                if any(indicator in sentence.lower() for indicator in [
                    'must', 'shall', 'required', 'need', 'should', 'expect',
                    'deliver', 'provide', 'implement', 'support', 'include'
                ]):
                    if len(sentence) > 20 and len(sentence) < 200:  # Reasonable length
                        requirements.append(sentence)
            
            return requirements[:20]  # Limit to top 20 requirements
            
        except Exception as e:
            print(f"Warning: Could not extract requirements: {e}")
            return []
    
    def _format_context_for_prompt(self, context: Dict[str, Any], analysis_type: str) -> str:
        """Format vector context for AI prompt"""
        try:
            if not context:
                return ""
            
            context_parts = []
            
            # Add relevant proposals context
            if context.get('relevant_proposals'):
                context_parts.append("\n--- RELEVANT PAST EXPERIENCE ---")
                for i, proposal in enumerate(context['relevant_proposals'][:3]):  # Top 3
                    confidence = proposal.get('confidence', 0)
                    if confidence > 0.7:  # Only high-confidence matches
                        context_parts.append(f"""
Past Project: {proposal['metadata'].get('title', 'Unknown')}
Client: {proposal['metadata'].get('client_name', 'Unknown')}
Solution: {proposal['past_solution'][:300]}...
Confidence: {confidence:.2f}
                        """)
            
            # Add success metrics
            if context.get('success_metrics'):
                metrics = context['success_metrics']
                context_parts.append(f"\n--- SUCCESS PATTERNS ---")
                context_parts.append(f"Similar Won Proposals: {metrics.get('similar_won_proposals', 0)}")
                context_parts.append(f"Win Rate: {metrics.get('win_rate', 0):.1%}")
                if metrics.get('key_success_factors'):
                    context_parts.append(f"Key Success Factors: {', '.join(metrics['key_success_factors'][:5])}")
            
            # Add industry insights
            if context.get('industry_insights'):
                insights = context['industry_insights']
                context_parts.append(f"\n--- INDUSTRY INSIGHTS ---")
                if insights.get('common_technologies'):
                    tech_list = [f"{tech[0]} ({tech[1]} projects)" for tech in insights['common_technologies'][:3]]
                    context_parts.append(f"Common Technologies: {', '.join(tech_list)}")
                if insights.get('typical_duration'):
                    context_parts.append(f"Typical Duration: {insights['typical_duration']}")
            
            if context_parts:
                return "\n".join(context_parts) + "\n--- END CONTEXT ---\n"
            else:
                return ""
                
        except Exception as e:
            print(f"Warning: Could not format context: {e}")
            return ""
    
    # Add methods to the class
    RealAnalysisSystem._get_vector_context = _get_vector_context
    RealAnalysisSystem._extract_key_requirements = _extract_key_requirements
    RealAnalysisSystem._format_context_for_prompt = _format_context_for_prompt

# Apply the enhancements
add_vector_context_methods()
