"""Offline stand-in used when no API key / Jev URL is configured.

Not a real model: it counts blue-ink pixels around the signature line of the
sample documents, so the demo runs without any credentials.
"""

import io
import math

from PIL import Image

# região da linha de assinatura nas imagens de exemplo (escala 400x500)
SIGNATURE_BOX = (200, 350, 400, 500)


def signature_probability(image_bytes: bytes) -> float:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((400, 500))
    pixels = list(img.crop(SIGNATURE_BOX).get_flattened_data())
    blue_ratio = sum(1 for r, g, b in pixels if b > r + 25 and b > g + 15) / len(pixels)
    return 1 / (1 + math.exp(-(blue_ratio - 0.005) * 500))


# texto: se a política diz que o agente consulta estoque, pergunta de estoque não escala
def escalation_probability(policy: str, message: str) -> float:
    asks_stock = any(w in message.lower() for w in ("tem a", "tem o", "cor", "tamanho", "estoque"))
    if asks_stock and "estoque" in policy.lower():
        return 0.22
    return 0.81


# roteamento: palavras-chave simples, só para rodar sem chave
def route_probabilities(message: str) -> dict[str, float]:
    text = message.lower()
    if any(w in text for w in ("procon", "processar", "fraude", "atendente", "indevida")):
        top = "humano"
    elif any(w in text for w in ("compar", "calcul", "mais barato", "quanto sai")):
        top = "reasoning"
    elif any(w in text for w in ("prazo", "preço", "valor", "documento", "regra", "?")):
        top = "rag"
    else:
        top = "modelo_leve"
    routes = ("modelo_leve", "rag", "reasoning", "humano")
    return {r: (0.85 if r == top else 0.05) for r in routes}
