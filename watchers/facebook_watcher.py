# facebook_watcher.py - Monitors Facebook Page via Graph API for new messages/comments
import os
import datetime
import logging
import requests
from pathlib import Path
from watchers.base_watcher import BaseWatcher
from utils.audit_logger import audit_log
from utils.retry_handler import with_retry

logger = logging.getLogger('FacebookWatcher')

GRAPH_API_BASE = 'https://graph.facebook.com/v21.0'


class FacebookWatcher(BaseWatcher):
    """Monitors a Facebook Page for new comments, messages, and mentions via Graph API."""

    def __init__(self, vault_path: str, check_interval: int = 120):
        super().__init__(vault_path, check_interval)
        self.access_token = os.getenv('FACEBOOK_ACCESS_TOKEN', '')
        self.page_id = os.getenv('FACEBOOK_PAGE_ID', '')
        self.processed_ids = set()

        if not self.access_token:
            logger.warning("FACEBOOK_ACCESS_TOKEN not set — Facebook watcher will not run")
        if not self.page_id:
            logger.warning("FACEBOOK_PAGE_ID not set — Facebook watcher will not run")

        # Load already-processed IDs from existing files
        self._load_processed_ids()

    def _load_processed_ids(self):
        """Scan Needs_Action/ and Done/ for existing FACEBOOK_* files."""
        for folder in [self.needs_action, self.vault_path / 'Done']:
            if folder.exists():
                for f in folder.glob('FACEBOOK_*.md'):
                    item_id = f.stem.replace('FACEBOOK_', '')
                    self.processed_ids.add(item_id)
        logger.info(f"Loaded {len(self.processed_ids)} previously processed Facebook IDs")

    def _api_get(self, endpoint: str, params: dict = None) -> dict:
        """Make a GET request to the Facebook Graph API."""
        params = params or {}
        params['access_token'] = self.access_token
        url = f"{GRAPH_API_BASE}/{endpoint}"
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    @with_retry(max_attempts=3, base_delay=5, max_delay=60)
    def check_for_updates(self) -> list:
        """Fetch new comments and messages from the Facebook Page."""
        if not self.access_token or not self.page_id:
            return []

        new_items = []

        # 1. Check page feed for recent posts with new comments
        try:
            feed = self._api_get(f'{self.page_id}/feed', {
                'fields': 'id,message,created_time,from,comments.limit(10){id,message,from,created_time}',
                'limit': 10,
            })
            for post in feed.get('data', []):
                comments = post.get('comments', {}).get('data', [])
                for comment in comments:
                    cid = comment['id']
                    if cid not in self.processed_ids:
                        new_items.append({
                            'type': 'comment',
                            'id': cid,
                            'post_id': post['id'],
                            'post_message': post.get('message', '(no text)'),
                            'from': comment.get('from', {}).get('name', 'Unknown'),
                            'message': comment.get('message', ''),
                            'created_time': comment.get('created_time', ''),
                        })
                        self.processed_ids.add(cid)
        except Exception as e:
            logger.error(f"Error fetching page feed comments: {e}")

        # 2. Check page conversations (Messenger) for new messages
        try:
            conversations = self._api_get(f'{self.page_id}/conversations', {
                'fields': 'id,updated_time,participants,messages.limit(3){id,message,from,created_time}',
                'limit': 10,
            })
            for conv in conversations.get('data', []):
                messages = conv.get('messages', {}).get('data', [])
                for msg in messages:
                    mid = msg['id']
                    if mid not in self.processed_ids:
                        sender = msg.get('from', {}).get('name', 'Unknown')
                        # Skip messages from the page itself
                        if sender and msg.get('from', {}).get('id') != self.page_id:
                            new_items.append({
                                'type': 'message',
                                'id': mid,
                                'conversation_id': conv['id'],
                                'from': sender,
                                'message': msg.get('message', ''),
                                'created_time': msg.get('created_time', ''),
                            })
                            self.processed_ids.add(mid)
        except Exception as e:
            logger.error(f"Error fetching page conversations: {e}")

        # 3. Check page mentions/tags
        try:
            tagged = self._api_get(f'{self.page_id}/tagged', {
                'fields': 'id,message,from,created_time',
                'limit': 10,
            })
            for post in tagged.get('data', []):
                tid = post['id']
                if tid not in self.processed_ids:
                    new_items.append({
                        'type': 'mention',
                        'id': tid,
                        'from': post.get('from', {}).get('name', 'Unknown'),
                        'message': post.get('message', ''),
                        'created_time': post.get('created_time', ''),
                    })
                    self.processed_ids.add(tid)
        except Exception as e:
            logger.error(f"Error fetching page mentions: {e}")

        if new_items:
            logger.info(f"Found {len(new_items)} new Facebook items")
        return new_items

    def create_action_file(self, item) -> Path:
        """Create a FACEBOOK_<id>.md file in Needs_Action/."""
        item_id = item['id'].replace('_', '-')
        item_type = item['type']
        sender = item.get('from', 'Unknown')
        message = item.get('message', '')
        created = item.get('created_time', datetime.datetime.now().isoformat())

        # Determine priority
        urgent_keywords = ['urgent', 'asap', 'help', 'emergency', 'payment', 'invoice']
        priority = 'high' if any(kw in message.lower() for kw in urgent_keywords) else 'medium'

        filename = f"FACEBOOK_{item_id}.md"
        filepath = self.needs_action / filename

        # Build type-specific content
        extra_context = ''
        if item_type == 'comment':
            extra_context = f"**On Post:** {item.get('post_message', '(no text)')}\n**Post ID:** {item.get('post_id', '')}\n"
        elif item_type == 'message':
            extra_context = f"**Conversation ID:** {item.get('conversation_id', '')}\n"
        elif item_type == 'mention':
            extra_context = "**Type:** Page mention/tag\n"

        content = f"""---
type: facebook_{item_type}
from: "{sender}"
facebook_id: "{item['id']}"
received: "{created}"
priority: {priority}
status: pending
---

# Facebook {item_type.title()} from {sender}

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
            action_type=f'facebook_{item_type}_detected',
            actor='facebook_watcher',
            target=sender,
            parameters={'facebook_id': item['id'], 'action_file': filename},
            result='success',
        )
        return filepath
