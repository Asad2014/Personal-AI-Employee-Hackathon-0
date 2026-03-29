# linkedin_poster.py - Watches Approved/ for LinkedIn posts and publishes via Playwright
import os
import re
import shutil
import datetime
import logging
import time
from pathlib import Path
from utils.audit_logger import audit_log
from utils.retry_handler import with_retry

logger = logging.getLogger('LinkedInPoster')

# Playwright imported lazily so the module can be imported without it installed
_playwright = None


def _get_playwright():
    global _playwright
    if _playwright is None:
        from playwright.sync_api import sync_playwright
        _playwright = sync_playwright
    return _playwright


class LinkedInPoster:
    def __init__(self, vault_path: str, session_path: str = None, check_interval: int = 60):
        self.vault_path = Path(vault_path)
        self.approved = self.vault_path / 'Approved'
        self.done = self.vault_path / 'Done'
        self.logs = self.vault_path / 'Logs'
        self.check_interval = check_interval
        self.session_path = Path(session_path or os.path.expanduser('~/.linkedin_session'))
        self.headless = os.getenv('LINKEDIN_HEADLESS', 'true').lower() == 'true'

        # Ensure directories exist
        self.approved.mkdir(parents=True, exist_ok=True)
        self.done.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
        self.session_path.mkdir(parents=True, exist_ok=True)

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
        # Remove frontmatter
        cleaned = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, count=1, flags=re.DOTALL)
        return cleaned.strip()

    def check_for_approved_posts(self) -> list:
        """Scan Approved/ for files with type: linkedin_post."""
        posts = []
        if not self.approved.exists():
            return posts

        for filepath in self.approved.glob('*.md'):
            fm = self._parse_frontmatter(filepath)
            if fm.get('type') == 'linkedin_post':
                posts.append(filepath)

        return posts

    @with_retry(max_attempts=2, base_delay=5, max_delay=30)
    def publish_post(self, filepath: Path) -> bool:
        """Use Playwright to publish a LinkedIn post."""
        content = self._extract_post_content(filepath)
        if not content:
            logger.warning(f"Empty post content in {filepath.name}, skipping")
            return False

        sync_playwright = _get_playwright()

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_path),
                    headless=self.headless,
                    viewport={'width': 1280, 'height': 900},
                )
                page = browser.pages[0] if browser.pages else browser.new_page()

                # Navigate to LinkedIn feed
                page.goto('https://www.linkedin.com/feed/', wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(3000)

                # Check if we need to log in (redirect to login page)
                if '/login' in page.url or '/uas/' in page.url or '/checkpoint/' in page.url:
                    if self.headless:
                        logger.error(
                            "Not logged in to LinkedIn. "
                            "Run with LINKEDIN_HEADLESS=false first to log in manually."
                        )
                        browser.close()
                        return False
                    else:
                        logger.info("Please log in to LinkedIn in the browser window...")
                        # Wait until URL no longer contains login/checkpoint pages (5 min timeout)
                        for _ in range(300):
                            page.wait_for_timeout(1000)
                            current = page.url
                            if '/login' not in current and '/uas/' not in current and '/checkpoint/' not in current:
                                break
                        else:
                            logger.error("Login timed out after 5 minutes")
                            browser.close()
                            return False
                        logger.info(f"Login successful, now at: {page.url}")
                        # Navigate to feed after login
                        page.goto('https://www.linkedin.com/feed/', wait_until='domcontentloaded', timeout=30000)
                        page.wait_for_timeout(3000)

                # Click "Start a post" button
                start_post_btn = page.locator('button.share-box-feed-entry__trigger').first
                if not start_post_btn.is_visible():
                    # Try alternate selector
                    start_post_btn = page.locator('[data-control-name="share.start"]').first
                if not start_post_btn.is_visible():
                    # Another fallback — the text-based approach
                    start_post_btn = page.get_by_role('button', name=re.compile(r'start a post', re.IGNORECASE)).first

                start_post_btn.click()
                page.wait_for_timeout(2000)

                # Type in the post editor
                editor = page.locator('div.ql-editor[contenteditable="true"]').first
                if not editor.is_visible():
                    editor = page.locator('[role="textbox"]').first

                editor.click()
                editor.fill(content)
                page.wait_for_timeout(1000)

                # Click the "Post" button
                post_btn = page.get_by_role('button', name=re.compile(r'^Post$', re.IGNORECASE)).first
                post_btn.click()
                page.wait_for_timeout(5000)

                browser.close()

            logger.info(f"Successfully published LinkedIn post from {filepath.name}")
            audit_log(
                action_type='linkedin_post_published',
                actor='linkedin_poster',
                target='linkedin.com',
                parameters={'file': filepath.name},
                approval_status='approved',
                result='success',
            )
            return True

        except Exception as e:
            logger.error(f"Failed to publish LinkedIn post: {e}")
            audit_log(
                action_type='linkedin_post_published',
                actor='linkedin_poster',
                target='linkedin.com',
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
            f"\n## {now} - LinkedIn Post: {filepath.name}\n"
            f"- **Type:** linkedin_post\n"
            f"- **Action Taken:** Published to LinkedIn via Playwright\n"
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
        logger.info(f"LinkedInPoster started (interval: {self.check_interval}s, headless: {self.headless})")
        while True:
            try:
                posts = self.check_for_approved_posts()
                for filepath in posts:
                    logger.info(f"Found approved LinkedIn post: {filepath.name}")
                    success = self.publish_post(filepath)
                    self._log_action(filepath, success)
                    if success:
                        self._move_to_done(filepath)
            except Exception as e:
                logger.error(f"LinkedInPoster error: {e}")
            time.sleep(self.check_interval)
