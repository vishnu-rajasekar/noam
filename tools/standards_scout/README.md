# Standards Scout — local Qwen evaluation harness (Lab spike)

**Status: experimental Lab capability. NOT part of Noam's authoritative
architecture.** Do not integrate with `src/noam/`, the registry, A5.1, or any
engineering record. This harness never decides engineering compliance; it is a
*standards evidence and procedure researcher* whose output is untrusted until an
engineer reviews it.

## What this is

A deliberately small, offline, auditable harness to evaluate whether a locally
hosted Qwen model can, over a controlled evidence packet:

1. retrieve relevant requirements from controlled documents;
2. identify candidate applicable clauses;
3. turn retrieved evidence into proposed verification procedures;
4. abstain (`INSUFFICIENT_EVIDENCE`) when evidence is missing;
5. avoid unsupported normative claims;
6. reproduce findings the engineer has already established manually.

The **harness**, not the prompt, provides the primary hallucination controls: a
deterministic citation validator (`validate.py`) makes an unsupported normative
claim detectable and, where possible, structurally invalid.

## What is NOT built here (and why)

This session ran inside the Noam sandbox, which denies outbound and loopback
network access (`.claude/settings.json`) and package installation. Therefore:

- **No live model call was executed.** `qwen_runner.OllamaRunner` is written but
  cannot run here; it must be run from an unsandboxed environment. Tests and the
  offline pipeline use `qwen_runner.StubRunner`.
- **No PDF extraction library.** `ingest.py` handles UTF-8 `.txt` / `.md` only;
  `.pdf` raises `UnsupportedFormatError`. Adding a text-PDF extractor is a
  separate, approval-gated step (see "Limitations").
- **No embeddings / reranker.** The retrieval interface (`interfaces.Retriever`)
  is designed so a Qwen3 Embedding + Reranker implementation can be dropped in
  later without touching ingestion, validation, or evaluation. Only the lexical
  BM25 baseline (`retrieve.LexicalRetriever`, stdlib `sqlite3` FTS5) is
  implemented.
- **No restricted data.** Only synthetic, non-proprietary fixtures under
  `fixtures/synthetic/` are committed.
- **No PyYAML.** None of this workstation's interpreters have PyYAML and the
  sandbox forbids installing it, so the committed corpus is JSON
  (`documents.json`, `ground_truth.json`). `tools/standards_scout/_loaders.py`
  still reads `.yaml` / `.yml` when PyYAML *is* importable, so the restricted
  Airport library may be authored as YAML on a machine that has it.

## Detected local setup (2026-09-01, this workstation)

| Item | Finding |
|---|---|
| `qwen` / Qwen Code CLI | not installed (no Node.js on PATH, no `~/.qwen`) |
| Local runtime | Ollama at `%LOCALAPPDATA%\Programs\Ollama\ollama` |
| Installed model | `qwen3:4b` (id `359d7dd4bcda`, 2.5 GB) |
| API | OpenAI-compatible, `http://localhost:11434/v1` |
| Structured output | via Ollama `format` = JSON schema (not a Qwen-CLI flag) |
| Embedding / reranker | none installed |

Because there is no Qwen Code CLI, the `--json-schema` headless mechanism from
the task brief is unavailable; `OllamaRunner` uses the OpenAI-compatible
`/chat/completions` endpoint with `format` set to the response schema and
`temperature = 0`. The runner is configurable (`--base-url`, `--model`,
`--provider-label`) so it is not hard-wired to Ollama.

## Layout

```
tools/standards_scout/
  interfaces.py     dataclasses + Retriever / ModelRunner protocols (the seam)
  _loaders.py       json / optional-yaml structured-file loading
  ingest.py         deterministic .txt/.md extraction -> provenance-tagged chunks
  retrieve.py       lexical BM25 baseline over sqlite FTS5; stable evidence IDs
  qwen_runner.py    StubRunner (offline, used everywhere here) + OllamaRunner
  validate.py       deterministic citation / unsupported-claim validator
  evaluate.py       retrieval metrics + answer metrics, kept separate
  report.py         per-question side-by-side review report (markdown)
  run.py            pipeline orchestrator + reproducibility manifest
  prompts/          versioned system prompt
  schemas/          JSON schemas (response, document metadata, ground truth)
  fixtures/synthetic/
    documents/*.txt        invented "standard" / "annex" / "spec" text
    documents.json         library metadata + SHA-256
    ground_truth.json      5 synthetic eval questions
    stub_responses/*.json  hand-authored answers for the offline pipeline demo
tests/standards_scout/  unittest suite over the synthetic fixtures
BASELINE_REPORT.md    findings, limitations, next-step recommendation
```

## Restricted data layout (local only, never committed)

Create under the existing `knowledge/restricted/` boundary (already gitignored):

```
knowledge/restricted/standards_scout/
  documents/{standards,national_annexes,project_specifications,basis_of_design,reports}/
  metadata/documents.yaml        (or documents.json)
  extracted/
  ground_truth/airport_eval.yaml (or airport_eval.json)
  runs/
  indexes/
```

`run.py --root <dir>` resolves `metadata/documents.{yaml,json}` and
`ground_truth/airport_eval.{yaml,json}`, preferring `.yaml` when present.

**Output confinement (fail-closed).** When a run reads from a restricted tree —
either `--root` is given, or any `--docs/--metadata/--ground-truth` path lies
under `knowledge/restricted/` — the run output is forced to stay inside that
tree. The default becomes `<root>/runs/<timestamp>` (root mode) or
`<restricted-tree>/standards_scout/runs/<timestamp>` (loose restricted inputs),
and an explicit `--out` pointing outside the boundary aborts the run before
anything is written. Restricted-derived evidence and raw model responses never
reach the repository worktree. Purely synthetic runs default to `./_scout_out`.

`run.py --root knowledge/restricted/standards_scout` writes indexes and run
records there. Everything under `knowledge/restricted/` is covered by the
existing `.gitignore` rule — do not add narrower rules that could re-expose it.

## Running (outside the sandbox)

```
# offline dry run over synthetic fixtures, stub model
python -m tools.standards_scout.run \
    --docs tools/standards_scout/fixtures/synthetic/documents \
    --metadata tools/standards_scout/fixtures/synthetic/documents.json \
    --ground-truth tools/standards_scout/fixtures/synthetic/ground_truth.json \
    --runner stub \
    --stub-responses tools/standards_scout/fixtures/synthetic/stub_responses \
    --out ./_scout_out

# real evaluation against local Qwen (needs loopback network)
python -m tools.standards_scout.run \
    --root knowledge/restricted/standards_scout \
    --runner ollama --base-url http://localhost:11434/v1 --model qwen3:4b \
    --repeats 3
```

## Tests

```
python -m unittest discover -s tests/standards_scout -p "test_*.py" -v
```

Not wired into `scripts/verify.sh` — this is Lab code, kept out of the canonical
verification path on purpose.

## Limitations

- No live-model result exists yet; reliability is unmeasured.
- `.pdf` / scanned inputs unsupported; OCR explicitly out of scope.
- Tables and equations in source text are kept as raw text lines only; no
  structural table model.
- Semantic "does this clause actually support this claim" is **not** machine
  judged here — the engineer's manual ground truth is the authority. Qwen is
  never the sole judge of Qwen.
