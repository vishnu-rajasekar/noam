"""Regression test: importing spike.task0_energy must redirect $HOME to a
project-local directory unconditionally, not only when $HOME happens to be
unset already (os.environ.setdefault would be a no-op in any normal process,
since HOME is essentially always set)."""
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_package_import_overrides_an_already_set_home():
    env = dict(os.environ)
    env["HOME"] = "/Users/apple"  # simulate a normal process with a real HOME
    env["PYTHONPATH"] = REPO_ROOT
    result = subprocess.run(
        [sys.executable, "-c", "import spike.task0_energy, os; print(os.environ['HOME'])"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    reported_home = result.stdout.strip()
    assert reported_home != "/Users/apple"
    assert reported_home.endswith(".ladybug_home")
