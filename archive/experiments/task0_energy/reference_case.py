"""End-to-end Task 0 deterministic reference case.

Builds the rectangular office model, writes a plain IDF via Honeybee's direct
writer, runs it through the pinned EnergyPlus executable, parses the declared
annual/peak heating and cooling results, and writes an evidence bundle
(raw EnergyPlus logs + reproducibility metadata + parsed results) to disk.

Usage:
    python -m spike.task0_energy.reference_case [--evidence-dir PATH]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import platform
import sys
from datetime import datetime, timezone

import spike.task0_energy  # noqa: F401  (bootstraps HOME before any honeybee import)
from spike.task0_energy.building import OfficeBuildingParameters, build_office_model
from spike.task0_energy.results import EnergySummary, parse_energy_summary
from spike.task0_energy.simulate import (
    build_simulation_parameter,
    configure_energyplus,
    preserve_run_directory,
    run_energyplus,
    write_idf,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENERGYPLUS_INSTALL_DIR = os.path.join(REPO_ROOT, ".tools", "energyplus-26.1.0")
WEATHER_DIR = os.path.join(ENERGYPLUS_INSTALL_DIR, "WeatherData")

#: Local EnergyPlus-bundled TMY3 weather file used for this reference case.
#: Chicago O'Hare is ASHRAE climate zone 5A (cold/mixed-humid), which
#: exercises both heating- and cooling-dominated periods in one annual run.
#: No weather data is downloaded; this file ships with the pinned
#: EnergyPlus 26.1.0 install already present in .tools/.
WEATHER_FILE_BASENAME = "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3"
EPW_PATH = os.path.join(WEATHER_DIR, f"{WEATHER_FILE_BASENAME}.epw")
DDY_PATH = os.path.join(WEATHER_DIR, f"{WEATHER_FILE_BASENAME}.ddy")

DEFAULT_EVIDENCE_DIR = os.path.join(REPO_ROOT, "spike", "task0_energy", "_evidence")


def run_reference_case(
    params: OfficeBuildingParameters, evidence_dir: str
) -> "ReferenceCaseResult":
    """Run the full Task 0 pipeline once and return its evidence paths."""
    if not os.path.isfile(EPW_PATH):
        raise FileNotFoundError(
            f"Missing local weather file: {EPW_PATH!r}. This reference case "
            "requires a local EnergyPlus-bundled EPW/DDY pair and does not "
            "download weather data."
        )
    if not os.path.isfile(DDY_PATH):
        raise FileNotFoundError(
            f"Missing local design-day file: {DDY_PATH!r}. Required for "
            "ASHRAE 99.6%/0.4% zone sizing of the ideal-air systems."
        )

    energyplus_version = configure_energyplus(ENERGYPLUS_INSTALL_DIR)

    model = build_office_model(params)
    sim_par = build_simulation_parameter(DDY_PATH)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = os.path.join(evidence_dir, f"run_{run_id}")
    idf_path = os.path.join(run_dir, "in.idf")
    write_idf(model, sim_par, idf_path)

    ep_run = run_energyplus(idf_path, EPW_PATH)
    summary = parse_energy_summary(ep_run.sql_path)

    metadata = build_reproducibility_metadata(
        params=params,
        energyplus_version=energyplus_version,
        epw_path=EPW_PATH,
        ddy_path=DDY_PATH,
        summary=summary,
    )
    metadata_path = os.path.join(run_dir, "reproducibility_metadata.json")
    with open(metadata_path, "w") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    return ReferenceCaseResult(
        run_directory=run_dir,
        idf_path=idf_path,
        sql_path=ep_run.sql_path,
        err_path=ep_run.err_path,
        html_path=ep_run.html_path,
        metadata_path=metadata_path,
        summary=summary,
    )


def build_reproducibility_metadata(
    params: OfficeBuildingParameters,
    energyplus_version: str,
    epw_path: str,
    ddy_path: str,
    summary: EnergySummary,
) -> dict:
    return {
        "task": "Task 0 -- feasibility and deterministic reference case",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": {
            "machine": platform.machine(),
            "system": platform.system(),
            "release": platform.release(),
            "python_version": sys.version,
        },
        "dependency_versions": {
            "honeybee_energy": _package_version("honeybee_energy"),
            "honeybee_core": _package_version("honeybee"),
            "honeybee_standards": _package_version("honeybee_standards"),
            "ladybug_core": _package_version("ladybug"),
            "energyplus": energyplus_version,
        },
        "model_parameters": dataclasses.asdict(params),
        "modelling_path": "honeybee_energy.writer.model_to_idf (direct IDF write, no OpenStudio)",
        "weather": {
            "epw_path": epw_path,
            "ddy_path": ddy_path,
            "source": "bundled with local EnergyPlus 26.1.0 install "
            "(.tools/energyplus-26.1.0/WeatherData); not downloaded",
        },
        "sizing": "ASHRAE 99.6% heating / 0.4% cooling design days via "
        "SizingParameter.add_from_ddy_996_004; ideal-air capacities left at "
        "honeybee-energy's Autosize default",
        "declared_outputs": {
            "annual_heating_energy_kwh": {
                "value": summary.annual_heating_energy_kwh,
                "unit": summary.UNITS["annual_heating_energy_kwh"],
                "source": "Zone Ideal Loads Supply Air Total Heating Energy "
                "(sum over annual run period, all zones)",
            },
            "annual_cooling_energy_kwh": {
                "value": summary.annual_cooling_energy_kwh,
                "unit": summary.UNITS["annual_cooling_energy_kwh"],
                "source": "Zone Ideal Loads Supply Air Total Cooling Energy "
                "(sum over annual run period, all zones)",
            },
            "peak_heating_load_w": {
                "value": summary.peak_heating_load_w,
                "unit": summary.UNITS["peak_heating_load_w"],
                "source": "HVACSizingSummary / Zone Sensible Heating / "
                "Calculated Design Load (sum over zones)",
            },
            "peak_cooling_load_w": {
                "value": summary.peak_cooling_load_w,
                "unit": summary.UNITS["peak_cooling_load_w"],
                "source": "HVACSizingSummary / Zone Sensible Cooling / "
                "Calculated Design Load (sum over zones)",
            },
            "zone_count": summary.zone_count,
        },
        "modelling_assumptions": [
            "Program type: honeybee-energy standards library "
            "'Generic Office Program' applied uniformly to every floor.",
            "Constructions: honeybee-energy standards library "
            "'Default Generic Construction Set' applied uniformly.",
            "HVAC: honeybee-energy IdealAirSystem equivalent per zone "
            "(no plant/system equipment or distribution losses modelled).",
            "One thermal zone per floor; no internal partitioning.",
            "Interior floor/ceiling adjacencies solved automatically "
            "(Surface boundary condition); ground floor slab is Ground, "
            "top floor roof is Outdoors.",
            "Window-to-wall ratio applied uniformly to all exterior walls "
            "via wall_apertures_by_ratio; no explicit shading devices.",
            "Peak loads are EnergyPlus's own ASHRAE 99.6%/0.4% design-day "
            "zone sizing result, not a maximum sampled from the annual "
            "hourly run.",
        ],
        "explicit_non_claims": [
            "This is a feasibility/reference case, not a compliance or "
            "code-review calculation (see AGENTS.md product boundary).",
            "No validation against a measured or third-party-verified "
            "reference case has been performed.",
        ],
    }


def _package_version(package_name: str) -> str:
    from importlib.metadata import version, PackageNotFoundError

    try:
        return version(package_name.replace("_", "-"))
    except PackageNotFoundError:
        try:
            return version(package_name)
        except PackageNotFoundError:
            return "unknown"


@dataclasses.dataclass(frozen=True)
class ReferenceCaseResult:
    run_directory: str
    idf_path: str
    sql_path: str
    err_path: str
    html_path: str
    metadata_path: str
    summary: EnergySummary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-dir",
        default=DEFAULT_EVIDENCE_DIR,
        help="Directory to write the run's evidence bundle into.",
    )
    parser.add_argument("--floor-count", type=int, default=3)
    parser.add_argument("--orientation-angle-deg", type=float, default=0.0)
    args = parser.parse_args(argv)

    params = OfficeBuildingParameters(
        floor_count=args.floor_count,
        orientation_angle_deg=args.orientation_angle_deg,
    )

    try:
        result = run_reference_case(params, args.evidence_dir)
    except Exception as exc:  # noqa: BLE001 -- top-level CLI failure reporting
        print(f"Task 0 reference case FAILED: {exc}", file=sys.stderr)
        return 1

    print(f"Task 0 reference case PASSED")
    print(f"  run directory: {result.run_directory}")
    print(f"  IDF: {result.idf_path}")
    print(f"  SQL: {result.sql_path}")
    print(f"  metadata: {result.metadata_path}")
    print(f"  annual heating: {result.summary.annual_heating_energy_kwh:.1f} kWh")
    print(f"  annual cooling: {result.summary.annual_cooling_energy_kwh:.1f} kWh")
    print(f"  peak heating:   {result.summary.peak_heating_load_w:.1f} W")
    print(f"  peak cooling:   {result.summary.peak_cooling_load_w:.1f} W")
    return 0


if __name__ == "__main__":
    sys.exit(main())
