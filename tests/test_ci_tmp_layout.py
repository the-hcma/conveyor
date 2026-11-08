"""The uv and pytest CI wrappers re-exec through with-tmp-layout (repository-helpers#832)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_WRAPPERS = {
    "assert-uv-lock-version": ["uv"],
    "python-static": ["uv"],
    "pytest-hermetic": ["uv", "pytest"],
    "setup-python": ["uv"],
}


def _run(
    wrapper: str, tmp_path: Path, helpers: Path, **env: str
) -> subprocess.CompletedProcess[str]:
    """Run a wrapper with the layout variables cleared and the helper clone set to ``helpers``."""

    base = {
        key: value
        for key, value in os.environ.items()
        if key not in {"CI_TMP_LAYOUT", "GITHUB_ACTIONS", "REPOSITORY_HELPERS_DIR"}
    }
    base.update(HOME=str(tmp_path), REPOSITORY_HELPERS_DIR=str(helpers), TMPDIR=str(tmp_path))
    base.update(env)
    return subprocess.run(
        ["bash", str(_REPO_ROOT / ".github" / "ci" / wrapper)],
        cwd=_REPO_ROOT,
        env=base,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("wrapper", sorted(_WRAPPERS))
def test_ci_without_the_layout_helper_fails_with_a_pointer_to_the_action(
    wrapper: str, tmp_path: Path
) -> None:
    """In GitHub Actions a missing helper is an error that names the action to add."""

    result = _run(wrapper, tmp_path, tmp_path / "none", GITHUB_ACTIONS="true")
    assert result.returncode == 1
    assert "setup-tmp-layout" in result.stderr


@pytest.mark.parametrize("wrapper", sorted(_WRAPPERS))
def test_the_wrapper_runs_under_the_expected_layout_tools(wrapper: str, tmp_path: Path) -> None:
    """Each wrapper nests the layouts of the tools it runs, outermost first."""

    helpers = tmp_path / "helpers"
    (helpers / "scripts" / "dev").mkdir(parents=True)
    fake = helpers / "scripts" / "dev" / "with-tmp-layout"
    # Record the tool of this layer, then stop: the nested layers are what is under test.
    fake.write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s\\n\' "$1" >> "$TMPDIR/layout-tools"\n'
        'if [[ "$3" == "$(dirname "$0")/with-tmp-layout" ]]; then shift 2; exec "$@"; fi\n'
        "exit 0\n"
    )
    fake.chmod(0o755)
    result = _run(wrapper, tmp_path, helpers)
    assert result.returncode == 0
    assert (tmp_path / "layout-tools").read_text().split() == _WRAPPERS[wrapper]
