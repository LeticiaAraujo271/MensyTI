"""Formatação do WhatsApp (*negrito*, _itálico_, ~riscado~) nas mensagens mostradas no painel."""
import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

_NEGRITO = re.compile(r"\*([^*\n]+)\*")
_ITALICO = re.compile(r"(^|[\s(])_([^_\n]+)_(?=[\s).,!?:;]|$)")
_RISCADO = re.compile(r"~([^~\n]+)~")


@register.filter
def whatsapp(texto):
    """Escapa o HTML primeiro (o texto vem do colaborador) e só depois aplica a formatação."""
    t = escape(texto or "")
    t = _NEGRITO.sub(r"<strong>\1</strong>", t)
    t = _ITALICO.sub(r"\1<em>\2</em>", t)
    t = _RISCADO.sub(r"<s>\1</s>", t)
    return mark_safe(t.replace("\n", "<br>"))
