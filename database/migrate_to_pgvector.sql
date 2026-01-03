-- ============================================
-- Connect3 Newsletter - pgvector Migration
-- ============================================
-- This migration upgrades the event_embeddings table to use
-- native pgvector for 10-100x faster similarity search.
--
-- PREREQUISITES:
-- 1. Enable pgvector extension in Supabase Dashboard:
--    Database > Extensions > Search "vector" > Enable
--
-- RUN THIS IN: Supabase SQL Editor
-- ============================================

-- Step 1: Enable pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: Create new table with native vector type
-- Using vector(1536) for OpenAI text-embedding-3-small dimensions
CREATE TABLE IF NOT EXISTS public.event_embeddings_v2 (
    event_id TEXT PRIMARY KEY,
    embedding vector(1536) NOT NULL,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 3: Migrate existing data from JSONB to vector
-- This converts the JSONB array to native vector type
INSERT INTO public.event_embeddings_v2 (event_id, embedding, category, created_at)
SELECT 
    event_id,
    embedding::text::vector(1536),
    category,
    created_at
FROM public.event_embeddings
ON CONFLICT (event_id) DO UPDATE SET
    embedding = EXCLUDED.embedding,
    category = EXCLUDED.category;

-- Step 4: Create indexes for fast similarity search
-- IVFFlat index for approximate nearest neighbor (ANN) search
-- lists = sqrt(n_rows) is a good starting point, using 100 for ~10k events
CREATE INDEX IF NOT EXISTS idx_event_embeddings_v2_embedding 
ON public.event_embeddings_v2 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Category index for filtered searches
CREATE INDEX IF NOT EXISTS idx_event_embeddings_v2_category 
ON public.event_embeddings_v2(category);

-- Step 5: Enable RLS
ALTER TABLE public.event_embeddings_v2 ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read event_embeddings_v2" ON public.event_embeddings_v2
    FOR SELECT USING (true);

CREATE POLICY "Allow all event_embeddings_v2" ON public.event_embeddings_v2
    FOR ALL USING (true) WITH CHECK (true);

-- Step 6: Create function for similarity search
-- This replaces the NumPy-based search with database-native search
CREATE OR REPLACE FUNCTION match_events(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 10,
    category_filter text DEFAULT NULL
)
RETURNS TABLE (
    event_id text,
    category text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.event_id,
        e.category,
        1 - (e.embedding <=> query_embedding) as similarity
    FROM public.event_embeddings_v2 e
    WHERE 
        (category_filter IS NULL OR e.category = category_filter)
        AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Step 7: Swap tables (CAREFUL - this drops the old table!)
-- Uncomment these lines after verifying the migration worked:
-- DROP TABLE IF EXISTS public.event_embeddings;
-- ALTER TABLE public.event_embeddings_v2 RENAME TO event_embeddings;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check row counts match
SELECT 
    (SELECT COUNT(*) FROM public.event_embeddings) as old_count,
    (SELECT COUNT(*) FROM public.event_embeddings_v2) as new_count;

-- Test similarity search (use a sample event's embedding)
-- SELECT * FROM match_events(
--     (SELECT embedding FROM public.event_embeddings_v2 LIMIT 1),
--     0.5,
--     5
-- );

-- ============================================
-- ROLLBACK (if needed)
-- ============================================
-- DROP TABLE IF EXISTS public.event_embeddings_v2;
-- DROP FUNCTION IF EXISTS match_events;
