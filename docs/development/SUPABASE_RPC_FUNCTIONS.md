# Supabase RPC Functions Documentation

This document provides a comprehensive reference for all Supabase RPC (Remote Procedure Call) functions used in the project.

## Overview

RPC functions are used to:
- Access cross-schema tables (especially `auth.users`)
- Perform complex database operations
- Encapsulate business logic in the database
- Provide secure, controlled access to sensitive data

## Why RPC Functions?

### Supabase Client Limitations
The Supabase Python client has limitations when accessing tables outside the `public` schema:

```python
# ❌ This fails - tries to query "public.auth.users"
supabase.table("auth.users").select("*").execute()

# ✅ This works - uses RPC function
supabase.rpc('check_user_exists', {'user_id': user_id}).execute()
```

### Benefits of RPC Approach
- **Schema-Agnostic**: Can access any schema (`auth`, `public`, etc.)
- **Security**: `SECURITY DEFINER` provides controlled access
- **Performance**: Pre-compiled functions are faster
- **Type Safety**: Predictable return types
- **Maintainability**: Logic centralized in database

## Available RPC Functions

### 1. User Management Functions

#### `check_user_exists(user_id uuid) → boolean`

**Purpose**: Check if a user exists in the `auth.users` table

**Migration**: `20250813000008_add_check_user_exists_function.sql`

**Definition**:
```sql
CREATE OR REPLACE FUNCTION check_user_exists(user_id uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM auth.users
        WHERE id = user_id
    );
END;
$$;
```

**Usage**:
```python
# Python/API Gateway
result = supabase.rpc('check_user_exists', {'user_id': 'uuid-string'}).execute()
if result.data is True:
    print("User exists")
```

**Use Cases**:
- GitHub installation callback validation
- User existence checks before operations
- Authentication validation

**Permissions**:
- `authenticated` role
- `service_role`

---

### 2. Node Knowledge Functions (RAG System)

#### `match_node_knowledge(query_embedding, match_threshold, match_count, node_type_filter) → table`

**Purpose**: Vector similarity search for node knowledge (RAG system)

**Migration**: `20250715000002_node_knowledge_vectors.sql`

**Definition**:
```sql
CREATE OR REPLACE FUNCTION match_node_knowledge(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.3,
    match_count int DEFAULT 5,
    node_type_filter text DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    node_type varchar,
    node_subtype varchar,
    title varchar,
    description text,
    content text,
    similarity float,
    metadata jsonb
)
```

**Usage**:
```python
# Workflow Agent RAG
result = supabase.rpc('match_node_knowledge', {
    'query_embedding': embedding_vector,
    'match_threshold': 0.3,
    'match_count': 5,
    'node_type_filter': 'TRIGGER_NODE'
}).execute()
```

**Use Cases**:
- AI workflow agent knowledge retrieval
- Node type recommendations
- Semantic search for workflow examples

---

## Usage Patterns

### 1. Authentication Validation
```python
async def validate_user_exists(user_id: str) -> bool:
    """Validate user exists in auth.users table"""
    try:
        supabase_admin = get_supabase_admin()
        result = supabase_admin.rpc('check_user_exists', {'user_id': user_id}).execute()
        return result.data is True
    except Exception as e:
        logger.error(f"Error validating user {user_id}: {e}")
        return False
```

### 2. RAG Knowledge Retrieval
```python
async def get_node_knowledge(query: str, node_type: str = None) -> List[Dict]:
    """Get relevant node knowledge using vector similarity"""
    # Generate embedding for query
    embedding = await generate_embedding(query)

    # Search for similar knowledge
    result = supabase.rpc('match_node_knowledge', {
        'query_embedding': embedding,
        'match_threshold': 0.3,
        'match_count': 5,
        'node_type_filter': node_type
    }).execute()

    return result.data
```

### 3. Error Handling
```python
def safe_rpc_call(function_name: str, params: dict):
    """Safe wrapper for RPC calls with error handling"""
    try:
        result = supabase.rpc(function_name, params).execute()
        if result.data is None:
            logger.warning(f"RPC {function_name} returned None")
            return None
        return result.data
    except Exception as e:
        logger.error(f"RPC {function_name} failed: {e}")
        return None
```

## Development Guidelines

### Creating New RPC Functions

1. **Create Migration File**:
```sql
-- Migration: 20250813000009_add_new_rpc_function.sql
CREATE OR REPLACE FUNCTION your_function_name(param1 type1, param2 type2)
RETURNS return_type
LANGUAGE plpgsql
SECURITY DEFINER  -- Allows access to restricted schemas
AS $$
BEGIN
    -- Function logic here
    RETURN result;
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION your_function_name(type1, type2) TO authenticated;
GRANT EXECUTE ON FUNCTION your_function_name(type1, type2) TO service_role;
```

2. **Add to This Documentation**
3. **Update Application Code**
4. **Add Tests**

### Best Practices

#### ✅ Do:
- Use `SECURITY DEFINER` for cross-schema access
- Grant minimal necessary permissions
- Include comprehensive error handling
- Document parameters and return types
- Use type-safe parameters (uuid, not text for IDs)

#### ❌ Don't:
- Return sensitive data unnecessarily
- Use dynamic SQL without sanitization
- Grant `PUBLIC` execute permissions
- Forget to handle NULL/empty cases

### Testing RPC Functions

#### Database Level Testing:
```sql
-- Test the function directly
SELECT check_user_exists('b6c5d44a-a94f-4459-928e-90283a88f105'::uuid);

-- Test edge cases
SELECT check_user_exists('00000000-0000-0000-0000-000000000000'::uuid);
```

#### Application Level Testing:
```python
async def test_rpc_function():
    """Test RPC function through Supabase client"""
    result = supabase.rpc('check_user_exists', {
        'user_id': 'b6c5d44a-a94f-4459-928e-90283a88f105'
    }).execute()
    assert result.data is True
```

## Migration Files

All RPC functions are defined in migration files:

- `20250715000002_node_knowledge_vectors.sql` - RAG functions
- `20250813000008_add_check_user_exists_function.sql` - User validation

## Security Considerations

### SECURITY DEFINER
- Functions run with creator's privileges
- Allows access to `auth` schema
- Use carefully - only for necessary operations

### Permission Model
```sql
-- Standard permissions for most RPC functions
GRANT EXECUTE ON FUNCTION function_name TO authenticated;
GRANT EXECUTE ON FUNCTION function_name TO service_role;

-- Avoid public access
-- GRANT EXECUTE ON FUNCTION function_name TO PUBLIC; -- ❌ Don't do this
```

### Data Exposure
- Only return necessary data
- Avoid exposing sensitive auth information
- Use specific return types, not `SELECT *`

## Troubleshooting

### Common Issues

#### 1. Permission Denied
```
ERROR: permission denied for function check_user_exists
```
**Solution**: Grant execute permissions to appropriate roles

#### 2. Function Does Not Exist
```
ERROR: function check_user_exists(text) does not exist
```
**Solution**: Check parameter types - use `uuid` not `text` for user IDs

#### 3. Cross-Schema Access Denied
```
ERROR: permission denied for schema auth
```
**Solution**: Use `SECURITY DEFINER` in function definition

### Debugging RPC Calls

#### Check Function Exists:
```sql
SELECT proname, proargnames, proargtypes
FROM pg_proc
WHERE proname = 'your_function_name';
```

#### Test Function Directly:
```sql
SELECT your_function_name('test_param');
```

#### Check Permissions:
```sql
SELECT has_function_privilege('authenticated', 'your_function_name(uuid)', 'execute');
```

## Future RPC Functions

Consider adding these RPC functions as the project grows:

### User Management
- `get_user_metadata(user_id uuid) → jsonb`
- `update_user_app_metadata(user_id uuid, metadata jsonb) → void`
- `get_user_roles(user_id uuid) → text[]`

### Workflow Operations
- `get_user_workflows(user_id uuid) → table`
- `validate_workflow_ownership(workflow_id uuid, user_id uuid) → boolean`
- `get_workflow_execution_stats(workflow_id uuid) → jsonb`

### Integration Management
- `get_user_integrations(user_id uuid) → table`
- `validate_integration_access(user_id uuid, provider text) → boolean`
- `cleanup_expired_tokens() → integer`

## Resources

- [Supabase RPC Documentation](https://supabase.com/docs/guides/database/functions)
- [PostgreSQL Function Documentation](https://www.postgresql.org/docs/current/sql-createfunction.html)
- [Vector Similarity Search Guide](https://supabase.com/docs/guides/ai/vector-columns)

---

**Last Updated**: 2025-08-13
**Maintainer**: Backend Team
**Related Docs**: `DEPLOYMENT.md`, `README.md`
