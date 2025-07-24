-- Just the function creation (for existing database)
-- Copy and paste this in Supabase SQL Editor

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
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        nkv.id,
        nkv.node_type,
        nkv.node_subtype,
        nkv.title,
        nkv.description,
        nkv.content,
        1 - (nkv.embedding <=> query_embedding) as similarity,
        nkv.metadata
    FROM node_knowledge_vectors nkv
    WHERE
        (node_type_filter IS NULL OR nkv.node_type = node_type_filter)
        AND 1 - (nkv.embedding <=> query_embedding) > match_threshold
    ORDER BY nkv.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Verify function was created
SELECT 'Vector search function created successfully!' as status;
