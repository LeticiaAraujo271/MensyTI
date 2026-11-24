from django.contrib import admin

from .models import Categoria, Orientacao


class OrientacaoInline(admin.StackedInline):
    model = Orientacao
    extra = 0
    fields = ("titulo", "passos", "observacao", "palavras_chave", "prioridade", "abre_chamado", "exige_aprovacao", "ordem", "ativa")


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "emoji", "ordem", "sla_horas", "ativa")
    list_editable = ("ordem", "sla_horas", "ativa")
    inlines = [OrientacaoInline]


@admin.register(Orientacao)
class OrientacaoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "prioridade", "abre_chamado", "exige_aprovacao", "ordem", "ativa", "atualizada_em")
    list_filter = ("categoria", "ativa", "prioridade", "abre_chamado", "exige_aprovacao")
    search_fields = ("titulo", "passos", "palavras_chave")
