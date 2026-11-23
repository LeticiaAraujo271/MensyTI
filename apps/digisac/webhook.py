"""
Leitura do payload de webhook do Digisac.

Formato esperado (evento de mensagem nova):
{
  "event": "message.created",
  "data": {
    "id": "...", "contactId": "...", "ticketId": "...", "serviceId": "...",
    "isFromMe": false, "isFromBot": false, "type": "chat", "text": "oi",
    "data": {"ticketClose": false, ...}
  }
}
Python puro: não depende de Django, para poder ser testado isoladamente.
"""
from __future__ import annotations

from dataclasses import dataclass

EVENTO_MENSAGEM_NOVA = "message.created"
TIPO_TEXTO = "chat"
TIPO_TICKET = "ticket"  # mensagens de sistema (abertura/transferência/fechamento)


@dataclass
class MensagemDigisac:
    id: str
    contato_id: str
    ticket_id: str
    service_id: str
    texto: str
    tipo: str
    eh_do_contato: bool          # False = enviada pela empresa (atendente ou bot)
    fechou_ticket: bool          # mensagem de sistema de fechamento de atendimento


def interpretar(payload: dict) -> list[MensagemDigisac]:
    """Devolve as mensagens do payload (o Digisac pode mandar uma ou uma lista)."""
    if not isinstance(payload, dict) or payload.get("event") != EVENTO_MENSAGEM_NOVA:
        return []
    dados = payload.get("data")
    itens = dados if isinstance(dados, list) else [dados]
    mensagens = []
    for d in itens:
        if not isinstance(d, dict) or not d.get("contactId"):
            continue
        interno = d.get("data") if isinstance(d.get("data"), dict) else {}
        mensagens.append(
            MensagemDigisac(
                id=str(d.get("id") or ""),
                contato_id=str(d["contactId"]),
                ticket_id=str(d.get("ticketId") or ""),
                service_id=str(d.get("serviceId") or ""),
                texto=(d.get("text") or "").strip(),
                tipo=d.get("type") or "",
                eh_do_contato=not d.get("isFromMe") and not d.get("isFromBot"),
                fechou_ticket=bool(interno.get("ticketClose")),
            )
        )
    return mensagens
