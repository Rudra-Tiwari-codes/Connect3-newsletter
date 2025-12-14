# Deployment Checklist

## Phase 1: Core Implementation (Complete)

### Category Classification
- [x] AI-powered event categorization (GPT-4o-mini)
- [x] 14 distinct event categories
- [x] Automatic category assignment on event creation
- [x] Batch processing for existing events

### Naive Bayes Recommender
- [x] User preference modeling from interactions
- [x] Prior/likelihood/posterior scoring
- [x] Diversity enforcement (max 1 event per cluster)
- [x] Recency weighting

### Email Templates
- [x] HTML email design (category-email-template.ts)
- [x] Mobile-responsive layout
- [x] Feedback buttons (Love it / Not for me)

## Phase 2: Database Integration

- [x] Events table has category column
- [x] User_feedback table exists
- [x] Event_interactions table for click tracking
- [ ] Add index on events.category

## Phase 3: API Integration

- [x] POST /api/feedback route implemented
- [ ] GET /api/recommendations
- [ ] POST /api/preferences
- [ ] GET /api/events

## Phase 4: Email Delivery

- [x] Nodemailer configuration
- [x] Gmail app password in .env
- [x] send-newsletters.ts script
- [ ] Rate limiting (Gmail: 500/day free tier)
- [ ] Cron job or scheduled function

## Phase 5: Testing

- [x] test-category-system-local.ts
- [x] demo-category-recommendations.ts
- [ ] Test with real Supabase data
- [ ] Verify email delivery
- [ ] Load test recommendation engine

## Environment Variables

```env
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
OPENAI_API_KEY=sk-...
GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

## Key Files

| File | Purpose |
|------|---------|
| src/lib/category-classifier.ts | Event categorization |
| src/lib/category-recommender.ts | Naive Bayes recommendations |
| src/lib/category-email-template.ts | HTML email generation |
| scripts/test-category-system-local.ts | Local testing |

## Commands

```bash
npm run test-category-local   # Local test (no database)
npm run demo-category         # HTML preview
npm run send-newsletters      # Send real newsletters
npm run embed-events          # Embed and categorize events
```

## Troubleshooting

**Category is null**: Run `npm run embed-events`

**No recommendations**: Check user has interactions, events have categories, date filtering shows future events

**Email not sending**: Verify Gmail app password (not regular password), 2FA enabled

**OpenAI rate limit**: Add delays between calls, use batch processing

## Deployment Steps

### Before Deploy
- [ ] All env variables set
- [ ] Database schema applied
- [ ] Test locally

### First Deploy
- [ ] Deploy to Vercel
- [ ] Test feedback endpoint
- [ ] Send test newsletter
- [ ] Monitor for errors
