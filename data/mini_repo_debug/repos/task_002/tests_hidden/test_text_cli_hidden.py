import subprocess
import sys
from pathlib import Path


def test_cli_uppercase_flag_prints_uppercase():
    script = Path(__file__).resolve().parents[1] / "src" / "text_cli.py"
    proc = subprocess.run([sys.executable, str(script), "Hello", "--uppercase"], text=True, capture_output=True)

    assert proc.returncode == 0
    assert proc.stdout.strip() == "HELLO"


def test_default_still_lowercases():
    script = Path(__file__).resolve().parents[1] / "src" / "text_cli.py"
    proc = subprocess.run([sys.executable, str(script), "Hello"], text=True, capture_output=True)

    assert proc.stdout.strip() == "hello"
