# Personal AI Employee

An autonomous AI employee powered by Claude Code and Obsidian. It monitors your email, WhatsApp, file drops, and social media — then processes, plans, and acts on your behalf with human-in-the-loop approval gates. Integrates with Odoo ERP for accounting, Facebook/Instagram/Twitter for social media, and Gmail for email — all via MCP servers.

A real-time **Next.js dashboard** lets you approve/reject AI actions, monitor activity, and manage alerts — all from your browser.

---

## Dashboard (New)

A professional real-time control center built with **Next.js + FastAPI**.

### Features
- **Overview** — Live stats (pending, approved, done, in-progress), activity chart, alerts
- **Inbox** — All items awaiting Claude processing
- **Approvals** — One-click Approve / Reject for every AI-drafted action
- **Completed** — Full history of processed items
- **Activity Logs** — Structured audit log of every action
- **Alert Dismiss** — Remove resolved alerts directly from the dashboard
- **File Modal** — Click any item to read full content + metadata
- **Auto-refresh** — Data refreshes every 30 seconds

### Quick Start (Dashboard)
```bash
# Terminal 1 — Backend
source venv/bin/activate
cd dashboard/backend
pip install fastapi uvicorn python-multipart
python app.py               # runs on http://localhost:8000

# Terminal 2 — Frontend
cd dashboard/frontend
npm install
npm run dev                 # runs on http://localhost:3000
```

### Dashboard Tech Stack
| Component | Technology |
|-----------|-----------|
| Frontend | Next.js 16 (App Router) + TypeScript |
| Styling | Tailwind CSS |
| Backend | FastAPI + Uvicorn (Python) |
| Data Source | Obsidian Vault (live file reads) |

---

## Bronze Tier Features
*Estimated time: 8-12 hours*

- **Obsidian Vault** — Dashboard.md and Company_Handbook.md as single source of truth
- **One Watcher** — Gmail OR file system monitoring (your choice)
- **Vault Read/Write** — Claude Code reads from and writes to the vault
- **Basic Folder Structure** — Inbox/, Needs_Action/, Done/
- **Agent Skills** — All AI functionality implemented as Claude Code skills

## Silver Tier Features
*Estimated time: 20-30 hours — All Bronze requirements plus:*

- **Multiple Watchers** — Gmail + WhatsApp + LinkedIn running simultaneously
- **LinkedIn Auto-Posting** — Automatically drafts and posts to LinkedIn to generate leads
- **Plan.md Generation** — Claude reasoning loop creates structured multi-step plans
- **First MCP Server** — External action capability (e.g., sending emails via Gmail API)
- **Approval Workflow** — Human-in-the-loop gates for sensitive actions
- **Basic Scheduling** — Cron or Task Scheduler for timed operations
- **Agent Skills** — All AI functionality implemented as Claude Code skills

## Gold Tier: Autonomous Employee
*Estimated time: 40+ hours — All Silver requirements plus:*

1. **Full cross-domain integration** — Personal + Business operations unified
2. **Odoo Community ERP** — Self-hosted accounting system (Odoo 19+) integrated via MCP server using JSON-RPC APIs — invoicing, contacts, financial reports
3. **Facebook + Instagram integration** — Post messages and generate engagement summaries via Meta Graph API
4. **Twitter (X) integration** — Post messages and generate activity summaries via Twitter API v2
5. **Multiple MCP Servers** — Separate MCP servers for Gmail, Facebook, Instagram, Twitter, Odoo
6. **Weekly CEO Briefing** — Automated business and accounting audit combining Odoo financials + social media metrics + vault activity
7. **Error recovery and graceful degradation** — Exponential backoff, thread health monitoring, auto-restart
8. **Comprehensive audit logging** — Markdown + structured JSON (JSONL) logs for every action
9. **Ralph Wiggum Loop** — Autonomous re-execution loop for multi-step task completion (Stop hook pattern)
10. **Documentation** — Architecture diagrams and lessons learned
11. **Agent Skills** — All AI functionality implemented as Claude Code skills

## Platinum Tier: Always-On Cloud + Local Executive
*Estimated time: 60+ hours — All Gold requirements plus:*

1. **Run AI Employee on Cloud 24/7** — Always-on watchers + orchestrator + health monitoring on Oracle Cloud VM (or AWS/GCP). Oracle Cloud Free VMs recommended.
2. **Work-Zone Specialization (domain ownership)**
   - **Cloud owns:** Email triage + draft replies + social post drafts/scheduling (draft-only; requires Local approval before send/post)
   - **Local owns:** Approvals, WhatsApp session, payments/banking, and final send/post actions
3. **Delegation via Synced Vault**
   - Agents communicate by writing files into `/Needs_Action/`, `/Plans/`, `/Pending_Approval/`
   - Prevent double-work using `/In_Progress/<agent>/` claim-by-move rule
   - Single-writer rule for Dashboard.md — Cloud writes to `/Updates/`, Local merges
   - Vault sync via Git (recommended) or Syncthing
4. **Security rule** — Vault sync includes only markdown/state files. Secrets never sync (.env, tokens, WhatsApp sessions, banking credentials)
5. **Odoo on Cloud VM (24/7)** — With HTTPS, backups, and health monitoring; Cloud Agent uses Odoo MCP for draft-only actions; Local approves invoice posting/payments
6. **Platinum Demo (minimum passing gate)** — Email arrives while Local is offline → Cloud drafts reply + writes approval file → when Local returns, user approves → Local executes send via MCP → logs → moves to /Done

---

## Architecture

```
orchestrator.py               ← Main entry point (spawns 12 background threads)
├── watchers/
│   ├── base_watcher.py        ← Abstract base class for all watchers
│   ├── filesystem_watcher.py  ← Monitors Inbox/ for file drops
│   ├── gmail_watcher.py       ← Monitors Gmail via API
│   ├── whatsapp_watcher.py    ← Monitors WhatsApp Web via Playwright
│   ├── linkedin_poster.py     ← Publishes approved LinkedIn posts (Playwright)
│   ├── facebook_watcher.py    ← Monitors Facebook Page comments/messages
│   ├── facebook_poster.py     ← Publishes approved Facebook posts
│   ├── instagram_watcher.py   ← Monitors Instagram comments
│   ├── instagram_poster.py    ← Publishes approved Instagram posts
│   ├── twitter_watcher.py     ← Monitors Twitter/X mentions
│   ├── twitter_poster.py      ← Publishes approved tweets
│   └── approved_email_sender.py ← Auto-sends approved emails (Local only)
├── claude_processor.py         ← Invokes Claude Code CLI with claim-by-move
├── mcp_servers/
│   ├── gmail_sender.py         ← MCP: send/draft emails (OAuth2)
│   ├── facebook_mcp.py         ← MCP: post, insights, comments
│   ├── instagram_mcp.py        ← MCP: post photos, insights, comments
│   ├── twitter_mcp.py          ← MCP: tweet, profile, mentions
│   └── odoo_mcp.py             ← MCP: invoicing, contacts, reports
├── utils/
│   ├── audit_logger.py         ← Structured JSON audit logging
│   ├── retry_handler.py        ← Exponential backoff decorator
│   └── ralph_wiggum.py         ← Autonomous task completion loop
├── dashboard/
│   ├── backend/
│   │   └── app.py              ← FastAPI REST API (reads/writes vault)
│   └── frontend/
│       └── app/                ← Next.js dashboard (TypeScript + Tailwind)
├── .claude/
│   ├── skills/                 ← Agent skill definitions
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
├── deploy_gemini_router.sh     ← Cloud deployment script
├── ssh_to_cloud.sh             ← SSH into Oracle Cloud VM
└── AI_Employee_Vault/          ← Obsidian vault (single source of truth)
    ├── Inbox/                  ← Drop zone for new files
    ├── Needs_Action/           ← Items awaiting Claude processing
    ├── In_Progress/cloud/      ← Files claimed by Cloud agent
    ├── In_Progress/local/      ← Files claimed by Local agent
    ├── Plans/                  ← Multi-step action plans
    ├── Pending_Approval/       ← Actions needing human approval
    ├── Approved/               ← Human-approved actions
    ├── Rejected/               ← Declined actions
    ├── Done/                   ← Completed items (30+ processed)
    ├── Briefings/              ← CEO Briefing reports
    ├── Logs/                   ← Activity logs (.md + .json)
    ├── Company_Handbook.md     ← Rules of engagement
    └── Dashboard.md            ← Live status dashboard
```

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install requests-oauthlib
playwright install chromium
```

### 2. Odoo ERP Setup (Docker)
```bash
docker compose up -d
# Open http://localhost:8069 — create database, install Invoicing module
```

### 3. Configure Environment
Copy `.env.example` to `.env` and fill in your API keys:
```bash
FACEBOOK_ACCESS_TOKEN=...
FACEBOOK_PAGE_ID=...
INSTAGRAM_BUSINESS_ACCOUNT_ID=...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...
```

### 4. Run the Orchestrator
```bash
python3 orchestrator.py
```

### 5. Open the Dashboard
```bash
# Backend
cd dashboard/backend && python app.py

# Frontend (new terminal)
cd dashboard/frontend && npm run dev
# → http://localhost:3000
```

---

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
| `TWITTER_API_KEY` | Twitter API Key | — |
| `TWITTER_API_SECRET` | Twitter API Secret | — |
| `TWITTER_ACCESS_TOKEN` | Twitter Access Token | — |
| `TWITTER_ACCESS_TOKEN_SECRET` | Twitter Access Token Secret | — |
| `ODOO_URL` | Odoo instance URL | `http://localhost:8069` |
| `ODOO_DB` | Odoo database name | `odoo` |
| `AGENT_MODE` | `cloud` (draft-only) or `local` (execute) | `local` |
| `GOOGLE_API_KEY` | Google Gemini API key (for CCR) | — |

---

## Agent Skills

| Skill | Command | Description |
|-------|---------|-------------|
| CEO Briefing | `/ceo-briefing` | Weekly business report (Odoo + social + vault) |
| Process Inbox | `/process-inbox` | Process all pending items in Needs_Action/ |
| Update Dashboard | `/update-dashboard` | Refresh Dashboard.md with current stats |
| Create Plan | `/create-plan` | Generate a multi-step plan for complex tasks |
| LinkedIn Post | `/linkedin-post "topic"` | Draft a LinkedIn post |
| Facebook Post | `/facebook-post "topic"` | Draft a Facebook page post |
| Instagram Post | `/instagram-post "topic"` | Draft an Instagram photo post |
| Twitter Post | `/twitter-post "topic"` | Draft a tweet (max 280 chars) |

---

## Workflow

```
Input → Queue → Process → Approve → Execute → Archive → Report

1. INPUT      Watchers detect events (email, message, comment, file drop)
2. QUEUE      Create .md file in Needs_Action/ with YAML frontmatter
3. PROCESS    Claude reads item, assesses complexity, creates plan or acts
4. APPROVE    Sensitive actions → Pending_Approval/ → Dashboard approval
5. EXECUTE    Approved actions executed (emails sent, posts published, invoices created)
6. ARCHIVE    Completed items → Done/, actions logged in Logs/
7. REPORT     Dashboard updated, CEO Briefing generated weekly
```

---

## Cloud Deployment (Platinum)

```bash
# SSH into Oracle Cloud VM
./ssh_to_cloud.sh

# Check service status
sudo systemctl status ai-employee ccr-router

# View live logs
sudo journalctl -u ai-employee -f --no-pager -n 50
```

Vault syncs automatically via Git cron every 5 minutes between cloud and local.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Brain (Local) | Claude Code (Opus) |
| AI Brain (Cloud) | Claude Code Router → Google Gemini API |
| Dashboard Frontend | Next.js 16 + TypeScript + Tailwind CSS |
| Dashboard Backend | FastAPI + Uvicorn (Python) |
| Knowledge Base | Obsidian (Markdown vault) |
| Email | Gmail API v1 + OAuth2 |
| Facebook | Meta Graph API v21.0 |
| Instagram | Meta Graph API v21.0 |
| Twitter/X | Twitter API v2 + OAuth 1.0a |
| LinkedIn | Playwright (browser automation) |
| WhatsApp | Playwright (browser automation) |
| Accounting | Odoo 19 Community (Docker) + XML-RPC |
| Database | PostgreSQL 16 |
| MCP Protocol | 5 custom MCP servers |
| Cloud | Oracle Cloud Free Tier |
| Deployment | systemd + Git-based vault sync |
| Language | Python 3.12+ |

---

## License

Private project — Panaversity Hackathon 0 submission.
