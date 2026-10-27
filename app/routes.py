"""The routing question, shared by both paths so they answer exactly the same thing."""

QUESTION = "Qual caminho o agente deve usar para responder esta mensagem?"

ROUTES = {
    "modelo_leve": "saudação, agradecimento ou conversa simples, sem consultar dados",
    "rag": "pergunta sobre regras, prazos, preços ou informações que estão na base de conhecimento",
    "reasoning": "pedido que exige comparar opções, calcular ou planejar em vários passos",
    "humano": "reclamação grave, ameaça jurídica, fraude ou pedido explícito por um atendente",
}
