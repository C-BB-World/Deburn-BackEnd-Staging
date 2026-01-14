# Backend Refactor To-Do

Pre-requisites and setup tasks before the refactored backend can work.

---

## External Services Setup

### 1. Firebase (Authentication)

1) Go to [Firebase Console](https://console.firebase.google.com/)
2) Create a new project (or use existing)
3) Enable Authentication → Sign-in methods → Email/Password
4) Go to Project Settings → Service Accounts
5) Generate new private key (downloads JSON file)
6) Set environment variables:
   - `FIREBASE_PROJECT_ID`
   - `FIREBASE_PRIVATE_KEY`
   - `FIREBASE_CLIENT_EMAIL`

### 2. MongoDB (Database)

1) Go to [MongoDB Atlas](https://www.mongodb.com/atlas) (or use self-hosted)
2) Create a cluster
3) Create database user with read/write access
4) Whitelist IP addresses (or allow from anywhere for development)
5) Get connection string
6) Set environment variables:
   - `MONGODB_URI` (main database)
   - `HUB_MONGODB_URI` (hub database - can be same cluster, different DB)

### 3. Resend (Email)

1) Go to [Resend](https://resend.com/)
2) Sign up and verify your domain
3) Get API key from dashboard
4) Set environment variables:
   - `RESEND_API_KEY`
   - `EMAIL_FROM_ADDRESS` (e.g., noreply@yourdomain.com)
   - `EMAIL_FROM_NAME` (e.g., "Eve")

### 4. Google Cloud (Calendar Integration)

1) Go to [Google Cloud Console](https://console.cloud.google.com/)
2) Create a new project (or use existing)
3) Enable Google Calendar API
4) Go to Credentials → Create OAuth 2.0 Client ID
5) Set authorized redirect URIs (e.g., `https://yourdomain.com/api/calendar/callback`)
6) Download client credentials JSON
7) Set environment variables:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI`
   - `CALENDAR_ENCRYPTION_KEY` (generate with `openssl rand -hex 32`)

### 5. Anthropic (AI - Claude API)

1) Go to [Anthropic Console](https://console.anthropic.com/)
2) Sign up and add payment method
3) Get API key from dashboard
4) Set environment variables:
   - `CLAUDE_API_KEY`

### 6. FAL.ai (Image Generation) - Optional

1) Go to [FAL.ai](https://fal.ai/)
2) Sign up and get API key
3) Set environment variables:
   - `FAL_API_KEY`

---

## Environment Variables Summary

```bash
# Auth (Firebase)
FIREBASE_PROJECT_ID=
FIREBASE_PRIVATE_KEY=
FIREBASE_CLIENT_EMAIL=

# Database (MongoDB)
MONGODB_URI=
HUB_MONGODB_URI=

# Email (Resend)
RESEND_API_KEY=
EMAIL_FROM_ADDRESS=
EMAIL_FROM_NAME=
EMAIL_MODE=resend  # console | resend | smtp

# Calendar (Google)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
CALENDAR_ENCRYPTION_KEY=

# AI (Anthropic)
CLAUDE_API_KEY=

# Image Generation (FAL.ai) - Optional
FAL_API_KEY=

# App Settings
JWT_SECRET=  # generate with: openssl rand -hex 32
APP_URL=     # e.g., https://app.yourdomain.com
PORT=5001
NODE_ENV=development
```

---

## Code Implementation Tasks

### 1. Agent Implementation

1) Decide on AI approach (Claude direct, RAG, memory system)
2) Implement `Agent` class with required methods:
   - `generate_coaching_response()`
   - `generate_checkin_insight()`
   - `enhance_recommendation()`
   - `extract_topics()`
3) Write system prompts (or migrate existing from `prompts/system/`)

### 2. Database Migrations

1) Create MongoDB indexes for all collections
2) Seed initial Hub admin (first platform admin)
3) Seed insight triggers (streak milestones, patterns)
4) Seed safety keywords (if storing in DB vs hardcoded)

### 3. Cron Jobs Setup

1) Email queue processor (every 30 seconds)
2) Scheduled emails - weekly focus (Monday 9 AM)
3) Scheduled emails - check-in reminders (daily 6 PM)
4) Meeting reminders (every 15 minutes)
5) Invitation expiration (hourly)
6) Commitment expiration (daily)
7) Session cleanup (daily)

### 4. Translation Files

1) Create/migrate `locales/en/` translation files
2) Create/migrate `locales/sv/` translation files
3) Create email templates for both languages

---

## Testing Checklist

- [ ] Firebase auth flow (sign up, verify, login)
- [ ] MongoDB connections (main + hub)
- [ ] Email sending (verification, password reset)
- [ ] Google Calendar OAuth flow
- [ ] AI coaching conversation
- [ ] Check-in with insight generation
- [ ] Circle invitation flow
- [ ] Meeting scheduling with calendar sync

---

## Deployment Checklist

- [ ] Environment variables set in production
- [ ] MongoDB IP whitelist updated
- [ ] Domain verified for email (SPF, DKIM)
- [ ] SSL certificate configured
- [ ] Google OAuth redirect URIs updated
- [ ] Cron jobs scheduled
- [ ] Initial Hub admin seeded
