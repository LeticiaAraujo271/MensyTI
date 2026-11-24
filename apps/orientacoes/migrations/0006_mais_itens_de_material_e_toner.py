"""
Inclui os itens novos da Requisição de material e o "Toner ou cartucho acabando" (Impressora)
em bancos que já têm a base carregada. Não altera orientações que a TI já editou, só a ordem.
"""
from django.db import migrations

ANTIGO_OUTRO = "Outro material (headset, webcam, carregador...)"


def _criar(Orientacao, categoria, ori, ordem):
    Orientacao.objects.create(
        categoria=categoria, titulo=ori["titulo"], passos="\n".join(ori["passos"]),
        observacao=ori.get("observacao", ""), palavras_chave=", ".join(ori.get("palavras_chave", [])),
        prioridade=ori.get("prioridade", "media"), abre_chamado=ori.get("abre_chamado", False),
        exige_aprovacao=ori.get("exige_aprovacao", False), ordem=ordem,
    )


def sincronizar(apps, schema_editor):
    from apps.orientacoes.conteudo_inicial import CATALOGO_INICIAL

    Categoria = apps.get_model("orientacoes", "Categoria")
    Orientacao = apps.get_model("orientacoes", "Orientacao")
    dados = {c["nome"]: c for c in CATALOGO_INICIAL}

    material = Categoria.objects.filter(nome="Requisição de material").first()
    if material and "Requisição de material" in dados:
        novo_outro = next(o for o in dados["Requisição de material"]["orientacoes"] if o["titulo"] == "Outro material")
        for o in Orientacao.objects.filter(categoria=material, titulo=ANTIGO_OUTRO):
            o.titulo = novo_outro["titulo"]
            o.palavras_chave = ", ".join(novo_outro["palavras_chave"])
            o.save(update_fields=["titulo", "palavras_chave"])
        for j, ori in enumerate(dados["Requisição de material"]["orientacoes"], start=1):
            existente = Orientacao.objects.filter(categoria=material, titulo=ori["titulo"]).first()
            if existente:
                Orientacao.objects.filter(pk=existente.pk).update(ordem=j)
            else:
                _criar(Orientacao, material, ori, j)

    impressora = Categoria.objects.filter(nome="Impressora").first()
    if impressora and "Impressora" in dados:
        toner = next((o for o in dados["Impressora"]["orientacoes"] if o["titulo"] == "Toner ou cartucho acabando"), None)
        if toner and not Orientacao.objects.filter(categoria=impressora, titulo=toner["titulo"]).exists():
            ultima = Orientacao.objects.filter(categoria=impressora).order_by("-ordem").values_list("ordem", flat=True).first()
            _criar(Orientacao, impressora, toner, (ultima or 0) + 1)


class Migration(migrations.Migration):
    dependencies = [("orientacoes", "0005_requisicao_de_material")]

    operations = [migrations.RunPython(sincronizar, migrations.RunPython.noop)]
