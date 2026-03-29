# Architecture - Personal AI Employee

## System Design

The Personal AI Employee is a **multi-threaded autonomous agent** that uses an Obsidian vault as its single source of truth. It follows the **Read → Think → Plan → Act** reasoning loop for decision-making.

At the Platinum tier, the system operates in two zones:
- **Cloud Agent** — Always-on Oracle Cloud VM running via Gemini free API. Monitors, processes, and drafts actions 24/7. Never sends or executes directly.
- **Local Agent** — Runs on the developer's machine with full Claude Opus. Approves drafts, sends emails, publishes posts, and manages the Dashboard.

## Data Flow (Platinum — Cloud + Local)

```
┌──────────────────────────────────────────────────────────────────────┐
│                        INPUT CHANNELS                                │
│                                                                      │
│  Gmail API    WhatsApp Web    Facebook    Instagram    Twitter   FS   │
│     │              │             │            │           │      │    │
│     ▼              ▼             ▼            ▼           ▼      ▼    │
│  gmail_watcher  whatsapp    fb_watcher   ig_watcher  tw_watcher fs   │
└──────┬────────────┬────────────┬────────────┬───────────┬───────┬────┘
       │            │            │            │           │       │
       ▼            ▼            ▼            ▼           ▼       ▼
  ┌────────────────────────────────────────────────────────────────┐
  │                      Needs_Action/                              │
  │          (Markdown files with YAML frontmatter)                 │
  └───────────────────────────┬────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Claim-by-Move    │
                    │  _claim_file()    │
                    └────┬─────────┬────┘
                         │         │
              ┌──────────▼──┐  ┌──▼──────────────┐
              │ In_Progress/ │  │ In_Progress/     │
              │ cloud/       │  │ local/           │
              └──────┬───────┘  └──┬──────────────┘
                     │             │
          ┌──────────▼──┐  ┌──────▼──────────────┐
          │ CLOUD AGENT  │  │ LOCAL AGENT          │
          │ (Gemini API) │  │ (Claude Opus)        │
          │              │  │                      │
          │ - Draft only │  │ - Full execution     │
          │ - No sending │  │ - Send emails        │
          │ - Creates    │  │ - Publish posts      │
          │   approvals  │  │ - Create invoices    │
          │ - Writes to  │  │ - Merge Dashboard    │
          │   Updates/   │  │ - Process approvals  │
          └──────┬───────┘  └──────┬──────────────┘
                 │                 │
                 ▼                 ▼
  ┌────────────────────────────────────────────────────────────────┐
  │                   Pending_Approval/                             │
  │            (Human reviews in Obsidian)                         │
  └───────────────────────────┬────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Human Decision    │
                    └────┬─────────┬────┘
                         │         │
              ┌──────────▼──┐  ┌──▼──────────┐
              │  Approved/   │  │  Rejected/   │
              └──────┬───────┘  └─────────────┘
                     │
                     ▼
  ┌────────────────────────────────────────────────────────────────┐
  │                 OUTPUT EXECUTION (Local Only)                   │
  │                                                                │
  │  MCP: Gmail Sender ──── send_email / draft_email               │
  │  MCP: Facebook ──────── post_to_facebook / reply_to_comment    │
  │  MCP: Instagram ─────── post_to_instagram / reply_to_comment   │
  │  MCP: Twitter ───────── post_tweet / reply_to_tweet            │
  │  MCP: Odoo ──────────── create_invoice / create_contact        │
  │  Playwright: LinkedIn ── publish post via browser automation   │
  │  ApprovedEmailSender ── auto-send approved email responses     │
  └───────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────────────┐
  │  Done/ ──── archived items                                     │
  │  Logs/ ──── .md (human) + .json (machine JSONL)               │
  │  Dashboard.md ──── live status (Local single-writer)           │
  │  Briefings/ ──── CEO weekly reports                            │
  └────────────────────────────────────────────────────────────────┘
```

## Claim-by-Move Rule

Prevents double-work when both Cloud and Local agents are running:

```
File arrives in Needs_Action/
        │
        ▼
  ┌─────────────────────────────┐
  │ Agent calls _claim_file()   │
  │                             │
  │ 1. Check: does other agent  │
  │    already have this file   │
  │    in In_Progress/<other>/? │
  │                             │
  │ 2. NO → Move file to       │
  │    In_Progress/<self>/      │
  │    (atomically claimed)     │
  │                             │
  │ 3. YES → Skip this file    │
  └─────────────────────────────┘
```

## Single-Writer Dashboard

Prevents merge conflicts between Cloud and Local agents:

```
Cloud Agent                          Local Agent
    │                                    │
    │  Writes update files to            │  Reads Updates/*.md
    │  AI_Employee_Vault/Updates/        │  Merges into Dashboard.md
    │                                    │  Deletes processed updates
    │                                    │
    ▼                                    ▼
Updates/cloud_update_001.md    →    Dashboard.md (merged)
Updates/cloud_update_002.md    →    (deleted after merge)
```

Only the Local agent (`AGENT_MODE=local`) calls `_merge_dashboard_updates()`.

## Thread Model

The orchestrator runs up to 12 threads:

| Thread | Component | Role | Required |
|--------|-----------|------|----------|
| Main | `processing_loop()` | Invokes Claude processor every N seconds | Yes |
| Daemon | `FileSystemWatcher` | Monitors Inbox/ via watchdog polling | Yes |
| Daemon | `GmailWatcher` | Polls Gmail API for unread important emails | If credentials.json exists |
| Daemon | `WhatsAppWatcher` | Monitors WhatsApp Web via Playwright | If playwright installed |
| Daemon | `LinkedInPoster` | Watches Approved/ for linkedin_post files | If playwright installed |
| Daemon | `FacebookWatcher` | Monitors Facebook Page comments/messages | If FACEBOOK_ACCESS_TOKEN set |
| Daemon | `FacebookPoster` | Publishes approved Facebook posts | If FACEBOOK_ACCESS_TOKEN set |
| Daemon | `InstagramWatcher` | Monitors Instagram comments | If IG tokens set |
| Daemon | `InstagramPoster` | Publishes approved Instagram posts | If IG tokens set |
| Daemon | `TwitterWatcher` | Monitors Twitter/X mentions | If TWITTER_API_KEY set |
| Daemon | `TwitterPoster` | Publishes approved tweets | If TWITTER_API_KEY set |
| Daemon | `ApprovedEmailSender` | Auto-sends approved email responses | Local agent only |

All daemon threads are optional — the system degrades gracefully if dependencies are missing.

### Thread Health Monitoring

```
Thread dies → Health monitor detects → Auto-restart (max 5 attempts)
                                        │
                                        ▼
                               Exceeded max? → Log error, stop retrying
```

## Error Recovery

```
Thread dies → Health monitor detects → Auto-restart (max 5 attempts)
API call fails → @with_retry decorator → Exponential backoff (2s → 4s → 8s → ... → 60s max)
Browser crash → Playwright reconnect → Re-authenticate if needed
Cloud VM OOM → 1GB swap file absorbs spikes → systemd auto-restart on failure
Gemini quota → 429 error → Exponential backoff → Resume when quota resets
```

## MCP (Model Context Protocol) Servers

5 MCP servers expose tools that Claude Code can call directly during processing:

```
.mcp.json
├── gmail-sender       → send_email, draft_email, list_drafts
├── facebook-manager   → post_to_facebook, get_page_insights, list_page_posts,
│                        reply_to_comment, get_page_summary
├── instagram-manager  → post_to_instagram, get_instagram_profile,
│                        list_instagram_media, reply_to_instagram_comment,
│                        get_instagram_insights
├── twitter-manager    → post_tweet, get_twitter_profile, list_recent_tweets,
│                        search_mentions, reply_to_tweet
└── odoo-accounting    → create_invoice, list_invoices, get_invoice,
                         create_contact, list_contacts, get_account_summary,
                         get_ceo_briefing_data
```

## Cloud Architecture (Platinum)

```
┌─────────────────────────────────────────────────┐
│           Oracle Cloud VM (1GB RAM)              │
│                                                  │
│  systemd: ccr-router.service                     │
│  ├── Claude Code Router (@nicepkg/ccr)           │
│  └── Proxies to Google Gemini API (free tier)    │
│                                                  │
│  systemd: ai-employee.service                    │
│  ├── orchestrator.py (AGENT_MODE=cloud)          │
│  ├── Gmail watcher (monitors inbox)              │
│  ├── File watcher (monitors Inbox/)              │
│  └── Claude processor (drafts via Gemini)        │
│                                                  │
│  1GB swap file (prevents OOM)                    │
│  Git cron (vault sync every 5 min)               │
└──────────────────┬──────────────────────────────┘
                   │
                   │ Git push/pull (every 5 min)
                   │
┌──────────────────▼──────────────────────────────┐
│           Local Machine                          │
│                                                  │
│  orchestrator.py (AGENT_MODE=local)              │
│  ├── All watchers (Gmail, FB, IG, X, WA, FS)    │
│  ├── All posters (FB, IG, X, LinkedIn)           │
│  ├── ApprovedEmailSender                         │
│  ├── Claude processor (Opus — full power)        │
│  └── Dashboard merger (single-writer)            │
│                                                  │
│  Obsidian (human reviews Pending_Approval/)      │
│  Docker: Odoo 19 + PostgreSQL 16                 │
└─────────────────────────────────────────────────┘
```

## Ralph Wiggum Loop (Autonomous Task Completion)

For complex tasks requiring multiple processing cycles:

```
1. Claude processes task file
2. Attempts to exit
3. Stop hook checks: is task file in Done/?
4. NO → re-inject prompt, loop continues
5. YES → allow exit
6. Safety: max 10 iterations (configurable via RALPH_MAX_ITERATIONS)
```

## Vault Structure

```
AI_Employee_Vault/
├── Inbox/              ← Watcher input (file drops)
├── Needs_Action/       ← Processing queue (all watchers write here)
├── In_Progress/        ← Claim-by-move work zone (Platinum)
│   ├── cloud/          ← Files claimed by Cloud agent
│   └── local/          ← Files claimed by Local agent
├── Updates/            ← Cloud dashboard updates (Platinum, single-writer)
├── Plans/              ← Multi-step plans generated by Claude
├── Pending_Approval/   ← Approval gate (human reviews here)
├── Approved/           ← Ready for execution
├── Rejected/           ← Declined items
├── Done/               ← Completed archive (30+ processed)
├── Logs/               ← .md (human) + .json (machine JSONL) logs
├── Briefings/          ← CEO weekly/monthly briefings
├── Company_Handbook.md ← Rules of engagement
├── Business_Goals.md   ← KPIs and targets
└── Dashboard.md        ← Live status (Local single-writer only)
```

## File Format Convention

All vault files use Markdown with YAML frontmatter:

```yaml
---
type: email | file_drop | whatsapp_message | linkedin_post | facebook_post |
      instagram_post | twitter_post | facebook_comment | instagram_comment |
      twitter_mention | email_response | task
priority: high | medium | low
status: pending | plan_created | awaiting_approval | completed
[type-specific fields]
---

# Content here
```

## Tier Progression

| Tier | Features |
|------|----------|
| **Bronze** | File watcher + Claude processing + Obsidian vault |
| **Silver** | + Gmail watcher + WhatsApp monitor + LinkedIn poster + MCP email |
| **Gold** | + Facebook/Instagram/Twitter (Graph API + API v2) + Odoo ERP + CEO Briefing + 5 MCP servers |
| **Platinum** | + Cloud 24/7 (Gemini) + Work-Zone Specialization + Claim-by-Move + Single-Writer Dashboard + Auto Email Sender |
