# twitter_watcher.py - Monitors Twitter/X for new mentions via API v2
import os
import datetime
import logging
import requests
from pathlib import Path
from watchers.base_watcher import BaseWatcher
from utils.audit_logger import audit_log
from utils.retry_handler import with_retry

logger = logging.getLogger('TwitterWatcher')

TWITTER_API_BASE = 'https://api.twitter.com/2'


class TwitterWatcher(BaseWatcher):
    """Monitors Twitter/X for new mentions of the authenticated user via API v2."""

    def __init__(self, vault_path: str, check_interval: int = 120):
        super().__init__(vault_path, check_interval)
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN', '')
        self.processed_ids = set()
        self._user_id = None

        if not self.bearer_token:
            logger.warning("TWITTER_BEARER_TOKEN not set — Twitter watcher will not run")

        # Load already-processed IDs from existing files
        self._load_processed_ids()

    def _load_processed_ids(self):
        """Scan Needs_Action/ and Done/ for existing TWITTER_MENTION_* files."""
        for folder in [self.needs_action, self.vault_path / 'Done']:
            if folder.exists():
                for f in folder.glob('TWITTER_MENTION_*.md'):
                    item_id = f.stem.replace('TWITTER_MENTION_', '')
                    self.processed_ids.add(item_id)
        logger.info(f"Loaded {len(self.processed_ids)} previously processed Twitter mention IDs")

    def _get_headers(self) -> dict:
        """Return Bearer token authorization headers."""
        return {"Authorization": f"Bearer {self.bearer_token}"}

    def _get_user_id(self) -> str:
        """Fetch and cache the authenticated user's ID."""
        if self._user_id:
            return self._user_id

        resp = requests.get(
            f"{TWITTER_API_BASE}/users/me",
            headers=self._get_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        self._user_id = resp.json()['data']['id']
        logger.info(f"Authenticated as Twitter user ID: {self._user_id}")
        return self._user_id

    @with_retry(max_attempts=3, base_delay=5, max_delay=60)
    def check_for_updates(self) -> list:
        """Fetch new mentions of the authenticated user from Twitter API v2."""
        if not self.bearer_token:
            return []

        new_items = []

        try:
            user_id = self._get_user_id()
            resp = requests.get(
                f"{TWITTER_API_BASE}/users/{user_id}/mentions",
                params={
                    "tweet.fields": "public_metrics,created_at,author_id,conversation_id",
                    "max_results": 20,
                },
                headers=self._get_headers(),
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()

            for tweet in result.get('data', []):
                tweet_id = tweet['id']
                if tweet_id not in self.processed_ids:
                    metrics = tweet.get('public_metrics', {})
                    new_items.append({
                        'id': tweet_id,
                        'text': tweet.get('text', ''),
                        'author_id': tweet.get('author_id', ''),
                        'created_at': tweet.get('created_at', ''),
                        'conversation_id': tweet.get('conversation_id', ''),
                        'likes': metrics.get('like_count', 0),
                        'retweets': metrics.get('retweet_count', 0),
                        'replies': metrics.get('reply_count', 0),
                    })
                    self.processed_ids.add(tweet_id)

        except Exception as e:
            logger.error(f"Error fetching Twitter mentions: {e}")

        if new_items:
            logger.info(f"Found {len(new_items)} new Twitter mentions")
        return new_items

    def create_action_file(self, item) -> Path:
        """Create a TWITTER_MENTION_<id>.md file in Needs_Action/."""
        tweet_id = item['id']
        author_id = item.get('author_id', 'Unknown')
        text = item.get('text', '')
        created_at = item.get('created_at', datetime.datetime.now().isoformat())

        # Determine priority based on keywords
        urgent_keywords = ['urgent', 'asap', 'help', 'emergency', 'payment', 'invoice']
        priority = 'high' if any(kw in text.lower() for kw in urgent_keywords) else 'medium'

        filename = f"TWITTER_MENTION_{tweet_id}.md"
        filepath = self.needs_action / filename

        content = f"""---
type: twitter_mention
tweet_id: "{tweet_id}"
author_id: "{author_id}"
conversation_id: "{item.get('conversation_id', '')}"
received: "{created_at}"
priority: {priority}
status: pending
---

# Twitter Mention

**Tweet ID:** {tweet_id}
**Author ID:** {author_id}
**Received:** {created_at}
**Conversation ID:** {item.get('conversation_id', '')}

## Content
{text}

## Engagement
- Likes: {item.get('likes', 0)}
- Retweets: {item.get('retweets', 0)}
- Replies: {item.get('replies', 0)}

## Suggested Actions
- [ ] Read and assess mention content
- [ ] Draft appropriate response following handbook guidelines
- [ ] Check if reply needs approval (new contact policy)
"""
        filepath.write_text(content, encoding='utf-8')
        logger.info(f"Created action file: {filename}")
        audit_log(
            action_type='twitter_mention_detected',
            actor='twitter_watcher',
            target=author_id,
            parameters={'tweet_id': tweet_id, 'action_file': filename},
            result='success',
        )
        return filepath
