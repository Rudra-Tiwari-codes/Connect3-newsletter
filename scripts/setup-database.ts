import * as fs from 'fs';
import * as path from 'path';

async function setupDatabase() {
  console.log('Setting up database...\n');

  try {
    const schemaPath = path.join(__dirname, '../database/schema.sql');
    const seedPath = path.join(__dirname, '../database/seed.sql');

    // Check if SQL files exist
    if (!fs.existsSync(schemaPath)) {
      console.error('❌ Error: database/schema.sql not found');
      process.exit(1);
    }

    if (!fs.existsSync(seedPath)) {
      console.error('❌ Error: database/seed.sql not found');
      process.exit(1);
    }

    // Read SQL files
    const schemaSQL = fs.readFileSync(schemaPath, 'utf-8');
    const seedSQL = fs.readFileSync(seedPath, 'utf-8');

    console.log('📋 Database Setup Instructions\n');
    console.log('To set up your database, follow these steps:\n');
    
    console.log('1. Go to your Supabase project dashboard');
    console.log('2. Navigate to SQL Editor');
    console.log('3. Create a new query and run the schema SQL:\n');
    console.log('─'.repeat(60));
    console.log(schemaSQL);
    console.log('─'.repeat(60));
    console.log('\n4. After the schema is created, run the seed SQL:\n');
    console.log('─'.repeat(60));
    console.log(seedSQL);
    console.log('─'.repeat(60));
    
    console.log('\n✅ Setup instructions displayed above.');
    console.log('\n💡 Tip: You can copy the SQL from the files:');
    console.log(`   - Schema: ${path.resolve(schemaPath)}`);
    console.log(`   - Seed: ${path.resolve(seedPath)}`);
    
    console.log('\n⚠️  Note: This script displays the SQL for manual execution.');
    console.log('   Automated execution requires Supabase REST API or direct database access.');
    
  } catch (error: any) {
    console.error('❌ Error reading setup files:', error.message);
    process.exit(1);
  }
}

setupDatabase();
