"""Variáveis de template da identidade visual (logo da marca d'água)."""
from functools import lru_cache

from django.contrib.staticfiles import finders

# Coloque o arquivo oficial do logo em apps/portal/static/marca/ com um destes nomes.
LOGOS = ("marca/logo.svg", "marca/logo.png", "marca/logo.webp")


@lru_cache(maxsize=1)
def _logo() -> str:
    return next((nome for nome in LOGOS if finders.find(nome)), "")


def marca(request):
    """`logo_marca`: caminho estático do logo ("" se ainda não foi colocado) e o nome do cookie CSRF
    (configurável; o JavaScript lê por ele para mandar o X-CSRFToken)."""
    from django.conf import settings

    return {"logo_marca": _logo(), "csrf_cookie_nome": settings.CSRF_COOKIE_NAME}
