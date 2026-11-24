"""Carrega os feriados nacionais de 2025 a 2030 e recalcula o prazo de SLA dos chamados abertos."""
from django.db import migrations

ABERTOS = ("aberto", "em_fila", "em_atendimento", "aguardando_usuario")


def carregar(apps, schema_editor):
    from apps.chamados.feriados_nacionais import feriados_do_ano
    from apps.chamados.sla import somar_horas_uteis

    Feriado = apps.get_model("chamados", "Feriado")
    for ano in range(2025, 2031):
        for dia, nome in feriados_do_ano(ano):
            Feriado.objects.get_or_create(data=dia, defaults={"nome": nome})

    datas = set(Feriado.objects.values_list("data", flat=True))
    Chamado = apps.get_model("chamados", "Chamado")
    for ch in Chamado.objects.filter(status__in=ABERTOS).only("id", "criado_em", "sla_horas"):
        Chamado.objects.filter(pk=ch.pk).update(
            prazo_sla=somar_horas_uteis(ch.criado_em, ch.sla_horas, dias_sem_expediente=datas))


class Migration(migrations.Migration):
    dependencies = [("chamados", "0004_feriado")]
    operations = [migrations.RunPython(carregar, migrations.RunPython.noop)]
