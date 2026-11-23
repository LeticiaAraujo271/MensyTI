from .base import ChannelAdapter


class WebChannel(ChannelAdapter):
    """Portal web: as mensagens ficam no banco e o navegador as busca (/api/mensagens/)."""

    nome = "web"

    def entregar(self, conversa, textos):
        return None
