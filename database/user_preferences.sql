-- Connect3: user_preferences table (profiles + preferences schema)

CREATE TABLE IF NOT EXISTS public.user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    academic_workshops DOUBLE PRECISION DEFAULT 0.0714,
    arts_music DOUBLE PRECISION DEFAULT 0.0714,
    career_networking DOUBLE PRECISION DEFAULT 0.0714,
    entrepreneurship DOUBLE PRECISION DEFAULT 0.0714,
    environment_sustainability DOUBLE PRECISION DEFAULT 0.0714,
    food_dining DOUBLE PRECISION DEFAULT 0.0714,
    gaming_esports DOUBLE PRECISION DEFAULT 0.0714,
    health_wellness DOUBLE PRECISION DEFAULT 0.0714,
    social_cultural DOUBLE PRECISION DEFAULT 0.0714,
    sports_fitness DOUBLE PRECISION DEFAULT 0.0714,
    tech_innovation DOUBLE PRECISION DEFAULT 0.0714,
    travel_adventure DOUBLE PRECISION DEFAULT 0.0714,
    volunteering_community DOUBLE PRECISION DEFAULT 0.0714,
    recruitment DOUBLE PRECISION DEFAULT 0.0714,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON public.user_preferences(user_id);
