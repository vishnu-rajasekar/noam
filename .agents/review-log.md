# Independent Review Log

Append-only record of Codex review verdicts for implementation tasks. Each
entry must identify the task, reviewed diff/state, verification commands,
evidence paths, verdict, conditions or findings, and timestamp.


## 2026-08-09T00:51:14Z -- verdict: C (no test runner detected)
The uncommitted documentation defines incompatible delivery scopes, so there is no single authoritative implementation sequence.
- **high** TASKS.md: Tasks 0–5 define the first shipped vertical slice as Joule/EnergyPlus-only and contain no Maxwell task, while PROJECT_LAYER.md:227–238 and ROADMAP.md:52–83 require the first slice to include both bounded Maxwell and Joule studies. ROADMAP.md:97–108 also postpones EnergyPlus until Phase 4, contradicting TASKS.md:6–42. Resolving which scope and sequencing governs requires a product/architecture decision rather than a local correction.

## 2026-08-09T14:07:44Z -- round cap (2) reached, skipping auto-review

## 2026-08-09T14:26:38Z — TASK-000 interim verdict: FAIL

Reviewed the uncommitted Task 0 implementation and generated evidence after
the human accepted the bounded EnergyPlus 25.1 profile.

- Acceptance criterion failed: implementation, tests, and `scripts/verify.sh`
  hard-code `.tools/energyplus-26.1.0` and assert EnergyPlus 26.1.
- Prohibited action occurred: evidence at
  `spike/task0_energy/_evidence/run_20260809T135930Z/` records an actual 26.1
  simulation, although `TASKS.md` and the acquisition decision blocked that
  profile. This evidence is rejected and must not be relabelled or used as the
  Task 0 reference case.
- The run also reports implausible sizing temperatures up to 407.31 C and
  negative sentinel maximum airflow, so successful process exit would not have
  established physically credible results.
- Repair sent to Claude: bind execution to the exact accepted EnergyPlus 25.1
  digest, reject version/digest mismatch, generate new 25.1 evidence, and
  disclose this failed attempt in the durable handoff.

No commit or integration is permitted until Codex reruns and passes the repaired
canonical verification independently.

## 2026-08-09T17:07:27Z -- verdict: C (no test runner detected)
The implementation executes a solver profile that the same diff explicitly marks blocked, so Task 0 cannot satisfy its declared architecture and security boundary. The standalone import path also fails to enforce its claimed project-local HOME isolation.
- **high** spike/task0_energy/reference_case.py: Lines 33-43 and 64 hard-code and execute EnergyPlus 26.1, while TASKS.md lines 14-19 require the accepted EnergyPlus 25.1 compatibility chain and explicitly state that the direct 26.1 profile is blocked. security/acquisitions/energyplus-26.1.0.json also prohibits executing this runtime. Tests reinforce the prohibited semantic contract by requiring version 26.1.
- **high** spike/task0_energy/__init__.py: Line 27 uses os.environ.setdefault("HOME", ...), which does nothing in a normal process where HOME is already defined. Consequently, the documented standalone command can let Ladybug read or create files under the user's real home directory, contrary to the project-scoped isolation claimed by lines 15-24.

## 2026-08-09T17:11:08Z -- round cap (2) reached, skipping auto-review

## 2026-08-31T23:16:49Z -- verdict: C (no test runner detected)
The new core schema cannot represent two traceability distinctions required by the repository architecture. These are semantic model/API mismatches requiring design decisions rather than a small local patch.
- **high** src/noam/models/experiment.py: Experiment is defined as a run against a ModelHypothesis, but it has no ModelHypothesis ID/reference—only an unrelated free-text `hypothesis` field. Consequently, experiments and results cannot be traced to the reviewed modelling idealisation that governed them.
- **high** src/noam/models/result.py: A single `validation_status` collapses software correctness and numerical/physics correctness, despite ARCHITECTURE.md explicitly requiring these to remain distinct. The persisted schema therefore cannot record whether code verification passed independently of numerical/physics validation.

## 2026-09-01T00:16:34Z — TASK-001 Phase A closure, review round 1 — FAIL

Reviewed handoff
`.agents/handoffs/TASK-001-phase-a-closure.json` at SHA-256
`43e4dc14dbed55b92e240efebfc5b903e82793abd4964e0f9c5a51b6d9bf07ed`
in the unborn-`main` bootstrap worktree. No baseline commit exists.

### Acceptance criteria checked

- canonical `scripts/verify.sh --fast` from the documented entry point;
- interpreter discovery and explicit missing-dependency failure;
- the complete existing core suite;
- registry filename/id, duplicate, containment, approval-state, and
  cross-reference validation;
- S001's absent/unreviewed ModelHypothesis state;
- restricted-metadata/confidential-content documentation;
- durable `.agents` tracking;
- the authorised narrow Phase A.5/A5.1 roadmap insertion;
- S001 templates and static network/download/live-runtime scope.

### Independent commands and outcomes

- `bash scripts/verify.sh --fast` — **exit 1**: no interpreter discovered,
  although `/usr/local/Caskroom/miniconda/base/bin/python` is on the normal
  shell PATH and imports Pydantic/PyYAML. `python3` resolves to the Apple
  Command Line Tools interpreter without those dependencies.
- The same command under a clean `env -i` PATH — **exit 1** with the same
  explicit dependency error. The failure is correctly loud, but discovery is
  not robust and the canonical acceptance command does not pass.
- `PYTHONPATH=src /usr/local/Caskroom/miniconda/base/bin/python -m unittest
  discover -s tests/noam_core -p 'test_*.py' -v` — **38/38 passed**.
- `PYTHONPATH=src /usr/local/Caskroom/miniconda/base/bin/python -m
  noam.cli.main registry validate` — **exit 0**, real S001 reports valid.
- `git check-ignore -v` for the Phase A task, handoff, and review log — all
  are ignored by `.gitignore:50`.
- Independent temporary-registry adversarial case — validator incorrectly
  returned `ok=True` for duplicate `REQ-001` records in two studies, a Joule
  capability stored under `domains/maxwell`, a Result whose capability was
  not among its Experiment's capabilities, and empty `Study.*_ids` despite
  existing child records.

### Architectural, privacy, and scientific review

- The Experiment→ModelHypothesis link and Result software/numerical statuses
  remain separate. An Experiment referencing an unapproved hypothesis is now
  rejected. S001 still contains only blank templates/unknowns, and no
  engineering analysis or approval is claimed.
- ROADMAP.md's Phase A.5 insertion is narrow and accurately excludes live
  models, downloads, S001, standards, Rhino, and solvers.
- Static inspection found no new network client, download, installer, live
  model, solver, or invented S001 value.
- No numerical/physics or engineering conclusion is part of this gate.

### Blocking findings and bounded repair request

1. **High — canonical verification cannot pass.**
   `scripts/verify.sh:23-36` never considers the usable `python` command, so
   the documented entry point fails on this machine. `scripts/noam.sh` also
   hard-codes `python3` and fails here. Use one shared, deterministic
   interpreter-selection rule for both entry points: prefer the declared
   project environment, then inspect available named interpreters including
   `python`, accept one only after importing required dependencies, and retain
   the current explicit failure when none qualifies. Add tests for candidate
   ordering, dependency rejection, and the usable-`python`/broken-`python3`
   case. Do not install dependencies or conceal failure.

2. **High — durable reviewer records are still ignored.**
   `.gitignore:50` contains the blanket `.agents/` rule and currently hides
   the task, handoff, and this review log, directly violating the workflow.
   Make the repository robust to the known Stop-hook: retain a sentinel
   `.agents/` match if the hook requires it, but follow it with correctly
   ordered negations that re-include `.agents/`, `tasks/`, `handoffs/`, and
   `review-log.md`, while explicitly ignoring only the two ephemeral dotfiles.
   Prove the three durable paths are not ignored with `git check-ignore`.

3. **High — reported duplicate/containment/reference gaps remain open.**
   `src/noam/registry/validate.py:150-178` checks child duplicates only within
   one study; bare IDs can therefore collide across studies. Lines 110-119 do
   not verify a Capability/Precedent's declared domain against its containing
   directory. Lines 235-253 do not require a Result capability to belong to
   its Experiment, and no validation reconciles authoritative child files
   with the Study convenience references despite ROADMAP.md:34-40 claiming
   `Study↔child` checks. Close these exact cases and add negative tests. Do not
   invent S001 records merely to populate its lists; an empty study with no
   structured children must remain valid.

4. **High — the documented confidentiality rule is unsafe.**
   `ARCHITECTURE.md:198-223` declares everything under `studies/` safe to
   commit and uses whether a value can be typed from memory as the boundary.
   Confidentiality follows the information, not its source format: client
   identifiers, dimensions, decisions, and paraphrases can remain
   confidential even when manually typed. Revise the boundary so `studies/`
   contains only explicitly commit-approved, minimised/redacted metadata and
   opaque references; confidential/licensed source content *and confidential
   derived details* remain under `knowledge/restricted/`. Preserve S001's
   current unknown-only templates.

Gate 1 remains closed. Do not create the baseline commit or begin A5.1. Return
the same task with a new `ready_for_review` handoff after these bounded repairs
and the canonical commands pass.

## TASK-001 Phase A closure — FAIL

Reviewed repair-round-2 handoff
`.agents/handoffs/TASK-001-phase-a-closure.json` at SHA-256
`baa59d785d940be1d709ad03958b75c3118ab7266ae3f17481968452ea5e5080`
in the unborn-`main` bootstrap worktree. Timestamp: 2026-09-01T08:31:51Z.
No baseline commit exists.

### Acceptance criteria checked

- every bounded repair from the 2026-09-01T00:16:34Z `FAIL`;
- both documented Phase A entry points and the complete core suite;
- interpreter ordering, dependency rejection, and unavailable-dependency
  failure, including a broken declared project environment;
- duplicate ids across studies, domain-directory containment,
  Study↔child reconciliation, hypothesis approval, and
  Experiment/Result→Capability provenance;
- malformed authoring input and cross-domain reference adversaries;
- durable `.agents` and generated-environment ignore behaviour;
- the commit-safe/confidential boundary, S001 unknown-only templates, and the
  approved narrow Phase A.5/A5.1 roadmap insertion;
- no-network, no-download, no-live-model/solver, no-secret, and
  no-invented-S001 scope.

### Independent commands and outcomes

- `bash scripts/verify.sh --fast` — **exit 0**, 50/50 tests passed in a fresh
  process using `/usr/local/Caskroom/miniconda/base/bin/python3.13`.
- `bash scripts/noam.sh registry validate` — **exit 0**, real S001 reports
  `registry valid: no problems found`.
- `bash scripts/noam.sh study show S001` — **exit 0**; S001 remains draft,
  restricted, with unknown jurisdiction and no engineering approval claim.
- The explicit `unittest discover` entry point — **exit 0**, 50/50 passed.
- A clean `env -i` PATH with no usable dependencies — **exit 1** with the
  intended actionable Pydantic/PyYAML message.
- `git check-ignore` — task, handoff, and review log each returned **exit 1**
  (not ignored); `.last-review-hash` and `.review-round-count` each returned
  **exit 0** (ignored). The Stop-hook sentinel/negation order is currently
  durable.
- Independent temporary-registry adversaries correctly rejected duplicate
  requirement/hypothesis/experiment/result/insight/evidence ids across two
  studies, Capability/Precedent domain-directory mismatch, Result capability
  mismatch with its Experiment, both directions of Study child-index drift,
  unknown Study capability/precedent ids, and an unapproved hypothesis.
- A Maxwell Study and Experiment referencing a valid Joule Capability, plus a
  Maxwell Study referencing a valid Joule Precedent, incorrectly returned
  **`ok=True` with zero problems**.
- An invalid `REQ-001.yaml` raised an uncaught PyYAML `ParserError` instead of
  returning a `ValidationReport`/CLI invalid result.
- A temporary executable but dependency-broken
  `.venv-noam/bin/python`, with a usable PATH interpreter available, was
  selected with **status 0**; its required-dependency probe then failed.
- `git check-ignore` returned **exit 1** for `.venv-noam/pyvenv.cfg` and a
  representative `.venv-noam/lib/.../site-packages` file. Only its `bin/`
  content happens to match the generic ignore rule.
- Focused static scans found no implementation network client, downloader,
  installer, live model, solver execution, API secret, or populated S001
  project value.

### Architectural, privacy, roadmap, and scientific review

- The previous duplicate/containment/reconciliation cases are closed, and
  Experiment→ModelHypothesis plus separate Result software/numerical statuses
  remain intact. Cross-domain semantic containment is still unenforced.
- `ARCHITECTURE.md` now correctly states that confidentiality follows the
  information, requires explicit human commit clearance, and keeps
  confidential/licensed derived detail under `knowledge/restricted/`.
- `.gitignore` now preserves the prescribed durable reviewer records, but it
  does not durably exclude the newly declared generated `.venv-noam` tree.
- ROADMAP.md's A5.1 insertion remains narrow: recorded fixtures only, with no
  live model, download, S001 content, standards, Rhino, solver, approval, or
  schema broadening.
- S001's brief and model-hypothesis Markdown remain blank/unknown templates.
  No numerical, physics, compliance, or engineering conclusion is part of
  this gate.

### Blocking findings and bounded repair request

1. **High — interpreter selection violates the repair contract.**
   `scripts/lib/pick_python.sh:44-47` accepts any executable declared
   `.venv-noam/bin/python` without the required import probe, even when a
   later PATH candidate is valid. This contradicts TASK-001 acceptance item 1
   and the prior repair requirement that an interpreter be accepted only
   after importing Pydantic/PyYAML. Probe the declared environment too; if it
   is broken, continue deterministically to the override/PATH candidates, and
   add a negative test for this exact case. Preserve the actionable all-
   candidates-unavailable failure.

2. **High — the declared generated environment is not fully ignored.**
   `.gitignore:1-50` has no `.venv-noam/` rule. The generic `bin/` rule hides
   its interpreter, but `pyvenv.cfg`, `lib/`, and installed packages remain
   candidate files, violating the generated-dependency boundary. Add the
   narrow `.venv-noam/` ignore and prove representative root, `bin`, and
   `lib/site-packages` paths are ignored while the three durable `.agents`
   paths remain unignored.

3. **High — domain-scoped references can cross domains silently.**
   `src/noam/registry/validate.py:285-295` and `350-368` check only global id
   existence. A Maxwell Study/Experiment/Result can therefore reference a
   Joule Capability, and a Maxwell Study can reference a Joule Precedent,
   while validation reports success. Preserve id uniqueness and directory
   checks, retain records by id with their declared domain, and reject
   Study/Experiment/Result capability plus Study precedent references whose
   domain differs from the containing Study. Add Maxwell→Joule negative tests
   and a same-domain passing fixture.

4. **High — malformed authoring YAML escapes structured validation.**
   `src/noam/registry/validate.py:77-80` and `203-207` catch only Pydantic
   `ValidationError`; PyYAML parse failures propagate through
   `cmd_registry_validate` as a traceback. This contradicts the validator's
   own no-exception contract and `PROTOCOLS.md` structured-failure rule.
   Convert YAML/load failures into path-specific validation problems, keep
   scanning remaining files, make the CLI exit non-zero without a traceback,
   and add malformed study and child YAML adversarial tests.

Gate 1 remains closed. Do not create the baseline commit and do not begin
A5.1. This is the second unsuccessful repair review, so
`IMPLEMENTER_REVIEWER_PROTOCOL.md` requires a human checkpoint before any
further repair round; the acceptance criteria must not be weakened.

## TASK-001 Phase A closure — PASS

Reviewed the authorised repair-round-3 `ready_for_review` handoff
`.agents/handoffs/TASK-001-phase-a-closure.json` at SHA-256
`98391337dfca3f595837301d8c103a4748ff401b8814323d777ef64e78fec3a0`
in the unborn-`main` bootstrap worktree. Timestamp: 2026-09-01T08:51:34Z.
No baseline commit exists; this review made no commit or integration change.

### Acceptance criteria checked

- every bounded repair from the 2026-09-01T08:31:51Z `FAIL`, under the
  explicitly authorised human checkpoint for repair round 3;
- both documented Phase A entry points and the complete core suite;
- declared-environment probing, deterministic fallback, dependency rejection,
  and actionable all-candidates-unavailable failure;
- filename/id consistency; global duplicate detection for studies,
  requirements, hypotheses, experiments, results, insights, evidence,
  capabilities, and precedents; Study↔child reconciliation; hypothesis
  existence and approval; Experiment/Result capability provenance; domain
  directory containment; and domain-safe Study/Experiment/Result references;
- structured handling of malformed study and child YAML, including continued
  scanning and non-zero CLI exit without traceback;
- generated `.venv-noam/`, confidential `knowledge/restricted/`, and durable
  `.agents/` ignore behaviour;
- the commit-safe/confidential information boundary, S001's unknown-only
  modelling state, and the approved narrow Phase A.5/A5.1 roadmap insertion;
- no-network, no-download, no-live-model/solver, no-secret, no-A5.1-
  implementation, and no-invented-S001-engineering-value scope.

### Independent commands and outcomes

- `bash scripts/verify.sh --fast` — **exit 0**, 59/59 tests passed in a fresh
  process using `/usr/local/Caskroom/miniconda/base/bin/python3.13`.
- `bash scripts/noam.sh registry validate` — **exit 0**, real S001 reports
  `registry valid: no problems found`.
- `bash scripts/noam.sh study show S001` — **exit 0**; S001 remains draft and
  restricted, jurisdiction is unknown, and no engineering approval is claimed.
- Explicit `unittest discover` — **exit 0**, 59/59 tests passed independently.
- `env -i PATH=/usr/bin:/bin bash scripts/verify.sh --fast` — **exit 1** with
  the intended actionable Pydantic/PyYAML dependency message.
- `git check-ignore --no-index -q` — `.venv-noam/`, `pyvenv.cfg`, a
  representative `lib/.../site-packages` file, and `bin/python` each return
  **exit 0** (ignored); the task, handoff, and review log each return **exit 1**
  (not ignored); `.last-review-hash` and `.review-round-count` each return
  **exit 0** (ignored). `knowledge/restricted/example.pdf` is also ignored.
- Fresh temporary-registry adversary — a Maxwell study referencing a Joule
  capability from Study, Experiment, and Result plus a Joule precedent from
  Study returns **`ok=False`** with four distinct cross-domain problems.
- Fresh temporary-registry malformed-YAML adversaries — malformed child YAML
  and malformed `study.yaml` each produce CLI **exit 1**, name the offending
  path, and produce no traceback; the child case also reports a later invalid
  Insight, proving that scanning continued.
- Static source/import, dependency, secret-pattern, A5.1-marker, and S001-file
  inventories found no runtime network client, downloader, installer, live
  inference path, solver execution, credential, A5.1 implementation, populated
  Requirement/ModelHypothesis/Experiment/Result, or numerical project input.

### Architectural, privacy, roadmap, and scientific review

- The registry now enforces the declared Phase A traceability boundary,
  including the four round-3 cases, without weakening the existing checks.
  Experiment→ModelHypothesis approval and separate Result software/numerical
  validation statuses remain intact.
- `ARCHITECTURE.md` correctly makes human commit clearance and information
  sensitivity—not file format or origin—the boundary; confidential/licensed
  source content and confidential derived detail remain under the ignored
  `knowledge/restricted/` tree.
- `.gitignore` fully excludes the generated `.venv-noam/` tree while preserving
  the three durable reviewer records and ignoring only the two prescribed
  ephemeral `.agents` dotfiles. Its tail contains no later blanket `.agents/`
  rule that would undo the negations.
- ROADMAP.md limits A5.1 to recorded fixtures and expressly excludes live
  models, downloads/installations, S001/confidential content, licensed
  standards, solvers, engineering conclusions, autonomous approval, and
  unapproved schema changes. No A5.1 implementation exists in the candidate.
- S001's brief remains blank; its modelling template retains explicit Unknown
  values and draft status; there are no structured child records. No numerical,
  physics, compliance, model-approval, or engineering conclusion is claimed by
  this gate.

### Blocking findings

None. Gate 1 Phase A closure passes unconditionally. This reviewer record does
not itself create the baseline commit or begin A5.1; those actions were outside
the authorised review-only scope.

## 2026-09-01T10:26:44Z -- codex exec failed (exit 1), skipping

## 2026-09-01T10:32:23Z -- codex exec failed (exit 1), skipping
