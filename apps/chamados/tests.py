"""Testes do SLA em horas úteis:  python manage.py test apps.chamados"""
from datetime import datetime
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from . import sla

BOT_TESTE = {"HORARIO_DIAS": [0, 1, 2, 3, 4], "HORARIO_INICIO": "08:00", "HORARIO_FIM": "18:00"}


def hora(dia, h, m=0):
    """2026-11-23 é uma segunda-feira."""
    return timezone.make_aware(datetime(2026, 11, dia, h, m))


def chamado(criado_em, horas, status="em_fila", resolvido_em=None):
    return SimpleNamespace(criado_em=criado_em, sla_horas=horas, prazo_sla=None, resolvido_em=resolvido_em,
                           aberto=status in ("aberto", "em_fila", "em_atendimento", "aguardando_usuario"))


@override_settings(BOT=BOT_TESTE, SLA_PADRAO_HORAS=72)
class HorasUteis(SimpleTestCase):
    def test_soma_dentro_do_mesmo_dia(self):
        self.assertEqual(sla.somar_horas_uteis(hora(23, 9), 8), hora(23, 17))

    def test_soma_passa_para_o_dia_seguinte(self):
        self.assertEqual(sla.somar_horas_uteis(hora(23, 14), 8), hora(24, 12))

    def test_aberto_a_noite_comeca_a_contar_as_8h(self):
        self.assertEqual(sla.somar_horas_uteis(hora(23, 20), 8), hora(24, 16))

    def test_fim_de_semana_nao_conta(self):
        # sexta 27/11 às 16h + 8h úteis = 2h na sexta + 6h na segunda 30/11
        self.assertEqual(sla.somar_horas_uteis(hora(27, 16), 8), hora(30, 14))

    def test_72h_uteis_sao_sete_dias_uteis_e_duas_horas(self):
        self.assertEqual(sla.somar_horas_uteis(hora(23, 8), 72), timezone.make_aware(datetime(2026, 12, 2, 10)))

    def test_horas_entre_descontam_noite_e_fim_de_semana(self):
        self.assertAlmostEqual(sla.horas_uteis_entre(hora(23, 17), hora(24, 9)), 2)
        self.assertAlmostEqual(sla.horas_uteis_entre(hora(27, 17), hora(30, 9)), 2)
        self.assertEqual(sla.horas_uteis_entre(hora(28, 10), hora(29, 15)), 0)  # sábado e domingo


@override_settings(BOT=BOT_TESTE, SLA_PADRAO_HORAS=72)
class Cores(SimpleTestCase):
    def test_verde_antes_da_metade(self):
        s = sla.situacao(chamado(hora(23, 8), 8), agora=hora(23, 11, 59))
        self.assertEqual((s.cor, s.rotulo), (sla.VERDE, "No prazo"))

    def test_amarelo_a_partir_da_metade(self):
        s = sla.situacao(chamado(hora(23, 8), 8), agora=hora(23, 12))
        self.assertEqual((s.cor, s.percentual), (sla.AMARELO, 50))

    def test_vermelho_quando_vence(self):
        s = sla.situacao(chamado(hora(23, 8), 8), agora=hora(23, 16))
        self.assertEqual((s.cor, s.rotulo), (sla.VERMELHO, "Vencido"))
        self.assertIn("vencido há", sla.situacao(chamado(hora(23, 8), 8), agora=hora(23, 17)).texto_restante)

    def test_resolvido_congela_o_sla(self):
        c = chamado(hora(23, 8), 8, status="resolvido", resolvido_em=hora(23, 10))
        s = sla.situacao(c, agora=hora(30, 10))  # uma semana depois continua "cumprido"
        self.assertEqual((s.cor, s.rotulo, s.encerrado), (sla.VERDE, "Cumprido", True))

    def test_resolvido_depois_do_prazo_fica_vencido(self):
        c = chamado(hora(23, 8), 8, status="fechado", resolvido_em=hora(24, 9))
        self.assertEqual(sla.situacao(c).rotulo, "Vencido")
