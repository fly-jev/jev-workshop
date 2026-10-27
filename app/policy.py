"""Turning answers into actions. This is application code, not model code."""

ACCEPT = "accept"
ASK_RESUBMIT = "ask_resubmit"
HUMAN_REVIEW = "human_review"


# Caminho A: com um booleano só existem duas saídas possíveis.
def decide_from_llm(has_signature: bool) -> str:
    return ACCEPT if has_signature else ASK_RESUBMIT


# Caminho B: com probabilidade, a zona de dúvida vira revisão humana.
def decide_from_jev(p_signed: float, accept_above: float = 0.8, reject_below: float = 0.3) -> str:
    if p_signed >= accept_above:
        return ACCEPT
    if p_signed <= reject_below:
        return ASK_RESUBMIT
    return HUMAN_REVIEW


TRANSFER = "transfer_to_human"
AUTOMATE = "automate"


# Texto: com booleano, o LLM já decidiu sozinho.
def decide_escalation_from_llm(needs_human: bool) -> str:
    return TRANSFER if needs_human else AUTOMATE


# Texto: com probabilidade, o corte é uma escolha do negócio.
def decide_escalation_from_jev(p_yes: float, transfer_above: float = 0.5) -> str:
    return TRANSFER if p_yes >= transfer_above else AUTOMATE


STRONG_MODEL_FALLBACK = "reasoning"


# Roteamento: se nenhuma rota está claramente na frente, usa o caminho mais seguro.
def decide_route_from_jev(probabilities: dict[str, float], min_probability: float = 0.6) -> str:
    best = max(probabilities, key=probabilities.get)
    return best if probabilities[best] >= min_probability else STRONG_MODEL_FALLBACK
