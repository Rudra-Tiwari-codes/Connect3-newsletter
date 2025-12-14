-- Sample events for testing
INSERT INTO events (title, description, event_date, location, category, tags) VALUES
  ('Machine Learning Workshop', 'Learn the fundamentals of ML and neural networks', '2024-03-15 14:00:00+00', 'Engineering Building Room 301', 'tech_innovation', ARRAY['workshop', 'ai', 'technology']),
  ('Career Fair 2024', 'Meet recruiters from top companies', '2024-03-20 10:00:00+00', 'Student Union Hall', 'career_networking', ARRAY['career', 'networking', 'jobs']),
  ('Yoga in the Park', 'Free outdoor yoga session for all levels', '2024-03-18 07:00:00+00', 'University Park', 'health_wellness', ARRAY['yoga', 'wellness', 'outdoor']),
  ('Jazz Night', 'Live jazz performance by student ensemble', '2024-03-22 19:00:00+00', 'Music Hall', 'arts_music', ARRAY['music', 'jazz', 'performance']),
  ('Beach Cleanup Drive', 'Join us for environmental conservation', '2024-03-25 08:00:00+00', 'City Beach', 'volunteering_community', ARRAY['volunteering', 'environment', 'community']),
  ('Startup Pitch Competition', 'Present your business ideas to investors', '2024-03-28 15:00:00+00', 'Innovation Center', 'entrepreneurship', ARRAY['startup', 'business', 'pitch']),
  ('International Food Festival', 'Taste cuisines from around the world', '2024-03-30 12:00:00+00', 'Campus Plaza', 'food_dining', ARRAY['food', 'cultural', 'festival']),
  ('Basketball Tournament', 'Inter-college basketball championship', '2024-04-02 16:00:00+00', 'Sports Complex', 'sports_fitness', ARRAY['basketball', 'sports', 'tournament']),
  ('Gaming Convention', 'Esports tournaments and game demos', '2024-04-05 11:00:00+00', 'Convention Center', 'gaming_esports', ARRAY['gaming', 'esports', 'convention']),
  ('Hiking Trip', 'Weekend hiking adventure to mountain trails', '2024-04-08 06:00:00+00', 'North Mountain Trailhead', 'travel_adventure', ARRAY['hiking', 'outdoor', 'adventure'])
ON CONFLICT DO NOTHING;
