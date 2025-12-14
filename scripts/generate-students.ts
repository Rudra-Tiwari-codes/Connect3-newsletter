/**
 * Generate Synthetic Student Data for Testing
 * 
 * Creates 100 synthetic university students with:
 * - Name
 * - Email
 * - Year level
 * - Faculty
 * - Preference categories (interests)
 * 
 * Run: npm run generate-students
 */

import 'dotenv/config';
import { supabase } from '../src/lib/supabase';
import { CONNECT3_CATEGORIES, Connect3Category } from '../src/lib/embeddings';

// Australian first names for diversity
const FIRST_NAMES = [
  // Common Australian names
  'James', 'William', 'Oliver', 'Jack', 'Noah', 'Thomas', 'Henry', 'Leo', 'Charlie', 'Lucas',
  'Emma', 'Olivia', 'Charlotte', 'Mia', 'Amelia', 'Ava', 'Isla', 'Grace', 'Chloe', 'Sophie',
  // International diversity
  'Wei', 'Chen', 'Yuki', 'Aditya', 'Priya', 'Mohammed', 'Fatima', 'Krishna', 'Ananya', 'Raj',
  'Ming', 'Shu', 'Kenji', 'Sakura', 'Jin', 'Hana', 'Arjun', 'Meera', 'Vikram', 'Neha',
  'Ahmed', 'Zara', 'Omar', 'Layla', 'Hassan', 'Noor', 'Ali', 'Sara', 'Ibrahim', 'Yasmin',
  // More names
  'Liam', 'Ethan', 'Alexander', 'Daniel', 'Matthew', 'Ryan', 'Joshua', 'Andrew', 'Nathan', 'Benjamin',
  'Emily', 'Hannah', 'Sarah', 'Jessica', 'Ashley', 'Samantha', 'Rachel', 'Lauren', 'Nicole', 'Michelle',
  'David', 'Michael', 'Christopher', 'Kevin', 'Brian', 'Jason', 'Justin', 'Brandon', 'Eric', 'Steven',
  'Amanda', 'Melissa', 'Jennifer', 'Elizabeth', 'Rebecca', 'Katherine', 'Stephanie', 'Christina', 'Andrea', 'Maria',
];

const LAST_NAMES = [
  // Common Australian surnames
  'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Davis', 'Miller', 'Wilson', 'Taylor', 'Anderson',
  'Thomas', 'Jackson', 'White', 'Harris', 'Martin', 'Thompson', 'Garcia', 'Martinez', 'Robinson', 'Clark',
  // Asian surnames
  'Wang', 'Li', 'Zhang', 'Chen', 'Liu', 'Yang', 'Huang', 'Zhao', 'Wu', 'Zhou',
  'Nguyen', 'Tran', 'Le', 'Pham', 'Kim', 'Park', 'Lee', 'Jung', 'Kang', 'Cho',
  'Tanaka', 'Yamamoto', 'Suzuki', 'Watanabe', 'Ito', 'Takahashi', 'Kobayashi', 'Sato', 'Nakamura', 'Yamada',
  // Indian surnames
  'Patel', 'Sharma', 'Singh', 'Kumar', 'Gupta', 'Reddy', 'Rao', 'Mehta', 'Shah', 'Joshi',
  // Middle Eastern
  'Khan', 'Ali', 'Ahmed', 'Hassan', 'Hussein', 'Abbas', 'Rahman', 'Ibrahim', 'Hussain', 'Abdullah',
];

const FACULTIES = [
  'Engineering',
  'Science',
  'Business and Economics',
  'Arts',
  'Medicine, Dentistry and Health Sciences',
  'Law',
  'Architecture, Building and Planning',
  'Education',
  'Fine Arts and Music',
  'Veterinary and Agricultural Sciences',
];

const DEGREES = {
  'Engineering': ['Software Engineering', 'Electrical Engineering', 'Mechanical Engineering', 'Civil Engineering', 'Biomedical Engineering'],
  'Science': ['Computer Science', 'Data Science', 'Mathematics', 'Physics', 'Chemistry', 'Biology'],
  'Business and Economics': ['Commerce', 'Economics', 'Finance', 'Accounting', 'Marketing', 'Management'],
  'Arts': ['Psychology', 'Media and Communications', 'Politics', 'History', 'Linguistics', 'Philosophy'],
  'Medicine, Dentistry and Health Sciences': ['Medicine', 'Dentistry', 'Physiotherapy', 'Nursing', 'Public Health'],
  'Law': ['Law', 'Criminology'],
  'Architecture, Building and Planning': ['Architecture', 'Urban Planning', 'Property'],
  'Education': ['Education', 'Teaching'],
  'Fine Arts and Music': ['Music', 'Fine Arts', 'Theatre'],
  'Veterinary and Agricultural Sciences': ['Veterinary Science', 'Agricultural Science'],
};

// Student personas with realistic interest distributions
interface StudentPersona {
  name: string;
  interests: Connect3Category[];
  probability: number;
}

const STUDENT_PERSONAS: StudentPersona[] = [
  {
    name: 'Tech Enthusiast',
    interests: ['tech_workshop', 'hackathon', 'industry_talk', 'career_networking'],
    probability: 0.25,
  },
  {
    name: 'Career Focused',
    interests: ['career_networking', 'industry_talk', 'entrepreneurship'],
    probability: 0.20,
  },
  {
    name: 'Social Butterfly',
    interests: ['social_event', 'sports_recreation', 'community_service'],
    probability: 0.15,
  },
  {
    name: 'Academic',
    interests: ['academic_revision', 'tech_workshop', 'recruitment'],
    probability: 0.15,
  },
  {
    name: 'Entrepreneur',
    interests: ['entrepreneurship', 'hackathon', 'career_networking', 'industry_talk'],
    probability: 0.10,
  },
  {
    name: 'All-Rounder',
    interests: ['tech_workshop', 'social_event', 'career_networking', 'academic_revision'],
    probability: 0.10,
  },
  {
    name: 'Community Leader',
    interests: ['community_service', 'recruitment', 'social_event'],
    probability: 0.05,
  },
];

interface SyntheticStudent {
  name: string;
  email: string;
  year: number;
  faculty: string;
  degree: string;
  interests: Connect3Category[];
  preferences: Record<string, number>;
}

function generateEmail(firstName: string, lastName: string): string {
  const formats = [
    `${firstName.toLowerCase()}.${lastName.toLowerCase()}`,
    `${firstName.toLowerCase()}${lastName.toLowerCase()}`,
    `${firstName.toLowerCase()}.${lastName.toLowerCase()}${Math.floor(Math.random() * 100)}`,
    `${firstName[0].toLowerCase()}${lastName.toLowerCase()}`,
  ];

  const format = formats[Math.floor(Math.random() * formats.length)];
  return `${format}@student.unimelb.edu.au`;
}

function selectPersona(): StudentPersona {
  const random = Math.random();
  let cumulative = 0;

  for (const persona of STUDENT_PERSONAS) {
    cumulative += persona.probability;
    if (random <= cumulative) {
      return persona;
    }
  }

  return STUDENT_PERSONAS[0];
}

function generatePreferences(interests: Connect3Category[]): Record<string, number> {
  const preferences: Record<string, number> = {};

  // Map Connect3 categories to preference columns
  const categoryMapping: Record<string, string[]> = {
    'tech_workshop': ['tech_innovation'],
    'career_networking': ['career_networking'],
    'hackathon': ['tech_innovation', 'entrepreneurship'],
    'social_event': ['social_cultural'],
    'academic_revision': ['academic_workshops'],
    'recruitment': ['volunteering_community'],
    'industry_talk': ['career_networking', 'tech_innovation'],
    'sports_recreation': ['sports_fitness'],
    'entrepreneurship': ['entrepreneurship'],
    'community_service': ['volunteering_community'],
  };

  // Initialize all preferences to 0.5 (neutral)
  const allPrefs = [
    'academic_workshops', 'career_networking', 'social_cultural', 'sports_fitness',
    'arts_music', 'tech_innovation', 'volunteering_community', 'food_dining',
    'travel_adventure', 'health_wellness', 'entrepreneurship', 'environment_sustainability',
    'gaming_esports'
  ];

  for (const pref of allPrefs) {
    preferences[pref] = 0.5;
  }

  // Boost preferences based on interests
  for (const interest of interests) {
    const mappedPrefs = categoryMapping[interest] || [];
    for (const pref of mappedPrefs) {
      // Add 0.1-0.3 to the preference, capped at 1.0
      preferences[pref] = Math.min(1.0, preferences[pref] + 0.1 + Math.random() * 0.2);
    }
  }

  // Add some randomness to other preferences
  for (const pref of allPrefs) {
    preferences[pref] += (Math.random() - 0.5) * 0.1;
    preferences[pref] = Math.max(0, Math.min(1, preferences[pref]));
  }

  return preferences;
}

function generateStudent(): SyntheticStudent {
  const firstName = FIRST_NAMES[Math.floor(Math.random() * FIRST_NAMES.length)];
  const lastName = LAST_NAMES[Math.floor(Math.random() * LAST_NAMES.length)];
  const name = `${firstName} ${lastName}`;
  const email = generateEmail(firstName, lastName);

  const year = Math.floor(Math.random() * 5) + 1; // 1-5 years
  const faculty = FACULTIES[Math.floor(Math.random() * FACULTIES.length)];
  const degrees = DEGREES[faculty as keyof typeof DEGREES] || ['General Studies'];
  const degree = degrees[Math.floor(Math.random() * degrees.length)];

  const persona = selectPersona();

  // Add some variation to interests
  const interests = [...persona.interests];

  // Maybe add 1-2 random interests
  if (Math.random() > 0.5) {
    const otherCategories = CONNECT3_CATEGORIES.filter(c => !interests.includes(c));
    const randomCategory = otherCategories[Math.floor(Math.random() * otherCategories.length)];
    interests.push(randomCategory);
  }

  const preferences = generatePreferences(interests);

  return {
    name,
    email,
    year,
    faculty,
    degree,
    interests,
    preferences,
  };
}

async function generateAndInsertStudents(count: number = 100) {
  console.log(`🎓 Generating ${count} synthetic students...\n`);

  const students: SyntheticStudent[] = [];
  const usedEmails = new Set<string>();

  // Generate unique students
  while (students.length < count) {
    const student = generateStudent();

    // Ensure unique email
    if (!usedEmails.has(student.email)) {
      usedEmails.add(student.email);
      students.push(student);
    }
  }

  // Insert into database
  let successCount = 0;
  let errorCount = 0;

  for (const student of students) {
    try {
      // Insert user
      const { data: userData, error: userError } = await supabase
        .from('users')
        .insert({
          email: student.email,
          name: student.name,
        })
        .select()
        .single();

      if (userError) {
        throw new Error(`Failed to insert user: ${userError.message}`);
      }

      // Insert preferences
      const { error: prefError } = await supabase
        .from('user_preferences')
        .insert({
          user_id: userData.id,
          ...student.preferences,
        });

      if (prefError) {
        throw new Error(`Failed to insert preferences: ${prefError.message}`);
      }

      successCount++;
      console.log(`✓ Created: ${student.name} (${student.faculty}, Year ${student.year})`);
      console.log(`  Email: ${student.email}`);
      console.log(`  Interests: ${student.interests.join(', ')}`);
      console.log('');

    } catch (error: any) {
      errorCount++;
      console.error(`✗ Error creating ${student.name}: ${error.message}\n`);
    }
  }

  console.log('\n' + '='.repeat(50));
  console.log(`✅ Student generation complete!`);
  console.log(`   Success: ${successCount}`);
  console.log(`   Errors: ${errorCount}`);
  console.log('='.repeat(50));

  // Print distribution statistics
  await printStudentStatistics();
}

async function printStudentStatistics() {
  const { data: users } = await supabase.from('users').select('*');
  const { data: preferences } = await supabase.from('user_preferences').select('*');

  if (!users || !preferences) return;

  console.log('\n📊 Student Statistics:');
  console.log(`   Total students: ${users.length}`);

  // Calculate average preferences
  const avgPrefs: Record<string, number> = {};
  const prefKeys = [
    'academic_workshops', 'career_networking', 'social_cultural', 'sports_fitness',
    'arts_music', 'tech_innovation', 'volunteering_community', 'food_dining',
    'travel_adventure', 'health_wellness', 'entrepreneurship', 'environment_sustainability',
    'gaming_esports'
  ];

  for (const key of prefKeys) {
    avgPrefs[key] = preferences.reduce((sum, p) => sum + (p[key] || 0.5), 0) / preferences.length;
  }

  console.log('\n📈 Average Preference Scores:');
  const sorted = Object.entries(avgPrefs).sort((a, b) => b[1] - a[1]);
  for (const [pref, avg] of sorted) {
    const bar = '█'.repeat(Math.round(avg * 20));
    console.log(`   ${pref.padEnd(25)} ${avg.toFixed(2)} ${bar}`);
  }
}

// Export the data as JSON as well
async function exportToJSON() {
  const { data: users } = await supabase
    .from('users')
    .select('*, user_preferences(*)');

  if (users) {
    const fs = await import('fs');
    const path = await import('path');

    fs.writeFileSync(
      path.join(__dirname, '..', 'synthetic_students.json'),
      JSON.stringify(users, null, 2)
    );

    console.log('\n📁 Exported to synthetic_students.json');
  }
}

// Run
generateAndInsertStudents(100)
  .then(() => exportToJSON())
  .catch(console.error);
