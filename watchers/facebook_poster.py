# facebook_poster.py - Watches Approved/ for Facebook posts and publishes via Graph API
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

logger = logging.getLogger('FacebookPoster')

GRAPH_API_BASE = 'https://graph.facebook.com/v21.0'


class FacebookPoster:
    """Watches Approved/ for files with type: facebook_post and publishes via Graph API."""

    def __init__(self, vault_path: str, check_interval: int = 60):
        self.vault_path = Path(vault_path)
        self.approved = self.vault_path / 'Approved'
        self.done = self.vault_path / 'Done'
        self.logs = self.vault_path / 'Logs'
        self.check_interval = check_interval

        self.access_token = os.getenv('FACEBOOK_ACCESS_TOKEN', '')
        self.page_id = os.getenv('FACEBOOK_PAGE_ID', '')

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
        """Scan Approved/ for files with type: facebook_post."""
        posts = []
        if not self.approved.exists():
            return posts
        for filepath in self.approved.glob('*.md'):
            fm = self._parse_frontmatter(filepath)
            if fm.get('type') == 'facebook_post':
                posts.append(filepath)
        return posts

    @with_retry(max_attempts=2, base_delay=5, max_delay=30)
    def publish_post(self, filepath: Path) -> bool:
        """Publish a post to the Facebook Page via Graph API."""
        if not self.access_token or not self.page_id:
            logger.error("FACEBOOK_ACCESS_TOKEN or FACEBOOK_PAGE_ID not set")
            return False

        content = self._extract_post_content(filepath)
        if not content:
            logger.warning(f"Empty post content in {filepath.name}, skipping")
            return False

        try:
            url = f"{GRAPH_API_BASE}/{self.page_id}/feed"
            resp = requests.post(url, data={
                'message': content,
                'access_token': self.access_token,
            }, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            post_id = result.get('id', 'unknown')

            logger.info(f"Published Facebook post from {filepath.name} (post_id: {post_id})")
            audit_log(
                action_type='facebook_post_published',
                actor='facebook_poster',
                target='facebook.com',
                parameters={'file': filepath.name, 'post_id': post_id},
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
            logger.error(f"Facebook API error publishing post: {error_detail}")
            audit_log(
                action_type='facebook_post_published',
                actor='facebook_poster',
                target='facebook.com',
                parameters={'file': filepath.name},
                result='failure',
                error_message=error_detail,
            )
            return False
        except Exception as e:
            logger.error(f"Failed to publish Facebook post: {e}")
            audit_log(
                action_type='facebook_post_published',
                actor='facebook_poster',
                target='facebook.com',
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
            f"\n## {now} - Facebook Post: {filepath.name}\n"
            f"- **Type:** facebook_post\n"
            f"- **Action Taken:** Published to Facebook Page via Graph API\n"
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
        logger.info(f"FacebookPoster started (interval: {self.check_interval}s)")
        while True:
            try:
                posts = self.check_for_approved_posts()
                for filepath in posts:
                    logger.info(f"Found approved Facebook post: {filepath.name}")
                    success = self.publish_post(filepath)
                    self._log_action(filepath, success)
                    if success:
                        self._move_to_done(filepath)
            except Exception as e:
                logger.error(f"FacebookPoster error: {e}")
            time.sleep(self.check_interval)
