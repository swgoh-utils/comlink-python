"""Guard release identity and serialization, including an advanced checkout."""

import os
import re
import subprocess
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/release.yml"


def test_release_pins_checkout_and_serializes_publish_and_tag():
    workflow = WORKFLOW.read_text()
    assert "ref: ${{ github.sha }}" in workflow
    assert "ref: ${{ github.ref_name }}" not in workflow
    assert "\nconcurrency:\n" in workflow
    assert "\n    concurrency:\n" not in workflow
    assert 'echo "sha=${sha}"' in workflow
    assert '--target "${{ needs.build.outputs.sha }}"' in workflow


def test_release_rejects_checkout_other_than_dispatched_commit(tmp_path):
    workflow = WORKFLOW.read_text()
    guard = re.search(r"          sha=.*\n          test .*\n", workflow).group()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    git = ["git", "-C", str(tmp_path), "-c", "user.name=Test", "-c", "user.email=test@example.invalid"]
    subprocess.run([*git, "commit", "--allow-empty", "-qm", "first"], check=True)
    first = subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()
    env = {**os.environ, "GITHUB_SHA": first}
    assert subprocess.run(["bash", "-ec", guard], cwd=tmp_path, env=env).returncode == 0
    subprocess.run([*git, "commit", "--allow-empty", "-qm", "second"], check=True)
    assert subprocess.run(["bash", "-ec", guard], cwd=tmp_path, env=env).returncode != 0
