"""
Separação exigida pela especificação:
  Colaborador  -> quem é a pessoa (dados de identificação)
  Conversa     -> um atendimento em um canal (web ou WhatsApp), com o estado do motor
  Mensagem     -> histórico do atendimento (colaborador, bot, analista, sistema)
  Chamado      -> apps.chamados (pode existir sem o canal continuar ativo)
"""
from django.conf import settings
from django.db import models
from django.db.models import Q


class Colaborador(models.Model):
    nome = models.CharField(max_length=150)
    setor = models.CharField(max_length=100, blank=True)
    email = models.EmailField("e-mail corporativo", blank=True, db_index=True)
    matricula = models.CharField(max_length=20, blank=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "colaborador"
        verbose_name_plural = "colaboradores"

    def __str__(self):
        return f"{self.nome} ({self.email or self.matricula or self.setor})"


class Conversa(models.Model):
    """Um atendimento. Cada identidade de canal tem no máximo UMA conversa ativa."""

    class Canal(models.TextChoices):
        WEB = "web", "Portal web"
        WHATSAPP = "whatsapp", "WhatsApp"

    class Resultado(models.TextChoices):
        ANDAMENTO = "andamento", "Em andamento"
        RESOLVIDA = "resolvida", "Resolvida no autoatendimento"
        ESCALADA = "escalada", "Escalada para a TI (chamado)"
        CANCELADA = "cancelada", "Encerrada pelo colaborador"
        EXPIRADA = "expirada", "Expirada por inatividade"

    canal = models.CharField(max_length=10, choices=Canal.choices)
    identificador = models.CharField(
        "identidade no canal", max_length=64,
        help_text="Web: sessão do navegador. WhatsApp: ID do contato no provedor.",
    )
    colaborador = models.ForeignKey(Colaborador, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="conversas")
    etapa = models.CharField(max_length=20, default="inicio")
    dados = models.JSONField(default=dict, blank=True, help_text="Identificação e estado do atendimento.")
    ativa = models.BooleanField(default=True)
    resultado = models.CharField(max_length=10, choices=Resultado.choices, default=Resultado.ANDAMENTO)
    criada_em = models.DateTimeField(auto_now_add=True)
    ultima_interacao = models.DateTimeField(auto_now=True)
    encerrada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-ultima_interacao"]
        verbose_name = "conversa"
        verbose_name_plural = "conversas"
        constraints = [
            models.UniqueConstraint(fields=["canal", "identificador"], condition=Q(ativa=True),
                                    name="uma_conversa_ativa_por_identidade"),
        ]
        indexes = [models.Index(fields=["canal", "identificador"])]

    def __str__(self):
        return f"#{self.pk} {self.dados.get('nome') or self.identificador} ({self.get_canal_display()})"


class Mensagem(models.Model):
    class Autor(models.TextChoices):
        COLABORADOR = "colaborador", "Colaborador"
        BOT = "bot", "Assistente"
        ANALISTA = "analista", "Analista de TI"
        SISTEMA = "sistema", "Sistema"

    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="mensagens")
    autor = models.CharField(max_length=12, choices=Autor.choices)
    texto = models.TextField(blank=True)
    analista = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    id_externo = models.CharField(
        max_length=100, unique=True, null=True, blank=True,
        help_text="Evita processar a mesma mensagem duas vezes (reenvio de webhook, clique duplo).",
    )
    etapa = models.CharField(max_length=20, blank=True, help_text="Etapa em que a conversa estava.")
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criada_em", "id"]
        verbose_name = "mensagem"
        verbose_name_plural = "mensagens"


class OrientacaoVista(models.Model):
    """Métrica: quais orientações estão sendo usadas e se resolvem."""

    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="orientacoes_vistas")
    categoria = models.CharField(max_length=80)
    orientacao = models.CharField(max_length=120)
    resolveu = models.BooleanField(null=True)
    vista_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-vista_em"]
        verbose_name = "orientação vista"
        verbose_name_plural = "orientações vistas"


class Avaliacao(models.Model):
    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="avaliacoes")
    nota = models.PositiveSmallIntegerField()
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em"]
        verbose_name = "avaliação"
        verbose_name_plural = "avaliações"
