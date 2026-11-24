from django.db import migrations
from django.db.models import F

NOME = "Requisição de material"


def criar(apps, schema_editor):
    """Inclui a categoria em bancos que já têm a base carregada (bancos novos recebem pelo popular_orientacoes)."""
    from apps.orientacoes.conteudo_inicial import CATALOGO_INICIAL

    Categoria = apps.get_model("orientacoes", "Categoria")
    Orientacao = apps.get_model("orientacoes", "Orientacao")
    if not Categoria.objects.exists() or Categoria.objects.filter(nome=NOME).exists():
        return
    dados = next((c for c in CATALOGO_INICIAL if c["nome"] == NOME), None)
    if dados is None:
        return
    outros = Categoria.objects.filter(nome="Outros assuntos").first()
    if outros:  # entra logo antes de "Outros assuntos", que continua por último
        ordem = outros.ordem
        Categoria.objects.filter(ordem__gte=ordem).update(ordem=F("ordem") + 1)
    else:
        ordem = (Categoria.objects.order_by("-ordem").values_list("ordem", flat=True).first() or 0) + 1
    cat = Categoria.objects.create(nome=NOME, emoji=dados["emoji"], ordem=ordem, sla_horas=dados["sla_horas"])
    for j, ori in enumerate(dados["orientacoes"], start=1):
        Orientacao.objects.create(
            categoria=cat, titulo=ori["titulo"], passos="\n".join(ori["passos"]),
            observacao=ori.get("observacao", ""), palavras_chave=", ".join(ori.get("palavras_chave", [])),
            prioridade=ori.get("prioridade", "media"), abre_chamado=ori.get("abre_chamado", False),
            exige_aprovacao=ori.get("exige_aprovacao", False), ordem=j,
        )


def remover(apps, schema_editor):
    apps.get_model("orientacoes", "Categoria").objects.filter(nome=NOME).delete()


class Migration(migrations.Migration):
    dependencies = [("orientacoes", "0004_orientacao_exige_aprovacao")]

    operations = [migrations.RunPython(criar, remover)]
