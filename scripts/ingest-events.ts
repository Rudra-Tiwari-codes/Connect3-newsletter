import { supabase } from '@/lib/supabase';
import { EventClassifier } from '@/lib/ai-classifier';

async function ingestEvents() {
  console.log('Starting event ingestion and classification...');

  try {
    // Fetch events without categories
    const { data: events, error } = await supabase
      .from('events')
      .select('*')
      .is('category', null);

    if (error) {
      throw new Error(`Failed to fetch events: ${error.message}`);
    }

    if (!events || events.length === 0) {
      console.log('No unclassified events found.');
      return;
    }

    console.log(`Found ${events.length} unclassified events`);

    // Initialize classifier
    const classifier = new EventClassifier();

    // Classify events in batch
    const classifications = await classifier.classifyBatch(events);

    // Update events with classifications
    let successCount = 0;
    for (const [eventId, category] of classifications.entries()) {
      const { error: updateError } = await supabase
        .from('events')
        .update({ category })
        .eq('id', eventId);

      if (updateError) {
        console.error(`Failed to update event ${eventId}:`, updateError);
      } else {
        successCount++;
      }
    }

    console.log(`✓ Successfully classified ${successCount} events`);
  } catch (error: any) {
    console.error('Error during ingestion:', error.message);
    process.exit(1);
  }
}

ingestEvents();
