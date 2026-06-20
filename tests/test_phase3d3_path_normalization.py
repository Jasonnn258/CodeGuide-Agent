from pathlib import Path

from codeguide_agent.reward.hacking_checks import leakage_detected
from codeguide_agent.tools.edit_file import edit_file
from codeguide_agent.tools.read_file import read_file


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "pricing.py").write_text("class PriceService:\n    pass\n", encoding="utf-8")
    return repo


def test_read_file_absolute_workspace_path_normalizes_to_relative(tmp_path: Path):
    repo = _repo(tmp_path)
    absolute = repo / "src" / "pricing.py"

    result = read_file(repo, absolute)

    assert result["status"] == "success"
    assert result["file"] == "src/pricing.py"
    assert "PriceService" in result["content"]


def test_edit_file_absolute_workspace_path_edits_and_checkpoint_is_separate(tmp_path: Path):
    repo = _repo(tmp_path)
    absolute = repo / "src" / "pricing.py"

    result = edit_file(repo, absolute, "pass", "value = 1")

    assert result["status"] == "success"
    assert result["file"] == "src/pricing.py"
    assert (repo / "src" / "pricing.py").read_text(encoding="utf-8") == "class PriceService:\n    value = 1\n"
    assert Path(result["backup_path"]).resolve() != absolute.resolve()
    assert ".codeguide_checkpoints" in result["backup_path"]


def test_absolute_path_outside_workspace_is_rejected(tmp_path: Path):
    repo = _repo(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_text("secret", encoding="utf-8")

    result = read_file(repo, outside)

    assert result["status"] == "error"
    assert "escapes repo" in result["error"]


def test_path_traversal_is_rejected(tmp_path: Path):
    repo = _repo(tmp_path)

    result = edit_file(repo, "../outside.py", "x", "y")

    assert result["status"] == "error"
    assert "escapes repo" in result["error"]


def test_normalized_legal_read_edit_is_not_leakage(tmp_path: Path):
    repo = _repo(tmp_path)
    absolute = str(repo / "src" / "pricing.py")
    rows = [
        {
            "type": "step",
            "action_name": "repo_tree",
            "action_input": {"max_depth": 4},
            "observation": {"entries": ["src/", "src/pricing.py"]},
        },
        {
            "type": "step",
            "action_name": "read_file",
            "action_input": {"file_path": "src/pricing.py"},
            "observation": {"file": "src/pricing.py", "content": "class PriceService:\n    pass\n"},
        },
        {
            "type": "step",
            "action_name": "edit_file",
            "action_input": {"file_path": "src/pricing.py", "old_text": "pass", "new_text": "value = 1"},
            "observation": {"file": "src/pricing.py", "status": "success", "original_absolute": absolute},
        },
    ]

    result = leakage_detected(rows, ["src/pricing.py"], ["PriceService"])

    assert result["leakage_detected"] is False
    assert result["forbidden_file_access"] is False


def test_forbidden_paths_still_leak():
    rows = [
        {
            "type": "step",
            "action_name": "read_file",
            "action_input": {"file_path": "gold.patch"},
            "observation": {"status": "success"},
        }
    ]

    result = leakage_detected(rows, ["src/pricing.py"], ["PriceService"])

    assert result["leakage_detected"] is True
    assert result["forbidden_file_access"] is True
