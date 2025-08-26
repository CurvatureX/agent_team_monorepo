# Memory Integration Tests

Comprehensive test suite for memory implementations with real LLM integration and performance benchmarks.

## Overview

This test suite validates memory preservation and context enhancement when memory nodes are integrated with LLM nodes through real OpenAI API calls. Tests verify that memory systems effectively enhance LLM responses with relevant context from conversation history, entity relationships, knowledge facts, and graph connections.

## Test Categories

### 1. Memory-LLM Integration Tests (`test_memory_llm_integration.py`)

Tests core memory functionality with real LLM invocations:

- **Conversation Memory Preservation**: Verifies conversation history is maintained across LLM calls
- **Entity Memory Extraction**: Tests entity extraction from text and context enhancement
- **Knowledge Base Reasoning**: Validates fact storage and knowledge-based LLM reasoning
- **Graph Memory Relationships**: Tests relationship modeling and graph-based context
- **Episodic Memory Temporal Context**: Verifies temporal event storage and time-based context
- **Multi-Memory Context Merger**: Tests intelligent merging of multiple memory types
- **Memory-Enhanced Conversation Flow**: End-to-end conversation with memory accumulation

### 2. AI Node Integration Tests (`test_ai_node_memory_integration.py`)

Tests memory integration through AI Agent node execution pipeline:

- **AI Node with Conversation Memory**: Tests memory port connections with conversation context
- **AI Node with Multiple Memory Types**: Validates multiple memory connections simultaneously
- **Memory Context Prioritization**: Tests priority-based context selection
- **Memory Enhanced Workflow**: Complete workflow simulation with memory accumulation
- **Memory Node Specifications**: Validates node specifications include memory ports

### 3. Performance Tests (`test_memory_performance.py`)

Benchmarks memory system performance and scalability:

- **Bulk Storage Performance**: Tests high-volume message/entity/fact storage
- **Extraction Performance**: Benchmarks entity/fact extraction with OpenAI
- **Concurrent Operations**: Tests concurrent memory operations across types
- **Context Size Optimization**: Validates token limit management and compression
- **Memory Context Merger Performance**: Benchmarks context merging strategies

## Setup Requirements

### Environment Variables

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SECRET_KEY="your-service-role-key"
export OPENAI_API_KEY="sk-your-openai-key"
```

### Database Setup

Ensure Supabase database has memory tables created:

```sql
-- Run the database migrations
\i shared/memory_implementations/database_migrations.sql
```

## Running Tests

### Using the Test Runner (Recommended)

```bash
# Run all tests
python tests/test_runner.py

# Run specific test types
python tests/test_runner.py --type basic
python tests/test_runner.py --type integration
python tests/test_runner.py --type comprehensive

# Enable verbose logging
python tests/test_runner.py --verbose
```

### Using pytest

```bash
# Run all integration tests
pytest tests/ -v -m integration

# Run specific test file
pytest tests/test_memory_llm_integration.py -v

# Run with specific markers
pytest tests/ -m "memory and llm" -v

# Run performance tests
pytest tests/test_memory_performance.py -v
```

### Individual Test Modules

```bash
# Direct execution
python tests/test_memory_llm_integration.py
python tests/test_ai_node_memory_integration.py
python tests/test_memory_performance.py
```

## Test Architecture

### Mock Components

- **MockNodeExecutionContext**: Simulates workflow node execution environment
- **MockMemoryConnection**: Simulates memory port connections
- **AIAgentNodeMemoryExecutor**: Enhanced AI node executor with memory integration

### Memory Integration Pipeline

1. **Memory Storage**: Store data in various memory types
2. **Context Extraction**: Extract relevant context from memories
3. **Context Merging**: Intelligently merge multiple memory contexts
4. **LLM Enhancement**: Enhance LLM prompts with memory context
5. **Response Validation**: Verify LLM responses use memory information

### Performance Metrics

- **Storage Time**: Time to store data in memory systems
- **Extraction Time**: Time for AI-powered entity/fact extraction
- **Context Retrieval**: Time to retrieve relevant memory context
- **Merge Performance**: Time to merge multiple memory contexts
- **Token Optimization**: Efficiency of context compression
- **Concurrent Operations**: Scalability under concurrent load

## Expected Performance Benchmarks

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| Message Storage (100 msgs) | < 30s | Bulk conversation storage |
| Entity Extraction (5 texts) | < 10s avg | OpenAI extraction per text |
| Fact Storage (5 documents) | < 15s avg | Knowledge fact extraction |
| Graph Storage (5 texts) | < 12s avg | Relationship extraction |
| Context Retrieval | < 5s | Memory context generation |
| Context Merging | < 2s | Multi-memory context merge |
| Path Finding | < 5s | Graph relationship traversal |
| Concurrent Operations | < 60s | Mixed concurrent operations |

## Validation Criteria

### Memory Preservation
- LLM responses contain information from previous interactions
- Entity information persists across conversation turns
- Knowledge facts influence LLM reasoning
- Graph relationships inform response generation

### Context Enhancement
- Memory context improves response relevance
- Multiple memory types provide complementary information
- Context prioritization works correctly
- Token limits are respected with intelligent compression

### Integration Completeness
- AI nodes properly extract memory contexts from connections
- Memory port specifications are correctly defined
- Context merger handles multiple memory types
- End-to-end workflow maintains memory consistency

## Troubleshooting

### Common Issues

**Environment Variables Not Set**
```bash
# Check required variables
echo $SUPABASE_URL
echo $SUPABASE_SECRET_KEY
echo $OPENAI_API_KEY
```

**Database Connection Issues**
```bash
# Test Supabase connection
python -c "
from supabase import create_client
import os
client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SECRET_KEY'))
print('✅ Supabase connection successful')
"
```

**OpenAI API Issues**
```bash
# Test OpenAI connection
python -c "
import openai
import os
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
print('✅ OpenAI connection successful')
"
```

**Test Failures**
- Check test logs in `memory_tests.log`
- Verify database tables exist and have correct schema
- Ensure sufficient OpenAI API credits
- Check network connectivity for API calls

### Performance Issues

**Slow Entity/Fact Extraction**
- OpenAI API calls are inherently slower
- Consider reducing test data size for faster iteration
- Use `gpt-4o-mini` model for cost-effective testing

**Database Query Performance**
- Ensure indexes are created from migration script
- Check Supabase project performance metrics
- Consider connection pooling for high-volume tests

**Memory Usage**
- Large contexts can consume significant memory
- Token optimization helps reduce context size
- Monitor system memory during performance tests

## Contributing

When adding new memory types or integration tests:

1. Follow existing test patterns and naming conventions
2. Include both functional and performance tests
3. Add proper error handling and cleanup
4. Update this README with new test descriptions
5. Ensure tests work with mock and real LLM calls

## Test Results Interpretation

### Success Criteria
- ✅ All memory types store and retrieve data correctly
- ✅ LLM responses demonstrate memory usage
- ✅ Performance benchmarks are met
- ✅ Integration pipeline works end-to-end

### Warning Indicators
- ⚠️ Slow API responses (check OpenAI API status)
- ⚠️ High token usage (optimize context merging)
- ⚠️ Database connection timeouts (check Supabase)

### Failure Indicators
- ❌ Memory data not stored (database/auth issues)
- ❌ LLM responses lack context (integration failure)
- ❌ Performance benchmarks exceeded (scaling issues)
- ❌ Context merging failures (algorithm issues)
