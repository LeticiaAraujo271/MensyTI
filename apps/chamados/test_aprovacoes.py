"""Aprovação em dois níveis (coordenador -> gerente da área):  python manage.py test apps"""
import io

from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.bot import engine
from apps.bot.models import Conversa, Mensagem
from apps.bot.orquestrador import ConversationOrchestrator
from apps.bot.tests.test_orquestrador import CENTRAL_TESTE, IDENT, HorarioFixo
from apps.canais import WebChannel
from apps.chamados import aprovacoes
from apps.chamados.models import Aprovacao, Chamado
from apps.chamados.servicos import TicketService, TransicaoInvalida

S = Chamado.Status
A = Aprovacao.Situacao
PEDIDO = ("7", "1", "Acesso de leitura na pasta Financeiro",
          "Carlos Souza", "carlos@empresa.com.br", "Gina Prado", "gina@empresa.com.br")


@override_settings(CENTRAL=CENTRAL_TESTE, WHATSAPP_ATIVO=False, APROVACAO_ENVIAR_EMAIL=False)
class AprovacaoTest(TestCase):
    def setUp(self):
        call_command("popular_orientacoes", verbosity=0)
        call_command("configurar_perfis", stdout=io.StringIO())
        self.orq = ConversationOrchestrator(WebChannel(), horario=HorarioFixo(True))
        with self.captureOnCommitCallbacks(execute=True):
            for t in (*IDENT, *PEDIDO):
                self.respostas = self.orq.receber("u1", t)
        self.chamado = Chamado.objects.get()
        self.coord, self.gerente = self.chamado.aprovacoes.order_by("nivel")
        self.analista = User.objects.create_user("ana", password="senha-forte-123")
        self.analista.groups.add(Group.objects.get(name="Analista de TI"))

    def url(self, ap):
        return f"/aprovacao/{ap.token}/"

    def decidir_pelo_link(self, ap, decisao, comentario=""):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url(ap), {"decisao": decisao, "comentario": comentario})

    def mensagens_do_sistema(self):
        return list(Mensagem.objects.filter(autor=Mensagem.Autor.SISTEMA).values_list("texto", flat=True))

    def test_chamado_aguarda_aprovacao_sem_contar_sla(self):
        ch = self.chamado
        self.assertEqual(ch.status, S.AGUARDANDO_APROVACAO)
        self.assertTrue(ch.exige_aprovacao)
        self.assertIsNone(ch.prazo_sla)
        self.assertTrue(ch.sla.aguardando_aprovacao)
        self.assertEqual(ch.sla_horas, 40)
        self.assertEqual([(a.nivel, a.nome, a.email) for a in (self.coord, self.gerente)],
                         [(1, "Carlos Souza", "carlos@empresa.com.br"), (2, "Gina Prado", "gina@empresa.com.br")])
        self.assertTrue(self.coord.da_vez)
        self.assertFalse(self.gerente.da_vez)
        self.assertIn(ch.protocolo, self.respostas[-1])
        self.assertIn(ch, Chamado.objects.filter(status__in=Chamado.ABERTOS))

    def test_ti_nao_executa_antes_da_aprovacao(self):
        with self.assertRaises(TransicaoInvalida):
            TicketService().resolver(self.chamado, self.analista, "Acesso liberado")
        with self.assertRaises(TransicaoInvalida):
            TicketService().mudar_status(self.chamado, S.EM_FILA, self.analista)

    def test_gerente_so_decide_depois_do_coordenador(self):
        r = self.client.get(self.url(self.gerente))
        self.assertContains(r, "Ainda não é a sua vez")
        self.assertNotContains(r, 'value="aprovar"')
        r = self.decidir_pelo_link(self.gerente, "aprovar")
        self.assertContains(r, "não está pendente")
        self.gerente.refresh_from_db()
        self.assertEqual(self.gerente.situacao, A.PENDENTE)

    def test_coordenador_e_gerente_aprovam_e_chamado_entra_na_fila(self):
        r = self.client.get(self.url(self.coord))
        self.assertContains(r, "Acesso de leitura na pasta Financeiro")
        self.assertContains(r, 'value="aprovar"')

        r = self.decidir_pelo_link(self.coord, "aprovar", "Somente leitura")
        self.assertRedirects(r, self.url(self.coord))
        self.coord.refresh_from_db()
        self.assertEqual((self.coord.situacao, self.coord.comentario), (A.APROVADA, "Somente leitura"))
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, S.AGUARDANDO_APROVACAO)
        self.assertIn("Agora falta a aprovação do gerente da área *Gina Prado*", self.mensagens_do_sistema()[-1])
        self.assertContains(self.client.get(self.url(self.coord)), "Você aprovou")

        self.decidir_pelo_link(self.gerente, "aprovar")
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, S.EM_FILA)
        self.assertIsNotNone(self.chamado.aprovado_em)
        self.assertIsNotNone(self.chamado.prazo_sla)
        self.assertFalse(self.chamado.sla.aguardando_aprovacao)
        self.assertIn("foi *aprovada*", self.mensagens_do_sistema()[-1])
        # Agora a TI executa normalmente
        self.orq.resolver_chamado(self.chamado, self.analista, "Acesso liberado na pasta.")
        self.assertEqual(self.chamado.status, S.RESOLVIDO)

    def test_reprovacao_exige_motivo_e_encerra(self):
        r = self.decidir_pelo_link(self.coord, "reprovar")
        self.assertContains(r, "Informe o motivo")
        self.decidir_pelo_link(self.coord, "reprovar", "Não faz parte da função")
        self.chamado.refresh_from_db()
        self.gerente.refresh_from_db()
        self.assertEqual(self.chamado.status, S.FECHADO)
        self.assertEqual(self.gerente.situacao, A.CANCELADA)
        self.assertIn("Não faz parte da função", self.chamado.solucao)
        self.assertIn("*reprovada*", self.mensagens_do_sistema()[-1])
        conversa = Conversa.objects.get(identificador="u1")
        self.assertFalse(conversa.ativa)
        self.assertEqual(conversa.etapa, engine.ENCERRADO)
        # Reprovado não volta para a fila pela TI: precisa de nova solicitação
        with self.assertRaises(TransicaoInvalida):
            TicketService().mudar_status(self.chamado, S.EM_FILA, self.analista)
        # E a próxima mensagem do colaborador começa um novo atendimento
        respostas = self.orq.receber("u1", "oi")
        self.assertIn("Como posso te ajudar?", respostas[-1])

    def test_link_decidido_nao_decide_de_novo(self):
        self.decidir_pelo_link(self.coord, "aprovar")
        r = self.decidir_pelo_link(self.coord, "reprovar", "mudei de ideia")
        self.assertContains(r, "não está pendente")
        self.coord.refresh_from_db()
        self.assertEqual(self.coord.situacao, A.APROVADA)

    def test_link_invalido(self):
        self.assertEqual(self.client.get("/aprovacao/nao-existe/").status_code, 404)

    def test_painel_mostra_aprovacoes_e_registra_decisao_com_evidencia(self):
        self.client.login(username="ana", password="senha-forte-123")
        url = f"/painel/chamado/{self.chamado.protocolo}/"
        r = self.client.get(url)
        self.assertContains(r, "Carlos Souza")
        self.assertContains(r, f"/aprovacao/{self.coord.token}/")
        self.assertNotContains(r, self.gerente.token)  # o link do gerente só aparece na vez dele
        self.assertNotContains(r, 'value="resolver"')

        self.client.post(url + "acao/", {"acao": "aprovacao", "decisao": "aprovar", "comentario": ""})
        self.coord.refresh_from_db()
        self.assertEqual(self.coord.situacao, A.PENDENTE)  # sem evidência, não registra

        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(url + "acao/", {"acao": "aprovacao", "decisao": "aprovar",
                                             "comentario": "Aprovado por e-mail em 25/11"})
        self.coord.refresh_from_db()
        self.assertEqual((self.coord.situacao, self.coord.registrada_por), (A.APROVADA, self.analista))
        self.assertContains(self.client.get(url), f"/aprovacao/{self.gerente.token}/")

    def test_fila_mostra_status_aguardando_aprovacao(self):
        self.client.login(username="ana", password="senha-forte-123")
        r = self.client.get("/painel/")
        self.assertContains(r, "Aguardando aprovação")


@override_settings(CENTRAL={**CENTRAL_TESTE, "URL": "http://central.local:8000"}, WHATSAPP_ATIVO=False,
                   APROVACAO_ENVIAR_EMAIL=True)
class EmailAprovacaoTest(TestCase):
    def setUp(self):
        call_command("popular_orientacoes", verbosity=0)
        self.orq = ConversationOrchestrator(WebChannel(), horario=HorarioFixo(True))

    def test_links_vao_por_email_um_de_cada_vez(self):
        with self.captureOnCommitCallbacks(execute=True):
            for t in (*IDENT, *PEDIDO):
                self.orq.receber("u1", t)
        ch = Chamado.objects.get()
        coord, gerente = ch.aprovacoes.order_by("nivel")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["carlos@empresa.com.br"])
        self.assertIn(f"http://central.local:8000/aprovacao/{coord.token}/", mail.outbox[0].body)
        self.assertIn(ch.protocolo, mail.outbox[0].subject)
        coord.refresh_from_db()
        self.assertIsNotNone(coord.enviada_em)

        with self.captureOnCommitCallbacks(execute=True):
            aprovacoes.decidir(coord, True)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].to, ["gina@empresa.com.br"])
        self.assertIn(gerente.token, mail.outbox[1].body)


class TestarEmailTest(TestCase):
    @override_settings(EMAIL_HOST="", EMAIL_HOST_USER="", EMAIL_HOST_PASSWORD="", APROVACAO_ENVIAR_EMAIL=False)
    def test_aponta_o_que_falta(self):
        saida = io.StringIO()
        with self.assertRaises(CommandError):
            call_command("testar_email", stdout=saida)
        self.assertIn("[FALTA] EMAIL_HOST", saida.getvalue())

    @override_settings(EMAIL_HOST="smtp.exemplo", EMAIL_HOST_USER="central@exemplo.com",
                       EMAIL_HOST_PASSWORD="x", APROVACAO_ENVIAR_EMAIL=True,
                       CENTRAL={**CENTRAL_TESTE, "URL": "http://central.local:8000"})
    def test_envia_email_de_teste(self):
        call_command("testar_email", "--para", "ti@exemplo.com", stdout=io.StringIO())
        self.assertEqual(mail.outbox[0].to, ["ti@exemplo.com"])
