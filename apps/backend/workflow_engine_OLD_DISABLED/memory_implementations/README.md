# Memory Implementations for LLM Context Enhancement

This package provides comprehensive memory implementations designed specifically to enhance LLM context with various types of memory storage and retrieval systems. All memory types are designed to be **attached to LLM nodes** to provide contextual information.

## 🧠 Available Memory Types

### 1. **Conversation Buffer Memory**
- **Purpose**: Store and manage recent conversation history
- **Backend**: Redis (fast access) + Supabase (persistence)
- **Features**: Configurable window sizes, automatic TTL, token-aware windowing
- **Use Case**: Maintain recent chat context for conversational AI

```python
from memory_implementations import ConversationBufferMemory

config = {
    'redis_url': 'redis://localhost:6379',
    'supabase_url': 'YOUR_SUPABASE_URL',
    'supabase_key': 'YOUR_SUPABASE_KEY',
    'window_size': 10,
    'window_type': 'turns',
    'ttl_seconds': 3600
}

buffer_memory = ConversationBufferMemory(config)
```

### 2. **Conversation Summary Memory** ⭐
- **Purpose**: Optimal combination of buffer + summary for best LLM context
- **Backend**: Redis + Supabase + Gemini
- **Features**: Short-term buffer, progressive summarization, intelligent context composition, token optimization
- **Use Case**: Single memory for all conversation needs - recent context + historical summary

```python
from memory_implementations import ConversationSummaryMemory

config = {
    'redis_url': 'redis://localhost:6379',
    'supabase_url': 'YOUR_SUPABASE_URL',
    'supabase_key': 'YOUR_SUPABASE_KEY',
    'google_api_key': 'YOUR_GOOGLE_API_KEY',
    'buffer_window_size': 10,
    'summary_context_weight': 0.3,
    'max_total_tokens': 4000
}

summary_memory = ConversationSummaryMemory(config)
```

### 3. **Vector Database Memory**
- **Purpose**: Semantic similarity search and RAG (Retrieval-Augmented Generation)
- **Backend**: Supabase with pgvector + OpenAI embeddings
- **Features**: Automatic embedding generation, similarity search, metadata filtering
- **Use Case**: Find semantically relevant information for LLM context

```python
from memory_implementations import VectorDatabaseMemory

config = {
    'supabase_url': 'YOUR_SUPABASE_URL',
    'supabase_key': 'YOUR_SUPABASE_KEY',
    'openai_api_key': 'YOUR_OPENAI_API_KEY',
    'embedding_model': 'text-embedding-3-small',
    'similarity_threshold': 0.7
}

vector_memory = VectorDatabaseMemory(config)
```

### 4. **Working Memory**
- **Purpose**: Temporary memory for active reasoning and multi-step problem solving
- **Backend**: Redis with intelligent eviction policies
- **Features**: Importance scoring, reasoning chain tracking, namespace isolation
- **Use Case**: Track intermediate results during complex reasoning

```python
from memory_implementations import WorkingMemory

config = {
    'redis_url': 'redis://localhost:6379',
    'ttl_seconds': 1800,
    'capacity_limit': 100,
    'eviction_policy': 'importance',
    'enable_reasoning_chain': True
}

working_memory = WorkingMemory(config)
```

### 5. **Key-Value Store Memory**
- **Purpose**: Fast storage for user preferences, settings, and session data
- **Backend**: Redis + PostgreSQL backup
- **Features**: JSON serialization, compression, automatic sync
- **Use Case**: Store user context, preferences, and configuration

```python
from memory_implementations import KeyValueStoreMemory

config = {
    'redis_url': 'redis://localhost:6379',
    'supabase_url': 'YOUR_SUPABASE_URL',
    'supabase_key': 'YOUR_SUPABASE_KEY',
    'namespace': 'user_context',
    'serialize_json': True
}

kv_memory = KeyValueStoreMemory(config)
```

### 6. **Entity Memory**
- **Purpose**: Extract, track, and maintain entities from conversations
- **Backend**: PostgreSQL + OpenAI for extraction
- **Features**: Relationship tracking, importance scoring, alias management
- **Use Case**: Remember people, organizations, concepts mentioned in conversations

```python
from memory_implementations import EntityMemory

config = {
    'supabase_url': 'YOUR_SUPABASE_URL',
    'supabase_key': 'YOUR_SUPABASE_KEY',
    'openai_api_key': 'YOUR_OPENAI_API_KEY',
    'entity_types': ['person', 'organization', 'location', 'concept'],
    'relationship_tracking': True
}

entity_memory = EntityMemory(config)
```

### 7. **Memory Orchestrator** 🎯
- **Purpose**: Unified access to all memory types with intelligent context composition
- **Features**: Parallel queries, token optimization, cross-memory insights
- **Use Case**: Single interface for complex memory operations

```python
from memory_implementations import MemoryOrchestrator, MemoryType, ContextRequest

config = {
    'enabled_memories': [
        MemoryType.CONVERSATION_SUMMARY,
        MemoryType.VECTOR_DATABASE,
        MemoryType.ENTITY_MEMORY,
        MemoryType.WORKING_MEMORY
    ],
    # Include configs for each enabled memory type
    'redis_url': 'redis://localhost:6379',
    'supabase_url': 'YOUR_SUPABASE_URL',
    # ... other configs
}

orchestrator = MemoryOrchestrator(config)

# Get comprehensive context
request = ContextRequest(
    query="How do I implement async programming in Python?",
    session_id="session_123",
    user_id="user_456",
    max_total_tokens=4000
)

context = await orchestrator.get_comprehensive_context(request)
```

## 🗄️ Database Setup

### 1. Run Database Migrations

Apply the database schema:

```sql
-- Run the migrations script
psql -h your-supabase-host -p 5432 -U postgres -d postgres -f database_migrations.sql
```

### 2. Enable Required Extensions

```sql
-- Enable necessary PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";  -- For pgvector support
```

### 3. Row Level Security (RLS)

The migrations automatically set up RLS policies for multi-tenant isolation. Customize the policies based on your authentication system.

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install individually
pip install redis supabase openai google-generativeai numpy psycopg2-binary
```

### Basic Usage

```python
import asyncio
from memory_implementations import ConversationSummaryMemory

async def main():
    config = {
        'redis_url': 'redis://localhost:6379',
        'supabase_url': 'YOUR_SUPABASE_URL',
        'supabase_key': 'YOUR_SUPABASE_KEY',
        'google_api_key': 'YOUR_GOOGLE_API_KEY'
    }

    # Initialize memory
    memory = ConversationSummaryMemory(config)
    await memory.initialize()

    # Store a conversation message
    await memory.store({
        "session_id": "chat_123",
        "user_id": "user_456",
        "role": "user",
        "content": "Hello, I need help with Python async programming"
    })

    # Get context for LLM
    context = await memory.get_context({
        "session_id": "chat_123"
    })

    # Use context in your LLM prompt
    llm_prompt = f"""
    Based on our conversation history:
    {context.get('summary', '')}

    Recent messages:
    {[msg['content'] for msg in context.get('messages', [])]}

    User's question: How do I handle exceptions in async functions?
    """

if __name__ == "__main__":
    asyncio.run(main())
```

## 📋 Memory Selection Guide

| Use Case | Recommended Memory | Why |
|----------|-------------------|-----|
| **Chatbot/Assistant** | `ConversationSummaryMemory` | Best balance of recency and history |
| **Knowledge Q&A** | `VectorDatabaseMemory` | Semantic search over knowledge base |
| **Complex Reasoning** | `WorkingMemory` | Track reasoning steps and intermediate results |
| **User Personalization** | `KeyValueStoreMemory` | Fast access to preferences and settings |
| **CRM/People Tracking** | `EntityMemory` | Remember people, companies, relationships |
| **Multi-Modal Context** | `MemoryOrchestrator` | Combine multiple memory types intelligently |

## 🔧 Configuration Guide

### Essential Configuration

```python
# Minimum required configuration
config = {
    # Database connections
    'redis_url': 'redis://localhost:6379',
    'supabase_url': 'https://your-project.supabase.co',
    'supabase_key': 'your-service-role-key',

    # AI API keys
    'openai_api_key': 'sk-your-openai-key',
    'google_api_key': 'your-google-ai-key',
}
```

### Advanced Configuration

```python
# Advanced configuration with all options
config = {
    # Core connections
    'redis_url': 'redis://localhost:6379',
    'supabase_url': 'https://your-project.supabase.co',
    'supabase_key': 'your-service-role-key',
    'openai_api_key': 'sk-your-openai-key',
    'google_api_key': 'your-google-ai-key',

    # Memory-specific settings
    'window_size': 10,
    'window_type': 'turns',  # 'turns', 'tokens', 'time'
    'ttl_seconds': 3600,
    'similarity_threshold': 0.7,
    'max_results': 5,
    'embedding_model': 'text-embedding-3-small',
    'summarization_model': 'gemini-2.0-flash-exp',

    # Orchestrator settings
    'enabled_memories': [
        MemoryType.CONVERSATION_SUMMARY,
        MemoryType.VECTOR_DATABASE,
        MemoryType.ENTITY_MEMORY,
        MemoryType.WORKING_MEMORY,
        MemoryType.KEY_VALUE_STORE
    ],
    'parallel_queries': True,
    'cross_memory_links': True,
    'default_context_priority': {
        'recent_conversation': 0.4,
        'summary': 0.2,
        'entities': 0.15,
        'vector_search': 0.15,
        'working_memory': 0.1
    }
}
```

## 📊 Performance Optimization

### Token Management

All memory implementations are designed with token efficiency in mind:

- **Automatic token estimation** (1 token ≈ 4 characters)
- **Context truncation** when approaching limits
- **Priority-based content selection**
- **Configurable max token limits**

### Caching Strategy

- **Redis** for frequently accessed data
- **PostgreSQL/Supabase** for persistence
- **Automatic cache warming** from persistent storage
- **TTL-based expiration** to prevent stale data

### Scalability

- **Horizontal scaling** through Redis clustering
- **Database connection pooling** for high concurrency
- **Async/await** throughout for non-blocking operations
- **Batch operations** for bulk data processing

## 🔍 Monitoring and Debugging

### Health Checks

```python
# Check individual memory health
health = await memory.health_check()
print(health)  # {"status": "healthy", "timestamp": "..."}

# Check orchestrator health
health = await orchestrator.health_check()
print(health)  # Status of all enabled memories
```

### Logging

Enable debug logging to monitor memory operations:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('memory_implementations')
```

### Statistics

Most memory types provide statistics:

```python
# Conversation buffer stats
stats = await buffer_memory.get_session_stats("session_123")

# Entity memory analytics
analytics = await entity_memory.get_entity_analytics("user_456")

# Working memory namespace stats
stats = await working_memory.get_namespace_stats("reasoning_session")
```

## 🔒 Security Considerations

### Row Level Security (RLS)

All database tables use RLS for multi-tenant isolation:

```sql
-- Users can only access their own data
CREATE POLICY "Users can access own data" ON memory_table
    FOR ALL USING (auth.uid()::text = user_id);
```

### API Key Management

- Store API keys as environment variables
- Use different keys for development/production
- Rotate keys regularly
- Monitor API usage and costs

### Data Encryption

- All data is encrypted in transit (TLS)
- Supabase provides encryption at rest
- Consider field-level encryption for sensitive data

## 🚨 Error Handling

### Graceful Degradation

Memory implementations are designed to fail gracefully:

```python
try:
    context = await memory.get_context(query)
except Exception as e:
    logger.error(f"Memory failed: {e}")
    # Fallback to basic context
    context = {"error": "Memory unavailable", "fallback": True}
```

### Retry Logic

For network operations, implement retry logic:

```python
import asyncio
from asyncio import sleep

async def with_retry(operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await sleep(2 ** attempt)  # Exponential backoff
```

## 📚 Examples

See the `examples/` directory for comprehensive usage examples:

- `basic_usage.py` - Basic usage of each memory type
- `advanced_orchestration.py` - Complex orchestrator usage
- `llm_integration.py` - Integration with popular LLM libraries
- `performance_testing.py` - Performance benchmarking

## 🤝 Contributing

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for any API changes
4. Ensure backwards compatibility when possible

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:

1. Check the examples and documentation
2. Review error logs and health checks
3. Open an issue with reproduction steps
4. Include configuration (without secrets) and error logs

---

**Remember**: These memory implementations are designed specifically for LLM context enhancement. Each memory type provides a `get_context()` method that returns formatted data ready for LLM consumption.
