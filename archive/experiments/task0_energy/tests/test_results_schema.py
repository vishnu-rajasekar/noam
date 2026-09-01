"""Deterministic schema/units sanity tests and failure-reporting tests for
the results parser, using synthetic SQLite fixtures so these run fast and do
not require invoking EnergyPlus."""
import sqlite3

import pytest

from spike.task0_energy.results import (
    EnergySummary,
    ResultSchemaError,
    parse_energy_summary,
    validate_energy_summary,
)

TABULAR_SCHEMA = """
CREATE TABLE TabularDataWithStrings (
    ReportName TEXT,
    TableName TEXT,
    RowName TEXT,
    ColumnName TEXT,
    Value TEXT,
    Units TEXT
);
"""


def _make_sql_fixture(tmp_path, rows, extra_sql_setup=None, zone_names=("ZONE1", "ZONE2")):
    """Build a minimal SQLite file that mimics the subset of EnergyPlus's
    eplusout.sql schema this parser actually reads."""
    db_path = tmp_path / "eplusout.sql"
    connection = sqlite3.connect(str(db_path))
    try:
        connection.executescript(TABULAR_SCHEMA)
        connection.executemany(
            "INSERT INTO TabularDataWithStrings "
            "(ReportName, TableName, RowName, ColumnName, Value, Units) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        connection.commit()
    finally:
        connection.close()
    return str(db_path)


def _peak_rows(zone_names, heating_values, cooling_values):
    rows = []
    for zone, value in zip(zone_names, heating_values):
        rows.append(("HVACSizingSummary", "Zone Sensible Heating", zone, "Calculated Design Load", str(value), "W"))
    for zone, value in zip(zone_names, cooling_values):
        rows.append(("HVACSizingSummary", "Zone Sensible Cooling", zone, "Calculated Design Load", str(value), "W"))
    return rows


class _FakeCollection:
    def __init__(self, total):
        self.total = total


def test_validate_energy_summary_accepts_a_sane_result():
    summary = EnergySummary(
        annual_heating_energy_kwh=1000.0,
        annual_cooling_energy_kwh=800.0,
        peak_heating_load_w=5000.0,
        peak_cooling_load_w=4500.0,
        zone_count=2,
        sql_path="unused",
    )
    validate_energy_summary(summary)  # must not raise


@pytest.mark.parametrize(
    "overrides",
    [
        {"annual_heating_energy_kwh": -1.0},
        {"peak_cooling_load_w": float("nan")},
        {"peak_heating_load_w": float("inf")},
        {"zone_count": 0},
    ],
)
def test_validate_energy_summary_rejects_malformed_values(overrides):
    base = dict(
        annual_heating_energy_kwh=1000.0,
        annual_cooling_energy_kwh=800.0,
        peak_heating_load_w=5000.0,
        peak_cooling_load_w=4500.0,
        zone_count=2,
        sql_path="unused",
    )
    base.update(overrides)
    with pytest.raises(ResultSchemaError):
        validate_energy_summary(EnergySummary(**base))


def test_validate_energy_summary_rejects_all_zero_result():
    summary = EnergySummary(
        annual_heating_energy_kwh=0.0,
        annual_cooling_energy_kwh=0.0,
        peak_heating_load_w=0.0,
        peak_cooling_load_w=0.0,
        zone_count=2,
        sql_path="unused",
    )
    with pytest.raises(ResultSchemaError, match="exactly zero"):
        validate_energy_summary(summary)


def test_parse_energy_summary_reports_missing_peak_table(tmp_path, monkeypatch):
    rows = []  # no HVACSizingSummary rows at all
    sql_path = _make_sql_fixture(tmp_path, rows)

    monkeypatch.setattr(
        "spike.task0_energy.results.SQLiteResult",
        lambda path: _StubSqlResult(
            path,
            {
                "Zone Ideal Loads Supply Air Total Heating Energy": [_FakeCollection(1.0)],
                "Zone Ideal Loads Supply Air Total Cooling Energy": [_FakeCollection(1.0)],
            },
        ),
    )

    with pytest.raises(ResultSchemaError, match="Zone Sensible Heating"):
        parse_energy_summary(sql_path)


def test_parse_energy_summary_reports_missing_annual_output(tmp_path, monkeypatch):
    rows = _peak_rows(("ZONE1",), (5000,), (4000,))
    sql_path = _make_sql_fixture(tmp_path, rows)

    monkeypatch.setattr(
        "spike.task0_energy.results.SQLiteResult",
        lambda path: _StubSqlResult(
            path,
            {
                "Zone Ideal Loads Supply Air Total Heating Energy": [],
                "Zone Ideal Loads Supply Air Total Cooling Energy": [_FakeCollection(1.0)],
            },
        ),
    )

    with pytest.raises(ResultSchemaError, match="Zone Ideal Loads Supply Air Total Heating Energy"):
        parse_energy_summary(sql_path)


def test_parse_energy_summary_rejects_wrong_units(tmp_path, monkeypatch):
    rows = [
        ("HVACSizingSummary", "Zone Sensible Heating", "ZONE1", "Calculated Design Load", "5.0", "kW"),
        ("HVACSizingSummary", "Zone Sensible Cooling", "ZONE1", "Calculated Design Load", "4.0", "W"),
    ]
    sql_path = _make_sql_fixture(tmp_path, rows)

    monkeypatch.setattr(
        "spike.task0_energy.results.SQLiteResult",
        lambda path: _StubSqlResult(
            path,
            {
                "Zone Ideal Loads Supply Air Total Heating Energy": [_FakeCollection(1.0)],
                "Zone Ideal Loads Supply Air Total Cooling Energy": [_FakeCollection(1.0)],
            },
        ),
    )

    with pytest.raises(ResultSchemaError, match="Expected units 'W'"):
        parse_energy_summary(sql_path)


class _StubSqlResult:
    """Stand-in for ladybug.sql.SQLiteResult that returns pre-baked
    timeseries data collections without touching real EnergyPlus SQL."""

    def __init__(self, file_path, collections_by_output):
        self.file_path = file_path
        self._collections_by_output = collections_by_output
        self.available_outputs = list(collections_by_output)

    def data_collections_by_output_name(self, output_name):
        return self._collections_by_output.get(output_name, [])
