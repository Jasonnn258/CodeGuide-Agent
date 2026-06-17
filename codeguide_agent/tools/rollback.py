from __future__ import annotations

from pathlib import Path
import shutil

from codeguide_agent.tools.common import checkpoint_root, resolve_repo_path


def rollback(repo_path: str | Path) -> dict:
    try:
        root = resolve_repo_path(repo_path)
        checkpoints = checkpoint_root(root)
        latest = checkpoints / "LATEST"
        if not latest.exists():
            return {"tool_name": "rollback", "status": "error", "error": "no checkpoint available"}
        checkpoint_id = latest.read_text(encoding="utf-8").strip()
        checkpoint = checkpoints / checkpoint_id
        restored = []
        for backup in checkpoint.rglob("*"):
            if not backup.is_file():
                continue
            relative = backup.relative_to(checkpoint)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            restored.append(str(relative))
        shutil.rmtree(checkpoint)
        remaining = sorted(path.name for path in checkpoints.iterdir() if path.is_dir())
        if remaining:
            latest.write_text(remaining[-1], encoding="utf-8")
        else:
            latest.unlink(missing_ok=True)
        return {"tool_name": "rollback", "status": "success", "checkpoint_id": checkpoint_id, "restored_files": restored}
    except Exception as exc:
        return {"tool_name": "rollback", "status": "error", "error": str(exc)}
