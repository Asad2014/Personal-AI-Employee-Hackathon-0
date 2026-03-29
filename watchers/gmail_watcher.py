# gmail_watcher.py - Monitors Gmail for unread important emails
import datetime
import base64
from pathlib import Path
from watchers.base_watcher import BaseWatcher
from utils.audit_logger import audit_log
from utils.retry_handler import with_retry

# Google API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
]


class GmailWatcher(BaseWatcher):
    def __init__(self, vault_path: str, credentials_path: str = 'credentials.json',
                 token_path: str = 'token.json', check_interval: int = 120):
        super().__init__(vault_path, check_interval)
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.processed_ids = set()
        self.service = None

        # Load already-processed email IDs from existing files in Needs_Action and Done
        self._load_processed_ids()

    def _load_processed_ids(self):
        """Scan Needs_Action/ and Done/ for existing EMAIL_* files to avoid reprocessing."""
        for folder in [self.needs_action, self.vault_path / 'Done']:
            if folder.exists():
                for f in folder.glob('EMAIL_*.md'):
                    # Extract message ID from filename: EMAIL_<message_id>.md
                    msg_id = f.stem.replace('EMAIL_', '')
                    self.processed_ids.add(msg_id)
        self.logger.info(f"Loaded {len(self.processed_ids)} previously processed email IDs")

    def authenticate(self):
        """Handle OAuth2 flow — opens browser on first run, reuses token after."""
        creds = None

        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for subsequent runs
            self.token_path.write_text(creds.to_json())

        self.service = build('gmail', 'v1', credentials=creds)
        self.logger.info("Gmail API authenticated successfully")

    @with_retry(max_attempts=3, base_delay=2, max_delay=60)
    def check_for_updates(self) -> list:
        """Fetch unread important emails from Gmail."""
        if not self.service:
            self.authenticate()

        results = self.service.users().messages().list(
            userId='me',
            q='is:unread is:important',
            maxResults=10
        ).execute()

        messages = results.get('messages', [])
        new_emails = []

        for msg in messages:
            if msg['id'] not in self.processed_ids:
                # Fetch full message details
                full_msg = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                new_emails.append(full_msg)
                self.processed_ids.add(msg['id'])

        if new_emails:
            self.logger.info(f"Found {len(new_emails)} new important emails")

        return new_emails

    def create_action_file(self, item) -> Path:
        """Create an EMAIL_<id>.md file in Needs_Action/ for a Gmail message."""
        msg_id = item['id']
        headers = {h['name']: h['value'] for h in item['payload']['headers']}

        sender = headers.get('From', 'Unknown')
        subject = headers.get('Subject', 'No Subject')
        date = headers.get('Date', datetime.datetime.now().isoformat())

        # Extract body snippet
        snippet = item.get('snippet', '')

        # Try to get the plain text body
        body = self._extract_body(item['payload'])

        filename = f"EMAIL_{msg_id}.md"
        filepath = self.needs_action / filename

        content = f"""---
type: email
from: "{sender}"
subject: "{subject}"
received: "{date}"
priority: high
status: pending
gmail_id: "{msg_id}"
---

# Email from {sender}

**Subject:** {subject}
**Date:** {date}

## Content
{body if body else snippet}

## Suggested Actions
- [ ] Read and assess email content
- [ ] Draft appropriate response following handbook guidelines
- [ ] Check if reply needs approval (new contact policy)
"""
        filepath.write_text(content, encoding='utf-8')
        self.logger.info(f"Created action file: {filename}")
        audit_log(
            action_type='email_detected',
            actor='gmail_watcher',
            target=sender,
            parameters={'subject': subject, 'gmail_id': msg_id, 'action_file': filename},
            result='success',
        )
        return filepath

    def _extract_body(self, payload):
        """Extract plain text body from Gmail message payload."""
        if payload.get('mimeType') == 'text/plain' and payload.get('body', {}).get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')

        # Check parts for multipart messages
        parts = payload.get('parts', [])
        for part in parts:
            if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
            # Recurse into nested parts
            if part.get('parts'):
                result = self._extract_body(part)
                if result:
                    return result

        return None
