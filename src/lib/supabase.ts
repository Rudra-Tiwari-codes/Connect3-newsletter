import { createClient } from '@supabase/supabase-js';

// Support both naming conventions for Supabase credentials
const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_SECRET_KEY;

if (!supabaseUrl || !supabaseKey) {
  throw new Error('Missing Supabase environment variables. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_SECRET_KEY)');
}

export const supabase = createClient(supabaseUrl, supabaseKey);

// Database type definitions
export interface Event {
  id: string;
  title: string;
  description: string | null;
  event_date: string;
  location: string | null;
  category: string | null;
  tags: string[] | null;
  source_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  pca_cluster_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface UserPreferences {
  user_id: string;
  academic_workshops: number;
  career_networking: number;
  social_cultural: number;
  sports_fitness: number;
  arts_music: number;
  tech_innovation: number;
  volunteering_community: number;
  food_dining: number;
  travel_adventure: number;
  health_wellness: number;
  entrepreneurship: number;
  environment_sustainability: number;
  gaming_esports: number;
  updated_at: string;
}

export interface FeedbackLog {
  id: string;
  user_id: string;
  event_id: string;
  action: 'like' | 'dislike' | 'click';
  created_at: string;
}

export interface RankedEvent extends Event {
  score: number;
  cluster_match: number;
  urgency_score: number;
}

// Event categories mapping
export const EVENT_CATEGORIES = [
  'academic_workshops',
  'career_networking',
  'social_cultural',
  'sports_fitness',
  'arts_music',
  'tech_innovation',
  'volunteering_community',
  'food_dining',
  'travel_adventure',
  'health_wellness',
  'entrepreneurship',
  'environment_sustainability',
  'gaming_esports',
] as const;

export type EventCategory = typeof EVENT_CATEGORIES[number];

// Mapping preference columns to event categories
export const PREFERENCE_TO_CATEGORY: Record<string, EventCategory> = {
  academic_workshops: 'academic_workshops',
  career_networking: 'career_networking',
  social_cultural: 'social_cultural',
  sports_fitness: 'sports_fitness',
  arts_music: 'arts_music',
  tech_innovation: 'tech_innovation',
  volunteering_community: 'volunteering_community',
  food_dining: 'food_dining',
  travel_adventure: 'travel_adventure',
  health_wellness: 'health_wellness',
  entrepreneurship: 'entrepreneurship',
  environment_sustainability: 'environment_sustainability',
  gaming_esports: 'gaming_esports',
};
