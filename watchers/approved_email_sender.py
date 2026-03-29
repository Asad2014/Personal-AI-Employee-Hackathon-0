# approved_email_sender.py - Watches Approved/ for email responses and sends via Gmail API
import os
import re
import shutil
import datetime
import logging
import time
import json
from pathlib import Path
from utils.audit_logger import audit_log
from utils.retry_handler import with_retry

logger = logging.getLogger('ApprovedEmailSender')


class ApprovedEmailSender:
    """Watches Approved/ for files with type: email_response and sends via Gmail API."""

    def __init__(self, vault_path: str, check_interval: int = 30):
        self.vault_path = Path(vault_path)
        self.approved = self.vault_path / 'Approved'
        self.done = self.vault_path / 'Done'
        self.logs = self.vault_path / 'Logs'
        self.check_interval = check_interval

        # Gmail API setup
        self.service = None
        self._init_gmail()

        # Ensure directories exist
        self.approved.mkdir(parents=True, exist_ok=True)
        self.done.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)

    def _init_gmail(self):
        """Initialize Gmail API service."""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds_path = os.getenv('GMAIL_CREDENTIALS_PATH', './credentials.json')
            token_path = os.getenv('GMAIL_TOKEN_PATH', './token.json')

            if not Path(token_path).exists():
                logger.error(f"Gmail token not found at {token_path}")
                return

            creds = Credentials.from_authorized_user_file(token_path)
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API initialized for ApprovedEmailSender")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail API: {e}")

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

    def _extract_body(self, filepath: Path) -> str:
        """Extract the email body from the approval file."""
        text = filepath.read_text(encoding='utf-8')
        # Remove frontmatter
        cleaned = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, count=1, flags=re.DOTALL)
        # Remove markdown headers and formatting, extract plain text body
        lines = []
        for line in cleaned.splitlines():
            # Skip header lines and metadata lines
            if line.startswith('## ') or line.startswith('**To:') or line.startswith('**Subject:') or line.startswith('**Action:') or line.startswith('---'):
                continue
            lines.append(line)
        return '\n'.join(lines).strip()

    def check_for_approved_emails(self) -> list:
        """Scan Approved/ for files with type: email_response."""
        emails = []
        if not self.approved.exists():
            return emails
        for filepath in self.approved.glob('*.md'):
            fm = self._parse_frontmatter(filepath)
            if fm.get('type') == 'email_response':
                emails.append(filepath)
        return emails

    @with_retry(max_attempts=2, base_delay=5, max_delay=30)
    def send_email(self, filepath: Path) -> bool:
        """Send an approved email via Gmail API."""
        if not self.service:
            logger.error("Gmail API not initialized")
            return False

        fm = self._parse_frontmatter(filepath)
        to = fm.get('to', '')
        subject = fm.get('subject', '')
        body = self._extract_body(filepath)

        if not to or not body:
            logger.warning(f"Missing 'to' or body in {filepath.name}, skipping")
            return False

        try:
            import base64
            from email.mime.text import MIMEText

            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject

            # Add In-Reply-To header if gmail_id exists
            in_reply_to = fm.get('in_reply_to', '')
            if in_reply_to:
                message['In-Reply-To'] = in_reply_to
                message['References'] = in_reply_to

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            result = self.service.users().messages().send(
                userId='me', body={'raw': raw}
            ).execute()

            msg_id = result.get('id', 'unknown')
            logger.info(f"Sent email from {filepath.name} to {to} (msg_id: {msg_id})")
            audit_log(
                action_type='email_send',
                actor='approved_email_sender',
                target=to,
                parameters={'subject': subject, 'file': filepath.name, 'msg_id': msg_id},
                approval_status='approved',
                result='success',
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send email from {filepath.name}: {e}")
            audit_log(
                action_type='email_send',
                actor='approved_email_sender',
                target=to,
                parameters={'subject': subject, 'file': filepath.name},
                result='failure',
                error_message=str(e),
            )
            return False

    def _move_to_done(self, filepath: Path):
        """Move a sent email file to Done/."""
        dest = self.done / filepath.name
        shutil.move(str(filepath), str(dest))
        logger.info(f"Moved {filepath.name} to Done/")

        # Also move the source email file if it exists in Needs_Action
        fm = self._parse_frontmatter(dest)
        source_file = fm.get('source_file', '')
        if source_file:
            source_path = self.vault_path / 'Needs_Action' / source_file
            if source_path.exists():
                shutil.move(str(source_path), str(self.done / source_file))
                logger.info(f"Moved source file {source_file} to Done/")

    def _log_action(self, filepath: Path, to: str, success: bool):
        """Log the email send action to today's log file."""
        today = datetime.date.today().isoformat()
        now = datetime.datetime.now().strftime('%H:%M:%S')
        log_file = self.logs / f"{today}.md"

        status = 'success' if success else 'error'
        entry = (
            f"\n## {now} - Email Sent: {filepath.name}\n"
            f"- **Type:** email_response (approved)\n"
            f"- **To:** {to}\n"
            f"- **Action Taken:** Sent via Gmail API\n"
            f"- **Result:** {status}\n"
        )

        if log_file.exists():
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(entry)
        else:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"# Activity Log - {today}\n{entry}")

    def run(self):
        """Main loop — check for approved emails and send them."""
        logger.info(f"ApprovedEmailSender started (interval: {self.check_interval}s)")
        while True:
            try:
                emails = self.check_for_approved_emails()
                for filepath in emails:
                    fm = self._parse_frontmatter(filepath)
                    to = fm.get('to', 'unknown')
                    logger.info(f"Found approved email: {filepath.name} → {to}")
                    success = self.send_email(filepath)
                    self._log_action(filepath, to, success)
                    if success:
                        self._move_to_done(filepath)
            except Exception as e:
                logger.error(f"ApprovedEmailSender error: {e}")
            time.sleep(self.check_interval)
