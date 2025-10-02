# Memory Node Persistence Plan

## 🎯 **Objective**
Migrate from in-memory storage to proper Supabase persistence for all memory node types while maintaining performance and scalability.

## 📊 **Current State Analysis**

### ❌ **Problems with Current Implementation**
- Memory data lost on service restart
- No sharing between workflow executions
- No persistence across sessions
- Memory leaks in long-running processes
- No backup/recovery capabilities

### ✅ **Existing Infrastructure**
- `memory_nodes` table - Node definitions ✅
- `memory_data` table - Generic key-value storage ✅
- `embeddings` table - Vector storage ✅
- `entities` & `entity_relationships` tables - Entity tracking ✅

## 🗄️ **Database Schema Plan**

### **Tables to PRESERVE (from cleanup migration)**

```sql
-- DO NOT DROP - Required for memory persistence
conversation_buffers      -- For CONVERSATION_BUFFER memory type
conversation_summaries    -- For CONVERSATION_SUMMARY memory type
document_store           -- For DOCUMENT_STORE memory type
episodic_memory          -- For EPISODIC_MEMORY memory type
knowledge_facts          -- For KNOWLEDGE_BASE memory type
knowledge_rules          -- For KNOWLEDGE_BASE memory type
graph_nodes              -- For GRAPH_MEMORY memory type
graph_relationships      -- For GRAPH_MEMORY memory type
```

### **Tables Already Available**
```sql
memory_nodes             -- ✅ Node configuration & metadata
memory_data              -- ✅ Generic key-value storage (KEY_VALUE_STORE, WORKING_MEMORY)
embeddings              -- ✅ Vector storage (VECTOR_DATABASE)
entities                -- ✅ Entity storage (ENTITY_MEMORY)
entity_relationships    -- ✅ Entity relationships (ENTITY_MEMORY)
```

## 🔧 **Implementation Strategy**

### **Phase 1: Update Database Schema (Immediate)**

1. **Modify Cleanup Migration** - Remove specific memory tables from DROP list
2. **Enhance Existing Tables** - Add missing columns for memory features
3. **Create Indexes** - Optimize for memory operations

### **Phase 2: Implement Persistent Memory Classes**

#### **2.1 ConversationBufferMemory → Supabase**
```python
class ConversationBufferMemory(MemoryBase):
    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Store in conversation_buffers table
        query = """
        INSERT INTO conversation_buffers
        (user_id, memory_node_id, role, content, message_order, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        # Retrieve from conversation_buffers table
        # Order by message_order for chronological history
```

#### **2.2 VectorDatabaseMemory → Supabase**
```python
class VectorDatabaseMemory(MemoryBase):
    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Use existing embeddings table
        # Generate embeddings using OpenAI/sentence-transformers

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        # Semantic search using vector similarity
        # Use pgvector for efficient similarity queries
```

#### **2.3 EntityMemory → Supabase**
```python
class EntityMemory(MemoryBase):
    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Use existing entities + entity_relationships tables
        # Support entity extraction and relationship mapping
```

### **Phase 3: Migration Strategy**

#### **3.1 Backward Compatibility**
- Keep in-memory fallback for development
- Gradual migration flag: `use_database_storage`
- Support both implementations during transition

#### **3.2 Data Migration**
- Export existing in-memory data (if any)
- Bulk insert into appropriate tables
- Validate data integrity

## 📋 **Detailed Table Requirements**

### **conversation_buffers**
```sql
CREATE TABLE conversation_buffers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_node_id VARCHAR(255) NOT NULL,
    message_order INTEGER NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Ensure ordering within memory node
    UNIQUE(user_id, memory_node_id, message_order)
);
```

### **conversation_summaries**
```sql
CREATE TABLE conversation_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_node_id VARCHAR(255) NOT NULL,
    summary_text TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    last_message_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- One summary per memory node
    UNIQUE(user_id, memory_node_id)
);
```

### **episodic_memory**
```sql
CREATE TABLE episodic_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_node_id VARCHAR(255) NOT NULL,
    episode_id VARCHAR(255) NOT NULL,
    context TEXT NOT NULL,
    importance_score DECIMAL(3, 2) DEFAULT 0.5,
    temporal_context JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, memory_node_id, episode_id)
);
```

### **document_store**
```sql
CREATE TABLE document_store (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_node_id VARCHAR(255) NOT NULL,
    document_id VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    document_type VARCHAR(100) DEFAULT 'text',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, memory_node_id, document_id)
);
```

### **knowledge_facts & knowledge_rules**
```sql
CREATE TABLE knowledge_facts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_node_id VARCHAR(255) NOT NULL,
    fact_id VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    predicate VARCHAR(255) NOT NULL,
    object TEXT NOT NULL,
    confidence DECIMAL(3, 2) DEFAULT 0.8,
    source VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, memory_node_id, fact_id)
);

CREATE TABLE knowledge_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_node_id VARCHAR(255) NOT NULL,
    rule_id VARCHAR(255) NOT NULL,
    condition_pattern TEXT NOT NULL,
    action_pattern TEXT NOT NULL,
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, memory_node_id, rule_id)
);
```

### **graph_nodes & graph_relationships**
```sql
CREATE TABLE graph_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_node_id VARCHAR(255) NOT NULL,
    node_id VARCHAR(255) NOT NULL,
    node_type VARCHAR(100) NOT NULL,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, memory_node_id, node_id)
);

CREATE TABLE graph_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_node_id VARCHAR(255) NOT NULL,
    relationship_id VARCHAR(255) NOT NULL,
    source_node_id VARCHAR(255) NOT NULL,
    target_node_id VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(100) NOT NULL,
    properties JSONB DEFAULT '{}',
    weight DECIMAL(5, 3) DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, memory_node_id, relationship_id),

    -- Foreign keys to graph_nodes (within same memory node)
    FOREIGN KEY (user_id, memory_node_id, source_node_id)
        REFERENCES graph_nodes(user_id, memory_node_id, node_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id, memory_node_id, target_node_id)
        REFERENCES graph_nodes(user_id, memory_node_id, node_id) ON DELETE CASCADE
);
```

## 🚀 **Implementation Phases**

### **Phase 1: Database Schema (Week 1)**
- [ ] Update cleanup migration to preserve memory tables
- [ ] Create enhanced table schemas with proper indexes
- [ ] Add RLS policies for multi-tenant security
- [ ] Create helper functions for common operations

### **Phase 2: Base Classes (Week 2)**
- [ ] Create abstract `PersistentMemoryBase` class
- [ ] Implement Supabase client integration
- [ ] Add transaction support and error handling
- [ ] Create memory node factory with database config

### **Phase 3: Memory Implementations (Week 3-4)**
- [ ] `ConversationBufferMemory` → `conversation_buffers`
- [ ] `ConversationSummaryMemory` → `conversation_summaries`
- [ ] `VectorDatabaseMemory` → `embeddings` (enhanced)
- [ ] `EntityMemory` → `entities` + `entity_relationships`
- [ ] `DocumentStoreMemory` → `document_store`

### **Phase 4: Advanced Memory Types (Week 5-6)**
- [ ] `EpisodicMemory` → `episodic_memory`
- [ ] `KnowledgeBaseMemory` → `knowledge_facts` + `knowledge_rules`
- [ ] `GraphMemory` → `graph_nodes` + `graph_relationships`
- [ ] `WorkingMemory` → `memory_data` (enhanced TTL support)

### **Phase 5: Testing & Migration (Week 7)**
- [ ] Comprehensive testing with real data
- [ ] Performance benchmarking vs in-memory
- [ ] Migration scripts for existing workflows
- [ ] Documentation and examples

## 📈 **Performance Considerations**

### **Optimization Strategies**
1. **Connection Pooling** - Use pgbouncer for database connections
2. **Batch Operations** - Bulk insert/update for conversation buffers
3. **Indexes** - Proper indexing on user_id, memory_node_id, timestamps
4. **Caching** - Redis cache for frequently accessed memory data
5. **Vector Search** - Use pgvector for efficient similarity queries

### **Expected Performance**
- **Memory Operations**: 10-50ms (vs <1ms in-memory)
- **Vector Search**: 50-200ms with proper indexes
- **Conversation History**: 20-100ms for typical queries
- **Entity Lookup**: 10-30ms with proper indexes

## 🔒 **Security & Privacy**

### **Row Level Security (RLS)**
```sql
-- Example RLS policy for conversation_buffers
CREATE POLICY "Users can manage their own conversation buffers" ON conversation_buffers
    FOR ALL USING (auth.uid() = user_id);
```

### **Data Privacy**
- All memory data is user-scoped
- Automatic cleanup of expired data
- Support for data export/import
- GDPR compliance with user data deletion

## 🎯 **Success Metrics**

1. **Persistence**: Memory data survives service restarts
2. **Performance**: <100ms for typical memory operations
3. **Scalability**: Support 1000+ concurrent users
4. **Reliability**: 99.9% uptime for memory operations
5. **Data Integrity**: Zero data loss during operations

## 📝 **Next Steps**

1. **Review and approve this plan**
2. **Update the cleanup migration immediately**
3. **Begin Phase 1 database schema implementation**
4. **Create proof-of-concept for one memory type**
5. **Establish testing framework for memory persistence**
