from django.db import migrations, models

# Orientações que passam a exigir aprovação do coordenador e do gerente da área.
COM_APROVACAO = {
    "Acesso a sistema, pasta de rede ou grupo de e-mail": (
        "Informe o nome do seu gestor, que precisa aprovar o acesso.",
        "O seu coordenador e o gerente da área precisam aprovar o acesso (o assistente pede os dois).",
    ),
    "Acesso para colaborador novo": (
        "A solicitação deve ser feita pelo gestor ou pelo RH.",
        "A criação do usuário precisa da aprovação do coordenador e do gerente da área (o assistente pede os dois).",
    ),
}


def marcar(apps, schema_editor):
    Orientacao = apps.get_model("orientacoes", "Orientacao")
    for titulo, (antigo, novo) in COM_APROVACAO.items():
        for o in Orientacao.objects.filter(titulo=titulo):
            o.exige_aprovacao = True
            # Só troca o passo se ele ainda for o texto original (não sobrescreve edição da TI).
            o.passos = "\n".join(novo if p.strip() == antigo else p for p in o.passos.splitlines())
            o.save(update_fields=["exige_aprovacao", "passos"])


class Migration(migrations.Migration):
    dependencies = [("orientacoes", "0003_sla_das_categorias")]

    operations = [
        migrations.AddField(
            model_name="orientacao",
            name="exige_aprovacao",
            field=models.BooleanField(
                default=False, verbose_name="exige aprovação",
                help_text="O assistente pede o coordenador e o gerente da área do colaborador. O chamado só entra "
                          "na fila da TI depois que os dois aprovarem (nessa ordem). Ex.: criação de usuário, "
                          "liberar acesso.",
            ),
        ),
        migrations.RunPython(marcar, migrations.RunPython.noop),
    ]
