from django.contrib import admin

from .models import Chamado, EventoChamado, Feriado, PesquisaSatisfacao


class EventoInline(admin.TabularInline):
    model = EventoChamado
    extra = 0
    can_delete = False
    fields = ("criado_em", "tipo", "autor", "descricao")
    readonly_fields = fields


@admin.register(Chamado)
class ChamadoAdmin(admin.ModelAdmin):
    list_display = ("protocolo", "nome_colaborador", "setor", "centro_custo", "categoria", "prioridade", "status",
                    "situacao_sla", "responsavel", "canal", "fora_do_horario", "criado_em")
    list_filter = ("status", "prioridade", "canal", "fora_do_horario", "categoria", "centro_custo", "criado_em")
    search_fields = ("protocolo", "nome_colaborador", "contato", "setor", "centro_custo", "descricao", "resumo")
    readonly_fields = ("protocolo", "conversa", "colaborador", "canal", "resumo", "criado_em",
                       "atualizado_em", "resolvido_em", "sla_horas", "prazo_sla")
    inlines = [EventoInline]

    @admin.display(description="SLA")
    def situacao_sla(self, obj):
        s = obj.sla
        return f"{ {'verde': '🟢', 'amarelo': '🟡'}.get(s.cor, '🔴') } {s.rotulo} ({s.percentual}%)"

    def save_model(self, request, obj, form, change):
        # Mudou a categoria pelo Admin: o SLA passa a ser o da nova categoria.
        if change and "categoria" in form.changed_data:
            from .servicos import TicketService

            nova = obj.categoria
            obj.categoria = form.initial.get("categoria", "")
            super().save_model(request, obj, form, change)
            TicketService().reclassificar(obj, nova, request.user)
            return
        super().save_model(request, obj, form, change)


@admin.register(PesquisaSatisfacao)
class PesquisaSatisfacaoAdmin(admin.ModelAdmin):
    list_display = ("chamado", "resposta", "observacao", "respondida_em")
    list_filter = ("resposta", "respondida_em")
    search_fields = ("chamado__protocolo", "chamado__nome_colaborador", "observacao")
    readonly_fields = ("chamado", "resposta", "observacao", "respondida_em")

    def has_add_permission(self, request):
        return False  # quem responde é o colaborador, pelo chat


@admin.register(Feriado)
class FeriadoAdmin(admin.ModelAdmin):
    """Dias sem expediente: não contam no SLA. Os nacionais já vêm cadastrados (manage.py carregar_feriados)."""

    list_display = ("data", "dia_da_semana", "nome")
    list_filter = (("data", admin.DateFieldListFilter),)
    search_fields = ("nome",)
    date_hierarchy = "data"

    @admin.display(description="Dia da semana")
    def dia_da_semana(self, obj):
        return ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")[obj.data.weekday()]
