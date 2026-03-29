# Skill: LinkedIn Post

Generate a professional LinkedIn post and submit it for approval.

## When to Use
Invoke with `/linkedin-post` or `/linkedin-post "topic here"` to create a LinkedIn post draft about your business.

## Instructions

### Step 1: Read the Handbook
Read `AI_Employee_Vault/Company_Handbook.md` to understand the company's tone, communication guidelines, and branding.

### Step 2: Determine the Topic
- If the user provided a topic (e.g., `/linkedin-post "AI automation for small businesses"`), use that topic.
- If no topic was given, ask the user what the post should be about.

### Step 3: Generate the Post
Write a professional LinkedIn post following these guidelines:
- **Length:** 150-300 words
- **Tone:** Professional but approachable (follow handbook guidelines)
- **Structure:** Hook line, main content, call to action
- **Include:** 3-5 relevant hashtags at the end
- Do NOT include any emojis unless the handbook specifically encourages them

### Step 4: Save to Pending_Approval
Create a file in `AI_Employee_Vault/Pending_Approval/` named `LINKEDIN_POST_<YYYYMMDD_HHMMSS>.md` with:

```
---
type: linkedin_post
platform: linkedin
status: pending
timestamp: <ISO 8601>
---

<post content here>
```

### Step 5: Log the Action
Append to today's log file in `AI_Employee_Vault/Logs/YYYY-MM-DD.md`:
```
## HH:MM:SS - LinkedIn Post Draft Created
- **Type:** linkedin_post
- **Action Taken:** Generated LinkedIn post about "<topic>"
- **Result:** pending_approval
```

### Step 6: Inform the User
Tell the user:
1. The post draft has been saved to `Pending_Approval/`
2. They should review it in Obsidian
3. To publish: move the file from `Pending_Approval/` to `Approved/`
4. The LinkedIn Poster background thread will detect it and publish automatically
5. To reject: move it to `Rejected/`

## Example Output
```
LinkedIn post draft created!

File: AI_Employee_Vault/Pending_Approval/LINKEDIN_POST_20260227_143000.md

To publish: Move the file to AI_Employee_Vault/Approved/ in Obsidian
To reject: Move the file to AI_Employee_Vault/Rejected/

The LinkedIn Poster will automatically detect approved posts and publish them.
```
