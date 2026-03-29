# whatsapp_watcher.py - Monitors WhatsApp Web for new messages via Playwright
import os
import hashlib
import datetime
from pathlib import Path
from watchers.base_watcher import BaseWatcher
from utils.audit_logger import audit_log
from utils.retry_handler import with_retry

# Playwright imported lazily so the module can be imported without it installed
_sync_playwright = None


def _get_sync_playwright():
    global _sync_playwright
    if _sync_playwright is None:
        from playwright.sync_api import sync_playwright
        _sync_playwright = sync_playwright
    return _sync_playwright


class WhatsAppWatcher(BaseWatcher):
    def __init__(self, vault_path: str, session_path: str = None, check_interval: int = 60):
        super().__init__(vault_path, check_interval)
        self.session_path = Path(
            session_path or os.path.expanduser('~/.whatsapp_session')
        )
        self.headless = os.getenv('WHATSAPP_HEADLESS', 'true').lower() == 'true'
        self.processed_hashes = set()
        self.browser_context = None
        self.page = None
        self._pw_instance = None

        # Ensure directories exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.session_path.mkdir(parents=True, exist_ok=True)

        # Load already-processed message hashes from existing files
        self._load_processed_hashes()

    def _load_processed_hashes(self):
        """Scan Needs_Action/ and Done/ for existing WHATSAPP_* files to avoid reprocessing."""
        for folder in [self.needs_action, self.vault_path / 'Done']:
            if folder.exists():
                for f in folder.glob('WHATSAPP_*.md'):
                    # Read the file and compute a hash from sender + timestamp + content preview
                    try:
                        text = f.read_text(encoding='utf-8')
                        # Extract from/received/first line of content for hash
                        sender = ''
                        received = ''
                        for line in text.splitlines():
                            if line.startswith('from:'):
                                sender = line.split(':', 1)[1].strip().strip('"')
                            elif line.startswith('received:'):
                                received = line.split(':', 1)[1].strip().strip('"')
                        msg_hash = self._compute_hash(sender, received, '')
                        self.processed_hashes.add(msg_hash)
                    except Exception:
                        pass
        self.logger.info(f"Loaded {len(self.processed_hashes)} previously processed WhatsApp message hashes")

    @staticmethod
    def _compute_hash(sender: str, timestamp: str, content_preview: str) -> str:
        """Compute a deduplication hash from sender + timestamp + first 50 chars of content."""
        key = f"{sender}|{timestamp}|{content_preview[:50]}"
        return hashlib.sha256(key.encode()).hexdigest()

    def authenticate(self):
        """Launch persistent Playwright browser and navigate to WhatsApp Web.
        On first run (no session), user must scan QR code in the browser.
        """
        sync_playwright = _get_sync_playwright()
        self._pw_instance = sync_playwright().start()

        self.browser_context = self._pw_instance.chromium.launch_persistent_context(
            user_data_dir=str(self.session_path),
            headless=self.headless,
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled'],
        )
        self.page = (
            self.browser_context.pages[0]
            if self.browser_context.pages
            else self.browser_context.new_page()
        )

        self.page.goto('https://web.whatsapp.com', wait_until='domcontentloaded', timeout=60000)

        # Wait for either QR code or the main chat list to appear
        try:
            # If the chat list side panel is already present, we're logged in
            self.page.wait_for_selector(
                'div[aria-label="Chat list"], div[aria-label="Search input textbox"], canvas[aria-label="Scan this QR code to link a device!"]',
                timeout=30000,
            )
        except Exception:
            pass

        # Check if QR code is showing (need manual scan)
        qr = self.page.query_selector('canvas[aria-label="Scan this QR code to link a device!"]')
        if qr:
            if self.headless:
                self.logger.error(
                    "Not logged in to WhatsApp Web. "
                    "Run with WHATSAPP_HEADLESS=false first to scan the QR code."
                )
                self._cleanup()
                raise RuntimeError("WhatsApp QR login required — run in non-headless mode first")

            self.logger.info("QR code displayed — please scan it with your phone's WhatsApp app...")
            # Wait up to 2 minutes for the user to scan QR and the chat list to load
            try:
                self.page.wait_for_selector(
                    'div[aria-label="Chat list"]',
                    timeout=120000,
                )
                self.logger.info("WhatsApp Web authenticated successfully")
            except Exception:
                self.logger.error("QR scan timed out after 2 minutes")
                self._cleanup()
                raise RuntimeError("WhatsApp QR scan timed out")
        else:
            # Already logged in — wait for chat list to fully load
            try:
                self.page.wait_for_selector('div[aria-label="Chat list"]', timeout=30000)
            except Exception:
                pass
            self.logger.info("WhatsApp Web session restored from saved data")

    @with_retry(max_attempts=3, base_delay=5, max_delay=60)
    def check_for_updates(self) -> list:
        """Check WhatsApp Web for unread messages."""
        if not self.page or self.page.is_closed():
            self.authenticate()

        new_messages = []

        try:
            # Use JavaScript to gather unread chat info in a single evaluation.
            # This avoids fragile closest() DOM traversal — instead we walk up from
            # each unread badge to the chat list boundary and read the sender title.
            unread_info = self.page.evaluate('''() => {
                const chatList = document.querySelector('div[aria-label="Chat list"]');
                if (!chatList) return [];

                const badges = chatList.querySelectorAll('span[aria-label*="unread message"]');
                const results = [];
                const seen = new Set();

                for (const badge of badges) {
                    // Walk up from the badge until we reach a direct child of chatList
                    let row = badge;
                    while (row.parentElement && row.parentElement !== chatList) {
                        row = row.parentElement;
                    }
                    if (!row || row.parentElement !== chatList) continue;

                    // Extract sender name from span[title] inside this row
                    const titleEl = row.querySelector('span[title]');
                    const sender = titleEl ? titleEl.getAttribute('title') : null;
                    if (!sender || seen.has(sender)) continue;
                    seen.add(sender);

                    results.push({ sender: sender });
                }
                return results;
            }''')

            if not unread_info:
                return []

            self.logger.info(f"Found {len(unread_info)} chats with unread messages")

            for chat_info in unread_info:
                sender = chat_info['sender']
                try:
                    # Click the chat by finding the title span with this sender's name
                    title_span = self.page.locator(
                        f'div[aria-label="Chat list"] span[title="{sender}"]'
                    ).first
                    if not title_span.is_visible(timeout=2000):
                        self.logger.warning(f"Chat title not visible for: {sender}")
                        continue

                    title_span.click()
                    self.page.wait_for_timeout(2000)

                    # Read the latest messages from the opened chat
                    messages_text = self._read_recent_messages()

                    # Get the timestamp shown in the chat header (if any)
                    timestamp_text = ''
                    try:
                        header_el = self.page.query_selector('header span[title]')
                        if header_el:
                            timestamp_text = header_el.inner_text()
                    except Exception:
                        pass

                    # Build timestamp — use current time since WhatsApp shows relative times
                    now = datetime.datetime.now()
                    received = now.isoformat()

                    # Compute deduplication hash
                    content_for_hash = messages_text or ''
                    msg_hash = self._compute_hash(sender, timestamp_text, content_for_hash)

                    if msg_hash not in self.processed_hashes:
                        self.processed_hashes.add(msg_hash)
                        new_messages.append({
                            'sender': sender,
                            'preview': messages_text[:200] if messages_text else '',
                            'messages': messages_text,
                            'received': received,
                            'timestamp_text': timestamp_text,
                            'hash': msg_hash,
                        })

                except Exception as e:
                    self.logger.warning(f"Error reading chat from {sender}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error checking for unread messages: {e}")
            # If the page crashed or disconnected, reset so authenticate() runs again
            if self.page and self.page.is_closed():
                self.page = None

        if new_messages:
            self.logger.info(f"Found {len(new_messages)} new WhatsApp messages")

        return new_messages

    def _read_recent_messages(self) -> str:
        """Read the most recent messages from the currently opened chat pane."""
        try:
            # Use JavaScript to extract message texts — more resilient to DOM changes.
            # Looks for selectable-text spans inside incoming message rows.
            texts = self.page.evaluate('''() => {
                // Try multiple selectors for the message container
                const selectors = [
                    'div.message-in span.selectable-text span',
                    'div.message-in div.copyable-text span',
                    'div[data-testid="msg-container"] span.selectable-text span',
                    'div.message-in span.selectable-text',
                ];

                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    if (els.length > 0) {
                        // Take the last 10 matching elements
                        const recent = Array.from(els).slice(-10);
                        const result = recent
                            .map(el => el.innerText.trim())
                            .filter(t => t.length > 0);
                        if (result.length > 0) return result;
                    }
                }

                // Last resort: grab all copyable-text divs
                const fallback = document.querySelectorAll('div.copyable-text');
                if (fallback.length > 0) {
                    const recent = Array.from(fallback).slice(-10);
                    return recent
                        .map(el => el.innerText.trim())
                        .filter(t => t.length > 0);
                }

                return [];
            }''')

            return '\n'.join(texts) if texts else ''
        except Exception:
            return ''

    def create_action_file(self, item) -> Path:
        """Create a WHATSAPP_<timestamp>_<hash>.md file in Needs_Action/."""
        now = datetime.datetime.now()
        ts = now.strftime('%Y%m%d_%H%M%S')
        # Use first 6 chars of the message hash to avoid filename collisions
        short_hash = item.get('hash', '')[:6]
        filename = f"WHATSAPP_{ts}_{short_hash}.md"
        filepath = self.needs_action / filename

        sender = item.get('sender', 'Unknown')
        received = item.get('received', now.isoformat())
        messages = item.get('messages', item.get('preview', ''))

        content = f"""---
type: whatsapp_message
from: "{sender}"
received: "{received}"
priority: medium
status: pending
---

# WhatsApp Message from {sender}

**Received:** {received}

## Message Content
{messages}

## Suggested Actions
- [ ] Read and assess message content
- [ ] Draft appropriate response following handbook guidelines
- [ ] Check if reply needs approval (new contact policy)
"""
        filepath.write_text(content, encoding='utf-8')
        self.logger.info(f"Created action file: {filename}")
        audit_log(
            action_type='whatsapp_message_detected',
            actor='whatsapp_watcher',
            target=sender,
            parameters={'action_file': filename},
            result='success',
        )
        return filepath

    def _cleanup(self):
        """Close browser resources."""
        try:
            if self.browser_context:
                self.browser_context.close()
        except Exception:
            pass
        try:
            if self._pw_instance:
                self._pw_instance.stop()
        except Exception:
            pass
        self.browser_context = None
        self.page = None
        self._pw_instance = None

    def run(self):
        """Override base run to keep browser open between checks and handle cleanup."""
        self.logger.info(
            f"WhatsAppWatcher started (interval: {self.check_interval}s, headless: {self.headless})"
        )
        try:
            self.authenticate()
            while True:
                try:
                    items = self.check_for_updates()
                    for item in items:
                        self.create_action_file(item)
                except Exception as e:
                    self.logger.error(f"Error during check cycle: {e}")
                    # If browser died, reset so next cycle re-authenticates
                    if self.page and self.page.is_closed():
                        self.page = None
                import time
                time.sleep(self.check_interval)
        except Exception as e:
            self.logger.error(f"WhatsAppWatcher fatal error: {e}")
        finally:
            self._cleanup()
