"""
Exportação dos chamados para Excel (.xlsx), usada pelo botão "Exportar Excel" da fila.

A planilha tem duas abas:
  Dashboard  indicadores e gráficos nas cores Mensori, com filtros (qualidade do atendimento,
             situação do SLA e status) que recalculam tudo na hora, dentro do próprio Excel
  Chamados   a lista completa (uma linha por chamado), com filtro em cada coluna

Os números do Dashboard são fórmulas (CONT.SES) sobre a aba Chamados: o Excel recalcula ao abrir
e sempre que um filtro muda. Não usa macros.
"""
from __future__ import annotations

from collections import Counter
from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.chart import BarChart, DoughnutChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.series import DataPoint
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.pagebreak import Break
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.worksheet.table import Table, TableStyleInfo

from apps.chamados import sla
from apps.chamados.models import Chamado, PesquisaSatisfacao

# --- Paleta Mensori ---------------------------------------------------------------------------
VERDE = "00564F"
VERDE_ESCURO = "003C38"
VERDE_MEDIO = "3F9A90"
VERDE_CLARO = "DCEBE9"
CINZA_FUNDO = "F3F5F5"
CINZA_TEXTO = "5E6665"
BORDA = "DDE3E2"
BRANCO = "FFFFFF"
PRETO = "111315"
FONTE = "Calibri"

SEM_RESPOSTA = "Sem resposta"
SEM_CENTRO = "Não informado"
QUALIDADES = tuple(PesquisaSatisfacao.Resposta.labels) + (SEM_RESPOSTA,)
CORES_QUALIDADE = {
    "Muito satisfeito": VERDE, "Satisfeito": "7FC3BA", "Insatisfeito": "F79009",
    "Muito insatisfeito": "B42318", SEM_RESPOSTA: "C4CBCA",
}
SITUACOES_SLA = ("No prazo", "Atenção", "Vencido", "Cumprido")
CORES_SITUACAO = {"No prazo": VERDE_MEDIO, "Atenção": "E2A100", "Vencido": "B42318", "Cumprido": VERDE}
STATUS = tuple(Chamado.Status.labels)
STATUS_ABERTOS = tuple(Chamado.Status(s).label for s in Chamado.ABERTOS)

# --- Aba Chamados -----------------------------------------------------------------------------
# (título da coluna, largura)
COLUNAS = (
    ("Número do chamado", 18),
    ("Colaborador", 26),
    ("Centro de custo", 20),
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
COLUNAS_DATA = {"Prazo do SLA", "Aberto em", "Data do fechamento"}
COLUNAS_QUEBRA = {"Assunto", "Observação da pesquisa"}  # textos longos quebram a linha

fino = Side(style="thin", color=BORDA)
BORDA_FINA = Border(left=fino, right=fino, top=fino, bottom=fino)


def _coluna(titulo: str) -> int:
    return next(i for i, (t, _) in enumerate(COLUNAS, start=1) if t == titulo)


def _letra(titulo: str) -> str:
    return get_column_letter(_coluna(titulo))


def _data(valor):
    """O Excel não guarda fuso: grava no horário de Brasília (o mesmo que aparece no painel)."""
    return timezone.localtime(valor).replace(tzinfo=None) if valor else None


def _texto(celula, valor: str) -> None:
    # Texto digitado pelo colaborador sempre como texto (nunca como fórmula, ex.: "=HIPERLINK(...)").
    celula.value = valor
    celula.data_type = "s"


def _linha_do_chamado(ch) -> tuple:
    s = ch.sla
    pesquisa = next(iter(ch.pesquisas.all()), None)  # a mais recente (já vem ordenada)
    responsavel = ""
    if ch.responsavel:
        responsavel = ch.responsavel.get_full_name() or ch.responsavel.get_username()
    return (
        ch.protocolo or "",
        ch.nome_colaborador,
        ch.centro_custo or SEM_CENTRO,
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
        pesquisa.get_resposta_display() if pesquisa else SEM_RESPOSTA,
        pesquisa.observacao if pesquisa else "",
    ), s.cor


def _aba_chamados(ws, linhas) -> None:
    ws.title = "Chamados"
    ws.sheet_properties.tabColor = VERDE_MEDIO
    for i, (titulo, largura) in enumerate(COLUNAS, start=1):
        c = ws.cell(row=1, column=i, value=titulo)
        c.font = Font(name=FONTE, bold=True, color=BRANCO)
        c.fill = PatternFill("solid", fgColor=VERDE_ESCURO)
        c.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = largura
    ws.row_dimensions[1].height = 32

    for linha, (valores, cor) in enumerate(linhas, start=2):
        for (titulo, _), col, valor in zip(COLUNAS, range(1, len(COLUNAS) + 1), valores):
            c = ws.cell(row=linha, column=col)
            if isinstance(valor, str):
                _texto(c, valor)
            else:
                c.value = valor
            if titulo in COLUNAS_DATA:
                c.number_format = FORMATO_DATA
            c.alignment = Alignment(vertical="top", wrap_text=titulo in COLUNAS_QUEBRA)
        fundo, fonte = CORES_SLA[cor]
        celula_sla = ws.cell(row=linha, column=_coluna("SLA"))
        celula_sla.fill = PatternFill("solid", fgColor=fundo)
        celula_sla.font = Font(name=FONTE, bold=True, color=fonte)

    ws.freeze_panes = "B2"
    ultima = get_column_letter(len(COLUNAS))
    if linhas:
        tabela = Table(displayName="TabelaChamados", ref=f"A1:{ultima}{len(linhas) + 1}")
        tabela.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
        ws.add_table(tabela)
    else:
        ws.auto_filter.ref = f"A1:{ultima}1"


# --- Aba Dashboard ----------------------------------------------------------------------------
PRIMEIRA, ULTIMA = 2, 16  # colunas B..P
FILTROS = (  # (rótulo, coluna da aba Chamados, opções, colunas do rótulo, colunas da lista)
    ("Qualidade do atendimento", "Pesquisa de satisfação", ("Todas",) + QUALIDADES, (2, 3), (4, 6)),
    ("Situação do SLA", "SLA", ("Todas",) + SITUACOES_SLA, (7, 8), (9, 11)),
    ("Status", "Status", ("Todos",) + STATUS, (12, 13), (14, 16)),
)
COL_AUX = 18  # coluna R (oculta): critérios dos filtros
LINHA_FILTRO = 5


def _rotulos(valor=False, percentual=False, posicao=None) -> DataLabelList:
    """Rótulos só com o número (ou o %): o Excel mostra tudo o que não estiver desligado."""
    rot = DataLabelList(showVal=valor, showPercent=percentual, showSerName=False, showCatName=False,
                        showLegendKey=False, showLeaderLines=False)
    if posicao:
        rot.dLblPos = posicao
    rot.txPr = None
    return rot


class _Dashboard:
    def __init__(self, ws, total_linhas: int):
        self.ws = ws
        self.ultima_linha = max(2, total_linhas + 1)
        ws.title = "Dashboard"
        ws.sheet_properties.tabColor = VERDE
        ws.sheet_view.showGridLines = False
        ws.sheet_view.zoomScale = 90
        ws.column_dimensions["A"].width = 2
        for c in range(PRIMEIRA, ULTIMA + 1):
            ws.column_dimensions[get_column_letter(c)].width = 11.5
        ws.column_dimensions["Q"].width = 2
        ws.column_dimensions[get_column_letter(COL_AUX)].hidden = True

    # -- auxiliares de fórmula --
    def faixa(self, titulo: str) -> str:
        letra = _letra(titulo)
        return f"Chamados!${letra}$2:${letra}${self.ultima_linha}"

    def criterios(self) -> str:
        aux = get_column_letter(COL_AUX)
        return ",".join(f"{self.faixa(campo)},${aux}${LINHA_FILTRO + i}"
                        for i, (_, campo, *_r) in enumerate(FILTROS))

    def contar(self, *extras: tuple[str, str]) -> str:
        partes = [self.criterios()] + [f"{self.faixa(campo)},{criterio}" for campo, criterio in extras]
        return f"COUNTIFS({','.join(partes)})"

    # -- blocos visuais --
    def mesclar(self, linha, c1, c2, valor=None, *, fonte=None, fundo=None, alinhar="left", linha2=None):
        ws = self.ws
        linha2 = linha2 or linha
        ws.merge_cells(start_row=linha, start_column=c1, end_row=linha2, end_column=c2)
        c = ws.cell(row=linha, column=c1)
        if valor is not None:
            c.value = valor
        if fonte:
            c.font = fonte
        if fundo:
            for r in range(linha, linha2 + 1):
                for col in range(c1, c2 + 1):
                    ws.cell(row=r, column=col).fill = PatternFill("solid", fgColor=fundo)
        c.alignment = Alignment(horizontal=alinhar, vertical="center", wrap_text=True)
        return c

    def cabecalho(self, total: int) -> None:
        ws = self.ws
        self.mesclar(1, PRIMEIRA, ULTIMA, "Central de TI  ·  Dashboard de chamados", linha2=2,
                     fonte=Font(name=FONTE, size=20, bold=True, color=BRANCO), fundo=VERDE_ESCURO)
        ws.row_dimensions[1].height = 24
        ws.row_dimensions[2].height = 24
        agora = timezone.localtime()
        self.mesclar(3, PRIMEIRA, ULTIMA,
                     f"Exportado em {agora:%d/%m/%Y às %H:%M}  ·  {total} chamado(s) na exportação  ·  "
                     "Escolha os filtros nos campos verdes: os números e os gráficos se atualizam.",
                     fonte=Font(name=FONTE, size=10, italic=True, color=CINZA_TEXTO))

    def filtros(self) -> None:
        ws = self.ws
        aux = get_column_letter(COL_AUX)
        for i, (rotulo, _campo, opcoes, (r1, r2), (l1, l2)) in enumerate(FILTROS):
            self.mesclar(LINHA_FILTRO, r1, r2, rotulo, alinhar="right",
                         fonte=Font(name=FONTE, size=10, bold=True, color=VERDE_ESCURO))
            lista = self.mesclar(LINHA_FILTRO, l1, l2, opcoes[0], alinhar="center",
                                 fonte=Font(name=FONTE, size=11, bold=True, color=VERDE), fundo=VERDE_CLARO)
            for col in range(l1, l2 + 1):
                ws.cell(row=LINHA_FILTRO, column=col).border = Border(
                    top=Side(style="thin", color=VERDE), bottom=Side(style="medium", color=VERDE),
                    left=Side(style="thin", color=VERDE) if col == l1 else None,
                    right=Side(style="thin", color=VERDE) if col == l2 else None)
            dv = DataValidation(type="list", formula1='"' + ",".join(opcoes) + '"', allow_blank=False,
                                showDropDown=False, promptTitle=rotulo, prompt="Escolha uma opção da lista.")
            dv.error, dv.errorTitle = "Escolha uma opção da lista.", rotulo
            ws.add_data_validation(dv)
            dv.add(lista.coordinate)
            # Critério do CONT.SES: "Todas"/"Todos" vira "*" (qualquer valor).
            ref = lista.coordinate
            ws[f"{aux}{LINHA_FILTRO + i}"] = f'=IF(OR({ref}="Todas",{ref}="Todos",{ref}=""),"*",{ref})'
        ws.row_dimensions[LINHA_FILTRO].height = 24

    def indicadores(self, linha: int) -> dict:
        ws = self.ws
        cartoes = (
            ("Chamados", f"={self.contar()}", "0", "no filtro escolhido"),
            ("Em aberto", "=" + "+".join(self.contar(("Status", f'"{s}"')) for s in STATUS_ABERTOS),
             "0", "aguardando solução"),
            ("SLA vencido", f'={self.contar(("SLA", chr(34) + "Vencido" + chr(34)))}', "0", "prazo estourado"),
            ("Pesquisas respondidas", f'={self.contar(("Pesquisa de satisfação", chr(34) + "<>" + SEM_RESPOSTA + chr(34)))}',
             "0", "com avaliação do colaborador"),
            ("Satisfação", None, "0%", "satisfeitos + muito satisfeitos"),
        )
        refs = {}
        for i, (rotulo, formula, formato, legenda) in enumerate(cartoes):
            c1 = PRIMEIRA + i * 3
            c2 = c1 + 2
            for r in range(linha, linha + 4):
                for col in range(c1, c2 + 1):
                    cel = ws.cell(row=r, column=col)
                    cel.fill = PatternFill("solid", fgColor=CINZA_FUNDO)
                    cel.border = Border(top=Side(style="thick", color=VERDE) if r == linha else None)
            self.mesclar(linha, c1, c2, rotulo.upper(),
                         fonte=Font(name=FONTE, size=9, bold=True, color=CINZA_TEXTO))
            valor = self.mesclar(linha + 1, c1, c2, linha2=linha + 2,
                                 fonte=Font(name=FONTE, size=26, bold=True, color=VERDE))
            if formula:
                valor.value = formula
            valor.number_format = formato
            refs[rotulo] = valor.coordinate
            self.mesclar(linha + 3, c1, c2, legenda, fonte=Font(name=FONTE, size=9, color=CINZA_TEXTO))
        satisfeitos = "+".join(self.contar(("Pesquisa de satisfação", f'"{q}"'))
                               for q in ("Muito satisfeito", "Satisfeito"))
        ws[refs["Satisfação"]] = f'=IFERROR(({satisfeitos})/{refs["Pesquisas respondidas"]},0)'
        for r, altura in zip(range(linha, linha + 4), (18, 22, 22, 16)):
            ws.row_dimensions[r].height = altura
        return refs

    def titulo_secao(self, linha: int, texto: str, subtitulo: str = "") -> None:
        ws = self.ws
        self.mesclar(linha, PRIMEIRA, ULTIMA, texto, fonte=Font(name=FONTE, size=14, bold=True, color=VERDE_ESCURO))
        for col in range(PRIMEIRA, ULTIMA + 1):
            ws.cell(row=linha, column=col).border = Border(bottom=Side(style="medium", color=VERDE))
        ws.row_dimensions[linha].height = 24
        if subtitulo:
            self.mesclar(linha + 1, PRIMEIRA, ULTIMA, subtitulo,
                         fonte=Font(name=FONTE, size=9, italic=True, color=CINZA_TEXTO))

    def cabecalho_tabela(self, linha: int, colunas: list[tuple[int, int, str]]) -> None:
        for c1, c2, texto in colunas:
            cel = self.mesclar(linha, c1, c2, texto, alinhar="center" if c1 > PRIMEIRA else "left",
                               fonte=Font(name=FONTE, size=10, bold=True, color=BRANCO), fundo=VERDE)
            cel.border = BORDA_FINA

    def tabela_contagem(self, linha: int, rotulo: str, campo: str, itens, total_ref: str) -> tuple[int, int]:
        """Tabela item | chamados | % (colunas B-D, E, F). Devolve (primeira, última) linha de dados."""
        ws = self.ws
        self.cabecalho_tabela(linha, [(2, 4, rotulo), (5, 5, "Chamados"), (6, 6, "% do total")])
        for i, item in enumerate(itens, start=1):
            r = linha + i
            nome = self.mesclar(r, 2, 4, fonte=Font(name=FONTE, size=10, color=PRETO),
                                fundo=CINZA_FUNDO if i % 2 == 0 else None)
            _texto(nome, item)
            qtd = ws.cell(row=r, column=5, value=f"={self.contar((campo, f'$B${r}'))}")
            qtd.font = Font(name=FONTE, size=10, bold=True, color=VERDE_ESCURO)
            qtd.alignment = Alignment(horizontal="center")
            pct = ws.cell(row=r, column=6, value=f"=IFERROR(E{r}/{total_ref},0)")
            pct.number_format = "0%"
            pct.font = Font(name=FONTE, size=10, color=CINZA_TEXTO)
            pct.alignment = Alignment(horizontal="center")
            for col in (5, 6):
                if i % 2 == 0:
                    ws.cell(row=r, column=col).fill = PatternFill("solid", fgColor=CINZA_FUNDO)
        primeira, ultima = linha + 1, linha + max(1, len(itens))
        ws.conditional_formatting.add(f"E{primeira}:E{ultima}",
                                      DataBarRule(start_type="num", start_value=0, end_type="max",
                                                  color=VERDE_MEDIO, showValue=True))
        return primeira, ultima

    def grafico_barras(self, cabecalho: int, primeira: int, ultima: int, ancora: str, cores=None,
                       altura=None) -> None:
        ch = BarChart()
        ch.type = "bar"
        ch.style = 10
        ch.legend = None
        ch.gapWidth = 55
        ch.add_data(Reference(self.ws, min_col=5, min_row=cabecalho, max_row=ultima), titles_from_data=True)
        ch.set_categories(Reference(self.ws, min_col=2, min_row=primeira, max_row=ultima))
        serie = ch.series[0]
        serie.graphicalProperties.solidFill = VERDE
        serie.graphicalProperties.line.solidFill = VERDE
        if cores:
            for i, cor in enumerate(cores):
                pt = DataPoint(idx=i)
                pt.graphicalProperties.solidFill = cor
                pt.graphicalProperties.line.solidFill = cor
                serie.dPt.append(pt)
        ch.dataLabels = _rotulos(valor=True, posicao="outEnd")
        ch.x_axis.scaling.orientation = "maxMin"  # mesma ordem da tabela (maior em cima)
        ch.x_axis.delete = False
        ch.y_axis.delete = True
        ch.y_axis.majorGridlines = None
        ch.width = 17.5
        ch.height = altura or max(6.5, 1.0 + 0.62 * (ultima - primeira + 1))
        self.ws.add_chart(ch, ancora)

    def grafico_rosca(self, cabecalho: int, primeira: int, ultima: int, ancora: str, cores) -> None:
        ch = DoughnutChart(holeSize=55)
        ch.style = 10
        ch.add_data(Reference(self.ws, min_col=5, min_row=cabecalho, max_row=ultima), titles_from_data=True)
        ch.set_categories(Reference(self.ws, min_col=2, min_row=primeira, max_row=ultima))
        serie = ch.series[0]
        for i, cor in enumerate(cores):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = cor
            pt.graphicalProperties.line.solidFill = BRANCO
            serie.dPt.append(pt)
        ch.dataLabels = _rotulos(percentual=True)
        ch.legend.position = "r"
        ch.width = 17.5
        ch.height = 7.5
        self.ws.add_chart(ch, ancora)

    def matriz(self, linha: int, centros) -> int:
        """Qualidade do atendimento (colunas) x centro de custo (linhas)."""
        ws = self.ws
        colunas = [(2, 4, "Centro de custo")]
        colunas += [(5 + 2 * i, 6 + 2 * i, q) for i, q in enumerate(QUALIDADES)]
        colunas += [(15, 16, "Total")]
        self.cabecalho_tabela(linha, colunas)
        ws.row_dimensions[linha].height = 30
        for i, centro in enumerate(centros, start=1):
            r = linha + i
            fundo = CINZA_FUNDO if i % 2 == 0 else None
            _texto(self.mesclar(r, 2, 4, fonte=Font(name=FONTE, size=10), fundo=fundo), centro)
            for j, q in enumerate(QUALIDADES):
                c = self.mesclar(r, 5 + 2 * j, 6 + 2 * j, alinhar="center", fonte=Font(name=FONTE, size=10))
                c.value = f'={self.contar(("Centro de custo", f"$B${r}"), ("Pesquisa de satisfação", chr(34) + q + chr(34)))}'
            total = self.mesclar(r, 15, 16, alinhar="center", fonte=Font(name=FONTE, size=10, bold=True, color=VERDE_ESCURO),
                                 fundo=fundo)
            total.value = f"=SUM(E{r}:N{r})"
        primeira, ultima = linha + 1, linha + max(1, len(centros))
        verde = ColorScaleRule(start_type="num", start_value=0, start_color=BRANCO, end_type="max", end_color="7FC3BA")
        vermelho = ColorScaleRule(start_type="num", start_value=0, start_color=BRANCO, end_type="max", end_color="F9B4AE")
        ws.conditional_formatting.add(f"E{primeira}:H{ultima}", verde)
        ws.conditional_formatting.add(f"I{primeira}:L{ultima}", vermelho)
        return ultima


def planilha_chamados(chamados) -> bytes:
    linhas = [_linha_do_chamado(ch) for ch in chamados]
    wb = Workbook()
    painel = wb.active
    dados = wb.create_sheet("Chamados")
    _aba_chamados(dados, linhas)

    d = _Dashboard(painel, len(linhas))
    d.cabecalho(len(linhas))
    d.filtros()
    refs = d.indicadores(7)
    total = refs["Chamados"]

    def ordenados(indice: int) -> list[str]:
        return [nome for nome, _ in Counter(v[indice] for v, _ in linhas).most_common()] or [SEM_CENTRO]

    i_centro = _coluna("Centro de custo") - 1
    i_assunto = _coluna("Assunto") - 1
    centros, assuntos = ordenados(i_centro), ordenados(i_assunto)

    linha = 13
    d.titulo_secao(linha, "Chamados por centro de custo", "Quantidade de chamados de cada centro de custo, "
                   "conforme os filtros acima.")
    cab = linha + 2
    p, u = d.tabela_contagem(cab, "Centro de custo", "Centro de custo", centros, total)
    d.grafico_barras(cab, p, u, f"H{cab}")
    linha = max(u, cab + 13) + 3

    painel.row_breaks.append(Break(id=linha - 1))  # impressão: cada página com seções inteiras
    d.titulo_secao(linha, "Qualidade do atendimento", "Respostas da pesquisa de satisfação enviada ao resolver "
                   "o chamado.")
    cab = linha + 2
    p, u = d.tabela_contagem(cab, "Avaliação", "Pesquisa de satisfação", QUALIDADES, total)
    d.grafico_rosca(cab, p, u, f"H{cab}", [CORES_QUALIDADE[q] for q in QUALIDADES])
    linha = max(u, cab + 14) + 3

    d.titulo_secao(linha, "Situação do SLA", "No prazo: menos da metade do SLA · Atenção: metade ou mais · "
                   "Vencido: prazo estourado · Cumprido: resolvido dentro do prazo.")
    cab = linha + 2
    p, u = d.tabela_contagem(cab, "Situação", "SLA", SITUACOES_SLA, total)
    d.grafico_rosca(cab, p, u, f"H{cab}", [CORES_SITUACAO[s] for s in SITUACOES_SLA])
    linha = max(u, cab + 14) + 3

    painel.row_breaks.append(Break(id=linha - 1))
    d.titulo_secao(linha, "Chamados por assunto")
    cab = linha + 2
    p, u = d.tabela_contagem(cab, "Assunto", "Assunto", assuntos, total)
    d.grafico_barras(cab, p, u, f"H{cab}")
    linha = max(u, cab + 13) + 3

    d.titulo_secao(linha, "Qualidade do atendimento por centro de custo",
                   "Quantas avaliações de cada tipo cada centro de custo deu. Verde: satisfeitos; "
                   "vermelho: insatisfeitos.")
    d.matriz(linha + 2, centros)

    painel.print_options.horizontalCentered = True
    painel.page_setup.orientation = "landscape"
    painel.page_setup.fitToWidth = 1
    painel.page_setup.fitToHeight = 0
    painel.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    wb.active = 0
    wb.calculation.fullCalcOnLoad = True  # o Excel calcula as fórmulas ao abrir

    saida = BytesIO()
    wb.save(saida)
    return saida.getvalue()
