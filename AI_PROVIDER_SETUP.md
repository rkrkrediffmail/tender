# AI Provider Setup Guide

This system supports multiple AI providers with automatic fallback. You can use Claude (Anthropic), OpenAI GPT, or both.

## Quick Setup

### Environment Variables

Add these to your `.env` file or docker-compose.yml:

```bash
# AI Provider Selection
AI_PROVIDER=claude                    # 'claude' or 'openai' (default: claude)
AI_FALLBACK_ENABLED=true             # Enable automatic fallback (default: true)

# Claude (Anthropic) - Recommended for complex analysis
ANTHROPIC_API_KEY=your_claude_api_key
CLAUDE_MODEL=claude-3-sonnet-20240229 # Optional, uses default if not set

# OpenAI GPT - Good for general tasks and speed  
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4-turbo-preview      # Optional, uses default if not set

# Optional Performance Tuning
AI_TIMEOUT_SECONDS=60                 # API timeout (default: 60)
AI_RETRY_ATTEMPTS=3                   # Retry attempts (default: 3)
```

## Provider Comparison

| Feature | Claude (Anthropic) | OpenAI GPT |
|---------|-------------------|------------|
| **Document Analysis** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Very Good |
| **Complex Reasoning** | ⭐⭐⭐⭐⭐ Superior | ⭐⭐⭐⭐ Good |
| **Speed** | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐⭐ Fast |
| **Cost** | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐ Lower |
| **Context Length** | ⭐⭐⭐⭐⭐ 200K tokens | ⭐⭐⭐⭐ 128K tokens |
| **Legal/Technical** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good |

## Getting API Keys

### Claude (Anthropic)
1. Visit [console.anthropic.com](https://console.anthropic.com)
2. Sign up for an account
3. Go to API Keys section
4. Create a new API key
5. Copy and add to environment: `ANTHROPIC_API_KEY=your_key_here`

### OpenAI GPT
1. Visit [platform.openai.com](https://platform.openai.com)
2. Sign up for an account
3. Go to API Keys section
4. Create a new secret key
5. Copy and add to environment: `OPENAI_API_KEY=your_key_here`

## Configuration Options

### Provider Selection
```bash
# Use Claude as primary
AI_PROVIDER=claude

# Use OpenAI as primary  
AI_PROVIDER=openai
```

### Model Selection (Latest 2025 Models)
```bash
# Claude Models - Latest (Recommended)
CLAUDE_MODEL=claude-sonnet-4-20250514      # Latest Claude 4 - Best performance
CLAUDE_MODEL=claude-3-5-sonnet-20241022    # Enhanced Claude 3.5 - Good balance
CLAUDE_MODEL=claude-3-5-haiku-20241022     # Fast Claude 3.5 - Cost effective
CLAUDE_MODEL=claude-3-opus-20240229        # Legacy Claude 3 - Compatible

# OpenAI Models - Latest (Future-Ready)
OPENAI_MODEL=gpt-5                          # Next-gen GPT-5 (when available)
OPENAI_MODEL=gpt-5-mini                     # Compact GPT-5 (when available)
OPENAI_MODEL=gpt-5-nano                     # Ultra-fast GPT-5 (when available)
OPENAI_MODEL=gpt-4.1                        # Enhanced GPT-4 (when available)
OPENAI_MODEL=gpt-4.1-mini                   # Efficient GPT-4.1 (when available)
OPENAI_MODEL=gpt-4.1-nano                   # Fast GPT-4.1 (when available)
OPENAI_MODEL=gpt-4-turbo                    # Current production model
OPENAI_MODEL=gpt-4o                         # Optimized GPT-4 variant
OPENAI_MODEL=gpt-4o-mini                    # Cost-effective GPT-4o

# Note: Future models (GPT-5, GPT-4.1) may not be available yet
# The system will show errors for unavailable models
```

### Fallback Configuration
```bash
# Enable automatic fallback (recommended)
AI_FALLBACK_ENABLED=true

# Disable fallback (use only primary provider)
AI_FALLBACK_ENABLED=false
```

## Using the Web Interface

1. **Access Settings**: Click your username → "AI Settings"
2. **Check Status**: View which providers are available
3. **Switch Providers**: Click "Use Claude" or "Use OpenAI"
4. **Test Connection**: Use "Test Connection" to verify setup
5. **View Results**: See test results and current configuration

## Programmatic Usage

### Switching Providers
```bash
# Via API
curl -X POST http://localhost:5000/api/ai/providers/switch \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai"}'

# Via Environment Variable (restart required)
AI_PROVIDER=openai
```

### Testing Providers
```bash
# Test current provider
curl -X POST http://localhost:5000/api/ai/test \
  -H "Content-Type: application/json" \
  -d '{"provider": "claude"}'
```

## Troubleshooting

### Common Issues

**"No AI providers available"**
- Check API keys are set correctly
- Verify environment variables are loaded
- Restart the application after setting keys

**"API key not valid"**
- Verify API key is copied correctly (no extra spaces)
- Check API key has proper permissions
- Ensure account has credits/usage allowance

**"Provider timeout"**
- Increase timeout: `AI_TIMEOUT_SECONDS=120`
- Check network connectivity
- Try different model (faster variants)

**"Rate limit exceeded"**
- Wait a few minutes and retry
- Enable fallback provider
- Upgrade API plan for higher limits

### Health Check

Visit `/health` endpoint to see AI provider status:
```bash
curl http://localhost:5000/health
```

### Logs

Check application logs for detailed error messages:
```bash
docker-compose logs web
docker-compose logs celery
```

## Recommendations

### For Production
- **Primary**: Claude (better analysis quality)
- **Fallback**: OpenAI (faster, cheaper backup)
- **Settings**: Enable fallback, set reasonable timeouts

### For Development  
- **Single Provider**: OpenAI (faster iteration)
- **Settings**: Shorter timeouts, basic models

### For Cost Optimization
- **Primary**: OpenAI with GPT-3.5-turbo
- **Fallback**: Claude with Haiku model
- **Settings**: Enable caching, limit retries

## Support

- **Documentation**: See `CLAUDE.md` for system overview
- **API Reference**: Visit `/api/ai/providers` for status
- **Issues**: Check application health and logs first
- **Updates**: Both providers are actively maintained