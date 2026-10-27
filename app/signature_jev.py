"""Image example, path B: decision model (fly-jev).

Instead of generating text, fly-jev receives a state, the image and a yes/no
question, and returns the probability of "yes". Deciding what to do with that
probability is the application's job (see policy.py).

Contract: https://fly-jev.com/docs/como-usar
"""

import base64
import io
import os
import time

import httpx
from PIL import Image

from app import mock

JEV_URL = os.getenv("JEV_URL", "https://br.fly-jev.com/v1/decisions")
JEV_MODEL = "fly-jev-y0"  # modelo com suporte a imagem

STATE = "Enrollment document sent by a student through the support chat."
QUESTION = {
    "type": "noul",
    "instructions": "Does this document have a signature?",
}


def check_signature(image_bytes: bytes) -> dict:
    if not os.getenv("JEV_API_KEY"):
        return _mock_result(image_bytes)

    started = time.perf_counter()
    response = httpx.post(
        JEV_URL,
        headers={"Authorization": f"Bearer {os.getenv('JEV_API_KEY')}"},
        json={
            "model": JEV_MODEL,
            "state": STATE,
            "images": [{"url": _data_url(image_bytes)}],
            "questions": {"signature": QUESTION},
        },
        timeout=60,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    body = response.json()

    p_yes = body["answers"]["signature"]["noul"]
    return {
        "mock": False,
        "model": body.get("model", JEV_MODEL),
        "request": {"state": STATE, "images": ["<image>"], "questions": {"signature": QUESTION}},
        "probabilities": {"yes": round(p_yes, 4), "no": round(1 - p_yes, 4)},
        "latency_ms": round(latency_ms),
        "processing_ms": body.get("processing_ms"),
        "cost_usd": body.get("usage", {}).get("cost_usd"),
    }


def _data_url(image_bytes: bytes) -> str:
    media_type = f"image/{Image.open(io.BytesIO(image_bytes)).format.lower()}"
    return f"data:{media_type};base64,{base64.standard_b64encode(image_bytes).decode()}"


def _mock_result(image_bytes: bytes) -> dict:
    started = time.perf_counter()
    p_yes = mock.signature_probability(image_bytes)
    return {
        "mock": True,
        "model": "mock",
        "request": {"state": STATE, "images": ["<image>"], "questions": {"signature": QUESTION}},
        "probabilities": {"yes": round(p_yes, 4), "no": round(1 - p_yes, 4)},
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "processing_ms": None,
        "cost_usd": None,
    }
