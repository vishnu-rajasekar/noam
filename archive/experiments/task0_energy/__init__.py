"""Task 0 feasibility spike: neutral rectangular office -> Honeybee Energy
direct IDF writing -> EnergyPlus.

This package is a bounded, deterministic proof of the local simulation path
described in TASKS.md ("Task 0"). It is not the Noam application core and must
not be imported by Task 1+ product code.
"""

import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LADYBUG_HOME = os.path.join(_PROJECT_ROOT, ".ladybug_home")


def _ensure_ladybug_home() -> None:
    """Point ladybug-tools' self-managed cache folder at a project-local
    writable directory instead of the real $HOME.

    ladybug.config builds a module-level Folders() instance at import time
    that reads/creates "$HOME/ladybug_tools". Under this project's sandbox
    policy, "~/" is denied for reads, which turns that into an unhandled
    PermissionError on the very first honeybee/honeybee_energy import.

    This must override HOME unconditionally (not os.environ.setdefault):
    HOME is set in essentially every normal process, so setdefault would be
    a silent no-op and this function would provide no isolation at all for
    any entry point that does not separately export a HOME override first.
    """
    os.makedirs(os.path.join(_LADYBUG_HOME, "ladybug_tools"), exist_ok=True)
    os.environ["HOME"] = _LADYBUG_HOME


_ensure_ladybug_home()
