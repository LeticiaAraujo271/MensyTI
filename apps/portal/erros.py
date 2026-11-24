"""
Página da falha de CSRF (proteção contra formulário forjado) em português e com o motivo.

O Django só mostra o motivo com DEBUG=True. O motivo não é segredo (ex.: "CSRF cookie not set")
e ajuda a resolver na hora, por isso aparece aqui e também no log (logs/servidor.log).
"""
import logging

from django.http import HttpResponseForbidden
from django.utils.html import escape

log = logging.getLogger("apps.portal.csrf")

DICAS = {
    "cookie": "O navegador não enviou o cookie de segurança. Recarregue a página (F5) e tente de novo. "
              "Se usar aba anônima ou bloqueio de cookies, libere os cookies deste endereço.",
    "origin": "O endereço de onde o formulário foi enviado não está liberado. No .env, inclua-o em "
              "DJANGO_CSRF_TRUSTED_ORIGINS (ex.: https://*.app.github.dev no Codespaces) e reinicie a Central.",
    "referer": "O navegador não informou de qual página veio o envio. Recarregue a página e tente de novo.",
    "token": "A página estava aberta havia muito tempo ou foi aberta antes de um login. Recarregue (F5) e tente de novo.",
}


def _dica(motivo: str) -> str:
    m = motivo.lower()
    if "cookie" in m:
        return DICAS["cookie"]
    if "origin" in m:
        return DICAS["origin"]
    if "referer" in m:
        return DICAS["referer"]
    return DICAS["token"]


def falha_csrf(request, reason=""):
    log.warning("CSRF recusado: %s | host=%s | origin=%s | caminho=%s", reason, request.META.get("HTTP_HOST", ""),
                request.META.get("HTTP_ORIGIN", ""), request.path)
    html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Envio recusado (403)</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px;color:#111}}
h1{{color:#003C38}}code{{background:#F3F5F5;padding:2px 6px;border-radius:4px}}a{{color:#00564F}}</style></head>
<body><h1>Envio recusado (403)</h1>
<p>A proteção do formulário (CSRF) não confirmou este envio, então nada foi gravado.</p>
<p><b>O que fazer:</b> {escape(_dica(reason))}</p>
<p><small>Motivo técnico: <code>{escape(reason)}</code></small></p>
<p><a href="{escape(request.path)}">Voltar e tentar de novo</a></p></body></html>"""
    return HttpResponseForbidden(html)
