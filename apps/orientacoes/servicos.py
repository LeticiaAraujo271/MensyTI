"""KnowledgeService: entrega ao motor apenas o conteúdo aprovado e ativo da base de conhecimento."""
from django.db.models import Prefetch

from apps.bot import engine

from .models import Categoria, Orientacao


class KnowledgeService:
    def catalogo(self) -> list[dict]:
        ativas = Prefetch("orientacoes",
                          queryset=Orientacao.objects.filter(ativa=True).order_by("ordem", "id"))
        catalogo = []
        for cat in Categoria.objects.filter(ativa=True).prefetch_related(ativas):
            catalogo.append({
                "nome": cat.nome,
                "emoji": cat.emoji,
                # Categoria sem orientação (ex.: "Outros") aparece e leva direto ao chamado.
                "orientacoes": [
                    {
                        "titulo": o.titulo,
                        "passos": o.lista_passos(),
                        "observacao": o.observacao,
                        "palavras_chave": o.lista_palavras_chave(),
                        "prioridade": o.prioridade,
                        "abre_chamado": o.abre_chamado,
                        "exige_aprovacao": o.exige_aprovacao,
                    }
                    for o in cat.orientacoes.all()
                ],
            })
        return catalogo

    def buscar(self, texto: str, limite: int = 3) -> list[dict]:
        catalogo = self.catalogo()
        return [
            {"categoria": catalogo[ci]["nome"], **catalogo[ci]["orientacoes"][oi], "pontos": pontos}
            for pontos, ci, oi in engine.buscar_orientacoes(catalogo, texto, limite)
        ]
