/**
 * Category-Based Recommender
 * Recommends 3 events from 3 different categories based on Naive Bayes classification
 */

import { supabase } from './supabase';
import { categoryClassifier, getCategoryCluster, getClusterCategories } from './category-classifier';

export interface CategoryRecommendation {
  category: string;
  cluster: string;
  event: {
    id: string;
    title: string;
    description: string;
    category: string;
    event_date: string;
    location: string;
    url?: string;
    club_name?: string;
  };
  reason: string;
  rank: number; // 1 = highest priority category, 2 = second, 3 = third
}

export interface UserCategoryProfile {
  userId: string;
  topCategories: string[];
  topClusters: string[];
  recommendations: CategoryRecommendation[];
}

export class CategoryBasedRecommender {
  /**
   * Get 3 recommendations (one from each of top 3 categories)
   */
  async getRecommendations(userId: string): Promise<CategoryRecommendation[]> {
    // Get top 3 diverse categories for the user
    const topCategories = await categoryClassifier.getDiverseCategories(userId, 3);
    
    console.log(`\n📊 Top categories for user ${userId}:`, topCategories);

    // Get one event from each category
    const recommendations: CategoryRecommendation[] = [];
    
    for (let i = 0; i < topCategories.length; i++) {
      const category = topCategories[i];
      const event = await this.getTopEventFromCategory(userId, category);
      
      if (event) {
        const cluster = getCategoryCluster(category) || 'Unknown';
        recommendations.push({
          category,
          cluster,
          event,
          reason: this.generateRecommendationReason(category, cluster, i + 1),
          rank: i + 1
        });
      }
    }

    // If we don't have 3 recommendations, fill with random events from unused categories
    if (recommendations.length < 3) {
      console.log(`⚠️ Only ${recommendations.length} recommendations found, filling with random events...`);
      const usedCategories = recommendations.map(r => r.category);
      const remainingCount = 3 - recommendations.length;
      
      const randomRecs = await this.getRandomEventsFromUnusedCategories(
        userId,
        usedCategories,
        remainingCount
      );
      
      recommendations.push(...randomRecs);
    }

    return recommendations.slice(0, 3);
  }

  /**
   * Get the best event from a specific category
   */
  private async getTopEventFromCategory(
    userId: string,
    category: string
  ): Promise<CategoryRecommendation['event'] | null> {
    try {
      // Get events user has already interacted with
      const { data: interactedEvents } = await supabase
        .from('user_interactions')
        .select('event_id')
        .eq('user_id', userId);

      const excludeIds = interactedEvents?.map(i => i.event_id) || [];

      // Get upcoming events from this category
      const { data: events, error } = await supabase
        .from('events')
        .select('*')
        .eq('category', category)
        .gte('event_date', new Date().toISOString())
        .not('id', 'in', `(${excludeIds.join(',')})`)
        .order('event_date', { ascending: true })
        .limit(5);

      if (error) throw error;

      if (!events || events.length === 0) {
        console.log(`⚠️ No events found for category: ${category}`);
        return null;
      }

      // Return the soonest upcoming event
      const event = events[0];
      return {
        id: event.id,
        title: event.title,
        description: event.description,
        category: event.category,
        event_date: event.event_date,
        location: event.location,
        url: event.url,
        club_name: event.club_name
      };
    } catch (error) {
      console.error(`Error fetching event for category ${category}:`, error);
      return null;
    }
  }

  /**
   * Get random events from unused categories to fill gaps
   */
  private async getRandomEventsFromUnusedCategories(
    userId: string,
    usedCategories: string[],
    count: number
  ): Promise<CategoryRecommendation[]> {
    try {
      // Get events user has already interacted with
      const { data: interactedEvents } = await supabase
        .from('user_interactions')
        .select('event_id')
        .eq('user_id', userId);

      const excludeIds = interactedEvents?.map(i => i.event_id) || [];

      // Get random upcoming events not from used categories
      const { data: events, error } = await supabase
        .from('events')
        .select('*')
        .gte('event_date', new Date().toISOString())
        .not('category', 'in', `(${usedCategories.join(',')})`)
        .not('id', 'in', `(${excludeIds.join(',')})`)
        .order('event_date', { ascending: true })
        .limit(count * 3); // Get extra to randomize

      if (error) throw error;

      if (!events || events.length === 0) {
        return [];
      }

      // Shuffle and take requested count
      const shuffled = events.sort(() => Math.random() - 0.5).slice(0, count);
      
      return shuffled.map((event, index) => {
        const cluster = getCategoryCluster(event.category) || 'Unknown';
        return {
          category: event.category,
          cluster,
          event: {
            id: event.id,
            title: event.title,
            description: event.description,
            category: event.category,
            event_date: event.event_date,
            location: event.location,
            url: event.url,
            club_name: event.club_name
          },
          reason: this.generateRecommendationReason(event.category, cluster, usedCategories.length + index + 1),
          rank: usedCategories.length + index + 1
        };
      });
    } catch (error) {
      console.error('Error fetching random events:', error);
      return [];
    }
  }

  /**
   * Generate recommendation reason text
   */
  private generateRecommendationReason(category: string, cluster: string, rank: number): string {
    const reasons = {
      1: [
        `Based on your history, ${category} events are your top match!`,
        `You love ${category} events - this one's perfect for you!`,
        `${category} is your favorite - we found this gem for you!`,
        `This ${category} event matches your interests perfectly!`
      ],
      2: [
        `You've shown interest in ${category} events before.`,
        `${category} events are among your preferences.`,
        `We think you'll enjoy this ${category} event!`,
        `This ${category} event aligns with your interests.`
      ],
      3: [
        `Exploring ${category} events based on your ${cluster} interests.`,
        `You might like this ${category} event!`,
        `Trying something new: ${category} events.`,
        `Broadening your horizons with ${category}.`
      ]
    };

    const rankReasons = reasons[rank as keyof typeof reasons] || reasons[3];
    return rankReasons[Math.floor(Math.random() * rankReasons.length)];
  }

  /**
   * Get user's category profile
   */
  async getUserProfile(userId: string): Promise<UserCategoryProfile> {
    const topCategories = await categoryClassifier.getTopCategoriesForUser(userId, 5);
    const topClusters = await categoryClassifier.getTopClustersForUser(userId, 3);
    const recommendations = await this.getRecommendations(userId);

    return {
      userId,
      topCategories,
      topClusters,
      recommendations
    };
  }

  /**
   * Record that user clicked on an event (updates their category preferences)
   */
  async recordClick(userId: string, eventId: string): Promise<void> {
    try {
      // Get event category
      const { data: event } = await supabase
        .from('events')
        .select('category')
        .eq('id', eventId)
        .single();

      if (!event) {
        console.error('Event not found:', eventId);
        return;
      }

      // Log interaction
      await supabase
        .from('user_interactions')
        .insert({
          user_id: userId,
          event_id: eventId,
          interaction_type: 'click',
          created_at: new Date().toISOString()
        });

      console.log(`✅ Recorded click: User ${userId} clicked ${event.category} event`);
    } catch (error) {
      console.error('Error recording click:', error);
    }
  }

  /**
   * Record feedback (interested/not interested)
   */
  async recordFeedback(
    userId: string,
    eventId: string,
    feedbackType: 'interested' | 'not_interested'
  ): Promise<void> {
    try {
      // Get event category
      const { data: event } = await supabase
        .from('events')
        .select('category')
        .eq('id', eventId)
        .single();

      if (!event) {
        console.error('Event not found:', eventId);
        return;
      }

      // Log feedback
      await supabase
        .from('feedback_logs')
        .insert({
          user_id: userId,
          event_id: eventId,
          feedback_type: feedbackType,
          created_at: new Date().toISOString()
        });

      // Update category classifier
      await categoryClassifier.updateUserCategoryPreference(userId, event.category, feedbackType);

      console.log(`✅ Recorded feedback: User ${userId} ${feedbackType} for ${event.category} event`);
    } catch (error) {
      console.error('Error recording feedback:', error);
    }
  }

  /**
   * Get events from a user's preferred cluster (for follow-up emails)
   */
  async getEventsFromPreferredCluster(
    userId: string,
    count: number = 5
  ): Promise<CategoryRecommendation['event'][]> {
    try {
      // Get user's top cluster
      const topClusters = await categoryClassifier.getTopClustersForUser(userId, 1);
      if (topClusters.length === 0) {
        return [];
      }

      const preferredCluster = topClusters[0];
      const clusterCategories = getClusterCategories(preferredCluster);

      // Get events user has already interacted with
      const { data: interactedEvents } = await supabase
        .from('user_interactions')
        .select('event_id')
        .eq('user_id', userId);

      const excludeIds = interactedEvents?.map(i => i.event_id) || [];

      // Get upcoming events from cluster categories
      const { data: events, error } = await supabase
        .from('events')
        .select('*')
        .in('category', clusterCategories)
        .gte('event_date', new Date().toISOString())
        .not('id', 'in', `(${excludeIds.join(',')})`)
        .order('event_date', { ascending: true })
        .limit(count);

      if (error) throw error;

      return events?.map(event => ({
        id: event.id,
        title: event.title,
        description: event.description,
        category: event.category,
        event_date: event.event_date,
        location: event.location,
        url: event.url,
        club_name: event.club_name
      })) || [];
    } catch (error) {
      console.error('Error fetching cluster events:', error);
      return [];
    }
  }
}

// Export singleton instance
export const categoryRecommender = new CategoryBasedRecommender();
