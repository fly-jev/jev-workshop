"""Routing example, path B: decision model (fly-jev).

One "choice" question returns a probability for each route. The application
decides what to do when no route is clearly ahead (see policy.py).

Contract: https://fly-jev.com/docs/como-usar
"""

import os
import time

import httpx

from app import mock
from app.routes import QUESTION, ROUTES

JEV_URL = os.getenv("JEV_URL", "https://br.fly-jev.com/v1/decisions")
JEV_MODEL = "fly-jev-y0-lite"  # modelo só texto

CHOICE = {"type": "choice", "instructions": QUESTION, "criteria": ROUTES}


def choose_route(message: str) -> dict:
    state = f"Mensagem do cliente: {message}"

    if not os.getenv("JEV_API_KEY"):
        return _mock_result(message, state)

    started = time.perf_counter()
    response = httpx.post(
        JEV_URL,
        headers={"Authorization": f"Bearer {os.getenv('JEV_API_KEY')}"},
        json={"model": JEV_MODEL, "state": state, "questions": {"route": CHOICE}},
        timeout=60,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    body = response.json()

    answer = body["answers"]["route"]
    return {
        "mock": False,
        "model": body.get("model", JEV_MODEL),
        "request": {"state": state, "questions": {"route": CHOICE}},
        "probabilities": {k: round(v, 4) for k, v in answer["probabilities"].items()},
        "latency_ms": round(latency_ms),
        "processing_ms": body.get("processing_ms"),
        "cost_usd": body.get("usage", {}).get("cost_usd"),
    }


def _mock_result(message: str, state: str) -> dict:
    started = time.perf_counter()
    return {
        "mock": True,
        "model": "mock",
        "request": {"state": state, "questions": {"route": CHOICE}},
        "probabilities": mock.route_probabilities(message),
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "processing_ms": None,
        "cost_usd": None,
    }
