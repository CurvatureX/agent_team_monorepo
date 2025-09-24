# LLM Provider Configuration Guide

This guide explains how to configure different LLM providers (OpenAI, OpenRouter, Anthropic) for the Workflow Agent.

## Overview

The Workflow Agent now supports multiple LLM providers through a flexible configuration system. You can easily switch between providers by modifying environment variables without changing any code.

## Supported Providers

1. **OpenAI** - Direct OpenAI API access (default)
2. **OpenRouter** - Access to multiple models through OpenRouter's unified API
3. **Anthropic** - Claude models (future support)

## Configuration

All LLM configuration is done through environment variables in the `.env` file.

### Basic Configuration

```bash
# Select your LLM provider (openai, openrouter, anthropic)
LLM_PROVIDER=openai

# Common settings applied to all providers
LLM_TEMPERATURE=0
LLM_MAX_TOKENS=4096
LLM_TIMEOUT=60
```

### OpenAI Configuration

```bash
# Use OpenAI directly (default)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
# Optional: Use a custom OpenAI-compatible endpoint
# OPENAI_BASE_URL=https://your-custom-endpoint.com/v1
```

### OpenRouter Configuration

```bash
# Use OpenRouter for access to multiple models
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-your-openrouter-api-key
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=https://your-site.com
OPENROUTER_APP_NAME=Your App Name
```

#### Available OpenRouter Models

OpenRouter provides access to many models. Some popular options:

- `openai/gpt-4o-mini` - Fast and efficient
- `openai/gpt-4o` - Most capable OpenAI model
- `anthropic/claude-3-haiku` - Fast Claude model
- `anthropic/claude-3-sonnet` - Balanced Claude model
- `google/gemini-pro` - Google's Gemini model
- `meta-llama/llama-3-70b-instruct` - Open source alternative

See [OpenRouter Models](https://openrouter.ai/models) for the full list.

### Anthropic Configuration (Future)

```bash
# Use Anthropic Claude models
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
ANTHROPIC_MODEL=claude-3-haiku-20240307
```

## Embedding Configuration

Embeddings are used for RAG (Retrieval Augmented Generation) and similarity search.

```bash
# Embedding provider (currently only OpenAI is supported)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-ada-002
```

Note: OpenRouter doesn't provide embedding models, so embeddings will always use OpenAI even when using OpenRouter for LLM.

## Testing Your Configuration

Use the provided test script to verify your configuration:

```bash
# From the backend directory
uv run python workflow_agent/test_llm_provider.py
```

This will test:
1. LLM creation and basic query
2. Embedding model creation
3. Connection to the configured provider

## Switching Providers

To switch between providers:

1. Update the `LLM_PROVIDER` environment variable
2. Ensure the corresponding API key is set
3. Restart the Workflow Agent service

Example: Switching from OpenAI to OpenRouter

```bash
# Before (using OpenAI)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx

# After (using OpenRouter)
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-xxx
OPENROUTER_MODEL=openai/gpt-4o-mini
```

## Cost Considerations

Different providers and models have different costs:

- **OpenAI**: Direct pricing, typically lower for high volume
- **OpenRouter**: Pay-per-use across multiple providers, good for testing different models
- **Anthropic**: Competitive pricing for Claude models

## Performance Tips

1. **Model Selection**: Choose models based on your needs
   - Fast responses: `gpt-4o-mini`, `claude-3-haiku`
   - Best quality: `gpt-4o`, `claude-3-sonnet`
   - Cost-effective: `gpt-3.5-turbo`, open source models via OpenRouter

2. **Timeout Settings**: Adjust `LLM_TIMEOUT` based on model and complexity
   - Simple queries: 30-60 seconds
   - Complex workflows: 120-300 seconds

3. **Token Limits**: Set `LLM_MAX_TOKENS` appropriately
   - Short responses: 1024-2048
   - Detailed workflows: 4096-8192

## Troubleshooting

### "API key not configured" Error
- Ensure the API key environment variable is set for your selected provider
- Check that the key has the correct format and permissions

### "Model not found" Error
- Verify the model name is correct for your provider
- For OpenRouter, use the full model path (e.g., `openai/gpt-4o-mini`)

### Timeout Errors
- Increase `LLM_TIMEOUT` for complex queries
- Consider using a faster model
- Check your network connection

### Rate Limiting
- OpenRouter and OpenAI have different rate limits
- Consider implementing retry logic
- Use multiple API keys if needed

## Implementation Details

The LLM provider system is implemented in `workflow_agent/core/llm_provider.py`:

- `LLMConfig`: Reads and manages environment configuration
- `LLMFactory`: Creates LLM instances based on configuration
- Supports both sync and async operations
- Compatible with LangChain's tool binding for MCP integration

## MCP Integration

The Model Context Protocol (MCP) tools work seamlessly with all supported LLM providers. The system automatically binds MCP tools to the configured LLM, allowing for dynamic workflow generation regardless of the provider choice.