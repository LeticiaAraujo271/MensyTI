"""Preenche o SLA (horas úteis) das categorias que já existem, pela tabela de SLA da TI."""
from django.db import migrations

SLA_POR_CATEGORIA = {
    "Acesso e login": 8,
    "Segurança e incidentes": 8,
    "Internet, rede e VPN": 8,
    "E-mail e Microsoft 365": 16,
    "Sistemas internos": 16,
    "Computador lento ou travando": 24,
    "Impressora": 24,
    "Solicitação de acesso": 40,
    "Outros assuntos": 72,
}


def preencher(apps, schema_editor):
    Categoria = apps.get_model("orientacoes", "Categoria")
    for nome, horas in SLA_POR_CATEGORIA.items():
        Categoria.objects.filter(nome=nome).update(sla_horas=horas)


class Migration(migrations.Migration):
    dependencies = [("orientacoes", "0002_categoria_sla_horas")]
    operations = [migrations.RunPython(preencher, migrations.RunPython.noop)]
