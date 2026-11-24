"""
SLA dos chamados, contado em HORAS ÚTEIS.

Horas úteis = a janela de atendimento configurada no .env (BOT_HORARIO_DIAS, BOT_HORARIO_INICIO,
BOT_HORARIO_FIM; padrão: segunda a sexta, das 8h às 18h). Um chamado aberto às 20h começa a contar
às 8h do próximo dia útil. Os FERIADOS cadastrados no Admin (Chamados > Feriados) não contam.

Cores (percentual do SLA já consumido):
  verde     menos da metade
  amarelo   metade ou mais, ainda no prazo
  vermelho  prazo vencido

Solicitações com aprovação (coordenador e gerente): o SLA da TI só começa quando a última
aprovação é dada. Enquanto isso o chamado aparece como "Aguardando aprovação".
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.conf import settings
from django.utils import timezone

VERDE, AMARELO, VERMELHO = "verde", "amarelo", "vermelho"

_cache_feriados: frozenset | None = None


def feriados() -> frozenset:
    """Datas dos feriados cadastrados (em memória; recarrega quando um feriado muda no Admin)."""
    global _cache_feriados
    if _cache_feriados is None:
        from .models import Feriado

        _cache_feriados = frozenset(Feriado.objects.values_list("data", flat=True))
    return _cache_feriados


def limpar_cache_feriados(**kwargs) -> None:
    global _cache_feriados
    _cache_feriados = None


def _janela(cfg: dict | None = None):
    cfg = cfg or settings.BOT
    return (set(cfg["HORARIO_DIAS"]), time.fromisoformat(cfg["HORARIO_INICIO"]),
            time.fromisoformat(cfg["HORARIO_FIM"]))


def _expediente(dia, inicio: time, fim: time, tz):
    return (timezone.make_aware(datetime.combine(dia, inicio), tz),
            timezone.make_aware(datetime.combine(dia, fim), tz))


def somar_horas_uteis(inicio: datetime, horas: float, cfg: dict | None = None,
                      dias_sem_expediente=None) -> datetime:
    """Data/hora em que se completam `horas` úteis a partir de `inicio`."""
    dias, h_ini, h_fim = _janela(cfg)
    fechados = feriados() if dias_sem_expediente is None else dias_sem_expediente
    if not dias or h_fim <= h_ini:
        return inicio + timedelta(hours=horas)
    tz = timezone.get_current_timezone()
    atual = timezone.localtime(inicio, tz)
    restante = timedelta(hours=horas)
    dia = atual.date()
    for _ in range(3660):  # limite de segurança: 10 anos
        if dia.weekday() in dias and dia not in fechados:
            abre, fecha = _expediente(dia, h_ini, h_fim, tz)
            comeco = max(atual, abre)
            if comeco < fecha:
                disponivel = fecha - comeco
                if restante <= disponivel:
                    return comeco + restante
                restante -= disponivel
        dia += timedelta(days=1)
    return atual + restante


def horas_uteis_entre(inicio: datetime, fim: datetime, cfg: dict | None = None,
                      dias_sem_expediente=None) -> float:
    """Quantas horas úteis passaram entre `inicio` e `fim`."""
    if fim <= inicio:
        return 0.0
    dias, h_ini, h_fim = _janela(cfg)
    fechados = feriados() if dias_sem_expediente is None else dias_sem_expediente
    if not dias or h_fim <= h_ini:
        return (fim - inicio).total_seconds() / 3600
    tz = timezone.get_current_timezone()
    inicio, fim = timezone.localtime(inicio, tz), timezone.localtime(fim, tz)
    total = timedelta()
    dia = inicio.date()
    while dia <= fim.date():
        if dia.weekday() in dias and dia not in fechados:
            abre, fecha = _expediente(dia, h_ini, h_fim, tz)
            a, b = max(inicio, abre), min(fim, fecha)
            if b > a:
                total += b - a
        dia += timedelta(days=1)
    return total.total_seconds() / 3600


def sla_da_categoria(nome_categoria: str) -> int:
    """SLA (horas úteis) cadastrado na categoria; sem categoria, vale o padrão (Outros = 72h)."""
    from apps.orientacoes.models import Categoria

    padrao = settings.SLA_PADRAO_HORAS
    if not nome_categoria:
        return padrao
    cat = Categoria.objects.filter(nome=nome_categoria).only("sla_horas").first()
    return cat.sla_horas if cat and cat.sla_horas else padrao


@dataclass(frozen=True)
class SituacaoSLA:
    cor: str                # verde | amarelo | vermelho
    horas: int              # SLA da categoria
    consumidas: float       # horas úteis já usadas
    prazo: datetime | None
    encerrado: bool         # chamado resolvido/fechado: SLA congelado no momento da solução
    aguardando_aprovacao: bool = False  # o SLA ainda não começou

    @property
    def percentual(self) -> int:
        return min(999, round(100 * self.consumidas / self.horas)) if self.horas else 0

    @property
    def restantes(self) -> float:
        return max(0.0, self.horas - self.consumidas)

    @property
    def rotulo(self) -> str:
        if self.aguardando_aprovacao:
            return "Aguardando aprovação"
        if self.encerrado:
            return "Cumprido" if self.cor != VERMELHO else "Vencido"
        return {VERDE: "No prazo", AMARELO: "Atenção", VERMELHO: "Vencido"}[self.cor]

    @property
    def texto_restante(self) -> str:
        if self.aguardando_aprovacao:
            return "o SLA começa depois da aprovação"
        if self.cor == VERMELHO:
            return f"vencido há {_horas(self.consumidas - self.horas)} úteis"
        return f"faltam {_horas(self.restantes)} úteis"


def situacao(chamado, agora: datetime | None = None) -> SituacaoSLA:
    horas = chamado.sla_horas or settings.SLA_PADRAO_HORAS
    encerrado = not chamado.aberto and chamado.resolvido_em is not None
    inicio = getattr(chamado, "inicio_sla", chamado.criado_em)
    if inicio is None:  # aguardando aprovação (ou reprovado): o SLA da TI não começou
        return SituacaoSLA(cor=VERDE, horas=horas, consumidas=0.0, prazo=None, encerrado=encerrado,
                           aguardando_aprovacao=not encerrado)
    fim = chamado.resolvido_em if encerrado else (agora or timezone.now())
    consumidas = horas_uteis_entre(inicio, fim)
    if consumidas >= horas:
        cor = VERMELHO
    elif consumidas >= horas / 2:
        cor = AMARELO
    else:
        cor = VERDE
    return SituacaoSLA(cor=cor, horas=horas, consumidas=consumidas, prazo=chamado.prazo_sla,
                       encerrado=encerrado)


def _horas(h: float) -> str:
    minutos = round(h * 60)
    if minutos < 60:
        return f"{minutos}min"
    hh, mm = divmod(minutos, 60)
    return f"{hh}h{mm:02d}" if mm else f"{hh}h"
