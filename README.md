# Connect3 - AI-Powered Event Recommendation System

An intelligent email newsletter system that delivers personalized university event recommendations using either:
- **🆕 Category-Based Naive Bayes** (v2.0): 3 events from 3 diverse categories
- **Two-Tower Neural Network** (v1.0): 5 similar events using OpenAI embeddings

Built for [DSCubed](https://www.instagram.com/dscubed.unimelb/) at the University of Melbourne.

> **🎯 NEW! Category-Based Recommendations**  
> The system now features a category-first approach with **Naive Bayes classification** for diverse, explainable recommendations. See [CATEGORY-QUICKSTART.md](CATEGORY-QUICKSTART.md) to get started!

## Features

### Core Recommendation Engine (v2.0 - NEW!)
- **🎯 Category-Based**: 3 events from 3 different categories for maximum diversity
- **🧠 Naive Bayes Classifier**: Ranks categories based on user interaction history
- **📊 7 Category Clusters**: Technical, Professional, Social, Academic, Wellness, Creative, Advocacy
- **🔄 Progressive Learning**: Explores → Refines → Groups users by preferences
- **⚡ Fast & Free**: No embedding calls, 50-100ms per user, $0 API costs

### Core Recommendation Engine (v1.0 - Original)
- **Two-Tower Architecture**: Event embeddings + User embeddings for semantic matching
- **OpenAI Embeddings**: 1536-dimensional vectors via `text-embedding-3-small`
- **AI Classification**: GPT-4o-mini categorizes events into 10 categories
- **Vector Similarity Search**: In-memory FAISS-like index for fast retrieval
- **Smart Ranking**: Combined similarity + recency + diversity scoring

### Email System
- **Personalized Newsletters**: Category-ranked events with personalized reasons
- **Feedback Loop**: Like/dislike/click interactions improve future recommendations
- **Magic Links**: One-click feedback from email
- **Beautiful Templates**: Ranked event cards with cluster emojis

## Tech Stack

| Component | Technology |
|-----------|------------|
| Database | Supabase (PostgreSQL) |
| Backend | Next.js 14, TypeScript |
| Embeddings | OpenAI text-embedding-3-small |
| Classification | GPT-4o-mini |
| Vector Search | Custom in-memory index |
| Email | Gmail SMTP / Nodemailer |

## Prerequisites

- **Node.js** >= 18.x
- **npm** >= 9.x
- **Supabase** account (free tier works)
- **OpenAI API** key with access to embeddings
- **Gmail** account with App Password (for email sending)

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/Rudra-Tiwari-codes/Connect-3-email-recommendation-system.git
cd Connect-3-email-recommendation-system
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_SECRET_KEY=your-service-role-key

# OpenAI
OPENAI_API_KEY=sk-proj-your-openai-key

# Email (Gmail)
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password

# App URL
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

**Getting Gmail App Password:**
1. Enable 2-Factor Authentication on your Google account
2. Go to Google Account > Security > 2-Step Verification > App passwords
3. Generate a new app password for "Mail"

### 3. Setup Database

Run these SQL files in Supabase SQL Editor (in order):

```bash
# 1. Base schema (users, events, preferences)
database/schema.sql

# 2. Embedding tables (event_embeddings, user_embeddings, etc.)
database/schema-embeddings.sql

# 3. (Optional) Seed data
database/seed.sql
```

### 4. Test the System

#### New Category-Based System (Recommended)

```bash
# Generate 50 synthetic events from clubs
npm run generate-synthetic-events

# Test category recommendations (opens HTML preview)
npm run demo-category
```

#### Original Two-Tower System

```bash
# Run the test pipeline to verify everything works
npm run test-pipeline
```

Expected output:
```
Testing Two-Tower Recommendation Pipeline
✓ Load all_posts.json
✓ Initialize Embedding Service
✓ Generate Text Embedding
✓ Vector Index Operations
✓ Cosine Similarity Calculation
✓ Event Category Classification
✓ Vector Index Serialization
✓ Filtered Vector Search
All tests passed!
```

### 5. Run the Full Pipeline

#### Category-Based Recommendations (NEW!)

```bash
# Step 1: Generate synthetic events from clubs
npm run generate-synthetic-events

# Step 2: Generate synthetic test users (if not done)
npm run generate-students

# Step 3: Test recommendations with HTML preview
npm run demo-category

# Step 4: Send emails using category system (when ready)
# Update your send script to use categoryRecommender
```

#### Two-Tower Recommendations (Original)

```bash
# Step 1: Embed all events (generates vectors + classifies categories)
npm run embed-events

# Step 2: Generate synthetic test users (for testing)
npm run generate-students

# Step 3: Generate recommendations (dry run)
npm run recommend

# Step 4: Send emails (when ready)
npm run recommend -- --send
```

### 6. Run the Demo

```bash
# Category-based demo (NEW!)
npm run demo-category

# Two-Tower demo (original - no database needed)
npm run demo
```

### 7. Generate Sample Emails

```bash
# Creates SAMPLE-EMAILS.md with personalized emails for all users
npm run generate-emails
```

## Available Scripts

| Script | Command | Description |
|--------|---------|-------------|
| `dev` | `npm run dev` | Start Next.js development server |
| `build` | `npm run build` | Build for production |
| **Category System (NEW!)** |
| `generate-synthetic-events` | `npm run generate-synthetic-events` | Generate 50 events from clubs |
| `demo-category` | `npm run demo-category` | Test category recommendations |
| **Two-Tower System (Original)** |
| `test-pipeline` | `npm run test-pipeline` | Run system tests |
| `embed-events` | `npm run embed-events` | Generate event embeddings |
| `generate-students` | `npm run generate-students` | Create synthetic users |
| `recommend` | `npm run recommend` | Generate recommendations |
| `demo` | `npm run demo` | Run local demo |
| `generate-emails` | `npm run generate-emails` | Create sample email file |

## Project Structure

```
connect3-email-system/
├── src/
│   └── lib/
│       ├── category-classifier.ts   # NEW! Naive Bayes classifier
│       ├── category-recommender.ts  # NEW! Category-based recommendations
│       ├── category-email-template.ts # NEW! Category email templates
│       ├── embeddings.ts       # Two-Tower embedding logic (OpenAI)
│       ├── vector-index.ts     # FAISS-like vector search
│       ├── recommender.ts      # Original recommendation engine
│       ├── email-template-v2.ts # AI-powered email templates
│       ├── email-delivery.ts   # Gmail SMTP sender
│       └── supabase.ts         # Database client
├── scripts/
│   ├── generate-synthetic-events.ts  # NEW! Generate 50 club events
│   ├── demo-category-recommendations.ts # NEW! Test category system
│   ├── embed-events.ts         # Embed events from all_posts.json
│   ├── generate-students.ts    # Create synthetic test data
│   ├── run-recommendations.ts  # Full pipeline runner
│   ├── test-recommendation-pipeline.ts
│   ├── demo-local.ts           # Local demo without DB
│   └── generate-sample-emails.ts
├── database/
│   ├── schema.sql              # Base schema
│   ├── schema-embeddings.sql   # Embedding tables
│   ├── seed.sql                # Sample data
│   └── test-data.sql           # Test events
├── all_posts.json              # Instagram events data
├── synthetic-events.json       # NEW! Generated club events
├── SAMPLE-EMAILS.md            # Generated sample emails
├── CATEGORY-QUICKSTART.md      # NEW! Quick start guide
├── CATEGORY-SYSTEM.md          # NEW! Full documentation
├── SYSTEM-COMPARISON.md        # NEW! Old vs New comparison
└── package.json
```

## Documentation

- 📘 **[CATEGORY-QUICKSTART.md](CATEGORY-QUICKSTART.md)** - Get started with category-based recommendations (5 min read)
- 📗 **[CATEGORY-SYSTEM.md](CATEGORY-SYSTEM.md)** - Complete category system documentation
- 📊 **[SYSTEM-COMPARISON.md](SYSTEM-COMPARISON.md)** - Old vs New system comparison
- 📄 **[PHASE_WISE_BREAKDOWN.md](PHASE_WISE_BREAKDOWN.md)** - Original project phases

## How It Works

### Category-Based System (NEW!)

```
User Interactions
       ↓
┌──────────────────┐
│ Naive Bayes      │ → Categories Ranked (1st, 2nd, 3rd)
│ Classifier       │
└──────────────────┘
       ↓
┌──────────────────┐
│ Pick 1 Event     │ → 3 Diverse Events
│ from Each        │
└──────────────────┘
       ↓
User Feedback (Click/Like/Dislike)
       ↓
System Learns → Refines Categories
```

### Two-Tower Architecture (Original)

```
┌─────────────────┐     ┌─────────────────┐
│   Event Tower   │     │   User Tower    │
│  (embeddings)   │     │  (embeddings)   │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
    ┌─────────────────────────────────┐
    │     Vector Similarity Search     │
    │         (Cosine Distance)        │
    └────────────────┬────────────────┘
                     │
                     ▼
    ┌─────────────────────────────────┐
    │    Business Rules & Ranking      │
    │  (recency, diversity, filters)   │
    └────────────────┬────────────────┘
                     │
                     ▼
              Personalized Email
```

### Scoring Formula

```
Final Score = (Similarity × 0.7) + (Recency × 0.3) - Diversity Penalty
```

### Event Categories

| Category | Description |
|----------|-------------|
| `tech_workshop` | AI, ML, coding workshops |
| `career_networking` | Industry panels, networking |
| `hackathon` | Datathons, coding competitions |
| `social_event` | Bar nights, social mixers |
| `academic_revision` | SWOTVAC, exam prep |
| `recruitment` | Club recruitment, AGMs |
| `industry_talk` | Company presentations |
| `sports_recreation` | Sports day, activities |
| `entrepreneurship` | Startup events |
| `community_service` | Volunteering |

## Database Schema

### Core Tables
- **events**: Event data with AI-classified categories
- **users**: User profiles with preferences
- **user_preferences**: Interest vectors
- **feedback_logs**: User interaction tracking

### Embedding Tables
- **event_embeddings**: 1536-dim event vectors
- **user_embeddings**: Cached user vectors
- **recommendation_logs**: Recommendation history
- **user_interactions**: Detailed click/like tracking
- **email_campaigns**: Campaign analytics

## API Endpoints

### `GET /api/feedback`
Magic link endpoint for email feedback.

**Parameters:**
- `uid`: User ID
- `eid`: Event ID
- `action`: `like | dislike | click`

## Troubleshooting

### Common Issues

**"Missing Supabase environment variables"**
- Ensure both `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are set in `.env`
- The service key should be your service role key from Supabase dashboard

**"Cannot find module 'dotenv'"**
```bash
npm install dotenv
```

**"OPENAI_API_KEY not set"**
- Get an API key from https://platform.openai.com/api-keys
- Ensure you have credits/billing enabled

**"Could not find table 'event_embeddings'"**
- Run `database/schema-embeddings.sql` in Supabase SQL Editor

**Gmail authentication errors**
- Use App Passwords, not your regular password
- Enable 2FA on your Google account first

### Testing Without Database

Use the demo script to test locally without database:
```bash
npm run demo
```

## Future Improvements

- [ ] Train actual Two-Tower model with user interaction data
- [ ] Migrate to pgvector or Pinecone for production
- [ ] Add A/B testing framework
- [ ] Real-time recommendations API
- [ ] Multi-modal embeddings (images + text)

## License

MIT License - Built for Connect3 by DSCubed

---

**Questions?** Open an issue or contact the DSCubed team.
#   C o n n e c t 3 - n e w s l e t t e r  
 