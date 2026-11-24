"""Testes de integração do orquestrador (banco + chamados + canais):  python manage.py test apps"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.bot import engine
from apps.bot.models import Avaliacao, Colaborador, Conversa, Mensagem, OrientacaoVista
from apps.bot.orquestrador import ConversationOrchestrator
from apps.canais import WebChannel, WhatsAppChannel
from apps.chamados.models import Chamado, PesquisaSatisfacao
from apps.chamados.servicos import TicketService

CENTRAL_TESTE = {"NOME": "Central de TI", "IDENTIFICACAO": ["nome", "setor", "email"],
                 "DOMINIOS_EMAIL": [], "LIMITE_MENSAGENS_MINUTO": 100}
IDENT = ("oi", "Maria Silva", "Financeiro", "maria@empresa.com.br")


class HorarioFixo:
    def __init__(self, dentro=True):
        self.dentro = dentro

    def dentro_do_horario(self, agora=None):
        return self.dentro

    def texto(self):
        return "segunda a sexta, das 8h às 18h"


class ClienteQuebrado:
    def enviar_texto(self, contato_id, texto):
        raise ConnectionError("provedor fora do ar")


@override_settings(CENTRAL=CENTRAL_TESTE, WHATSAPP_ATIVO=False)
class OrquestradorTest(TestCase):
    def setUp(self):
        call_command("popular_orientacoes", verbosity=0)
        self.orq = ConversationOrchestrator(WebChannel(), horario=HorarioFixo(True))

    def falar(self, *textos, ident="u1", orq=None):
        respostas = None
        for t in textos:
            respostas = (orq or self.orq).receber(ident, t)
        return respostas

    def conversa(self, ident="u1"):
        return Conversa.objects.filter(identificador=ident).order_by("-criada_em").first()

    # --- ramos do BPMN ----------------------------------------------------
    def test_resolvido_registra_avaliacao_e_encerra(self):
        self.falar(*IDENT, "3", "1", "1", "5")
        c = self.conversa()
        self.assertFalse(c.ativa)
        self.assertEqual(c.resultado, Conversa.Resultado.RESOLVIDA)
        self.assertEqual(Avaliacao.objects.get().nota, 5)
        self.assertTrue(OrientacaoVista.objects.get().resolveu)
        self.assertEqual(c.colaborador.email, "maria@empresa.com.br")
        self.assertFalse(Chamado.objects.exists())

    def test_nao_resolvido_abre_chamado_com_protocolo(self):
        respostas = self.falar(*IDENT, "3", "1", "2", "Cabo conectado e continua sem rede")
        ch = Chamado.objects.get()
        self.assertTrue(ch.protocolo.startswith("TI-"))
        self.assertIn(ch.protocolo, respostas[-1])
        self.assertEqual(ch.status, Chamado.Status.EM_FILA)
        self.assertEqual(ch.prioridade, Chamado.Prioridade.MEDIA)
        self.assertEqual(ch.categoria, "Internet, rede e VPN")
        self.assertEqual(ch.descricao, "Cabo conectado e continua sem rede")
        self.assertEqual((ch.nome_colaborador, ch.setor, ch.contato),
                         ("Maria Silva", "Financeiro", "maria@empresa.com.br"))
        self.assertIn("Estou sem internet", ch.resumo)
        self.assertEqual(ch.colaborador, Colaborador.objects.get())
        self.assertFalse(OrientacaoVista.objects.get().resolveu)
        self.assertEqual(self.conversa().etapa, engine.HUMANO)
        self.assertEqual(self.conversa().resultado, Conversa.Resultado.ESCALADA)
        self.assertTrue(ch.eventos.filter(tipo="aberto").exists())

    def test_incidente_critico_tem_prioridade_critica(self):
        self.falar(*IDENT, "8", "1")
        ch = Chamado.objects.get()
        self.assertEqual(ch.prioridade, Chamado.Prioridade.CRITICA)
        self.assertFalse(self.conversa().orientacoes_vistas.filter(resolveu=True).exists())

    def test_fora_do_horario_fica_na_fila_sem_perder_mensagens(self):
        orq = ConversationOrchestrator(WebChannel(), horario=HorarioFixo(False))
        respostas = self.falar(*IDENT, "0", "Notebook não liga desde ontem", orq=orq)
        ch = Chamado.objects.get()
        self.assertTrue(ch.fora_do_horario)
        self.assertEqual(ch.status, Chamado.Status.EM_FILA)
        self.assertIn("fora do horário", respostas[-1])
        self.assertIn("segunda a sexta", respostas[-1])
        # O colaborador continua escrevendo: tudo vai para o chamado, nada se perde.
        self.assertEqual(self.falar("Esqueci de dizer: é o notebook da sala 3", orq=orq), [])
        self.assertTrue(Mensagem.objects.filter(conversa=ch.conversa, texto__contains="sala 3").exists())
        self.assertEqual(Chamado.objects.count(), 1)

    # --- duplicidade ------------------------------------------------------
    def test_mensagem_repetida_nao_duplica(self):
        self.assertIsNotNone(self.orq.receber("u1", "oi", id_externo="msg-1"))
        self.assertIsNone(self.orq.receber("u1", "oi", id_externo="msg-1"))
        self.assertEqual(Mensagem.objects.filter(autor="colaborador").count(), 1)

    def test_chamado_nao_duplica_na_mesma_conversa(self):
        self.falar(*IDENT, "0", "Preciso de ajuda com o ERP")
        conversa = self.conversa()
        TicketService().abrir(conversa, motivo="de novo")
        self.assertEqual(Chamado.objects.count(), 1)

    # --- canais -----------------------------------------------------------
    @override_settings(WHATSAPP_ATIVO=True)
    def test_falha_do_whatsapp_nao_perde_mensagens(self):
        orq = ConversationOrchestrator(WhatsAppChannel(cliente=ClienteQuebrado()), horario=HorarioFixo())
        respostas = orq.receber("5511999999999", "oi")
        self.assertTrue(respostas)
        c = Conversa.objects.get(canal="whatsapp")
        self.assertEqual(c.mensagens.filter(autor="bot").count(), len(respostas))

    def test_canal_whatsapp_desligado_nao_afeta_o_portal(self):
        self.falar(*IDENT, "0", "Preciso de ajuda com o ERP")
        self.assertEqual(Chamado.objects.get().canal, "web")

    # --- equipe de TI -----------------------------------------------------
    def test_analista_responde_e_resolve(self):
        analista = User.objects.create_user("ana", password="x", first_name="Ana")
        self.falar(*IDENT, "0", "Preciso de ajuda com o ERP")
        ch = Chamado.objects.get()
        self.orq.responder_como_analista(ch, analista, "Oi Maria, pode reiniciar o ERP?")
        ch.refresh_from_db()
        self.assertEqual(ch.status, Chamado.Status.EM_ATENDIMENTO)
        self.assertEqual(ch.responsavel, analista)
        self.assertTrue(Mensagem.objects.filter(autor="analista", analista=analista).exists())

        self.orq.resolver_chamado(ch, analista, "Cache do ERP limpo.")
        ch.refresh_from_db()
        self.assertEqual(ch.status, Chamado.Status.RESOLVIDO)
        self.assertTrue(Mensagem.objects.filter(autor="sistema", texto__contains="Cache do ERP").exists())
        # Junto com a solução vai a pesquisa de satisfação.
        self.assertEqual(self.conversa().etapa, engine.PESQUISA)
        self.assertTrue(Mensagem.objects.filter(autor="bot", texto__contains="Muito insatisfeito").exists())

        self.falar("1", "pular")
        self.assertFalse(self.conversa().ativa)
        self.assertEqual(self.conversa().resultado, Conversa.Resultado.ESCALADA)
        self.assertEqual(ch.pesquisas.get().resposta, PesquisaSatisfacao.Resposta.MUITO_SATISFEITO)

        # Novo atendimento reaproveita a identificação.
        respostas = self.falar("oi de novo")
        self.assertIn("Olá, Maria", respostas[0])
        self.assertEqual(Conversa.objects.filter(identificador="u1").count(), 2)

    # --- pesquisa de satisfação --------------------------------------------
    def _resolvido(self):
        analista = User.objects.create_user("ana", password="x")
        self.falar(*IDENT, "0", "Preciso de ajuda com o ERP")
        ch = Chamado.objects.get()
        self.orq.resolver_chamado(ch, analista, "ERP reinstalado.")
        return ch

    def test_pesquisa_insatisfeito_exige_observacao(self):
        ch = self._resolvido()
        respostas = self.falar("4")  # muito insatisfeito
        self.assertIn("obrigatório", respostas[-1])
        respostas = self.falar("pular")
        self.assertIn("obrigatória", respostas[-1])
        self.assertFalse(PesquisaSatisfacao.objects.exists())
        self.falar("Demorou dois dias e ninguém me avisou")
        p = ch.pesquisas.get()
        self.assertEqual(p.resposta, PesquisaSatisfacao.Resposta.MUITO_INSATISFEITO)
        self.assertEqual(p.observacao, "Demorou dois dias e ninguém me avisou")
        self.assertTrue(ch.eventos.filter(tipo="pesquisa").exists())
        self.assertFalse(self.conversa().ativa)

    def test_pesquisa_satisfeito_com_observacao_opcional(self):
        ch = self._resolvido()
        self.falar("Satisfeito", "Atendimento rápido, obrigado!")
        p = ch.pesquisas.get()
        self.assertEqual((p.resposta, p.observacao), ("satisfeito", "Atendimento rápido, obrigado!"))

    def test_pesquisa_resposta_invalida_pergunta_de_novo(self):
        self._resolvido()
        respostas = self.falar("talvez")
        self.assertIn("número", respostas[0])
        self.assertEqual(self.conversa().etapa, engine.PESQUISA)

    def test_pesquisa_espera_mais_que_o_timeout_normal(self):
        self._resolvido()
        Conversa.objects.update(ultima_interacao=timezone.now() - timedelta(hours=5))
        self.falar("2", "pular")  # 5h depois ainda vale (limite padrão: 72h)
        self.assertEqual(PesquisaSatisfacao.objects.count(), 1)

    def test_pesquisa_expirada_nao_muda_resultado(self):
        self._resolvido()
        Conversa.objects.update(ultima_interacao=timezone.now() - timedelta(days=4))
        self.falar("oi")
        antiga = Conversa.objects.filter(identificador="u1").order_by("criada_em").first()
        self.assertEqual(antiga.resultado, Conversa.Resultado.ESCALADA)
        self.assertFalse(PesquisaSatisfacao.objects.exists())

    def test_registrar_pesquisa_valida_observacao(self):
        ch = self._resolvido()
        with self.assertRaises(ValueError):
            TicketService().registrar_pesquisa(ch, "insatisfeito", "  ")
        with self.assertRaises(ValueError):
            TicketService().registrar_pesquisa(ch, "mais_ou_menos")

    # --- SLA ----------------------------------------------------------------
    def test_chamado_recebe_sla_da_categoria(self):
        self.falar(*IDENT, "1", "1", "2", "Continua dando senha inválida")  # Acesso e login
        ch = Chamado.objects.get()
        self.assertEqual(ch.sla_horas, 8)
        self.assertIsNotNone(ch.prazo_sla)
        self.assertIn("SLA: 8h", ch.eventos.get(tipo="aberto").descricao)

    def test_chamado_sem_categoria_usa_sla_de_outros(self):
        self.falar(*IDENT, "0", "Preciso de ajuda com o ERP")
        self.assertEqual(Chamado.objects.get().sla_horas, 72)

    # --- segurança --------------------------------------------------------
    def test_senha_nao_e_gravada(self):
        respostas = self.falar(*IDENT, "0", "Minha senha é Segredo123 e não entra")
        self.assertIn(engine.AVISO_SENSIVEL, respostas)
        self.assertFalse(Mensagem.objects.filter(texto__contains="Segredo123").exists())
        self.assertNotIn("Segredo123", Chamado.objects.get().descricao)

    def test_conversa_inativa_expira(self):
        self.falar(*IDENT, "3")
        Conversa.objects.update(ultima_interacao=timezone.now() - timedelta(hours=2))
        respostas = self.falar("oi")
        antiga = Conversa.objects.filter(identificador="u1").order_by("criada_em").first()
        self.assertEqual(antiga.resultado, Conversa.Resultado.EXPIRADA)
        self.assertIn("Olá, Maria", respostas[0])


CENTRAL_CC = {**CENTRAL_TESTE, "IDENTIFICACAO": ["nome", "setor", "centro_custo", "email"]}


@override_settings(CENTRAL=CENTRAL_CC, WHATSAPP_ATIVO=False)
class CentroDeCustoTest(TestCase):
    def setUp(self):
        call_command("popular_orientacoes", verbosity=0)
        self.orq = ConversationOrchestrator(WebChannel(), horario=HorarioFixo(True))

    def test_chamado_guarda_o_centro_de_custo_separado(self):
        for t in ("oi", "Maria Silva", "Financeiro", "1105 - Financeiro", "maria@empresa.com.br",
                  "0", "Preciso de ajuda com o ERP"):
            self.orq.receber("u1", t)
        ch = Chamado.objects.get()
        self.assertEqual((ch.nome_colaborador, ch.centro_custo), ("Maria Silva", "1105 - Financeiro"))
        self.assertIn("Centro de custo: 1105 - Financeiro", ch.resumo)
        self.assertEqual(Colaborador.objects.get().centro_custo, "1105 - Financeiro")
