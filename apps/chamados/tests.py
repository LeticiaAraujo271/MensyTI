"""Testes do SLA em horas úteis:  python manage.py test apps.chamados"""
from datetime import datetime
from types import SimpleNamespace

from django.test import TestCase, override_settings
from django.utils import timezone

from . import sla
from .models import Feriado

BOT_TESTE = {"HORARIO_DIAS": [0, 1, 2, 3, 4], "HORARIO_INICIO": "08:00", "HORARIO_FIM": "18:00"}


def hora(dia, h, m=0):
    """2026-11-23 é uma segunda-feira."""
    return timezone.make_aware(datetime(2026, 11, dia, h, m))


def chamado(criado_em, horas, status="em_fila", resolvido_em=None):
    return SimpleNamespace(criado_em=criado_em, sla_horas=horas, prazo_sla=None, resolvido_em=resolvido_em,
                           aberto=status in ("aberto", "em_fila", "em_atendimento", "aguardando_usuario"))


@override_settings(BOT=BOT_TESTE, SLA_PADRAO_HORAS=72)
class HorasUteis(TestCase):
    def setUp(self):
        Feriado.objects.all().delete()  # os testes definem os próprios feriados
        sla.limpar_cache_feriados()

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
class Cores(TestCase):
    def setUp(self):
        Feriado.objects.all().delete()
        sla.limpar_cache_feriados()

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


@override_settings(BOT=BOT_TESTE, SLA_PADRAO_HORAS=72)
class Feriados(TestCase):
    def setUp(self):
        Feriado.objects.all().delete()
        sla.limpar_cache_feriados()

    def tearDown(self):
        sla.limpar_cache_feriados()  # o rollback do teste não avisa o cache

    def test_feriado_nao_conta_no_prazo(self):
        # quarta 25/11 é feriado: segunda 14h + 24h úteis = 4h seg + 10h ter + (pula qua) + 10h qui
        Feriado.objects.create(data=hora(25, 0).date(), nome="Feriado de teste")
        self.assertEqual(sla.somar_horas_uteis(hora(23, 14), 24), hora(26, 18))

    def test_feriado_nao_conta_nas_horas_consumidas(self):
        Feriado.objects.create(data=hora(24, 0).date(), nome="Feriado de teste")
        self.assertAlmostEqual(sla.horas_uteis_entre(hora(23, 17), hora(25, 9)), 2)

    def test_cadastrar_feriado_no_admin_atualiza_na_hora(self):
        self.assertAlmostEqual(sla.horas_uteis_entre(hora(24, 8), hora(24, 18)), 10)
        f = Feriado.objects.create(data=hora(24, 0).date(), nome="Feriado de teste")
        self.assertAlmostEqual(sla.horas_uteis_entre(hora(24, 8), hora(24, 18)), 0)
        f.delete()
        self.assertAlmostEqual(sla.horas_uteis_entre(hora(24, 8), hora(24, 18)), 10)

    def test_feriados_nacionais(self):
        from datetime import date

        from .feriados_nacionais import feriados_do_ano, pascoa

        self.assertEqual(pascoa(2026), date(2026, 4, 5))
        self.assertEqual(pascoa(2027), date(2027, 3, 28))
        datas = dict(feriados_do_ano(2026))
        self.assertEqual(datas[date(2026, 4, 3)], "Sexta-feira Santa")
        self.assertIn(date(2026, 11, 20), datas)
        self.assertEqual(len(datas), 10)

    def test_migracao_cadastrou_os_feriados_nacionais(self):
        from django.core.management import call_command

        call_command("carregar_feriados", ano=[2026], stdout=__import__("io").StringIO())
        self.assertTrue(Feriado.objects.filter(data=hora(25, 0).date().replace(month=12)).exists())
