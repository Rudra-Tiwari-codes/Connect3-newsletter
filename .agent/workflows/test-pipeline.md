---
description: Step-by-step testing workflow for the Connect3 recommendation system
---

# Connect3 Testing Workflow

This workflow guides you through testing the entire recommendation pipeline step by step.

## Prerequisites

Before starting, ensure you have:
- [ ] Node.js installed (v18+)
- [ ] `.env` file configured with `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `OPENAI_API_KEY`
- [ ] Dependencies installed (`npm install`)

---

## Step 1: Verify Environment Setup

Check that your environment is configured correctly:

```bash
npm run dev
```

Visit http://localhost:3000 to confirm the app is running. Press `Ctrl+C` to stop when done.

---

## Step 2: Database Setup

Display the SQL needed to set up your database:

```bash
npm run db:setup
```

Copy the SQL output and run it in your Supabase SQL Editor if you haven't already.

---

## Step 3: Generate Synthetic Events

Create 50 test events from University of Melbourne clubs:

```bash
npm run generate-synthetic-events
```

This populates your `events` table with diverse event data.

---

## Step 4: Generate Synthetic Students

Create 100 synthetic student users with preferences:

```bash
npm run generate-students
```

This creates users in the `users` table and their preferences in `user_preferences`.

---

## Step 5: Embed Events (Requires OpenAI API)

Generate embeddings for all events using OpenAI:

```bash
npm run embed-events
```

⚠️ This requires `OPENAI_API_KEY` and will make API calls.

---

## Step 6: Run Event Ingestion

Classify any unclassified events:

```bash
npm run ingest
```

---

## Step 7: Update User Clusters

Run PCA clustering on users based on their preferences:

```bash
npm run cluster
```

---

## Step 8: Generate Recommendations

Generate personalized recommendations for all users:

```bash
npm run recommend
```

To also send emails (requires email config):

```bash
npm run recommend -- --send
```

---

## Step 9: Demo Category-Based System

Test the category-based recommendation system:

```bash
npm run demo-category
```

This generates sample emails and saves them to HTML/TXT files.

---

## Step 10: Test Pipeline (Unit Tests)

Run unit tests for the recommendation pipeline:

```bash
npm run test-pipeline
```

---

## Step 11: Local Demo (No Database)

Run a local demo without database access:

```bash
npm run demo
```

---

## Step 12: Test Category System Locally

Test the category system with mock data (no database):

```bash
npm run test-category-local
```

---

## Quick Test (Minimal Steps)

If you just want to quickly verify everything works:

```bash
# 1. Generate students
npm run generate-students

# 2. Generate events
npm run generate-synthetic-events

# 3. Test demo
npm run demo-category
```

---

## Troubleshooting

### "Missing Supabase environment variables"
→ Ensure your `.env` file has `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` set.

### "Missing OpenAI API key"
→ Add `OPENAI_API_KEY` to your `.env` file for embedding scripts.

### "column X does not exist"
→ Run `npm run db:setup` and execute the SQL in your Supabase dashboard.

### Scripts still failing after fixes
→ Run `npm install` to ensure all dependencies are installed.
