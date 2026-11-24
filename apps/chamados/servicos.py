"""
TicketService: abertura e ciclo de vida dos chamados.

Ciclo: aberto -> [aguardando_aprovacao: coordenador -> gerente] -> em_fila -> em_atendimento <-> aguardando_usuario -> resolvido -> fechado
       (resolvido/fechado podem ser reabertos por quem tem permissão: volta para em_fila)
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from .models import Chamado, EventoChamado, PesquisaSatisfacao
from .sla import sla_da_categoria, somar_horas_uteis

log = logging.getLogger(__name__)

PRIORIDADE_POR_NOME = {
    "critica": Chamado.Prioridade.CRITICA,
    "alta": Chamado.Prioridade.ALTA,
    "media": Chamado.Prioridade.MEDIA,
    "baixa": Chamado.Prioridade.BAIXA,
}

S = Chamado.Status
TRANSICOES = {
    S.ABERTO: {S.EM_FILA, S.EM_ATENDIMENTO},
    # Sai daqui só pelas aprovações (apps/chamados/aprovacoes.py): aprovado -> em_fila, reprovado -> fechado.
    S.AGUARDANDO_APROVACAO: set(),
    S.EM_FILA: {S.EM_ATENDIMENTO, S.AGUARDANDO_USUARIO, S.RESOLVIDO},
    S.EM_ATENDIMENTO: {S.EM_FILA, S.AGUARDANDO_USUARIO, S.RESOLVIDO},
    S.AGUARDANDO_USUARIO: {S.EM_ATENDIMENTO, S.RESOLVIDO},
    S.RESOLVIDO: {S.FECHADO, S.EM_FILA},
    S.FECHADO: {S.EM_FILA},
}


class TransicaoInvalida(Exception):
    pass


class TicketService:
    def abrir(self, conversa, *, categoria="", orientacao="", prioridade="media", motivo="",
              descricao="", resumo="", fora_do_horario=False, aprovadores=None) -> Chamado:
        """Abre um chamado para a conversa. Se ela já tem um chamado aberto, reaproveita (sem duplicar)."""
        existente = conversa.chamados.filter(status__in=Chamado.ABERTOS).first() if conversa.pk else None
        if existente:
            self._evento(existente, EventoChamado.Tipo.NOTA, f"Nova solicitação na mesma conversa: {motivo}")
            return existente

        dados = conversa.dados or {}
        chamado = Chamado.objects.create(
            conversa=conversa,
            colaborador=conversa.colaborador,
            canal=conversa.canal,
            nome_colaborador=dados.get("nome", "")[:150],
            setor=dados.get("setor", "")[:100],
            centro_custo=dados.get("centro_custo", "")[:60],
            contato=(dados.get("email") or dados.get("matricula") or "")[:150],
            categoria=categoria[:80],
            orientacao=orientacao[:120],
            descricao=descricao,
            resumo=resumo,
            motivo=motivo[:255],
            prioridade=PRIORIDADE_POR_NOME.get(prioridade, Chamado.Prioridade.MEDIA),
            fora_do_horario=fora_do_horario,
        )
        chamado.protocolo = f"TI-{chamado.criado_em.year}-{chamado.pk:06d}"
        chamado.exige_aprovacao = bool(aprovadores)
        chamado.status = S.AGUARDANDO_APROVACAO if aprovadores else S.EM_FILA
        self._definir_sla(chamado)
        chamado.save(update_fields=["protocolo", "status", "sla_horas", "prazo_sla", "exige_aprovacao"])
        self._evento(chamado, EventoChamado.Tipo.ABERTO,
                     f"Aberto pelo assistente ({conversa.get_canal_display()}). Motivo: {motivo}"
                     + (" | Fora do horário de atendimento." if fora_do_horario else "")
                     + f" | SLA: {chamado.sla_horas}h úteis"
                     + (", a partir da aprovação." if aprovadores else "."))
        if aprovadores:
            from . import aprovacoes

            aprovacoes.criar(chamado, aprovadores)
        self._enviar_ao_sistema_externo(chamado)
        return chamado

    def atribuir(self, chamado: Chamado, usuario) -> Chamado:
        chamado.responsavel = usuario
        campos = ["responsavel", "atualizado_em"]
        if chamado.status in (S.ABERTO, S.EM_FILA):
            chamado.status = S.EM_ATENDIMENTO
            campos.append("status")
        chamado.save(update_fields=campos)
        self._evento(chamado, EventoChamado.Tipo.ATRIBUIDO, f"Assumido por {_nome(usuario)}", usuario)
        return chamado

    def mudar_status(self, chamado: Chamado, novo: str, usuario=None, nota: str = "") -> Chamado:
        if novo == chamado.status:
            return chamado
        if chamado.status == S.AGUARDANDO_APROVACAO:
            raise TransicaoInvalida("Aguardando aprovação do coordenador e do gerente da área: "
                                    "o chamado entra na fila sozinho quando os dois aprovarem.")
        if chamado.exige_aprovacao and chamado.aprovado_em is None and novo == S.EM_FILA:
            raise TransicaoInvalida("Esta solicitação foi reprovada (não tem as aprovações). "
                                    "O colaborador precisa abrir uma nova solicitação.")
        if novo not in TRANSICOES.get(chamado.status, set()):
            raise TransicaoInvalida(f"Não é possível ir de '{chamado.get_status_display()}' para '{S(novo).label}'.")
        reabrindo = chamado.status in (S.RESOLVIDO, S.FECHADO)
        anterior = chamado.get_status_display()
        chamado.status = novo
        chamado.save(update_fields=["status", "atualizado_em"])
        tipo = EventoChamado.Tipo.REABERTO if reabrindo else EventoChamado.Tipo.STATUS
        texto = f"{anterior} → {chamado.get_status_display()}" + (f". {nota}" if nota else "")
        self._evento(chamado, tipo, texto, usuario)
        return chamado

    def resolver(self, chamado: Chamado, usuario, solucao: str) -> Chamado:
        solucao = (solucao or "").strip()
        if not solucao:
            raise TransicaoInvalida("Descreva a solução antes de resolver o chamado.")
        if chamado.status == S.AGUARDANDO_APROVACAO:
            raise TransicaoInvalida("Aguarde as aprovações do coordenador e do gerente da área antes de executar.")
        if chamado.status not in TRANSICOES or S.RESOLVIDO not in TRANSICOES[chamado.status]:
            raise TransicaoInvalida(f"Chamado '{chamado.get_status_display()}' não pode ser resolvido.")
        chamado.status = S.RESOLVIDO
        chamado.solucao = solucao
        chamado.resolvido_em = timezone.now()
        if chamado.responsavel is None:
            chamado.responsavel = usuario
        chamado.save()
        self._evento(chamado, EventoChamado.Tipo.SOLUCAO, solucao, usuario)
        return chamado

    def reclassificar(self, chamado: Chamado, categoria: str, usuario=None) -> Chamado:
        """Troca a categoria; o SLA passa a ser o da nova categoria (contado desde a abertura)."""
        categoria = (categoria or "").strip()[:80]
        if categoria == chamado.categoria:
            return chamado
        anterior, sla_anterior = chamado.categoria or "sem categoria", chamado.sla_horas
        chamado.categoria = categoria
        self._definir_sla(chamado)
        chamado.save(update_fields=["categoria", "sla_horas", "prazo_sla", "atualizado_em"])
        self._evento(chamado, EventoChamado.Tipo.RECLASSIFICADO,
                     f"{anterior} → {categoria or 'sem categoria'}. SLA: {sla_anterior}h → {chamado.sla_horas}h úteis.",
                     usuario)
        return chamado

    def registrar_pesquisa(self, chamado: Chamado, resposta: str, observacao: str = "") -> PesquisaSatisfacao:
        observacao = (observacao or "").strip()
        if resposta not in PesquisaSatisfacao.Resposta.values:
            raise ValueError("Resposta da pesquisa inválida.")
        if resposta in PesquisaSatisfacao.EXIGEM_OBSERVACAO and not observacao:
            raise ValueError("A observação é obrigatória para respostas de insatisfação.")
        pesquisa = PesquisaSatisfacao.objects.create(chamado=chamado, resposta=resposta, observacao=observacao)
        self._evento(chamado, EventoChamado.Tipo.PESQUISA,
                     pesquisa.get_resposta_display() + (f": {observacao}" if observacao else ""))
        return pesquisa

    def registrar_resposta(self, chamado: Chamado, usuario, texto: str) -> None:
        if chamado.status in (S.ABERTO, S.EM_FILA):
            chamado.status = S.EM_ATENDIMENTO
            if chamado.responsavel is None:
                chamado.responsavel = usuario
            chamado.save(update_fields=["status", "responsavel", "atualizado_em"])
        self._evento(chamado, EventoChamado.Tipo.RESPOSTA, texto[:500], usuario)

    def colaborador_respondeu(self, chamado: Chamado) -> None:
        if chamado.status == S.AGUARDANDO_USUARIO:
            self.mudar_status(chamado, S.EM_ATENDIMENTO, nota="Colaborador respondeu.")
        else:
            Chamado.objects.filter(pk=chamado.pk).update(atualizado_em=timezone.now())

    # --- auxiliares -------------------------------------------------------
    def _definir_sla(self, chamado: Chamado) -> None:
        chamado.sla_horas = sla_da_categoria(chamado.categoria)
        inicio = chamado.inicio_sla  # None = aguardando aprovação: o prazo é calculado ao aprovar
        chamado.prazo_sla = somar_horas_uteis(inicio, chamado.sla_horas) if inicio else None

    def _evento(self, chamado, tipo, descricao, autor=None):
        return EventoChamado.objects.create(chamado=chamado, tipo=tipo, descricao=descricao, autor=autor)

    def _enviar_ao_sistema_externo(self, chamado: Chamado) -> None:
        backend = import_string(settings.CHAMADOS_BACKEND)()
        try:
            # savepoint: uma falha externa não pode desfazer o chamado local
            with transaction.atomic():
                protocolo = backend.abrir(chamado)
        except Exception:  # o atendimento não pode parar por falha no sistema externo
            log.exception("Falha ao enviar o chamado %s ao sistema externo", chamado.protocolo)
            self._evento(chamado, EventoChamado.Tipo.INTEGRACAO, "Falha ao enviar ao sistema externo.")
            return
        if protocolo:
            chamado.protocolo_externo = protocolo
            chamado.save(update_fields=["protocolo_externo"])
            self._evento(chamado, EventoChamado.Tipo.INTEGRACAO, f"Criado no sistema externo: {protocolo}")


def _nome(usuario) -> str:
    if usuario is None:
        return "sistema"
    return usuario.get_full_name() or usuario.get_username()
