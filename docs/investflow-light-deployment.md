# Invest Flow Lightweight Deployment

Invest Flow runs as a lightweight browser app. Heavy Edgar jobs stay with the
existing Telegram bot.

```text
Browser
  |
  v
Vercel Free
  - InvestFlowWeb UI
  - lightweight API endpoints
  - Supabase family state read/write
  |
  v
Supabase Free
  - invest_flow_states
  - shared data for Vercel and Oracle

Oracle Cloud
  - existing bot.py runs 24 hours
  - yfinance market data
  - DeepSeek / LLM
  - YouTube API
  - PDF analysis
  - Supabase persistence
```

## Supabase

Run this in the existing Edgar Supabase SQL Editor:

```sql
CREATE TABLE IF NOT EXISTS invest_flow_states (
    family_id  text PRIMARY KEY,
    payload    jsonb       NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_invest_flow_states_updated
    ON invest_flow_states (updated_at DESC);
```

## Vercel

Vercel serves the app and installs only the light dependency set from
`requirements-vercel.txt`:

```text
python-dotenv
requests
supabase
```

Set Vercel environment variables:

```bash
SUPABASE_URL=...
SUPABASE_KEY=...
```

`SUPABASE_ANON_KEY` also works instead of `SUPABASE_KEY`.

Vercel endpoints:

```text
GET  /api/health
GET  /api/market                 -> lightweight mock metadata
POST /api/deepseek               -> disabled, frontend uses local mock summary
GET  /api/investflow/state       -> Supabase family state
POST /api/investflow/state       -> Supabase family state
```

## Oracle

Keep the current Telegram bot setup as-is:

```text
bot.py runs 24 hours on Oracle
SUPABASE_URL / SUPABASE_KEY stay configured there
Telegram, DeepSeek, YouTube, yfinance, and PDF-related keys stay there
```

Oracle shares data with Invest Flow through Supabase only.

## Family URL

Open the same URL on iPad and iPhone Chrome:

```text
https://YOUR-VERCEL-APP.vercel.app/?family=YOUR_PRIVATE_FAMILY_CODE
```

Both devices share the same Supabase-backed Invest Flow state.

## Smoke Tests

Check Vercel:

```text
https://YOUR-VERCEL-APP.vercel.app/api/health
```

Check family state:

```text
https://YOUR-VERCEL-APP.vercel.app/api/investflow/state?family_id=test
```
