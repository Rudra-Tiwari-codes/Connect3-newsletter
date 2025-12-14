/**
 * Naive Bayes Category Classifier
 * Ranks event categories for users based on their interaction history and preferences
 */

import { supabase } from './supabase';

// Category clusters from our event taxonomy
export const CATEGORY_CLUSTERS = {
  'Technical': ['Hackathon', 'Tech Workshop', 'Programming Competition'],
  'Professional': ['Career & Networking', 'Industry Talk', 'Recruitment', 'Workshop'],
  'Social': ['Social Event', 'Cultural Event', 'Food & Dining', 'Entertainment'],
  'Academic': ['Academic Support', 'Study Session', 'Tutorial', 'Lecture Series'],
  'Wellness': ['Sports & Recreation', 'Fitness', 'Mental Health', 'Yoga & Meditation'],
  'Creative': ['Arts & Crafts', 'Music', 'Performance', 'Film & Media'],
  'Advocacy': ['Community Service', 'Volunteering', 'Environmental', 'Social Justice']
};

// Get cluster for a category
export function getCategoryCluster(category: string): string | null {
  for (const [cluster, categories] of Object.entries(CATEGORY_CLUSTERS)) {
    if (categories.includes(category)) {
      return cluster;
    }
  }
  return null;
}

// Get all categories from a cluster
export function getClusterCategories(cluster: string): string[] {
  return CATEGORY_CLUSTERS[cluster as keyof typeof CATEGORY_CLUSTERS] || [];
}

interface UserInteraction {
  event_id: string;
  category: string;
  feedback_type: string; // 'interested', 'not_interested', 'registered'
  interaction_date: string;
}

interface CategoryProbability {
  category: string;
  cluster: string;
  probability: number;
  score: number;
}

export class NaiveBayesClassifier {
  private categoryPriors: Map<string, number> = new Map();
  private clusterPriors: Map<string, number> = new Map();
  
  constructor() {
    // Initialize with uniform priors for all categories
    const allCategories = Object.values(CATEGORY_CLUSTERS).flat();
    allCategories.forEach(category => {
      this.categoryPriors.set(category, 1 / allCategories.length);
    });
    
    // Initialize cluster priors
    Object.keys(CATEGORY_CLUSTERS).forEach(cluster => {
      this.clusterPriors.set(cluster, 1 / Object.keys(CATEGORY_CLUSTERS).length);
    });
  }

  /**
   * Rank categories for a user based on their history
   */
  async rankCategoriesForUser(userId: string): Promise<CategoryProbability[]> {
    // Get user's interaction history
    const interactions = await this.getUserInteractions(userId);
    
    // If no history, return random categories with equal probability
    if (interactions.length === 0) {
      return this.getRandomCategories();
    }

    // Calculate category scores using Naive Bayes
    const categoryScores = this.calculateCategoryScores(interactions);
    
    // Sort by probability (descending)
    return categoryScores
      .sort((a, b) => b.probability - a.probability);
  }

  /**
   * Get user's top N categories
   */
  async getTopCategoriesForUser(userId: string, topN: number = 3): Promise<string[]> {
    const rankedCategories = await this.rankCategoriesForUser(userId);
    return rankedCategories.slice(0, topN).map(c => c.category);
  }

  /**
   * Get user's top N clusters
   */
  async getTopClustersForUser(userId: string, topN: number = 3): Promise<string[]> {
    const rankedCategories = await this.rankCategoriesForUser(userId);
    
    // Aggregate scores by cluster
    const clusterScores = new Map<string, number>();
    rankedCategories.forEach(cat => {
      const currentScore = clusterScores.get(cat.cluster) || 0;
      clusterScores.set(cat.cluster, currentScore + cat.score);
    });
    
    // Sort and return top clusters
    return Array.from(clusterScores.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, topN)
      .map(([cluster]) => cluster);
  }

  /**
   * Get user interactions from database
   */
  private async getUserInteractions(userId: string): Promise<UserInteraction[]> {
    try {
      // Get feedback from feedback_logs
      const { data: feedbackData, error: feedbackError } = await supabase
        .from('feedback_logs')
        .select(`
          event_id,
          feedback_type,
          created_at,
          events (
            category
          )
        `)
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
        .limit(50); // Last 50 interactions

      if (feedbackError) throw feedbackError;

      // Get clicks from user_interactions
      const { data: clickData, error: clickError } = await supabase
        .from('user_interactions')
        .select(`
          event_id,
          interaction_type,
          created_at,
          events (
            category
          )
        `)
        .eq('user_id', userId)
        .eq('interaction_type', 'click')
        .order('created_at', { ascending: false })
        .limit(50);

      if (clickError) throw clickError;

      // Combine and format interactions
      const interactions: UserInteraction[] = [];

      feedbackData?.forEach((item: any) => {
        if (item.events?.category) {
          interactions.push({
            event_id: item.event_id,
            category: item.events.category,
            feedback_type: item.feedback_type,
            interaction_date: item.created_at
          });
        }
      });

      clickData?.forEach((item: any) => {
        if (item.events?.category) {
          interactions.push({
            event_id: item.event_id,
            category: item.events.category,
            feedback_type: 'clicked',
            interaction_date: item.created_at
          });
        }
      });

      return interactions;
    } catch (error) {
      console.error('Error fetching user interactions:', error);
      return [];
    }
  }

  /**
   * Calculate category scores using weighted Naive Bayes
   */
  private calculateCategoryScores(interactions: UserInteraction[]): CategoryProbability[] {
    // Count interactions per category with weights
    const categoryWeights = new Map<string, number>();
    const feedbackWeights = {
      'interested': 3.0,
      'registered': 5.0,
      'clicked': 2.0,
      'not_interested': -2.0,
      'not_for_me': -1.0
    };

    interactions.forEach(interaction => {
      const weight = feedbackWeights[interaction.feedback_type as keyof typeof feedbackWeights] || 1.0;
      const currentWeight = categoryWeights.get(interaction.category) || 0;
      categoryWeights.set(interaction.category, currentWeight + weight);
    });

    // Apply recency decay
    const now = new Date().getTime();
    interactions.forEach(interaction => {
      const daysSince = (now - new Date(interaction.interaction_date).getTime()) / (1000 * 60 * 60 * 24);
      const decayFactor = Math.exp(-daysSince / 30); // 30-day half-life
      const weight = feedbackWeights[interaction.feedback_type as keyof typeof feedbackWeights] || 1.0;
      
      const currentWeight = categoryWeights.get(interaction.category) || 0;
      categoryWeights.set(interaction.category, currentWeight + (weight * decayFactor * 0.5));
    });

    // Calculate probabilities for all categories
    const allCategories = Object.values(CATEGORY_CLUSTERS).flat();
    const scores: CategoryProbability[] = [];
    
    // Add smoothing parameter (Laplace smoothing)
    const alpha = 0.5;
    const totalInteractions = interactions.length + (allCategories.length * alpha);

    allCategories.forEach(category => {
      const weight = (categoryWeights.get(category) || 0) + alpha;
      const cluster = getCategoryCluster(category) || 'Unknown';
      
      // Calculate probability
      const probability = weight / totalInteractions;
      
      scores.push({
        category,
        cluster,
        probability,
        score: weight
      });
    });

    return scores;
  }

  /**
   * Return random categories for new users
   */
  private getRandomCategories(): CategoryProbability[] {
    const allCategories = Object.values(CATEGORY_CLUSTERS).flat();
    
    // Shuffle categories
    const shuffled = allCategories
      .map(category => ({
        category,
        cluster: getCategoryCluster(category) || 'Unknown',
        probability: 1 / allCategories.length,
        score: Math.random(),
        sort: Math.random()
      }))
      .sort((a, b) => a.sort - b.sort);

    return shuffled;
  }

  /**
   * Update user's category preference based on feedback
   */
  async updateUserCategoryPreference(
    userId: string,
    category: string,
    feedbackType: 'interested' | 'not_interested' | 'clicked'
  ): Promise<void> {
    // This is handled by the feedback API route
    // Just recalculate probabilities
    await this.rankCategoriesForUser(userId);
  }

  /**
   * Get diverse categories from different clusters
   */
  async getDiverseCategories(userId: string, count: number = 3): Promise<string[]> {
    const rankedCategories = await this.rankCategoriesForUser(userId);
    const selectedCategories: string[] = [];
    const usedClusters = new Set<string>();

    // Try to pick one category from different clusters
    for (const cat of rankedCategories) {
      if (selectedCategories.length >= count) break;
      
      if (!usedClusters.has(cat.cluster)) {
        selectedCategories.push(cat.category);
        usedClusters.add(cat.cluster);
      }
    }

    // If we don't have enough, fill with remaining top categories
    if (selectedCategories.length < count) {
      for (const cat of rankedCategories) {
        if (selectedCategories.length >= count) break;
        if (!selectedCategories.includes(cat.category)) {
          selectedCategories.push(cat.category);
        }
      }
    }

    return selectedCategories;
  }
}

// Export singleton instance
export const categoryClassifier = new NaiveBayesClassifier();
