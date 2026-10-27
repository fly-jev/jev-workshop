# Decisions: LLM vs Jev

Workshop demo. The same decision made in two ways, side by side: a generative LLM returning a typed JSON, and a decision model (fly-jev) returning probabilities.

## Example 0 · Routing: which path should the agent take?

One `choice` question picks the path for each message: `modelo_leve`, `rag`, `reasoning` or `humano`. Try *"Bom dia! Tudo bem?"*: it does not need the strongest model.

| | A · LLM with typed JSON | B · fly-jev |
|---|---|---|
| File | `app/routing_llm.py` | `app/routing_jev.py` |
| Output | `Route(path: Literal[...], reason: str)` | one probability per route |
| Policy (`app/policy.py`) | the LLM's label | best route if p ≥ threshold, else the reasoning model |

Question and options are shared by both paths in `app/routes.py`.

## Example 1 · Text: does this message need a human?

Message: *"Você tem a blusa cod 123 na cor preta?"* (from the [fly-jev playground](https://fly-jev.com/playground)). Change the **policy** and watch the decision flip.

The policy is a fixed prefix sent **before** the message, so the provider can reuse the prompt cache; only the message at the end changes.

| | A · LLM with typed JSON | B · fly-jev |
|---|---|---|
| File | `app/escalation_llm.py` | `app/escalation_jev.py` |
| Order | `system` = policy + question → `user` = message | `state` = policy + message, question `noul` |
| Output | `EscalationCheck(needs_human: bool, reason: str)` | `p(yes)` |
| Model | `LLM_MODEL` (Hecate) | `fly-jev-y0-lite` (text only) |

## Example 2 · Image: is the document signed?

| | A · LLM with typed JSON | B · fly-jev |
|---|---|---|
| File | `app/signature_llm.py` | `app/signature_jev.py` |
| Output | `SignatureCheck(has_signature: bool, reason: str)` | `p(yes)` |
| Policy (`app/policy.py`) | accept / ask to resubmit | accept / **human review** / ask to resubmit |
| Model | `LLM_MODEL` (Hecate) | `fly-jev-y0` (accepts images) |

## Running

```bash
git clone <repo> && cd <repo>
cp .env.example .env        # preencha LLM_API_KEY e JEV_API_KEY
docker compose up --build
```

Abrir http://localhost:8000. O guia do workshop (fluxo do agente, onde entram as decisões e os dois casos) fica em http://localhost:8000/guide.html.

## Configuration

Preencha as chaves no `.env` (já criado a partir do `.env.example`; o arquivo está no `.gitignore`):

| Variável | Uso |
|---|---|
| `LLM_API_KEY` | chave do Hecate (`LLM_BASE_URL`, API compatível com OpenAI, `POST /chat/completions`) |
| `LLM_MODEL` | nome do modelo no gateway |
| `JEV_API_KEY` | chave do fly-jev (`JEV_URL`, `POST /v1/decisions`, contrato em https://fly-jev.com/docs/como-usar) |

Se uma chave estiver vazia, aquele caminho roda em **modo mock**: `app/mock.py`, uma heurística que conta pixels de tinta azul na linha de assinatura. Serve para ensaiar sem credenciais. Nesse modo, latência e custo **não** representam os modelos reais. A tela marca esses resultados com `mock`.

O custo vem das próprias APIs: `usage.cost` no Hecate e `usage.cost_usd` no fly-jev.

## Samples

`samples/images/` tem um documento real em duas versões: `01_signed_clear_01.jpg` (assinado) e `02_unsigned_clear_01.jpg` (a mesma imagem com a assinatura apagada). Qualquer `.jpg`, `.png` ou `.webp` colocado nessa pasta aparece na tela sem precisar de rebuild.

## What to look at in the workshop

1. **Text:** rode a blusa com "No policy" e depois com "Agent has stock tools". A mensagem é a mesma; o enunciado muda a decisão.
2. **Typed JSON vs probability:** o LLM devolve um booleano validado pelo schema. O fly-jev devolve `p(yes)`, e o corte fica em `app/policy.py`. Mova o slider e a ação muda sem chamar o modelo de novo.
3. **Image:** rode o par assinado / sem assinatura. Os dois acertam; compare custo, latência e o formato da resposta (booleano vs probabilidade).
