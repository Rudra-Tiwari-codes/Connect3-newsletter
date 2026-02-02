-- Connect3: user_preferences table (profiles + preferences schema)

CREATE TABLE IF NOT EXISTS public.user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    tech_innovation DOUBLE PRECISION DEFAULT 0.077,
    career_networking DOUBLE PRECISION DEFAULT 0.077,
    academic_workshops DOUBLE PRECISION DEFAULT 0.077,
    social_cultural DOUBLE PRECISION DEFAULT 0.077,
    entrepreneurship DOUBLE PRECISION DEFAULT 0.077,
    sports_fitness DOUBLE PRECISION DEFAULT 0.077,
    arts_music DOUBLE PRECISION DEFAULT 0.077,
    volunteering_community DOUBLE PRECISION DEFAULT 0.077,
    food_dining DOUBLE PRECISION DEFAULT 0.077,
    travel_adventure DOUBLE PRECISION DEFAULT 0.077,
    health_wellness DOUBLE PRECISION DEFAULT 0.077,
    environment_sustainability DOUBLE PRECISION DEFAULT 0.077,
    gaming_esports DOUBLE PRECISION DEFAULT 0.077,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON public.user_preferences(user_id);
