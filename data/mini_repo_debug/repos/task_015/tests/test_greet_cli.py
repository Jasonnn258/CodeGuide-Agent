import subprocess
import sys
from pathlib import Path


def test_default_cli_greeting_still_works():
    script = Path(__file__).resolve().parents[1] / "src" / "greet_cli.py"
    proc = subprocess.run([sys.executable, str(script), "Ada"], text=True, capture_output=True)

    assert proc.returncode == 0
    assert proc.stdout.strip() == "Hello, Ada"


def test_excited_flag_adds_exclamation():
    script = Path(__file__).resolve().parents[1] / "src" / "greet_cli.py"
    proc = subprocess.run([sys.executable, str(script), "Ada", "--excited"], text=True, capture_output=True)

    assert proc.returncode == 0
    assert proc.stdout.strip() == "Hello, Ada!"
