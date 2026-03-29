# Personal AI Employee

An autonomous AI employee powered by Claude Code and Obsidian. It monitors your email, WhatsApp, file drops, and social media — then processes, plans, and acts on your behalf with human-in-the-loop approval gates. Integrates with Odoo ERP for accounting, Facebook/Instagram/Twitter for social media, and Gmail for email — all via MCP servers.

**Tier: Platinum** — Always-on Cloud + Local Executive with Work-Zone Specialization.

## Platinum Tier Features

- **Cloud 24/7 Deployment** — Oracle Cloud VM running AI Employee as systemd service with auto-restart, health monitoring, and 1GB swap
- **Gemini Free API** — Claude Code Router proxies requests to Google Gemini API (free tier) for cloud processing
- **Work-Zone Specialization** — `AGENT_MODE=cloud` (draft-only, never sends) vs `AGENT_MODE=local` (approves and executes)
- **Claim-by-Move Rule** — Files move from `Needs_Action/` to `In_Progress/<agent>/` to prevent double-work between Cloud and Local agents
- **Single-Writer Dashboard** — Cloud writes to `Updates/`, only Local merges into `Dashboard.md` (prevents conflicts)
- **Approved Email Sender** — Local agent auto-sends approved emails from `Approved/` folder via Gmail API
- **Vault Sync** — Git-based sync between Cloud and Local (cron every 5 minutes)
- **Platinum Demo** — Email arrives → Cloud drafts reply + approval file → Human approves in Obsidian → Local sends via MCP → Done

## Gold Tier Features

- **Multi-Channel Monitoring** — Gmail, WhatsApp Web, Facebook, Instagram, Twitter, file system inbox — all running as background threads
- **Social Media Posting** — Facebook (Graph API), Instagram (Graph API), Twitter/X (API v2), LinkedIn (Playwright)
- **Odoo ERP Accounting** — Self-hosted Odoo 19 via Docker, invoicing, contacts, financial reports via XML-RPC
- **CEO Briefing** — Weekly automated business report combining Odoo financials + social media metrics + vault activity
- **Approval Workflow** — Sensitive actions (payments, new contacts, social posts) require human sign-off in Obsidian
- **Structured Planning** — Complex tasks get broken into multi-step plans with approval gates
- **Ralph Wiggum Loop** — Autonomous re-execution loop that keeps Claude running until complex tasks are fully complete
- **Audit Logging** — Both Markdown and structured JSON (JSONL) logs for every action
- **Error Recovery** — Exponential backoff retry, thread health monitoring, auto-restart (max 5 attempts)
- **5 MCP Servers** — Gmail, Facebook, Instagram, Twitter, Odoo — giving Claude direct tool access
- **Agent Skills** — Modular skills for every operation (`/ceo-briefing`, `/process-inbox`, `/facebook-post`, etc.)

## Architecture

```
orchestrator.py               ← Main entry point (spawns 10 background threads)
├── watchers/
│   ├── base_watcher.py        ← Abstract base class for all watchers
│   ├── filesystem_watcher.py  ← Monitors Inbox/ for file drops
│   ├── gmail_watcher.py       ← Monitors Gmail via API
│   ├── whatsapp_watcher.py    ← Monitors WhatsApp Web via Playwright
│   ├── linkedin_poster.py     ← Publishes approved LinkedIn posts (Playwright)
│   ├── facebook_watcher.py    ← Monitors Facebook Page comments/messages (Graph API)
│   ├── facebook_poster.py     ← Publishes approved Facebook posts (Graph API)
│   ├── instagram_watcher.py   ← Monitors Instagram comments (Graph API)
│   ├── instagram_poster.py    ← Publishes approved Instagram posts (Graph API)
│   ├── twitter_watcher.py     ← Monitors Twitter/X mentions (API v2)
│   ├── twitter_poster.py      ← Publishes approved tweets (API v2 + OAuth 1.0a)
│   └── approved_email_sender.py ← Auto-sends approved emails (Local agent only)
├── claude_processor.py         ← Invokes Claude Code CLI with AGENT_MODE + claim-by-move
├── mcp_servers/
│   ├── gmail_sender.py         ← MCP: send/draft emails (OAuth2)
│   ├── facebook_mcp.py         ← MCP: post, insights, comments (Graph API v21.0)
│   ├── instagram_mcp.py        ← MCP: post photos, insights, comments (Graph API)
│   ├── twitter_mcp.py          ← MCP: tweet, profile, mentions (API v2)
│   └── odoo_mcp.py             ← MCP: invoicing, contacts, reports (XML-RPC)
├── utils/
│   ├── audit_logger.py         ← Structured JSON audit logging
│   ├── retry_handler.py        ← Exponential backoff decorator
│   └── ralph_wiggum.py         ← Autonomous task completion loop
├── .claude/
│   ├── skills/                 ← Agent skill definitions (SKILL.md files)
│   │   ├── ceo-briefing/
│   │   ├── process-inbox/
│   │   ├── update-dashboard/
│   │   ├── create-plan/
│   │   ├── linkedin-post/
│   │   ├── facebook-post/
│   │   ├── instagram-post/
│   │   └── twitter-post/
│   └── hooks/
│       └── stop_hook.sh        ← Ralph Wiggum loop stop condition
├── docker-compose.yml          ← Odoo 19 + PostgreSQL 16
├── deploy_gemini_router.sh     ← Cloud deployment script (Gemini + CCR)
├── deploy_to_cloud.sh          ← Initial cloud VM setup script
├── ssh_to_cloud.sh             ← SSH into Oracle Cloud VM
├── upload_to_cloud.sh          ← Upload secrets to cloud VM
├── refresh_token.py            ← Gmail OAuth token refresh utility
└── AI_Employee_Vault/          ← Obsidian vault (single source of truth)
    ├── Inbox/                  ← Drop zone for new files
    ├── Needs_Action/           ← Items awaiting Claude processing
    ├── In_Progress/cloud/      ← Files claimed by Cloud agent (Platinum)
    ├── In_Progress/local/      ← Files claimed by Local agent (Platinum)
    ├── Updates/                ← Cloud dashboard updates (Platinum)
    ├── Plans/                  ← Multi-step action plans
    ├── Pending_Approval/       ← Actions needing human approval
    ├── Approved/               ← Human-approved actions
    ├── Rejected/               ← Declined actions
    ├── Done/                   ← Completed items (30+ processed)
    ├── Briefings/              ← CEO Briefing reports
    ├── Logs/                   ← Activity logs (.md + .json)
    ├── Company_Handbook.md     ← Rules of engagement
    ├── Business_Goals.md       ← KPIs, targets, alert thresholds
    └── Dashboard.md            ← Live status dashboard (Local single-writer)
```

## Integration Map

```
                    ┌─────────────────────────────┐
                    │      Claude Code (Brain)      │
                    │   Processes, Plans, Decides    │
                    └──────────┬──────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
        ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
        │  Watchers  │   │MCP Servers│   │  Skills   │
        │ (Monitor)  │   │ (Act)     │   │ (Commands)│
        └─────┬──────┘   └─────┬─────┘   └─────┬─────┘
              │                │                │
    ┌─────────┼────────┐  ┌───┼────┐    ┌──────┼──────┐
    │   │   │   │   │  │  │  │  │  │    │  │   │   │  │
   Gmail WA  FB  IG  X FS GM FB IG OD  CEO INB PLN PST
```

**Watchers:** Gmail, WhatsApp, Facebook, Instagram, Twitter, FileSystem
**MCP Servers:** Gmail Sender, Facebook Manager, Instagram Manager, Twitter Manager, Odoo Accounting
**Skills:** /ceo-briefing, /process-inbox, /update-dashboard, /create-plan, /linkedin-post, /facebook-post, /instagram-post, /twitter-post

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install requests-oauthlib    # For Twitter OAuth 1.0a
playwright install chromium       # For LinkedIn & WhatsApp
```

### 2. Odoo ERP Setup (Docker)
```bash
docker compose up -d
# Open http://localhost:8069
# Create database: name=odoo, email=admin, password=admin
# Install Invoicing + CRM modules
```

### 3. Facebook + Instagram Setup
1. Create a Meta App at developers.facebook.com
2. Create a Facebook Page
3. Generate Page Access Token with permissions: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `pages_messaging`, `read_insights`, `instagram_basic`, `instagram_content_publish`, `instagram_manage_comments`
4. Link Instagram Business Account to Facebook Page
5. Set `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`, `INSTAGRAM_BUSINESS_ACCOUNT_ID` in `.env`

### 4. Twitter/X Setup
1. Create Developer account at developer.x.com
2. Create an app with Read+Write permissions
3. Generate API Key, API Secret, Access Token, Access Token Secret
4. Set `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET` in `.env`

### 5. Gmail Setup
1. Enable Gmail API at console.cloud.google.com
2. Create OAuth 2.0 credentials (Desktop app)
3. Download `credentials.json` to project root
4. First run opens browser for Google authorization

### 6. Run the Orchestrator
```bash
python3 orchestrator.py
```

The orchestrator starts all watchers as background threads and runs the Claude processing loop on the main thread.

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `VAULT_PATH` | Path to Obsidian vault | `./AI_Employee_Vault` |
| `PROCESS_INTERVAL` | Processing loop interval (seconds) | `120` |
| `RALPH_MAX_ITERATIONS` | Max autonomous loop iterations | `10` |
| `GMAIL_CREDENTIALS_PATH` | Gmail OAuth credentials | `credentials.json` |
| `FACEBOOK_ACCESS_TOKEN` | Facebook/Instagram Page Access Token | — |
| `FACEBOOK_PAGE_ID` | Facebook Page ID | — |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Instagram Business Account ID | — |
| `TWITTER_API_KEY` | Twitter API Key (Consumer Key) | — |
| `TWITTER_API_SECRET` | Twitter API Secret (Consumer Secret) | — |
| `TWITTER_ACCESS_TOKEN` | Twitter Access Token | — |
| `TWITTER_ACCESS_TOKEN_SECRET` | Twitter Access Token Secret | — |
| `ODOO_URL` | Odoo instance URL | `http://localhost:8069` |
| `ODOO_DB` | Odoo database name | `odoo` |
| `ODOO_USER` | Odoo username | `admin` |
| `ODOO_PASSWORD` | Odoo password | `admin` |
| `LINKEDIN_HEADLESS` | LinkedIn browser headless mode | `true` |
| `WHATSAPP_HEADLESS` | WhatsApp browser headless mode | `true` |
| `AGENT_MODE` | Agent mode: `cloud` (draft-only) or `local` (approve+send) | `local` |
| `ANTHROPIC_BASE_URL` | Claude Code Router URL (Gemini proxy) | — |
| `CLAUDE_CONFIG_DIR` | Alternate Claude config dir (for Gemini key) | — |
| `GOOGLE_API_KEY` | Google Gemini API key (for CCR) | — |

## Agent Skills

| Skill | Command | Description |
|-------|---------|-------------|
| CEO Briefing | `/ceo-briefing` | Generate weekly business report (Odoo + social + vault) |
| Process Inbox | `/process-inbox` | Process all pending items in Needs_Action/ |
| Update Dashboard | `/update-dashboard` | Refresh Dashboard.md with current stats |
| Create Plan | `/create-plan` | Generate a multi-step plan for complex tasks |
| LinkedIn Post | `/linkedin-post "topic"` | Draft a LinkedIn post |
| Facebook Post | `/facebook-post "topic"` | Draft a Facebook page post |
| Instagram Post | `/instagram-post "topic"` | Draft an Instagram photo post |
| Twitter Post | `/twitter-post "topic"` | Draft a tweet (max 280 chars) |

## Workflow

```
Input → Queue → Process → Approve → Execute → Archive → Report

1. INPUT      Watchers detect events (email, message, comment, file drop)
2. QUEUE      Create .md file in Needs_Action/ with YAML frontmatter
3. PROCESS    Claude reads item, assesses complexity, creates plan or acts
4. APPROVE    Sensitive actions → Pending_Approval/ for human review
5. EXECUTE    Approved actions executed (emails sent, posts published, invoices created)
6. ARCHIVE    Completed items → Done/, actions logged in Logs/
7. REPORT     Dashboard updated, CEO Briefing generated weekly
```

## Cloud Deployment (Platinum)

### Oracle Cloud VM Setup
```bash
# 1. SSH into your Oracle Cloud VM
ssh -i ~/.ssh/cloud_vm_key ubuntu@<VM_IP>

# 2. Run the deployment script
bash deploy_gemini_router.sh

# 3. Or deploy manually:
# Install Claude Code Router (Gemini proxy)
npm install -g @anthropic-ai/claude-code
npm install -g @nicepkg/claude-code-router

# Create systemd services
sudo systemctl enable ccr-router ai-employee
sudo systemctl start ccr-router ai-employee
```

### Vault Sync (Git-based)
```bash
# On cloud VM — cron job every 5 minutes
*/5 * * * * cd /home/ubuntu/AI_Employee_Vault && git pull --rebase && git add -A && git commit -m "cloud sync" && git push
```

### Health Check
```bash
# Check services
sudo systemctl status ccr-router ai-employee

# Check logs
sudo journalctl -u ai-employee -f --no-pager -n 50

# Check RAM + swap
free -h
```

## Demo Scenarios

1. **Platinum Demo (End-to-End)** — Email arrives → Cloud agent (Gemini) drafts reply + creates approval file → Git sync to local → Human approves in Obsidian → Local agent auto-sends via Gmail API → File archived to Done/
2. **Email Processing** — Important email arrives → Gmail watcher → Claude drafts reply → sends or creates approval
3. **Social Post** — `/facebook-post "AI trends"` → draft in Pending_Approval → human approves → auto-published to Facebook
4. **Instagram Post** — `/instagram-post "launch day"` → draft with image URL → approved → published via Graph API
5. **CEO Briefing** — `/ceo-briefing` → pulls Odoo revenue ($381K), Facebook metrics, vault activity → generates executive report
6. **Invoice Creation** — Odoo MCP creates invoice → logs action → updates dashboard
7. **Complex Task** — Multi-step task → Plan.md generated → Ralph Wiggum loop executes steps → approval gates honored
8. **File Drop** — Drop file in Inbox/ → watcher detects → Claude processes → archived to Done/

## Lessons Learned

### Technical
- **Graph API > Playwright for social media** — REST APIs are faster, more reliable, and don't need browser sessions. Used Graph API for Facebook and Instagram instead of Playwright.
- **MCP servers are powerful** — Giving Claude direct tool access (send email, create invoice, post to social) makes it truly autonomous rather than just advisory.
- **Token management is critical** — Facebook short-lived tokens expire in ~1 hour. Converting to long-lived/permanent Page tokens is essential for production.
- **OAuth 1.0a for Twitter** — Twitter v2 API uses OAuth 1.0a for write operations and Bearer tokens for read-only. Different auth for different operations.
- **Docker for self-hosted services** — Odoo via Docker Compose made setup reproducible and isolated from the host system.

### Architecture
- **Obsidian as the control plane** — Using markdown files with YAML frontmatter as the "database" makes everything human-readable and debuggable in Obsidian.
- **Watcher pattern works well** — Abstract BaseWatcher class with concrete implementations for each channel keeps code organized and extensible.
- **Approval workflow is essential** — Human-in-the-loop prevents embarrassing automated actions. The Pending_Approval → Approved flow is simple but effective.
- **Ralph Wiggum loop for persistence** — Re-executing Claude until a task is fully complete solves the "Claude gives up halfway" problem.
- **Work-Zone Specialization prevents conflicts** — Cloud agent drafts, Local agent executes. Claim-by-move prevents double-work. Single-writer Dashboard prevents merge conflicts.
- **Free API tier is viable for cloud** — Claude Code Router proxying to Gemini free API handles email processing, drafting, and planning without paid API credits.

### Business
- **Collection rate matters more than revenue** — Having $381K in invoices means nothing if collection rate is 0%. CEO Briefing highlighted this immediately.
- **Cross-platform presence needs consistency** — Managing Facebook, Instagram, Twitter, and LinkedIn from one system ensures regular posting across all platforms.
- **Automated monitoring catches things humans miss** — Overdue invoices, stale tasks, expired tokens — all surfaced automatically via alerts.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Brain (Local) | Claude Code (Opus) |
| AI Brain (Cloud) | Claude Code Router → Google Gemini API |
| Knowledge Base | Obsidian (Markdown vault) |
| Email | Gmail API + OAuth2 |
| Facebook | Meta Graph API v21.0 |
| Instagram | Meta Graph API v21.0 |
| Twitter/X | Twitter API v2 + OAuth 1.0a |
| LinkedIn | Playwright (browser automation) |
| WhatsApp | Playwright (browser automation) |
| Accounting | Odoo 19 Community (Docker) + XML-RPC |
| Database | PostgreSQL 16 (for Odoo) |
| MCP Protocol | 5 Model Context Protocol servers |
| Cloud | Oracle Cloud Free Tier (1GB RAM + 1GB swap) |
| Deployment | systemd services + Git-based vault sync |
| Language | Python 3.12+ |

## License

Private project — Panaversity Hackathon 0 submission.
