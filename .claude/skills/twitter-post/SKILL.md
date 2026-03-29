# Skill: Twitter Post

Generate a tweet for Twitter/X and submit it for approval.

## When to Use
Invoke with `/twitter-post` or `/twitter-post "topic here"` to create a tweet draft.

## Instructions

### Step 1: Read the Handbook
Read `AI_Employee_Vault/Company_Handbook.md` to understand the company's tone, communication guidelines, and branding.

### Step 2: Determine the Topic
- If the user provided a topic (e.g., `/twitter-post "new product launch"`), use that topic.
- If no topic was given, ask the user what the tweet should be about.

### Step 3: Generate the Tweet
Write a tweet following these guidelines:
- **Length:** Maximum 280 characters (this is a hard Twitter limit)
- **Tone:** Professional but conversational (follow handbook guidelines)
- **Structure:** Concise, impactful message with a clear point or call to action
- **Include:** 1-3 relevant hashtags (these count toward the 280-character limit)
- Do NOT include any emojis unless the handbook specifically encourages them
- Count characters carefully — the entire tweet including hashtags must be 280 characters or fewer

### Step 4: Save to Pending_Approval
Create a file in `AI_Employee_Vault/Pending_Approval/` named `TWITTER_POST_<YYYYMMDD_HHMMSS>.md` with:

```
---
type: twitter_post
platform: twitter
status: pending
timestamp: <ISO 8601>
---

<tweet content here>
```

### Step 5: Log the Action
Append to today's log file in `AI_Employee_Vault/Logs/YYYY-MM-DD.md`:
```
## HH:MM:SS - Twitter Post Draft Created
- **Type:** twitter_post
- **Action Taken:** Generated tweet about "<topic>"
- **Result:** pending_approval
```

### Step 6: Inform the User
Tell the user:
1. The tweet draft has been saved to `Pending_Approval/`
2. They should review it in Obsidian
3. To publish: move the file from `Pending_Approval/` to `Approved/`
4. The Twitter Poster background thread will detect it and publish via Twitter API v2 automatically
5. To reject: move it to `Rejected/`
6. Remind them that tweets have a strict 280-character limit

## Example Output
```
Tweet draft created! (X characters)

File: AI_Employee_Vault/Pending_Approval/TWITTER_POST_20260301_143000.md

To publish: Move the file to AI_Employee_Vault/Approved/ in Obsidian
To reject: Move the file to AI_Employee_Vault/Rejected/

The Twitter Poster will automatically detect approved posts and publish them to your account.

Note: Tweets have a strict 280-character limit. Please verify the length before approving.
```
