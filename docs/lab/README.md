# Lab documentation (background, not current architecture)

These documents describe an earlier, BEM/facade-first product direction:
*create a project → generate a Building Energy Model from Rhino massing →
assign facade typologies → create a bay → run one Maxwell and one Joule study
→ produce a graph-backed comparison*. They predate the study-driven
restructuring recorded in the top-level `ROADMAP.md` and `ARCHITECTURE.md`
(2026-09-01).

**None of this is superseded knowledge** — the domain modelling, knowledge
graph, and AI-native reasoning-record thinking are genuinely useful and are
expected to matter again once Noam grows past its first study
(`S001 · Maxwell · Airport Unitised Curtain Wall`) into project-scale,
multi-study, multi-domain work. They are **not** the current implementation
target, and none of it should be read as already built or already agreed.

If you are picking up work today: read the top-level `README.md`,
`ARCHITECTURE.md`, `ROADMAP.md`, and `AGENTS.md` first. Come here only when a
later phase (see `ROADMAP.md` Phase C onward) needs this background.

| File | Original scope | Still relevant for |
|---|---|---|
| `AI_NATIVE_ARCHITECTURE.md` | Reasoning-record pattern, learning boundary, dev-agent cost rules | The reasoning-record concept generalises to `Insight`/`Precedent`; the dev-agent cost rules are now folded into the top-level `AGENTS.md` directly |
| `DOMAIN_FOUNDATION.md` | Facade classification, systems, functional units, CAD→model workflow | Phase F facade/system-level studies, once Noam handles more than one curtain-wall study |
| `KNOWLEDGE_GRAPH.md` | System-of-record graph schema linking geometry/physics/requirements/evidence/decisions | The long-term target once the flat-file `studies/`/`domains/` registry (see `ARCHITECTURE.md`) needs graph-shaped queries |
| `PROJECT_LAYER.md` | Project → BEM → facade typology → bay pipeline, Rhino MVVM panel navigation | Future Rhino panel work and any BEM-generation feature; not needed for S001's structural-only scope |
| `INTEGRATIONS.md` | Rhino MCP platform and solver-adapter integration strategy | Future Rhino/Karamba/RFEM adapter work (see `adapters/README.md` for the current, narrower S001-scoped version) |
| `JOULE_ENGINE_PROFILES.md` | Versioned solver "engine profile" policy for Ladybug/OpenStudio/EnergyPlus | Whenever Joule/EnergyPlus work resumes (Phase F) — the versioned-profile discipline it describes is exactly right and should be reused, not reinvented |

None of these files are gitignored or deleted; they remain fully readable
history and design input.
