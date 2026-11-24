"""Variáveis de template da identidade visual (logo da marca d'água)."""
from functools import lru_cache

from django.contrib.staticfiles import finders

# Coloque o arquivo oficial do logo em apps/portal/static/marca/ com um destes nomes.
LOGOS = ("marca/logo.svg", "marca/logo.png", "marca/logo.webp")


@lru_cache(maxsize=1)
def _logo() -> str:
    return next((nome for nome in LOGOS if finders.find(nome)), "")


def marca(request):
    """`logo_marca`: caminho estático do logo, ou "" se ainda não foi colocado."""
    return {"logo_marca": _logo()}
