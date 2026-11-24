"""Exportação dos chamados para Excel (.xlsx), usada pelo botão "Exportar Excel" da fila."""
from __future__ import annotations

from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from apps.chamados import sla

# (título da coluna, largura)
COLUNAS = (
    ("Número do chamado", 18),
    ("Colaborador", 26),
    ("Assunto", 28),
    ("Status", 22),
    ("SLA", 12),
    ("SLA (horas úteis)", 10),
    ("SLA consumido (%)", 11),
    ("Prazo do SLA", 17),
    ("Responsável", 18),
    ("Canal", 11),
    ("Aberto em", 17),
    ("Data do fechamento", 17),
    ("Pesquisa de satisfação", 22),
    ("Observação da pesquisa", 50),
)

CORES_SLA = {
    sla.VERDE: ("DCFAE6", "067647"),
    sla.AMARELO: ("FEF0C7", "8A5A00"),
    sla.VERMELHO: ("FEE4E2", "B42318"),
}
FORMATO_DATA = "dd/mm/yyyy hh:mm"


def _data(valor):
    """O Excel não guarda fuso: grava no horário de Brasília (o mesmo que aparece no painel)."""
    return timezone.localtime(valor).replace(tzinfo=None) if valor else None


def _texto(celula, valor: str) -> None:
    # Texto digitado pelo colaborador sempre como texto (nunca como fórmula, ex.: "=HIPERLINK(...)").
    celula.value = valor
    celula.data_type = "s"


def planilha_chamados(chamados) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Chamados"

    cabecalho = PatternFill("solid", fgColor="003C38")
    for i, (titulo, largura) in enumerate(COLUNAS, start=1):
        c = ws.cell(row=1, column=i, value=titulo)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = cabecalho
        c.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = largura
    ws.row_dimensions[1].height = 32

    for linha, ch in enumerate(chamados, start=2):
        s = ch.sla
        pesquisa = next(iter(ch.pesquisas.all()), None)  # a mais recente (já vem ordenada)
        responsavel = ""
        if ch.responsavel:
            responsavel = ch.responsavel.get_full_name() or ch.responsavel.get_username()
        valores = (
            ch.protocolo or "",
            ch.nome_colaborador,
            ch.categoria or "Sem categoria",
            ch.get_status_display(),
            s.rotulo,
            s.horas,
            s.percentual,
            _data(ch.prazo_sla),
            responsavel,
            {"web": "Portal web", "whatsapp": "WhatsApp"}.get(ch.canal, ch.canal),
            _data(ch.criado_em),
            _data(ch.resolvido_em) if not ch.aberto else None,
            pesquisa.get_resposta_display() if pesquisa else "",
            pesquisa.observacao if pesquisa else "",
        )
        for col, valor in enumerate(valores, start=1):
            c = ws.cell(row=linha, column=col)
            if isinstance(valor, str):
                _texto(c, valor)
            else:
                c.value = valor
            if col in (8, 11, 12):
                c.number_format = FORMATO_DATA
            c.alignment = Alignment(vertical="top", wrap_text=col in (3, 14))
        fundo, fonte = CORES_SLA[s.cor]
        celula_sla = ws.cell(row=linha, column=5)
        celula_sla.fill = PatternFill("solid", fgColor=fundo)
        celula_sla.font = Font(bold=True, color=fonte)

    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUNAS))}{max(1, len(chamados) + 1)}"

    saida = BytesIO()
    wb.save(saida)
    return saida.getvalue()
