-- Connect3: interactions table (aligned with database/migrate_tables.sql)
-- Creates the table if missing and applies the interaction_type constraint.

CREATE TABLE IF NOT EXISTS public.interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscriber_id UUID REFERENCES public.subscribers(id) ON DELETE CASCADE,
    event_id TEXT REFERENCES public.events(id) ON DELETE CASCADE,
    interaction_type TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.interactions
DROP CONSTRAINT IF EXISTS interactions_interaction_type_check;

ALTER TABLE public.interactions
ADD CONSTRAINT interactions_interaction_type_check
CHECK (interaction_type IN ('like', 'dislike', 'click', 'view'));

CREATE INDEX IF NOT EXISTS idx_interactions_subscriber_id ON public.interactions(subscriber_id);
CREATE INDEX IF NOT EXISTS idx_interactions_event_id ON public.interactions(event_id);
CREATE INDEX IF NOT EXISTS idx_interactions_created_at ON public.interactions(created_at);
