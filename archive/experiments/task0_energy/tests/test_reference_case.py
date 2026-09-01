"""Real end-to-end EnergyPlus integration test for the Task 0 exit criteria:
a valid IDF is produced via Honeybee's direct writer, the pinned EnergyPlus
26.1 executable actually runs it, and declared annual/peak heating and
cooling outputs are parsed with explicit units."""
import json
import os

from spike.task0_energy.results import EnergySummary


def test_reference_case_produces_a_schema_valid_energy_summary(reference_case_result):
    summary = reference_case_result.summary
    assert isinstance(summary, EnergySummary)

    for field_name, unit in EnergySummary.UNITS.items():
        value = getattr(summary, field_name)
        assert isinstance(value, float)
        assert value == value  # not NaN
        assert value >= 0.0
        assert unit in ("kWh", "W")

    # Chicago is heating- and cooling-mixed (ASHRAE 5A): a two-floor generic
    # office should show non-trivial demand on every declared metric.
    assert summary.annual_heating_energy_kwh > 0
    assert summary.annual_cooling_energy_kwh > 0
    assert summary.peak_heating_load_w > 0
    assert summary.peak_cooling_load_w > 0
    assert summary.zone_count == 2


def test_reference_case_preserves_raw_energyplus_logs(reference_case_result):
    assert os.path.isfile(reference_case_result.idf_path)
    assert os.path.isfile(reference_case_result.sql_path)
    assert os.path.isfile(reference_case_result.err_path)
    assert os.path.isfile(reference_case_result.html_path)

    with open(reference_case_result.err_path) as handle:
        err_contents = handle.read()
    assert "EnergyPlus Completed Successfully" in err_contents or "Fatal" not in err_contents


def test_reference_case_writes_reproducibility_metadata(reference_case_result):
    assert os.path.isfile(reference_case_result.metadata_path)
    with open(reference_case_result.metadata_path) as handle:
        metadata = json.load(handle)

    assert metadata["dependency_versions"]["honeybee_energy"] != "unknown"
    assert metadata["dependency_versions"]["energyplus"].startswith("26.1")
    assert metadata["weather"]["source"].startswith("bundled with local EnergyPlus")
    assert "declared_outputs" in metadata
    assert metadata["declared_outputs"]["annual_heating_energy_kwh"]["unit"] == "kWh"
    assert metadata["declared_outputs"]["peak_heating_load_w"]["unit"] == "W"
    assert len(metadata["modelling_assumptions"]) > 0
