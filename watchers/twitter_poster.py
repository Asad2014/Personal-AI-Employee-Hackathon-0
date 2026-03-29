# twitter_poster.py - Watches Approved/ for Twitter posts and publishes via Twitter API v2
import os
import re
import shutil
import datetime
import logging
import time
import requests
from requests_oauthlib import OAuth1
from pathlib import Path
from utils.audit_logger import audit_log
from utils.retry_handler import with_retry

logger = logging.getLogger('TwitterPoster')

TWITTER_API_BASE = 'https://api.twitter.com/2'


class TwitterPoster:
    """Watches Approved/ for files with type: twitter_post and publishes via Twitter API v2."""

    def __init__(self, vault_path: str, check_interval: int = 60):
        self.vault_path = Path(vault_path)
        self.approved = self.vault_path / 'Approved'
        self.done = self.vault_path / 'Done'
        self.logs = self.vault_path / 'Logs'
        self.check_interval = check_interval

        self.consumer_key = os.getenv('TWITTER_API_KEY', '')
        self.consumer_secret = os.getenv('TWITTER_API_SECRET', '')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN', '')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET', '')

        # Ensure directories exist
        self.approved.mkdir(parents=True, exist_ok=True)
        self.done.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)

    def _get_oauth1(self) -> OAuth1:
        """Return an OAuth1 auth object for posting."""
        if not all([self.consumer_key, self.consumer_secret, self.access_token, self.access_token_secret]):
            raise ValueError(
                "TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, "
                "and TWITTER_ACCESS_TOKEN_SECRET must all be set"
            )
        return OAuth1(self.consumer_key, self.consumer_secret, self.access_token, self.access_token_secret)

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
        """Extract the tweet body (everything after frontmatter)."""
        text = filepath.read_text(encoding='utf-8')
        cleaned = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, count=1, flags=re.DOTALL)
        return cleaned.strip()

    def check_for_approved_posts(self) -> list:
        """Scan Approved/ for files with type: twitter_post."""
        posts = []
        if not self.approved.exists():
            return posts
        for filepath in self.approved.glob('*.md'):
            fm = self._parse_frontmatter(filepath)
            if fm.get('type') == 'twitter_post':
                posts.append(filepath)
        return posts

    @with_retry(max_attempts=2, base_delay=5, max_delay=30)
    def publish_post(self, filepath: Path) -> bool:
        """Publish a tweet via Twitter API v2 using OAuth 1.0a."""
        try:
            auth = self._get_oauth1()
        except ValueError as e:
            logger.error(str(e))
            return False

        content = self._extract_post_content(filepath)
        if not content:
            logger.warning(f"Empty tweet content in {filepath.name}, skipping")
            return False

        if len(content) > 280:
            logger.warning(f"Tweet in {filepath.name} exceeds 280 chars ({len(content)}), truncating")
            content = content[:277] + '...'

        try:
            resp = requests.post(
                f"{TWITTER_API_BASE}/tweets",
                json={"text": content},
                auth=auth,
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
            tweet_id = result.get('data', {}).get('id', 'unknown')

            logger.info(f"Published tweet from {filepath.name} (tweet_id: {tweet_id})")
            audit_log(
                action_type='twitter_post_published',
                actor='twitter_poster',
                target='twitter.com',
                parameters={'file': filepath.name, 'tweet_id': tweet_id},
                approval_status='approved',
                result='success',
            )
            return True

        except requests.exceptions.HTTPError as e:
            error_detail = ''
            try:
                error_detail = e.response.json().get('detail', str(e))
            except Exception:
                error_detail = str(e)
            logger.error(f"Twitter API error publishing tweet: {error_detail}")
            audit_log(
                action_type='twitter_post_published',
                actor='twitter_poster',
                target='twitter.com',
                parameters={'file': filepath.name},
                result='failure',
                error_message=error_detail,
            )
            return False
        except Exception as e:
            logger.error(f"Failed to publish tweet: {e}")
            audit_log(
                action_type='twitter_post_published',
                actor='twitter_poster',
                target='twitter.com',
                parameters={'file': filepath.name},
                result='failure',
                error_message=str(e),
            )
            return False

    def _move_to_done(self, filepath: Path):
        """Move a published tweet file to Done/."""
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
            f"\n## {now} - Twitter Post: {filepath.name}\n"
            f"- **Type:** twitter_post\n"
            f"- **Action Taken:** Published tweet to Twitter/X via API v2\n"
            f"- **Result:** {status}\n"
        )

        if log_file.exists():
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(entry)
        else:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"# Activity Log - {today}\n{entry}")

    def run(self):
        """Main loop — check for approved tweets and publish them."""
        logger.info(f"TwitterPoster started (interval: {self.check_interval}s)")
        while True:
            try:
                posts = self.check_for_approved_posts()
                for filepath in posts:
                    logger.info(f"Found approved Twitter post: {filepath.name}")
                    success = self.publish_post(filepath)
                    self._log_action(filepath, success)
                    if success:
                        self._move_to_done(filepath)
            except Exception as e:
                logger.error(f"TwitterPoster error: {e}")
            time.sleep(self.check_interval)
