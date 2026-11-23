from __future__ import annotations

from abc import ABC, abstractmethod


class ChannelAdapter(ABC):
    """Contrato de um canal de atendimento."""

    nome: str = ""

    def disponivel(self) -> bool:
        """O canal está ligado e operacional?"""
        return True

    @abstractmethod
    def entregar(self, conversa, textos: list[str]) -> None:
        """
        Entrega ao colaborador mensagens que JÁ estão gravadas no banco.
        Nunca deve levantar exceção: uma falha de entrega não pode perder mensagens
        nem derrubar o atendimento (o histórico continua no banco e no painel).
        """
