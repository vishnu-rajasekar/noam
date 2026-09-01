# Joule Engine Profiles

Joule treats a simulation stack as a versioned engine profile, not as an
unqualified global installation. Every experiment records the selected profile,
translation path, component versions, executable digests, weather source, and
validation status.

## Accepted exploratory baseline: `lbt-1.10-os-3.10-eplus-25.1`

This is the first profile targeted for promotion because it follows the
published Ladybug Tools compatibility chain:

- Ladybug Tools Grasshopper 1.10 family, with an exact patch release pinned in
  the acquisition manifest;
- Python 3.10.10 for the isolated Joule/Ladybug worker;
- OpenStudio 3.10.0;
- EnergyPlus 25.1.0 supplied by the compatible OpenStudio distribution;
- Rhino 8, with the installed Rhino build verified separately against the exact
  plugin package used.

On 2026-08-09 the human engineer accepted execution of the publisher-hash-
matched EnergyPlus 25.1 runtime despite failed native signature verification,
strictly for local sandboxed exploratory work. This is a bounded risk
acceptance, not a finding that the binary is trusted, signed, suitable for
production, or capable of supporting compliance conclusions.

The profile is not supported until it passes the promotion rule below. The Noam
application core remains on its own supported Python runtime. It calls
the Joule worker through typed application contracts, so Ladybug's Python and
solver constraints do not leak into the project, graph, REST, MCP, or Rhino
MVVM layers.

OpenStudio being present does not imply that every study must translate through
an OSM. The Joule adapter records whether a run used Honeybee direct IDF,
OpenStudio translation, or another declared recipe. A direct-IDF path is
supported only after parity and regression tests establish it for this exact
profile.

## Experimental profile: `hb-direct-eplus-26.1`

The Python 3.12, Honeybee Energy 1.123.12, direct-IDF, EnergyPlus 26.1 path is an
experimental profile. It is outside the published Ladybug Tools compatibility
matrix and its official macOS binaries currently fail native signature
verification. It remains blocked from execution until the acquisition record's
clearance requirement is satisfied.

Experimental profiles may generate models and fixtures but cannot support
private-alpha calculations, compliance statements, benchmarks against the
supported profile, or engineering evidence while blocked.

## Promotion rule

A profile becomes supported only when all of the following are version-bound
and recorded:

1. authoritative compatibility or an equivalent project-owned compatibility
   test matrix;
2. provenance, licence, digest, signature, and archive-safety checks;
3. deterministic reference cases with declared units and expected outputs;
4. translation-path parity or explicitly documented differences;
5. failure, stale-input, and result-provenance tests;
6. responsible human approval for the stated use and platform.

The current human approval satisfies only the sandboxed-exploration decision;
it does not waive the remaining promotion requirements.
