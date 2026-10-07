"""Re-run local quality checks without model credentials or billable calls."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
commands = [['verify_setup.py'], ['-m', 'unittest', 'discover', '-s', 'tests', '-v'],
            ['evals/compare.py', '--mode', 'offline', '--repeat', '3'],
            ['evals/replay_guards.py'], ['scripts/check_secrets.py']]
for command in commands:
    result = subprocess.run([sys.executable, *command], cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)
print('All offline checks passed. Live evaluation is a separate explicit command.')
