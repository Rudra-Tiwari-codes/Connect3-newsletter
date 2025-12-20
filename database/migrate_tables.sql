-- ============================================
-- Connect3 Newsletter - Required Tables Migration
-- Run this in Supabase SQL Editor
-- ============================================

-- 1. Create event_embeddings table
-- NOTE: event_id is INT8 to match your events.id column
CREATE TABLE IF NOT EXISTS public.event_embeddings (
    event_id INT8 PRIMARY KEY REFERENCES public.events(id) ON DELETE CASCADE,
    embedding JSONB NOT NULL,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add index for faster category lookups
CREATE INDEX IF NOT EXISTS idx_event_embeddings_category ON public.event_embeddings(category);

-- Enable RLS (Row Level Security)
ALTER TABLE public.event_embeddings ENABLE ROW LEVEL SECURITY;

-- Allow all users to read event_embeddings
CREATE POLICY "Allow read access to event_embeddings" ON public.event_embeddings
    FOR SELECT USING (true);

-- Allow all operations (for service key)
CREATE POLICY "Allow all operations on event_embeddings" ON public.event_embeddings
    FOR ALL USING (true) WITH CHECK (true);

-- ============================================
-- NOTE: You already have an 'interactions' table!
-- The pipeline can use it instead of feedback_logs.
-- If you still want feedback_logs, uncomment below:
-- ============================================

-- CREATE TABLE IF NOT EXISTS public.feedback_logs (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
--     event_id INT8 REFERENCES public.events(id) ON DELETE CASCADE,
--     feedback_type TEXT NOT NULL CHECK (feedback_type IN ('like', 'dislike', 'click', 'view')),
--     created_at TIMESTAMPTZ DEFAULT NOW()
-- );

-- ============================================
-- Verify table created
-- ============================================
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name = 'event_embeddings';

