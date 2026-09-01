"""Failure-reporting tests against the real EnergyPlus executable: invalid
input must raise a specific, diagnosable error rather than fail silently or
report a false pass."""
import os

import pytest

from spike.task0_energy.simulate import configure_energyplus, run_energyplus

EP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".tools",
    "energyplus-26.1.0",
)
EPW_PATH = os.path.join(
    EP_DIR, "WeatherData", "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
)


@pytest.fixture(scope="module", autouse=True)
def _configure():
    configure_energyplus(EP_DIR)


def test_invalid_idf_raises_runtime_error_with_err_log_tail(tmp_path):
    idf_path = tmp_path / "in.idf"
    idf_path.write_text("THIS IS NOT A VALID IDF FILE\n")

    with pytest.raises(RuntimeError) as excinfo:
        run_energyplus(str(idf_path), EPW_PATH)

    message = str(excinfo.value)
    assert "did not produce a result SQL file" in message
    assert "not a valid Object Type" in message or "Errors occurred on processing input file" in message

    err_path = tmp_path / "eplusout.err"
    assert err_path.is_file()


def test_missing_epw_path_is_reported(tmp_path):
    idf_path = tmp_path / "in.idf"
    idf_path.write_text("Version,26.1;\n")

    with pytest.raises(Exception):
        run_energyplus(str(idf_path), str(tmp_path / "does_not_exist.epw"))


def test_configure_energyplus_rejects_unknown_install_dir(tmp_path):
    from spike.task0_energy.simulate import configure_energyplus as configure

    # honeybee_energy.config.folders itself asserts on a missing executable;
    # configure_energyplus() does not swallow or soften that failure.
    with pytest.raises(AssertionError, match="not a valid path to an energyplus installation"):
        configure(str(tmp_path / "not_a_real_install"))
