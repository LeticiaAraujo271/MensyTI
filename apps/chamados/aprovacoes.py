"""
Aprovação em dois níveis das solicitações de acesso (criação de usuário, liberar acesso).

    1. Coordenador  ->  2. Gerente da área  ->  chamado entra na fila da TI (o SLA começa aqui)

- Cada aprovador recebe um link próprio (/aprovacao/<token>/), por e-mail se o e-mail estiver
  configurado; senão a TI copia o link no painel e envia pelo Teams/e-mail.
- O gerente só recebe o link depois que o coordenador aprovar.
- Uma reprovação encerra a solicitação (o colaborador é avisado com o motivo).
- A TI pode registrar no painel uma decisão recebida por outro meio (com comentário obrigatório).
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import Aprovacao, Chamado, EventoChamado
from .sla import somar_horas_uteis

log = logging.getLogger(__name__)

A = Aprovacao.Situacao
S = Chamado.Status


class AprovacaoInvalida(Exception):
    pass


def criar(chamado: Chamado, aprovadores: list[dict]) -> None:
    """Cria os níveis de aprovação (coordenador, gerente) e envia o link para o primeiro."""
    for a in aprovadores:
        Aprovacao.objects.create(chamado=chamado, nivel=a["nivel"], nome=a["nome"][:150], email=a["email"])
    nomes = " → ".join(f"{ap.get_nivel_display()}: {ap.nome} ({ap.email})" for ap in chamado.aprovacoes.all())
    _evento(chamado, f"Aguardando aprovação. {nomes}")
    primeira = proxima(chamado)
    if primeira:
        transaction.on_commit(lambda: notificar(primeira))


def proxima(chamado: Chamado) -> Aprovacao | None:
    """O nível que precisa decidir agora (None = nenhum)."""
    if chamado.status != S.AGUARDANDO_APROVACAO:
        return None
    for ap in chamado.aprovacoes.order_by("nivel"):
        if ap.situacao == A.PENDENTE:
            return ap
        if ap.situacao != A.APROVADA:
            return None
    return None


def link(aprovacao: Aprovacao, base: str | None = None) -> str:
    caminho = reverse("portal:aprovacao", args=[aprovacao.token])
    base = (base if base is not None else settings.CENTRAL.get("URL", "")).rstrip("/")
    return base + caminho


def notificar(aprovacao: Aprovacao) -> bool:
    """Envia o link ao aprovador por e-mail (se configurado). Falha de e-mail não trava nada."""
    chamado = aprovacao.chamado
    if not settings.APROVACAO_ENVIAR_EMAIL:
        _evento(chamado, f"E-mail não configurado: copie o link do {aprovacao.get_nivel_display().lower()} "
                         "no painel e envie a ele.")
        return False
    if not settings.CENTRAL.get("URL"):
        log.warning("CENTRAL_URL vazio: o link de aprovação do %s não foi enviado.", chamado.protocolo)
        _evento(chamado, "Link de aprovação não enviado: preencha CENTRAL_URL no .env (ou copie o link no painel).")
        return False
    assunto = f"[{settings.CENTRAL['NOME']}] Aprovação pendente: {chamado.protocolo} · {chamado.orientacao or chamado.categoria}"
    corpo = (
        f"Olá, {aprovacao.nome.split()[0]}!\n\n"
        f"{chamado.nome_colaborador} ({chamado.setor or 'setor não informado'}) pediu: "
        f"{chamado.orientacao or chamado.categoria}.\n"
        f"Descrição: {chamado.descricao or '-'}\n\n"
        f"Você é o aprovador ({aprovacao.get_nivel_display().lower()}). Para aprovar ou reprovar, abra:\n"
        f"{link(aprovacao)}\n\n"
        "A TI só executa o pedido depois das aprovações.\n"
    )
    try:
        send_mail(assunto, corpo, None, [aprovacao.email])
    except Exception:  # SMTP fora do ar, credencial errada...
        log.exception("Falha ao enviar o e-mail de aprovação do %s", chamado.protocolo)
        _evento(chamado, f"Falha ao enviar o e-mail para {aprovacao.email}. Copie o link no painel.")
        return False
    Aprovacao.objects.filter(pk=aprovacao.pk).update(enviada_em=timezone.now())
    _evento(chamado, f"Link de aprovação enviado por e-mail para {aprovacao.nome} ({aprovacao.email}).")
    return True


def decidir(aprovacao: Aprovacao, aprovado: bool, comentario: str = "", usuario=None) -> str:
    """
    Registra a decisão de um nível. Devolve a mensagem para o colaborador.
    `usuario` = analista registrando pelo painel uma decisão recebida por outro meio.
    """
    comentario = (comentario or "").strip()
    if not aprovado and not comentario:
        raise AprovacaoInvalida("Informe o motivo da reprovação.")
    if usuario is not None and not comentario:
        raise AprovacaoInvalida("Informe como a decisão foi recebida (ex.: e-mail de 25/11, Teams).")
    with transaction.atomic():
        chamado = Chamado.objects.select_for_update().get(pk=aprovacao.chamado_id)
        aprovacao = Aprovacao.objects.select_related("chamado").get(pk=aprovacao.pk)
        aprovacao.chamado = chamado
        if not aprovacao.da_vez:
            raise AprovacaoInvalida("Esta aprovação não está pendente (já foi decidida ou ainda não é a vez dela).")
        agora = timezone.now()
        aprovacao.situacao = A.APROVADA if aprovado else A.REPROVADA
        aprovacao.comentario = comentario[:1000]
        aprovacao.decidida_em = agora
        aprovacao.registrada_por = usuario
        aprovacao.save()
        quem = f"{aprovacao.get_nivel_display()} {aprovacao.nome}"
        via = f" (registrado por {usuario.get_full_name() or usuario.get_username()})" if usuario else ""
        _evento(chamado, f"{quem} {'aprovou' if aprovado else 'reprovou'}{via}"
                         + (f": {comentario}" if comentario else "."), usuario)

        if not aprovado:
            chamado.aprovacoes.filter(situacao=A.PENDENTE).update(situacao=A.CANCELADA)
            chamado.status = S.FECHADO
            chamado.resolvido_em = agora
            chamado.solucao = f"Solicitação reprovada por {quem}: {comentario}"
            chamado.save(update_fields=["status", "resolvido_em", "solucao", "atualizado_em"])
            return (f"❌ A sua solicitação *{chamado.protocolo}* foi *reprovada* por {quem}.\n"
                    f"*Motivo:* {comentario}\n\n"
                    "Se precisar, converse com o seu gestor e abra uma nova solicitação.")

        seguinte = proxima(chamado)
        if seguinte:
            transaction.on_commit(lambda: notificar(seguinte))
            return (f"✅ {quem} aprovou a sua solicitação *{chamado.protocolo}*.\n"
                    f"Agora falta a aprovação do {seguinte.get_nivel_display().lower()} *{seguinte.nome}*.")

        chamado.aprovado_em = agora
        chamado.status = S.EM_FILA
        chamado.prazo_sla = somar_horas_uteis(agora, chamado.sla_horas)
        chamado.save(update_fields=["aprovado_em", "status", "prazo_sla", "atualizado_em"])
        _evento(chamado, f"Aprovações concluídas: chamado na fila da TI. SLA de {chamado.sla_horas}h úteis "
                         "a partir de agora.")
        return (f"✅ A sua solicitação *{chamado.protocolo}* foi *aprovada* pelo coordenador e pelo gerente "
                "da área.\nEla entrou na fila da TI, que vai executar o pedido e te avisar por aqui.")


def decidir_e_avisar(aprovacao: Aprovacao, aprovado: bool, comentario: str = "", usuario=None) -> str:
    """decidir() + avisa o colaborador no canal da conversa (web ou WhatsApp)."""
    texto = decidir(aprovacao, aprovado, comentario, usuario)
    from apps.bot.orquestrador import ConversationOrchestrator
    from apps.canais import WebChannel

    chamado = Chamado.objects.get(pk=aprovacao.chamado_id)
    ConversationOrchestrator(WebChannel()).avisar_colaborador(chamado, texto)
    return texto


def _evento(chamado, descricao, autor=None):
    return EventoChamado.objects.create(chamado=chamado, tipo=EventoChamado.Tipo.APROVACAO,
                                        descricao=descricao, autor=autor)
