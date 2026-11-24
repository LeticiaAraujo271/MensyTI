from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.chamados.feriados_nacionais import feriados_do_ano
from apps.chamados.models import Feriado


class Command(BaseCommand):
    help = ("Cadastra os feriados nacionais (não descontados do SLA). Sem --ano, carrega o ano atual e "
            "os 4 seguintes. Não altera nem apaga os feriados já cadastrados.")

    def add_arguments(self, parser):
        parser.add_argument("--ano", type=int, action="append", help="Ano (pode repetir: --ano 2031 --ano 2032).")

    def handle(self, *args, ano=None, **opts):
        atual = timezone.localdate().year
        anos = ano or range(atual, atual + 5)
        novos = 0
        for a in anos:
            for dia, nome in feriados_do_ano(a):
                _, criado = Feriado.objects.get_or_create(data=dia, defaults={"nome": nome})
                novos += int(criado)
        self.stdout.write(self.style.SUCCESS(f"{novos} feriado(s) cadastrado(s)."))
