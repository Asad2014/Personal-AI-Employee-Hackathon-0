# utils/ralph_wiggum.py - Autonomous multi-step task completion loop
#
# Named after the "I'm in danger" meme — the loop keeps Claude running
# until a complex task is fully completed (file moved to Done/).
#
# Flow:
# 1. Claude processor detects a complex task (type: task)
# 2. Creates a state file tracking the task
# 3. Claude processes, tries to exit
# 4. Stop hook checks: is the source file in Done/?
# 5. NO → re-injects the prompt, loop continues
# 6. YES → allows exit
# 7. Safety: max iterations limit prevents infinite loops

import os
import json
import datetime
import logging
from pathlib import Path

logger = logging.getLogger('RalphWiggum')

VAULT_PATH = Path(os.getenv('VAULT_PATH', './AI_Employee_Vault'))
STATE_DIR = Path(os.getenv('RALPH_STATE_DIR', '.ralph_state'))
MAX_ITERATIONS = int(os.getenv('RALPH_MAX_ITERATIONS', '10'))


def create_loop_state(source_file: str, prompt: str) -> Path:
    """Create a state file for a Ralph Wiggum loop.

    Args:
        source_file: The Needs_Action/ file being processed
        prompt: The prompt to re-inject on each iteration

    Returns:
        Path to the state file
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    state = {
        'source_file': source_file,
        'prompt': prompt,
        'iteration': 0,
        'max_iterations': MAX_ITERATIONS,
        'created': datetime.datetime.now().isoformat(),
        'status': 'active',
    }

    state_file = STATE_DIR / f'loop_{Path(source_file).stem}.json'
    state_file.write_text(json.dumps(state, indent=2))
    logger.info(f'Ralph Wiggum loop created for {source_file}')
    return state_file


def check_completion(state_file: Path) -> dict:
    """Check if the task tracked by this state file is complete.

    Returns:
        dict with keys: completed (bool), should_continue (bool), prompt (str), iteration (int)
    """
    if not state_file.exists():
        return {'completed': True, 'should_continue': False, 'prompt': '', 'iteration': 0}

    state = json.loads(state_file.read_text())

    # Check if source file has been moved to Done/
    source_name = Path(state['source_file']).name
    done_path = VAULT_PATH / 'Done' / source_name

    if done_path.exists():
        state['status'] = 'completed'
        state_file.write_text(json.dumps(state, indent=2))
        logger.info(f'Task completed: {source_name} found in Done/')
        return {'completed': True, 'should_continue': False, 'prompt': '', 'iteration': state['iteration']}

    # Check iteration limit
    state['iteration'] += 1
    if state['iteration'] >= state['max_iterations']:
        state['status'] = 'max_iterations_reached'
        state_file.write_text(json.dumps(state, indent=2))
        logger.warning(f'Max iterations ({MAX_ITERATIONS}) reached for {source_name}')
        return {'completed': False, 'should_continue': False, 'prompt': '', 'iteration': state['iteration']}

    # Task not done, continue looping
    state_file.write_text(json.dumps(state, indent=2))
    logger.info(f'Iteration {state["iteration"]}/{MAX_ITERATIONS} for {source_name} — continuing')
    return {
        'completed': False,
        'should_continue': True,
        'prompt': state['prompt'],
        'iteration': state['iteration'],
    }


def get_active_loops() -> list[Path]:
    """Return all active loop state files."""
    if not STATE_DIR.exists():
        return []
    return [
        f for f in STATE_DIR.glob('loop_*.json')
        if json.loads(f.read_text()).get('status') == 'active'
    ]


def cleanup_completed():
    """Remove state files for completed or expired loops."""
    if not STATE_DIR.exists():
        return
    for f in STATE_DIR.glob('loop_*.json'):
        try:
            state = json.loads(f.read_text())
            if state.get('status') in ('completed', 'max_iterations_reached'):
                f.unlink()
                logger.info(f'Cleaned up state file: {f.name}')
        except Exception:
            pass
