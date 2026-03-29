# utils/audit_logger.py - Structured JSON audit logging
import json
import os
import datetime
import logging
from pathlib import Path

logger = logging.getLogger('AuditLogger')

VAULT_PATH = Path(os.getenv('VAULT_PATH', './AI_Employee_Vault'))
LOGS_PATH = VAULT_PATH / 'Logs'


def audit_log(
    action_type: str,
    actor: str,
    target: str = '',
    parameters: dict | None = None,
    approval_status: str = 'n/a',
    result: str = 'success',
    error_message: str = '',
):
    """Write a structured JSON audit log entry to today's JSON log file.

    Args:
        action_type: Type of action (e.g. email_send, file_process, linkedin_post)
        actor: Who performed the action (e.g. claude_code, gmail_watcher, filesystem_watcher)
        target: Target of the action (e.g. recipient email, filename)
        parameters: Additional parameters dict
        approval_status: approved / pending / rejected / n/a
        result: success / failure / pending
        error_message: Error details if result is failure
    """
    LOGS_PATH.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    log_file = LOGS_PATH / f'{today}.json'

    entry = {
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'action_type': action_type,
        'actor': actor,
        'target': target,
        'parameters': parameters or {},
        'approval_status': approval_status,
        'result': result,
    }
    if error_message:
        entry['error_message'] = error_message

    # Append JSON entry (one JSON object per line — JSONL format)
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        logger.error(f'Failed to write audit log: {e}')


def read_audit_logs(date: str | None = None) -> list[dict]:
    """Read audit log entries for a given date (YYYY-MM-DD). Defaults to today."""
    if date is None:
        date = datetime.date.today().isoformat()
    log_file = LOGS_PATH / f'{date}.json'
    if not log_file.exists():
        return []
    entries = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except Exception as e:
        logger.error(f'Failed to read audit log for {date}: {e}')
    return entries
