# instagram_watcher.py - Monitors Instagram for new comments via Graph API
import os
import datetime
import logging
import requests
from pathlib import Path
from watchers.base_watcher import BaseWatcher
from utils.audit_logger import audit_log
from utils.retry_handler import with_retry

logger = logging.getLogger('InstagramWatcher')

GRAPH_API_BASE = 'https://graph.facebook.com/v21.0'


class InstagramWatcher(BaseWatcher):
    """Monitors an Instagram Business account for new comments on posts via Graph API."""

    def __init__(self, vault_path: str, check_interval: int = 120):
        super().__init__(vault_path, check_interval)
        self.access_token = os.getenv('FACEBOOK_ACCESS_TOKEN', '')
        self.ig_user_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID', '')
        self.processed_ids = set()

        if not self.access_token:
            logger.warning("FACEBOOK_ACCESS_TOKEN not set — Instagram watcher will not run")
        if not self.ig_user_id:
            logger.warning("INSTAGRAM_BUSINESS_ACCOUNT_ID not set — Instagram watcher will not run")

        # Load already-processed IDs from existing files
        self._load_processed_ids()

    def _load_processed_ids(self):
        """Scan Needs_Action/ and Done/ for existing INSTAGRAM_* files."""
        for folder in [self.needs_action, self.vault_path / 'Done']:
            if folder.exists():
                for f in folder.glob('INSTAGRAM_*.md'):
                    item_id = f.stem.replace('INSTAGRAM_', '')
                    self.processed_ids.add(item_id)
        logger.info(f"Loaded {len(self.processed_ids)} previously processed Instagram IDs")

    def _api_get(self, endpoint: str, params: dict = None) -> dict:
        """Make a GET request to the Instagram Graph API."""
        params = params or {}
        params['access_token'] = self.access_token
        url = f"{GRAPH_API_BASE}/{endpoint}"
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    @with_retry(max_attempts=3, base_delay=5, max_delay=60)
    def check_for_updates(self) -> list:
        """Fetch new comments from Instagram posts."""
        if not self.access_token or not self.ig_user_id:
            return []

        new_items = []

        # Check recent media for new comments
        try:
            media = self._api_get(f'{self.ig_user_id}/media', {
                'fields': 'id,caption,timestamp,comments{id,text,username,timestamp}',
                'limit': 10,
            })
            for post in media.get('data', []):
                comments = post.get('comments', {}).get('data', [])
                for comment in comments:
                    cid = comment['id']
                    if cid not in self.processed_ids:
                        new_items.append({
                            'type': 'comment',
                            'id': cid,
                            'post_id': post['id'],
                            'post_caption': post.get('caption', '(no caption)'),
                            'from': comment.get('username', 'Unknown'),
                            'message': comment.get('text', ''),
                            'created_time': comment.get('timestamp', ''),
                        })
                        self.processed_ids.add(cid)
        except Exception as e:
            logger.error(f"Error fetching Instagram media comments: {e}")

        if new_items:
            logger.info(f"Found {len(new_items)} new Instagram items")
        return new_items

    def create_action_file(self, item) -> Path:
        """Create an INSTAGRAM_<id>.md file in Needs_Action/."""
        item_id = item['id'].replace('_', '-')
        item_type = item['type']
        sender = item.get('from', 'Unknown')
        message = item.get('message', '')
        created = item.get('created_time', datetime.datetime.now().isoformat())

        # Determine priority
        urgent_keywords = ['urgent', 'asap', 'help', 'emergency', 'payment', 'invoice']
        priority = 'high' if any(kw in message.lower() for kw in urgent_keywords) else 'medium'

        filename = f"INSTAGRAM_{item_id}.md"
        filepath = self.needs_action / filename

        # Build type-specific content
        extra_context = ''
        if item_type == 'comment':
            extra_context = f"**On Post:** {item.get('post_caption', '(no caption)')}\n**Post ID:** {item.get('post_id', '')}\n"

        content = f"""---
type: instagram_{item_type}
from: "{sender}"
instagram_id: "{item['id']}"
received: "{created}"
priority: {priority}
status: pending
---

# Instagram {item_type.title()} from {sender}

**Received:** {created}
{extra_context}
## Content
{message}

## Suggested Actions
- [ ] Read and assess content
- [ ] Draft appropriate response following handbook guidelines
- [ ] Check if reply needs approval (new contact policy)
"""
        filepath.write_text(content, encoding='utf-8')
        logger.info(f"Created action file: {filename}")
        audit_log(
            action_type=f'instagram_{item_type}_detected',
            actor='instagram_watcher',
            target=sender,
            parameters={'instagram_id': item['id'], 'action_file': filename},
            result='success',
        )
        return filepath
