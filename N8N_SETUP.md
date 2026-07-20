# Hybrid Setup: n8n + Python Intelligence Service

## How the pieces fit together

```
┌─────────────────────────────────────────────────────────┐
│  n8n (Docker container)                                  │
│  - Schedule triggers (replaces APScheduler)               │
│  - RSS / HTTP fetch nodes (replaces feedparser/requests)  │
│  - Telegram node (replaces telegram_client.py)            │
│  - IF nodes for skip/dedup branching                       │
└───────────────────┬─────────────────────────────────────┘
                     │ HTTP calls
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Python Intelligence Service (Docker container)           │
│  - /dedup/check, /dedup/mark  (state.py logic)             │
│  - /interpret                 (Claude prompt + parsing)    │
│  - /digest                    (daily synthesis)            │
│  - /alerts/log, /alerts/recent                              │
└─────────────────────────────────────────────────────────┘
```

n8n never talks to Claude directly and never touches SQLite directly. It calls your Python service's HTTP endpoints, which do the actual work. This means your prompt engineering, editorial context, and dedup logic stay in version-controlled Python — only the "when to run" and "where to send" logic lives in n8n's visual editor.

## What's new in this drop

```
service/
  main.py          # FastAPI app wrapping intelligence.py + state.py
  Dockerfile        # Container for the Python service
docker-compose.yml   # Runs n8n + intelligence service together
requirements-service.txt
.env.n8n.example
n8n_workflows/
  rss_monitor.json  # Importable template workflow
```

## Setup on your GCP VM

### 1. Install Docker (if not already installed)
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Log out and back in for the group change to apply
```

### 2. Set up your env files
```bash
cd ~/yex_seo_bot

# Your existing .env still holds TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, OPENAI_API_KEY
# (the intelligence service reads it directly)
cp .env.example .env
nano .env   # fill in your keys as before

# n8n's own basic-auth login credentials
cp .env.n8n.example .env.n8n
nano .env.n8n   # set a real password
```

### 3. Start everything
```bash
docker compose --env-file .env --env-file .env.n8n up -d
```

This builds the Python service image and pulls the n8n image, then starts both. First run takes a few minutes.

### 4. Verify the intelligence service is up
```bash
curl http://localhost:8000/health
# Should return {"status":"ok"}
```

### 5. Open n8n
On your Mac, tunnel to the VM so you can reach the n8n UI securely (it's not exposed to the public internet):
```bash
gcloud compute ssh VM_NAME --zone=ZONE -- -L 5678:localhost:5678
```
Leave that terminal open, then visit `http://localhost:5678` in your Mac browser. Log in with the `N8N_USER`/`N8N_PASSWORD` you set.

### 6. Add your Telegram credential in n8n
1. In the n8n UI: Settings (gear icon) → Credentials → Add Credential
2. Search "Telegram" → paste your bot token (same one from `.env`)
3. Save it, name it something like "YEX SEO Bot Telegram"

### 7. Import the RSS workflow template
1. In n8n: Workflows → Import from File
2. Select `n8n_workflows/rss_monitor.json`
3. Open the imported workflow, click the **"Send Telegram Alert"** node
4. In the Credential dropdown, select the Telegram credential you just created (replaces the placeholder)
5. Click **Save**, then toggle **Active** (top right) to turn it on

### 8. Test it
Click **"Execute Workflow"** manually (bottom of canvas) to run it once immediately instead of waiting 15 minutes. Watch the node-by-node execution — green checkmarks mean success, red means a node failed and you can click it to see exactly what data it had and what error occurred. This is the debugging improvement over raw Python logs.

You should get Telegram alerts within a minute if there's new news.

## Replicating the pattern for other modules

The RSS workflow is the template. Every other module follows the same shape:

```
Schedule Trigger → Fetch data → Normalize → Dedup check → IF new 
  → Mark seen → Interpret (POST /interpret) → IF not skip → Telegram → Log alert
```

**Market anomalies:** Replace the RSS nodes with an HTTP Request node hitting `https://api.coingecko.com/api/v3/coins/markets`. Add a Code node to compute the 24h change and volume comparison (or call new `/price/record` and `/price/baseline` endpoints I built into the service for this). Same `/interpret` and Telegram pattern after.

**Reddit trends:** n8n doesn't have a native Reddit node, so use an HTTP Request node against Reddit's public JSON API (`https://www.reddit.com/r/cryptocurrency/hot.json`) with a User-Agent header, or install the community Reddit node.

**Google Trends:** No clean API exists (pytrends is unofficial and scrapes Google). Easiest: keep this one as a small scheduled Python script that POSTs its findings to `/interpret` — no need to force everything into n8n if a source doesn't have a clean HTTP API.

**GSC performance:** Google Search Console has official OAuth — use n8n's HTTP Request node with OAuth2 credentials (n8n supports Google OAuth natively), call the `searchanalytics.query` endpoint directly. This is actually easier in n8n than the Python OAuth flow I originally wrote.

**Daily digest:** A single Cron Trigger (07:00 UTC) → HTTP GET `/alerts/recent?hours=24` → HTTP POST `/digest` → Telegram send.

I can build out any of these next — tell me which module to do next and I'll hand you the importable JSON like I did for RSS.

## Tuning without touching code

This is where the hybrid setup pays off. To change how often RSS runs, open the workflow, click the Schedule Trigger node, change "15" to whatever you want, save. No redeploying, no SSH.

To change Claude's interpretation strictness (what counts as noise), that's still in `modules/intelligence.py` on the Python side — edit the prompt, then:
```bash
docker compose restart intelligence
```

## Monitoring both services

```bash
# n8n logs
docker compose logs -f n8n

# Python service logs
docker compose logs -f intelligence

# Both
docker compose logs -f
```

n8n also keeps an **Executions** tab in its UI showing every run of every workflow, with full input/output at each node — much richer than the systemd journal you'd get from the pure-Python version.

## Cost / resource note

Running both containers adds maybe 300-400MB RAM overhead vs the bare Python version. An `e2-small` (2GB RAM) handles this fine. If your VM is an `e2-micro` (1GB), consider upgrading — n8n alone wants ~250MB minimum.
