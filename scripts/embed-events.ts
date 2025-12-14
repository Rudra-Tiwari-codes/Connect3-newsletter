/**
 * Script to embed all events from all_posts.json
 * 
 * This reads the Instagram posts, generates embeddings using OpenAI,
 * classifies them into categories, and stores them in the database.
 * 
 * Run: npm run embed-events
 */

import 'dotenv/config';
import * as fs from 'fs';
import * as path from 'path';
import { supabase } from '../src/lib/supabase';
import { EmbeddingService, CONNECT3_CATEGORIES } from '../src/lib/embeddings';

interface InstagramPost {
  id: string;
  caption: string;
  media_type: string;
  media_url: string;
  permalink: string;
  timestamp: string;
}

async function embedEvents() {
  console.log(' Starting event embedding process...\n');

  // Read all_posts.json
  const postsPath = path.join(__dirname, '..', 'all_posts.json');

  if (!fs.existsSync(postsPath)) {
    console.error(' all_posts.json not found!');
    process.exit(1);
  }

  const posts: InstagramPost[] = JSON.parse(fs.readFileSync(postsPath, 'utf-8'));
  console.log(` Found ${posts.length} posts to process\n`);

  const embeddingService = new EmbeddingService();

  // Process in batches to avoid rate limits
  const batchSize = 5;
  let successCount = 0;
  let errorCount = 0;

  for (let i = 0; i < posts.length; i += batchSize) {
    const batch = posts.slice(i, i + batchSize);
    console.log(`Processing batch ${Math.floor(i / batchSize) + 1}/${Math.ceil(posts.length / batchSize)}...`);

    const results = await Promise.allSettled(
      batch.map(async (post) => {
        try {
          // Generate embedding
          const eventEmbedding = await embeddingService.embedEvent({
            id: post.id,
            caption: post.caption,
            timestamp: post.timestamp,
          });

          // Skip events table upsert - Instagram IDs are not UUIDs
          // Just store embeddings directly in event_embeddings table

          // Insert embedding
          const { error: embError } = await supabase
            .from('event_embeddings')
            .upsert({
              event_id: post.id,
              embedding: eventEmbedding.embedding,
              category: eventEmbedding.category,
              created_at: post.timestamp,
            }, { onConflict: 'event_id' });

          if (embError) {
            throw new Error(`Failed to store embedding: ${embError.message}`);
          }

          return { id: post.id, category: eventEmbedding.category };
        } catch (error: any) {
          throw new Error(`Failed to embed event ${post.id}: ${error.message}`);
        }
      })
    );

    // Process results
    for (const result of results) {
      if (result.status === 'fulfilled') {
        successCount++;
        console.log(`  ✓ Embedded: ${result.value.id} → ${result.value.category || 'uncategorized'}`);
      } else {
        errorCount++;
        console.error(`  ✗ Error: ${result.reason}`);
      }
    }

    // Rate limiting - wait between batches
    if (i + batchSize < posts.length) {
      await sleep(1000);
    }
  }

  console.log('\n' + '='.repeat(50));
  console.log(` Embedding complete!`);
  console.log(`   Success: ${successCount}`);
  console.log(`   Errors: ${errorCount}`);
  console.log('='.repeat(50));

  // Print category distribution
  await printCategoryDistribution();
}

/**
 * Extract title from caption (first meaningful line)
 */
function extractTitle(caption: string): string {
  if (!caption) return 'Event';

  // Get first non-empty line
  const lines = caption.split('\n').filter(l => l.trim().length > 0);
  if (lines.length === 0) return 'Event';

  let title = lines[0];

  // Remove leading emojis
  title = title.replace(/^[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\s]+/gu, '');

  // Truncate
  if (title.length > 200) {
    title = title.substring(0, 200) + '...';
  }

  return title || 'Event';
}

/**
 * Extract location from caption
 */
function extractLocation(caption: string): string | null {
  if (!caption) return null;

  // Look for location patterns
  const locationPatterns = [
    / \s*([^\n]+)/i,
    /Location:\s*([^\n]+)/i,
    /Where:\s*([^\n]+)/i,
    /at\s+([\w\s,]+(?:Building|Room|Theatre|Hall|Level|Melbourne|Campus)[\w\s,]*)/i,
  ];

  for (const pattern of locationPatterns) {
    const match = caption.match(pattern);
    if (match) {
      return match[1].trim();
    }
  }

  return null;
}

/**
 * Print category distribution
 */
async function printCategoryDistribution() {
  const { data: embeddings } = await supabase
    .from('event_embeddings')
    .select('category');

  if (!embeddings) return;

  const distribution: Record<string, number> = {};

  for (const emb of embeddings) {
    const cat = emb.category || 'uncategorized';
    distribution[cat] = (distribution[cat] || 0) + 1;
  }

  console.log('\n Category Distribution:');
  for (const [category, count] of Object.entries(distribution).sort((a, b) => b[1] - a[1])) {
    const bar = '█'.repeat(Math.ceil(count / 2));
    console.log(`   ${category.padEnd(20)} ${count.toString().padStart(3)} ${bar}`);
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Run
embedEvents().catch(console.error);
