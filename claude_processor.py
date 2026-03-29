# claude_processor.py - Triggers Claude Code to process Needs_Action items
import os
import shutil
import subprocess
import logging
import datetime
from pathlib import Path
from utils.audit_logger import audit_log
from utils.ralph_wiggum import create_loop_state, get_active_loops, check_completion, cleanup_completed

logger = logging.getLogger('ClaudeProcessor')

VAULT_PATH = Path(os.getenv('VAULT_PATH', './AI_Employee_Vault'))
NEEDS_ACTION = VAULT_PATH / 'Needs_Action'
IN_PROGRESS = VAULT_PATH / 'In_Progress'
UPDATES_PATH = VAULT_PATH / 'Updates'
LOGS_PATH = VAULT_PATH / 'Logs'
PROJECT_ROOT = Path(__file__).parent.resolve()
AGENT_MODE = os.getenv('AGENT_MODE', 'local')  # 'cloud' or 'local'


def _claim_file(filepath: Path) -> Path | None:
    """Claim-by-move: move file from Needs_Action/ to In_Progress/<agent>/.
    Returns the new path if claimed, None if already claimed by another agent."""
    agent_dir = IN_PROGRESS / AGENT_MODE
    agent_dir.mkdir(parents=True, exist_ok=True)

    # Check if the other agent already claimed it
    other_agent = 'local' if AGENT_MODE == 'cloud' else 'cloud'
    other_dir = IN_PROGRESS / other_agent
    if (other_dir / filepath.name).exists():
        logger.info(f'Skipping {filepath.name}: already claimed by {other_agent} agent')
        return None

    # Claim it
    dest = agent_dir / filepath.name
    try:
        shutil.move(str(filepath), str(dest))
        logger.info(f'Claimed {filepath.name} → In_Progress/{AGENT_MODE}/')
        return dest
    except Exception as e:
        logger.warning(f'Failed to claim {filepath.name}: {e}')
        return None


def get_pending_files() -> list[Path]:
    """Return list of .md files in Needs_Action/ with status: pending."""
    if not NEEDS_ACTION.exists():
        return []
    pending = []
    for f in sorted(NEEDS_ACTION.glob('*.md')):
        try:
            text = f.read_text(encoding='utf-8')
            # Quick check: only process files that still have status: pending
            if 'status: pending' in text:
                pending.append(f)
        except Exception as e:
            logger.warning(f'Could not read {f.name}: {e}')
    return pending


def build_prompt(files: list[Path]) -> str:
    """Build the prompt that tells Claude what to process."""
    file_list = '\n'.join(f'- {f.name}' for f in files)

    # Cloud mode: draft-only, never send directly
    if AGENT_MODE == 'cloud':
        cloud_rules = (
            '\n\nCLOUD AGENT RULES (MANDATORY):\n'
            '- You are running as the CLOUD agent. You must NEVER send emails directly.\n'
            '- For ALL emails: use draft_email MCP tool (NOT send_email). Never call send_email.\n'
            '- For ALL actions: create an approval file in Pending_Approval/ for the Local agent.\n'
            '- Do NOT post to any social media directly. Only create draft files in Pending_Approval/.\n'
            '- The Local agent (human) will review approvals and execute final send/post actions.\n'
            '- Write processing updates to AI_Employee_Vault/Updates/ instead of editing Dashboard.md directly.\n'
        )
    else:
        cloud_rules = ''

    work_dir = f'AI_Employee_Vault/In_Progress/{AGENT_MODE}'
    return (
        f'You are the AI Employee ({AGENT_MODE} agent). Process the following items in '
        f'{work_dir}/ using the /process-inbox skill.\n\n'
        f'Files to process:\n{file_list}\n\n'
        f'IMPORTANT — Plan Generation (Read → Think → Plan → Act):\n'
        f'For each item, assess its complexity BEFORE acting:\n'
        f'- If the item is type "task", or requires 2+ steps to complete, '
        f'use /create-plan to generate a Plan.md in AI_Employee_Vault/Plans/ first.\n'
        f'- For simple items (file categorization, acknowledgments), process directly.\n'
        f'- Plans must include: objective, numbered steps with checkboxes, '
        f'approval gates (per Company Handbook), and resource links.\n\n'
        f'After processing, update the dashboard using /update-dashboard.\n'
        f'Follow all rules in AI_Employee_Vault/Company_Handbook.md.'
        f'{cloud_rules}'
    )


def _build_env() -> dict:
    """Build environment for Claude subprocess, adding router vars if configured."""
    env = os.environ.copy()
    # If ANTHROPIC_BASE_URL is set (e.g. for Gemini router), pass it through.
    # Also support CLAUDE_CONFIG_DIR for alternate API key config.
    for var in ('ANTHROPIC_BASE_URL', 'CLAUDE_CONFIG_DIR', 'GOOGLE_API_KEY', 'AGENT_MODE'):
        val = os.getenv(var)
        if val:
            env[var] = val
    return env


def invoke_claude(prompt: str) -> tuple[bool, str]:
    """Invoke claude CLI in non-interactive mode and return (success, output)."""
    cmd = [
        'claude',
        '--print',          # non-interactive, output only
        '--dangerously-skip-permissions',  # unattended mode
        prompt,
    ]
    logger.info('Invoking Claude Code...')
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per run
            env=_build_env(),
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            err = result.stderr.strip()
            logger.error(f'Claude returned non-zero exit code {result.returncode}: {err}')
            return False, err or output
        logger.info('Claude finished processing successfully')
        return True, output
    except FileNotFoundError:
        msg = 'claude CLI not found. Ensure Claude Code is installed and on PATH.'
        logger.error(msg)
        return False, msg
    except subprocess.TimeoutExpired:
        msg = 'Claude processing timed out after 5 minutes'
        logger.error(msg)
        return False, msg
    except Exception as e:
        logger.error(f'Error invoking Claude: {e}')
        return False, str(e)


def log_result(success: bool, output: str, file_count: int):
    """Append processing result to today's log file."""
    LOGS_PATH.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    log_file = LOGS_PATH / f'{today}.md'
    now = datetime.datetime.now().strftime('%H:%M:%S')

    if not log_file.exists():
        log_file.write_text(f'# Activity Log - {today}\n\n')

    status = 'success' if success else 'error'
    entry = (
        f'## {now} - Claude Processor Run\n'
        f'- **Files queued:** {file_count}\n'
        f'- **Result:** {status}\n'
        f'- **Output preview:** {output[:300]}\n\n'
    )
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(entry)


def _merge_dashboard_updates():
    """Single-writer Dashboard rule: only Local agent merges Updates/ into Dashboard.md."""
    if AGENT_MODE != 'local':
        return
    UPDATES_PATH.mkdir(parents=True, exist_ok=True)
    updates = sorted(UPDATES_PATH.glob('*.md'))
    if not updates:
        return

    dashboard = VAULT_PATH / 'Dashboard.md'
    for update_file in updates:
        if update_file.name == '.gitkeep':
            continue
        try:
            update_text = update_file.read_text(encoding='utf-8').strip()
            if not update_text:
                update_file.unlink()
                continue

            # Append cloud update to Dashboard
            with open(dashboard, 'a', encoding='utf-8') as f:
                f.write(f'\n\n## Cloud Update ({update_file.stem})\n{update_text}\n')

            logger.info(f'Merged dashboard update: {update_file.name}')
            update_file.unlink()
        except Exception as e:
            logger.warning(f'Failed to merge update {update_file.name}: {e}')


def _is_complex_task(filepath: Path) -> bool:
    """Check if a file represents a complex task that needs the Ralph Wiggum loop."""
    try:
        text = filepath.read_text(encoding='utf-8')
        return 'type: task' in text
    except Exception:
        return False


def process():
    """Main processing loop — check for pending files and invoke Claude."""
    # First, check active Ralph Wiggum loops
    active_loops = get_active_loops()
    for state_file in active_loops:
        result = check_completion(state_file)
        if result['should_continue']:
            logger.info(f'Ralph Wiggum loop continuing (iteration {result["iteration"]})')
            success, output = invoke_claude(result['prompt'])
            log_result(success, output, 1)
            audit_log(
                action_type='ralph_wiggum_iteration',
                actor='claude_processor',
                target=state_file.name,
                parameters={'iteration': result['iteration']},
                result='success' if success else 'failure',
            )
    cleanup_completed()

    files = get_pending_files()
    if not files:
        logger.info('No pending items in Needs_Action/')
        # Merge dashboard updates if local agent
        _merge_dashboard_updates()
        return False

    # Claim-by-move: move files to In_Progress/<agent>/
    claimed_files = []
    for f in files:
        claimed = _claim_file(f)
        if claimed:
            claimed_files.append(claimed)

    if not claimed_files:
        logger.info('No files claimed (all taken by other agent)')
        _merge_dashboard_updates()
        return False

    # Check for complex tasks that need Ralph Wiggum loop
    complex_tasks = [f for f in claimed_files if _is_complex_task(f)]
    for task_file in complex_tasks:
        create_loop_state(str(task_file), build_prompt([task_file]))
        logger.info(f'Created Ralph Wiggum loop for complex task: {task_file.name}')

    logger.info(f'Found {len(claimed_files)} claimed item(s) to process')
    prompt = build_prompt(claimed_files)
    success, output = invoke_claude(prompt)
    log_result(success, output, len(claimed_files))
    audit_log(
        action_type='claude_processing_run',
        actor='claude_processor',
        target=f'In_Progress/{AGENT_MODE}',
        parameters={'file_count': len(claimed_files), 'files': [f.name for f in claimed_files]},
        result='success' if success else 'failure',
        error_message='' if success else output[:200],
    )

    # Merge dashboard updates if local agent
    _merge_dashboard_updates()
    return success


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('ai_employee.log'),
            logging.StreamHandler(),
        ],
    )
    process()
