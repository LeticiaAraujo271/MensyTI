"""
Cria (ou atualiza) os perfis de acesso da equipe:
    python manage.py configurar_perfis

  Analista de TI      -> painel de chamados (ver, atender, responder, resolver)
  Administrador de TI -> tudo do analista + base de conhecimento, conversas e métricas no Admin

Depois, no Admin > Usuários, coloque cada pessoa no grupo certo e marque "Membro da equipe"
para quem for usar o Admin.
"""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

ANALISTA = [
    "chamados.atender_chamado", "chamados.view_chamado", "chamados.change_chamado",
    "chamados.view_eventochamado", "bot.view_conversa", "bot.view_mensagem", "bot.view_colaborador",
]
ADMINISTRADOR = ANALISTA + [
    "orientacoes.add_categoria", "orientacoes.change_categoria", "orientacoes.delete_categoria",
    "orientacoes.view_categoria", "orientacoes.add_orientacao", "orientacoes.change_orientacao",
    "orientacoes.delete_orientacao", "orientacoes.view_orientacao",
    "bot.change_conversa", "bot.change_colaborador", "bot.view_avaliacao", "bot.view_orientacaovista",
    "chamados.add_chamado", "chamados.delete_chamado",
]
PERFIS = {"Analista de TI": ANALISTA, "Administrador de TI": ADMINISTRADOR}


def _permissao(codigo: str) -> Permission:
    app, codename = codigo.split(".")
    return Permission.objects.get(content_type__app_label=app, codename=codename)


class Command(BaseCommand):
    help = "Cria os grupos 'Analista de TI' e 'Administrador de TI' com as permissões corretas."

    def handle(self, *args, **opts):
        for nome, codigos in PERFIS.items():
            grupo, _ = Group.objects.get_or_create(name=nome)
            grupo.permissions.set([_permissao(c) for c in codigos])
            self.stdout.write(self.style.SUCCESS(f"Perfil '{nome}': {len(codigos)} permissões."))
