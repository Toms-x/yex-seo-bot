# Pure Python Deployment (systemd, no Docker)

## Setup on GCP VM

### 1. SSH in and install Python
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv git
```

### 2. Upload/clone the bot, then install deps
```bash
cd ~/yex_seo_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure API keys
```bash
cp .env.example .env
nano .env
```
Fill in `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `OPENAI_API_KEY` at minimum.

### 4. Test one module
```bash
source venv/bin/activate
python -m modules.rss_monitor
```
Wait for a Telegram message.

### 5. Install as systemd service
```bash
nano yex-seo-bot.service   # replace YOUR_USERNAME with `whoami` output

sudo cp yex-seo-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable yex-seo-bot
sudo systemctl start yex-seo-bot
sudo systemctl status yex-seo-bot
```

### 6. Watch logs
```bash
journalctl -u yex-seo-bot -f
tail -f ~/yex_seo_bot/logs/bot.log
```

## Google Search Console setup

1. GCP Console → APIs & Services → Library → enable **Google Search Console API**
2. Credentials → Create OAuth client ID → Desktop app → download JSON
3. Rename to `gsc_credentials.json`, place in `config/`
4. Verify domain ownership in GSC if not already done
5. Set `GSC_SITE_URL` in `.env` (e.g., `sc-domain:yex.com`)
6. First run: `python -m modules.gsc_performance` — opens browser for auth, caches token after

## Roll-out plan

**Week 1:** RSS + market anomalies + daily digest only
**Week 2:** Add GSC (highest-value module)
**Week 3:** Add Reddit + Google Trends
**Week 4:** Add competitor watch + unlocks

## Tuning

Edit `config/settings.py`:
- `PRICE_CHANGE_THRESHOLD_24H` — raise if too many market alerts
- Reddit `post.score < 200` threshold in `reddit_monitor.py`
- RSS feed list — trim if overwhelming

## Cost estimate

- GCP e2-small: ~$13/mo (or free tier e2-micro: $0)
- Anthropic API: ~$5-15/mo at expected volume
- Total: under $30/mo
