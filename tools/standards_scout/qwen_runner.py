"""Model invocation.

``StubRunner`` is offline and deterministic - it is what the tests and the
sandboxed pipeline use. ``OllamaRunner`` talks to an OpenAI-compatible local
endpoint (Ollama's ``/v1``) with structured output and ``temperature = 0``; it
CANNOT run inside the Noam sandbox (loopback network denied) and must be driven
from an unsandboxed environment.

Neither runner validates the response - that is ``validate.py``'s job.
"""

from __future__ import annotations

import json
from pathlib import Path

from .interfaces import EvidencePacket, ModelRunner, ScoutRequest


def build_messages(request: ScoutRequest) -> list[dict]:
    """Compose the system + user messages. The evidence packet is the only
    authoritative source the user message offers the model."""

    lines: list[str] = [
        f"QUESTION_ID: {request.question_id}",
        "",
        "QUESTION:",
        request.question.strip(),
        "",
        "PROJECT CONTEXT (supplied for this test only):",
        request.project_context.strip() or "(none)",
        "",
        "EVIDENCE PACKET (your only authoritative source; cite these ids):",
    ]
    if not request.packet.items:
        lines.append("  (empty - no evidence retrieved)")
    for item in request.packet.items:
        lines += [
            f"  [{item.evidence_id}] document_id={item.document_id} "
            f"page={item.page} clause={item.clause} chunk_id={item.chunk_id}",
            f"      {item.text.strip()}",
        ]
    lines += [
        "",
        "RESPONSE CONTRACT:",
        "Return exactly one JSON object valid against this schema:",
        json.dumps(request.response_schema, indent=2, sort_keys=True),
    ]
    return [
        {"role": "system", "content": request.system_prompt},
        {"role": "user", "content": "\n".join(lines)},
    ]


class StubRunner(ModelRunner):
    """Deterministic offline runner.

    Reads a canned response keyed by ``question_id`` from ``responses_dir`` (a
    ``<question_id>.json`` file). When none exists it returns a well-formed
    ``INSUFFICIENT_EVIDENCE`` skeleton, so the whole pipeline is exercisable
    with zero model access.
    """

    provider_label = "stub"
    model_id = "stub-deterministic"
    provider_is_local = True
    generation_settings = {"temperature": 0.0, "deterministic": True}

    def __init__(self, responses_dir: Path | None = None) -> None:
        self._dir = Path(responses_dir) if responses_dir else None

    def run(self, request: ScoutRequest) -> dict:
        if self._dir is not None:
            canned = self._dir / f"{request.question_id}.json"
            if canned.exists():
                return json.loads(canned.read_text(encoding="utf-8"))
        return {
            "question_id": request.question_id,
            "status": "INSUFFICIENT_EVIDENCE",
            "requirements": [],
            "verification_procedure": [],
            "missing_information": [
                "StubRunner produced no canned answer for this question."
            ],
            "conflicts": [],
        }


class OllamaRunner(ModelRunner):
    """OpenAI-compatible local endpoint (default: Ollama). Not runnable in the
    Noam sandbox."""

    provider_is_local = True

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "qwen3:4b",
        provider_label: str = "ollama-openai-compat",
        timeout_s: float = 120.0,
        temperature: float = 0.0,
        seed: int = 0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_id = model
        self.provider_label = provider_label
        self.timeout_s = timeout_s
        self.generation_settings = {"temperature": temperature, "seed": seed}

    def run(self, request: ScoutRequest) -> dict:
        import urllib.error
        import urllib.request

        payload = {
            "model": self.model_id,
            "messages": build_messages(request),
            "temperature": self.generation_settings["temperature"],
            "seed": self.generation_settings["seed"],
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "scout_response",
                    "schema": request.response_schema,
                    "strict": True,
                },
            },
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:  # pragma: no cover - env dependent
            raise RuntimeError(
                f"OllamaRunner could not reach {self.base_url}: {exc}. This runner "
                f"needs loopback network and cannot run inside the Noam sandbox."
            ) from exc
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)


def make_runner(kind: str, **kwargs) -> ModelRunner:
    if kind == "stub":
        return StubRunner(kwargs.get("responses_dir"))
    if kind == "ollama":
        return OllamaRunner(
            base_url=kwargs.get("base_url", "http://localhost:11434/v1"),
            model=kwargs.get("model", "qwen3:4b"),
            provider_label=kwargs.get("provider_label", "ollama-openai-compat"),
        )
    raise ValueError(f"unknown runner kind: {kind!r}")


__all__ = [
    "build_messages",
    "StubRunner",
    "OllamaRunner",
    "make_runner",
    "EvidencePacket",
]
