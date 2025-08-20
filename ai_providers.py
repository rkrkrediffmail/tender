"""
AI Provider Abstraction Layer
Supports Claude (Anthropic) and OpenAI with unified interface
"""

import os
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a chat completion"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass

class ClaudeProvider(AIProvider):
    """Anthropic Claude provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.client = None
        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.error("anthropic package not installed. Run: pip install anthropic")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
    
    @property
    def name(self) -> str:
        return "claude"
    
    def is_available(self) -> bool:
        return self.client is not None and self.api_key is not None
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate completion using Claude"""
        if not self.is_available():
            raise Exception("Claude provider not available")
        
        try:
            from ai_config import get_ai_config, get_model_info
            
            # Get current configuration
            config = get_ai_config()
            default_model = config['claude']['model']
            specified_model = kwargs.get('model', default_model)
            
            # Get model info for token limits
            model_info = get_model_info('claude', specified_model)
            max_tokens = kwargs.get('max_tokens', 
                model_info.get('max_tokens', 8192) if model_info else 4000)
            
            # Convert OpenAI-style messages to Claude format
            if messages and messages[0].get('role') == 'system':
                system_message = messages[0]['content']
                user_messages = messages[1:]
            else:
                system_message = "You are a helpful AI assistant specialized in analyzing RFP documents and tender analysis."
                user_messages = messages
            
            # Claude expects alternating user/assistant messages
            formatted_messages = []
            for msg in user_messages:
                if msg['role'] in ['user', 'assistant']:
                    formatted_messages.append(msg)
            
            response = self.client.messages.create(
                model=specified_model,
                max_tokens=max_tokens,
                system=system_message,
                messages=formatted_messages,
                temperature=kwargs.get('temperature', 0.3)
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise Exception(f"Claude API error: {str(e)}")

class OpenAIProvider(AIProvider):
    """OpenAI provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.client = None
        if self.api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
    
    @property
    def name(self) -> str:
        return "openai"
    
    def is_available(self) -> bool:
        return self.client is not None and self.api_key is not None
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate completion using OpenAI"""
        if not self.is_available():
            raise Exception("OpenAI provider not available")
        
        try:
            from ai_config import get_ai_config, get_model_info
            
            # Get current configuration
            config = get_ai_config()
            default_model = config['openai']['model']
            specified_model = kwargs.get('model', default_model)
            
            # Get model info for token limits
            model_info = get_model_info('openai', specified_model)
            max_tokens = kwargs.get('max_tokens', 
                model_info.get('max_tokens', 4096) if model_info else 4000)
            
            response = self.client.chat.completions.create(
                model=specified_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=kwargs.get('temperature', 0.3)
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"OpenAI API error: {str(e)}")

class AIProviderManager:
    """Manages multiple AI providers with fallback support"""
    
    def __init__(self, preferred_provider: str = None):
        self.providers = {
            'claude': ClaudeProvider(),
            'openai': OpenAIProvider()
        }
        
        # Determine preferred provider
        self.preferred_provider = (
            preferred_provider or 
            os.getenv('AI_PROVIDER', 'claude').lower()
        )
        
        # Get available providers
        self.available_providers = [
            name for name, provider in self.providers.items() 
            if provider.is_available()
        ]
        
        logger.info(f"Available AI providers: {self.available_providers}")
        logger.info(f"Preferred provider: {self.preferred_provider}")
    
    def get_provider(self, provider_name: str = None) -> AIProvider:
        """Get a specific provider or the preferred one"""
        name = provider_name or self.preferred_provider
        
        if name in self.providers and name in self.available_providers:
            return self.providers[name]
        
        # Fallback to any available provider
        if self.available_providers:
            fallback_name = self.available_providers[0]
            logger.warning(f"Provider '{name}' not available, using fallback: {fallback_name}")
            return self.providers[fallback_name]
        
        raise Exception("No AI providers available. Check your API keys.")
    
    def chat_completion(self, messages: List[Dict[str, str]], provider: str = None, **kwargs) -> Dict[str, Any]:
        """Generate chat completion with provider info"""
        ai_provider = self.get_provider(provider)
        
        try:
            content = ai_provider.chat_completion(messages, **kwargs)
            return {
                'success': True,
                'content': content,
                'provider': ai_provider.name,
                'model': kwargs.get('model', 'default')
            }
        except Exception as e:
            # Try fallback provider if preferred one fails
            if provider is None and len(self.available_providers) > 1:
                for fallback_name in self.available_providers:
                    if fallback_name != ai_provider.name:
                        try:
                            fallback_provider = self.providers[fallback_name]
                            content = fallback_provider.chat_completion(messages, **kwargs)
                            logger.warning(f"Fallback to {fallback_name} after {ai_provider.name} failed")
                            return {
                                'success': True,
                                'content': content,
                                'provider': fallback_provider.name,
                                'model': kwargs.get('model', 'default'),
                                'fallback_used': True
                            }
                        except Exception as fallback_error:
                            logger.error(f"Fallback provider {fallback_name} also failed: {fallback_error}")
                            continue
            
            return {
                'success': False,
                'error': str(e),
                'provider': ai_provider.name
            }
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        status = {}
        for name, provider in self.providers.items():
            status[name] = {
                'available': provider.is_available(),
                'name': provider.name
            }
        
        return {
            'providers': status,
            'preferred': self.preferred_provider,
            'available_count': len(self.available_providers)
        }

# Global instance
ai_manager = AIProviderManager()

def get_ai_manager() -> AIProviderManager:
    """Get the global AI provider manager"""
    return ai_manager

def set_preferred_provider(provider_name: str):
    """Set the preferred AI provider"""
    global ai_manager
    ai_manager.preferred_provider = provider_name.lower()
    logger.info(f"Preferred AI provider set to: {provider_name}")

# Convenience functions for backward compatibility
def get_ai_client():
    """Get AI client (backward compatibility)"""
    return get_ai_manager().get_provider()

def analyze_with_ai(messages: List[Dict[str, str]], **kwargs) -> str:
    """Analyze with AI using the preferred provider"""
    result = ai_manager.chat_completion(messages, **kwargs)
    if result['success']:
        return result['content']
    else:
        raise Exception(f"AI analysis failed: {result['error']}")