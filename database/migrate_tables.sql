-- ============================================
-- Connect3 Newsletter - Complete Database Schema
-- Run this in Supabase SQL Editor
-- ============================================

-- ============================================
-- EXISTING TABLES (already in your database)
-- ============================================
-- 1. events (id: int8, title, description, date, category, image_url, created_at)
-- 2. users (id: uuid, email, name, preferences, top_categories, created_at)
-- 3. interactions (id, user_id, event_id, interaction_type, created_at)

-- ============================================
-- ADD top_categories COLUMN TO USERS TABLE
-- ============================================
-- This stores user's top 3 preferred categories as a JSON array
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS top_categories JSONB DEFAULT '[]'::jsonb;

-- ============================================
-- NEW TABLES TO CREATE
-- ============================================

-- 1. event_embeddings - Stores vector embeddings for event recommendations
-- NOTE: Uses TEXT for event_id to match Instagram post IDs from all_posts.json
DROP TABLE IF EXISTS public.event_embeddings;
CREATE TABLE public.event_embeddings (
    event_id TEXT PRIMARY KEY,
    embedding JSONB NOT NULL,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_embeddings_category ON public.event_embeddings(category);

ALTER TABLE public.event_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read event_embeddings" ON public.event_embeddings
    FOR SELECT USING (true);

CREATE POLICY "Allow all event_embeddings" ON public.event_embeddings
    FOR ALL USING (true) WITH CHECK (true);

-- ============================================

-- 2. user_preferences - Stores user interest scores for cold-start recommendations
-- Defaults to uniform distribution: 1/13 ≈ 0.077 per category
CREATE TABLE IF NOT EXISTS public.user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    tech_innovation FLOAT DEFAULT 0.077,
    career_networking FLOAT DEFAULT 0.077,
    academic_workshops FLOAT DEFAULT 0.077,
    social_cultural FLOAT DEFAULT 0.077,
    entrepreneurship FLOAT DEFAULT 0.077,
    sports_fitness FLOAT DEFAULT 0.077,
    arts_music FLOAT DEFAULT 0.077,
    volunteering_community FLOAT DEFAULT 0.077,
    food_dining FLOAT DEFAULT 0.077,
    travel_adventure FLOAT DEFAULT 0.077,
    health_wellness FLOAT DEFAULT 0.077,
    environment_sustainability FLOAT DEFAULT 0.077,
    gaming_esports FLOAT DEFAULT 0.077,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON public.user_preferences(user_id);

ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own preferences" ON public.user_preferences
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Allow all user_preferences" ON public.user_preferences
    FOR ALL USING (true) WITH CHECK (true);

-- ============================================

-- 3. email_logs - Tracks sent emails for analytics
CREATE TABLE IF NOT EXISTS public.email_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('sent', 'failed', 'pending')),
    error_message TEXT,
    events_sent JSONB,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_logs_user_id ON public.email_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_status ON public.email_logs(status);

ALTER TABLE public.email_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read email_logs" ON public.email_logs
    FOR SELECT USING (true);

CREATE POLICY "Allow all email_logs" ON public.email_logs
    FOR ALL USING (true) WITH CHECK (true);

-- ============================================
-- VERIFY ALL TABLES EXIST
-- ============================================
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('events', 'users', 'interactions', 'event_embeddings', 'user_preferences', 'email_logs')
ORDER BY table_name;


ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS is_unsubscribed BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS unsubscribed_at TIMESTAMPTZ;
  