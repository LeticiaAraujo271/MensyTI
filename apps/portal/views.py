"""
Portal web (canal principal). Cada navegador recebe um identificador aleatório guardado
na sessão (cookie HttpOnly). As APIs só leem e gravam mensagens desse identificador:
um colaborador nunca vê a conversa de outro.
"""
import json
import re
import time
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from apps.bot.models import Conversa, Mensagem
from apps.bot.orquestrador import ConversationOrchestrator
from apps.canais import WebChannel
from apps.chamados.models import Chamado

CHAVE_SESSAO = "central_web_id"
CHAVE_ENVIOS = "central_envios"
_RE_ID_CLIENTE = re.compile(r"^[A-Za-z0-9-]{8,64}$")
MAX_TEXTO = 2000


def _identificador(request) -> str:
    ident = request.session.get(CHAVE_SESSAO)
    if not ident:
        ident = uuid.uuid4().hex
        request.session[CHAVE_SESSAO] = ident
    return ident


def _mensagens(ident: str):
    return Mensagem.objects.filter(conversa__canal=Conversa.Canal.WEB, conversa__identificador=ident)


def _serializar(m: Mensagem) -> dict:
    return {
        "id": m.id,
        "autor": m.autor,
        "texto": m.texto,
        "hora": timezone.localtime(m.criada_em).strftime("%H:%M"),
        "analista": (m.analista.get_full_name() or m.analista.get_username()) if m.analista else "",
    }


def _estado(ident: str) -> dict:
    chamado = (Chamado.objects.filter(conversa__canal=Conversa.Canal.WEB, conversa__identificador=ident,
                                      status__in=Chamado.ABERTOS)
               .order_by("-criado_em").first())
    return {
        "chamado": {
            "protocolo": chamado.protocolo,
            "status": chamado.get_status_display(),
            "prioridade": chamado.get_prioridade_display(),
        } if chamado else None,
    }


def _resposta(ident: str, depois: int) -> JsonResponse:
    msgs = _mensagens(ident).filter(id__gt=depois).select_related("analista").order_by("id")[:200]
    return JsonResponse({"mensagens": [_serializar(m) for m in msgs], "estado": _estado(ident)})


@ensure_csrf_cookie
@require_GET
def chat(request):
    _identificador(request)
    return render(request, "portal/chat.html", {"nome_central": settings.CENTRAL["NOME"]})


@require_GET
def api_mensagens(request):
    ident = _identificador(request)
    try:
        depois = max(int(request.GET.get("depois") or 0), 0)
    except ValueError:
        depois = 0
    if depois == 0 and not _mensagens(ident).exists():
        ConversationOrchestrator(WebChannel()).iniciar(ident)
    return _resposta(ident, depois)


@require_POST
def api_enviar(request):
    ident = _identificador(request)
    try:
        corpo = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"erro": "Requisição inválida."}, status=400)
    texto = str(corpo.get("texto") or "").strip()
    id_cliente = str(corpo.get("id") or "")
    if not texto:
        return JsonResponse({"erro": "Digite uma mensagem."}, status=400)
    if len(texto) > MAX_TEXTO:
        return JsonResponse({"erro": f"Mensagem muito longa (máximo {MAX_TEXTO} caracteres)."}, status=400)
    if id_cliente and not _RE_ID_CLIENTE.match(id_cliente):
        id_cliente = ""

    agora = time.time()
    envios = [t for t in request.session.get(CHAVE_ENVIOS, []) if agora - t < 60]
    if len(envios) >= settings.CENTRAL["LIMITE_MENSAGENS_MINUTO"]:
        return JsonResponse({"erro": "Muitas mensagens em pouco tempo. Aguarde um instante."}, status=429)
    request.session[CHAVE_ENVIOS] = envios + [agora]

    ConversationOrchestrator(WebChannel()).receber(ident, texto, id_externo=id_cliente)
    try:
        depois = max(int(corpo.get("depois") or 0), 0)
    except (TypeError, ValueError):
        depois = 0
    return _resposta(ident, depois)
