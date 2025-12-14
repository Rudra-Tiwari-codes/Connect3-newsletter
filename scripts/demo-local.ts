/**
 * Local Demo - Two-Tower Recommendation System
 * 
 * This script demonstrates the complete recommendation pipeline locally
 * without requiring database access. It shows:
 * 1. How events are embedded
 * 2. How synthetic users are created
 * 3. How recommendations are generated
 * 4. What the final email output looks like
 * 
 * Run: npm run demo
 */

import 'dotenv/config';
import * as fs from 'fs';
import * as path from 'path';
import { EmbeddingService, CONNECT3_CATEGORIES } from '../src/lib/embeddings';
import { VectorIndex } from '../src/lib/vector-index';

// ============================================================
// CONFIGURATION
// ============================================================
const NUM_EVENTS_TO_PROCESS = 10;  // Process a subset for demo
const NUM_SYNTHETIC_USERS = 5;     // Create a few test users

interface InstagramPost {
  id: string;
  caption: string;
  media_type: string;
  media_url: string;
  permalink: string;
  timestamp: string;
}

interface SyntheticUser {
  id: string;
  name: string;
  email: string;
  preferences: string[];
  embedding?: number[];
}

interface EventData {
  id: string;
  title: string;
  description: string;
  category: string;
  embedding: number[];
  timestamp: string;
  permalink: string;
}

// ============================================================
// HELPER FUNCTIONS
// ============================================================

function extractTitle(caption: string): string {
  const lines = caption.split('\n').filter(l => l.trim());
  const titleLine = lines[0] || 'Untitled Event';
  return titleLine.replace(/[^\w\s.,!?-]/g, '').trim().slice(0, 100);
}

function cleanCaption(caption: string): string {
  return caption
    .replace(/[\u{1F600}-\u{1F6FF}]/gu, '')  // Emojis
    .replace(/#\w+/g, '')                      // Hashtags
    .replace(/@\w+/g, '')                      // Mentions
    .replace(/https?:\/\/\S+/g, '')            // URLs
    .replace(/\s+/g, ' ')
    .trim();
}

// ============================================================
// MAIN DEMO
// ============================================================

async function runDemo() {
  console.log('\n' + '='.repeat(70));
  console.log('   CONNECT3 TWO-TOWER RECOMMENDATION SYSTEM - LOCAL DEMO');
  console.log('='.repeat(70) + '\n');

  // Step 1: Load posts
  console.log('STEP 1: Loading Instagram posts...\n');
  const postsPath = path.join(__dirname, '..', 'all_posts.json');
  const allPosts: InstagramPost[] = JSON.parse(fs.readFileSync(postsPath, 'utf-8'));
  const posts = allPosts.slice(0, NUM_EVENTS_TO_PROCESS);
  console.log(`   Loaded ${allPosts.length} total posts, processing ${posts.length} for demo\n`);

  // Step 2: Initialize embedding service
  console.log('STEP 2: Initializing embedding service (OpenAI text-embedding-3-small)...\n');
  const embeddingService = new EmbeddingService();
  
  // Step 3: Generate embeddings for events
  console.log('STEP 3: Generating event embeddings...\n');
  const events: EventData[] = [];
  const vectorIndex = new VectorIndex(1536);

  for (let i = 0; i < posts.length; i++) {
    const post = posts[i];
    const title = extractTitle(post.caption);
    const cleanedCaption = cleanCaption(post.caption);
    
    console.log(`   [${i + 1}/${posts.length}] Processing: "${title.slice(0, 50)}..."`);
    
    try {
      // Generate embedding
      const embedding = await embeddingService.generateEmbedding(cleanedCaption);
      
      // Classify category
      const category = await embeddingService.classifyEventCategory(cleanedCaption);
      
      const eventData: EventData = {
        id: post.id,
        title,
        description: cleanedCaption.slice(0, 200),
        category,
        embedding,
        timestamp: post.timestamp,
        permalink: post.permalink
      };
      
      events.push(eventData);
      vectorIndex.add(post.id, embedding, { category, title });
      
      console.log(`            Category: ${category}`);
    } catch (error: any) {
      console.log(`            Error: ${error.message}`);
    }
  }

  console.log(`\n   Event embedding complete! ${events.length} events indexed.\n`);

  // Show category distribution
  const categoryCount: Record<string, number> = {};
  events.forEach(e => {
    categoryCount[e.category] = (categoryCount[e.category] || 0) + 1;
  });
  console.log('   Category distribution:');
  Object.entries(categoryCount)
    .sort((a, b) => b[1] - a[1])
    .forEach(([cat, count]) => {
      console.log(`     - ${cat}: ${count}`);
    });
  console.log();

  // Step 4: Create synthetic users
  console.log('STEP 4: Creating synthetic users...\n');
  
  const userProfiles = [
    { name: 'Tech Enthusiast', preferences: ['tech_workshop', 'hackathon', 'industry_talk'] },
    { name: 'Career Focused', preferences: ['career_networking', 'industry_talk', 'recruitment'] },
    { name: 'Social Butterfly', preferences: ['social_event', 'sports_recreation', 'community_service'] },
    { name: 'Academic Star', preferences: ['academic_revision', 'tech_workshop', 'career_networking'] },
    { name: 'Startup Dreamer', preferences: ['entrepreneurship', 'hackathon', 'industry_talk'] }
  ];

  const users: SyntheticUser[] = [];

  for (let i = 0; i < NUM_SYNTHETIC_USERS; i++) {
    const profile = userProfiles[i % userProfiles.length];
    const user: SyntheticUser = {
      id: `user_${i + 1}`,
      name: `${profile.name} ${i + 1}`,
      email: `test${i + 1}@unimelb.edu.au`,
      preferences: profile.preferences
    };

    // Create user embedding from preferences
    const preferenceText = `I am interested in ${profile.preferences.join(', ')} events at university.`;
    user.embedding = await embeddingService.generateEmbedding(preferenceText);
    
    users.push(user);
    console.log(`   Created: ${user.name} (${user.preferences.join(', ')})`);
  }
  console.log();

  // Step 5: Generate recommendations
  console.log('STEP 5: Generating recommendations for each user...\n');
  console.log('-'.repeat(70));

  for (const user of users) {
    console.log(`\n USER: ${user.name}`);
    console.log(`   Interests: ${user.preferences.join(', ')}`);
    console.log('   Top 5 Recommended Events:\n');

    if (!user.embedding) continue;

    // Search for similar events
    const results = vectorIndex.search(user.embedding, 5);

    results.forEach((result, idx) => {
      const event = events.find(e => e.id === result.id);
      if (!event) return;

      const matchScore = (result.score * 100).toFixed(1);
      const categoryMatch = user.preferences.includes(event.category) ? '[MATCH]' : '';
      
      console.log(`   ${idx + 1}. ${event.title.slice(0, 50)}`);
      console.log(`      Category: ${event.category} ${categoryMatch}`);
      console.log(`      Similarity: ${matchScore}%`);
      console.log(`      Date: ${new Date(event.timestamp).toLocaleDateString()}`);
      console.log();
    });

    console.log('-'.repeat(70));
  }

  // Step 6: Show sample email output
  console.log('\n' + '='.repeat(70));
  console.log('   SAMPLE EMAIL OUTPUT');
  console.log('='.repeat(70) + '\n');

  const sampleUser = users[0];
  const sampleRecs = vectorIndex.search(sampleUser.embedding!, 3);

  console.log(`To: ${sampleUser.email}`);
  console.log(`Subject: Your Personalized Event Recommendations - Connect3\n`);
  console.log('-----------------------------------------------------------');
  console.log(`Hi ${sampleUser.name.split(' ')[0]},\n`);
  console.log(`Based on your interests in ${sampleUser.preferences.slice(0, 2).join(' and ')},`);
  console.log('we think you\'ll love these upcoming events:\n');

  sampleRecs.forEach((rec, idx) => {
    const event = events.find(e => e.id === rec.id);
    if (!event) return;
    
    const matchPercent = (rec.score * 100).toFixed(0);
    console.log(`${idx + 1}. ${event.title}`);
    console.log(`   [${matchPercent}% match] - ${event.category.replace('_', ' ')}`);
    console.log(`   ${event.description.slice(0, 100)}...`);
    console.log(`   Link: ${event.permalink}\n`);
  });

  console.log('-----------------------------------------------------------');
  console.log('Cheers,');
  console.log('The Connect3 Team @ DSCubed');
  console.log('-----------------------------------------------------------\n');

  // Summary
  console.log('='.repeat(70));
  console.log('   DEMO COMPLETE - SUMMARY');
  console.log('='.repeat(70));
  console.log(`
   How the Two-Tower System Works:
   
   1. EVENT TOWER
      - Each Instagram post is converted to a 1536-dimensional vector
      - OpenAI's text-embedding-3-small model captures semantic meaning
      - GPT-4o-mini classifies events into 10 categories
   
   2. USER TOWER  
      - Users get embeddings based on their preferences
      - For active users: weighted average of liked event embeddings
      - For new users: embedding from declared interests
   
   3. MATCHING
      - Cosine similarity finds closest events to user embedding
      - Business rules boost recency, penalize duplicate categories
      - Top N events selected for email newsletter
   
   4. SCORING FORMULA
      Final Score = (Similarity * 0.7) + (Recency * 0.3) - Diversity Penalty
   
   Events Processed: ${events.length}
   Users Created: ${users.length}
   Embedding Dimensions: 1536
   Model: OpenAI text-embedding-3-small
`);
}

// Run the demo
runDemo().catch(console.error);
