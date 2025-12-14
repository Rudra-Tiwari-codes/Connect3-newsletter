-- Seed initial users
INSERT INTO users (email, name) VALUES
  ('student1@university.edu', 'Alice Johnson'),
  ('student2@university.edu', 'Bob Smith'),
  ('student3@university.edu', 'Carol Davis'),
  ('student4@university.edu', 'David Wilson'),
  ('student5@university.edu', 'Emma Brown')
ON CONFLICT (email) DO NOTHING;

-- Initialize user preferences with default values (0.5 for all categories)
INSERT INTO user_preferences (user_id)
SELECT id FROM users
ON CONFLICT (user_id) DO NOTHING;
