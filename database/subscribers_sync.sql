-- Keep subscribers in sync with profiles (profiles -> subscribers)
-- Run in Supabase SQL editor with service role privileges.

-- Ensure profile_id can be uniquely referenced (NULLs are allowed)
CREATE UNIQUE INDEX IF NOT EXISTS subscribers_profile_id_key
ON public.subscribers(profile_id);

-- Upsert subscriber row when a profile is created or updated
CREATE OR REPLACE FUNCTION public.upsert_subscriber_from_profile()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.subscribers (
    profile_id,
    first_name,
    last_name,
    is_new_recipient,
    is_unsubscribed
  )
  VALUES (
    NEW.id,
    NEW.first_name,
    NEW.last_name,
    TRUE,
    FALSE
  )
  ON CONFLICT (profile_id) DO UPDATE
    SET first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

DROP TRIGGER IF EXISTS trg_profiles_to_subscribers ON public.profiles;

CREATE TRIGGER trg_profiles_to_subscribers
AFTER INSERT OR UPDATE OF first_name, last_name ON public.profiles
FOR EACH ROW
EXECUTE FUNCTION public.upsert_subscriber_from_profile();

-- Backfill existing profiles
INSERT INTO public.subscribers (
  profile_id,
  first_name,
  last_name,
  is_new_recipient,
  is_unsubscribed
)
SELECT
  p.id,
  p.first_name,
  p.last_name,
  TRUE,
  FALSE
FROM public.profiles p
ON CONFLICT (profile_id) DO UPDATE
  SET first_name = EXCLUDED.first_name,
      last_name = EXCLUDED.last_name;
