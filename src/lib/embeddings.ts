/**
 * Two-Tower Embedding System for Connect3 Event Recommendations
 * 
 * This implements a simplified two-tower architecture:
 * - Event Tower: Converts event text → embedding using OpenAI embeddings
 * - User Tower: Converts user preferences → embedding
 * 
 * For MVP, we use OpenAI's text-embedding-3-small which is:
 * - Fast and cheap ($0.02 per 1M tokens)
 * - 1536 dimensions (can be reduced)
 * - Good semantic understanding
 */

import OpenAI from 'openai';
import { supabase } from './supabase';

if (!process.env.OPENAI_API_KEY) {
  throw new Error('Missing OpenAI API key');
}

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Event categories for Connect3 (derived from DSCubed events)
export const CONNECT3_CATEGORIES = [
  'tech_workshop',      // AI, ML, coding workshops
  'career_networking',  // Industry panels, networking events
  'hackathon',          // Datathons, coding competitions
  'social_event',       // Bar nights, board games, social mixers
  'academic_revision',  // SWOTVAC sessions, exam prep
  'recruitment',        // Club recruitment, AGMs
  'industry_talk',      // Company presentations, guest speakers
  'sports_recreation',  // Sports day, physical activities
  'entrepreneurship',   // Startup events, founder talks
  'community_service',  // Volunteering, community events
] as const;

export type Connect3Category = typeof CONNECT3_CATEGORIES[number];

// Embedding dimensions
export const EMBEDDING_DIM = 1536; // OpenAI text-embedding-3-small

export interface EventEmbedding {
  event_id: string;
  embedding: number[];
  category: Connect3Category | null;
  created_at: string;
}

export interface UserEmbedding {
  user_id: string;
  embedding: number[];
  updated_at: string;
}

export class EmbeddingService {
  /**
   * Generate embedding for text using OpenAI
   */
  async generateEmbedding(text: string): Promise<number[]> {
    const response = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: text,
      encoding_format: 'float',
    });

    return response.data[0].embedding;
  }

  /**
   * Generate embeddings for multiple texts in batch
   */
  async generateBatchEmbeddings(texts: string[]): Promise<number[][]> {
    // OpenAI supports batch embedding
    const response = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: texts,
      encoding_format: 'float',
    });

    return response.data.map(d => d.embedding);
  }

  /**
   * EVENT TOWER: Convert event to embedding
   * Combines title, description, and inferred category
   */
  async embedEvent(event: {
    id: string;
    caption: string;
    timestamp: string;
  }): Promise<EventEmbedding> {
    // Create rich text representation for embedding
    const eventText = this.prepareEventText(event.caption);
    
    const embedding = await this.generateEmbedding(eventText);
    
    // Classify event category using the caption
    const category = await this.classifyEventCategory(event.caption);

    return {
      event_id: event.id,
      embedding,
      category,
      created_at: event.timestamp,
    };
  }

  /**
   * Prepare event text for embedding
   */
  private prepareEventText(caption: string): string {
    // Clean up Instagram caption for embedding
    // Remove hashtags but keep the words
    let cleanText = caption.replace(/#(\w+)/g, '$1');
    
    // Remove emoji (optional - they can add context)
    cleanText = cleanText.replace(/[\u{1F600}-\u{1F64F}]/gu, '');
    cleanText = cleanText.replace(/[\u{1F300}-\u{1F5FF}]/gu, '');
    cleanText = cleanText.replace(/[\u{1F680}-\u{1F6FF}]/gu, '');
    cleanText = cleanText.replace(/[\u{1F1E0}-\u{1F1FF}]/gu, '');
    cleanText = cleanText.replace(/[\u{2600}-\u{26FF}]/gu, '');
    cleanText = cleanText.replace(/[\u{2700}-\u{27BF}]/gu, '');
    
    // Collapse whitespace
    cleanText = cleanText.replace(/\s+/g, ' ').trim();
    
    // Truncate to reasonable length (8191 tokens max for OpenAI)
    return cleanText.substring(0, 8000);
  }

  /**
   * Classify event into Connect3 category using AI
   */
  async classifyEventCategory(caption: string): Promise<Connect3Category | null> {
    try {
      const response = await openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: `Classify this university club event into ONE of these categories:
${CONNECT3_CATEGORIES.join(', ')}

Respond with ONLY the category name, nothing else.`
          },
          { role: 'user', content: caption.substring(0, 2000) }
        ],
        temperature: 0.1,
        max_tokens: 50,
      });

      const category = response.choices[0].message.content?.trim().toLowerCase();
      
      if (CONNECT3_CATEGORIES.includes(category as Connect3Category)) {
        return category as Connect3Category;
      }
      
      return null;
    } catch (error) {
      console.error('Error classifying event:', error);
      return null;
    }
  }

  /**
   * USER TOWER: Convert user preferences to embedding
   * 
   * For users with interaction history: Average their interacted event embeddings
   * For new users: Generate from declared preferences
   */
  async embedUser(userId: string): Promise<UserEmbedding> {
    // Check if user has interaction history
    const { data: interactions } = await supabase
      .from('feedback_logs')
      .select('event_id, action')
      .eq('user_id', userId);

    if (interactions && interactions.length > 0) {
      // User has history - use weighted average of interacted events
      return this.embedUserFromHistory(userId, interactions);
    } else {
      // Cold start - use declared preferences
      return this.embedUserFromPreferences(userId);
    }
  }

  /**
   * Embed user from interaction history (weighted average)
   */
  private async embedUserFromHistory(
    userId: string,
    interactions: { event_id: string; action: string }[]
  ): Promise<UserEmbedding> {
    // Fetch event embeddings for interacted events
    const eventIds = interactions.map(i => i.event_id);
    
    const { data: eventEmbeddings } = await supabase
      .from('event_embeddings')
      .select('event_id, embedding')
      .in('event_id', eventIds);

    if (!eventEmbeddings || eventEmbeddings.length === 0) {
      // Fall back to preferences
      return this.embedUserFromPreferences(userId);
    }

    // Weight by action type
    const weights: Record<string, number> = {
      'like': 1.0,
      'click': 0.5,
      'dislike': -0.5,
    };

    // Compute weighted average
    const embedding = new Array(EMBEDDING_DIM).fill(0);
    let totalWeight = 0;

    for (const interaction of interactions) {
      const eventEmb = eventEmbeddings.find(e => e.event_id === interaction.event_id);
      if (eventEmb && eventEmb.embedding) {
        const weight = weights[interaction.action] || 0;
        const embVector = typeof eventEmb.embedding === 'string' 
          ? JSON.parse(eventEmb.embedding) 
          : eventEmb.embedding;
        
        for (let i = 0; i < EMBEDDING_DIM; i++) {
          embedding[i] += embVector[i] * weight;
        }
        totalWeight += Math.abs(weight);
      }
    }

    // Normalize
    if (totalWeight > 0) {
      for (let i = 0; i < EMBEDDING_DIM; i++) {
        embedding[i] /= totalWeight;
      }
    }

    return {
      user_id: userId,
      embedding,
      updated_at: new Date().toISOString(),
    };
  }

  /**
   * Embed user from declared preferences (cold start)
   */
  private async embedUserFromPreferences(userId: string): Promise<UserEmbedding> {
    // Fetch user preferences
    const { data: preferences } = await supabase
      .from('user_preferences')
      .select('*')
      .eq('user_id', userId)
      .single();

    // Build a text representation of preferences
    let preferencesText = 'University student interested in: ';
    
    if (preferences) {
      const interests: string[] = [];
      
      // Map preference scores to interests
      const prefMapping: Record<string, string> = {
        tech_innovation: 'technology, AI, machine learning, coding',
        career_networking: 'career development, networking, industry connections',
        academic_workshops: 'academic workshops, revision sessions, study groups',
        social_cultural: 'social events, parties, cultural activities',
        entrepreneurship: 'startups, entrepreneurship, business',
        sports_fitness: 'sports, fitness, physical activities',
      };

      for (const [key, description] of Object.entries(prefMapping)) {
        const score = preferences[key];
        if (score && score > 0.6) {
          interests.push(description);
        }
      }

      if (interests.length > 0) {
        preferencesText += interests.join(', ');
      } else {
        preferencesText += 'general university events';
      }
    } else {
      preferencesText += 'general university events, student activities';
    }

    const embedding = await this.generateEmbedding(preferencesText);

    return {
      user_id: userId,
      embedding,
      updated_at: new Date().toISOString(),
    };
  }

  /**
   * Compute cosine similarity between two embeddings
   */
  cosineSimilarity(a: number[], b: number[]): number {
    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
  }

  /**
   * Find top-N similar events for a user embedding
   */
  async findSimilarEvents(
    userEmbedding: number[],
    topN: number = 10,
    excludeEventIds: string[] = []
  ): Promise<{ event_id: string; similarity: number }[]> {
    // Fetch all event embeddings
    const { data: eventEmbeddings } = await supabase
      .from('event_embeddings')
      .select('event_id, embedding');

    if (!eventEmbeddings) return [];

    // Compute similarities
    const similarities = eventEmbeddings
      .filter(e => !excludeEventIds.includes(e.event_id))
      .map(event => {
        const embVector = typeof event.embedding === 'string'
          ? JSON.parse(event.embedding)
          : event.embedding;
        
        return {
          event_id: event.event_id,
          similarity: this.cosineSimilarity(userEmbedding, embVector),
        };
      })
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, topN);

    return similarities;
  }
}

export const embeddingService = new EmbeddingService();
