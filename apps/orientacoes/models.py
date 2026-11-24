from django.db import models


class Categoria(models.Model):
    nome = models.CharField(max_length=80)
    emoji = models.CharField(max_length=8, blank=True)
    ordem = models.PositiveSmallIntegerField(default=0, help_text="Posição no menu (menor aparece primeiro).")
    sla_horas = models.PositiveSmallIntegerField(
        "SLA (horas úteis)", default=72,
        help_text="Prazo para resolver os chamados desta categoria, em horas úteis (horário de atendimento). "
                  "Ex.: 8 = um dia útil.",
    )
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["ordem", "id"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.nome


class Orientacao(models.Model):
    """Procedimento padrão aprovado pela TI. O assistente só usa o que está cadastrado aqui."""

    class Prioridade(models.TextChoices):
        BAIXA = "baixa", "Baixa"
        MEDIA = "media", "Média"
        ALTA = "alta", "Alta"
        CRITICA = "critica", "Crítica (incidente / segurança)"

    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name="orientacoes")
    titulo = models.CharField(max_length=120)
    passos = models.TextField(help_text="Um passo por linha. O assistente numera automaticamente.")
    observacao = models.CharField(max_length=255, blank=True, help_text="Aviso exibido no fim (opcional).")
    palavras_chave = models.CharField(
        max_length=255, blank=True,
        help_text="Separadas por vírgula. Ajudam o assistente a achar esta orientação quando o "
                  "colaborador descreve o problema com as próprias palavras.",
    )
    prioridade = models.CharField(
        max_length=8, choices=Prioridade.choices, default=Prioridade.MEDIA,
        help_text="Prioridade do chamado, se for aberto. 'Crítica' mostra os avisos e abre o chamado "
                  "na hora, sem perguntar se resolveu.",
    )
    abre_chamado = models.BooleanField(
        "sempre abre chamado", default=False,
        help_text="Mostra a orientação e abre o chamado (ex.: solicitação de acesso, que a TI precisa executar).",
    )
    ordem = models.PositiveSmallIntegerField(default=0)
    ativa = models.BooleanField(default=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria__ordem", "ordem", "id"]
        verbose_name = "orientação"
        verbose_name_plural = "orientações"

    def __str__(self):
        return self.titulo

    def lista_passos(self):
        return [p.strip() for p in self.passos.splitlines() if p.strip()]

    def lista_palavras_chave(self):
        return [p.strip() for p in self.palavras_chave.split(",") if p.strip()]
