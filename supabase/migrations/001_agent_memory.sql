-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- LangGraph Native BaseStore & Memory Table
CREATE TABLE IF NOT EXISTS langgraph_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    value JSONB DEFAULT '{}'::jsonb NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Unique constraint on namespace + key
CREATE UNIQUE INDEX IF NOT EXISTS langgraph_memory_namespace_key_idx 
ON langgraph_memory (namespace, key);

-- HNSW Vector Index for low-latency semantic similarity search
CREATE INDEX IF NOT EXISTS langgraph_memory_embedding_hnsw_idx 
ON langgraph_memory USING hnsw (embedding vector_cosine_ops);
