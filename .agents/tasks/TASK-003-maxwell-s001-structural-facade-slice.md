# TASK-003 — Maxwell S001 structural/facade slice

- Decision class: B — scoped feature against the approved Phase B roadmap direction
- Dependency: reviewed Phase A baseline; TASK-002 is not a dependency
- Base commit: `062f57ec0d59dc6239db6981fef8079f8735d423`
- Branch: `agent/claude/task-003-maxwell-s001-structural-facade-slice`
- Worktree: `.worktrees/task-003-maxwell-s001-structural-facade-slice`
- Implementer/session: Claude / `noam-claude-task-003`
- Orchestrator/reviewer: Codex
- Owned paths:
  - `src/noam/domains/__init__.py`
  - `src/noam/domains/maxwell/**`
  - `tests/noam_core/test_maxwell_structural.py`
  - `tests/noam_core/test_maxwell_facade_idealisation.py`
  - `.agents/handoffs/TASK-003-maxwell-s001-structural-facade-slice.json`
- Forbidden paths:
  - `FrameSizer/**`, `BayBuilder/**`, and every external repository
  - `tools/**` and `tests/standards_scout/**` (concurrent, unrelated work)
  - `studies/S001_airport_cw/**` and `knowledge/restricted/**`
  - existing core models, registry, CLI, adapters, roadmap, architecture, policy,
    dependency, lock, sandbox, and verification-script files
  - Rhino/Grasshopper, Cobra, standards/design-check, package-installation,
    network, deployment, Git-history, remote, and metered-API scope

## Objective

Deliver the smallest solver-neutral Maxwell structural/facade vertical slice
needed to trace one rectangular S001 curtain-wall unit's left mullion from
physical geometry and pressure, through an explicit independent-span
idealisation and tributary line-load conversion, to deterministic closed-form
analysis results. This is analysis evidence only: it makes no adequacy,
compliance, modelling-approval, or engineering-decision claim.

This brief is retroactive recovery documentation. The candidate already
exists as 13 untracked/intent-to-add files in the primary worktree following
three chat-directed implementation turns. Recovery must relocate those exact
files into this task's isolated worktree, preserve unrelated concurrent work,
run the canonical check there, and produce the durable handoff. Do not use the
recovery as permission to redesign or broaden the slice.

## Invariants and stop conditions

- Preserve the architecture's physical facade → explicit idealisation →
  solver-neutral structural analysis separation. Nothing under `facade/`
  imports `structural/`; `idealisation.py` is the mapper allowed to depend on
  both.
- Preserve the hard boundary between analysis and design checks. No strength,
  stability, serviceability limit, material-code, partial-factor,
  combination, generic utilisation, or compliance result belongs here.
- The modelling hypothesis is explicitly
  `SIMPLY_SUPPORTED_INDEPENDENT_SPAN`: one prismatic left mullion with support
  locations coincident with its physical endpoints, PIN at one end and ROLLER
  at the other. It is not a universal curtain-wall truth or a human-approved
  `ModelHypothesis`.
- Use millimetres, newtons, N/mm², and mm⁴ in explicitly named fields. Do not
  imply a project-wide or Rhino coordinate convention.
- Retain explicit IDs across physical member, analytical member, source
  pressure, derived line load, model, load case, result, and reactions. Do not
  reconstruct provenance by list position or floating-point matching.
- Pressure-to-line-load conversion is performed once and recorded as
  `w [N/mm] = p [N/mm²] × tributary width [mm]`.
- Unsupported topology, support arrangements, loads, and hypotheses fail
  explicitly; no approximation or solver fallback is permitted.
- Do not read, copy, modify, stage, or report the contents of the unrelated
  `tools/` or `tests/standards_scout/` work.
- Do not install packages, enable network access, weaken the sandbox, or use
  API credits. If no existing interpreter can import Pydantic and PyYAML,
  record the exact canonical-check failure and stop for environment repair.
- Stop if relocation cannot preserve every candidate file byte-for-byte, if
  the pinned base/owned paths conflict with another task, if the real
  dependency behaviour invalidates the model, or if satisfying a criterion
  requires expanding this scope.

## Acceptance criteria

1. `noam.domains.maxwell.structural` defines strict, solver-neutral models
   with explicit IDs and unit-bearing field names for nodes, members,
   supports, materials, sections, point loads, full/partial-range distributed
   loads, load cases, reactions, and analysis results.
2. `SupportKind` exposes PIN and ROLLER with no default; the closed-form
   adapter accepts exactly one of each at the member endpoints and explicitly
   rejects PIN+PIN and every unsupported arrangement.
3. Material elastic modulus and section second moment must be positive;
   zero/non-positive member length is rejected before analysis.
4. The adapter accepts exactly one single-span member with either one central
   point load or one full-span UDL, rejects mixed/off-centre/partial-span or
   otherwise unsupported cases, and applies no load factors or design checks.
5. The central-point-load case returns `R=P/2`, `Mmax=PL/4`, and
   `δmax=PL³/(48EI)` with explicit model/member/load-case/method provenance.
6. The full-span UDL case returns `R=wL/2`, `Mmax=wL²/8`, and
   `δmax=5wL⁴/(384EI)` with explicit model/member/load-case/method provenance.
7. `facade/` defines its own strict `Point`, `FacadeMember`,
   `CurtainWallUnit`, `MemberRole`, `FacadePressureLoad`, and
   `PressureDirection` vocabulary without importing structural code.
8. `build_rectangular_unit` constructs caller-ID-supplied left/right
   mullions and head/sill transoms with validated roles and the documented
   local convention: origin bottom-left, +X left-to-right, +Y bottom-to-top,
   +Z outward; this convention is explicitly S001-local and unrelated to
   Rhino coordinates.
9. The idealisation builder maps only the physical left mullion to one
   analytical member under the named independent-span hypothesis and records
   the physical-to-analytical identity mapping explicitly.
10. Tributary conversion records the pressure ID, physical-member ID,
    analytical-member ID, tributary width, and derived magnitude; conversion
    to `DistributedLoad` preserves the analytical member ID and full span.
    Pressure direction may remain recorded but unsigned only if this
    limitation is explicit and no inward/outward distinction is claimed.
11. The deterministic fixture `p=0.002 N/mm²`, tributary width `750 mm`,
    `L=3000 mm`, `E=70000 N/mm²`, and `I=1673000 mm⁴` produces `w=1.5 N/mm`,
    reactions `2250 N` each, `Mmax=1687500 N·mm`, and
    `δmax=13.50893390829135 mm`, including `ΣR=wL`.
12. The candidate changes only owned paths, adds focused positive and
    rejection tests for the criteria above, contains no secrets/generated
    artefacts/external dependencies, and passes the canonical command from a
    fresh process:

    ```bash
    bash scripts/verify.sh --fast
    ```

## Required evidence

- A `.agents/handoffs/TASK-003-maxwell-s001-structural-facade-slice.json`
  record conforming to `.agents/handoffs/TEMPLATE.json`.
- Exact changed-file list and diff stat against the pinned base, confirming no
  forbidden or unrelated path changed.
- Unedited canonical-command exit status and output summary, including the
  selected interpreter and dependency versions when runnable. A dependency
  failure is evidence of a blocker, not a passing check.
- Python compilation result for every owned Python file.
- Independent arithmetic reproduction of the declared UDL fixture with
  inputs, units, equations, outputs, and equilibrium check.
- Static evidence that `facade/` has no executable structural import and the
  Maxwell slice introduces no FrameSizer/BayBuilder, Rhino, network,
  subprocess, secret, design-check, or standards dependency.
- Assumptions and limitations, including unsigned pressure direction,
  endpoint-coincident supports, left-mullion-only/single-unit scope, and the
  distinction between software/numerical evidence and human modelling or
  engineering approval.
