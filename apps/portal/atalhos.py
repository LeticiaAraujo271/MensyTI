"""
Uma porta por tela (usado no GitHub Codespaces, que mostra uma linha por porta na aba PORTS):

    SERVIDOR_ATALHOS=8001:/painel/,8002:/admin/

O servir.py atende também nessas portas, mas elas só REDIRECIONAM para a tela na porta principal
(SERVIDOR_PORTA, 8000). Assim o login e os cookies de segurança ficam sempre num único endereço:
para o navegador, cada porta é um site diferente (ou, em localhost, as portas dividem os mesmos
cookies), e usar o painel numa porta e o admin em outra fazia o login cair em "CSRF falhou".
Vazio (padrão) = desligado.
"""
import os

from django.conf import settings
from django.http import HttpResponseRedirect
from django.http.request import split_domain_port


def ler_atalhos(texto: str) -> dict[int, str]:
    """'8001:/painel/,8002:/admin/' -> {8001: '/painel/', 8002: '/admin/'} (ignora itens inválidos)."""
    atalhos = {}
    for item in (texto or "").split(","):
        porta, _, caminho = item.strip().partition(":")
        if porta.strip().isdigit() and caminho.strip().startswith("/"):
            atalhos[int(porta)] = caminho.strip()
    return atalhos


def endereco_principal(request, porta_principal: int) -> str:
    """Endereço da porta principal, visto pelo navegador de quem pediu."""
    nome, dominio = os.environ.get("CODESPACE_NAME"), os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")
    if nome and dominio:  # Codespaces: https://<codespace>-8000.app.github.dev
        return f"https://{nome}-{porta_principal}.{dominio}"
    host, _porta_atual = split_domain_port(request.get_host())
    return f"{request.scheme}://{host}:{porta_principal}"


class AtalhoPorPorta:
    def __init__(self, get_response):
        self.get_response = get_response
        self.atalhos = ler_atalhos(getattr(settings, "SERVIDOR_ATALHOS", ""))
        self.principal = int(getattr(settings, "SERVIDOR_PORTA", 8000))

    def __call__(self, request):
        if self.atalhos:
            porta = _porta(request)
            if porta in self.atalhos and porta != self.principal:
                destino = self.atalhos[porta] if request.path == "/" else request.get_full_path()
                return HttpResponseRedirect(endereco_principal(request, self.principal) + destino)
        return self.get_response(request)


def _porta(request) -> int | None:
    # Porta em que a conexão chegou ao servidor (o Waitress informa a de cada socket que ele escuta).
    porta = str(request.META.get("SERVER_PORT", ""))
    return int(porta) if porta.isdigit() else None
