import base64
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import escalation_jev, escalation_llm, policy, routing_jev, routing_llm, signature_jev, signature_llm

ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = ROOT / "samples" / "images"

app = FastAPI(title="Decisions: LLM vs Jev")


# mostra na tela o erro devolvido pela API externa (status + corpo)
@app.exception_handler(httpx.HTTPStatusError)
def upstream_error(_: Request, exc: httpx.HTTPStatusError) -> JSONResponse:
    detail = f"{exc.request.url.host} returned {exc.response.status_code}: {exc.response.text[:500]}"
    return JSONResponse(status_code=502, content={"detail": detail})


# timeout, conexão recusada etc.
@app.exception_handler(httpx.RequestError)
def upstream_unreachable(_: Request, exc: httpx.RequestError) -> JSONResponse:
    return JSONResponse(status_code=504, content={"detail": f"{exc.request.url.host}: {type(exc).__name__}"})


# ---------- Exemplo de roteamento: qual caminho o agente deve seguir? ----------


class RoutingRequest(BaseModel):
    message: str


class RoutingPolicyRequest(BaseModel):
    probabilities: dict[str, float]
    min_probability: float


@app.post("/api/routing/llm")
def routing_with_llm(req: RoutingRequest) -> dict:
    result = routing_llm.choose_route(req.message)
    result["action"] = result["answer"]["path"]
    return result


@app.post("/api/routing/jev")
def routing_with_jev(req: RoutingRequest) -> dict:
    result = routing_jev.choose_route(req.message)
    result["action"] = policy.decide_route_from_jev(result["probabilities"])
    return result


# reaplica a política sem chamar o modelo de novo (slider da tela)
@app.post("/api/routing/policy")
def routing_policy(req: RoutingPolicyRequest) -> dict:
    return {"action": policy.decide_route_from_jev(req.probabilities, req.min_probability)}


# ---------- Exemplo de texto: precisa de atendente humano? ----------


class EscalationRequest(BaseModel):
    policy: str
    message: str


class EscalationPolicyRequest(BaseModel):
    p_yes: float
    transfer_above: float


@app.post("/api/escalation/llm")
def escalation_with_llm(req: EscalationRequest) -> dict:
    result = escalation_llm.check_escalation(req.policy, req.message)
    result["action"] = policy.decide_escalation_from_llm(result["answer"]["needs_human"])
    return result


@app.post("/api/escalation/jev")
def escalation_with_jev(req: EscalationRequest) -> dict:
    result = escalation_jev.check_escalation(req.policy, req.message)
    result["action"] = policy.decide_escalation_from_jev(result["probabilities"]["yes"])
    return result


# reaplica a política sem chamar o modelo de novo (slider da tela)
@app.post("/api/escalation/policy")
def escalation_policy(req: EscalationPolicyRequest) -> dict:
    return {"action": policy.decide_escalation_from_jev(req.p_yes, req.transfer_above)}


# ---------- Exemplo de imagem: o documento tem assinatura? ----------


class SignatureRequest(BaseModel):
    sample: str | None = None
    image_base64: str | None = None


class SignaturePolicyRequest(BaseModel):
    p_signed: float
    accept_above: float
    reject_below: float


def load_image(req: SignatureRequest) -> bytes:
    if req.sample:
        path = (SAMPLES_DIR / req.sample).resolve()
        if path.parent != SAMPLES_DIR or not path.is_file():
            raise HTTPException(404, "Sample not found")
        return path.read_bytes()
    if req.image_base64:
        return base64.b64decode(req.image_base64)
    raise HTTPException(400, "Send a sample name or an image")


@app.get("/api/samples")
def list_samples() -> list[str]:
    return sorted(p.name for p in SAMPLES_DIR.iterdir() if p.suffix in (".png", ".jpg", ".jpeg", ".webp"))


@app.post("/api/signature/llm")
def signature_with_llm(req: SignatureRequest) -> dict:
    result = signature_llm.check_signature(load_image(req))
    result["action"] = policy.decide_from_llm(result["answer"]["has_signature"])
    return result


@app.post("/api/signature/jev")
def signature_with_jev(req: SignatureRequest) -> dict:
    result = signature_jev.check_signature(load_image(req))
    result["action"] = policy.decide_from_jev(result["probabilities"]["yes"])
    return result


# reaplica a política sem chamar o modelo de novo (sliders da tela)
@app.post("/api/signature/policy")
def signature_policy(req: SignaturePolicyRequest) -> dict:
    return {"action": policy.decide_from_jev(req.p_signed, req.accept_above, req.reject_below)}


app.mount("/samples", StaticFiles(directory=SAMPLES_DIR), name="samples")
app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
