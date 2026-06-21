#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def exists(path: str) -> bool:
    return Path(path).exists()


def run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return ''


def grep(pattern: str, paths: list[str]) -> bool:
    for base in paths:
        p = Path(base)
        if not p.exists():
            continue
        files = [p] if p.is_file() else [x for x in p.rglob('*') if x.is_file()]
        for f in files:
            try:
                if pattern in f.read_text(encoding='utf-8', errors='ignore'):
                    return True
            except Exception:
                pass
    return False


checks = [
    ('P4 20-task Mini-Repo-Debug dataset', exists('data/mini_repo_debug/tasks') or exists('data/mini_repo_debug'), 'dataset present'),
    ('P5 SFT/preference export CLI', exists('codeguide_agent/dataset/export_training_candidates.py'), 'export_training_candidates.py'),
    ('P6 train package builder', exists('codeguide_agent/dataset/prepare_training_package.py'), 'prepare_training_package.py'),
    ('P7 dry-run trainer', exists('codeguide_agent/training/dry_run_train.py'), 'dry_run_train.py'),
    ('P7 replay eval', exists('codeguide_agent/training/replay_eval.py'), 'replay_eval.py'),
    ('P8 experiment creation', exists('codeguide_agent/training/create_experiment.py'), 'create_experiment.py'),
    ('P8 mock artifact', exists('codeguide_agent/training/mock_train_artifact.py'), 'mock_train_artifact.py'),
    ('P8 trained policy interface', exists('codeguide_agent/training/trained_policy.py'), 'trained_policy.py'),
    ('P9 preference bank expansion', exists('codeguide_agent/dataset/expand_preference_candidates.py'), 'expand_preference_candidates.py'),
    ('P10 full pipeline validator', exists('scripts/validate_mini_repo_pipeline.sh'), 'validate_mini_repo_pipeline.sh'),
    ('P10 summary snapshot', exists('docs/snapshots/mini_repo_debug_p4_p10_summary.md'), 'p4-p10 summary snapshot'),
    ('P10.1 generated-trajectory-independent tests', exists('codeguide_agent/testing/mini_repo_trajectory_fixture.py'), 'mini_repo_trajectory_fixture.py'),
    ('P11 Makefile entrypoints', exists('Makefile') and grep('clean-check', ['Makefile']), 'Makefile clean-check'),
    ('P11 reproducible runbook', exists('docs/P11_REPRODUCIBLE_RUNBOOK.md'), 'P11 runbook'),
    ('P12 project story', exists('docs/PROJECT_STORY.md'), 'PROJECT_STORY.md'),
    ('P13 GitHub CI', exists('.github/workflows/mini_repo_debug_ci.yml'), 'GitHub Actions workflow'),
    ('P13 release check', exists('scripts/release_check.sh'), 'release_check.sh'),
    ('P14 interview docs', exists('docs/INTERVIEW_PROJECT_BRIEF.md') and exists('docs/RESUME_BULLETS.md'), 'interview brief + resume bullets'),
    ('P15 model-facing audit', exists('scripts/audit_model_facing_artifacts.sh') and grep('audit:', ['Makefile']), 'make audit'),
]

tags = run(['git', 'tag', '--list'])
tag_checks = [
    ('stable P11 tag', 'mini-repo-debug-p4-p11-stable' in tags, 'mini-repo-debug-p4-p11-stable'),
    ('P13 CI tag', 'mini-repo-debug-p13-ci' in tags, 'mini-repo-debug-p13-ci'),
    ('P14 docs tag', 'mini-repo-debug-p14-interview-docs' in tags, 'mini-repo-debug-p14-interview-docs'),
    ('P15 audit tag', 'mini-repo-debug-p15-audit' in tags, 'mini-repo-debug-p15-audit'),
]

all_checks = checks + tag_checks
passed = [c for c in all_checks if c[1]]
failed = [c for c in all_checks if not c[1]]

print('# Design Completion Check')
print()
for name, ok, note in all_checks:
    mark = 'PASS' if ok else 'MISS'
    print(f'- [{mark}] {name}: {note}')
print()
print(f'Passed: {len(passed)} / {len(all_checks)}')

out = {
    'passed': len(passed),
    'total': len(all_checks),
    'missing': [{'name': n, 'note': note} for n, ok, note in failed],
}
Path('docs/design_completion_report.json').write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')

if failed:
    raise SystemExit(1)
