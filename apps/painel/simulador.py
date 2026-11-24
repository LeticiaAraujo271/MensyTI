"""
Simulador do WhatsApp (painel > "Simulador do WhatsApp").

Mostra como o atendimento aparece para o colaborador no WhatsApp, sem Digisac e sem enviar nada
a ninguém. Cada mensagem digitada vira um webhook do Digisac (o mesmo formato de produção), passa
pelo mesmo motor e pelo canal WhatsApp, e as respostas são lidas do banco, exatamente o que seria
enviado ao celular.

Os atendimentos do simulador usam o identificador "simulador-..." e o canal WhatsApp: os chamados
aparecem na fila do painel (marcados como simulação) e podem ser atendidos, respondidos e
resolvidos normalmente. O botão "Apagar testes" remove tudo o que foi criado pelo simulador.
"""
import uuid

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.bot.models import Colaborador, Conversa, Mensagem
from apps.bot.orquestrador import ConversationOrchestrator
from apps.canais import WhatsAppChannel
from apps.canais.whatsapp import PREFIXO_SIMULADOR
from apps.chamados.models import Chamado
from apps.digisac.webhook import TIPO_TEXTO, interpretar

from .views import atendente

CHAVE_SESSAO = "simulador_whatsapp"
MAX_TEXTO = 2000


def _contato(request, novo=False) -> str:
    ident = request.session.get(CHAVE_SESSAO)
    if novo or not ident:
        ident = f"{PREFIXO_SIMULADOR}{request.user.pk}-{uuid.uuid4().hex[:8]}"
        request.session[CHAVE_SESSAO] = ident
    return ident


def _texto_whatsapp(m: Mensagem) -> str:
    """O texto exatamente como chega no celular (o analista vai com o nome na frente)."""
    if m.autor == Mensagem.Autor.ANALISTA and m.analista:
        nome = m.analista.get_full_name() or m.analista.get_username()
        return f"🙋 *{nome}* (TI): {m.texto}"
    return m.texto


@require_GET
@atendente
def tela(request):
    return render(request, "painel/simulador_whatsapp.html", {"contato": _contato(request)})


@require_GET
@atendente
def mensagens(request):
    ident = _contato(request)
    try:
        depois = int(request.GET.get("depois") or 0)
    except ValueError:
        depois = 0
    msgs = (Mensagem.objects.filter(conversa__canal=Conversa.Canal.WHATSAPP, conversa__identificador=ident,
                                    id__gt=depois)
            .select_related("analista").order_by("id"))
    chamado = (Chamado.objects.filter(conversa__identificador=ident, status__in=Chamado.ABERTOS)
               .order_by("-id").first())
    return JsonResponse({
        "mensagens": [{
            "id": m.id,
            "de_mim": m.autor == Mensagem.Autor.COLABORADOR,
            "texto": _texto_whatsapp(m),
            "hora": timezone.localtime(m.criada_em).strftime("%H:%M"),
        } for m in msgs],
        "chamado": {"protocolo": chamado.protocolo, "status": chamado.get_status_display()} if chamado else None,
    })


@require_POST
@atendente
def enviar(request):
    texto = (request.POST.get("texto") or "").strip()[:MAX_TEXTO]
    if not texto:
        return JsonResponse({"erro": "Digite uma mensagem."}, status=400)
    ident = _contato(request)
    # Mesmo formato do webhook do Digisac (evento message.created), lido pelo mesmo interpretador.
    payload = {"event": "message.created", "data": {
        "id": f"sim-{uuid.uuid4().hex}", "contactId": ident, "type": TIPO_TEXTO, "text": texto,
        "isFromMe": False, "isFromBot": False,
    }}
    orquestrador = ConversationOrchestrator(WhatsAppChannel())
    for msg in interpretar(payload):
        orquestrador.receber(msg.contato_id, msg.texto, id_externo=msg.id)
    return JsonResponse({"ok": True})


@require_POST
@atendente
def nova_conversa(request):
    """Começa como um contato novo (outro número): pede a identificação de novo."""
    _contato(request, novo=True)
    return JsonResponse({"ok": True})


@require_POST
@atendente
def apagar_testes(request):
    """Remove conversas, chamados e colaboradores criados pelo simulador."""
    with transaction.atomic():
        conversas = Conversa.objects.filter(canal=Conversa.Canal.WHATSAPP,
                                            identificador__startswith=PREFIXO_SIMULADOR)
        colaboradores = set(conversas.exclude(colaborador=None).values_list("colaborador", flat=True))
        qs_chamados = Chamado.objects.filter(conversa__in=conversas)
        chamados = qs_chamados.count()
        qs_chamados.delete()
        conversas.delete()
        # Só apaga o colaborador se ele não tiver atendimentos reais.
        Colaborador.objects.filter(pk__in=colaboradores, conversas__isnull=True).delete()
    _contato(request, novo=True)
    return JsonResponse({"ok": True, "chamados": chamados})
