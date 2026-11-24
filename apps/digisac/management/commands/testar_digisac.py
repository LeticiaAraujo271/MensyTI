"""
Confere a configuração do WhatsApp (Digisac) antes de ligar o canal.

    python manage.py testar_digisac                         só confere o .env (não envia nada)
    python manage.py testar_digisac --enviar-para CONTATO   envia UMA mensagem de teste real

CONTATO é o ID do contato no Digisac (aparece na URL do contato ou no webhook, campo contactId).
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.digisac.client import ClienteDigisac, ErroDigisac


EXEMPLOS = ("suaempresa", "cole-aqui", "gere-um", "troque")


def _preenchido(valor) -> bool:
    """Preenchido de verdade (não vazio e não o texto de exemplo do .env.example)."""
    valor = str(valor or "").strip().lower()
    return bool(valor) and not any(e in valor for e in EXEMPLOS)


class Command(BaseCommand):
    help = "Confere a configuração do Digisac e, opcionalmente, envia uma mensagem de teste."

    def add_arguments(self, parser):
        parser.add_argument("--enviar-para", metavar="CONTATO",
                            help="ID do contato no Digisac que vai receber a mensagem de teste.")

    def handle(self, *args, enviar_para=None, **opts):
        cfg = settings.DIGISAC
        itens = [
            ("WHATSAPP_ATIVO", settings.WHATSAPP_ATIVO, "liga o canal (o webhook passa a responder)"),
            ("DIGISAC_URL", _preenchido(cfg["URL"]), "endereço da conta, ex.: https://suaempresa.digisac.app"),
            ("DIGISAC_TOKEN", _preenchido(cfg["TOKEN"]), "Digisac > Conta > API > Tokens de acesso pessoal"),
            ("DIGISAC_WEBHOOK_TOKEN", _preenchido(cfg["WEBHOOK_TOKEN"]), "segredo que vai na URL do webhook"),
            ("DIGISAC_SERVICE_ID", _preenchido(cfg["SERVICE_ID"]), "conexão de WhatsApp usada (opcional)"),
            ("DIGISAC_ENVIAR_MENSAGENS", cfg["ENVIAR_MENSAGENS"], "false = só registra no log"),
        ]
        faltando = False
        for nome, ok, ajuda in itens:
            opcional = nome in ("DIGISAC_SERVICE_ID", "DIGISAC_ENVIAR_MENSAGENS", "WHATSAPP_ATIVO")
            marca = "[ok]   " if ok else ("[--]   " if opcional else "[FALTA]")
            faltando |= not ok and not opcional
            self.stdout.write(f"{marca} {nome:<26} {ajuda}")
        if _preenchido(cfg["WEBHOOK_TOKEN"]):
            self.stdout.write("\nURL do webhook para cadastrar no Digisac (evento message.created):")
            self.stdout.write(f"   https://SEU_ENDERECO/webhooks/digisac/?token={cfg['WEBHOOK_TOKEN'][:4]}..."
                              " (use o token completo do .env)")
        if faltando:
            raise CommandError("Preencha os itens marcados com [FALTA] no .env e rode de novo.")
        if not enviar_para:
            self.stdout.write(self.style.SUCCESS("\nConfiguração completa. Para um teste real: "
                                                 "--enviar-para <ID do contato>"))
            return
        try:
            ClienteDigisac(enviar=True).enviar_texto(
                enviar_para, "✅ Teste da Central de TI: a integração com o WhatsApp está funcionando.")
        except ErroDigisac as e:
            raise CommandError(f"O Digisac recusou o envio: {e}") from e
        except Exception as e:  # rede, DNS, certificado...
            raise CommandError(f"Não foi possível falar com o Digisac: {e}") from e
        self.stdout.write(self.style.SUCCESS("Mensagem de teste enviada. Confira no WhatsApp do contato."))
