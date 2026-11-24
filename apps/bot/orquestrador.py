"""
ConversationOrchestrator: liga o motor (engine.py) ao banco, aos chamados e aos canais.

Fluxo de uma mensagem do colaborador (qualquer canal):
  1. Localiza a conversa ativa da identidade (ou cria uma nova, reaproveitando a identificação).
  2. Grava a mensagem já sem dados sensíveis (ignora se o id_externo já foi processado).
  3. Chamado aberto? A mensagem vai para o chamado e o bot não responde.
     Senão: roda o motor, executa as ações (abrir chamado, avaliação, métricas) e grava as respostas.
  4. Fora da transação: pede ao canal para entregar as respostas (falha de entrega não perde nada).

A equipe de TI usa responder_como_analista() e resolver_chamado() pelo painel. Ao resolver,
o colaborador recebe a solução e a pesquisa de satisfação (etapas pesquisa/pesquisa_obs do motor).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.canais import ChannelAdapter, obter_canal
from apps.chamados.models import Chamado
from apps.chamados.servicos import TicketService
from apps.orientacoes.servicos import KnowledgeService

from . import engine
from .horario import WorkingHoursService
from .models import Avaliacao, Colaborador, Conversa, Mensagem, OrientacaoVista

log = logging.getLogger(__name__)

CAMPOS_IDENTIFICACAO = ("nome", "setor", "email", "matricula")

ETAPAS_PESQUISA = (engine.PESQUISA, engine.PESQUISA_OBS)

TEXTO_SO_TEXTO = (
    "Por enquanto eu só entendo mensagens de *texto* 🙂 "
    "Responda com o número da opção ou descreva o problema."
)


class ConversationOrchestrator:
    def __init__(self, canal: ChannelAdapter, tickets: TicketService | None = None,
                 conhecimento: KnowledgeService | None = None, horario: WorkingHoursService | None = None):
        self.canal = canal
        self.tickets = tickets or TicketService()
        self.conhecimento = conhecimento or KnowledgeService()
        self.horario = horario or WorkingHoursService()

    # ------------------------------------------------------------------
    # Colaborador -> assistente
    # ------------------------------------------------------------------
    def contexto(self) -> engine.Contexto:
        central = settings.CENTRAL
        return engine.Contexto(
            catalogo=self.conhecimento.catalogo(),
            dentro_do_horario=self.horario.dentro_do_horario(),
            texto_horario=self.horario.texto(),
            campos_identificacao=tuple(central["IDENTIFICACAO"]),
            dominios_email=tuple(central["DOMINIOS_EMAIL"]),
            nome_central=central["NOME"],
        )

    def iniciar(self, identificador: str) -> list[str]:
        """Cumprimenta quem acabou de abrir o canal (sem mensagem do colaborador)."""
        with transaction.atomic():
            conversa = self._conversa_ativa(identificador)
            if conversa.mensagens.exists():
                return []
            return self._rodar_motor(conversa, "", sensivel=False)

    def receber(self, identificador: str, texto: str, id_externo: str = "") -> list[str] | None:
        """Processa uma mensagem de texto. Devolve as respostas do bot (None = mensagem repetida)."""
        texto = (texto or "")[:2000]
        with transaction.atomic():
            conversa = self._conversa_ativa(identificador)
            texto_seguro, sensivel = engine.mascarar_sensivel(texto)
            if not self._registrar_entrada(conversa, texto_seguro, id_externo):
                return None
            if conversa.etapa == engine.HUMANO:
                chamado = conversa.chamados.filter(status__in=Chamado.ABERTOS).first()
                if chamado:
                    self.tickets.colaborador_respondeu(chamado)
                    conversa.save(update_fields=["ultima_interacao"])
                    respostas = [engine.AVISO_SENSIVEL] if sensivel else []
                    self._gravar_respostas(conversa, respostas)
                    return self._entregar(conversa, respostas)
                conversa.etapa = engine.ENCERRADO  # chamado já resolvido: recomeça
            respostas = self._rodar_motor(conversa, texto_seguro, sensivel)
        return self._entregar(conversa, respostas)

    def receber_midia(self, identificador: str, tipo: str, id_externo: str = "") -> list[str] | None:
        """Áudio, imagem, documento... Fica no histórico; o bot pede texto (exceto com chamado aberto)."""
        with transaction.atomic():
            conversa = self._conversa_ativa(identificador)
            if not self._registrar_entrada(conversa, f"[{tipo or 'mídia'}]", id_externo):
                return None
            if conversa.etapa == engine.HUMANO:
                chamado = conversa.chamados.filter(status__in=Chamado.ABERTOS).first()
                if chamado:
                    self.tickets.colaborador_respondeu(chamado)
                return []
            self._gravar_respostas(conversa, [TEXTO_SO_TEXTO])
        return self._entregar(conversa, [TEXTO_SO_TEXTO])

    # ------------------------------------------------------------------
    # Equipe de TI -> colaborador (painel)
    # ------------------------------------------------------------------
    def responder_como_analista(self, chamado: Chamado, usuario, texto: str) -> Mensagem:
        texto = (texto or "").strip()
        if not texto:
            raise ValueError("Escreva a mensagem.")
        if chamado.conversa_id is None:
            raise ValueError("Este chamado não tem conversa vinculada.")
        with transaction.atomic():
            conversa = chamado.conversa
            msg = Mensagem.objects.create(conversa=conversa, autor=Mensagem.Autor.ANALISTA,
                                          analista=usuario, texto=texto, etapa=conversa.etapa)
            self.tickets.registrar_resposta(chamado, usuario, texto)
        nome = usuario.get_full_name() or usuario.get_username()
        self._entregar(conversa, [f"🙋 *{nome}* (TI): {texto}"])
        return msg

    def resolver_chamado(self, chamado: Chamado, usuario, solucao: str) -> Chamado:
        with transaction.atomic():
            self.tickets.resolver(chamado, usuario, solucao)
            conversa = chamado.conversa
            if conversa is None:
                return chamado
            texto = (f"✅ O seu chamado *{chamado.protocolo}* foi resolvido.\n\n"
                     f"*Solução:* {chamado.solucao}\n\n"
                     "Se o problema voltar, é só escrever aqui para iniciar um novo atendimento.")
            Mensagem.objects.create(conversa=conversa, autor=Mensagem.Autor.SISTEMA, texto=texto,
                                    etapa=conversa.etapa)
            textos = [texto]
            if conversa.ativa and conversa.etapa == engine.HUMANO:
                # Pesquisa de satisfação: a conversa continua até o colaborador responder.
                conversa.etapa = engine.PESQUISA
                conversa.dados = {**(conversa.dados or {}), "tentativas": 0,
                                  "pesquisa": {"chamado": chamado.pk, "protocolo": chamado.protocolo}}
                conversa.save()
                pergunta = engine.texto_pesquisa(chamado.protocolo)
                self._gravar_respostas(conversa, [pergunta])
                textos.append(pergunta)
        self._entregar(conversa, textos)
        return chamado

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------
    def _conversa_ativa(self, identificador: str) -> Conversa:
        canal = self.canal.nome
        qs = Conversa.objects.select_for_update().filter(canal=canal, identificador=identificador, ativa=True)
        conversa = qs.first()
        if conversa and self._expirou(conversa):
            # Pesquisa sem resposta não muda o resultado do atendimento (continua "escalada").
            resultado = (conversa.resultado if conversa.etapa in ETAPAS_PESQUISA
                         else Conversa.Resultado.EXPIRADA)
            conversa.etapa = engine.ENCERRADO
            self._fechar(conversa, resultado)
            conversa = None
        if conversa:
            return conversa

        anterior = (Conversa.objects.filter(canal=canal, identificador=identificador)
                    .order_by("-criada_em").first())
        dados = {k: v for k, v in (anterior.dados if anterior else {}).items() if k in CAMPOS_IDENTIFICACAO}
        try:
            with transaction.atomic():
                return Conversa.objects.create(canal=canal, identificador=identificador, dados=dados,
                                               colaborador=anterior.colaborador if anterior else None)
        except IntegrityError:  # outra requisição criou ao mesmo tempo
            return qs.get()

    def _expirou(self, conversa: Conversa) -> bool:
        if conversa.etapa in (engine.INICIO, engine.HUMANO):
            return False
        if conversa.etapa in ETAPAS_PESQUISA:
            limite = timedelta(hours=settings.BOT.get("PESQUISA_HORAS", 72))
        else:
            limite = timedelta(minutes=settings.BOT["TIMEOUT_MINUTOS"])
        return timezone.now() - conversa.ultima_interacao > limite

    def _fechar(self, conversa: Conversa, resultado: str) -> None:
        conversa.ativa = False
        conversa.resultado = resultado
        conversa.encerrada_em = timezone.now()
        conversa.save()

    def _registrar_entrada(self, conversa: Conversa, texto: str, id_externo: str) -> bool:
        try:
            with transaction.atomic():
                Mensagem.objects.create(
                    conversa=conversa, autor=Mensagem.Autor.COLABORADOR, texto=texto,
                    id_externo=f"{self.canal.nome}:{id_externo}" if id_externo else None,
                    etapa=conversa.etapa,
                )
            return True
        except IntegrityError:
            log.info("Mensagem %s já processada; ignorando.", id_externo)
            return False

    def _rodar_motor(self, conversa: Conversa, texto: str, sensivel: bool) -> list[str]:
        ctx = self.contexto()
        etapa_anterior = conversa.etapa
        resultado = engine.processar(engine.Estado(conversa.etapa, conversa.dados), texto, ctx)
        conversa.etapa = resultado.estado.etapa
        conversa.dados = resultado.estado.dados
        respostas = list(resultado.respostas)
        if sensivel:
            respostas.insert(0, engine.AVISO_SENSIVEL)

        self._marcar_resolveu(conversa, etapa_anterior, resultado.acoes)
        for acao in resultado.acoes:
            respostas = self._executar(conversa, acao, ctx, respostas)
        if conversa.ativa:
            conversa.save()
        self._gravar_respostas(conversa, respostas)
        return respostas

    def _executar(self, conversa: Conversa, acao: engine.Acao, ctx: engine.Contexto,
                  respostas: list[str]) -> list[str]:
        if acao.tipo == engine.ACAO_IDENTIFICADO:
            conversa.colaborador = self._vincular_colaborador(acao.params)
        elif acao.tipo == engine.ACAO_REGISTRAR_ORIENTACAO:
            OrientacaoVista.objects.create(conversa=conversa, **acao.params)
        elif acao.tipo == engine.ACAO_ABRIR_CHAMADO:
            conversa.save()
            chamado = self.tickets.abrir(conversa, fora_do_horario=not ctx.dentro_do_horario, **acao.params)
            conversa.resultado = Conversa.Resultado.ESCALADA
            respostas = [r.replace(engine.PROTOCOLO, chamado.protocolo) for r in respostas]
        elif acao.tipo == engine.ACAO_REGISTRAR_AVALIACAO:
            Avaliacao.objects.create(conversa=conversa, nota=acao.params["nota"])
        elif acao.tipo == engine.ACAO_REGISTRAR_PESQUISA:
            chamado = Chamado.objects.filter(pk=acao.params.get("chamado")).first()
            if chamado:
                self.tickets.registrar_pesquisa(chamado, acao.params["resposta"], acao.params["observacao"])
        elif acao.tipo == engine.ACAO_ENCERRAR:
            self._fechar(conversa, acao.params.get("resultado") or Conversa.Resultado.CANCELADA)
        return respostas

    def _vincular_colaborador(self, dados: dict) -> Colaborador:
        colaborador = None
        if dados.get("email"):
            colaborador = Colaborador.objects.filter(email=dados["email"]).first()
        elif dados.get("matricula"):
            colaborador = Colaborador.objects.filter(matricula=dados["matricula"]).first()
        colaborador = colaborador or Colaborador()
        for campo in CAMPOS_IDENTIFICACAO:
            if dados.get(campo):
                setattr(colaborador, campo, dados[campo])
        colaborador.save()
        return colaborador

    def _marcar_resolveu(self, conversa: Conversa, etapa_anterior: str, acoes: list[engine.Acao]) -> None:
        """Métrica: a orientação vista resolveu (Sim) ou não (virou chamado)?"""
        if etapa_anterior != engine.RESOLVEU:
            return
        if conversa.etapa == engine.AVALIACAO:
            resolveu = True
        elif conversa.etapa == engine.DESCREVER:
            resolveu = False
        else:
            return  # voltou ao menu / viu outra orientação
        ultima = conversa.orientacoes_vistas.filter(resolveu__isnull=True).first()
        if ultima:
            ultima.resolveu = resolveu
            ultima.save(update_fields=["resolveu"])

    def _gravar_respostas(self, conversa: Conversa, respostas: list[str]) -> None:
        for texto in respostas:
            Mensagem.objects.create(conversa=conversa, autor=Mensagem.Autor.BOT, texto=texto,
                                    etapa=conversa.etapa)

    def _entregar(self, conversa: Conversa, textos: list[str]) -> list[str]:
        if not textos:
            return textos
        canal = self.canal if self.canal.nome == conversa.canal else obter_canal(conversa.canal)
        try:
            canal.entregar(conversa, textos)
        except Exception:  # defesa extra: o adaptador não deveria levantar
            log.exception("Falha na entrega pelo canal %s (conversa #%s).", canal.nome, conversa.pk)
        return textos
