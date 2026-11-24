from django.conf import settings
from django.db import models


class Chamado(models.Model):
    """Chamado de TI aberto pelo assistente (ou pela equipe), com protocolo e histórico."""

    class Status(models.TextChoices):
        ABERTO = "aberto", "Aberto"
        EM_FILA = "em_fila", "Em fila"
        EM_ATENDIMENTO = "em_atendimento", "Em atendimento"
        AGUARDANDO_APROVACAO = "aguardando_aprovacao", "Aguardando aprovação"
        AGUARDANDO_USUARIO = "aguardando_usuario", "Aguardando colaborador"
        RESOLVIDO = "resolvido", "Resolvido"
        FECHADO = "fechado", "Fechado"

    class Prioridade(models.IntegerChoices):  # número menor = mais urgente (ordena a fila)
        CRITICA = 1, "Crítica"
        ALTA = 2, "Alta"
        MEDIA = 3, "Média"
        BAIXA = 4, "Baixa"

    ABERTOS = (Status.ABERTO, Status.AGUARDANDO_APROVACAO, Status.EM_FILA, Status.EM_ATENDIMENTO,
               Status.AGUARDANDO_USUARIO)

    protocolo = models.CharField(max_length=20, unique=True, null=True, blank=True)
    conversa = models.ForeignKey("bot.Conversa", on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="chamados")
    colaborador = models.ForeignKey("bot.Colaborador", on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="chamados")
    canal = models.CharField(max_length=10, blank=True)

    # Cópia dos dados no momento da abertura (o colaborador não precisa repetir nada)
    nome_colaborador = models.CharField("colaborador", max_length=150, blank=True)
    setor = models.CharField(max_length=100, blank=True)
    centro_custo = models.CharField("centro de custo", max_length=60, blank=True, db_index=True)
    contato = models.CharField(max_length=150, blank=True, help_text="E-mail corporativo ou matrícula.")

    categoria = models.CharField(max_length=80, blank=True)
    orientacao = models.CharField("orientação vista", max_length=120, blank=True)
    descricao = models.TextField("descrição", blank=True)
    resumo = models.TextField(blank=True)
    motivo = models.CharField(max_length=255, blank=True)

    prioridade = models.PositiveSmallIntegerField(choices=Prioridade.choices, default=Prioridade.MEDIA)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABERTO)
    fora_do_horario = models.BooleanField(default=False)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                    blank=True, related_name="chamados_atribuidos")
    solucao = models.TextField("solução", blank=True)
    protocolo_externo = models.CharField(max_length=60, blank=True,
                                         help_text="Número no sistema de chamados externo (quando integrado).")

    sla_horas = models.PositiveSmallIntegerField(
        "SLA (horas úteis)", default=72,
        help_text="Vem da categoria na abertura; muda se a TI reclassificar o chamado.")
    prazo_sla = models.DateTimeField("prazo do SLA", null=True, blank=True)
    exige_aprovacao = models.BooleanField(
        "exige aprovação", default=False,
        help_text="Solicitação que precisa do coordenador e do gerente da área antes da TI executar.")
    aprovado_em = models.DateTimeField(
        "aprovado em", null=True, blank=True,
        help_text="Quando a última aprovação foi dada. O SLA da TI começa a contar a partir daqui.")

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    resolvido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["prioridade", "criado_em"]
        verbose_name = "chamado"
        verbose_name_plural = "chamados"
        permissions = [("atender_chamado", "Pode atender chamados no painel de TI")]
        indexes = [models.Index(fields=["status", "prioridade"])]

    def __str__(self):
        return f"{self.protocolo} - {self.nome_colaborador} - {self.categoria or self.motivo}"

    @property
    def aberto(self) -> bool:
        return self.status in self.ABERTOS

    @property
    def inicio_sla(self):
        """De quando o SLA conta: abertura, ou a aprovação final (None = ainda aguardando aprovação)."""
        if self.exige_aprovacao:
            return self.aprovado_em
        return self.criado_em

    @property
    def sla(self):
        """Situação do SLA agora: cor (verde/amarelo/vermelho), percentual, prazo..."""
        from .sla import situacao

        if not hasattr(self, "_sla"):
            self._sla = situacao(self)
        return self._sla


class EventoChamado(models.Model):
    """Trilha de auditoria do chamado: quem fez o quê e quando."""

    class Tipo(models.TextChoices):
        ABERTO = "aberto", "Aberto"
        STATUS = "status", "Mudança de status"
        ATRIBUIDO = "atribuido", "Atribuído"
        RESPOSTA = "resposta", "Resposta ao colaborador"
        NOTA = "nota", "Nota"
        SOLUCAO = "solucao", "Solução registrada"
        REABERTO = "reaberto", "Reaberto"
        RECLASSIFICADO = "reclassif", "Reclassificado"
        PESQUISA = "pesquisa", "Pesquisa de satisfação"
        APROVACAO = "aprovacao", "Aprovação"
        INTEGRACAO = "integracao", "Integração externa"

    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name="eventos")
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    descricao = models.TextField(blank=True)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em", "id"]
        verbose_name = "evento do chamado"
        verbose_name_plural = "eventos do chamado"

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.descricao[:60]}"


def _gerar_token() -> str:
    import secrets

    return secrets.token_urlsafe(32)


class Aprovacao(models.Model):
    """Um nível de aprovação da solicitação (1 = coordenador, 2 = gerente da área). Um depois do outro."""

    class Nivel(models.IntegerChoices):
        COORDENADOR = 1, "Coordenador"
        GERENTE = 2, "Gerente da área"

    class Situacao(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        APROVADA = "aprovada", "Aprovada"
        REPROVADA = "reprovada", "Reprovada"
        CANCELADA = "cancelada", "Cancelada"  # um nível anterior reprovou

    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name="aprovacoes")
    nivel = models.PositiveSmallIntegerField(choices=Nivel.choices)
    nome = models.CharField("aprovador", max_length=150)
    email = models.EmailField("e-mail do aprovador")
    situacao = models.CharField(max_length=10, choices=Situacao.choices, default=Situacao.PENDENTE)
    # Segredo do link que o aprovador recebe (quem tem o link decide; não precisa de login).
    token = models.CharField(max_length=64, unique=True, default=_gerar_token, editable=False)
    comentario = models.TextField("comentário", blank=True)
    decidida_em = models.DateTimeField(null=True, blank=True)
    registrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="Analista que registrou a decisão no painel (quando o aprovador respondeu por outro meio).")
    enviada_em = models.DateTimeField("link enviado em", null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["chamado", "nivel"]
        verbose_name = "aprovação"
        verbose_name_plural = "aprovações"
        constraints = [models.UniqueConstraint(fields=["chamado", "nivel"], name="aprovacao_unica_por_nivel")]

    def __str__(self):
        return f"{self.chamado.protocolo} · {self.get_nivel_display()}: {self.get_situacao_display()}"

    @property
    def da_vez(self) -> bool:
        """É este nível que precisa decidir agora?"""
        if self.situacao != self.Situacao.PENDENTE or self.chamado.status != Chamado.Status.AGUARDANDO_APROVACAO:
            return False
        anteriores = self.chamado.aprovacoes.filter(nivel__lt=self.nivel)
        return not anteriores.exclude(situacao=self.Situacao.APROVADA).exists()


class PesquisaSatisfacao(models.Model):
    """Resposta do colaborador à pesquisa enviada quando o chamado é resolvido."""

    class Resposta(models.TextChoices):
        MUITO_SATISFEITO = "muito_satisfeito", "Muito satisfeito"
        SATISFEITO = "satisfeito", "Satisfeito"
        INSATISFEITO = "insatisfeito", "Insatisfeito"
        MUITO_INSATISFEITO = "muito_insatisfeito", "Muito insatisfeito"

    # Nessas respostas a observação é obrigatória (para a TI entender o que melhorar).
    EXIGEM_OBSERVACAO = (Resposta.INSATISFEITO, Resposta.MUITO_INSATISFEITO)

    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name="pesquisas")
    resposta = models.CharField(max_length=20, choices=Resposta.choices)
    observacao = models.TextField("observação", blank=True)
    respondida_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-respondida_em"]
        verbose_name = "pesquisa de satisfação"
        verbose_name_plural = "pesquisas de satisfação"

    def __str__(self):
        return f"{self.chamado.protocolo}: {self.get_resposta_display()}"

    @property
    def negativa(self) -> bool:
        return self.resposta in self.EXIGEM_OBSERVACAO

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.resposta in self.EXIGEM_OBSERVACAO and not (self.observacao or "").strip():
            raise ValidationError({"observacao": "A observação é obrigatória para respostas de insatisfação."})


class Feriado(models.Model):
    """Dia sem expediente: não conta no SLA dos chamados."""

    data = models.DateField(unique=True)
    nome = models.CharField(max_length=80)

    class Meta:
        ordering = ["data"]
        verbose_name = "feriado"
        verbose_name_plural = "feriados"

    def __str__(self):
        return f"{self.data:%d/%m/%Y} - {self.nome}"
