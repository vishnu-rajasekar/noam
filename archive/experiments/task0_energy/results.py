"""Parse declared annual and peak heating/cooling results from an EnergyPlus
SQL output, with explicit units and a deterministic schema/units sanity check.

Two distinct EnergyPlus outputs are used, both requested explicitly by
``simulate.build_simulation_parameter`` rather than relying on defaults:

- Annual heating/cooling energy [kWh]: the sum, over the annual run period,
  of each zone's "Zone Ideal Loads Supply Air Total {Heating,Cooling}
  Energy" timeseries output (honeybee-energy's ideal-air equivalent HVAC).
- Peak heating/cooling load [W]: the "Calculated Design Load" row of the
  HVACSizingSummary report's "Zone Sensible {Heating,Cooling}" table, summed
  across zones. This is EnergyPlus's own ASHRAE 99.6%/0.4% design-day zone
  sizing result, not a maximum sampled from the annual hourly run.

This is a feasibility-case result reader, not a compliance or code-review
calculation; see AGENTS.md's product boundary.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Dict

from ladybug.sql import SQLiteResult

ANNUAL_HEATING_OUTPUT = "Zone Ideal Loads Supply Air Total Heating Energy"
ANNUAL_COOLING_OUTPUT = "Zone Ideal Loads Supply Air Total Cooling Energy"
PEAK_HEATING_TABLE = "Zone Sensible Heating"
PEAK_COOLING_TABLE = "Zone Sensible Cooling"
PEAK_REPORT_NAME = "HVACSizingSummary"
PEAK_COLUMN_NAME = "Calculated Design Load"


class ResultSchemaError(ValueError):
    """Raised when the SQL result does not contain the declared outputs in
    the expected shape, so callers get an explicit, named failure instead of
    a silently wrong or missing number."""


@dataclass(frozen=True)
class EnergySummary:
    """Declared annual and peak heating/cooling results, with units fixed
    by convention: energy in kWh, load in W."""

    annual_heating_energy_kwh: float
    annual_cooling_energy_kwh: float
    peak_heating_load_w: float
    peak_cooling_load_w: float
    zone_count: int
    sql_path: str

    UNITS = {
        "annual_heating_energy_kwh": "kWh",
        "annual_cooling_energy_kwh": "kWh",
        "peak_heating_load_w": "W",
        "peak_cooling_load_w": "W",
    }


def _annual_energy_kwh(sql_result: SQLiteResult, output_name: str) -> tuple[float, int]:
    collections = sql_result.data_collections_by_output_name(output_name)
    if not collections:
        raise ResultSchemaError(
            f"EnergyPlus SQL result at {sql_result.file_path!r} has no "
            f"timeseries data for declared output {output_name!r}. Available "
            f"outputs: {sql_result.available_outputs!r}"
        )
    total_kwh = sum(collection.total for collection in collections)
    return float(total_kwh), len(collections)


def _peak_load_w(sql_path: str, table_name: str) -> float:
    connection = sqlite3.connect(sql_path)
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT RowName, Value, Units FROM TabularDataWithStrings "
            "WHERE ReportName = ? AND TableName = ? AND ColumnName = ?",
            (PEAK_REPORT_NAME, table_name, PEAK_COLUMN_NAME),
        )
        rows = cursor.fetchall()
    finally:
        connection.close()

    if not rows:
        raise ResultSchemaError(
            f"EnergyPlus SQL result at {sql_path!r} has no "
            f"{PEAK_REPORT_NAME}/{table_name!r} '{PEAK_COLUMN_NAME}' rows. "
            "This report requires design-day sizing periods to have been "
            "configured (see simulate.build_simulation_parameter)."
        )

    total_w = 0.0
    for row_name, value, units in rows:
        if units != "W":
            raise ResultSchemaError(
                f"Expected units 'W' for {table_name!r} '{PEAK_COLUMN_NAME}' "
                f"row {row_name!r}, got {units!r}."
            )
        try:
            total_w += float(value)
        except (TypeError, ValueError) as exc:
            raise ResultSchemaError(
                f"Non-numeric value {value!r} for {table_name!r} row "
                f"{row_name!r} in {sql_path!r}."
            ) from exc
    return total_w


def parse_energy_summary(sql_path: str) -> EnergySummary:
    """Parse annual and peak heating/cooling results from an EnergyPlus SQL
    output file. Raises ResultSchemaError with a specific, named reason if
    any declared output is missing or malformed."""
    sql_result = SQLiteResult(sql_path)

    annual_heating_kwh, heating_zone_count = _annual_energy_kwh(
        sql_result, ANNUAL_HEATING_OUTPUT
    )
    annual_cooling_kwh, cooling_zone_count = _annual_energy_kwh(
        sql_result, ANNUAL_COOLING_OUTPUT
    )
    if heating_zone_count != cooling_zone_count:
        raise ResultSchemaError(
            f"Zone count mismatch between heating ({heating_zone_count}) and "
            f"cooling ({cooling_zone_count}) outputs in {sql_path!r}."
        )

    peak_heating_w = _peak_load_w(sql_path, PEAK_HEATING_TABLE)
    peak_cooling_w = _peak_load_w(sql_path, PEAK_COOLING_TABLE)

    summary = EnergySummary(
        annual_heating_energy_kwh=annual_heating_kwh,
        annual_cooling_energy_kwh=annual_cooling_kwh,
        peak_heating_load_w=peak_heating_w,
        peak_cooling_load_w=peak_cooling_w,
        zone_count=heating_zone_count,
        sql_path=sql_path,
    )
    validate_energy_summary(summary)
    return summary


def validate_energy_summary(summary: EnergySummary) -> None:
    """Deterministic schema/units sanity check: every declared metric must be
    a finite, non-negative number, zone_count must be positive, and at least
    one of the four metrics must be non-zero (an all-zero result indicates
    the HVAC/output wiring did not take effect, not a legitimate outcome for
    this reference case)."""
    values: Dict[str, float] = {
        "annual_heating_energy_kwh": summary.annual_heating_energy_kwh,
        "annual_cooling_energy_kwh": summary.annual_cooling_energy_kwh,
        "peak_heating_load_w": summary.peak_heating_load_w,
        "peak_cooling_load_w": summary.peak_cooling_load_w,
    }
    for name, value in values.items():
        if not isinstance(value, float) or value != value or value in (float("inf"), float("-inf")):
            raise ResultSchemaError(f"{name} is not a finite number: {value!r}")
        if value < 0:
            raise ResultSchemaError(f"{name} is negative: {value!r}")
    if summary.zone_count < 1:
        raise ResultSchemaError(f"zone_count must be >= 1, got {summary.zone_count!r}")
    if all(value == 0.0 for value in values.values()):
        raise ResultSchemaError(
            "All four declared energy/load metrics are exactly zero; this "
            "indicates the ideal-air HVAC or output request did not take "
            "effect rather than a legitimate zero-load result."
        )
