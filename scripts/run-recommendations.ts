/**
 * Run Recommendations Script
 * 
 * Generates personalized recommendations for all users and optionally sends emails.
 * 
 * Usage:
 *   npm run recommend              # Generate recommendations only
 *   npm run recommend -- --send    # Generate and send emails
 */

import { supabase } from '../src/lib/supabase';
import { TwoTowerRecommender, RecommendedEvent } from '../src/lib/recommender';
import { EmailDeliveryService } from '../src/lib/email-delivery';

interface UserRecommendations {
  userId: string;
  email: string;
  name: string;
  recommendations: RecommendedEvent[];
}

async function runRecommendations() {
  const sendEmails = process.argv.includes('--send');
  
  console.log(' Starting Two-Tower Recommendation Pipeline');
  console.log(`   Mode: ${sendEmails ? 'Generate + Send Emails' : 'Generate Only (dry run)'}`);
  console.log('');

  // Initialize recommender
  const recommender = new TwoTowerRecommender({
    topK: 10,
    recencyWeight: 0.3,
    similarityWeight: 0.7,
    maxDaysOld: 90,
  });

  // Load event index
  console.log(' Loading event embeddings...');
  await recommender.loadEventIndex();

  // Fetch all users
  console.log(' Fetching users...');
  const { data: users, error: usersError } = await supabase
    .from('users')
    .select('id, email, name');

  if (usersError || !users) {
    console.error(' Failed to fetch users:', usersError?.message);
    process.exit(1);
  }

  console.log(`   Found ${users.length} users\n`);

  // Generate recommendations for each user
  const allRecommendations: UserRecommendations[] = [];
  let successCount = 0;
  let errorCount = 0;

  for (const user of users) {
    try {
      process.stdout.write(`Processing ${user.name || user.email}... `);
      
      const recommendations = await recommender.getRecommendations(user.id);
      
      allRecommendations.push({
        userId: user.id,
        email: user.email,
        name: user.name || 'User',
        recommendations,
      });

      // Log recommendations to database
      for (let i = 0; i < recommendations.length; i++) {
        const rec = recommendations[i];
        await supabase.from('recommendation_logs').insert({
          user_id: user.id,
          event_id: rec.event_id,
          similarity_score: rec.similarity_score,
          recency_score: rec.recency_score,
          final_score: rec.final_score,
          position: i + 1,
          model_version: 'v2-two-tower',
        });
      }

      successCount++;
      console.log(`✓ ${recommendations.length} recommendations`);

    } catch (error: any) {
      errorCount++;
      console.log(`✗ Error: ${error.message}`);
    }
  }

  // Print summary
  console.log('\n' + '='.repeat(60));
  console.log(' Recommendation Summary');
  console.log('='.repeat(60));
  console.log(`   Users processed: ${successCount}/${users.length}`);
  console.log(`   Errors: ${errorCount}`);
  
  // Statistics
  const allRecs = allRecommendations.flatMap(u => u.recommendations);
  if (allRecs.length > 0) {
    const avgSimilarity = allRecs.reduce((s, r) => s + r.similarity_score, 0) / allRecs.length;
    const avgFinalScore = allRecs.reduce((s, r) => s + r.final_score, 0) / allRecs.length;
    
    console.log(`   Total recommendations: ${allRecs.length}`);
    console.log(`   Avg similarity score: ${avgSimilarity.toFixed(3)}`);
    console.log(`   Avg final score: ${avgFinalScore.toFixed(3)}`);
    
    // Category distribution
    const categoryDist: Record<string, number> = {};
    for (const rec of allRecs) {
      const cat = rec.category || 'unknown';
      categoryDist[cat] = (categoryDist[cat] || 0) + 1;
    }
    
    console.log('\n Category Distribution in Recommendations:');
    for (const [cat, count] of Object.entries(categoryDist).sort((a, b) => b[1] - a[1])) {
      const pct = (count / allRecs.length * 100).toFixed(1);
      console.log(`   ${cat.padEnd(20)} ${count.toString().padStart(4)} (${pct}%)`);
    }
  }

  // Send emails if requested
  if (sendEmails) {
    console.log('\n Sending personalized emails...');
    
    const emailService = new EmailDeliveryService();
    
    // Convert to format expected by email service
    const emailMap = new Map();
    for (const userRecs of allRecommendations) {
      if (userRecs.recommendations.length > 0) {
        // Convert RecommendedEvent to RankedEvent format
        const rankedEvents = userRecs.recommendations.map(rec => ({
          id: rec.event_id,
          title: rec.title,
          description: rec.caption,
          event_date: rec.timestamp,
          location: null,
          category: rec.category,
          tags: null,
          source_url: rec.permalink,
          created_at: rec.timestamp,
          updated_at: rec.timestamp,
          score: rec.final_score * 100, // Scale to match old scoring
          cluster_match: rec.similarity_score,
          urgency_score: rec.recency_score * 30,
        }));
        
        emailMap.set(userRecs.userId, rankedEvents);
      }
    }

    await emailService.sendNewsletters(emailMap);
    console.log(' Email sending complete!');
  }

  // Print sample recommendations
  console.log('\n' + '='.repeat(60));
  console.log(' Sample Recommendations (first 3 users)');
  console.log('='.repeat(60));
  
  for (const userRecs of allRecommendations.slice(0, 3)) {
    console.log(`\n👤 ${userRecs.name} (${userRecs.email})`);
    
    for (let i = 0; i < Math.min(3, userRecs.recommendations.length); i++) {
      const rec = userRecs.recommendations[i];
      console.log(`   ${i + 1}. ${rec.title.substring(0, 50)}...`);
      console.log(`      Score: ${rec.final_score.toFixed(3)} | Category: ${rec.category || 'unknown'}`);
      console.log(`      Reason: ${rec.reason}`);
    }
  }

  console.log('\n Recommendation pipeline complete!');
}

runRecommendations().catch(console.error);
