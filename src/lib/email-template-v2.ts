/**
 * Updated Email Template for Two-Tower Recommendations
 * 
 * Generates personalized HTML emails with recommendation reasons
 */

import { format } from 'date-fns';
import { User } from './supabase';
import { RecommendedEvent } from './recommender';

export class TwoTowerEmailTemplate {
  /**
   * Generate personalized HTML email for a user with AI-powered recommendations
   */
  generateEmail(user: User, events: RecommendedEvent[], feedbackBaseUrl: string): string {
    const eventCards = events
      .map((event, index) => this.generateEventCard(event, user, feedbackBaseUrl, index + 1))
      .join('');

    return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Events Picked Just For You | Connect3</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f0f4f8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <div style="max-width: 600px; margin: 0 auto; background-color: white;">
    
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%); color: white; padding: 40px 30px; text-align: center;">
      <h1 style="margin: 0; font-size: 28px; font-weight: 700;">
         Events Picked Just For You
      </h1>
      <p style="margin: 12px 0 0 0; opacity: 0.95; font-size: 16px;">
        Hey ${this.escapeHtml(user.name || 'there')}! Our AI found ${events.length} events you'll love
      </p>
    </div>
    
    <!-- AI Badge -->
    <div style="background: #fef3c7; padding: 12px 30px; border-bottom: 1px solid #fcd34d;">
      <p style="margin: 0; color: #92400e; font-size: 13px; text-align: center;">
         <strong>Powered by Connect3 AI</strong> — These recommendations are personalized based on your interests and activity
      </p>
    </div>
    
    <!-- Events Section -->
    <div style="padding: 30px;">
      <h2 style="margin: 0 0 20px 0; color: #1e293b; font-size: 18px; font-weight: 600;">
         Your Top Events This Week
      </h2>
      
      ${eventCards}
      
      <!-- How it works -->
      <div style="margin-top: 30px; padding: 20px; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 12px; border: 1px solid #bae6fd;">
        <h3 style="margin: 0 0 12px 0; color: #0369a1; font-size: 14px; font-weight: 600;">
           How Connect3 AI Works
        </h3>
        <p style="margin: 0; color: #0c4a6e; font-size: 13px; line-height: 1.6;">
          We use a Two-Tower neural network to match events to your interests. 
          The more you interact, the better our recommendations become!
        </p>
      </div>
    </div>
    
    <!-- Footer -->
    <div style="background: #f8fafc; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0;">
      <p style="margin: 0 0 8px 0; color: #64748b; font-size: 13px;">
        Connect3 by DSCubed • University of Melbourne
      </p>
      <p style="margin: 0; color: #94a3b8; font-size: 11px;">
        Powered by AI and Machine Learning
      </p>
    </div>
  </div>
</body>
</html>
    `;
  }

  /**
   * Generate a single event card
   */
  private generateEventCard(
    event: RecommendedEvent,
    user: User,
    feedbackBaseUrl: string,
    rank: number
  ): string {
    const eventDate = new Date(event.timestamp);
    const formattedDate = format(eventDate, "EEEE, MMMM d 'at' h:mm a");
    
    // Determine match quality badge
    const matchBadge = this.getMatchBadge(event.similarity_score);
    
    return `
      <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
        
        <!-- Event Header -->
        <div style="display: flex; align-items: start; margin-bottom: 12px;">
          <span style="background: #6366f1; color: white; width: 28px; height: 28px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; margin-right: 12px; flex-shrink: 0;">
            ${rank}
          </span>
          <div style="flex: 1;">
            <h3 style="margin: 0; color: #1e293b; font-size: 16px; font-weight: 600; line-height: 1.4;">
              ${this.escapeHtml(event.title)}
            </h3>
          </div>
        </div>
        
        <!-- Match Badge & Category -->
        <div style="margin-bottom: 12px;">
          ${matchBadge}
          ${event.category ? `
            <span style="display: inline-block; background: #f1f5f9; color: #475569; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 500; margin-left: 6px;">
              ${this.formatCategory(event.category)}
            </span>
          ` : ''}
        </div>
        
        <!-- Event Details -->
        <p style="margin: 0 0 12px 0; color: #64748b; font-size: 13px; line-height: 1.5;">
          📅 ${formattedDate}
        </p>
        
        <!-- Description -->
        <p style="margin: 0 0 16px 0; color: #475569; font-size: 14px; line-height: 1.6;">
          ${this.escapeHtml(this.truncateDescription(event.caption))}
        </p>
        
        <!-- Why Recommended -->
        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 10px 12px; margin-bottom: 16px;">
          <p style="margin: 0; color: #166534; font-size: 12px;">
            💡 <strong>Why this event?</strong> ${this.escapeHtml(event.reason)}
          </p>
        </div>
        
        <!-- Action Buttons -->
        <div style="display: flex; gap: 8px;">
          <a href="${this.escapeHtml(feedbackBaseUrl)}?uid=${this.escapeHtml(user.id)}&eid=${this.escapeHtml(event.event_id)}&action=like" 
             style="flex: 1; background: #22c55e; color: white; padding: 12px 16px; text-decoration: none; border-radius: 8px; text-align: center; font-size: 14px; font-weight: 600;">
             Interested
          </a>
          <a href="${this.escapeHtml(feedbackBaseUrl)}?uid=${this.escapeHtml(user.id)}&eid=${this.escapeHtml(event.event_id)}&action=dislike" 
             style="flex: 1; background: #f1f5f9; color: #475569; padding: 12px 16px; text-decoration: none; border-radius: 8px; text-align: center; font-size: 14px; font-weight: 600;">
             Not for me
          </a>
        </div>
        
        ${event.permalink ? `
          <a href="${this.escapeHtml(event.permalink)}" 
             style="display: block; margin-top: 12px; color: #6366f1; text-decoration: none; font-size: 13px; font-weight: 500; text-align: center;">
            View on Instagram →
          </a>
        ` : ''}
      </div>
    `;
  }

  /**
   * Get match quality badge based on similarity score
   */
  private getMatchBadge(score: number): string {
    if (score >= 0.85) {
      return `<span style="display: inline-block; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); color: #92400e; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600;">⭐ Perfect Match</span>`;
    } else if (score >= 0.7) {
      return `<span style="display: inline-block; background: #dcfce7; color: #166534; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600;">✓ Great Match</span>`;
    } else if (score >= 0.5) {
      return `<span style="display: inline-block; background: #e0f2fe; color: #0369a1; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600;">~ Good Match</span>`;
    }
    return `<span style="display: inline-block; background: #f1f5f9; color: #475569; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 500;">Suggested</span>`;
  }

  /**
   * Format category name for display
   */
  private formatCategory(category: string): string {
    const categoryNames: Record<string, string> = {
      'tech_workshop': ' Tech Workshop',
      'career_networking': ' Career & Networking',
      'hackathon': ' Hackathon',
      'social_event': ' Social Event',
      'academic_revision': ' Academic',
      'recruitment': ' Club Recruitment',
      'industry_talk': ' Industry Talk',
      'sports_recreation': ' Sports',
      'entrepreneurship': ' Entrepreneurship',
      'community_service': ' Community',
    };
    
    return categoryNames[category] || category.replace(/_/g, ' ');
  }

  /**
   * Truncate description to reasonable length
   */
  private truncateDescription(text: string): string {
    if (!text) return '';
    
    // Remove hashtags
    let cleaned = text.replace(/#\w+/g, '');
    
    // Get first 2-3 sentences or 200 chars
    const sentences = cleaned.split(/[.!?]+/).filter(s => s.trim());
    const preview = sentences.slice(0, 2).join('. ').trim();
    
    if (preview.length > 200) {
      return preview.substring(0, 200) + '...';
    }
    
    return preview + (sentences.length > 2 ? '...' : '');
  }

  /**
   * Escape HTML to prevent XSS
   */
  private escapeHtml(text: string): string {
    if (!text) return '';
    const map: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
  }
}

export const twoTowerEmailTemplate = new TwoTowerEmailTemplate();
