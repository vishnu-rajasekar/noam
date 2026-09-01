# TASK-002 — A5.1 Recorded-Fixture Local Proposal Intake

- Decision class: C — architectural trust, privacy, provenance, and future
  local-model compatibility boundary
- Class C authority: explicitly authorised by the human in the current Gate 1
  integration/A5.1 orchestration instruction; the Phase A.5 sequencing decision
  is recorded in `ROADMAP.md` as the human decision of 2026-09-02. This authority
  is limited to the scope and acceptance criteria below. It does not authorise
  any later A5 task or any engineering-schema, privacy-policy, dependency,
  deployment, or live-model change.
- Dependency: TASK-001 Phase A closure, unconditional Gate 1 `PASS`
- Reviewed baseline / implementation base commit:
  `21781d0b27a375948883e5a374be1582fe5544a7`
- Branch: `agent/claude/task-002-a5-1-recorded-fixture-intake`
- Worktree: `.worktrees/task-002-a5-1-recorded-fixture-intake`
- Implementer/session: Claude / `noam-claude-task-002`
- Orchestrator/reviewer: Codex
- One-task isolation: this branch and worktree are the only writable
  implementation location for A5.1; the primary `main` worktree remains
  Codex-owned.

## Objective

Implement the smallest entirely offline runtime contract that accepts a
proposal request over a tiny recorded source fixture and returns a deterministic,
provenance-complete, proposal-only package. The result must prove the contract a
future local model backend would have to satisfy without running or simulating a
live model, approving an engineering record, or writing project/study state.

## Owned paths

Claude may create or modify only:

- `src/noam/proposals/**` — A5.1 request, response, provenance, canonical
  serialisation, unresolved-state, and recorded-fixture backend code;
- `tests/a5_1/**` — A5.1 contract, determinism, failure, privacy, network-denial,
  prompt-injection-content, and authority-boundary tests;
- `tests/fixtures/a5_1/**` — the tiny synthetic/redistributable corpus, recorded
  requests and outputs, and their provenance/hash manifests;
- `scripts/verify.sh` — only the minimal addition that makes `--integration`
  execute the A5.1 integration gate while preserving the existing `--fast`
  semantics and failure behaviour;
- `.agents/handoffs/TASK-002-a5-1-recorded-fixture-intake.json` — the required
  durable implementation handoff.

No ownership is implied outside these paths. If a public import can only be
provided by changing `src/noam/__init__.py`, stop and ask Codex to decide whether
that is necessary; `noam.proposals` itself is the authorised package boundary.

## Forbidden paths and actions

- Do not modify `src/noam/models/**` or any established engineering schema. A
  concrete compatibility defect requires a new independent Codex finding and a
  new human Class C approval; it is not repair authority for this task.
- Do not modify `studies/**`, `domains/**`, `knowledge/**`, `registry/**`,
  `adapters/**`, `experiments/**`, `archive/**`, `security/**`, governance files,
  `.claude/**`, `.gitignore`, `pyproject.toml`, existing `tests/noam_core/**`, the
  task brief, or `.agents/review-log.md`.
- No live Ollama or other model, model emulation, hosted inference, signed-in
  model CLI, network access, socket client, subprocess-backed model, downloads,
  installations, new dependency, lockfile, embedding/vector search, licensed
  standard, confidential/project/S001 content, `RuleCard` promotion,
  Rhino/Grasshopper, solver, engineering result/conclusion, autonomous approval,
  persistence into the study registry, or telemetry containing content.
- Do not commit, merge, rebase, push, publish, deploy, remove worktrees, or alter
  Git history. Claude returns a `ready_for_review` handoff; Codex alone reviews
  and forms any later local implementation commit.

## Invariants and stop conditions

1. Deterministic tools remain authoritative and the human engineer remains the
   only approval authority. Every produced record and claim stays
   `status=proposed`; confidence is evidence metadata, never approval.
2. Proposal contracts are A5.1 runtime DTOs under `noam.proposals`, not new
   `Study`, `Requirement`, `ModelHypothesis`, `Result`, `RuleCard`, or other
   engineering-authoring schemas.
3. The backend is a literal recorded-fixture backend: it resolves only declared
   fixture inputs/digests to recorded outputs. It must not contain heuristic,
   stochastic, generative, remote, or live-inference behaviour.
4. The operation is side-effect free with respect to authoring state: it returns
   a proposal package and does not create, update, approve, index, or persist a
   study record.
5. Raw prompts and corpus/source content never enter logs, exceptions, telemetry,
   or handoff prose. Tests use unique sentinels and capture all logging/error
   surfaces to prove this boundary.
6. Treat fixture text as untrusted data. Text resembling system instructions,
   prompt injection, tool calls, approval directions, or schema overrides cannot
   alter control flow, provenance, package shape, or authority status.
7. Stop without broadening scope if implementation would require a new package,
   download, network access, ambiguous/non-redistributable fixture licence,
   confidential material, an engineering-schema change, a policy change, or a
   write outside the owned paths.

## Gate 2 acceptance criteria

All criteria are blocking and must be demonstrated by executable tests and the
durable handoff.

1. **Runtime contracts.** Typed, strict request, response, source-provenance,
   claim/citation, unresolved-state, and proposal-package contracts exist under
   `src/noam/proposals/`. Unknown fields are rejected. The request identifies
   the recorded fixture and expected source digest; the response identifies the
   contract/backend version, request digest, source provenance, and output
   digest. Digest semantics state exactly which bytes are hashed.
2. **Required proposal shape.** A successful package contains all six distinct
   sections: `sourced_facts`, `inferred_facts`, `missing_information`,
   `proposed_study_fields`, `proposed_requirements`, and
   `proposed_model_hypothesis`, plus package-level provenance/status. Empty
   sections remain present as empty collections; categories are not collapsed.
3. **Claim provenance and confidence.** Every factual or proposed claim has a
   stable claim id, at least one citation to a declared source id with a
   machine-checkable locator, an explicit sourced-versus-inferred category, and
   a validated confidence value in the closed interval `[0, 1]`. An inferred
   claim remains labelled inferred even when cited. No claim can cite an unknown
   source.
4. **Proposal-only authority.** Package, proposed study fields, proposed
   requirements, and proposed model hypothesis are all fixed to
   `status=proposed`. Recorded content attempting to set `approved`, claim
   compliance, claim engineering validity, or imitate a human decision is
   rejected or represented as untrusted source text; it never changes output
   authority. No existing engineering record is mutated.
5. **Recorded backend only.** The backend accepts the nominal declared fixture
   and rejects unknown fixture ids, source-digest mismatches, recorded-output
   digest mismatches, backend/contract version mismatches, and malformed fixture
   records using structured errors/unresolved states. There is no fallback to a
   live model or invented result.
6. **Structured unresolved inputs.** Missing required source information and
   incompatible inputs produce explicit, typed unresolved items with stable
   reason codes, affected field/source references, and human-action text. They
   do not receive invented dimensions, jurisdictions, standards, units,
   assumptions, confidence, or other defaults.
7. **Byte stability.** Canonical UTF-8 serialisation has a documented ordering,
   numeric representation, whitespace, and final-newline rule. Repeating the
   same request in fresh instances produces byte-identical output; the bytes
   equal the checked-in recorded output and its declared SHA-256. Tests must
   fail on any byte or digest drift.
8. **Fixture provenance and redistribution.** The corpus is tiny and contains
   only purpose-written synthetic material or material with clearly documented
   redistribution permission. Every source fixture has adjacent machine-readable
   metadata recording fixture/source id, origin and source locator, author or
   publisher, licence/permission statement, creation or retrieval date, exact
   byte length, SHA-256, and redistribution rationale. Every recorded request
   and output records its own SHA-256 plus the producing contract/backend
   version. No licensed standard, project document, S001 value, or confidential
   derivative is present.
9. **Prompt-injection-content test.** A dedicated fixture contains inert text
   that tries to override instructions, add fields, approve a hypothesis, invoke
   a tool/network action, and exfiltrate a sentinel. The test proves it remains
   source data, citations remain valid, the strict output schema is unchanged,
   status remains proposed, and no action is invoked.
10. **Network denial.** The complete A5.1 integration suite runs with network
    connection primitives denied and fails if code attempts DNS, socket, HTTP,
    subprocess model execution, or another outbound path. Static inspection
    finds no network/model client dependency or endpoint. Tests do not merely
    rely on the developer machine being offline.
11. **Privacy and logging.** With logging captured at all levels and success,
    malformed, digest-mismatch, missing, incompatible, and injection cases
    exercised, no raw prompt, raw corpus text, unique secret-like sentinel, or
    complete proposal content appears in logs or exception strings. Operational
    logs may contain only non-content identifiers, versions, digests, reason
    codes, and counts.
12. **Regression and offline execution.** Existing Phase A behaviour and all 59
    baseline tests remain unchanged and passing. A5.1 requires no network,
    installed model, API credential, paid API, package installation, or generated
    runtime tree. No ignored/cache/runtime/result artefact is added to the handoff.
13. **Scope inventory.** The handoff and reviewer diff inventory show changes
    only in the owned paths, no A5.2/later work, and no unsupported numerical,
    physics, compliance, model-approval, or engineering claim.

## Exact exit checks

Run from the A5.1 worktree root in fresh processes:

```bash
bash scripts/verify.sh --fast
bash scripts/verify.sh --integration
```

- `bash scripts/verify.sh --fast` must exit `0` and run the complete existing
  Phase A core suite (baseline: 59 tests) without weakening or skipping it.
- `bash scripts/verify.sh --integration` must exit `0` and run the complete A5.1
  contract, recorded-fixture, determinism, unresolved-state, provenance,
  injection, network-denial, privacy/logging, and authority-boundary suite.
- An unknown verification mode must retain the existing loud non-zero failure.
  `--release` is not authorised or required by A5.1.

## Required fixture and review evidence

The implementation return must include:

- the complete fixture inventory, relative paths, provenance metadata, licences
  or permission statements, exact byte lengths, and independently recomputable
  SHA-256 values for every source, request, and recorded output;
- the nominal canonical output bytes and digest, plus evidence that at least two
  fresh backend instances reproduced those exact bytes;
- dedicated missing-input, incompatible-input, digest-mismatch, unknown-fixture,
  version-mismatch, malformed-record, and prompt-injection-content cases;
- captured evidence for network primitive denial, zero attempted external/model
  calls, unchanged authority status, no authoring-state writes, and raw-content
  absence from logs/errors;
- unedited command, exit-code, interpreter, and pass/fail summaries for both
  exact exit checks;
- an owned-path diff inventory and an ignored/generated/secret/runtime artefact
  check;
- explicit assumptions, limitations, unresolved risks, and a statement that the
  recorded backend demonstrates only the interface/trust contract—not model
  quality, engineering correctness, standards applicability, or approval.

## Durable handoff

Claude must create
`.agents/handoffs/TASK-002-a5-1-recorded-fixture-intake.json` conforming to
`.agents/handoffs/TEMPLATE.json`, with:

- `task_id: TASK-002`, `state: ready_for_review`, the exact pinned baseline SHA,
  branch, worktree, implementer/session, and actual changed-file list;
- both canonical commands, exit codes, unedited summaries, and evidence paths;
- every fixture/output/provenance artefact path and SHA-256;
- the evidence listed above, assumptions, limitations, and unresolved risks;
- no raw prompt, corpus, confidential content, or secret in the handoff itself.

Stop after the handoff is complete and the two exact checks pass. Do not commit
or begin A5.2. Codex will independently diff against the pinned baseline, rerun
both gates from a fresh process, inspect fixture bytes and provenance, and append
the Gate 2 verdict to `.agents/review-log.md`.
