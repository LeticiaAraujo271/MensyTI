"""Calcula o SLA e o prazo dos chamados que já existiam antes do SLA."""
from django.conf import settings
from django.db import migrations


def preencher(apps, schema_editor):
    from apps.chamados.sla import somar_horas_uteis

    Chamado = apps.get_model("chamados", "Chamado")
    Categoria = apps.get_model("orientacoes", "Categoria")
    sla = dict(Categoria.objects.values_list("nome", "sla_horas"))
    padrao = settings.SLA_PADRAO_HORAS
    for ch in Chamado.objects.all().only("id", "categoria", "criado_em"):
        horas = sla.get(ch.categoria) or padrao
        Chamado.objects.filter(pk=ch.pk).update(sla_horas=horas,
                                                prazo_sla=somar_horas_uteis(ch.criado_em, horas))


class Migration(migrations.Migration):
    dependencies = [
        ("chamados", "0002_sla_e_pesquisa"),
        ("orientacoes", "0003_sla_das_categorias"),
    ]
    operations = [migrations.RunPython(preencher, migrations.RunPython.noop)]
