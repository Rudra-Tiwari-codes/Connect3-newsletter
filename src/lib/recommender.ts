/**
 * Two-Tower Recommendation Engine for Connect3
 * 
 * This implements the full recommendation pipeline:
 * 1. Load event embeddings
 * 2. Compute user embedding
 * 3. Retrieve top-N candidates via vector similarity
 * 4. Apply business rules (recency, diversity, etc.)
 * 5. Return final recommendations
 */

import { supabase } from './supabase';
import { embeddingService, CONNECT3_CATEGORIES, Connect3Category } from './embeddings';
import { VectorIndex, getEventIndex, SearchResult } from './vector-index';
import { differenceInDays } from 'date-fns';

export interface RecommendedEvent {
  event_id: string;
  title: string;
  caption: string;
  timestamp: string;
  permalink: string;
  media_url: string;
  category: Connect3Category | null;
  similarity_score: number;
  recency_score: number;
  final_score: number;
  reason: string; // Why this event is recommended
}

export interface RecommendationConfig {
  topK: number;               // Number of final recommendations
  candidateMultiplier: number; // Retrieve topK * this for re-ranking
  recencyWeight: number;      // Weight for recency (0-1)
  similarityWeight: number;   // Weight for similarity (0-1)
  diversityPenalty: number;   // Penalty for same-category events
  maxDaysOld: number;         // Filter out events older than this
}

const DEFAULT_CONFIG: RecommendationConfig = {
  topK: 10,
  candidateMultiplier: 3,
  recencyWeight: 0.3,
  similarityWeight: 0.7,
  diversityPenalty: 0.1,
  maxDaysOld: 60,
};

export class TwoTowerRecommender {
  private eventIndex: VectorIndex;
  private config: RecommendationConfig;

  constructor(config: Partial<RecommendationConfig> = {}) {
    this.eventIndex = getEventIndex();
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Load event embeddings into the vector index
   */
  async loadEventIndex(): Promise<void> {
    // Fetch all event embeddings from database
    const { data: eventEmbeddings, error } = await supabase
      .from('event_embeddings')
      .select('event_id, embedding, category, created_at');

    if (error) {
      throw new Error(`Failed to load event embeddings: ${error.message}`);
    }

    if (!eventEmbeddings || eventEmbeddings.length === 0) {
      console.log('No event embeddings found in database');
      return;
    }

    // Load into vector index
    this.eventIndex.clear();
    
    for (const event of eventEmbeddings) {
      const embedding = typeof event.embedding === 'string'
        ? JSON.parse(event.embedding)
        : event.embedding;

      this.eventIndex.add(event.event_id, embedding, {
        category: event.category,
        created_at: event.created_at,
      });
    }

    console.log(`Loaded ${eventEmbeddings.length} events into vector index`);
  }

  /**
   * Get recommendations for a user
   */
  async getRecommendations(userId: string): Promise<RecommendedEvent[]> {
    // Step 1: Get user embedding
    const userEmbedding = await embeddingService.embedUser(userId);

    // Step 2: Get user's past interactions to exclude
    const { data: pastInteractions } = await supabase
      .from('feedback_logs')
      .select('event_id')
      .eq('user_id', userId);

    const excludeIds = new Set(pastInteractions?.map(i => i.event_id) || []);

    // Step 3: Retrieve candidates via vector search
    const numCandidates = this.config.topK * this.config.candidateMultiplier;
    const candidates = this.eventIndex.search(
      userEmbedding.embedding,
      numCandidates,
      excludeIds
    );

    if (candidates.length === 0) {
      return [];
    }

    // Step 4: Fetch full event data for candidates
    const candidateIds = candidates.map(c => c.id);
    const { data: events } = await supabase
      .from('events')
      .select('*')
      .in('id', candidateIds);

    if (!events) return [];

    // Step 5: Apply business rules and re-rank
    const rankedEvents = this.applyBusinessRules(candidates, events);

    // Step 6: Add recommendation reasons
    return rankedEvents.slice(0, this.config.topK).map(event => ({
      ...event,
      reason: this.generateRecommendationReason(event),
    }));
  }

  /**
   * Apply business rules for re-ranking
   */
  private applyBusinessRules(
    candidates: SearchResult[],
    events: any[]
  ): Omit<RecommendedEvent, 'reason'>[] {
    const now = new Date();
    const scoredEvents: Omit<RecommendedEvent, 'reason'>[] = [];

    // Create lookup map for events
    const eventMap = new Map(events.map(e => [e.id, e]));

    // Track category counts for diversity
    const categoryCounts = new Map<string, number>();

    for (const candidate of candidates) {
      const event = eventMap.get(candidate.id);
      if (!event) continue;

      // Calculate recency score (newer = higher)
      const eventDate = new Date(event.timestamp || event.event_date);
      const daysOld = Math.abs(differenceInDays(eventDate, now));

      // Filter out old events
      if (daysOld > this.config.maxDaysOld) continue;

      // Recency score: 1 for today, decreasing with age
      const recencyScore = Math.max(0, 1 - (daysOld / this.config.maxDaysOld));

      // Diversity penalty
      const category = event.category || 'unknown';
      const categoryCount = categoryCounts.get(category) || 0;
      const diversityPenalty = categoryCount * this.config.diversityPenalty;
      categoryCounts.set(category, categoryCount + 1);

      // Final score
      const finalScore = 
        (candidate.score * this.config.similarityWeight) +
        (recencyScore * this.config.recencyWeight) -
        diversityPenalty;

      scoredEvents.push({
        event_id: event.id,
        title: event.title || this.extractTitle(event.caption),
        caption: event.caption || event.description,
        timestamp: event.timestamp || event.event_date,
        permalink: event.permalink || event.source_url,
        media_url: event.media_url || '',
        category: event.category,
        similarity_score: candidate.score,
        recency_score: recencyScore,
        final_score: finalScore,
      });
    }

    // Sort by final score
    scoredEvents.sort((a, b) => b.final_score - a.final_score);

    return scoredEvents;
  }

  /**
   * Extract title from caption (first line or first sentence)
   */
  private extractTitle(caption: string): string {
    if (!caption) return 'Event';
    
    // Get first line
    const firstLine = caption.split('\n')[0];
    
    // Clean emojis and truncate
    const cleaned = firstLine
      .replace(/[\u{1F600}-\u{1F64F}]/gu, '')
      .replace(/[\u{1F300}-\u{1F5FF}]/gu, '')
      .replace(/[\u{1F680}-\u{1F6FF}]/gu, '')
      .trim();

    return cleaned.length > 100 ? cleaned.substring(0, 100) + '...' : cleaned;
  }

  /**
   * Generate human-readable recommendation reason
   */
  private generateRecommendationReason(event: Omit<RecommendedEvent, 'reason'>): string {
    const reasons: string[] = [];

    // High similarity
    if (event.similarity_score > 0.8) {
      reasons.push('Matches your interests very well');
    } else if (event.similarity_score > 0.6) {
      reasons.push('Related to topics you enjoy');
    }

    // Category-based reason
    if (event.category) {
      const categoryNames: Record<string, string> = {
        'tech_workshop': 'tech and coding workshops',
        'career_networking': 'career and networking events',
        'hackathon': 'hackathons and competitions',
        'social_event': 'social activities',
        'academic_revision': 'academic support',
        'recruitment': 'club activities',
        'industry_talk': 'industry insights',
        'sports_recreation': 'sports and recreation',
        'entrepreneurship': 'entrepreneurship',
        'community_service': 'community events',
      };
      
      const categoryName = categoryNames[event.category] || event.category;
      reasons.push(`You've shown interest in ${categoryName}`);
    }

    // Recent event
    if (event.recency_score > 0.8) {
      reasons.push('Happening soon');
    }

    return reasons.length > 0 ? reasons.join(' • ') : 'Recommended for you';
  }

  /**
   * Get recommendations for all users (batch mode for email sending)
   */
  async getBatchRecommendations(
    userIds: string[]
  ): Promise<Map<string, RecommendedEvent[]>> {
    const results = new Map<string, RecommendedEvent[]>();

    // Process in parallel with concurrency limit
    const batchSize = 10;
    
    for (let i = 0; i < userIds.length; i += batchSize) {
      const batch = userIds.slice(i, i + batchSize);
      
      const batchResults = await Promise.all(
        batch.map(async (userId) => {
          try {
            const recommendations = await this.getRecommendations(userId);
            return { userId, recommendations };
          } catch (error) {
            console.error(`Failed to get recommendations for user ${userId}:`, error);
            return { userId, recommendations: [] };
          }
        })
      );

      for (const { userId, recommendations } of batchResults) {
        results.set(userId, recommendations);
      }
    }

    return results;
  }
}

export const recommender = new TwoTowerRecommender();
