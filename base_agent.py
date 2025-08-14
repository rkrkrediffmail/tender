# agents/base_agent.py
import logging
import requests
import json
import os
from typing import Dict, Any

class BaseAgent:
    """Base class for all AI agents"""

    def __init__(self):
        self.agent_type = "BASE"
        self.agent_name = "Base Agent"
        self.logger = logging.getLogger(f"agents.{self.agent_type}")

        # API configuration
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')

    def _call_claude_api(self, prompt: str, max_tokens: int = 1000) -> str:
        """Call Claude API with the given prompt"""
        try:
            if not self.anthropic_api_key:
                raise Exception("ANTHROPIC_API_KEY not configured")

            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.anthropic_api_key
            }

            payload = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }

            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=60
            )

            response.raise_for_status()
            result = response.json()

            return result["content"][0]["text"]

        except Exception as e:
            self.logger.error(f"Claude API call failed: {str(e)}")
            raise

    def _get_detailed_analysis(self, product, requirements, architecture) -> Dict[str, Any]:
        """Get detailed AI analysis for a product fit"""
        try:
            prompt = f"""
            Analyze this partner product for project fit:

            PRODUCT: {product.product_name}
            CATEGORY: {product.category}
            FUNCTIONALITY: {product.functionality}

            REQUIREMENTS: {str(requirements)[:1000]}...
            ARCHITECTURE: {str(architecture)[:500]}...

            Provide detailed analysis as JSON:
            {{
                "reasoning": "detailed explanation",
                "technical_considerations": ["point1", "point2"],
                "business_benefits": ["benefit1", "benefit2"],
                "matching_requirements": ["req1", "req2"]
            }}
            """

            response = self._call_claude_api(prompt)

            # Try to parse JSON, fallback to basic structure if parsing fails
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {
                    "reasoning": response,
                    "technical_considerations": [],
                    "business_benefits": [],
                    "matching_requirements": []
                }

        except Exception as e:
            self.logger.error(f"Error in detailed analysis: {str(e)}")
            return {
                "reasoning": "Analysis unavailable",
                "technical_considerations": [],
                "business_benefits": [],
                "matching_requirements": []
            }
