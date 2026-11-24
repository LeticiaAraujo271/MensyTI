"""
Painel da equipe de TI. Exige login e a permissão 'chamados.atender_chamado'
(grupo 'Analista de TI' ou 'Administrador de TI'; veja `manage.py configurar_perfis`).
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.bot.orquestrador import ConversationOrchestrator
from apps.canais import WebChannel
from apps.chamados import sla
from apps.chamados.models import Chamado
from apps.orientacoes.models import Categoria
from apps.chamados.servicos import TicketService, TransicaoInvalida

PERMISSAO = "chamados.atender_chamado"
S = Chamado.Status


def atendente(view):
    @login_required
    @wraps(view)
    def interno(request, *args, **kwargs):
        if not request.user.has_perm(PERMISSAO):
            raise PermissionDenied("Seu usuário não tem acesso ao painel de TI.")
        return view(request, *args, **kwargs)
    return interno


def _orquestrador():
    # O canal de entrega é escolhido pela conversa de cada chamado (web ou WhatsApp).
    return ConversationOrchestrator(WebChannel())


def _filtrar(request, limite=300):
    """Chamados conforme os filtros da fila (status, prioridade, SLA, busca, só os meus)."""
    status = request.GET.get("status", "abertos")
    qs = Chamado.objects.select_related("responsavel", "conversa")
    if status == "abertos":
        qs = qs.filter(status__in=Chamado.ABERTOS)
    elif status in S.values:
        qs = qs.filter(status=status)
    if request.GET.get("prioridade", "").isdigit():
        qs = qs.filter(prioridade=int(request.GET["prioridade"]))
    if request.GET.get("meus"):
        qs = qs.filter(responsavel=request.user)
    busca = request.GET.get("q", "").strip()
    if busca:
        qs = qs.filter(Q(protocolo__icontains=busca) | Q(nome_colaborador__icontains=busca)
                       | Q(contato__icontains=busca) | Q(descricao__icontains=busca)
                       | Q(centro_custo__icontains=busca))
    qs = qs.prefetch_related("pesquisas").order_by("prioridade", "criado_em")
    chamados = list(qs[:limite] if limite else qs)
    cor_sla = request.GET.get("sla", "")
    if cor_sla in (sla.VERDE, sla.AMARELO, sla.VERMELHO):
        chamados = [c for c in chamados if c.sla.cor == cor_sla]
    return chamados, status, cor_sla, busca


@require_GET
@atendente
def exportar(request):
    """Planilha Excel com os chamados do filtro atual da fila (sem o limite de 300 da tela)."""
    from .exportacao import planilha_chamados

    chamados, *_ = _filtrar(request, limite=None)
    conteudo = planilha_chamados(chamados)
    nome = f"chamados_{timezone.localtime():%Y-%m-%d_%H%M}.xlsx"
    resposta = HttpResponse(conteudo, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resposta["Content-Disposition"] = f'attachment; filename="{nome}"'
    return resposta


@require_GET
@atendente
def fila(request):
    chamados, status, cor_sla, busca = _filtrar(request)
    contagem = dict(Chamado.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    em_aberto = Chamado.objects.filter(status__in=Chamado.ABERTOS).only(
        "status", "sla_horas", "prazo_sla", "criado_em", "resolvido_em")
    sla_vencidos = sum(1 for c in em_aberto if c.sla.cor == sla.VERMELHO)
    return render(request, "painel/fila.html", {
        "chamados": chamados,
        "sla": cor_sla,
        "sla_vencidos": sla_vencidos,
        "opcoes_sla": [(sla.VERDE, "🟢 No prazo"), (sla.AMARELO, "🟡 Metade do SLA consumida"),
                       (sla.VERMELHO, "🔴 SLA vencido")],
        "status": status,
        "prioridade": request.GET.get("prioridade", ""),
        "meus": bool(request.GET.get("meus")),
        "busca": busca,
        "opcoes_status": [("abertos", "Abertos", sum(contagem.get(s, 0) for s in Chamado.ABERTOS))]
                         + [(s.value, s.label, contagem.get(s.value, 0)) for s in S]
                         + [("todos", "Todos", sum(contagem.values()))],
        "opcoes_prioridade": Chamado.Prioridade.choices,
        "criticos": Chamado.objects.filter(status__in=Chamado.ABERTOS,
                                           prioridade=Chamado.Prioridade.CRITICA).count(),
    })


@require_GET
@atendente
def detalhe(request, protocolo):
    chamado = get_object_or_404(Chamado.objects.select_related("responsavel", "conversa", "colaborador"),
                                protocolo=protocolo)
    conversa = chamado.conversa
    mensagens = conversa.mensagens.select_related("analista") if conversa else []
    return render(request, "painel/detalhe.html", {
        "chamado": chamado,
        "mensagens": mensagens,
        "ultimo_id": mensagens.last().id if conversa and mensagens.exists() else 0,
        "eventos": chamado.eventos.select_related("autor"),
        "pode_responder": chamado.aberto and conversa is not None,
        "pesquisas": chamado.pesquisas.all(),
        "categorias": Categoria.objects.filter(ativa=True).values_list("nome", "sla_horas"),
        "S": S,
    })


@require_POST
@atendente
def acao(request, protocolo):
    chamado = get_object_or_404(Chamado, protocolo=protocolo)
    acao = request.POST.get("acao", "")
    tickets = TicketService()
    try:
        if acao == "assumir":
            tickets.atribuir(chamado, request.user)
            messages.success(request, "Chamado assumido.")
        elif acao == "responder":
            if not chamado.aberto:
                raise TransicaoInvalida("Reabra o chamado para responder.")
            _orquestrador().responder_como_analista(chamado, request.user, request.POST.get("texto", ""))
            if request.POST.get("aguardar"):
                tickets.mudar_status(chamado, S.AGUARDANDO_USUARIO, request.user)
            messages.success(request, "Resposta enviada ao colaborador.")
        elif acao == "status":
            tickets.mudar_status(chamado, request.POST.get("status", ""), request.user,
                                 nota=request.POST.get("nota", "").strip())
            messages.success(request, f"Status: {chamado.get_status_display()}.")
        elif acao == "resolver":
            _orquestrador().resolver_chamado(chamado, request.user, request.POST.get("solucao", ""))
            messages.success(request, "Chamado resolvido e colaborador avisado.")
        elif acao == "reclassificar":
            tickets.reclassificar(chamado, request.POST.get("categoria", ""), request.user)
            messages.success(request, f"Categoria: {chamado.categoria or 'sem categoria'} · "
                                      f"SLA {chamado.sla_horas}h úteis.")
        elif acao == "fechar":
            tickets.mudar_status(chamado, S.FECHADO, request.user)
            messages.success(request, "Chamado fechado.")
        elif acao == "reabrir":
            tickets.mudar_status(chamado, S.EM_FILA, request.user,
                                 nota=request.POST.get("nota", "").strip() or "Reaberto pela TI.")
            messages.success(request, "Chamado reaberto.")
        else:
            messages.error(request, "Ação desconhecida.")
    except (TransicaoInvalida, ValueError) as e:
        messages.error(request, str(e))
    return redirect("painel:detalhe", protocolo=protocolo)


@require_GET
@atendente
def mensagens(request, protocolo):
    chamado = get_object_or_404(Chamado, protocolo=protocolo)
    if chamado.conversa_id is None:
        return JsonResponse({"mensagens": [], "status": chamado.get_status_display()})
    try:
        depois = int(request.GET.get("depois") or 0)
    except ValueError:
        depois = 0
    msgs = chamado.conversa.mensagens.filter(id__gt=depois).select_related("analista")
    return JsonResponse({
        "status": chamado.get_status_display(),
        "mensagens": [{
            "id": m.id, "autor": m.autor, "autor_nome": m.get_autor_display(),
            "analista": (m.analista.get_full_name() or m.analista.get_username()) if m.analista else "",
            "texto": m.texto, "hora": timezone.localtime(m.criada_em).strftime("%d/%m %H:%M"),
        } for m in msgs],
    })
