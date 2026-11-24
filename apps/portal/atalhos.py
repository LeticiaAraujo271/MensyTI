"""
Uma porta por tela (usado no GitHub Codespaces, que mostra uma linha por porta na aba PORTS):

    SERVIDOR_ATALHOS=8001:/painel/,8002:/admin/

O servir.py passa a atender também nessas portas, e quem abre a raiz (/) delas vai direto para
a tela correspondente. A porta principal (SERVIDOR_PORTA, 8000) continua abrindo o chat.
Vazio (padrão) = desligado.
"""
from django.conf import settings
from django.http import HttpResponseRedirect


def ler_atalhos(texto: str) -> dict[int, str]:
    """'8001:/painel/,8002:/admin/' -> {8001: '/painel/', 8002: '/admin/'} (ignora itens inválidos)."""
    atalhos = {}
    for item in (texto or "").split(","):
        porta, _, caminho = item.strip().partition(":")
        if porta.strip().isdigit() and caminho.strip().startswith("/"):
            atalhos[int(porta)] = caminho.strip()
    return atalhos


class AtalhoPorPorta:
    def __init__(self, get_response):
        self.get_response = get_response
        self.atalhos = ler_atalhos(getattr(settings, "SERVIDOR_ATALHOS", ""))

    def __call__(self, request):
        if self.atalhos and request.path == "/":
            destino = self.atalhos.get(_porta(request))
            if destino:
                return HttpResponseRedirect(destino)
        return self.get_response(request)


def _porta(request) -> int | None:
    # Porta em que a conexão chegou ao servidor (o Waitress informa a de cada socket que ele escuta).
    porta = str(request.META.get("SERVER_PORT", ""))
    return int(porta) if porta.isdigit() else None
