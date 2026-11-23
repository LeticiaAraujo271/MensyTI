"""
Adaptadores de canal (ChannelAdapter). O motor e o orquestrador não sabem qual é o canal:
eles gravam as mensagens no banco e pedem ao adaptador para entregá-las.

  web       -> WebChannel: o navegador busca as mensagens no banco (sempre disponível)
  whatsapp  -> WhatsAppChannel: envia pelo provedor (Digisac); desligado por padrão (WHATSAPP_ATIVO)
"""
from .base import ChannelAdapter
from .web import WebChannel
from .whatsapp import WhatsAppChannel

_CANAIS = {"web": WebChannel, "whatsapp": WhatsAppChannel}


def obter_canal(nome: str) -> ChannelAdapter:
    try:
        return _CANAIS[nome]()
    except KeyError:
        raise ValueError(f"Canal desconhecido: {nome}") from None


__all__ = ["ChannelAdapter", "WebChannel", "WhatsAppChannel", "obter_canal"]
