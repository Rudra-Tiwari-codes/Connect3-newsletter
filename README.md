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
# Connect3 - AI-Powered Event Recommendation System

A concise email newsletter system that delivers personalized university event recommendations.

Core approaches:
- Category-based recommendations (Naive Bayes) - 3 diverse events
- Two-Tower recommendations (embeddings) - semantic matches

Built for DSCubed at the University of Melbourne.

## Key Features
- Category-based recommender for explainable, diverse suggestions
- Two-Tower recommender using OpenAI embeddings for semantic matching
- Personalized email templates and feedback loop (like/dislike/click)
- Scripts for data ingestion, embedding generation, clustering, and email sending

## Tech Stack

| Component | Technology |
|-----------|------------|
| Database | Supabase (Postgres) |
| Backend | Next.js 14, TypeScript |
| Embeddings | OpenAI text-embedding-3-small |
| Classification | GPT-4o-mini |
| Email | Gmail SMTP / Nodemailer |

## Prerequisites
- Node.js >= 18
- npm >= 9
- Supabase project
- OpenAI API key
- Gmail account with App Password for sending mail

## Quick Start

1. Clone and install:

```bash
git clone https://github.com/Rudra-Tiwari-codes/Connect-3-email-recommendation-system.git
cd Connect-3-email-recommendation-system
npm install
```

2. Create environment file and set credentials:

```bash
cp .env.example .env
# edit .env with SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_API_KEY, GMAIL_USER, GMAIL_APP_PASSWORD
```

3. Initialize database (run SQL files in Supabase):

```
database/schema.sql
database/schema-embeddings.sql
database/seed.sql   # optional
```

4. Run demos or scripts:

```bash
npm run demo-category        # category-based demo (HTML preview)
npm run demo                 # two-tower local demo (no DB)
npm run embed-events         # generate embeddings
npm run generate-synthetic-events
```

## Useful Scripts

- `dev` - Start Next.js dev server
- `build` - Build for production
- `demo-category` - Test category recommender with sample data
- `demo` - Local two-tower demo without DB
- `embed-events` - Generate event embeddings
- `generate-students` - Create synthetic users
- `generate-emails` - Produce sample email previews

## Project Layout (short)

- `src/lib/` - core libraries (classifiers, recommenders, email templates)
- `scripts/` - automation and demo scripts
- `database/` - SQL schemas and seed data
- `all_posts.json` - sample event data

## Troubleshooting

- Missing Supabase env vars: set `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `.env`
- OpenAI key: set `OPENAI_API_KEY` and ensure billing is active
- Gmail: use an App Password with 2FA enabled

## License

MIT

For full documentation and detailed guides, see the repository files: `CATEGORY-QUICKSTART.md`, `CATEGORY-SYSTEM.md`, and `COMPLETE-CODEBASE-DOCUMENTATION.md`.
