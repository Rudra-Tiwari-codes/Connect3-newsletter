-- Connect3: event_embeddings table

CREATE TABLE IF NOT EXISTS public.event_embeddings (
    event_id TEXT PRIMARY KEY,
    embedding JSONB NOT NULL,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_embeddings_category ON public.event_embeddings(category);

CREATE OR REPLACE FUNCTION public.set_event_embeddings_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_trigger
    WHERE tgname = 'trg_event_embeddings_updated_at'
  ) THEN
    CREATE TRIGGER trg_event_embeddings_updated_at
    BEFORE UPDATE ON public.event_embeddings
    FOR EACH ROW
    EXECUTE FUNCTION public.set_event_embeddings_updated_at();
  END IF;
END $$;
