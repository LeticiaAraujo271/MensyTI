from django.contrib import admin

from .models import Chamado, EventoChamado


class EventoInline(admin.TabularInline):
    model = EventoChamado
    extra = 0
    can_delete = False
    fields = ("criado_em", "tipo", "autor", "descricao")
    readonly_fields = fields


@admin.register(Chamado)
class ChamadoAdmin(admin.ModelAdmin):
    list_display = ("protocolo", "nome_colaborador", "setor", "categoria", "prioridade", "status",
                    "responsavel", "canal", "fora_do_horario", "criado_em")
    list_filter = ("status", "prioridade", "canal", "fora_do_horario", "categoria", "criado_em")
    search_fields = ("protocolo", "nome_colaborador", "contato", "setor", "descricao", "resumo")
    readonly_fields = ("protocolo", "conversa", "colaborador", "canal", "resumo", "criado_em",
                       "atualizado_em", "resolvido_em")
    inlines = [EventoInline]
