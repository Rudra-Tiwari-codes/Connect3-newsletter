/**
 * Generate Sample Emails for All Synthetic Users
 * 
 * This script processes ALL events and generates personalized
 * email newsletters for each synthetic user, outputting to a markdown file.
 * 
 * Run: npm run generate-emails
 */

import 'dotenv/config';
import * as fs from 'fs';
import * as path from 'path';
import { EmbeddingService } from '../src/lib/embeddings';
import { VectorIndex } from '../src/lib/vector-index';

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
  faculty: string;
  degree: string;
  year: number;
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
// SYNTHETIC USER PROFILES
// ============================================================
const userProfiles: Omit<SyntheticUser, 'id' | 'embedding'>[] = [
  {
    name: 'Alex Chen',
    email: 'achen@student.unimelb.edu.au',
    faculty: 'Engineering',
    degree: 'Software Engineering',
    year: 2,
    preferences: ['tech_workshop', 'hackathon', 'industry_talk']
  },
  {
    name: 'Sarah Williams',
    email: 'swilliams@student.unimelb.edu.au',
    faculty: 'Business',
    degree: 'Commerce',
    year: 3,
    preferences: ['career_networking', 'industry_talk', 'recruitment']
  },
  {
    name: 'Jordan Lee',
    email: 'jlee@student.unimelb.edu.au',
    faculty: 'Science',
    degree: 'Data Science',
    year: 1,
    preferences: ['tech_workshop', 'academic_revision', 'hackathon']
  },
  {
    name: 'Emily Zhang',
    email: 'ezhang@student.unimelb.edu.au',
    faculty: 'Arts',
    degree: 'Media Studies',
    year: 2,
    preferences: ['social_event', 'community_service', 'recruitment']
  },
  {
    name: 'Michael Patel',
    email: 'mpatel@student.unimelb.edu.au',
    faculty: 'Engineering',
    degree: 'Mechanical Engineering',
    year: 4,
    preferences: ['career_networking', 'entrepreneurship', 'industry_talk']
  },
  {
    name: 'Jessica Brown',
    email: 'jbrown@student.unimelb.edu.au',
    faculty: 'Science',
    degree: 'Computer Science',
    year: 3,
    preferences: ['hackathon', 'tech_workshop', 'career_networking']
  },
  {
    name: 'David Kim',
    email: 'dkim@student.unimelb.edu.au',
    faculty: 'Business',
    degree: 'Finance',
    year: 2,
    preferences: ['entrepreneurship', 'industry_talk', 'career_networking']
  },
  {
    name: 'Olivia Martinez',
    email: 'omartinez@student.unimelb.edu.au',
    faculty: 'Science',
    degree: 'Statistics',
    year: 1,
    preferences: ['academic_revision', 'tech_workshop', 'social_event']
  },
  {
    name: 'Ryan Thompson',
    email: 'rthompson@student.unimelb.edu.au',
    faculty: 'Engineering',
    degree: 'Electrical Engineering',
    year: 3,
    preferences: ['tech_workshop', 'hackathon', 'recruitment']
  },
  {
    name: 'Sophia Nguyen',
    email: 'snguyen@student.unimelb.edu.au',
    faculty: 'Arts',
    degree: 'Psychology',
    year: 2,
    preferences: ['social_event', 'community_service', 'academic_revision']
  }
];

// ============================================================
// HELPER FUNCTIONS
// ============================================================

function extractTitle(caption: string): string {
  const lines = caption.split('\n').filter(l => l.trim());
  let titleLine = lines[0] || 'Untitled Event';
  // Clean up the title
  titleLine = titleLine
    .replace(/[\u{1F600}-\u{1F6FF}\u{1F300}-\u{1F5FF}\u{1F900}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '')
    .replace(/[^\w\s.,!?'-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return titleLine.slice(0, 80) || 'University Event';
}

function cleanCaption(caption: string): string {
  return caption
    .replace(/[\u{1F600}-\u{1F6FF}\u{1F300}-\u{1F5FF}\u{1F900}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '')
    .replace(/#\w+/g, '')
    .replace(/@\w+/g, '')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function formatDate(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleDateString('en-AU', { 
    weekday: 'long',
    day: 'numeric', 
    month: 'long', 
    year: 'numeric' 
  });
}

function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    'tech_workshop': 'Tech Workshop',
    'career_networking': 'Career & Networking',
    'hackathon': 'Hackathon',
    'social_event': 'Social Event',
    'academic_revision': 'Academic Support',
    'recruitment': 'Recruitment',
    'industry_talk': 'Industry Talk',
    'sports_recreation': 'Sports & Recreation',
    'entrepreneurship': 'Entrepreneurship',
    'community_service': 'Community Service'
  };
  return labels[category] || category;
}

function getMatchBadge(score: number): string {
  if (score >= 45) return 'Excellent Match';
  if (score >= 35) return 'Great Match';
  if (score >= 25) return 'Good Match';
  return 'You Might Like';
}

// ============================================================
// EMAIL GENERATION
// ============================================================

function generateEmailMarkdown(
  user: SyntheticUser,
  recommendations: Array<{ event: EventData; score: number; rank: number }>
): string {
  const firstName = user.name.split(' ')[0];
  const topPrefs = user.preferences.slice(0, 2).map(p => getCategoryLabel(p).toLowerCase()).join(' and ');
  
  let email = `### Email to: ${user.name}\n\n`;
  email += `**To:** ${user.email}  \n`;
  email += `**Subject:** ${firstName}, here are your personalized event picks this week!\n\n`;
  email += `---\n\n`;
  email += `Hi ${firstName},\n\n`;
  email += `Based on your interest in **${topPrefs}**, we've handpicked these events just for you:\n\n`;

  recommendations.forEach((rec, idx) => {
    const matchPercent = Math.round(rec.score * 100);
    const badge = getMatchBadge(matchPercent);
    const categoryLabel = getCategoryLabel(rec.event.category);
    const isPreferenceMatch = user.preferences.includes(rec.event.category);
    
    email += `---\n\n`;
    email += `#### ${idx + 1}. ${rec.event.title}\n\n`;
    email += `| | |\n`;
    email += `|---|---|\n`;
    email += `| **Match Score** | ${matchPercent}% - ${badge} ${isPreferenceMatch ? '(Matches your interests!)' : ''} |\n`;
    email += `| **Category** | ${categoryLabel} |\n`;
    email += `| **Date** | ${formatDate(rec.event.timestamp)} |\n\n`;
    email += `> ${rec.event.description.slice(0, 250)}${rec.event.description.length > 250 ? '...' : ''}\n\n`;
    email += `[View Event on Instagram](${rec.event.permalink})\n\n`;
  });

  email += `---\n\n`;
  email += `**Why these recommendations?**  \n`;
  email += `Our AI analyzes event descriptions and matches them to your stated interests `;
  email += `(${user.preferences.map(p => getCategoryLabel(p)).join(', ')}). `;
  email += `The match score reflects how well each event aligns with what you love.\n\n`;
  email += `Not interested in some of these? [Update your preferences](#) or [Unsubscribe](#)\n\n`;
  email += `Cheers,  \n`;
  email += `**The Connect3 Team**  \n`;
  email += `DSCubed @ University of Melbourne\n\n`;
  email += `---\n\n`;

  return email;
}

// ============================================================
// MAIN SCRIPT
// ============================================================

async function generateSampleEmails() {
  console.log('\n' + '='.repeat(70));
  console.log('   GENERATING SAMPLE EMAILS FOR ALL USERS');
  console.log('='.repeat(70) + '\n');

  // Step 1: Load ALL posts
  console.log('Step 1: Loading all Instagram posts...');
  const postsPath = path.join(__dirname, '..', 'all_posts.json');
  const posts: InstagramPost[] = JSON.parse(fs.readFileSync(postsPath, 'utf-8'));
  console.log(`   Loaded ${posts.length} posts\n`);

  // Step 2: Initialize embedding service
  console.log('Step 2: Initializing embedding service...');
  const embeddingService = new EmbeddingService();
  const vectorIndex = new VectorIndex(1536);

  // Step 3: Generate embeddings for ALL events
  console.log(`Step 3: Generating embeddings for ${posts.length} events...`);
  const events: EventData[] = [];
  
  for (let i = 0; i < posts.length; i++) {
    const post = posts[i];
    const title = extractTitle(post.caption);
    const cleanedCaption = cleanCaption(post.caption);
    
    process.stdout.write(`\r   Processing event ${i + 1}/${posts.length}: ${title.slice(0, 40)}...`);
    
    try {
      const embedding = await embeddingService.generateEmbedding(cleanedCaption);
      const category = await embeddingService.classifyEventCategory(cleanedCaption);
      
      const eventData: EventData = {
        id: post.id,
        title,
        description: cleanedCaption.slice(0, 400),
        category,
        embedding,
        timestamp: post.timestamp,
        permalink: post.permalink
      };
      
      events.push(eventData);
      vectorIndex.add(post.id, embedding, { category, title });
    } catch (error: any) {
      console.log(`\n   Warning: Could not process ${post.id}: ${error.message}`);
    }
  }
  
  console.log(`\n   Successfully embedded ${events.length} events\n`);

  // Show category distribution
  const categoryCount: Record<string, number> = {};
  events.forEach(e => {
    categoryCount[e.category] = (categoryCount[e.category] || 0) + 1;
  });
  console.log('   Category distribution:');
  Object.entries(categoryCount)
    .sort((a, b) => b[1] - a[1])
    .forEach(([cat, count]) => {
      console.log(`     - ${getCategoryLabel(cat)}: ${count}`);
    });
  console.log();

  // Step 4: Create user embeddings
  console.log(`Step 4: Creating ${userProfiles.length} synthetic users...`);
  const users: SyntheticUser[] = [];

  for (let i = 0; i < userProfiles.length; i++) {
    const profile = userProfiles[i];
    const preferenceText = `I am a university student interested in ${profile.preferences.map(p => getCategoryLabel(p).toLowerCase()).join(', ')} events. I study ${profile.degree} and want to learn, network, and grow professionally.`;
    
    const embedding = await embeddingService.generateEmbedding(preferenceText);
    
    users.push({
      ...profile,
      id: `user_${i + 1}`,
      embedding
    });
    
    console.log(`   Created: ${profile.name} (${profile.faculty} - ${profile.degree})`);
  }
  console.log();

  // Step 5: Generate recommendations and emails
  console.log('Step 5: Generating personalized recommendations...\n');
  
  let markdownContent = `# Connect3 Sample Email Newsletter\n\n`;
  markdownContent += `**Generated:** ${new Date().toLocaleString('en-AU')}\n\n`;
  markdownContent += `This document contains personalized email newsletters for ${users.length} synthetic users, `;
  markdownContent += `based on ${events.length} events from the DSCubed Instagram.\n\n`;
  markdownContent += `---\n\n`;
  markdownContent += `## Table of Contents\n\n`;
  
  users.forEach((user, idx) => {
    markdownContent += `${idx + 1}. [${user.name}](#email-to-${user.name.toLowerCase().replace(/\s+/g, '-')}) - ${user.faculty}, ${user.degree}\n`;
  });
  
  markdownContent += `\n---\n\n`;
  markdownContent += `## Event Summary\n\n`;
  markdownContent += `| Category | Count |\n`;
  markdownContent += `|----------|-------|\n`;
  Object.entries(categoryCount)
    .sort((a, b) => b[1] - a[1])
    .forEach(([cat, count]) => {
      markdownContent += `| ${getCategoryLabel(cat)} | ${count} |\n`;
    });
  markdownContent += `| **Total** | **${events.length}** |\n\n`;
  markdownContent += `---\n\n`;
  markdownContent += `## Sample Emails\n\n`;

  for (const user of users) {
    console.log(`   Generating email for ${user.name}...`);
    
    if (!user.embedding) continue;

    // Get top 5 recommendations
    const results = vectorIndex.search(user.embedding, 5);
    
    const recommendations = results.map((result, idx) => {
      const event = events.find(e => e.id === result.id)!;
      return {
        event,
        score: result.score,
        rank: idx + 1
      };
    }).filter(r => r.event);

    markdownContent += generateEmailMarkdown(user, recommendations);
    markdownContent += `<br>\n\n`;
  }

  // Add footer
  markdownContent += `---\n\n`;
  markdownContent += `## How This Works\n\n`;
  markdownContent += `### Two-Tower Architecture\n\n`;
  markdownContent += `1. **Event Tower**: Each event is converted to a 1536-dimensional embedding using OpenAI's text-embedding-3-small model\n`;
  markdownContent += `2. **User Tower**: User preferences are also converted to embeddings based on their stated interests\n`;
  markdownContent += `3. **Matching**: Cosine similarity finds the closest events to each user's embedding\n`;
  markdownContent += `4. **Ranking**: Events are scored and the top 5 are selected for each user\n\n`;
  markdownContent += `### Match Score Interpretation\n\n`;
  markdownContent += `| Score | Badge | Meaning |\n`;
  markdownContent += `|-------|-------|--------|\n`;
  markdownContent += `| 45%+ | Excellent Match | Highly relevant to your interests |\n`;
  markdownContent += `| 35-44% | Great Match | Strong alignment with preferences |\n`;
  markdownContent += `| 25-34% | Good Match | Relevant content you may enjoy |\n`;
  markdownContent += `| <25% | You Might Like | Broader recommendation |\n\n`;
  markdownContent += `---\n\n`;
  markdownContent += `*Generated by Connect3 Two-Tower Recommendation System*\n`;

  // Write to file
  const outputPath = path.join(__dirname, '..', 'SAMPLE-EMAILS.md');
  fs.writeFileSync(outputPath, markdownContent);
  
  console.log(`\n${'='.repeat(70)}`);
  console.log('   COMPLETE!');
  console.log('='.repeat(70));
  console.log(`\n   Output: SAMPLE-EMAILS.md`);
  console.log(`   Users: ${users.length}`);
  console.log(`   Events processed: ${events.length}`);
  console.log(`   Emails generated: ${users.length}\n`);
}

// Run
generateSampleEmails().catch(console.error);
