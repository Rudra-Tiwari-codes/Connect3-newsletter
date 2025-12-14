import 'dotenv/config';
import { supabase } from '@/lib/supabase';
import { EventScoringService } from '@/lib/scoring';
import { EmailDeliveryService } from '@/lib/email-delivery';

async function sendNewsletters() {
  console.log('Starting newsletter generation and delivery...');

  try {
    // Fetch all users
    const { data: users, error: usersError } = await supabase
      .from('users')
      .select('*');

    if (usersError || !users) {
      throw new Error(`Failed to fetch users: ${usersError?.message}`);
    }

    console.log(`Found ${users.length} users`);

    // Initialize services
    const scoringService = new EventScoringService();
    const emailService = new EmailDeliveryService();

    // Rank events for each user
    const rankedEventsByUser = new Map();

    for (const user of users) {
      try {
        const rankedEvents = await scoringService.rankEventsForUser(user.id, 10);
        if (rankedEvents.length > 0) {
          rankedEventsByUser.set(user.id, rankedEvents);
        }
      } catch (error: any) {
        console.error(`Failed to rank events for user ${user.id}:`, error.message);
      }
    }

    console.log(`Ranked events for ${rankedEventsByUser.size} users`);

    // Send emails
    await emailService.sendNewsletters(rankedEventsByUser);

    console.log('✓ Newsletter delivery complete!');
  } catch (error: any) {
    console.error('Error during newsletter sending:', error.message);
    process.exit(1);
  }
}

sendNewsletters();
