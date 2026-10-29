"""Routing example, path A: generative LLM returning a typed JSON.

The LLM picks the path for the message. Pydantic's Literal becomes an enum in
the JSON schema, so the answer is always one of the four routes, but it comes
without any confidence level.
"""

import os
import time
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict

from app import mock
from app.routes import QUESTION, ROUTES

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://hecate.governancia.online/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-5.5")

SYSTEM = QUESTION + "\n\n" + "\n".join(f"- {name}: {desc}" for name, desc in ROUTES.items())


# O contrato tipado: o Literal vira um enum no JSON Schema.
class Route(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Literal["modelo_leve", "rag", "reasoning", "humano"]
    reason: str


def choose_route(message: str) -> dict:
    if not os.getenv("LLM_API_KEY"):
        return _mock_result(message)

    started = time.perf_counter()
    response = httpx.post(
        f"{LLM_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('LLM_API_KEY')}"},
        json={
            "model": LLM_MODEL,
            "messages": [
                # 1º a pergunta e as opções (prefixo fixo), 2º a mensagem
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": message},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "route", "strict": True, "schema": Route.model_json_schema()},
            },
        },
        timeout=60,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    body = response.json()

    raw_json = body["choices"][0]["message"]["content"]
    answer = Route.model_validate_json(raw_json)
    usage = body.get("usage", {})

    return {
        "mock": False,
        "model": body.get("model", LLM_MODEL),
        "raw_json": raw_json,
        "answer": answer.model_dump(),
        "latency_ms": round(latency_ms),
        "input_tokens": usage.get("prompt_tokens"),
        "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "cost_usd": usage.get("cost"),  # custo informado pelo próprio gateway
    }


def _mock_result(message: str) -> dict:
    started = time.perf_counter()
    probabilities = mock.route_probabilities(message)
    answer = Route(
        path=max(probabilities, key=probabilities.get),
        reason="Mock answer (no LLM_API_KEY): keyword heuristic.",
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
