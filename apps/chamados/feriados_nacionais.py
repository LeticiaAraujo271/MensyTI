"""
Feriados nacionais do Brasil (lei federal), usados para descontar o SLA.

Pontos facultativos (Carnaval, Quarta-feira de Cinzas, Corpus Christi) e feriados estaduais e
municipais NÃO entram aqui: se a empresa não trabalha nesses dias, cadastre no Admin
(Chamados > Feriados).
"""
from datetime import date, timedelta

FIXOS = (
    (1, 1, "Confraternização Universal"),
    (4, 21, "Tiradentes"),
    (5, 1, "Dia do Trabalho"),
    (9, 7, "Independência do Brasil"),
    (10, 12, "Nossa Senhora Aparecida"),
    (11, 2, "Finados"),
    (11, 15, "Proclamação da República"),
    (11, 20, "Dia Nacional de Zumbi e da Consciência Negra"),
    (12, 25, "Natal"),
)


def pascoa(ano: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher, calendário gregoriano)."""
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(ano, mes, dia)


def feriados_do_ano(ano: int) -> list[tuple[date, str]]:
    lista = [(date(ano, mes, dia), nome) for mes, dia, nome in FIXOS]
    lista.append((pascoa(ano) - timedelta(days=2), "Sexta-feira Santa"))
    return sorted(lista)
