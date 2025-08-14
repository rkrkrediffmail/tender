# agents/partner_recommendation_agent.py
import json
import logging
from typing import List, Dict, Any
from datetime import datetime
from models import db, Partner, PartnerProduct, PartnerRecommendation, Requirement, AgentTask
from agents.base_agent import BaseAgent

class PartnerRecommendationAgent(BaseAgent):
    """
    AI Agent that analyzes requirements and recommends relevant partner products
    Extends the existing BaseAgent with async capabilities and database integration
    """

    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Main task execution method - required by BaseAgent
        """
        task_type = task.task_type
        input_data = task.input_data or {}

        if task_type == 'ANALYZE_PARTNER_OPPORTUNITIES':
            return await self._analyze_partner_opportunities(
                project_id=input_data.get('project_id'),
                requirements=input_data.get('requirements', []),
                solution_architecture=input_data.get('solution_architecture', {})
            )
        elif task_type == 'UPDATE_RECOMMENDATION_STATUS':
            return await self._update_recommendation_status(
                recommendation_id=input_data.get('recommendation_id'),
                status=input_data.get('status'),
                user_notes=input_data.get('user_notes'),
                user_id=input_data.get('user_id')
            )
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _analyze_partner_opportunities(self, project_id: int, requirements: List[Dict],
                                           solution_architecture: Dict) -> Dict[str, Any]:
        """
        Main method to analyze requirements and generate partner recommendations
        """
        try:
            self._log_event('INFO', 'partner_analysis_started', f"Starting partner analysis for project {project_id}")

            # Get all active partner products
            partner_products = self._get_active_partner_products()

            if not partner_products:
                self._log_event('WARNING', 'no_partners_found', "No active partner products found")
                return {
                    'recommendations': [],
                    'count': 0,
                    'message': 'No active partner products available'
                }

            # Extract requirement text for AI analysis
            requirement_text = self._extract_requirement_text(requirements)

            # Get solution architecture context
            architecture_context = self._extract_architecture_context(solution_architecture)

            recommendations = []

            # Process each partner product
            for product in partner_products:
                try:
                    # Calculate fit score using AI
                    fit_analysis = await self._calculate_fit_score_with_claude(
                        requirement_text,
                        architecture_context,
                        product
                    )

                    fit_score = fit_analysis.get('fit_score', 0)

                    if fit_score > 60:  # Only recommend if fit score > 60
                        recommendation = await self._create_recommendation(
                            project_id, product, fit_analysis, requirements, solution_architecture
                        )
                        recommendations.append(recommendation)

                except Exception as e:
                    self._log_event('WARNING', 'product_analysis_failed',
                                  f"Failed to analyze product {product.product_name}: {str(e)}")
                    continue

            # Sort by fit score descending
            recommendations.sort(key=lambda x: x['fit_score'], reverse=True)

            # Store in database
            await self._store_recommendations(recommendations)

            self._log_event('INFO', 'partner_analysis_completed',
                          f"Generated {len(recommendations)} partner recommendations")

            return {
                'recommendations': recommendations,
                'count': len(recommendations),
                'message': f'Successfully generated {len(recommendations)} recommendations'
            }

        except Exception as e:
            self._log_event('ERROR', 'partner_analysis_failed', f"Partner analysis failed: {str(e)}")
            raise

    def _get_active_partner_products(self) -> List[PartnerProduct]:
        """Get all products from active partners"""
        return db.session.query(PartnerProduct).join(Partner).filter(
            Partner.status == 'ACTIVE'
        ).all()

    def _extract_requirement_text(self, requirements: List[Dict]) -> str:
        """Extract and combine all requirement descriptions"""
        texts = []
        for req in requirements:
            if isinstance(req, dict):
                texts.append(req.get('description', ''))
                texts.append(req.get('title', ''))
            else:
                texts.append(str(req))

        return " ".join(texts)

    def _extract_architecture_context(self, architecture: Dict) -> str:
        """Extract relevant context from solution architecture"""
        context_parts = []

        if 'technologies' in architecture:
            context_parts.append(f"Technologies: {', '.join(architecture['technologies'])}")

        if 'components' in architecture:
            context_parts.append(f"Components: {', '.join(architecture['components'])}")

        if 'integration_patterns' in architecture:
            context_parts.append(f"Integration: {', '.join(architecture['integration_patterns'])}")

        return " ".join(context_parts)

    async def _calculate_fit_score_with_claude(self, requirement_text: str, architecture_context: str,
                                             product: PartnerProduct) -> Dict[str, Any]:
        """
        Use Claude API to calculate how well a partner product fits the requirements
        """
        try:
            # Prepare product information
            product_info = {
                'name': product.product_name,
                'category': product.category,
                'functionality': product.functionality,
                'technical_keywords': product.technical_keywords,
                'industry_fit': product.industry_fit,
                'integration_complexity': product.integration_complexity,
                'api_available': product.api_available,
                'cloud_native': product.cloud_native
            }

            # Create AI prompt for fit analysis
            prompt = f"""
            As a technical solutions architect, analyze how well this partner product fits the project requirements.

            PROJECT REQUIREMENTS:
            {requirement_text[:2000]}  # Limit text to avoid token limits

            SOLUTION ARCHITECTURE CONTEXT:
            {architecture_context[:1000]}

            PARTNER PRODUCT:
            {json.dumps(product_info, indent=2)}

            Evaluate the fit score (0-100) based on:
            1. Technical compatibility with requirements
            2. Integration complexity and feasibility
            3. Alignment with solution architecture
            4. Business value and functionality match

            Respond with ONLY a JSON object:
            {{
                "fit_score": <number 0-100>,
                "reasoning": "<explanation>",
                "technical_considerations": ["<point1>", "<point2>"],
                "business_benefits": ["<benefit1>", "<benefit2>"],
                "matching_requirements": ["<req1>", "<req2>"]
            }}
            """

            # Call Claude API using your existing method
            response = await self.call_claude(prompt, max_tokens=1500)

            # Parse response
            try:
                # Clean the response to extract JSON
                cleaned_response = response.strip()
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response[7:-3].strip()
                elif cleaned_response.startswith('```'):
                    cleaned_response = cleaned_response[3:-3].strip()

                analysis = json.loads(cleaned_response)

                # Validate the analysis structure
                if not isinstance(analysis.get('fit_score'), (int, float)):
                    analysis['fit_score'] = 0

                return analysis

            except json.JSONDecodeError as e:
                self._log_event('WARNING', 'json_parse_failed',
                              f"Failed to parse Claude response as JSON: {str(e)}")
                # Fallback response
                return {
                    'fit_score': 50,  # Default middle score
                    'reasoning': response[:500],  # Use first part of response
                    'technical_considerations': [],
                    'business_benefits': [],
                    'matching_requirements': []
                }

        except Exception as e:
            self._log_event('ERROR', 'fit_calculation_failed', f"Error calculating fit score: {str(e)}")
            return {
                'fit_score': 0,
                'reasoning': 'Analysis failed due to technical error',
                'technical_considerations': [],
                'business_benefits': [],
                'matching_requirements': []
            }

    async def _create_recommendation(self, project_id: int, product: PartnerProduct,
                                   fit_analysis: Dict, requirements: List[Dict],
                                   architecture: Dict) -> Dict:
        """
        Create a structured recommendation object
        """
        return {
            'project_id': project_id,
            'partner_id': product.partner_id,
            'product_id': product.id,
            'fit_score': fit_analysis.get('fit_score', 0),
            'partner_name': product.partner.name,
            'product_name': product.product_name,
            'category': product.category,
            'functionality': product.functionality,
            'integration_scope': self._determine_integration_scope(fit_analysis.get('fit_score', 0)),
            'estimated_cost': self._estimate_cost(product),
            'estimated_timeline': product.implementation_time,
            'ai_reasoning': fit_analysis.get('reasoning', ''),
            'technical_considerations': fit_analysis.get('technical_considerations', []),
            'business_benefits': fit_analysis.get('business_benefits', []),
            'matching_requirements': fit_analysis.get('matching_requirements', [])
        }

    def _determine_integration_scope(self, fit_score: float) -> str:
        """Determine integration scope based on fit score"""
        if fit_score >= 85:
            return 'CORE'
        elif fit_score >= 70:
            return 'ADDON'
        else:
            return 'OPTIONAL'

    def _estimate_cost(self, product: PartnerProduct) -> float:
        """
        Estimate integration cost based on product characteristics
        """
        base_cost = 10000  # Base integration cost

        # Adjust based on complexity
        complexity_multiplier = {
            'LOW': 0.5,
            'MEDIUM': 1.0,
            'HIGH': 2.0
        }

        multiplier = complexity_multiplier.get(product.integration_complexity, 1.0)

        # Adjust based on API availability
        if not product.api_available:
            multiplier *= 1.5

        return base_cost * multiplier

    async def _store_recommendations(self, recommendations: List[Dict]):
        """Store recommendations in database"""
        try:
            for rec_data in recommendations:
                # Check if recommendation already exists
                existing = PartnerRecommendation.query.filter_by(
                    project_id=rec_data['project_id'],
                    partner_id=rec_data['partner_id'],
                    product_id=rec_data['product_id']
                ).first()

                if existing:
                    # Update existing recommendation
                    existing.fit_score = rec_data['fit_score']
                    existing.ai_reasoning = rec_data['ai_reasoning']
                    existing.technical_considerations = rec_data['technical_considerations']
                    existing.business_benefits = rec_data['business_benefits']
                    existing.matching_requirements = rec_data['matching_requirements']
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new recommendation
                    recommendation = PartnerRecommendation(
                        project_id=rec_data['project_id'],
                        partner_id=rec_data['partner_id'],
                        product_id=rec_data['product_id'],
                        fit_score=rec_data['fit_score'],
                        integration_scope=rec_data['integration_scope'],
                        estimated_cost=rec_data['estimated_cost'],
                        estimated_timeline=rec_data['estimated_timeline'],
                        ai_reasoning=rec_data['ai_reasoning'],
                        technical_considerations=rec_data['technical_considerations'],
                        business_benefits=rec_data['business_benefits'],
                        matching_requirements=rec_data['matching_requirements']
                    )

                    db.session.add(recommendation)

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            self._log_event('ERROR', 'recommendation_storage_failed', f"Error storing recommendations: {str(e)}")
            raise

    async def _update_recommendation_status(self, recommendation_id: str, status: str,
                                          user_notes: str = None, user_id: int = None) -> Dict[str, Any]:
        """Update recommendation status (accept/reject)"""
        try:
            recommendation = PartnerRecommendation.query.filter_by(
                recommendation_id=recommendation_id
            ).first()

            if not recommendation:
                raise ValueError(f"Recommendation {recommendation_id} not found")

            recommendation.status = status
            recommendation.user_notes = user_notes
            recommendation.reviewed_by = user_id
            recommendation.reviewed_at = datetime.utcnow()

            db.session.commit()

            self._log_event('INFO', 'recommendation_updated',
                          f"Updated recommendation {recommendation_id} to {status}")

            return {
                'success': True,
                'recommendation_id': recommendation_id,
                'new_status': status
            }

        except Exception as e:
            db.session.rollback()
            self._log_event('ERROR', 'recommendation_update_failed', f"Error updating recommendation: {str(e)}")
            raise

    # Public methods for external use (non-async versions for Flask routes)
    def get_project_recommendations(self, project_id: int) -> List[Dict]:
        """Get stored recommendations for a project (synchronous)"""
        recommendations = db.session.query(PartnerRecommendation).filter_by(
            project_id=project_id
        ).order_by(PartnerRecommendation.fit_score.desc()).all()

        return [self._format_recommendation(rec) for rec in recommendations]

    def _format_recommendation(self, rec: PartnerRecommendation) -> Dict:
        """Format recommendation for API response"""
        return {
            'id': rec.recommendation_id,
            'partner_name': rec.partner.name,
            'product_name': rec.product.product_name,
            'category': rec.product.category,
            'fit_score': rec.fit_score,
            'integration_scope': rec.integration_scope,
            'estimated_cost': rec.estimated_cost,
            'estimated_timeline': rec.estimated_timeline,
            'ai_reasoning': rec.ai_reasoning,
            'technical_considerations': rec.technical_considerations,
            'business_benefits': rec.business_benefits,
            'status': rec.status,
            'user_notes': rec.user_notes,
            'created_at': rec.created_at.isoformat() if rec.created_at else None
        }
