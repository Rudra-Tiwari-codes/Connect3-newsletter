-- Two-Tower Recommendation System Schema for Connect3
-- Run this in Supabase SQL Editor

-- Enable pgvector extension for vector similarity search (if available)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- Event embeddings table
CREATE TABLE IF NOT EXISTS event_embeddings (
  event_id TEXT PRIMARY KEY,
  embedding JSONB NOT NULL,  -- Store as JSONB for flexibility (use vector type if pgvector enabled)
  category TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_event_embeddings_category ON event_embeddings(category);
CREATE INDEX idx_event_embeddings_created ON event_embeddings(created_at);

-- User embeddings table (cached user tower outputs)
CREATE TABLE IF NOT EXISTS user_embeddings (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  embedding JSONB NOT NULL,
  version INTEGER DEFAULT 1,  -- Increment when embedding model changes
  computed_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Recommendation logs (for offline evaluation and model improvement)
CREATE TABLE IF NOT EXISTS recommendation_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  event_id TEXT,
  similarity_score FLOAT,
  recency_score FLOAT,
  final_score FLOAT,
  position INTEGER,  -- Rank position in recommendations
  model_version TEXT DEFAULT 'v1-mvp',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recommendation_logs_user ON recommendation_logs(user_id);
CREATE INDEX idx_recommendation_logs_event ON recommendation_logs(event_id);
CREATE INDEX idx_recommendation_logs_created ON recommendation_logs(created_at);

-- Email campaign tracking (for measuring recommendation effectiveness)
CREATE TABLE IF NOT EXISTS email_campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  sent_at TIMESTAMPTZ DEFAULT NOW(),
  total_recipients INTEGER DEFAULT 0,
  total_opens INTEGER DEFAULT 0,
  total_clicks INTEGER DEFAULT 0,
  model_version TEXT DEFAULT 'v1-mvp'
);

-- Link email logs to campaigns
ALTER TABLE email_logs ADD COLUMN IF NOT EXISTS campaign_id UUID REFERENCES email_campaigns(id);

-- Interaction types enum (expanded)
-- Note: If you get an error about the type already existing, skip this
DO $$ 
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'interaction_type') THEN
    CREATE TYPE interaction_type AS ENUM ('view', 'click', 'like', 'dislike', 'register', 'attend');
  END IF;
END $$;

-- User interactions table (more detailed than feedback_logs)
CREATE TABLE IF NOT EXISTS user_interactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  event_id TEXT NOT NULL,
  interaction_type TEXT NOT NULL,  -- 'view', 'click', 'like', 'dislike', 'register', 'attend'
  source TEXT,  -- 'email', 'app', 'website'
  campaign_id UUID REFERENCES email_campaigns(id),
  metadata JSONB,  -- Additional context
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_interactions_user ON user_interactions(user_id);
CREATE INDEX idx_user_interactions_event ON user_interactions(event_id);
CREATE INDEX idx_user_interactions_type ON user_interactions(interaction_type);
CREATE INDEX idx_user_interactions_created ON user_interactions(created_at);

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_event_embeddings_updated_at ON event_embeddings;
CREATE TRIGGER update_event_embeddings_updated_at 
  BEFORE UPDATE ON event_embeddings
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_embeddings_updated_at ON user_embeddings;
CREATE TRIGGER update_user_embeddings_updated_at 
  BEFORE UPDATE ON user_embeddings
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View for recommendation analytics
CREATE OR REPLACE VIEW recommendation_analytics AS
SELECT 
  DATE_TRUNC('day', rl.created_at) as date,
  rl.model_version,
  COUNT(*) as total_recommendations,
  AVG(rl.similarity_score) as avg_similarity,
  AVG(rl.final_score) as avg_final_score,
  COUNT(DISTINCT rl.user_id) as unique_users,
  COUNT(DISTINCT rl.event_id) as unique_events
FROM recommendation_logs rl
GROUP BY DATE_TRUNC('day', rl.created_at), rl.model_version
ORDER BY date DESC;

-- View for user engagement metrics
CREATE OR REPLACE VIEW user_engagement AS
SELECT 
  u.id as user_id,
  u.email,
  u.name,
  COUNT(DISTINCT ui.id) as total_interactions,
  COUNT(DISTINCT CASE WHEN ui.interaction_type = 'like' THEN ui.id END) as likes,
  COUNT(DISTINCT CASE WHEN ui.interaction_type = 'click' THEN ui.id END) as clicks,
  COUNT(DISTINCT CASE WHEN ui.interaction_type = 'dislike' THEN ui.id END) as dislikes,
  MAX(ui.created_at) as last_interaction
FROM users u
LEFT JOIN user_interactions ui ON u.id = ui.user_id
GROUP BY u.id, u.email, u.name;

-- Function to get top events for a category
CREATE OR REPLACE FUNCTION get_top_events_by_category(
  p_category TEXT,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  event_id TEXT,
  category TEXT,
  created_at TIMESTAMPTZ
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    ee.event_id,
    ee.category,
    ee.created_at
  FROM event_embeddings ee
  WHERE ee.category = p_category
  ORDER BY ee.created_at DESC
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed)
-- GRANT SELECT ON recommendation_analytics TO authenticated;
-- GRANT SELECT ON user_engagement TO authenticated;
