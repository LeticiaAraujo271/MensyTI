"""
SLA dos chamados, contado em HORAS ÚTEIS.

Horas úteis = a janela de atendimento configurada no .env (BOT_HORARIO_DIAS, BOT_HORARIO_INICIO,
BOT_HORARIO_FIM; padrão: segunda a sexta, das 8h às 18h). Um chamado aberto às 20h começa a contar
às 8h do próximo dia útil. Feriados ainda não são descontados.

Cores (percentual do SLA já consumido):
  verde     menos da metade
  amarelo   metade ou mais, ainda no prazo
  vermelho  prazo vencido
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.conf import settings
from django.utils import timezone

VERDE, AMARELO, VERMELHO = "verde", "amarelo", "vermelho"


def _janela(cfg: dict | None = None):
    cfg = cfg or settings.BOT
    return (set(cfg["HORARIO_DIAS"]), time.fromisoformat(cfg["HORARIO_INICIO"]),
            time.fromisoformat(cfg["HORARIO_FIM"]))


def _expediente(dia, inicio: time, fim: time, tz):
    return (timezone.make_aware(datetime.combine(dia, inicio), tz),
            timezone.make_aware(datetime.combine(dia, fim), tz))


def somar_horas_uteis(inicio: datetime, horas: float, cfg: dict | None = None) -> datetime:
    """Data/hora em que se completam `horas` úteis a partir de `inicio`."""
    dias, h_ini, h_fim = _janela(cfg)
    if not dias or h_fim <= h_ini:
        return inicio + timedelta(hours=horas)
    tz = timezone.get_current_timezone()
    atual = timezone.localtime(inicio, tz)
    restante = timedelta(hours=horas)
    dia = atual.date()
    for _ in range(3660):  # limite de segurança: 10 anos
        if dia.weekday() in dias:
            abre, fecha = _expediente(dia, h_ini, h_fim, tz)
            comeco = max(atual, abre)
            if comeco < fecha:
                disponivel = fecha - comeco
                if restante <= disponivel:
                    return comeco + restante
                restante -= disponivel
        dia += timedelta(days=1)
    return atual + restante


def horas_uteis_entre(inicio: datetime, fim: datetime, cfg: dict | None = None) -> float:
    """Quantas horas úteis passaram entre `inicio` e `fim`."""
    if fim <= inicio:
        return 0.0
    dias, h_ini, h_fim = _janela(cfg)
    if not dias or h_fim <= h_ini:
        return (fim - inicio).total_seconds() / 3600
    tz = timezone.get_current_timezone()
    inicio, fim = timezone.localtime(inicio, tz), timezone.localtime(fim, tz)
    total = timedelta()
    dia = inicio.date()
    while dia <= fim.date():
        if dia.weekday() in dias:
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

    @property
    def percentual(self) -> int:
        return min(999, round(100 * self.consumidas / self.horas)) if self.horas else 0

    @property
    def restantes(self) -> float:
        return max(0.0, self.horas - self.consumidas)

    @property
    def rotulo(self) -> str:
        if self.encerrado:
            return "Cumprido" if self.cor != VERMELHO else "Vencido"
        return {VERDE: "No prazo", AMARELO: "Atenção", VERMELHO: "Vencido"}[self.cor]

    @property
    def texto_restante(self) -> str:
        if self.cor == VERMELHO:
            return f"vencido há {_horas(self.consumidas - self.horas)} úteis"
        return f"faltam {_horas(self.restantes)} úteis"


def situacao(chamado, agora: datetime | None = None) -> SituacaoSLA:
    horas = chamado.sla_horas or settings.SLA_PADRAO_HORAS
    encerrado = not chamado.aberto and chamado.resolvido_em is not None
    fim = chamado.resolvido_em if encerrado else (agora or timezone.now())
    consumidas = horas_uteis_entre(chamado.criado_em, fim)
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
