"""Behavioural tests for scripts/lib/pick_python.sh -- the interpreter
selection shared by scripts/verify.sh and scripts/noam.sh.

Phase A closure round-1 finding 1: verify.sh's own scan ignored a usable
`python` when `python3` lacked pydantic/PyYAML, so the canonical command
could not pass on such a machine. These tests build fake interpreters (shell
stubs that answer the `import pydantic, yaml` probe) and assert the ordering
and rejection rules directly, without needing a real Python zoo installed.
"""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB = REPO_ROOT / "scripts" / "lib" / "pick_python.sh"

_STUB_TEMPLATE = """#!/bin/sh
# Fake Python interpreter for tests. Answers only the dependency probe.
if [ "$1" = "-c" ]; then
    case "$2" in
        *pydantic*) exit {probe_exit} ;;
    esac
fi
exit 0
"""


def _write_stub(path: Path, *, has_deps: bool) -> None:
    path.write_text(
        _STUB_TEMPLATE.format(probe_exit=0 if has_deps else 1), encoding="utf-8"
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


class InterpreterSelectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.bindir = self.tmp / "bin"
        self.bindir.mkdir()
        self.repo_root = self.tmp / "repo"
        self.repo_root.mkdir()

    def _run(self, func: str, *, path_dirs: list[Path] | None = None,
             env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        dirs = path_dirs if path_dirs is not None else [self.bindir]
        env = {
            "PATH": os.pathsep.join([*(str(d) for d in dirs), "/usr/bin", "/bin"]),
        }
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            ["bash", "-c", f'source "$1"; {func} "$2"', "_", str(LIB), str(self.repo_root)],
            capture_output=True, text=True, env=env,
        )

    def test_picks_python_when_python3_lacks_dependencies(self) -> None:
        _write_stub(self.bindir / "python3", has_deps=False)
        _write_stub(self.bindir / "python", has_deps=True)
        result = self._run("noam_pick_python")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), self.bindir / "python")

    def test_returns_nonzero_when_no_interpreter_has_dependencies(self) -> None:
        _write_stub(self.bindir / "python3", has_deps=False)
        _write_stub(self.bindir / "python", has_deps=False)
        result = self._run("noam_pick_python")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.strip(), "")

    def test_candidate_order_is_deterministic(self) -> None:
        # both usable -> python3 wins because it is earlier in the list
        _write_stub(self.bindir / "python3", has_deps=True)
        _write_stub(self.bindir / "python", has_deps=True)
        result = self._run("noam_pick_python")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), self.bindir / "python3")

    def test_declared_project_environment_wins(self) -> None:
        venv_python = self.repo_root / ".venv-noam" / "bin" / "python"
        venv_python.parent.mkdir(parents=True)
        _write_stub(venv_python, has_deps=True)
        _write_stub(self.bindir / "python3", has_deps=True)
        result = self._run("noam_pick_python")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), venv_python)

    def test_broken_declared_environment_falls_through_to_path(self) -> None:
        # Round-3 finding 1: a .venv-noam/bin/python that exists but cannot
        # import the dependencies must be skipped (not selected), and a
        # usable PATH interpreter used instead.
        venv_python = self.repo_root / ".venv-noam" / "bin" / "python"
        venv_python.parent.mkdir(parents=True)
        _write_stub(venv_python, has_deps=False)
        _write_stub(self.bindir / "python3", has_deps=True)
        result = self._run("noam_pick_python")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), self.bindir / "python3")

    def test_broken_declared_environment_and_no_usable_path_fails(self) -> None:
        venv_python = self.repo_root / ".venv-noam" / "bin" / "python"
        venv_python.parent.mkdir(parents=True)
        _write_stub(venv_python, has_deps=False)
        _write_stub(self.bindir / "python3", has_deps=False)
        result = self._run("noam_require_python")
        self.assertEqual(result.returncode, 1)
        self.assertIn("pydantic", result.stderr)

    def test_honours_noam_python_override(self) -> None:
        override = self.bindir / "my-python"
        _write_stub(override, has_deps=True)
        _write_stub(self.bindir / "python3", has_deps=True)
        result = self._run("noam_pick_python", env_extra={"NOAM_PYTHON": str(override)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), override)

    def test_noam_python_override_rejected_when_deps_missing(self) -> None:
        override = self.bindir / "my-python"
        _write_stub(override, has_deps=False)
        _write_stub(self.bindir / "python3", has_deps=True)
        result = self._run("noam_pick_python", env_extra={"NOAM_PYTHON": str(override)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), self.bindir / "python3")

    def test_require_python_emits_actionable_error(self) -> None:
        _write_stub(self.bindir / "python3", has_deps=False)
        result = self._run("noam_require_python")
        self.assertEqual(result.returncode, 1)
        self.assertIn("pydantic", result.stderr)


if __name__ == "__main__":
    unittest.main()
