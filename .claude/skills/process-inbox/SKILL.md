# Skill: Process Inbox

Process all pending items in the AI Employee vault's `Needs_Action/` folder.

## When to Use
Invoke this skill with `/process-inbox` to process all pending action items that watchers have queued up.

## Instructions

### Step 1: Read the Rules
Read `AI_Employee_Vault/Company_Handbook.md` to understand current policies on communication, financial thresholds, and approval requirements.

### Step 2: Scan for Pending Items
List all `.md` files in `AI_Employee_Vault/Needs_Action/`. If the folder is empty, report "No items to process" and update the dashboard.

### Step 3: Assess Complexity
For each file, **before acting**, assess whether the item requires multiple steps:
- **Multi-step items** (2+ distinct actions needed): invoke `/create-plan` to generate a Plan.md first, then follow the plan
- **Simple items** (single action like categorize, file, or acknowledge): process directly without a plan

**Always create a plan for:** `type: task`, emails with action items requiring follow-up steps, WhatsApp messages needing multi-step responses.
**Process directly without a plan for:** `type: file_drop` (simple categorization), `type: linkedin_post` (just move to Pending_Approval), simple acknowledgment emails, simple WhatsApp reads.

### Step 4: Process Each Item
For each file in `Needs_Action/`:

1. **Read the file** and parse its YAML frontmatter for `type`, `priority`, and `status`.
2. **Skip** any file where `status` is not `pending`.
3. **Determine the action** based on the `type` field:

| Type | Action |
|------|--------|
| `file_drop` | Review the file content preview, categorize it, and summarize what it contains |
| `email` | Assess complexity: if it has action items or requires multi-step follow-up, invoke `/create-plan` first. Otherwise, draft a response following handbook communication guidelines. **For known contacts:** call the `send_email` MCP tool to send the reply directly (use `in_reply_to` with the `gmail_id` from frontmatter for threading). **For new/unknown contacts:** call the `draft_email` MCP tool to save a draft in Gmail, then create an approval request in `Pending_Approval/` — do NOT call `send_email` until the human approves. Include the drafted response text in the approval file so the human can review it. |
| `task` | **Always** invoke `/create-plan` to generate a structured Plan.md in `Plans/` with step-by-step actions, approval gates, and resource links. |
| `request` | Evaluate complexity: if multi-step, invoke `/create-plan`. Otherwise, act directly or escalate. |
| `whatsapp_message` | Assess complexity: if it requires multi-step response or follow-up actions, invoke `/create-plan` first. Otherwise, read the message content and assess urgency. Draft an appropriate response following handbook communication guidelines. If the sender is a new/unknown contact, create an approval request in `Pending_Approval/` before any reply is sent. Include the drafted response text in the approval file so the human can review it. *(WhatsApp is read-only — no sending tools available.)* |
| `linkedin_post` | This is a LinkedIn post draft. If found in Needs_Action (unusual), move it to `Pending_Approval/` for human review before publishing. Do not publish directly. |
| `facebook_comment` | A comment on the Facebook Page. Read the comment and post context. Draft an appropriate reply following handbook guidelines. For known contacts: use the `reply_to_comment` Facebook MCP tool. For new/unknown contacts: create an approval request in `Pending_Approval/` with the drafted reply. |
| `facebook_message` | A Messenger message to the Facebook Page. Assess urgency, draft response. For new contacts: create approval request. Log the action. |
| `facebook_mention` | The page was mentioned/tagged. Assess context and draft appropriate engagement response. Create approval request if needed. |
| `facebook_post` | This is a Facebook post draft. If found in Needs_Action (unusual), move it to `Pending_Approval/` for human review before publishing. |
| *(other)* | Assess complexity: if multi-step, invoke `/create-plan`. Otherwise, summarize the content and recommend next steps. |

4. **If `/create-plan` was invoked**, the plan file is now in `Plans/`. The source file's status is updated to `plan_created`. Continue to the next item — plan execution happens in subsequent processing cycles.

5. **Check approval requirements** per the Company Handbook:
   - Payment over $100 → create approval request in `Pending_Approval/`
   - New contact communication → create approval request
   - Personal account actions → create approval request

6. **For items needing approval:**
   - Create a file in `AI_Employee_Vault/Pending_Approval/` with:
     ```
     ---
     type: approval_request
     original_file: <filename>
     requested_action: <what you want to do>
     reason: <why approval is needed>
     timestamp: <ISO 8601>
     status: pending
     ---
     ```
   - Update the original file's status to `awaiting_approval`

7. **For items you can act on directly:**
   - Execute the action (create response, file document, etc.)
   - Move the original file from `Needs_Action/` to `AI_Employee_Vault/Done/`

### Step 5: Log Everything
For each item processed, append an entry to `AI_Employee_Vault/Logs/YYYY-MM-DD.md`:
```
## HH:MM:SS - Processed: <filename>
- **Type:** <type>
- **Priority:** <priority>
- **Action Taken:** <description>
- **Result:** <success/pending_approval/error>
```

If the log file for today doesn't exist, create it with a header:
```
# Activity Log - YYYY-MM-DD
```

### Step 6: Update Dashboard
After processing all items, invoke the `update-dashboard` skill or manually update `AI_Employee_Vault/Dashboard.md` with current counts and recent activity.

## Example Run
```
Processing 3 items in Needs_Action/...

1. FILE_20260220_143022_report.pdf.md
   Type: file_drop | Priority: medium
   Action: Reviewed content, categorized as quarterly report
   Result: Moved to Done/

2. FILE_20260220_150100_invoice.md
   Type: invoice | Amount: $250
   Action: Amount exceeds $100 threshold — created approval request
   Result: Moved to Pending_Approval/

3. FILE_20260220_151500_notes.txt.md
   Type: file_drop | Priority: low
   Action: Summarized content, no further action needed
   Result: Moved to Done/

Dashboard updated. 2 completed, 1 pending approval.
```
