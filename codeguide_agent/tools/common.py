from __future__ import annotations

from pathlib import Path
import shutil
import time


CHECKPOINT_DIR = ".codeguide_checkpoints"


def resolve_repo_path(repo_path: str | Path, relative_path: str | Path | None = None) -> Path:
    root = Path(repo_path).resolve()
    if relative_path is None:
        return root
    target = (root / relative_path).resolve()
    if root != target and root not in target.parents:
        raise ValueError(f"path escapes repo: {relative_path}")
    return target


def checkpoint_root(repo_path: str | Path) -> Path:
    return resolve_repo_path(repo_path) / CHECKPOINT_DIR


def create_checkpoint(repo_path: str | Path, file_path: str | Path) -> dict[str, str]:
    root = resolve_repo_path(repo_path)
    target = resolve_repo_path(root, file_path)
    if not target.exists():
        raise FileNotFoundError(str(file_path))
    checkpoint_dir = checkpoint_root(root)
    checkpoint_dir.mkdir(exist_ok=True)
    checkpoint_id = f"{int(time.time() * 1000)}"
    backup = checkpoint_dir / checkpoint_id / str(file_path)
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup)
    latest = checkpoint_dir / "LATEST"
    latest.write_text(checkpoint_id, encoding="utf-8")
    return {"checkpoint_id": checkpoint_id, "backup_path": str(backup)}
