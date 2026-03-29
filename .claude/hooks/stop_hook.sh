#!/bin/bash
# stop_hook.sh - Ralph Wiggum stop hook
# Intercepts Claude exit to check if complex tasks are fully completed.
# If an active loop state file exists and the task isn't in Done/,
# this hook signals Claude to continue processing.

STATE_DIR="${RALPH_STATE_DIR:-.ralph_state}"
VAULT_PATH="${VAULT_PATH:-./AI_Employee_Vault}"

# If no state directory exists, allow exit
if [ ! -d "$STATE_DIR" ]; then
    exit 0
fi

# Check each active loop state file
for state_file in "$STATE_DIR"/loop_*.json; do
    [ -f "$state_file" ] || continue

    # Read state using python3 (json parsing)
    result=$(python3 -c "
import json, sys
from pathlib import Path

state = json.loads(Path('$state_file').read_text())
if state.get('status') != 'active':
    sys.exit(0)

source_name = Path(state['source_file']).name
done_path = Path('$VAULT_PATH') / 'Done' / source_name

if done_path.exists():
    state['status'] = 'completed'
    Path('$state_file').write_text(json.dumps(state, indent=2))
    print('COMPLETED')
elif state.get('iteration', 0) >= state.get('max_iterations', 10):
    state['status'] = 'max_iterations_reached'
    Path('$state_file').write_text(json.dumps(state, indent=2))
    print('MAX_ITERATIONS')
else:
    state['iteration'] = state.get('iteration', 0) + 1
    Path('$state_file').write_text(json.dumps(state, indent=2))
    print('CONTINUE:' + state['prompt'])
" 2>/dev/null)

    if [[ "$result" == CONTINUE:* ]]; then
        prompt="${result#CONTINUE:}"
        echo "Ralph Wiggum: Task not complete. Re-injecting prompt (iteration $(python3 -c "import json; print(json.loads(open('$state_file').read()).get('iteration',0))" 2>/dev/null))..."
        echo "$prompt"
        exit 1  # Non-zero exit prevents Claude from stopping
    fi
done

# All tasks complete or no active loops — allow exit
exit 0
