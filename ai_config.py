"""
AI Provider Configuration
Environment variables and settings for different AI providers
"""

import os
from typing import Dict, Any, Optional

# AI Provider Configuration - Latest Models (2025)
AI_PROVIDER_CONFIG = {
    'claude': {
        'models': {
            # Claude Sonnet 4 - Latest and most capable
            'claude-sonnet-4-20250514': {
                'name': 'Claude Sonnet 4',
                'description': 'Latest Claude model with superior reasoning and analysis',
                'tier': 'premium',
                'max_tokens': 8192,
                'context_length': 200000
            },
            # Claude 3.5 Series
            'claude-3-5-sonnet-20241022': {
                'name': 'Claude 3.5 Sonnet',
                'description': 'Enhanced Claude 3 with improved capabilities',
                'tier': 'standard',
                'max_tokens': 8192,
                'context_length': 200000
            },
            'claude-3-5-haiku-20241022': {
                'name': 'Claude 3.5 Haiku',
                'description': 'Fast and efficient Claude model',
                'tier': 'fast',
                'max_tokens': 4096,
                'context_length': 200000
            },
            # Claude 3 Legacy (for compatibility)
            'claude-3-opus-20240229': {
                'name': 'Claude 3 Opus',
                'description': 'Most capable Claude 3 model (legacy)',
                'tier': 'premium',
                'max_tokens': 4096,
                'context_length': 200000
            }
        },
        'default_model': 'claude-sonnet-4-20250514',
        'temperature': 0.3
    },
    'openai': {
        'models': {
            # GPT-5 Series (if available)
            'gpt-5': {
                'name': 'GPT-5',
                'description': 'Next-generation OpenAI model',
                'tier': 'premium',
                'max_tokens': 16384,
                'context_length': 128000
            },
            'gpt-5-mini': {
                'name': 'GPT-5 Mini',
                'description': 'Compact version of GPT-5',
                'tier': 'standard',
                'max_tokens': 8192,
                'context_length': 64000
            },
            'gpt-5-nano': {
                'name': 'GPT-5 Nano',
                'description': 'Ultra-fast GPT-5 variant',
                'tier': 'fast',
                'max_tokens': 4096,
                'context_length': 32000
            },
            # GPT-4.1 Series
            'gpt-4.1': {
                'name': 'GPT-4.1',
                'description': 'Enhanced GPT-4 with improved performance',
                'tier': 'premium',
                'max_tokens': 8192,
                'context_length': 128000
            },
            'gpt-4.1-mini': {
                'name': 'GPT-4.1 Mini',
                'description': 'Efficient GPT-4.1 variant',
                'tier': 'standard',
                'max_tokens': 4096,
                'context_length': 64000
            },
            'gpt-4.1-nano': {
                'name': 'GPT-4.1 Nano',
                'description': 'Fast GPT-4.1 for quick tasks',
                'tier': 'fast',
                'max_tokens': 2048,
                'context_length': 32000
            },
            # GPT-4 Turbo (current production)
            'gpt-4-turbo': {
                'name': 'GPT-4 Turbo',
                'description': 'Current production GPT-4 model',
                'tier': 'standard',
                'max_tokens': 4096,
                'context_length': 128000
            },
            # GPT-4o Series
            'gpt-4o': {
                'name': 'GPT-4o',
                'description': 'GPT-4 optimized for various tasks',
                'tier': 'standard',
                'max_tokens': 4096,
                'context_length': 128000
            },
            'gpt-4o-mini': {
                'name': 'GPT-4o Mini',
                'description': 'Compact GPT-4o for cost efficiency',
                'tier': 'fast',
                'max_tokens': 2048,
                'context_length': 64000
            }
        },
        'default_model': 'gpt-4.1',
        'temperature': 0.3
    }
}

def get_ai_config() -> Dict[str, Any]:
    """Get AI configuration from environment"""
    return {
        'preferred_provider': os.getenv('AI_PROVIDER', 'claude').lower(),
        'fallback_enabled': os.getenv('AI_FALLBACK_ENABLED', 'true').lower() == 'true',
        'timeout': int(os.getenv('AI_TIMEOUT_SECONDS', '60')),
        'retry_attempts': int(os.getenv('AI_RETRY_ATTEMPTS', '3')),
        'claude': {
            'api_key': os.getenv('ANTHROPIC_API_KEY'),
            'model': os.getenv('CLAUDE_MODEL', AI_PROVIDER_CONFIG['claude']['default_model']),
            'max_tokens': int(os.getenv('CLAUDE_MAX_TOKENS', '8192')),
        },
        'openai': {
            'api_key': os.getenv('OPENAI_API_KEY'),
            'model': os.getenv('OPENAI_MODEL', AI_PROVIDER_CONFIG['openai']['default_model']),
            'max_tokens': int(os.getenv('OPENAI_MAX_TOKENS', '8192')),
        }
    }

def get_available_models(provider: str) -> Dict[str, Dict[str, Any]]:
    """Get available models for a provider"""
    return AI_PROVIDER_CONFIG.get(provider, {}).get('models', {})

def get_model_info(provider: str, model_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a specific model"""
    models = get_available_models(provider)
    return models.get(model_id)

def get_models_by_tier(provider: str, tier: str) -> Dict[str, Dict[str, Any]]:
    """Get models filtered by tier (fast, standard, premium)"""
    models = get_available_models(provider)
    return {
        model_id: model_info 
        for model_id, model_info in models.items() 
        if model_info.get('tier') == tier
    }

def get_default_model(provider: str) -> str:
    """Get default model for a provider"""
    return AI_PROVIDER_CONFIG.get(provider, {}).get('default_model', 'gpt-4-turbo')

def validate_model(provider: str, model_id: str) -> bool:
    """Validate that a model exists for a provider"""
    models = get_available_models(provider)
    return model_id in models

def get_provider_model(provider: str, model_type: str = 'default') -> str:
    """Get model name for a provider (legacy function for backwards compatibility)"""
    if model_type == 'default':
        return get_default_model(provider)
    
    # Map legacy model types to new tier system
    tier_mapping = {
        'fast': 'fast',
        'premium': 'premium',
        'default': 'standard'
    }
    
    tier = tier_mapping.get(model_type, 'standard')
    models_by_tier = get_models_by_tier(provider, tier)
    
    if models_by_tier:
        return next(iter(models_by_tier.keys()))
    
    return get_default_model(provider)

def validate_api_keys() -> Dict[str, bool]:
    """Validate that required API keys are present"""
    config = get_ai_config()
    return {
        'claude': bool(config['claude']['api_key']),
        'openai': bool(config['openai']['api_key'])
    }

def get_recommended_provider() -> str:
    """Get recommended provider based on available API keys"""
    keys = validate_api_keys()
    config = get_ai_config()
    
    preferred = config['preferred_provider']
    
    # Return preferred if available
    if keys.get(preferred, False):
        return preferred
    
    # Return first available
    for provider, available in keys.items():
        if available:
            return provider
    
    return 'claude'  # Default fallback