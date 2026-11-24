"""
WhatsAppChannel: envio pelo provedor (hoje, Digisac). Fica atrás da chave WHATSAPP_ATIVO.

Com a chave desligada (padrão), nada é enviado e o portal web funciona normalmente.
Retentativas com backoff, fila de envio e indicador de saúde estão previstos para a Fase 4.
"""
import logging

from django.conf import settings

from .base import ChannelAdapter

log = logging.getLogger(__name__)

# Contatos do simulador do painel: as mensagens ficam só no banco (nunca vão para o Digisac).
PREFIXO_SIMULADOR = "simulador-"


class WhatsAppChannel(ChannelAdapter):
    nome = "whatsapp"

    def __init__(self, cliente=None):
        self._cliente = cliente

    def disponivel(self) -> bool:
        return bool(settings.WHATSAPP_ATIVO)

    @property
    def cliente(self):
        if self._cliente is None:
            from apps.digisac.client import ClienteDigisac
            self._cliente = ClienteDigisac()
        return self._cliente

    def entregar(self, conversa, textos):
        if conversa.identificador.startswith(PREFIXO_SIMULADOR):
            return  # simulador do painel: o "celular" lê as mensagens direto do banco
        if not self.disponivel():
            log.warning("WhatsApp desativado: %d mensagem(ns) da conversa #%s ficaram só no histórico.",
                        len(textos), conversa.pk)
            return
        for texto in textos:
            try:
                self.cliente.enviar_texto(conversa.identificador, texto)
            except Exception:
                # A mensagem já está gravada; o analista vê no painel. Não propaga.
                log.exception("Falha ao enviar mensagem pelo WhatsApp (conversa #%s).", conversa.pk)
                return
