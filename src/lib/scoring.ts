import { differenceInDays } from 'date-fns';
import { supabase, Event, User, UserPreferences, RankedEvent, EVENT_CATEGORIES, EventCategory } from './supabase';
import { SCORING_CONFIG } from './config';

export class EventScoringService {
  /**
   * Rank events for a specific user
   * Score = (ClusterMatch × CLUSTER_MATCH_WEIGHT) + (MAX_URGENCY_SCORE - DaysUntilEvent)
   */
  async rankEventsForUser(userId: string, limit: number = 10): Promise<RankedEvent[]> {
    // Fetch user data
    const { data: user, error: userError } = await supabase
      .from('users')
      .select('*')
      .eq('id', userId)
      .single();

    if (userError || !user) {
      throw new Error(`Failed to fetch user: ${userError?.message}`);
    }

    // Fetch user preferences
    const { data: preferences, error: prefsError } = await supabase
      .from('user_preferences')
      .select('*')
      .eq('user_id', userId)
      .single();

    if (prefsError || !preferences) {
      throw new Error(`Failed to fetch preferences: ${prefsError?.message}`);
    }

    // Fetch upcoming events
    const { data: events, error: eventsError } = await supabase
      .from('events')
      .select('*')
      .gte('event_date', new Date().toISOString())
      .order('event_date', { ascending: true })
      .limit(100);

    if (eventsError || !events) {
      throw new Error(`Failed to fetch events: ${eventsError?.message}`);
    }

    // Score each event
    const rankedEvents: RankedEvent[] = events.map((event) => {
      const clusterMatch = this.calculateClusterMatch(event, preferences);
      const urgencyScore = this.calculateUrgencyScore(event);
      const score = clusterMatch * SCORING_CONFIG.CLUSTER_MATCH_WEIGHT + urgencyScore;

      return {
        ...event,
        score,
        cluster_match: clusterMatch,
        urgency_score: urgencyScore,
      };
    });

    // Sort by score and return top N
    rankedEvents.sort((a, b) => b.score - a.score);
    return rankedEvents.slice(0, limit);
  }

  /**
   * Rank events for all users in a specific cluster
   */
  async rankEventsForCluster(clusterId: number, limit: number = 10): Promise<Map<string, RankedEvent[]>> {
    // Fetch all users in the cluster
    const { data: users, error: usersError } = await supabase
      .from('users')
      .select('*')
      .eq('pca_cluster_id', clusterId);

    if (usersError || !users) {
      throw new Error(`Failed to fetch cluster users: ${usersError?.message}`);
    }

    // Rank events for each user
    const results = new Map<string, RankedEvent[]>();
    for (const user of users) {
      try {
        const rankedEvents = await this.rankEventsForUser(user.id, limit);
        results.set(user.id, rankedEvents);
      } catch (error) {
        console.error(`Failed to rank events for user ${user.id}:`, error);
      }
    }

    return results;
  }

  /**
   * Calculate how well an event matches user preferences (0-1 scale)
   */
  private calculateClusterMatch(event: Event, preferences: UserPreferences): number {
    if (!event.category) {
      return 0.5; // Default neutral match
    }

    // Validate that the category exists in EVENT_CATEGORIES
    if (!EVENT_CATEGORIES.includes(event.category as EventCategory)) {
      return 0.5; // Default if category is not valid
    }

    // Safely access the preference value with proper type checking
    const category = event.category as EventCategory;
    const preferenceKey = category as keyof UserPreferences;
    
    // Verify the preference key exists and is a number
    if (preferenceKey in preferences) {
      const preferenceValue = preferences[preferenceKey];
      if (typeof preferenceValue === 'number') {
        return preferenceValue;
      }
    }

    return 0.5; // Default if category not found in preferences
  }

  /**
   * Calculate urgency score based on days until event
   * Returns: MAX_URGENCY_SCORE - daysUntilEvent (capped at 0 minimum)
   */
  private calculateUrgencyScore(event: Event): number {
    const now = new Date();
    const eventDate = new Date(event.event_date);
    const daysUntil = differenceInDays(eventDate, now);

    return Math.max(0, SCORING_CONFIG.MAX_URGENCY_SCORE - daysUntil);
  }

  /**
   * Get event recommendations for a user (alias for rankEventsForUser)
   */
  async getRecommendations(userId: string, limit: number = 10): Promise<RankedEvent[]> {
    return this.rankEventsForUser(userId, limit);
  }
}
