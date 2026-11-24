from django.core.management.base import BaseCommand
from django.db import transaction

from apps.orientacoes.conteudo_inicial import CATALOGO_INICIAL
from apps.orientacoes.models import Categoria, Orientacao


class Command(BaseCommand):
    help = "Carrega as categorias e orientações iniciais de TI (não duplica nem altera as existentes)."

    def add_arguments(self, parser):
        parser.add_argument("--recriar", action="store_true", help="Apaga tudo e carrega de novo.")

    @transaction.atomic
    def handle(self, *args, recriar=False, **opts):
        if recriar:
            Categoria.objects.all().delete()
        criadas = 0
        for i, cat in enumerate(CATALOGO_INICIAL, start=1):
            categoria, _ = Categoria.objects.get_or_create(
                nome=cat["nome"], defaults={"emoji": cat.get("emoji", ""), "ordem": i, "sla_horas": cat.get("sla_horas", 72)}
            )
            for j, ori in enumerate(cat["orientacoes"], start=1):
                _, nova = Orientacao.objects.get_or_create(
                    categoria=categoria,
                    titulo=ori["titulo"],
                    defaults={
                        "passos": "\n".join(ori["passos"]),
                        "observacao": ori.get("observacao", ""),
                        "palavras_chave": ", ".join(ori.get("palavras_chave", [])),
                        "prioridade": ori.get("prioridade", "media"),
                        "abre_chamado": ori.get("abre_chamado", False),
                        "ordem": j,
                    },
                )
                criadas += int(nova)
        if opts.get("verbosity", 1):
            self.stdout.write(self.style.SUCCESS(f"{criadas} orientação(ões) criada(s)."))
