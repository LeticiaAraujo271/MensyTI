"""
Confere o e-mail usado nos links de aprovação.

    python manage.py testar_email                    só confere o .env (não envia nada)
    python manage.py testar_email --para nome@empresa.com.br   envia UM e-mail de teste
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Confere a configuração de e-mail (links de aprovação) e, opcionalmente, envia um teste."

    def add_arguments(self, parser):
        parser.add_argument("--para", metavar="EMAIL", help="Endereço que recebe o e-mail de teste.")

    def handle(self, *args, para=None, **opts):
        itens = [
            ("EMAIL_HOST", bool(settings.EMAIL_HOST), "servidor SMTP, ex.: smtp.office365.com"),
            ("EMAIL_HOST_USER", bool(settings.EMAIL_HOST_USER), "conta que envia"),
            ("EMAIL_HOST_PASSWORD", bool(settings.EMAIL_HOST_PASSWORD), "senha da conta (ou senha de app)"),
            ("CENTRAL_URL", bool(settings.CENTRAL.get("URL")), "endereço que vai no link, ex.: http://nb332:8000"),
            ("APROVACAO_ENVIAR_EMAIL", settings.APROVACAO_ENVIAR_EMAIL, "liga com EMAIL_HOST preenchido"),
        ]
        faltando = False
        for nome, ok, ajuda in itens:
            self.stdout.write(f"{'[ok]   ' if ok else '[FALTA]'} {nome:<24} {ajuda}")
            faltando |= not ok
        self.stdout.write(f"        porta {settings.EMAIL_PORT} · TLS {'sim' if settings.EMAIL_USE_TLS else 'não'}"
                          f" · remetente {settings.DEFAULT_FROM_EMAIL}")
        if faltando:
            raise CommandError("Preencha os itens marcados com [FALTA] no .env e rode de novo.")
        if not para:
            self.stdout.write(self.style.SUCCESS("\nConfiguração completa. Para um teste real: --para <e-mail>"))
            return
        try:
            send_mail(f"[{settings.CENTRAL['NOME']}] Teste de e-mail",
                      "Este é um teste da Central de TI: os links de aprovação vão chegar por este e-mail.",
                      None, [para])
        except Exception as e:  # autenticação, TLS, porta bloqueada...
            raise CommandError(f"Não foi possível enviar: {e}") from e
        self.stdout.write(self.style.SUCCESS(f"E-mail de teste enviado para {para}. Confira a caixa de entrada."))
