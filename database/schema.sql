-- Events table
CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  event_date TIMESTAMPTZ NOT NULL,
  location TEXT,
  category TEXT,
  tags TEXT[],
  source_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_date ON events(event_date);
CREATE INDEX idx_events_category ON events(category);
CREATE INDEX idx_events_created_at ON events(created_at);

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  pca_cluster_id INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_cluster ON users(pca_cluster_id);

-- User preferences table (13 dimensions matching event categories)
CREATE TABLE IF NOT EXISTS user_preferences (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  academic_workshops FLOAT DEFAULT 0.5,
  career_networking FLOAT DEFAULT 0.5,
  social_cultural FLOAT DEFAULT 0.5,
  sports_fitness FLOAT DEFAULT 0.5,
  arts_music FLOAT DEFAULT 0.5,
  tech_innovation FLOAT DEFAULT 0.5,
  volunteering_community FLOAT DEFAULT 0.5,
  food_dining FLOAT DEFAULT 0.5,
  travel_adventure FLOAT DEFAULT 0.5,
  health_wellness FLOAT DEFAULT 0.5,
  entrepreneurship FLOAT DEFAULT 0.5,
  environment_sustainability FLOAT DEFAULT 0.5,
  gaming_esports FLOAT DEFAULT 0.5,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Feedback logs table
CREATE TABLE IF NOT EXISTS feedback_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  event_id UUID REFERENCES events(id) ON DELETE CASCADE,
  action TEXT NOT NULL CHECK (action IN ('like', 'dislike', 'click')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_feedback_user ON feedback_logs(user_id);
CREATE INDEX idx_feedback_event ON feedback_logs(event_id);
CREATE INDEX idx_feedback_created ON feedback_logs(created_at);

-- Cluster templates table
CREATE TABLE IF NOT EXISTS cluster_templates (
  cluster_id INTEGER PRIMARY KEY,
  avg_preferences JSONB,
  member_count INTEGER DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Email logs table
CREATE TABLE IF NOT EXISTS email_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  sent_at TIMESTAMPTZ DEFAULT NOW(),
  status TEXT CHECK (status IN ('sent', 'failed', 'bounced')),
  error_message TEXT
);

CREATE INDEX idx_email_logs_user ON email_logs(user_id);
CREATE INDEX idx_email_logs_sent ON email_logs(sent_at);

-- Helper function for updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cluster_templates_updated_at BEFORE UPDATE ON cluster_templates
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
