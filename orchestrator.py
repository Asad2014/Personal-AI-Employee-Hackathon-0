# orchestrator.py - Main orchestrator for the AI Employee
import os
import sys
import time
import logging
import threading
from pathlib import Path
from watchers.filesystem_watcher import FileSystemWatcher
from claude_processor import process as claude_process

# Gmail watcher is optional — only loaded if credentials exist
try:
    from watchers.gmail_watcher import GmailWatcher
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

# LinkedIn poster is optional — only loaded if playwright is installed
try:
    from watchers.linkedin_poster import LinkedInPoster
    LINKEDIN_AVAILABLE = True
except ImportError:
    LINKEDIN_AVAILABLE = False

# WhatsApp watcher is optional — only loaded if playwright is installed
try:
    from watchers.whatsapp_watcher import WhatsAppWatcher
    WHATSAPP_AVAILABLE = True
except ImportError:
    WHATSAPP_AVAILABLE = False

# Facebook watcher and poster — requires requests + FACEBOOK_ACCESS_TOKEN
try:
    from watchers.facebook_watcher import FacebookWatcher
    from watchers.facebook_poster import FacebookPoster
    FACEBOOK_AVAILABLE = True
except ImportError:
    FACEBOOK_AVAILABLE = False

# Instagram watcher and poster — requires requests + INSTAGRAM_BUSINESS_ACCOUNT_ID
try:
    from watchers.instagram_watcher import InstagramWatcher
    from watchers.instagram_poster import InstagramPoster
    INSTAGRAM_AVAILABLE = True
except ImportError:
    INSTAGRAM_AVAILABLE = False

# Twitter/X watcher and poster — requires requests_oauthlib + TWITTER_API_KEY
try:
    from watchers.twitter_watcher import TwitterWatcher
    from watchers.twitter_poster import TwitterPoster
    TWITTER_AVAILABLE = True
except ImportError:
    TWITTER_AVAILABLE = False

# Approved email sender — watches Approved/ and sends approved email replies
try:
    from watchers.approved_email_sender import ApprovedEmailSender
    EMAIL_SENDER_AVAILABLE = True
except ImportError:
    EMAIL_SENDER_AVAILABLE = False


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_employee.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AI_Employee_Orchestrator')

# How often to check Needs_Action for items to process (seconds)
PROCESS_INTERVAL = int(os.getenv('PROCESS_INTERVAL', '120'))  # default 2 minutes


def run_watcher(vault_path: str):
    """Run the file system watcher in a background thread."""
    try:
        watcher = FileSystemWatcher(vault_path)
        watcher.run()
    except Exception as e:
        logger.error(f"File watcher error: {e}")


def run_gmail_watcher(vault_path: str, credentials_path: str):
    """Run the Gmail watcher in a background thread."""
    try:
        token_path = str(Path(credentials_path).parent / 'token.json')
        watcher = GmailWatcher(vault_path, credentials_path=credentials_path, token_path=token_path)
        watcher.run()
    except Exception as e:
        logger.error(f"Gmail watcher error: {e}")


def run_linkedin_poster(vault_path: str, session_path: str):
    """Run the LinkedIn poster in a background thread."""
    try:
        poster = LinkedInPoster(vault_path, session_path=session_path)
        poster.run()
    except Exception as e:
        logger.error(f"LinkedIn poster error: {e}")


def run_whatsapp_watcher(vault_path: str, session_path: str):
    """Run the WhatsApp watcher in a background thread."""
    try:
        watcher = WhatsAppWatcher(vault_path, session_path=session_path)
        watcher.run()
    except Exception as e:
        logger.error(f"WhatsApp watcher error: {e}")


def run_facebook_watcher(vault_path: str):
    """Run the Facebook watcher in a background thread."""
    try:
        watcher = FacebookWatcher(vault_path)
        watcher.run()
    except Exception as e:
        logger.error(f"Facebook watcher error: {e}")


def run_facebook_poster(vault_path: str):
    """Run the Facebook poster in a background thread."""
    try:
        poster = FacebookPoster(vault_path)
        poster.run()
    except Exception as e:
        logger.error(f"Facebook poster error: {e}")


def run_instagram_watcher(vault_path: str):
    """Run the Instagram watcher in a background thread."""
    try:
        watcher = InstagramWatcher(vault_path)
        watcher.run()
    except Exception as e:
        logger.error(f"Instagram watcher error: {e}")


def run_instagram_poster(vault_path: str):
    """Run the Instagram poster in a background thread."""
    try:
        poster = InstagramPoster(vault_path)
        poster.run()
    except Exception as e:
        logger.error(f"Instagram poster error: {e}")


def run_twitter_watcher(vault_path: str):
    """Run the Twitter watcher in a background thread."""
    try:
        watcher = TwitterWatcher(vault_path)
        watcher.run()
    except Exception as e:
        logger.error(f"Twitter watcher error: {e}")


def run_twitter_poster(vault_path: str):
    """Run the Twitter poster in a background thread."""
    try:
        poster = TwitterPoster(vault_path)
        poster.run()
    except Exception as e:
        logger.error(f"Twitter poster error: {e}")


def run_approved_email_sender(vault_path: str):
    """Run the approved email sender in a background thread."""
    try:
        sender = ApprovedEmailSender(vault_path)
        sender.run()
    except Exception as e:
        logger.error(f"Approved email sender error: {e}")


# Thread registry for health monitoring
_thread_registry: dict[str, dict] = {}
MAX_RESTART_ATTEMPTS = 5


def _register_thread(name: str, target, args: tuple, thread: threading.Thread):
    """Register a thread for health monitoring."""
    _thread_registry[name] = {
        'target': target,
        'args': args,
        'thread': thread,
        'restarts': 0,
    }


def _check_thread_health():
    """Check all registered threads and restart dead ones."""
    for name, info in _thread_registry.items():
        thread = info['thread']
        if not thread.is_alive() and info['restarts'] < MAX_RESTART_ATTEMPTS:
            info['restarts'] += 1
            logger.warning(
                f"Thread '{name}' died. Restarting (attempt {info['restarts']}/{MAX_RESTART_ATTEMPTS})..."
            )
            new_thread = threading.Thread(
                target=info['target'],
                args=info['args'],
                daemon=True,
                name=name,
            )
            new_thread.start()
            info['thread'] = new_thread
            logger.info(f"Thread '{name}' restarted successfully")
        elif not thread.is_alive() and info['restarts'] >= MAX_RESTART_ATTEMPTS:
            logger.error(f"Thread '{name}' exceeded max restart attempts ({MAX_RESTART_ATTEMPTS})")


def processing_loop():
    """Periodically invoke Claude to process Needs_Action items."""
    logger.info(f"Processing loop started (interval: {PROCESS_INTERVAL}s)")
    while True:
        try:
            claude_process()
        except Exception as e:
            logger.error(f"Claude processing error: {e}")
        # Check thread health every processing cycle
        _check_thread_health()
        time.sleep(PROCESS_INTERVAL)


def main():
    logger.info("Starting AI Employee Orchestrator")

    # Get the vault path
    vault_path = os.getenv('VAULT_PATH', './AI_Employee_Vault')
    if not Path(vault_path).exists():
        logger.error(f"Vault path does not exist: {vault_path}")
        return

    logger.info(f"Using vault path: {vault_path}")

    # Start file system watcher in a background thread
    watcher_thread = threading.Thread(
        target=run_watcher,
        args=(vault_path,),
        daemon=True,
        name='FileWatcher',
    )
    watcher_thread.start()
    _register_thread('FileWatcher', run_watcher, (vault_path,), watcher_thread)
    logger.info("File system watcher started in background thread")

    # Start Gmail watcher if credentials are available
    gmail_creds = os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials.json')
    if GMAIL_AVAILABLE and Path(gmail_creds).exists():
        gmail_thread = threading.Thread(
            target=run_gmail_watcher,
            args=(vault_path, gmail_creds),
            daemon=True,
            name='GmailWatcher',
        )
        gmail_thread.start()
        _register_thread('GmailWatcher', run_gmail_watcher, (vault_path, gmail_creds), gmail_thread)
        logger.info("Gmail watcher started in background thread")
    else:
        if not GMAIL_AVAILABLE:
            logger.warning("Gmail watcher unavailable: google-api-python-client not installed")
        else:
            logger.warning(f"Gmail watcher skipped: credentials not found at {gmail_creds}")

    # Start LinkedIn poster if Playwright is available
    if LINKEDIN_AVAILABLE:
        linkedin_session = os.getenv('LINKEDIN_SESSION_PATH', os.path.expanduser('~/.linkedin_session'))
        linkedin_thread = threading.Thread(
            target=run_linkedin_poster,
            args=(vault_path, linkedin_session),
            daemon=True,
            name='LinkedInPoster',
        )
        linkedin_thread.start()
        _register_thread('LinkedInPoster', run_linkedin_poster, (vault_path, linkedin_session), linkedin_thread)
        logger.info("LinkedIn poster started in background thread")
    else:
        logger.warning("LinkedIn poster unavailable: playwright not installed")

    # Start WhatsApp watcher if Playwright is available
    if WHATSAPP_AVAILABLE:
        whatsapp_session = os.getenv('WHATSAPP_SESSION_PATH', os.path.expanduser('~/.whatsapp_session'))
        whatsapp_thread = threading.Thread(
            target=run_whatsapp_watcher,
            args=(vault_path, whatsapp_session),
            daemon=True,
            name='WhatsAppWatcher',
        )
        whatsapp_thread.start()
        _register_thread('WhatsAppWatcher', run_whatsapp_watcher, (vault_path, whatsapp_session), whatsapp_thread)
        logger.info("WhatsApp watcher started in background thread")
    else:
        logger.warning("WhatsApp watcher unavailable: playwright not installed")

    # Start Facebook watcher and poster if token is available
    if FACEBOOK_AVAILABLE and os.getenv('FACEBOOK_ACCESS_TOKEN'):
        fb_watcher_thread = threading.Thread(
            target=run_facebook_watcher,
            args=(vault_path,),
            daemon=True,
            name='FacebookWatcher',
        )
        fb_watcher_thread.start()
        _register_thread('FacebookWatcher', run_facebook_watcher, (vault_path,), fb_watcher_thread)
        logger.info("Facebook watcher started in background thread")

        fb_poster_thread = threading.Thread(
            target=run_facebook_poster,
            args=(vault_path,),
            daemon=True,
            name='FacebookPoster',
        )
        fb_poster_thread.start()
        _register_thread('FacebookPoster', run_facebook_poster, (vault_path,), fb_poster_thread)
        logger.info("Facebook poster started in background thread")
    else:
        if not FACEBOOK_AVAILABLE:
            logger.warning("Facebook integration unavailable: requests not installed")
        else:
            logger.warning("Facebook integration skipped: FACEBOOK_ACCESS_TOKEN not set")

    # Start Instagram watcher and poster if token and IG account ID are available
    if INSTAGRAM_AVAILABLE and os.getenv('FACEBOOK_ACCESS_TOKEN') and os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID'):
        ig_watcher_thread = threading.Thread(
            target=run_instagram_watcher,
            args=(vault_path,),
            daemon=True,
            name='InstagramWatcher',
        )
        ig_watcher_thread.start()
        _register_thread('InstagramWatcher', run_instagram_watcher, (vault_path,), ig_watcher_thread)
        logger.info("Instagram watcher started in background thread")

        ig_poster_thread = threading.Thread(
            target=run_instagram_poster,
            args=(vault_path,),
            daemon=True,
            name='InstagramPoster',
        )
        ig_poster_thread.start()
        _register_thread('InstagramPoster', run_instagram_poster, (vault_path,), ig_poster_thread)
        logger.info("Instagram poster started in background thread")
    else:
        if not INSTAGRAM_AVAILABLE:
            logger.warning("Instagram integration unavailable: requests not installed")
        else:
            logger.warning("Instagram integration skipped: FACEBOOK_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID not set")

    # Start Twitter/X watcher and poster if API keys are available
    if TWITTER_AVAILABLE and os.getenv('TWITTER_API_KEY'):
        tw_watcher_thread = threading.Thread(
            target=run_twitter_watcher,
            args=(vault_path,),
            daemon=True,
            name='TwitterWatcher',
        )
        tw_watcher_thread.start()
        _register_thread('TwitterWatcher', run_twitter_watcher, (vault_path,), tw_watcher_thread)
        logger.info("Twitter watcher started in background thread")

        tw_poster_thread = threading.Thread(
            target=run_twitter_poster,
            args=(vault_path,),
            daemon=True,
            name='TwitterPoster',
        )
        tw_poster_thread.start()
        _register_thread('TwitterPoster', run_twitter_poster, (vault_path,), tw_poster_thread)
        logger.info("Twitter poster started in background thread")
    else:
        if not TWITTER_AVAILABLE:
            logger.warning("Twitter integration unavailable: requests_oauthlib not installed")
        else:
            logger.warning("Twitter integration skipped: TWITTER_API_KEY not set")

    # Start Approved Email Sender (Local agent — sends approved email replies)
    agent_mode = os.getenv('AGENT_MODE', 'local')
    if EMAIL_SENDER_AVAILABLE and agent_mode == 'local' and Path(gmail_creds).exists():
        email_sender_thread = threading.Thread(
            target=run_approved_email_sender,
            args=(vault_path,),
            daemon=True,
            name='ApprovedEmailSender',
        )
        email_sender_thread.start()
        _register_thread('ApprovedEmailSender', run_approved_email_sender, (vault_path,), email_sender_thread)
        logger.info("Approved email sender started in background thread (Local agent)")
    elif agent_mode == 'cloud':
        logger.info("Approved email sender skipped: Cloud agent does not send emails")

    # Run the Claude processing loop on the main thread
    try:
        processing_loop()
    except KeyboardInterrupt:
        logger.info("Orchestrator stopped by user")
    except Exception as e:
        logger.error(f"Error in orchestrator: {e}")
        raise


if __name__ == "__main__":
    main()
