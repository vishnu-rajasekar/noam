"""Regenerate the A5.1 recorded-fixture corpus.

Development-only helper. The *tests* never call this; they read the
checked-in artefacts and fail on any byte or digest drift (Gate 2
criterion 7). Run it only when intentionally changing a fixture:

    python tests/fixtures/a5_1/build_fixtures.py            # rewrite artefacts
    python tests/fixtures/a5_1/build_fixtures.py --check    # verify, exit 1 on drift

The source-of-truth text lives in ``corpus/<id>.txt`` (hand-written, never
rewritten here). This script derives the provenance sidecars, the canonical
recorded packages / unresolved states, the recorded requests, the per-fixture
metadata, and ``manifest.json``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from noam.proposals.backend import (  # noqa: E402
    FIXTURE_ROOT_MARKER_NAME,
    fixture_root_marker_bytes,
)
from noam.proposals.canonical import canonical_json, sha256_hex  # noqa: E402
from noam.proposals.contracts import (  # noqa: E402
    ProposalPackage,
    ProposalRequest,
)
from noam.proposals.unresolved import (  # noqa: E402
    REASON_HUMAN_ACTION,
    ReasonCode,
    UnresolvedState,
)
from noam.proposals.version import (  # noqa: E402
    BACKEND_ID,
    BACKEND_VERSION,
    CONTRACT_VERSION,
)

CORPUS = HERE / "corpus"
RECORDED = HERE / "recorded"

LICENCE = "CC0-1.0"
CREATED = "2026-09-01"
RATIONALE = (
    "Synthetic text written for this test; contains no third-party or project material."
)


def _prov(fixture_id: str, source_bytes: bytes) -> dict:
    return {
        "fixture_id": fixture_id,
        "source_id": fixture_id,
        "origin": "purpose-written for the Noam A5.1 recorded-fixture suite",
        "locator": "whole-file",
        "author_or_publisher": "Noam project (synthetic)",
        "licence": LICENCE,
        "created_or_retrieved": CREATED,
        "byte_length": len(source_bytes),
        "sha256": sha256_hex(source_bytes),
        "redistribution_rationale": RATIONALE,
    }


def _sources_field(prov: dict) -> list[dict]:
    return [
        {
            "source_id": prov["source_id"],
            "origin": prov["origin"],
            "locator": prov["locator"],
            "author_or_publisher": prov["author_or_publisher"],
            "licence": prov["licence"],
            "created_or_retrieved": prov["created_or_retrieved"],
            "byte_length": prov["byte_length"],
            "sha256": prov["sha256"],
            "redistribution_rationale": prov["redistribution_rationale"],
        }
    ]


def _package_common(fixture_id: str, prov: dict) -> dict:
    return {
        "status": "proposed",
        "provenance": {
            "contract_version": CONTRACT_VERSION,
            "backend_id": BACKEND_ID,
            "backend_version": BACKEND_VERSION,
            "fixture_id": fixture_id,
            "sources": _sources_field(prov),
        },
        "sourced_facts": [],
        "inferred_facts": [],
        "missing_information": [],
        "proposed_study_fields": [],
        "proposed_requirements": [],
        "proposed_model_hypothesis": {
            "present": False,
            "ref": "",
            "purpose": "",
            "analysis_question": "",
            "idealisation": "",
            "category": "none",
            "citations": [],
            "confidence": None,
            "status": "proposed",
        },
    }


def _cite(src: str, locator: str) -> dict:
    return {"source_id": src, "locator": locator}


# --------------------------------------------------------------------------
# per-fixture recorded payloads (plain dicts -> validated -> canonicalised)
# --------------------------------------------------------------------------


def build_cw_basics(prov: dict) -> dict:
    src = "cw-basics"
    pkg = _package_common(src, prov)
    pkg["sourced_facts"] = [
        {
            "claim_id": "SF-001",
            "category": "sourced",
            "statement": "The source describes a rectangular aluminium-framed glazed panel array.",
            "citations": [_cite(src, "line:2")],
            "confidence": 0.9,
        },
        {
            "claim_id": "SF-002",
            "category": "sourced",
            "statement": "The stated nominal panel size is 1.5 m wide by 3.0 m high.",
            "citations": [_cite(src, "line:3")],
            "confidence": 0.95,
        },
        {
            "claim_id": "SF-003",
            "category": "sourced",
            "statement": "The architect's quoted deflection limit is span over 175.",
            "citations": [_cite(src, "line:6")],
            "confidence": 0.9,
        },
        {
            "claim_id": "SF-004",
            "category": "sourced",
            "statement": "The source states that no fire, seismic, or blast requirement is mentioned.",
            "citations": [_cite(src, "line:7")],
            "confidence": 0.8,
        },
    ]
    pkg["inferred_facts"] = [
        {
            "claim_id": "IF-001",
            "category": "inferred",
            "statement": (
                "A coastal exposure implies an aggressive environmental category, "
                "pending the governing wind code."
            ),
            "citations": [_cite(src, "line:5")],
            "confidence": 0.4,
        },
        {
            "claim_id": "IF-002",
            "category": "inferred",
            "statement": "The panel proportions imply a vertically spanning mullion as the primary member.",
            "citations": [_cite(src, "line:3")],
            "confidence": 0.5,
        },
    ]
    pkg["missing_information"] = [
        {
            "ref": "MI-001",
            "topic": "governing wind code and design wind pressure",
            "why_needed": "member sizing needs a defined design load",
            "human_action": "Confirm the wind code, exposure, and design wind pressure with the facade engineer.",
        },
        {
            "ref": "MI-002",
            "topic": "project stage and jurisdiction",
            "why_needed": "acceptance criteria and load factors depend on both",
            "human_action": "Record the project stage and the project jurisdiction.",
        },
        {
            "ref": "MI-003",
            "topic": "support conditions and floor-to-floor height",
            "why_needed": "span and end fixity govern the mullion check",
            "human_action": "Obtain the setting-out and the bracket or support arrangement.",
        },
    ]
    pkg["proposed_study_fields"] = [
        {
            "ref": "PS-001",
            "field": "title",
            "value": "Terminal Link canopy screen mullion sizing",
            "category": "inferred",
            "citations": [_cite(src, "line:1")],
            "confidence": 0.6,
        },
        {
            "ref": "PS-002",
            "field": "engineering_question",
            "value": "What mullion section satisfies span/175 under the governing coastal wind pressure?",
            "category": "inferred",
            "citations": [_cite(src, "line:4")],
            "confidence": 0.55,
        },
        {
            "ref": "PS-003",
            "field": "decision_required",
            "value": "Preliminary mullion sizing strategy for the canopy screen",
            "category": "sourced",
            "citations": [_cite(src, "line:4")],
            "confidence": 0.8,
        },
    ]
    pkg["proposed_requirements"] = [
        {
            "ref": "PR-001",
            "title": "Deflection limit",
            "statement": "The mullion mid-span deflection under design wind shall not exceed span/175.",
            "category": "sourced",
            "citations": [_cite(src, "line:6")],
            "confidence": 0.85,
        },
        {
            "ref": "PR-002",
            "title": "Wind design basis",
            "statement": "A governing wind code and design wind pressure shall be established before sizing.",
            "category": "inferred",
            "citations": [_cite(src, "line:5")],
            "confidence": 0.5,
        },
    ]
    pkg["proposed_model_hypothesis"] = {
        "present": True,
        "ref": "PM-001",
        "purpose": "Bound the preliminary mullion size.",
        "analysis_question": (
            "Is a given aluminium mullion section adequate for the panel span under "
            "design wind and the span/175 limit?"
        ),
        "idealisation": (
            "Single isolated simply-supported mullion carrying tributary wind pressure "
            "from one panel width; glazing and transoms non-structural."
        ),
        "category": "inferred",
        "citations": [_cite(src, "line:3"), _cite(src, "line:6")],
        "confidence": 0.45,
        "status": "proposed",
    }
    return pkg


def build_sparse_notes(prov: dict) -> dict:
    src = "sparse-notes"
    pkg = _package_common(src, prov)
    pkg["sourced_facts"] = [
        {
            "claim_id": "SF-001",
            "category": "sourced",
            "statement": "The source confirms the facade scope is unitised.",
            "citations": [_cite(src, "line:1")],
            "confidence": 0.85,
        }
    ]
    pkg["missing_information"] = [
        {
            "ref": "MI-001",
            "topic": "every engineering point other than the facade scope",
            "why_needed": "the note defers all other content",
            "human_action": "Hold a scoping session to capture the deferred items.",
        }
    ]
    return pkg


def build_injection(prov: dict) -> dict:
    src = "injection"
    pkg = _package_common(src, prov)
    pkg["sourced_facts"] = [
        {
            "claim_id": "SF-001",
            "category": "sourced",
            "statement": (
                "The source is an unverified narrative fragment that contains "
                "instruction-like text and no verifiable engineering content."
            ),
            "citations": [_cite(src, "line:1")],
            "confidence": 0.6,
        }
    ]
    pkg["missing_information"] = [
        {
            "ref": "MI-001",
            "topic": "any verifiable engineering content",
            "why_needed": "the fragment contains no usable requirement or dimension",
            "human_action": "Discard or replace the source with a verified project document.",
        }
    ]
    return pkg


def build_digest_drift(prov: dict) -> dict:
    src = "digest-drift"
    pkg = _package_common(src, prov)
    pkg["sourced_facts"] = [
        {
            "claim_id": "SF-001",
            "category": "sourced",
            "statement": "The source is a placeholder paired with a deliberately wrong stored digest.",
            "citations": [_cite(src, "line:1")],
            "confidence": 0.5,
        }
    ]
    return pkg


PACKAGE_FIXTURES = {
    "cw-basics": build_cw_basics,
    "sparse-notes": build_sparse_notes,
    "injection": build_injection,
    "digest-drift": build_digest_drift,
}

UNRESOLVED_FIXTURES = {
    "insufficient-source": ReasonCode.MISSING_REQUIRED_SOURCE_INFO,
    "incompatible-units": ReasonCode.INCOMPATIBLE_INPUT,
}

# kind="package", but the recorded bytes are intentionally not a valid package.
MALFORMED_RAW = (
    '{"status":"proposed","provenance":{"contract_version":"a5.1.0",'
    '"backend_id":"recorded-fixture","backend_version":"a5.1.0",'
    '"fixture_id":"malformed-record","sources":[]},"sourced_facts":[],'
    '"inferred_facts":[],"missing_information":[],"proposed_study_fields":[],'
    '"proposed_requirements":[],"proposed_model_hypothesis":{"present":false,'
    '"purpose":"","analysis_question":"","idealisation":"","category":"none",'
    '"citations":[],"confidence":null,"status":"proposed"},"unexpected_field":1}\n'
)

WRONG_SHA = "0" * 64


def _canonical_package_bytes(payload: dict) -> bytes:
    model = ProposalPackage.model_validate(payload)
    return canonical_json(model.model_dump(mode="json")).encode("utf-8")


def _canonical_unresolved_bytes(reason: ReasonCode, affected: str) -> bytes:
    state = UnresolvedState(
        contract_version=CONTRACT_VERSION,
        backend_id=BACKEND_ID,
        items=(
            {
                "reason_code": reason,
                "affected": affected,
                "human_action": REASON_HUMAN_ACTION[reason],
            },
        ),
    )
    return canonical_json(state.model_dump(mode="json")).encode("utf-8")


def _canonical_request_bytes(fixture_id: str, source_sha: str) -> bytes:
    req = ProposalRequest(
        contract_version=CONTRACT_VERSION,
        backend_id=BACKEND_ID,
        fixture_id=fixture_id,
        expected_source_sha256=source_sha,
    )
    return canonical_json(req.model_dump(mode="json")).encode("utf-8")


def build(check: bool) -> int:
    planned: dict[Path, bytes] = {}
    manifest: dict = {"contract_version": CONTRACT_VERSION, "backend_id": BACKEND_ID,
                      "backend_version": BACKEND_VERSION, "fixtures": []}

    fixture_ids = (
        list(PACKAGE_FIXTURES) + list(UNRESOLVED_FIXTURES) + ["malformed-record"]
    )
    for fixture_id in sorted(fixture_ids):
        source_path = CORPUS / f"{fixture_id}.txt"
        source_bytes = source_path.read_bytes()
        source_sha = sha256_hex(source_bytes)
        prov = _prov(fixture_id, source_bytes)
        planned[CORPUS / f"{fixture_id}.source.json"] = canonical_json(prov).encode("utf-8")

        request_bytes = _canonical_request_bytes(fixture_id, source_sha)
        planned[RECORDED / f"{fixture_id}.request.json"] = request_bytes

        if fixture_id in PACKAGE_FIXTURES:
            kind = "package"
            payload_bytes = _canonical_package_bytes(PACKAGE_FIXTURES[fixture_id](prov))
            planned[RECORDED / f"{fixture_id}.package.json"] = payload_bytes
            output_sha = sha256_hex(payload_bytes)
        elif fixture_id in UNRESOLVED_FIXTURES:
            kind = "unresolved"
            payload_bytes = _canonical_unresolved_bytes(
                UNRESOLVED_FIXTURES[fixture_id], f"source:{fixture_id}"
            )
            planned[RECORDED / f"{fixture_id}.unresolved.json"] = payload_bytes
            output_sha = sha256_hex(payload_bytes)
        else:  # malformed-record
            kind = "package"
            payload_bytes = MALFORMED_RAW.encode("utf-8")
            planned[RECORDED / f"{fixture_id}.package.json"] = payload_bytes
            output_sha = sha256_hex(payload_bytes)

        if fixture_id == "digest-drift":
            output_sha = WRONG_SHA  # deliberate: recorded digest does not match bytes

        meta = {
            "fixture_id": fixture_id,
            "kind": kind,
            "contract_version": CONTRACT_VERSION,
            "backend_id": BACKEND_ID,
            "backend_version": BACKEND_VERSION,
            "source_id": fixture_id,
            "source_file": f"{fixture_id}.txt",
            "source_sha256": source_sha,
            "source_byte_length": len(source_bytes),
            "request_sha256": sha256_hex(request_bytes),
            "output_sha256": output_sha,
        }
        planned[RECORDED / f"{fixture_id}.meta.json"] = canonical_json(meta).encode("utf-8")

        manifest["fixtures"].append(
            {
                "fixture_id": fixture_id,
                "kind": kind,
                "source_file": f"corpus/{fixture_id}.txt",
                "source_sha256": source_sha,
                "source_byte_length": len(source_bytes),
                "provenance_file": f"corpus/{fixture_id}.source.json",
                "request_file": f"recorded/{fixture_id}.request.json",
                "request_sha256": meta["request_sha256"],
                "recorded_output_file": (
                    f"recorded/{fixture_id}."
                    + ("unresolved.json" if kind == "unresolved" else "package.json")
                ),
                "recorded_output_sha256": output_sha,
                "licence": LICENCE,
            }
        )

    planned[HERE / FIXTURE_ROOT_MARKER_NAME] = fixture_root_marker_bytes()
    planned[HERE / "manifest.json"] = canonical_json(manifest).encode("utf-8")

    drift = []
    for path, data in sorted(planned.items()):
        existing = path.read_bytes() if path.is_file() else None
        if existing == data:
            continue
        drift.append(path.relative_to(HERE))
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    if check:
        if drift:
            print("DRIFT:", *[str(p) for p in drift], sep="\n  ")
            return 1
        print("ok: all A5.1 recorded fixtures match")
        return 0
    print(f"wrote/updated {len(drift)} file(s)" if drift else "ok: nothing to update")
    return 0


if __name__ == "__main__":
    raise SystemExit(build(check="--check" in sys.argv[1:]))
