# Skill: Update Dashboard

Update the AI Employee Dashboard with current vault status, file counts, and recent activity.

## When to Use
Invoke this skill with `/update-dashboard` to refresh the dashboard. Also called automatically after processing inbox items.

## Instructions

### Step 1: Count Files in Each Folder
List files in each vault folder and count them (exclude hidden files and `.obsidian/`):

- `AI_Employee_Vault/Inbox/` — files awaiting watcher processing
- `AI_Employee_Vault/Needs_Action/` — items awaiting Claude processing
- `AI_Employee_Vault/Pending_Approval/` — items awaiting human approval
- `AI_Employee_Vault/Approved/` — approved items ready to execute
- `AI_Employee_Vault/Done/` — completed items
- `AI_Employee_Vault/Plans/` — active plans
- `AI_Employee_Vault/Rejected/` — rejected items
- `AI_Employee_Vault/Logs/` — log files

### Step 2: Read Recent Logs
Read today's log file (`AI_Employee_Vault/Logs/YYYY-MM-DD.md`) if it exists. Extract the last 5 activity entries for the "Recent Activity" section.

### Step 3: Identify Alerts
Flag any of these conditions as alerts:
- Files in `Needs_Action/` older than 4 hours (stale items)
- Files in `Pending_Approval/` older than 24 hours (awaiting human response)
- More than 10 items in any single folder (backlog warning)

### Step 4: Write the Dashboard
Overwrite `AI_Employee_Vault/Dashboard.md` with the following template, filling in real values:

```markdown
# AI Employee Dashboard

## Status
- **Last Updated:** <current ISO 8601 timestamp>
- **System Status:** Operational
- **Active Watchers:** 6 (File System, Gmail, LinkedIn, WhatsApp, Facebook Watcher, Facebook Poster)

## Folder Counts
| Folder | Count |
|--------|-------|
| Inbox | <count> |
| Needs Action | <count> |
| Pending Approval | <count> |
| Approved | <count> |
| Plans | <count> |
| Done | <count> |
| Rejected | <count> |
| Logs | <count> |

## Today's Activity

### Processed
- Files processed today: <count from log>
- Actions completed: <count>

### Pending
- Awaiting processing: <Needs_Action count>
- Awaiting approval: <Pending_Approval count>

## Recent Activity
<last 5 log entries, or "No activity logged today" if none>

## Alerts
<list of alerts, or "No alerts at this time">

---
*AI Employee v0.1 - Powered by Claude Code*
*Dashboard last refreshed: <timestamp>*
```

## Notes
- Always use the current real timestamp, never a placeholder
- If a log file doesn't exist for today, show "No activity logged today"
- Keep the dashboard concise — it should be scannable at a glance in Obsidian
