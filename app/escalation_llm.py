"""Text example, path A: generative LLM returning a typed JSON.

The policy goes first (system message) and the customer message goes last.
The policy prefix is the same on every call, so the provider can reuse its
prompt cache; only the message at the end changes.
"""

import os
import time

import httpx
from pydantic import BaseModel, ConfigDict

from app import mock

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://hecate.governancia.online/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-opus-5-5")

QUESTION = "Esta mensagem precisa ser transferida para um atendente humano?"


# O contrato tipado: o LLM é obrigado a devolver exatamente isto.
class EscalationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    needs_human: bool
    reason: str


def check_escalation(policy: str, message: str) -> dict:
    if not os.getenv("LLM_API_KEY"):
        return _mock_result(policy, message)

    started = time.perf_counter()
    response = httpx.post(
        f"{LLM_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('LLM_API_KEY')}"},
        json={
            "model": LLM_MODEL,
            "messages": [
                # 1º a política (prefixo fixo, reaproveita cache)
                {"role": "system", "content": f"{policy}\n\n{QUESTION}".strip()},
                # 2º a mensagem do cliente (a única parte que muda)
                {"role": "user", "content": message},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "escalation_check",
                    "strict": True,
                    "schema": EscalationCheck.model_json_schema(),
                },
            },
        },
        timeout=60,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    body = response.json()

    raw_json = body["choices"][0]["message"]["content"]
    answer = EscalationCheck.model_validate_json(raw_json)
    usage = body.get("usage", {})
    input_tokens = usage.get("prompt_tokens")
    output_tokens = usage.get("completion_tokens")

    return {
        "mock": False,
        "model": body.get("model", LLM_MODEL),
        "raw_json": raw_json,
        "answer": answer.model_dump(),
        "latency_ms": round(latency_ms),
        "input_tokens": input_tokens,
        "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
        "output_tokens": output_tokens,
        "cost_usd": usage.get("cost"),  # custo informado pelo próprio gateway
    }


def _mock_result(policy: str, message: str) -> dict:
    started = time.perf_counter()
    needs_human = mock.escalation_probability(policy, message) >= 0.5
    answer = EscalationCheck(
        needs_human=needs_human,
        reason="Mock answer (no LLM_API_KEY): keyword heuristic on the policy text.",
    )
    return {
        "mock": True,
        "model": "mock",
        "raw_json": answer.model_dump_json(indent=2),
        "answer": answer.model_dump(),
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "input_tokens": None,
        "cached_tokens": None,
        "output_tokens": None,
        "cost_usd": None,
    }
