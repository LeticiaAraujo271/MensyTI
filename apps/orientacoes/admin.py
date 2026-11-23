from django.contrib import admin

from .models import Categoria, Orientacao


class OrientacaoInline(admin.StackedInline):
    model = Orientacao
    extra = 0
    fields = ("titulo", "passos", "observacao", "palavras_chave", "prioridade", "abre_chamado", "ordem", "ativa")


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "emoji", "ordem", "ativa")
    list_editable = ("ordem", "ativa")
    inlines = [OrientacaoInline]


@admin.register(Orientacao)
class OrientacaoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "prioridade", "abre_chamado", "ordem", "ativa", "atualizada_em")
    list_filter = ("categoria", "ativa", "prioridade", "abre_chamado")
    search_fields = ("titulo", "passos", "palavras_chave")
