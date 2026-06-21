import subprocess
import sys
from pathlib import Path


def test_excited_flag_for_other_name():
    script = Path(__file__).resolve().parents[1] / "src" / "greet_cli.py"
    proc = subprocess.run([sys.executable, str(script), "Grace", "--excited"], text=True, capture_output=True)

    assert proc.returncode == 0
    assert proc.stdout.strip() == "Hello, Grace!"
