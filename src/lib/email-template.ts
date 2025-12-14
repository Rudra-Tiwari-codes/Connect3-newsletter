import { format } from 'date-fns';
import { RankedEvent, User } from './supabase';

export class EmailTemplateService {
  /**
   * Generate personalized HTML email for a user
   */
  generatePersonalizedEmail(user: User, events: RankedEvent[], feedbackBaseUrl: string): string {
    const eventCards = events
      .map(
        (event) => `
      <div style="background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h3 style="color: #1a73e8; margin-top: 0;">${this.escapeHtml(event.title)}</h3>
        <p style="color: #666; margin: 10px 0;">
          <strong>When:</strong> ${format(new Date(event.event_date), 'MMMM d, yyyy \'at\' h:mm a')}<br>
          <strong>Where:</strong> ${this.escapeHtml(event.location || 'TBA')}<br>
          <strong>Category:</strong> ${this.formatCategory(event.category || 'general')}
        </p>
        <p style="color: #333; line-height: 1.6;">${this.escapeHtml(event.description || 'No description available')}</p>
        <div style="margin-top: 15px;">
          <span style="background: #e8f0fe; color: #1a73e8; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 5px;">
            Match: ${Math.round(event.cluster_match * 100)}%
          </span>
          <span style="background: #fef7e0; color: #f9ab00; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
            Score: ${Math.round(event.score)}
          </span>
        </div>
        <div style="margin-top: 15px;">
          <a href="${this.escapeHtml(feedbackBaseUrl)}?uid=${this.escapeHtml(user.id)}&eid=${this.escapeHtml(event.id)}&action=like" 
             style="background: #34a853; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; margin-right: 10px; display: inline-block;">
            Interested
          </a>
          <a href="${this.escapeHtml(feedbackBaseUrl)}?uid=${this.escapeHtml(user.id)}&eid=${this.escapeHtml(event.id)}&action=dislike" 
             style="background: #ea4335; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block;">
            Not Interested
          </a>
        </div>
      </div>
    `
      )
      .join('');

    return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your Personalized Event Newsletter</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: Arial, sans-serif;">
  <div style="max-width: 600px; margin: 0 auto; background-color: white;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
      <h1 style="margin: 0; font-size: 28px;">Your Weekly Event Picks</h1>
      <p style="margin: 10px 0 0 0; opacity: 0.9;">Personalized just for you, ${this.escapeHtml(user.name || user.email)}</p>
    </div>
    
    <div style="padding: 30px;">
      <p style="color: #666; line-height: 1.6;">
        Hi ${this.escapeHtml(user.name || 'there')}! 👋<br><br>
        We've curated these ${events.length} events based on your interests and preferences. 
        Click the buttons to let us know what you think!
      </p>
      
      ${eventCards}
      
      <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; text-align: center;">
        <p style="color: #666; margin: 0; font-size: 14px;">
          Want to update your preferences? Reply to this email or visit your dashboard.
        </p>
      </div>
    </div>
    
    <div style="background: #f8f9fa; padding: 20px; text-align: center; color: #999; font-size: 12px;">
      <p style="margin: 0;">
        University Event Newsletter System<br>
        Powered by AI and Machine Learning
      </p>
    </div>
  </div>
</body>
</html>
    `;
  }

  /**
   * Generate batch email template for a cluster
   */
  generateClusterTemplate(clusterEvents: RankedEvent[], clusterId: number): string {
    return `Cluster ${clusterId} Template - ${clusterEvents.length} events`;
  }

  /**
   * Escape HTML to prevent XSS
   */
  private escapeHtml(text: string): string {
    const map: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
  }

  /**
   * Format category name for display
   */
  private formatCategory(category: string): string {
    return category
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }
}
