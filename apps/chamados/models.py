from django.conf import settings
from django.db import models


class Chamado(models.Model):
    """Chamado de TI aberto pelo assistente (ou pela equipe), com protocolo e histórico."""

    class Status(models.TextChoices):
        ABERTO = "aberto", "Aberto"
        EM_FILA = "em_fila", "Em fila"
        EM_ATENDIMENTO = "em_atendimento", "Em atendimento"
        AGUARDANDO_USUARIO = "aguardando_usuario", "Aguardando colaborador"
        RESOLVIDO = "resolvido", "Resolvido"
        FECHADO = "fechado", "Fechado"

    class Prioridade(models.IntegerChoices):  # número menor = mais urgente (ordena a fila)
        CRITICA = 1, "Crítica"
        ALTA = 2, "Alta"
        MEDIA = 3, "Média"
        BAIXA = 4, "Baixa"

    ABERTOS = (Status.ABERTO, Status.EM_FILA, Status.EM_ATENDIMENTO, Status.AGUARDANDO_USUARIO)

    protocolo = models.CharField(max_length=20, unique=True, null=True, blank=True)
    conversa = models.ForeignKey("bot.Conversa", on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="chamados")
    colaborador = models.ForeignKey("bot.Colaborador", on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="chamados")
    canal = models.CharField(max_length=10, blank=True)

    # Cópia dos dados no momento da abertura (o colaborador não precisa repetir nada)
    nome_colaborador = models.CharField("colaborador", max_length=150, blank=True)
    setor = models.CharField(max_length=100, blank=True)
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
