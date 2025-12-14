import OpenAI from 'openai';
import { Event, EVENT_CATEGORIES, EventCategory } from './supabase';

if (!process.env.OPENAI_API_KEY) {
  throw new Error('Missing OpenAI API key');
}

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export class EventClassifier {
  /**
   * Classify a single event into one of the predefined categories
   */
  async classifyEvent(event: Event): Promise<EventCategory> {
    const prompt = `Classify this university event into ONE of these categories:
${EVENT_CATEGORIES.join(', ')}

Event Title: ${event.title}
Event Description: ${event.description || 'No description'}
Event Location: ${event.location || 'No location'}

Respond with ONLY the category name, nothing else.`;

    try {
      const response = await openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: 'You are an event classification assistant. Respond with only the category name.',
          },
          { role: 'user', content: prompt },
        ],
        temperature: 0.3,
        max_tokens: 50,
      });

      const categoryString = response.choices[0].message.content?.trim().toLowerCase() || '';

      // Validate the category using type guard
      if (this.isValidEventCategory(categoryString)) {
        return categoryString;
      }

      console.warn(`Invalid category returned: ${categoryString}, defaulting to academic_workshops`);
      return 'academic_workshops';
    } catch (error) {
      console.error('Error classifying event:', error);
      return 'academic_workshops'; // Default fallback
    }
  }

  /**
   * Classify multiple events in parallel
   */
  async classifyBatch(events: Event[]): Promise<Map<string, EventCategory>> {
    const results = new Map<string, EventCategory>();

    const promises = events.map(async (event) => {
      const category = await this.classifyEvent(event);
      results.set(event.id, category);
    });

    await Promise.all(promises);
    return results;
  }

  /**
   * Type guard to check if a string is a valid EventCategory
   */
  private isValidEventCategory(category: string): category is EventCategory {
    return (EVENT_CATEGORIES as readonly string[]).includes(category);
  }

  /**
   * Extract relevant tags from event description using AI
   */
  async extractTags(event: Event): Promise<string[]> {
    const prompt = `Extract 3-5 relevant tags from this event:

Title: ${event.title}
Description: ${event.description || 'No description'}

Respond with comma-separated tags.`;

    try {
      const response = await openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: 'You are a tag extraction assistant. Respond with only comma-separated tags.',
          },
          { role: 'user', content: prompt },
        ],
        temperature: 0.5,
        max_tokens: 100,
      });

      const tagsString = response.choices[0].message.content?.trim() || '';
      return tagsString.split(',').map((tag) => tag.trim().toLowerCase()).filter(Boolean);
    } catch (error) {
      console.error('Error extracting tags:', error);
      return [];
    }
  }
}
