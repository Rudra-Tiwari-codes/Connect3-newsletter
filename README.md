# Connect3 - Event Recommendation System

Personalized university event newsletter system built for DSCubed at the University of Melbourne.

## Features

- Category-based recommendations using Naive Bayes classification (3 diverse events per email)
- Two-Tower recommendations using OpenAI embeddings (semantic matching)
- Personalized HTML email templates with feedback buttons
- User preference learning from clicks and feedback

## Tech Stack

| Component | Technology |
|-----------|------------|
| Database | Supabase (Postgres) |
| Backend | Next.js 14, TypeScript |
| Embeddings | OpenAI text-embedding-3-small (1536 dims) |
| Classification | GPT-4o-mini |
| Email | Gmail SMTP via Nodemailer |

## Prerequisites

- Node.js >= 18
- npm >= 9
- Supabase project
- OpenAI API key
- Gmail account with App Password

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure environment:
```bash
cp .env.example .env
# Set: SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_API_KEY, GMAIL_USER, GMAIL_APP_PASSWORD
```

3. Initialize database (run in Supabase SQL Editor):
```
database/schema.sql
database/schema-embeddings.sql
database/seed.sql  # optional
```

4. Run demos:
```bash
npm run demo-category   # category-based (HTML preview)
npm run demo            # two-tower (no DB required)
```

## Scripts

| Script | Description |
|--------|-------------|
| `dev` | Start Next.js dev server |
| `build` | Build for production |
| `demo-category` | Test category recommender |
| `demo` | Local two-tower demo |
| `embed-events` | Generate event embeddings |
| `generate-students` | Create test users |
| `generate-synthetic-events` | Create 50 sample events |

## Project Structure

```
src/lib/           # Core libraries (classifiers, recommenders, email templates)
scripts/           # Automation and demo scripts
database/          # SQL schemas and seed data
```

## Category Clusters

Events are grouped into 7 clusters:
- Technical (Hackathon, Tech Workshop)
- Professional (Career, Networking, Recruitment)
- Social (Cultural, Food, Entertainment)
- Academic (Study, Tutorial)
- Wellness (Sports, Fitness)
- Creative (Arts, Music)
- Advocacy (Volunteering, Environmental)

## License

MIT
