"""
Página do aprovador (coordenador ou gerente da área): /aprovacao/<token>/

Não exige login: quem tem o link (segredo aleatório, enviado só ao aprovador) decide.
Cada link vale para um nível e uma única decisão.
"""
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.chamados import aprovacoes
from apps.chamados.models import Aprovacao


@never_cache
@require_http_methods(["GET", "POST"])
def pagina(request, token):
    aprovacao = get_object_or_404(Aprovacao.objects.select_related("chamado"), token=token)
    erro = ""
    if request.method == "POST":
        decisao = request.POST.get("decisao")
        comentario = request.POST.get("comentario", "")
        if decisao not in ("aprovar", "reprovar"):
            erro = "Escolha aprovar ou reprovar."
        else:
            try:
                aprovacoes.decidir_e_avisar(aprovacao, decisao == "aprovar", comentario)
                return redirect("portal:aprovacao", token=token)  # evita reenvio ao recarregar
            except aprovacoes.AprovacaoInvalida as e:
                erro = str(e)
        aprovacao.refresh_from_db()
    chamado = aprovacao.chamado
    return render(request, "portal/aprovacao.html", {
        "aprovacao": aprovacao,
        "chamado": chamado,
        "niveis": chamado.aprovacoes.all(),
        "da_vez": aprovacao.da_vez,
        "erro": erro,
        "comentario": request.POST.get("comentario", "") if erro else "",
        "nome_central": settings.CENTRAL["NOME"],
    })
