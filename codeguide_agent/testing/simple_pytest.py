from __future__ import annotations

import argparse
import importlib.util
import inspect
import tempfile
import traceback
from pathlib import Path


def discover(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            files.extend(sorted(path.rglob("test_*.py")))
        elif path.is_file():
            files.append(path)
    return files


def load_module(path: Path):
    name = f"_codeguide_test_{abs(hash(path.resolve()))}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_test_function(func) -> None:
    signature = inspect.signature(func)
    kwargs = {}
    temp_dirs: list[tempfile.TemporaryDirectory[str]] = []
    try:
        if "tmp_path" in signature.parameters:
            temp_dir = tempfile.TemporaryDirectory()
            temp_dirs.append(temp_dir)
            kwargs["tmp_path"] = Path(temp_dir.name)
        func(**kwargs)
    finally:
        for temp_dir in temp_dirs:
            temp_dir.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(description="Small pytest-compatible runner for Mini-Repo-Debug tests.")
    parser.add_argument("targets", nargs="*", default=["tests"])
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    files = discover([target for target in args.targets if target != "-q"])
    failures = []
    total = 0
    for file_path in files:
        try:
            module = load_module(file_path)
            tests = [(name, value) for name, value in vars(module).items() if name.startswith("test_") and callable(value)]
            for name, func in tests:
                total += 1
                try:
                    run_test_function(func)
                    if not args.quiet:
                        print(f"PASS {file_path}::{name}")
                except Exception:
                    failures.append((file_path, name, traceback.format_exc()))
                    if not args.quiet:
                        print(f"FAIL {file_path}::{name}")
        except Exception:
            failures.append((file_path, "<module>", traceback.format_exc()))

    if failures:
        for file_path, name, tb in failures:
            print(f"\nFAILED {file_path}::{name}")
            print(tb)
        print(f"{len(failures)} failed, {total - len(failures)} passed")
        return 1

    print(f"{total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
