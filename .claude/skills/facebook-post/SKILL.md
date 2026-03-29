# Skill: Facebook Post

Generate a professional Facebook post for the business page and submit it for approval.

## When to Use
Invoke with `/facebook-post` or `/facebook-post "topic here"` to create a Facebook post draft for the business page.

## Instructions

### Step 1: Read the Handbook
Read `AI_Employee_Vault/Company_Handbook.md` to understand the company's tone, communication guidelines, and branding.

### Step 2: Determine the Topic
- If the user provided a topic (e.g., `/facebook-post "new product launch"`), use that topic.
- If no topic was given, ask the user what the post should be about.

### Step 3: Generate the Post
Write a professional Facebook post following these guidelines:
- **Length:** 100-250 words (Facebook optimal length)
- **Tone:** Professional but conversational (follow handbook guidelines)
- **Structure:** Attention-grabbing opening, value proposition, call to action
- **Include:** 2-4 relevant hashtags at the end
- Do NOT include any emojis unless the handbook specifically encourages them

### Step 4: Save to Pending_Approval
Create a file in `AI_Employee_Vault/Pending_Approval/` named `FACEBOOK_POST_<YYYYMMDD_HHMMSS>.md` with:

```
---
type: facebook_post
platform: facebook
status: pending
timestamp: <ISO 8601>
---

<post content here>
```

### Step 5: Log the Action
Append to today's log file in `AI_Employee_Vault/Logs/YYYY-MM-DD.md`:
```
## HH:MM:SS - Facebook Post Draft Created
- **Type:** facebook_post
- **Action Taken:** Generated Facebook post about "<topic>"
- **Result:** pending_approval
```

### Step 6: Inform the User
Tell the user:
1. The post draft has been saved to `Pending_Approval/`
2. They should review it in Obsidian
3. To publish: move the file from `Pending_Approval/` to `Approved/`
4. The Facebook Poster background thread will detect it and publish via Graph API automatically
5. To reject: move it to `Rejected/`

## Example Output
```
Facebook post draft created!

File: AI_Employee_Vault/Pending_Approval/FACEBOOK_POST_20260301_143000.md

To publish: Move the file to AI_Employee_Vault/Approved/ in Obsidian
To reject: Move the file to AI_Employee_Vault/Rejected/

The Facebook Poster will automatically detect approved posts and publish them to your page.
```
