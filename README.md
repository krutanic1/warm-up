# warm-up

Gmail warm-up automation service that runs on Vercel with cron scheduling.

## Features

- Sends emails between two Gmail accounts at random intervals
- Daily send limit (configurable)
- Minimum interval between sends (default: 30 minutes)
- Serverless deployment with Vercel
- Uses Vercel KV for state persistence (with local JSON fallback)

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create `.env` file:
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   MAIL1=your1@gmail.com
   PASS1=your_app_password_1
   MAIL2=your2@gmail.com
   PASS2=your_app_password_2
   DAILY_LIMIT=10
   MIN_INTERVAL_SECONDS=1800
   ```

3. For Vercel deployment, set environment variables in Vercel dashboard and configure Vercel KV:
   ```env
   KV_REST_API_URL=your_vercel_kv_url
   KV_REST_API_TOKEN=your_vercel_kv_token
   ```

## Local Testing

Run locally (uses local JSON state):
```bash
python api/warmup.py
```

## Deployment

Deploy to Vercel:
```bash
vercel --prod
```

The cron job runs every 30 minutes as configured in `vercel.json`.
