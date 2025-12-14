import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';
import { UserClusteringService } from '@/lib/clustering';
import { categoryRecommender } from '@/lib/category-recommender';

/**
 * Sanitize input to prevent injection attacks
 */
function sanitizeInput(input: string | null): string | null {
  if (!input) return null;
  // Remove any potentially dangerous characters and limit length
  return input
    .trim()
    .replace(/[<>'"&]/g, '')
    .substring(0, 255);
}

/**
 * Validate UUID format
 */
function isValidUUID(uuid: string | null): boolean {
  if (!uuid) return false;
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(uuid);
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const userId = sanitizeInput(searchParams.get('uid'));
  const eventId = sanitizeInput(searchParams.get('eid'));
  const action = sanitizeInput(searchParams.get('action'));

  // Validate parameters
  if (!userId || !eventId || !action) {
    return NextResponse.json(
      { error: 'Missing required parameters: uid, eid, action' },
      { status: 400 }
    );
  }

  // Validate UUIDs
  if (!isValidUUID(userId)) {
    return NextResponse.json(
      { error: 'Invalid user ID format' },
      { status: 400 }
    );
  }

  if (!isValidUUID(eventId)) {
    return NextResponse.json(
      { error: 'Invalid event ID format' },
      { status: 400 }
    );
  }

  // Validate action
  if (!['like', 'dislike', 'click'].includes(action)) {
    return NextResponse.json(
      { error: 'Invalid action. Must be: like, dislike, or click' },
      { status: 400 }
    );
  }

  try {
    // Validate that userId exists
    const { data: user, error: userError } = await supabase
      .from('users')
      .select('id')
      .eq('id', userId)
      .single();

    if (userError || !user) {
      return NextResponse.json(
        { error: 'Invalid user ID' },
        { status: 404 }
      );
    }

    // Validate that eventId exists
    const { data: event, error: eventError } = await supabase
      .from('events')
      .select('id')
      .eq('id', eventId)
      .single();

    if (eventError || !event) {
      return NextResponse.json(
        { error: 'Invalid event ID' },
        { status: 404 }
      );
    }

    // Log feedback
    const { error: logError } = await supabase.from('feedback_logs').insert({
      user_id: userId,
      event_id: eventId,
      action: action as 'like' | 'dislike' | 'click',
    });

    if (logError) {
      console.error('Error logging feedback:', logError);
      return NextResponse.json({ error: 'Failed to log feedback' }, { status: 500 });
    }

    // Get event category to update preferences (we already validated event exists above)
    const { data: eventWithCategory, error: categoryError } = await supabase
      .from('events')
      .select('category')
      .eq('id', eventId)
      .single();

    if (!categoryError && eventWithCategory && eventWithCategory.category) {
      try {
        // Update category-based recommendations (Naive Bayes classifier)
        if (action === 'like') {
          await categoryRecommender.recordFeedback(userId, eventId, 'interested');
        } else if (action === 'dislike') {
          await categoryRecommender.recordFeedback(userId, eventId, 'not_interested');
        } else if (action === 'click') {
          await categoryRecommender.recordClick(userId, eventId);
        }

        // Still update old clustering system for backward compatibility
        if (action === 'like' || action === 'dislike') {
          const clusteringService = new UserClusteringService();
          await clusteringService.updateUserPreferenceFromFeedback(
            userId,
            eventWithCategory.category,
            action as 'like' | 'dislike'
          );
        }
      } catch (prefError: any) {
        console.error('Error updating user preferences:', prefError);
        // Continue - preference update failure shouldn't block feedback logging
      }
    }

    // Return HTML thank you page
    const actionText = action === 'like' ? 'liked' : action === 'dislike' ? 'not interested in' : 'clicked';
    const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Thank You!</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      margin: 0;
      padding: 20px;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
    }
    .container {
      background: white;
      border-radius: 12px;
      padding: 40px;
      max-width: 500px;
      text-align: center;
      box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    }
    h1 {
      color: #667eea;
      margin-top: 0;
    }
    p {
      color: #666;
      line-height: 1.6;
    }
    .icon {
      font-size: 64px;
      margin-bottom: 20px;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="icon">${action === 'like' ? '✅' : action === 'dislike' ? '❌' : '👍'}</div>
    <h1>Thank You!</h1>
    <p>We've recorded that you ${actionText} this event.</p>
    <p>Your preferences have been updated to provide better recommendations in the future.</p>
  </div>
</body>
</html>
    `;

    return new NextResponse(html, {
      status: 200,
      headers: { 'Content-Type': 'text/html' },
    });
  } catch (error: any) {
    console.error('Error processing feedback:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error.message },
      { status: 500 }
    );
  }
}
