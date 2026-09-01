# AI-Native Architecture

Noam is AI-native because reasoning is a first-class, inspectable workflow over
engineering evidence—not because a language model sits in front of Honeybee.

## Differentiator

Honeybee and its underlying engines are valuable model-authoring and simulation
tools. Noam reuses robust tools rather than duplicating them. Its product layer
connects project intent, shared façade identity, requirements, experiments,
cross-domain evidence, alternatives, uncertainty, and human decisions. The
model may propose and explain; deterministic solvers calculate; recorded
evidence supports review; the engineer decides.

## Runtime pattern

```text
Rhino MVVM client ─┐
Web client later ──┼─> application use cases ─> graph-compatible project store
CLI ───────────────┤              │
REST/OpenAPI ──────┤              ├─> Joule / Maxwell / future environments
MCP ───────────────┘              └─> evidence and immutable artefacts
```

The Python application core is headless and frontend-independent. REST is the
local process boundary for Rhino and future web clients. MCP exposes bounded
agent tools and inspectable resources; it does not replace the typed application
API. Progress uses Server-Sent Events. Events use CloudEvents-shaped envelopes.
Tracing is behind an OpenTelemetry adapter with content capture disabled.

## Reasoning records

Important reasoning is persisted as structured proposals and decisions:
question, context entity IDs, assumptions, alternatives, evidence references,
uncertainty, recommendation, applicable requirements, reviewer, and status.
Natural-language explanations are projections of these records and cannot add
facts absent from their evidence.

## Learning boundary

Validated experiment observations may improve search and recommendations within
the same organisation. Organisation-wide learning is the default, with project
and user opt-outs. Only minimised, derived evidence that passes its declared
validator is eligible. Raw drawings, models, documents, conversations, and
unaccepted model output are excluded. Cross-organisation training or retrieval
is prohibited unless a later product introduces explicit opt-in, isolation,
licensing, and governance.

Surrogates are scoped to declared boundary conditions, training domains, and
error measurements. They accelerate inverse exploration but never obscure the
authoritative solver evidence or operate outside their validity domain without
a warning and fallback.

## Development agents and cost

Claude implements bounded tasks; Codex specifies and independently reviews
them. Both use interactive subscription authentication only. API keys, paid
token billing, credits, and automatic top-ups are forbidden for development.
Automated tests use deterministic fixtures; optional live-agent checks are
manual subscription-CLI checks and never release gates.

