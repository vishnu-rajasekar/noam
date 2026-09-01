"""Direct-IDF EnergyPlus invocation for the Task 0 feasibility spike.

Writes the Honeybee Model + SimulationParameter to a plain IDF (Honeybee's
direct writer; no OpenStudio anywhere in this path), invokes the pinned
EnergyPlus executable configured for this repository, and returns the paths
EnergyPlus produced so raw logs and result files can be preserved as
evidence.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Optional

from honeybee.model import Model
from honeybee_energy.config import folders as energy_folders
from honeybee_energy import run as energy_run
from honeybee_energy.simulation.output import SimulationOutput
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.writer import model_to_idf


@dataclass(frozen=True)
class EnergyPlusRun:
    """Paths produced by a completed (or failed) EnergyPlus invocation."""

    idf_path: str
    run_directory: str
    sql_path: Optional[str]
    rdd_path: Optional[str]
    html_path: Optional[str]
    err_path: Optional[str]
    energyplus_version: str


def configure_energyplus(energyplus_install_dir: str) -> str:
    """Point honeybee-energy's runtime config at the pinned EnergyPlus install.

    This mutates only the in-process config singleton; it does not write to
    any user-global honeybee/ladybug config file.
    """
    energy_folders.energyplus_path = os.path.abspath(energyplus_install_dir)
    if energy_folders.energyplus_exe is None:
        raise RuntimeError(
            f"No EnergyPlus executable found under {energyplus_install_dir!r}"
        )
    version = energy_folders.energyplus_version_str
    if version is None:
        raise RuntimeError(
            f"EnergyPlus executable at {energy_folders.energyplus_exe!r} did "
            "not report a version; refusing to proceed with an unidentified "
            "binary."
        )
    return version


def build_simulation_parameter(ddy_path: str) -> SimulationParameter:
    """Build an annual-run SimulationParameter with design-day sizing periods.

    - Full-year annual run period at Hourly reporting frequency (only the
      run period is executed; run_for_sizing_periods stays False).
    - ASHRAE 99.6%/0.4% heating/cooling design days loaded from the local DDY
      file bundled with the EnergyPlus install, so that each room's Autosize
      ideal-air capacity is sized without needing to execute the design days
      themselves.
    - Zone ideal-air heating/cooling energy outputs requested explicitly so
      the annual and peak parser has a declared, named source.
    """
    sim_output = SimulationOutput()
    sim_output.add_zone_energy_use(load_type="Total")

    sim_par = SimulationParameter()
    sim_par.output = sim_output
    sim_par.simulation_control.run_for_sizing_periods = False
    sim_par.simulation_control.run_for_run_periods = True
    sim_par.sizing_parameter.add_from_ddy_996_004(ddy_path)
    return sim_par


def write_idf(model: Model, sim_par: SimulationParameter, destination_path: str) -> str:
    """Write the model + simulation parameters to a single plain-text IDF."""
    model_idf_str = model_to_idf(model, use_ideal_air_equivalent=True)
    sim_par_idf_str = sim_par.to_idf()
    idf_str = "\n\n".join((sim_par_idf_str, model_idf_str))
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    with open(destination_path, "w") as idf_file:
        idf_file.write(idf_str)
    return destination_path


def run_energyplus(idf_path: str, epw_path: str) -> EnergyPlusRun:
    """Invoke the configured EnergyPlus executable on a prepared IDF + EPW.

    Raises RuntimeError with the tail of the .err log (and full run
    directory path) if EnergyPlus does not produce a result SQL file, so
    callers get an explicit, inspectable failure rather than a silent gap.
    """
    version = energy_folders.energyplus_version_str
    if version is None:
        raise RuntimeError("configure_energyplus() must be called before run_energyplus()")

    sql_path, _zsz, rdd_path, html_path, err_path = energy_run.run_idf(
        idf_path, epw_path, expand_objects=True, silent=True
    )
    run_directory = os.path.dirname(idf_path)

    if sql_path is None or not os.path.isfile(sql_path):
        err_tail = _read_tail(err_path, max_lines=60)
        raise RuntimeError(
            "EnergyPlus did not produce a result SQL file for "
            f"{idf_path!r}. Raw logs preserved at {run_directory!r}.\n"
            f"--- tail of {err_path} ---\n{err_tail}"
        )

    return EnergyPlusRun(
        idf_path=idf_path,
        run_directory=run_directory,
        sql_path=sql_path,
        rdd_path=rdd_path,
        html_path=html_path,
        err_path=err_path,
        energyplus_version=version,
    )


def _read_tail(file_path: Optional[str], max_lines: int) -> str:
    if file_path is None or not os.path.isfile(file_path):
        return "(no .err file was produced)"
    with open(file_path, "r", errors="replace") as handle:
        lines = handle.readlines()
    return "".join(lines[-max_lines:])


def preserve_run_directory(run_directory: str, evidence_directory: str) -> str:
    """Copy the full EnergyPlus run directory (raw logs + results) somewhere
    outside the transient run location so it survives as evidence."""
    destination = os.path.join(evidence_directory, os.path.basename(run_directory))
    if os.path.abspath(destination) != os.path.abspath(run_directory):
        if os.path.isdir(destination):
            shutil.rmtree(destination)
        shutil.copytree(run_directory, destination)
        return destination
    return run_directory
