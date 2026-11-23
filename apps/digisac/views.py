import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.bot.orquestrador import ConversationOrchestrator
from apps.canais import WhatsAppChannel

from .webhook import TIPO_TEXTO, TIPO_TICKET, interpretar

log = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def receber_webhook(request):
    """
    Endpoint configurado no Digisac:
        https://SEU_DOMINIO/webhooks/digisac/?token=DIGISAC_WEBHOOK_TOKEN
    Evento: message.created (mensagem nova)

    Com WHATSAPP_ATIVO=false o webhook responde 200 e ignora as mensagens:
    o canal fica desligado sem afetar o portal web.
    """
    esperado = settings.DIGISAC["WEBHOOK_TOKEN"]
    recebido = request.GET.get("token", "")
    if not esperado or not hmac.compare_digest(recebido, esperado):
        return HttpResponseForbidden("token inválido")

    if not settings.WHATSAPP_ATIVO:
        return JsonResponse({"ok": True, "ignorado": "canal WhatsApp desativado"})

    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return HttpResponse("json inválido", status=400)

    orquestrador = ConversationOrchestrator(WhatsAppChannel())
    processadas = 0
    for msg in interpretar(payload):
        if not msg.eh_do_contato or msg.tipo == TIPO_TICKET:
            continue  # mensagens do atendente/bot ou de sistema do Digisac
        try:
            if msg.tipo in (TIPO_TEXTO, ""):
                orquestrador.receber(msg.contato_id, msg.texto, id_externo=msg.id)
            else:
                orquestrador.receber_midia(msg.contato_id, msg.tipo, id_externo=msg.id)
            processadas += 1
        except Exception:
            # Sempre responder 200 para o provedor não ficar reenviando; o erro fica no log.
            log.exception("Erro ao processar mensagem %s do contato %s", msg.id, msg.contato_id)

    return JsonResponse({"ok": True, "processadas": processadas})
