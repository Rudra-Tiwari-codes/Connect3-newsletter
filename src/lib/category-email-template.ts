/**
 * Category-Based Email Template
 * Generates emails with 3 events from 3 different categories
 */

import { CategoryRecommendation } from './category-recommender';

export interface EmailData {
  userName: string;
  userEmail: string;
  recommendations: CategoryRecommendation[];
  userId: string;
}

/**
 * Generate email subject line
 */
export function generateSubject(userName: string): string {
  const subjects = [
    `${userName}, discover 3 events picked just for you!`,
    `${userName}'s personalized event picks are here!`,
    `${userName}, we found 3 events you'll love!`,
    `Your weekly event picks, ${userName}!`,
    `${userName}, check out these 3 must-see events!`
  ];
  
  return subjects[Math.floor(Math.random() * subjects.length)];
}

/**
 * Format event date
 */
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const options: Intl.DateTimeFormatOptions = {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  };
  return date.toLocaleDateString('en-AU', options);
}

/**
 * Truncate description
 */
function truncateDescription(description: string, maxLength: number = 200): string {
  if (description.length <= maxLength) return description;
  return description.substring(0, maxLength).trim() + '...';
}

/**
 * Get cluster emoji
 */
function getClusterEmoji(cluster: string): string {
  const emojis: Record<string, string> = {
    'Technical': '💻',
    'Professional': '💼',
    'Social': '🎉',
    'Academic': '📚',
    'Wellness': '🧘',
    'Creative': '🎨',
    'Advocacy': '🌍'
  };
  return emojis[cluster] || '✨';
}

/**
 * Generate HTML email
 */
export function generateCategoryEmail(data: EmailData): string {
  const { userName, recommendations, userId } = data;
  
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';

  // Generate event cards
  const eventCards = recommendations.map((rec, index) => {
    const clusterEmoji = getClusterEmoji(rec.cluster);
    const rankLabels = ['🥇 Top Pick', '🥈 Second Choice', '🥉 Third Choice'];
    const rankLabel = rankLabels[rec.rank - 1] || `#${rec.rank}`;

    const likeUrl = `${baseUrl}/api/feedback?uid=${userId}&eid=${rec.event.id}&action=like`;
    const dislikeUrl = `${baseUrl}/api/feedback?uid=${userId}&eid=${rec.event.id}&action=dislike`;
    const clickUrl = rec.event.url || `${baseUrl}/api/feedback?uid=${userId}&eid=${rec.event.id}&action=click`;

    return `
      <tr>
        <td style="padding: 20px 0;">
          <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <tr>
              <td style="padding: 24px;">
                <!-- Rank Badge -->
                <table cellpadding="0" cellspacing="0" border="0" width="100%">
                  <tr>
                    <td style="padding-bottom: 12px;">
                      <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;">${rankLabel}</span>
                      <span style="margin-left: 8px; font-size: 20px;">${clusterEmoji}</span>
                      <span style="margin-left: 8px; color: #666; font-size: 13px;">${rec.category}</span>
                    </td>
                  </tr>
                </table>

                <!-- Event Title -->
                <h2 style="margin: 16px 0 12px 0; font-size: 22px; color: #2d3748; line-height: 1.3;">
                  ${rec.event.title}
                </h2>

                <!-- Club Name -->
                ${rec.event.club_name ? `
                <p style="margin: 0 0 12px 0; color: #667eea; font-size: 14px; font-weight: 600;">
                  📍 ${rec.event.club_name}
                </p>
                ` : ''}

                <!-- Reason -->
                <div style="background: #f7fafc; padding: 12px; border-radius: 8px; margin-bottom: 16px; border-left: 3px solid #667eea;">
                  <p style="margin: 0; color: #4a5568; font-size: 14px; font-style: italic;">
                    💡 ${rec.reason}
                  </p>
                </div>

                <!-- Description -->
                <p style="margin: 0 0 16px 0; color: #4a5568; font-size: 15px; line-height: 1.6;">
                  ${truncateDescription(rec.event.description)}
                </p>

                <!-- Event Details -->
                <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 20px;">
                  <tr>
                    <td style="padding: 8px 0; border-top: 1px solid #e2e8f0;">
                      <table cellpadding="0" cellspacing="0" border="0">
                        <tr>
                          <td style="padding-right: 20px;">
                            <span style="color: #718096; font-size: 13px;">📅 ${formatDate(rec.event.event_date)}</span>
                          </td>
                          <td>
                            <span style="color: #718096; font-size: 13px;">📍 ${rec.event.location}</span>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>

                <!-- Action Buttons -->
                <table cellpadding="0" cellspacing="0" border="0" width="100%">
                  <tr>
                    <td style="text-align: center;">
                      <table cellpadding="0" cellspacing="0" border="0" style="display: inline-block;">
                        <tr>
                          <!-- View Event Button -->
                          <td style="padding-right: 8px;">
                            <a href="${clickUrl}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px;">
                              View Event →
                            </a>
                          </td>
                          <!-- Like Button -->
                          <td style="padding-right: 8px;">
                            <a href="${likeUrl}" style="display: inline-block; background: #48bb78; color: white; padding: 12px 16px; text-decoration: none; border-radius: 6px; font-size: 14px;">
                              👍 Interested
                            </a>
                          </td>
                          <!-- Dislike Button -->
                          <td>
                            <a href="${dislikeUrl}" style="display: inline-block; background: #f56565; color: white; padding: 12px 16px; text-decoration: none; border-radius: 6px; font-size: 14px;">
                              👎 Not for me
                            </a>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    `;
  }).join('');

  // Main HTML email
  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <title>${generateSubject(userName)}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f7fafc;">
  <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background: #f7fafc; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table cellpadding="0" cellspacing="0" border="0" width="600" style="max-width: 600px;">
          
          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 32px; text-align: center; border-radius: 12px 12px 0 0;">
              <h1 style="margin: 0; color: white; font-size: 28px; font-weight: bold;">
                Connect3
              </h1>
              <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 16px;">
                Your Personalized Event Newsletter
              </p>
            </td>
          </tr>

          <!-- Greeting -->
          <tr>
            <td style="background: white; padding: 24px 32px 16px 32px;">
              <h2 style="margin: 0 0 8px 0; color: #2d3748; font-size: 24px;">
                Hi ${userName}! 👋
              </h2>
              <p style="margin: 0; color: #4a5568; font-size: 16px; line-height: 1.6;">
                We've analyzed your interests and handpicked <strong>3 events from 3 different categories</strong> just for you. Each event is ranked based on how well it matches your preferences!
              </p>
            </td>
          </tr>

          <!-- Event Cards -->
          <tr>
            <td style="background: white; padding: 0 32px 32px 32px;">
              <table cellpadding="0" cellspacing="0" border="0" width="100%">
                ${eventCards}
              </table>
            </td>
          </tr>

          <!-- How It Works Section -->
          <tr>
            <td style="background: #edf2f7; padding: 24px 32px; border-radius: 0 0 12px 12px;">
              <h3 style="margin: 0 0 16px 0; color: #2d3748; font-size: 18px;">
                📊 How This Works
              </h3>
              <ul style="margin: 0; padding-left: 20px; color: #4a5568; font-size: 14px; line-height: 1.8;">
                <li><strong>Ranked Categories:</strong> We use Naive Bayes classification to rank event categories based on your click history and feedback.</li>
                <li><strong>Diverse Selection:</strong> We pick the top event from your 3 highest-ranked categories to ensure variety.</li>
                <li><strong>Learning System:</strong> Click "Interested" or "Not for me" to help us learn your preferences better!</li>
                <li><strong>Category Clusters:</strong> Once you consistently choose events from the same category, we'll group you with similar users for even better recommendations.</li>
              </ul>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px 0; text-align: center;">
              <p style="margin: 0 0 8px 0; color: #718096; font-size: 13px;">
                Not enjoying these recommendations?
              </p>
              <p style="margin: 0; color: #718096; font-size: 13px;">
                <a href="#" style="color: #667eea; text-decoration: none;">Update preferences</a> | 
                <a href="#" style="color: #667eea; text-decoration: none;">Unsubscribe</a>
              </p>
              <p style="margin: 16px 0 0 0; color: #a0aec0; font-size: 12px;">
                © 2025 Connect3 by DSCubed @ University of Melbourne
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
  `;
}

/**
 * Generate plain text email (fallback)
 */
export function generateCategoryEmailText(data: EmailData): string {
  const { userName, recommendations } = data;
  
  const eventTexts = recommendations.map((rec, index) => {
    const rankLabels = ['🥇 TOP PICK', '🥈 SECOND CHOICE', '🥉 THIRD CHOICE'];
    const rankLabel = rankLabels[rec.rank - 1] || `#${rec.rank}`;

    return `
${rankLabel} - ${rec.category.toUpperCase()}
${rec.event.title}
${rec.event.club_name ? `📍 ${rec.event.club_name}` : ''}

${rec.reason}

${rec.event.description}

📅 ${formatDate(rec.event.event_date)}
📍 ${rec.event.location}
${rec.event.url ? `🔗 ${rec.event.url}` : ''}

---
`;
  }).join('\n');

  return `
Hi ${userName}! 👋

We've analyzed your interests and handpicked 3 events from 3 different categories just for you!

${eventTexts}

HOW THIS WORKS:
- We use Naive Bayes classification to rank event categories based on your history
- We pick the top event from your 3 highest-ranked categories
- Click "Interested" or "Not for me" on events to help us learn your preferences
- Once you consistently choose events from the same category, we'll group you for better recommendations

Not enjoying these? Update your preferences or unsubscribe.

© 2025 Connect3 by DSCubed @ University of Melbourne
  `;
}
