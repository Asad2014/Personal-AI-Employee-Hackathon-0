# Skill: Instagram Post

Generate a professional Instagram post draft and submit it for approval.

## When to Use
Invoke with `/instagram-post` or `/instagram-post "topic here"` to create an Instagram post draft for the business account.

## Instructions

### Step 1: Read the Handbook
Read `AI_Employee_Vault/Company_Handbook.md` to understand the company's tone, communication guidelines, and branding.

### Step 2: Determine the Topic
- If the user provided a topic (e.g., `/instagram-post "new product launch"`), use that topic.
- If no topic was given, ask the user what the post should be about.

### Step 3: Generate the Post
Write a professional Instagram post following these guidelines:
- **Length:** 50-150 words (Instagram optimal length for captions)
- **Tone:** Professional but conversational (follow handbook guidelines)
- **Structure:** Attention-grabbing opening line, value proposition, call to action
- **Include:** 5-10 relevant hashtags at the end (Instagram best practice)
- **Image URL:** Ask the user for a publicly accessible image URL, or suggest they provide one before approval
- Do NOT include any emojis unless the handbook specifically encourages them

### Step 4: Save to Pending_Approval
Create a file in `AI_Employee_Vault/Pending_Approval/` named `INSTAGRAM_POST_<YYYYMMDD_HHMMSS>.md` with:

```
---
type: instagram_post
platform: instagram
status: pending
image_url: "<publicly accessible image URL>"
timestamp: <ISO 8601>
---

<post caption here>
```

IMPORTANT: The `image_url` field in frontmatter is required for Instagram posts. If the user has not provided one, use a placeholder value `REPLACE_WITH_IMAGE_URL` and instruct them to update it before moving to Approved/.

### Step 5: Log the Action
Append to today's log file in `AI_Employee_Vault/Logs/YYYY-MM-DD.md`:
```
## HH:MM:SS - Instagram Post Draft Created
- **Type:** instagram_post
- **Action Taken:** Generated Instagram post about "<topic>"
- **Result:** pending_approval
```

### Step 6: Inform the User
Tell the user:
1. The post draft has been saved to `Pending_Approval/`
2. They should review it in Obsidian
3. IMPORTANT: Ensure the `image_url` field in the frontmatter contains a valid, publicly accessible image URL before approving
4. To publish: move the file from `Pending_Approval/` to `Approved/`
5. The Instagram Poster background thread will detect it and publish via Graph API automatically
6. To reject: move it to `Rejected/`

## Example Output
```
Instagram post draft created!

File: AI_Employee_Vault/Pending_Approval/INSTAGRAM_POST_20260301_143000.md

IMPORTANT: Before approving, make sure the image_url field in the file's frontmatter
contains a valid, publicly accessible image URL. Instagram requires an image for every post.

To publish: Move the file to AI_Employee_Vault/Approved/ in Obsidian
To reject: Move the file to AI_Employee_Vault/Rejected/

The Instagram Poster will automatically detect approved posts and publish them to your account.
```
