"""Text example, path B: decision model (fly-jev).

Same order as the LLM path: the policy goes first in the state and the
customer message goes last, so the fixed prefix can be reused.

Contract: https://fly-jev.com/docs/como-usar
"""

import os
import time

import httpx

from app import mock

JEV_URL = os.getenv("JEV_URL", "https://br.fly-jev.com/v1/decisions")
JEV_MODEL = "fly-jev-y0-lite"  # modelo só texto

QUESTION = {
    "type": "noul",
    "instructions": "Esta mensagem precisa ser transferida para um atendente humano?",
}


def check_escalation(policy: str, message: str) -> dict:
    # 1º a política (prefixo fixo), 2º a mensagem do cliente
    state = f"{policy}\n\nMensagem do cliente: {message}".strip()

    if not os.getenv("JEV_API_KEY"):
        return _mock_result(policy, message, state)

    started = time.perf_counter()
    response = httpx.post(
        JEV_URL,
        headers={"Authorization": f"Bearer {os.getenv('JEV_API_KEY')}"},
        json={
            "model": JEV_MODEL,
            "state": state,
            "questions": {"needs_human": QUESTION},
        },
        timeout=60,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    body = response.json()

    p_yes = body["answers"]["needs_human"]["noul"]
    return {
        "mock": False,
        "model": body.get("model", JEV_MODEL),
        "request": {"state": state, "questions": {"needs_human": QUESTION}},
        "probabilities": {"yes": round(p_yes, 4), "no": round(1 - p_yes, 4)},
        "latency_ms": round(latency_ms),
        "processing_ms": body.get("processing_ms"),
        "cost_usd": body.get("usage", {}).get("cost_usd"),
    }


def _mock_result(policy: str, message: str, state: str) -> dict:
    started = time.perf_counter()
    p_yes = mock.escalation_probability(policy, message)
    return {
        "mock": True,
        "model": "mock",
        "request": {"state": state, "questions": {"needs_human": QUESTION}},
        "probabilities": {"yes": round(p_yes, 4), "no": round(1 - p_yes, 4)},
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "processing_ms": None,
        "cost_usd": None,
    }
