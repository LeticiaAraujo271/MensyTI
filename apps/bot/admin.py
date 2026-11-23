from django.contrib import admin

from .models import Avaliacao, Colaborador, Conversa, Mensagem, OrientacaoVista


class MensagemInline(admin.TabularInline):
    model = Mensagem
    extra = 0
    can_delete = False
    fields = ("criada_em", "autor", "analista", "etapa", "texto")
    readonly_fields = fields


@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = ("nome", "setor", "email", "matricula", "atualizado_em")
    search_fields = ("nome", "email", "matricula", "setor")


@admin.register(Conversa)
class ConversaAdmin(admin.ModelAdmin):
    list_display = ("id", "canal", "nome", "setor", "etapa", "resultado", "ativa", "ultima_interacao")
    list_filter = ("canal", "ativa", "resultado", "etapa")
    search_fields = ("identificador", "dados", "colaborador__nome", "colaborador__email")
    readonly_fields = ("canal", "identificador", "criada_em", "ultima_interacao", "encerrada_em")
    inlines = [MensagemInline]
    actions = ["encerrar"]

    @admin.display(description="Colaborador")
    def nome(self, obj):
        return obj.dados.get("nome", "")

    @admin.display(description="Setor")
    def setor(self, obj):
        return obj.dados.get("setor", "")

    @admin.action(description="Encerrar conversa (próxima mensagem inicia um novo atendimento)")
    def encerrar(self, request, queryset):
        queryset.filter(ativa=True).update(ativa=False, etapa="encerrado")


@admin.register(OrientacaoVista)
class OrientacaoVistaAdmin(admin.ModelAdmin):
    list_display = ("orientacao", "categoria", "resolveu", "vista_em")
    list_filter = ("categoria", "resolveu", "vista_em")


@admin.register(Avaliacao)
class AvaliacaoAdmin(admin.ModelAdmin):
    list_display = ("conversa", "nota", "criada_em")
    list_filter = ("nota", "criada_em")
