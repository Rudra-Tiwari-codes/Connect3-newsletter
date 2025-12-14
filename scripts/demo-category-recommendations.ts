/**
 * Demo Category-Based Recommendations
 * Tests the new Naive Bayes category-based recommendation system
 */

import 'dotenv/config';
import { categoryRecommender } from '../src/lib/category-recommender';
import { categoryClassifier } from '../src/lib/category-classifier';
import { generateCategoryEmail, generateCategoryEmailText } from '../src/lib/category-email-template';
import { supabase } from '../src/lib/supabase';
import * as fs from 'fs';

async function demoCategoryBasedRecommendations() {
  console.log('🎯 Category-Based Recommendation System Demo\n');
  console.log('='.repeat(60));

  try {
    // Get a sample user
    const { data: users, error: usersError } = await supabase
      .from('users')
      .select('*')
      .limit(5);

    if (usersError || !users || users.length === 0) {
      console.error('❌ No users found. Please run generate-students.ts first.');
      return;
    }

    console.log(`\n📋 Found ${users.length} users. Testing recommendations...\n`);

    const results: string[] = [];
    const htmlEmails: { user: string; html: string }[] = [];

    for (const user of users) {
      console.log('─'.repeat(60));
      console.log(`\n👤 User: ${user.name} (${user.email})`);
      console.log(`   Faculty: ${user.faculty}, Major: ${user.major}`);

      // Get user's category profile
      console.log('\n📊 Analyzing category preferences...');
      const profile = await categoryRecommender.getUserProfile(user.id);

      console.log(`\n🎯 Top 5 Categories:`);
      profile.topCategories.forEach((cat, i) => {
        console.log(`   ${i + 1}. ${cat}`);
      });

      console.log(`\n🎨 Top 3 Clusters:`);
      profile.topClusters.forEach((cluster, i) => {
        console.log(`   ${i + 1}. ${cluster}`);
      });

      console.log(`\n💌 Recommended Events (3 from 3 different categories):`);
      console.log('');

      if (profile.recommendations.length === 0) {
        console.log('   ⚠️ No recommendations available.');
        continue;
      }

      // Display recommendations
      profile.recommendations.forEach((rec, i) => {
        console.log(`   ${rec.rank}. [${rec.category}] ${rec.event.title}`);
        console.log(`      📍 ${rec.event.club_name || 'N/A'}`);
        console.log(`      💡 ${rec.reason}`);
        console.log(`      📅 ${new Date(rec.event.event_date).toLocaleDateString()}`);
        console.log(`      📍 ${rec.event.location}`);
        console.log('');
      });

      // Generate email
      console.log('📧 Generating email...');
      const emailData = {
        userName: user.name,
        userEmail: user.email,
        recommendations: profile.recommendations,
        userId: user.id
      };

      const htmlEmail = generateCategoryEmail(emailData);
      const textEmail = generateCategoryEmailText(emailData);

      htmlEmails.push({
        user: user.name,
        html: htmlEmail
      });

      // Save to results
      results.push(`
========================================
USER: ${user.name} (${user.email})
Faculty: ${user.faculty}, Major: ${user.major}
========================================

TOP CATEGORIES:
${profile.topCategories.map((cat, i) => `${i + 1}. ${cat}`).join('\n')}

TOP CLUSTERS:
${profile.topClusters.map((cluster, i) => `${i + 1}. ${cluster}`).join('\n')}

RECOMMENDATIONS:
${profile.recommendations.map(rec => `
${rec.rank}. [${rec.category}] ${rec.event.title}
   Club: ${rec.event.club_name || 'N/A'}
   Reason: ${rec.reason}
   Date: ${new Date(rec.event.event_date).toLocaleDateString()}
   Location: ${rec.event.location}
`).join('\n')}

PLAIN TEXT EMAIL:
${textEmail}
`);

      console.log('✅ Email generated successfully!');
      console.log('');
    }

    // Save results to file
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const resultsFile = `category-recommendations-demo-${timestamp}.txt`;
    fs.writeFileSync(resultsFile, results.join('\n\n'));
    console.log(`\n✅ Results saved to: ${resultsFile}`);

    // Save HTML emails
    const htmlFile = `category-emails-demo-${timestamp}.html`;
    const htmlContent = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Category-Based Email Samples</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f0f0f0; padding: 20px; }
    .email-container { margin-bottom: 40px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .email-header { background: #667eea; color: white; padding: 12px; border-radius: 4px; margin-bottom: 20px; }
    iframe { width: 100%; height: 800px; border: 1px solid #ddd; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>Category-Based Email Samples</h1>
  <p>Generated: ${new Date().toLocaleString()}</p>
  ${htmlEmails.map((item, i) => `
    <div class="email-container">
      <div class="email-header">
        <h2>Email ${i + 1}: ${item.user}</h2>
      </div>
      <iframe srcdoc="${item.html.replace(/"/g, '&quot;')}"></iframe>
    </div>
  `).join('\n')}
</body>
</html>
    `;
    fs.writeFileSync(htmlFile, htmlContent);
    console.log(`✅ HTML emails saved to: ${htmlFile}`);

    // Summary statistics
    console.log('\n📊 Summary Statistics:');
    console.log('─'.repeat(60));
    console.log(`Total users analyzed: ${users.length}`);
    console.log(`Total recommendations generated: ${users.length * 3}`);
    console.log(`Average categories per user: 3 (by design)`);

    console.log('\n✅ Category-based recommendation demo complete!');
    console.log('\n💡 Next Steps:');
    console.log('   1. Open the HTML file in a browser to preview emails');
    console.log('   2. Users can click "Interested" or "Not for me" to train the system');
    console.log('   3. After enough feedback, users will be grouped into category clusters');
    console.log('   4. Future emails will prioritize events from their preferred cluster');

  } catch (error) {
    console.error('❌ Error running demo:', error);
    throw error;
  }
}

// Run if called directly
if (require.main === module) {
  demoCategoryBasedRecommendations()
    .then(() => process.exit(0))
    .catch((error) => {
      console.error(error);
      process.exit(1);
    });
}

export { demoCategoryBasedRecommendations };
