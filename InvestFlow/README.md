# Invest Flow

Invest Flow is a minimal iPhone SwiftUI app focused on three workflows:

- Money: monthly cash-flow tracking, investable amount calculation, and recurring allocation planning.
- Routine: morning, intraday, and evening investing checklists with contrarian prompts and daily review notes.
- Post-it: stock and crypto idea capture with text or mock voice notes, AI summaries, allocation proposals, and explicit user approval before proposals enter the investment plan.

## Architecture

- SwiftUI views live in `InvestFlow/Views`.
- MVVM view models live in `InvestFlow/ViewModels`.
- SwiftData models live in `InvestFlow/Models`.
- Protocol-based services and mock implementations live in `InvestFlow/Services`.

The app currently uses mock market, AI, and voice-note services so external APIs can be connected later without changing the UI.

## Run

Open `InvestFlow.xcodeproj` in Xcode 15 or later, select an iPhone simulator, and run the `InvestFlow` scheme.

## iOS Chrome Web Version

The companion mobile web/PWA version lives in `../InvestFlowWeb`.

From the repository root:

```bash
python3 InvestFlowWeb/server.py
```

Open `http://localhost:8080` on a device or simulator browser. For a physical iPhone, serve it from a host address reachable on the same network.

`InvestFlowWeb/server.py` serves the web app, refreshes Edgar market ticker data in the background, and proxies DeepSeek requests so API keys are not exposed in mobile Chrome. Set `DEEPSEEK_API_KEY` before starting the server.

```bash
export DEEPSEEK_API_KEY=...
export INVEST_FLOW_MARKET_REFRESH_SECONDS=900
python3 InvestFlowWeb/server.py
```

iOS Chrome cannot keep JavaScript running in the background for 24 hours. Keep the Python server running on a Mac, NAS, VPS, or always-on machine; the mobile app reconnects to its `/api/market` and `/api/deepseek` endpoints.

## Oracle Cloud Deployment

Invest Flow can run on the same Oracle Cloud VM as Edgar. Use a separate
systemd service and expose it behind the existing nginx site at
`https://YOUR_DOMAIN/investflow/`.

Example files are in `../InvestFlowWeb/deploy`:

- `invest-flow.service`: keeps the Invest Flow Python server running 24 hours.
- `nginx-investflow.conf`: proxies `/investflow/` to the local Invest Flow port.

On the Oracle VM:

```bash
cd /home/ubuntu/edgar
cp InvestFlowWeb/deploy/invest-flow.service /etc/systemd/system/invest-flow.service
sudo systemctl daemon-reload
sudo systemctl enable --now invest-flow
sudo systemctl status invest-flow
```

Add the nginx location block from `InvestFlowWeb/deploy/nginx-investflow.conf`
inside the existing Edgar `server { ... }` block, then reload nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Keep `DEEPSEEK_API_KEY` in `/home/ubuntu/edgar/.env` so the key stays on the
server and is never exposed to iPad Chrome.

## Shared iPad/iPhone Chrome Deployment

For the simplest shared setup, deploy the repository to Vercel and reuse the
existing Edgar Supabase project.

Invest Flow stores the shared family app state in the `invest_flow_states`
table defined in `database/schema.sql`. Run the updated schema in the existing
Supabase SQL Editor before deploying.

Vercel environment variables:

```bash
SUPABASE_URL=...
SUPABASE_KEY=...
DEEPSEEK_API_KEY=...
```

`SUPABASE_ANON_KEY` also works if that is the key name you use in Vercel.

After deployment, open the same family URL on both devices:

```text
https://YOUR_VERCEL_APP.vercel.app/?family=YOUR_FAMILY_CODE
```

Both iPad and iPhone Chrome will read and write the same Supabase-backed Invest
Flow state. If the `family` query parameter is omitted, the app uses `family` as
the default shared code.
