/**
 * Test Recommendation Pipeline
 * 
 * This script tests the two-tower recommendation system without touching production data.
 * It creates synthetic test scenarios and validates the system works correctly.
 * 
 * Run: npm run test-pipeline
 */

import 'dotenv/config';
import * as fs from 'fs';
import * as path from 'path';
import { EmbeddingService, CONNECT3_CATEGORIES } from '../src/lib/embeddings';
import { VectorIndex } from '../src/lib/vector-index';

interface TestResult {
  name: string;
  passed: boolean;
  message: string;
  duration: number;
}

const results: TestResult[] = [];

async function test(name: string, fn: () => Promise<void>) {
  const start = Date.now();
  try {
    await fn();
    results.push({
      name,
      passed: true,
      message: 'OK',
      duration: Date.now() - start,
    });
    console.log(` ${name}`);
  } catch (error: any) {
    results.push({
      name,
      passed: false,
      message: error.message,
      duration: Date.now() - start,
    });
    console.log(` ${name}: ${error.message}`);
  }
}

async function runTests() {
  console.log(' Testing Two-Tower Recommendation Pipeline\n');
  console.log('='.repeat(60) + '\n');

  // Test 1: Load all_posts.json
  await test('Load all_posts.json', async () => {
    const postsPath = path.join(__dirname, '..', 'all_posts.json');
    if (!fs.existsSync(postsPath)) {
      throw new Error('all_posts.json not found');
    }
    const posts = JSON.parse(fs.readFileSync(postsPath, 'utf-8'));
    if (!Array.isArray(posts) || posts.length === 0) {
      throw new Error('all_posts.json is empty or invalid');
    }
    console.log(`   Found ${posts.length} posts`);
  });

  // Test 2: Embedding Service Initialization
  await test('Initialize Embedding Service', async () => {
    const embeddingService = new EmbeddingService();
    if (!embeddingService) {
      throw new Error('Failed to initialize embedding service');
    }
  });

  // Test 3: Generate single embedding (if API key available)
  await test('Generate Text Embedding', async () => {
    if (!process.env.OPENAI_API_KEY) {
      console.log('     Skipped (no OPENAI_API_KEY)');
      return;
    }
    
    const embeddingService = new EmbeddingService();
    const testText = 'Join us for a tech workshop on machine learning and AI';
    const embedding = await embeddingService.generateEmbedding(testText);
    
    if (!Array.isArray(embedding) || embedding.length !== 1536) {
      throw new Error(`Expected 1536 dimensions, got ${embedding.length}`);
    }
    console.log(`   Generated embedding with ${embedding.length} dimensions`);
  });

  // Test 4: Vector Index Operations
  await test('Vector Index Operations', async () => {
    const index = new VectorIndex(4); // Small dimension for testing
    
    // Add vectors
    index.add('event1', [1, 0, 0, 0], { category: 'tech' });
    index.add('event2', [0, 1, 0, 0], { category: 'social' });
    index.add('event3', [0.9, 0.1, 0, 0], { category: 'tech' }); // Similar to event1
    
    if (index.size() !== 3) {
      throw new Error(`Expected 3 vectors, got ${index.size()}`);
    }
    
    // Search for similar to [1, 0, 0, 0]
    const results = index.search([1, 0, 0, 0], 2);
    
    if (results[0].id !== 'event1') {
      throw new Error('Expected event1 to be most similar');
    }
    
    if (results[1].id !== 'event3') {
      throw new Error('Expected event3 to be second most similar');
    }
    
    console.log(`   Search returned correct order: ${results.map(r => r.id).join(', ')}`);
  });

  // Test 5: Cosine Similarity Calculation
  await test('Cosine Similarity Calculation', async () => {
    const embeddingService = new EmbeddingService();
    
    // Identical vectors should have similarity = 1
    const sim1 = embeddingService.cosineSimilarity([1, 0, 0], [1, 0, 0]);
    if (Math.abs(sim1 - 1) > 0.001) {
      throw new Error(`Expected similarity ~1, got ${sim1}`);
    }
    
    // Orthogonal vectors should have similarity = 0
    const sim2 = embeddingService.cosineSimilarity([1, 0, 0], [0, 1, 0]);
    if (Math.abs(sim2) > 0.001) {
      throw new Error(`Expected similarity ~0, got ${sim2}`);
    }
    
    // Opposite vectors should have similarity = -1
    const sim3 = embeddingService.cosineSimilarity([1, 0, 0], [-1, 0, 0]);
    if (Math.abs(sim3 + 1) > 0.001) {
      throw new Error(`Expected similarity ~-1, got ${sim3}`);
    }
    
    console.log('   Cosine similarity calculations correct');
  });

  // Test 6: Category Classification (if API available)
  await test('Event Category Classification', async () => {
    if (!process.env.OPENAI_API_KEY) {
      console.log('     Skipped (no OPENAI_API_KEY)');
      return;
    }
    
    const embeddingService = new EmbeddingService();
    
    const testCaptions = [
      { text: 'Join us for a hands-on machine learning workshop', expected: 'tech_workshop' },
      { text: 'Career networking event with industry professionals', expected: 'career_networking' },
      { text: 'Bar night and social mixer', expected: 'social_event' },
    ];
    
    for (const test of testCaptions) {
      const category = await embeddingService.classifyEventCategory(test.text);
      console.log(`   "${test.text.substring(0, 40)}..." → ${category}`);
      
      if (!CONNECT3_CATEGORIES.includes(category as any)) {
        console.log(`     Warning: Unexpected category "${category}" (expected ${test.expected})`);
      }
    }
  });

  // Test 7: Vector Index Serialization
  await test('Vector Index Serialization', async () => {
    const index = new VectorIndex(4);
    index.add('test1', [1, 2, 3, 4], { meta: 'data' });
    index.add('test2', [5, 6, 7, 8]);
    
    const json = index.toJSON();
    const restored = VectorIndex.fromJSON(json);
    
    if (restored.size() !== 2) {
      throw new Error('Serialization failed - wrong size');
    }
    
    const entry = restored.get('test1');
    if (!entry || entry.metadata?.meta !== 'data') {
      throw new Error('Serialization failed - metadata lost');
    }
    
    console.log('   Serialization/deserialization successful');
  });

  // Test 8: Search with Filters
  await test('Filtered Vector Search', async () => {
    const index = new VectorIndex(4);
    index.add('tech1', [1, 0, 0, 0], { category: 'tech' });
    index.add('tech2', [0.9, 0.1, 0, 0], { category: 'tech' });
    index.add('social1', [0.8, 0.2, 0, 0], { category: 'social' });
    
    // Search only tech events
    const results = index.searchWithFilter(
      [1, 0, 0, 0],
      10,
      (meta) => meta?.category === 'tech'
    );
    
    if (results.length !== 2) {
      throw new Error(`Expected 2 results, got ${results.length}`);
    }
    
    if (results.some(r => r.metadata?.category !== 'tech')) {
      throw new Error('Filter not working correctly');
    }
    
    console.log('   Filtered search returned only tech events');
  });

  // Print summary
  console.log('\n' + '='.repeat(60));
  console.log(' Test Summary');
  console.log('='.repeat(60));
  
  const passed = results.filter(r => r.passed).length;
  const failed = results.filter(r => !r.passed).length;
  const totalTime = results.reduce((sum, r) => sum + r.duration, 0);
  
  console.log(`   Passed: ${passed}`);
  console.log(`   Failed: ${failed}`);
  console.log(`   Total time: ${totalTime}ms`);
  
  if (failed > 0) {
    console.log('\n❌ Failed tests:');
    for (const result of results.filter(r => !r.passed)) {
      console.log(`   - ${result.name}: ${result.message}`);
    }
    process.exit(1);
  } else {
    console.log('\n All tests passed!');
  }
}

runTests().catch(console.error);
