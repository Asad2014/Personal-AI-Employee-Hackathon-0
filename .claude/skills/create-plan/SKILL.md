# Skill: Create Plan

Generate a structured Plan.md file for complex or multi-step tasks in the AI Employee vault.

## When to Use
Invoke this skill with `/create-plan` when processing an item from `Needs_Action/` that requires 2 or more steps to complete. This implements the **Read → Think → Plan → Act** reasoning loop.

## Triggers
Create a plan when:
- `type: task` — always create a plan
- `type: email` with action items or follow-ups that require multiple steps
- `type: whatsapp_message` with multi-step response needs
- Any item that requires coordinating across multiple vault folders or approval gates
- Any item where the action is non-trivial (more than a simple categorize-and-file)

## Instructions

### Step 1: Read the Source Item
Read the file from `AI_Employee_Vault/Needs_Action/` and parse its YAML frontmatter and body content. Understand what is being requested.

### Step 2: Read the Company Handbook
Read `AI_Employee_Vault/Company_Handbook.md` to determine:
- Which steps require human approval
- Financial thresholds that apply
- Communication guidelines relevant to the task
- Priority level and escalation rules

### Step 3: Analyze Complexity
Break the task into discrete steps. For each step, determine:
- What action is needed
- Whether it requires approval (per handbook rules)
- What resources or vault files are relevant
- Dependencies between steps (which steps must happen first)

### Step 4: Create the Plan File
Create a file in `AI_Employee_Vault/Plans/` named `PLAN_<description>_<YYYYMMDD_HHMMSS>.md` where `<description>` is a short snake_case summary of the task (e.g., `quarterly_report`, `vendor_reply`, `expense_review`).

Use this format:

```markdown
---
created: "<ISO 8601 timestamp>"
source_file: "<original filename from Needs_Action>"
status: in_progress
priority: <high/medium/low from source>
---

# Plan: <Short Title>

## Objective
<1-2 sentence summary of what needs to be accomplished>

## Source
- **File:** <source filename>
- **Type:** <type from frontmatter>
- **Priority:** <priority>
- **Received:** <timestamp>

## Steps
- [ ] Step 1: <description>
- [ ] Step 2: <description> **(REQUIRES APPROVAL)**
- [ ] Step 3: <description>
- [ ] Step 4: <description>

## Approval Required
- Step N: <reason approval is needed, per handbook rules>

## Resources
- [[Company_Handbook]] — <relevant section>
- <any other relevant vault files>

## Notes
<any additional context, constraints, or considerations>
```

### Step 5: Update the Source File
Update the original file in `Needs_Action/` to set `status: plan_created` so it is not reprocessed. Do NOT move it to `Done/` yet — it stays in `Needs_Action/` until the plan is fully executed.

### Step 6: Log the Plan Creation
Append an entry to today's log file in `AI_Employee_Vault/Logs/YYYY-MM-DD.md`:

```markdown
## HH:MM:SS - Plan Created: <plan filename>
- **Source:** <source filename>
- **Type:** <type>
- **Priority:** <priority>
- **Steps:** <number of steps>
- **Approval gates:** <number of steps requiring approval>
- **Result:** plan_created
```

If the log file for today doesn't exist, create it with a header:
```markdown
# Activity Log - YYYY-MM-DD
```

### Step 7: Update Dashboard
After creating the plan, update `AI_Employee_Vault/Dashboard.md` to reflect the new plan count and any items requiring attention.

## Example

Given a file `Needs_Action/FILE_20260228_100000_quarterly_report.md` with:
```yaml
---
type: task
priority: high
status: pending
---
Prepare the Q1 quarterly report. Gather sales data, compile metrics, draft executive summary, and send to leadership team for review.
```

The skill creates `Plans/PLAN_quarterly_report_20260228_100500.md`:
```markdown
---
created: "2026-02-28T10:05:00"
source_file: "FILE_20260228_100000_quarterly_report.md"
status: in_progress
priority: high
---

# Plan: Prepare Q1 Quarterly Report

## Objective
Gather data, compile metrics, and draft the Q1 quarterly report for leadership review.

## Source
- **File:** FILE_20260228_100000_quarterly_report.md
- **Type:** task
- **Priority:** high
- **Received:** 2026-02-28T10:00:00

## Steps
- [ ] Step 1: Gather Q1 sales data from available sources
- [ ] Step 2: Compile key performance metrics and summaries
- [ ] Step 3: Draft executive summary
- [ ] Step 4: Create final report document
- [ ] Step 5: Send report to leadership team **(REQUIRES APPROVAL)**

## Approval Required
- Step 5: Sending external communication to leadership requires human sign-off

## Resources
- [[Company_Handbook]] — Communication guidelines, escalation procedures

## Notes
- High priority task — should be completed promptly
- Final report must follow company communication tone guidelines
```
