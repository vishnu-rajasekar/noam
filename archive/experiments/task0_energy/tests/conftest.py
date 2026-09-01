import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pytest

import spike.task0_energy  # noqa: E402,F401  bootstraps HOME before any honeybee import
from spike.task0_energy.building import OfficeBuildingParameters
from spike.task0_energy.reference_case import run_reference_case


@pytest.fixture(scope="session")
def reference_case_result(tmp_path_factory):
    """Run the real Task 0 pipeline (Honeybee direct IDF -> EnergyPlus 26.1)
    exactly once for the whole test session and share the result.

    Uses a small two-floor building to keep the EnergyPlus run fast while
    still exercising the full multi-zone, multi-storey path.
    """
    evidence_dir = tmp_path_factory.mktemp("task0_evidence")
    params = OfficeBuildingParameters(floor_count=2)
    return run_reference_case(params, str(evidence_dir))
