# instagram_poster.py - Watches Approved/ for Instagram posts and publishes via Graph API
import os
import re
import shutil
import datetime
import logging
import time
import requests
from pathlib import Path
from utils.audit_logger import audit_log
from utils.retry_handler import with_retry

logger = logging.getLogger('InstagramPoster')

GRAPH_API_BASE = 'https://graph.facebook.com/v21.0'


class InstagramPoster:
    """Watches Approved/ for files with type: instagram_post and publishes via Graph API."""

    def __init__(self, vault_path: str, check_interval: int = 60):
        self.vault_path = Path(vault_path)
        self.approved = self.vault_path / 'Approved'
        self.done = self.vault_path / 'Done'
        self.logs = self.vault_path / 'Logs'
        self.check_interval = check_interval

        self.access_token = os.getenv('FACEBOOK_ACCESS_TOKEN', '')
        self.ig_user_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID', '')

        # Ensure directories exist
        self.approved.mkdir(parents=True, exist_ok=True)
        self.done.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)

    def _parse_frontmatter(self, filepath: Path) -> dict:
        """Parse YAML frontmatter from a markdown file."""
        text = filepath.read_text(encoding='utf-8')
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
        if not match:
            return {}
        frontmatter = {}
        for line in match.group(1).splitlines():
            if ':' in line:
                key, _, value = line.partition(':')
                frontmatter[key.strip()] = value.strip().strip('"').strip("'")
        return frontmatter

    def _extract_post_content(self, filepath: Path) -> str:
        """Extract the post body (everything after frontmatter)."""
        text = filepath.read_text(encoding='utf-8')
        cleaned = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, count=1, flags=re.DOTALL)
        return cleaned.strip()

    def check_for_approved_posts(self) -> list:
        """Scan Approved/ for files with type: instagram_post."""
        posts = []
        if not self.approved.exists():
            return posts
        for filepath in self.approved.glob('*.md'):
            fm = self._parse_frontmatter(filepath)
            if fm.get('type') == 'instagram_post':
                posts.append(filepath)
        return posts

    @with_retry(max_attempts=2, base_delay=5, max_delay=30)
    def publish_post(self, filepath: Path) -> bool:
        """Publish a photo post to Instagram via Graph API (two-step container flow)."""
        if not self.access_token or not self.ig_user_id:
            logger.error("FACEBOOK_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID not set")
            return False

        fm = self._parse_frontmatter(filepath)
        image_url = fm.get('image_url', '')
        if not image_url:
            logger.warning(f"No image_url in frontmatter of {filepath.name}, skipping (Instagram requires an image)")
            return False

        caption = self._extract_post_content(filepath)

        try:
            # Step 1: Create media container
            container_url = f"{GRAPH_API_BASE}/{self.ig_user_id}/media"
            container_data = {
                'image_url': image_url,
                'access_token': self.access_token,
            }
            if caption:
                container_data['caption'] = caption

            container_resp = requests.post(container_url, data=container_data, timeout=30)
            container_resp.raise_for_status()
            creation_id = container_resp.json().get('id')

            if not creation_id:
                logger.error(f"Failed to create media container for {filepath.name}")
                return False

            # Step 2: Publish the container
            publish_url = f"{GRAPH_API_BASE}/{self.ig_user_id}/media_publish"
            publish_resp = requests.post(publish_url, data={
                'creation_id': creation_id,
                'access_token': self.access_token,
            }, timeout=30)
            publish_resp.raise_for_status()
            result = publish_resp.json()
            media_id = result.get('id', 'unknown')

            logger.info(f"Published Instagram post from {filepath.name} (media_id: {media_id})")
            audit_log(
                action_type='instagram_post_published',
                actor='instagram_poster',
                target='instagram.com',
                parameters={'file': filepath.name, 'media_id': media_id},
                approval_status='approved',
                result='success',
            )
            return True

        except requests.exceptions.HTTPError as e:
            error_detail = ''
            try:
                error_detail = e.response.json().get('error', {}).get('message', str(e))
            except Exception:
                error_detail = str(e)
            logger.error(f"Instagram API error publishing post: {error_detail}")
            audit_log(
                action_type='instagram_post_published',
                actor='instagram_poster',
                target='instagram.com',
                parameters={'file': filepath.name},
                result='failure',
                error_message=error_detail,
            )
            return False
        except Exception as e:
            logger.error(f"Failed to publish Instagram post: {e}")
            audit_log(
                action_type='instagram_post_published',
                actor='instagram_poster',
                target='instagram.com',
                parameters={'file': filepath.name},
                result='failure',
                error_message=str(e),
            )
            return False

    def _move_to_done(self, filepath: Path):
        """Move a published post file to Done/."""
        dest = self.done / filepath.name
        shutil.move(str(filepath), str(dest))
        logger.info(f"Moved {filepath.name} to Done/")

    def _log_action(self, filepath: Path, success: bool):
        """Log the posting action to today's log file."""
        today = datetime.date.today().isoformat()
        now = datetime.datetime.now().strftime('%H:%M:%S')
        log_file = self.logs / f"{today}.md"

        status = 'success' if success else 'error'
        entry = (
            f"\n## {now} - Instagram Post: {filepath.name}\n"
            f"- **Type:** instagram_post\n"
            f"- **Action Taken:** Published to Instagram via Graph API\n"
            f"- **Result:** {status}\n"
        )

        if log_file.exists():
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(entry)
        else:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"# Activity Log - {today}\n{entry}")

    def run(self):
        """Main loop — check for approved posts and publish them."""
        logger.info(f"InstagramPoster started (interval: {self.check_interval}s)")
        while True:
            try:
                posts = self.check_for_approved_posts()
                for filepath in posts:
                    logger.info(f"Found approved Instagram post: {filepath.name}")
                    success = self.publish_post(filepath)
                    self._log_action(filepath, success)
                    if success:
                        self._move_to_done(filepath)
            except Exception as e:
                logger.error(f"InstagramPoster error: {e}")
            time.sleep(self.check_interval)
