# Cross-study experiments (Phase D — not built yet)

This top-level `experiments/` directory is reserved for future
cross-study datasets, parameter sweeps, and sensitivity/model-fidelity
comparison tooling (`ROADMAP.md` Phase D) — distinct from a single study's
own `studies/<ID>_<slug>/experiments/` folder, which already exists and is
in use (see `studies/S001_airport_cw/experiments/`).

Do not build sweep/dataset infrastructure here until a study has enough
repeated experiments to make it worth the added complexity. Until then, an
`Experiment` record lives inside its owning study.
