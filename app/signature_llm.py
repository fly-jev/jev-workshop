"""Image example, path A: generative LLM returning a typed JSON.

The model looks at the image and must answer with a JSON that matches the
Pydantic schema below. The answer is a yes/no: there is no confidence level,
so the application can only accept or reject.
"""

import base64
import io
import os
import time

import httpx
from PIL import Image
from pydantic import BaseModel, ConfigDict

from app import mock

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://hecate.governancia.online/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-opus-5-5")

PROMPT = (
    "You are validating an enrollment document sent by a student. "
    "Look at the image and answer: does this document have a signature? "
    "Answer only with the requested JSON."
)


# O contrato tipado: o LLM é obrigado a devolver exatamente isto.
class SignatureCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_signature: bool
    reason: str


def check_signature(image_bytes: bytes) -> dict:
    if not os.getenv("LLM_API_KEY"):
        return _mock_result(image_bytes)

    started = time.perf_counter()
    response = httpx.post(
        f"{LLM_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('LLM_API_KEY')}"},
        json={
            "model": LLM_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {"type": "image_url", "image_url": {"url": _data_url(image_bytes)}},
                    ],
                }
            ],
            # força a resposta a seguir o schema da classe SignatureCheck
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "signature_check",
                    "strict": True,
                    "schema": SignatureCheck.model_json_schema(),
                },
            },
        },
        timeout=60,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    body = response.json()

    raw_json = body["choices"][0]["message"]["content"]
    answer = SignatureCheck.model_validate_json(raw_json)
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
        "output_tokens": output_tokens,
        "cost_usd": usage.get("cost"),  # custo informado pelo próprio gateway
    }


def _data_url(image_bytes: bytes) -> str:
    media_type = f"image/{Image.open(io.BytesIO(image_bytes)).format.lower()}"
    return f"data:{media_type};base64,{base64.standard_b64encode(image_bytes).decode()}"


def _mock_result(image_bytes: bytes) -> dict:
    started = time.perf_counter()
    p_signed = mock.signature_probability(image_bytes)
    answer = SignatureCheck(
        has_signature=p_signed >= 0.5,
        reason="Mock answer (no LLM_API_KEY): blue ink detected near the signature line."
        if p_signed >= 0.5
        else "Mock answer (no LLM_API_KEY): no ink detected near the signature line.",
    )
    return {
        "mock": True,
        "model": "mock",
        "raw_json": answer.model_dump_json(indent=2),
        "answer": answer.model_dump(),
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "input_tokens": None,
        "output_tokens": None,
        "cost_usd": None,
    }
