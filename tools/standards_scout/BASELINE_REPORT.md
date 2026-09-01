# Standards Scout — offline skeleton baseline report

Status: experimental Lab spike, built to the "offline skeleton only" option.
No live model was run. No authoritative Noam integration. See `README.md`.

This corresponds to the task's "Completion report" (16 items).

### Codex review round 1: FAIL — code repairs applied (not re-reviewed)

- **Restricted-output leak** — fixed. `run.py` now derives a confinement
  boundary from restricted inputs / `--root`, defaults output to
  `<root>/runs/<ts>` (or `<restricted-tree>/standards_scout/runs/<ts>`), and
  aborts fail-closed (`RestrictedOutputError`) before writing anything if
  `--out` is outside that boundary. Purely synthetic runs still use
  `./_scout_out`. Regression tests: `tests/standards_scout/test_run_confinement.py`.
- **Malformed model output could crash validation** — fixed. `validate._check_schema`
  now fully type-checks every top-level collection and nested value before any
  traversal; `validate_response` bails to a structured `SCHEMA_INVALID` result;
  `_iter_cited`, `evaluate._response_text`, `evaluate.evaluate_answer`,
  `report.render_question_report`, and `run._all_cited/_stability` are all
  defensive against non-dict / wrong-type values. Regression tests:
  `TestMalformedResponsesNeverRaise` in `test_validate.py` (top-level scalar,
  `conflicts`/`requirements` as string, scalar list entries, `evidence_ids` as
  string, non-string `missing_information`, non-int `step`, plus a
  full-pipeline "must not raise" case).
- **Authorization / worktree isolation** — NOT resolved by code. Requires a
  human-approved bounded task record, pinned base, task branch + worktree,
  owned-file boundary, and durable handoff before this is anything more than a
  draft for review. See item 3 of the review and the note at the end.
- Test count is now **48** (was 32); all pass on `.venv-noam` Python 3.14 here.
  `scripts/verify.sh --fast` still cannot run in this environment (no
  pydantic+PyYAML interpreter) and these files are outside its scope.

### Post-sync regression (CRLF) — fixed

After the skeleton was committed (`b0326ea "WIP: work laptop progress before
syncing"`) and the tree re-checked out on a machine with `core.autocrlf=true`,
the synthetic `documents/*.txt` fixtures were rewritten with CRLF endings, which
changed their byte-exact SHA-256 and made `ingest_library` fail its provenance
check (6 test errors). Fixed: `ingest.source_sha256()` now hashes `.txt`/`.md`
sources after newline normalisation (`\r\n`, `\r` -> `\n`) — a content identity
that is platform-independent — while binary sources (PDF) stay byte-exact.
Added `tools/standards_scout/.gitattributes` pinning the fixtures / prompts /
schemas to `eol=lf` so the committed bytes also stay stable. 48/48 pass again.

---

## 1. Detected Qwen installation / provider / model

| Probe | Result |
|---|---|
| `qwen` / Qwen Code CLI on PATH | **not found** |
| Node.js on PATH | **not found** (Qwen Code is a Node CLI) |
| `~/.qwen` config dir | absent |
| Ollama | installed: `C:\Users\Vishnu\AppData\Local\Programs\Ollama\ollama` |
| `ollama list` | single model `qwen3:4b` (id `359d7dd4bcda`, 2.5 GB, pulled 2026-09-01) |
| Local hosting | yes — Ollama, OpenAI-compatible `http://localhost:11434/v1` |
| Structured output | Ollama `format` = JSON schema on `/api/chat`, or `response_format` on the `/v1` shim; **no Qwen-CLI `--json-schema`** because there is no Qwen Code install |
| Headless invocation | via HTTP only (no CLI); `OllamaRunner` does this |
| Context window / gen settings | not queried live (sandbox blocks loopback); `qwen3:4b` default context is 32K per the Qwen3 model card, to be confirmed on the target box |
| Embedding / reranker models | none installed |
| Global Qwen settings | none found; nothing changed |

Conclusion for the harness: treat the provider as **configurable** (`--base-url`,
`--model`, `--provider-label`); the default points at Ollama `qwen3:4b` but the
runner is not Ollama-specific beyond the OpenAI-compatible request shape.

## 2. Files created

```
tools/__init__.py
tools/standards_scout/
  __init__.py  README.md  BASELINE_REPORT.md
  interfaces.py  _loaders.py  ingest.py  retrieve.py  qwen_runner.py
  validate.py  evaluate.py  report.py  run.py
  prompts/system_prompt_v1.md
  schemas/scout_response.schema.json
  schemas/document_metadata.schema.json
  schemas/ground_truth.schema.json
  fixtures/synthetic/documents/SYN-SSGC-2024.txt
  fixtures/synthetic/documents/SYN-NA-2024.txt
  fixtures/synthetic/documents/SYN-SPEC-A.txt
  fixtures/synthetic/documents.json
  fixtures/synthetic/ground_truth.json
  fixtures/synthetic/stub_responses/SYN-00{1..5}.json
tests/standards_scout/__init__.py
tests/standards_scout/test_ingest.py
tests/standards_scout/test_retrieve.py
tests/standards_scout/test_validate.py
tests/standards_scout/test_evaluate.py
tests/standards_scout/test_restricted_isolation.py
```

Files modified: none outside the list above. `src/noam/**`, `studies/**`,
`.gitignore`, `pyproject.toml`, `scripts/**`, `.claude/**` untouched.

## 3. Restricted data layout

Documented in `README.md`; not created (it would be empty and is a restricted
location). Intended tree under the existing gitignored boundary:

```
knowledge/restricted/standards_scout/
  documents/{standards,national_annexes,project_specifications,basis_of_design,reports}/
  metadata/documents.{yaml,json}
  extracted/
  ground_truth/airport_eval.{yaml,json}
  runs/        indexes/
```

`knowledge/restricted/` is already covered by `.gitignore`; no ignore rule was
added or narrowed. `test_restricted_isolation.py` asserts that rule is intact
and that `git check-ignore` covers `knowledge/restricted/standards_scout/runs/`.

## 4. Ingestion method

`ingest.py`, deterministic, standard library only. UTF-8 `.txt` / `.md`.
`.pdf` raises `UnsupportedFormatError` (no bundled extractor). Clause/section
headings detected by a conservative regex (`<number> <Title phrase>`, annex
prefixes like `NA.4.3` preserved; a prose line such as "clause 4.3 shall be
taken as ..." is rejected as a heading). Chunks carry
`document_id, page, clause, heading, chunk_id, text`; `clause` is the literal
string `unknown` when not reliably detected — never invented. Page = form-feed
delimited, else 1. SHA-256 of each source is verified against the metadata file
at ingest; a mismatch is fatal.

## 5. Retrieval implementation

`retrieve.py`, `LexicalRetriever` = BM25 over an in-memory SQLite FTS5 table
(`porter unicode61`), standard library only. Query → OR-of-terms MATCH →
`ORDER BY bm25 ASC, chunk_id ASC` (deterministic tie-break). Returns
`EvidenceItem`s with rank-assigned ids `E001…`. `Retriever` is a Protocol; a
Qwen3 Embedding + Reranker retriever can replace it without touching ingest,
validate, evaluate, or the model interface.

## 6. Qwen invocation method

`qwen_runner.py`. `build_messages()` composes a system message (versioned
prompt file) + a user message containing QUESTION / PROJECT CONTEXT /
EVIDENCE PACKET (id, document_id, page, clause, chunk_id, text) / RESPONSE
CONTRACT (the JSON schema). Two runners implement `ModelRunner`:

- `StubRunner` — offline, deterministic; returns a canned `<question_id>.json`
  or a well-formed `INSUFFICIENT_EVIDENCE` skeleton. Used by the tests and the
  sandboxed pipeline.
- `OllamaRunner` — POSTs to an OpenAI-compatible `/chat/completions` with
  `response_format: json_schema`, `temperature 0`, `seed 0`, a timeout, and no
  API key. **Cannot run in the Noam sandbox** (loopback denied); raises a clear
  error if the endpoint is unreachable.

No filesystem/shell/agent tools are exposed to the model — it only receives the
packet text.

## 7. Structured response schema

`schemas/scout_response.schema.json` (draft-07, version `v1`). Required:
`question_id`, `status` (`ANSWERED|PARTIAL|INSUFFICIENT_EVIDENCE`),
`requirements[]`, `verification_procedure[]`, `missing_information[]`,
`conflicts[]`. Each requirement: `claim_id`, `claim`, `classification`
(`EXPLICIT_REQUIREMENT|INTERPRETATION|DERIVED_PROCEDURE`), `evidence_ids[]`,
optional `applicability_conditions[]`, `uncertainties[]`. Each procedure step:
`step`, `action`, `evidence_ids[]`, `classification` (`EXPLICIT|DERIVED`).
`additionalProperties:false` throughout.

## 8. Deterministic validation rules

`validate.py`. Checks (all ERROR unless noted):

- `SCHEMA_INVALID` — shape / required keys / enum values.
- `UNKNOWN_EVIDENCE_ID` — id never issued this run.
- `EVIDENCE_NOT_IN_RUN` — id not in this question's packet.
- `DOC_ID_MISMATCH` — cited item's document_id disagrees with metadata or chunk.
- `PAGE_NOT_FOUND` — cited page ≠ stored chunk page.
- `CLAUSE_MISMATCH` — cited clause ≠ stored chunk clause (when chunk clause known).
- `UNSUPPORTED_CLAIM` — a requirement with no `evidence_ids`.
- `MISSING_EVIDENCE` — an `EXPLICIT` procedure step with no `evidence_ids`.
- `PROSE_CITATION_UNBACKED` — free text names `EN/ISO/BS… n`, `clause n`, `§n`,
  `table/figure/eq n` and no cited evidence item carries that number.

`ValidationReport.ok` is false if any ERROR is present. The report is explicit
that passing = citation integrity only, **not** semantic correctness.

## 9. Ground-truth format

`schemas/ground_truth.schema.json`. Per question: `question_id`, `question`,
`project_context`, `answerability.answerable`, `expected_evidence.documents[]`
and `.clauses[]` (`{document_id, clause}`), `expected_concepts[]`,
`unacceptable_claims[]`, `expected_formula`, `expected_status[]`,
`stability_probe`, `engineer_notes`. Negative controls set
`answerable:false` + `expected_status:[INSUFFICIENT_EVIDENCE]`. Ground truth is
read only by the evaluator; it is never shown to the model.

## 10. Evaluation metrics

`evaluate.py`, retrieval and answer scored **separately**:

- Retrieval: `Recall@5`, `Recall@10`, `MRR`, matched/missing target list, over
  `expected_evidence` (doc-level and `{document_id, clause}` targets).
- Answer: status-in-expected, expected-concept coverage (substring),
  unsupported-claim count (from the validator), unacceptable-claim hits
  (substring), correct vs incorrect abstention, formula match (whitespace-
  insensitive substring), citation-integrity ok.
- `classify_limiting_factor()` → `RETRIEVAL_FAILURE` if an expected target is
  absent from the packet; else `ANSWER_FAILURE` if status/validation/
  unacceptable/abstention/formula is wrong; else `OK`; else `UNCERTAIN` when no
  expected evidence was defined.

`report.py` renders the per-question side-by-side (QUESTION / GROUND TRUTH /
RETRIEVED EVIDENCE / QWEN OUTPUT / VALIDATOR FINDINGS / SCORES / ENGINEER
VERDICT), truncating evidence excerpts to 240 chars to avoid reproducing
copyrighted text. `run.py` writes a reproducibility manifest (timestamp,
output_dir, runner/provider/model, prompt & schema SHA-256, retrieval
method+params, document hashes, ground-truth hash, retrieved evidence ids, raw
responses, validator output, scores) and, for `stability_probe` questions,
repeats N times (default 3) and reports status / cited-evidence /
unsupported-claim drift. This manifest contains restricted-derived text, so for
any restricted run it is written only inside the restricted boundary (see
"Output confinement" in `README.md`).

## 11. Synthetic tests and results

`python -m unittest discover -s tests/standards_scout -p "test_*.py" -t .`
→ **48 tests, all pass** (`.venv-noam` Python 3.14). Not wired into
`scripts/verify.sh` — Lab code stays out of the canonical path. Coverage:

- ingestion preserves document/page/chunk identity; annex-prefixed clauses;
  deterministic chunk ids; form-feed pages; `unknown` clause not invented;
  PDF rejected; SHA-256 mismatch fatal.
- retrieval: rank-assigned ids, determinism, re-index stability, relevant
  clause retrieved, packet carries method/params.
- validator: good response passes; unknown id; claim without evidence; clause
  mismatch; page mismatch; unbacked prose citation; valid abstention passes;
  broken schema; explicit step without evidence.
- malformed model output (`TestMalformedResponsesNeverRaise`): top-level scalar
  / list; `conflicts` and `requirements` as strings or with scalar entries;
  `evidence_ids` as a string; non-string `missing_information`; non-int `step`;
  nested list field wrong type — every case yields `SCHEMA_INVALID` and the full
  score + report path runs without raising.
- evaluation: retrieval-miss → `RETRIEVAL_FAILURE` vs evidence-present wrong
  answer → `ANSWER_FAILURE`; good answer → `OK`; false abstention; correct
  abstention on unanswerable; metric values.
- output confinement (`test_run_confinement.py`): root-mode default output is
  inside `--root`; explicit `--out` outside a restricted boundary aborts;
  loose restricted inputs are confined; synthetic inputs use `./_scout_out`.
- isolation: `.gitignore` rule intact; `git check-ignore` covers the restricted
  run dir; committed fixtures are synthetic-only; no restricted markers.

## 12. Real Airport baseline questions run

**None.** No restricted Airport documents or ground truth are present
(`knowledge/restricted/` holds only an unrelated FrameSizer audit). No live
model is reachable from the sandbox. The offline pipeline was exercised only
against the synthetic corpus.

## 13. Baseline results (synthetic, stub runner — plumbing only)

`run.py --runner stub --stub-responses …/stub_responses` over the 5 synthetic
questions:

| question | limiting factor | Recall@5 | status ok | unsupported | dangerous |
|---|---|---|---|---|---|
| SYN-001 (project override) | OK | 1.0 | yes | 0 | no |
| SYN-002 (NA dependency, ×3) | OK | 1.0 | yes | 0 | no |
| SYN-003 (formula extraction) | OK | 1.0 | yes | 0 | no |
| SYN-004 (missing evidence)  | OK | 0.0 | yes (abstained) | 0 | no |
| SYN-005 (trick / false premise) | OK | 1.0 | yes | 0 | no |

Lexical retrieval put every expected `{document, clause}` target in the top 3
on this tiny corpus (mean Recall@5 0.8 — the 0.0 is SYN-004, which by design
has no expected evidence). The `stub_responses` are **hand-authored correct
answers**: this table demonstrates the pipeline, validator, evaluator, report,
manifest, and stability loop working end to end — it is **not** a measurement
of Qwen. The failure-detection behaviour is demonstrated by the unit tests, not
this run.

## 14. Hallucinations / unsupported claims observed

Not applicable — no model output was generated. The controls that would catch
them (`validate.py` codes, `unacceptable_claims`, prose-citation backing,
separate retrieval attribution) are implemented and unit-tested.

## 15. Limitations

1. **No live-model evidence.** Reliability of `qwen3:4b` as a Standards Scout is
   entirely unmeasured. `OllamaRunner` must be run from an unsandboxed host.
2. **No PDF / OCR.** Real standards are PDFs; a text-PDF extractor needs an
   approved dependency (`pypdf`/`pdfminer.six`) — deliberately not added.
3. **PyYAML absent** on every interpreter here; corpus is JSON. YAML still works
   where PyYAML is installed.
4. **Lexical retrieval only.** BM25 on a 3-doc synthetic set is not predictive
   of behaviour on a real multi-hundred-page library; no semantic retrieval.
5. **`unacceptable_claims` / `expected_concepts` are substring checks.** A
   correct rebuttal that must quote the false figure (e.g. "not 30 mm") can trip
   the substring guard; genuine semantic scoring needs the engineer.
6. **Clause detection is heuristic.** Non-numbered or table/figure-only
   provisions land as `clause: unknown`; tables/equations are kept only as raw
   text lines.
7. **Context-window / generation-parameter introspection** for the local model
   was not done live.
8. **`scripts/verify.sh --fast` cannot run in this environment** (no
   pydantic+PyYAML interpreter) — pre-existing, unrelated to these files, which
   touch nothing in its scope.

## 16. Recommendation — next smallest experiment

Run the existing harness **once**, unchanged, on the smallest real slice, on a
host that can reach Ollama:

1. Engineer places 2–3 already-text-extractable Airport documents (or their
   pre-extracted `.txt`) under `knowledge/restricted/standards_scout/documents/`
   and fills `metadata/documents.{yaml,json}` (with real SHA-256) and
   `ground_truth/airport_eval.{yaml,json}` with **3–5** questions he has already
   answered manually — including one deliberately unanswerable and one
   trick/false-premise.
2. `python -m tools.standards_scout.run --root knowledge/restricted/standards_scout
   --runner ollama --model qwen3:4b --repeats 3`.
3. Preserve `run_manifest.json` + the per-question reports **before** any prompt
   or retrieval change. Engineer fills the ENGINEER VERDICT blocks.
4. Only then decide, from that first honest baseline, whether to invest in
   semantic retrieval or prompt work.

Do **not** broaden scope, add embeddings, or integrate with Noam on the basis
of this task.

## Limiting factor for the experiment as a whole

**(c) both remain uncertain.** No live model has run and no real retrieval
corpus exists, so neither retrieval sufficiency nor Qwen reasoning has been
measured. On the synthetic corpus, lexical retrieval was not the bottleneck;
that says nothing about a real standards library.
