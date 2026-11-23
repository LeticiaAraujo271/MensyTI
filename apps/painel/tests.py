import io

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.bot.models import Conversa, Mensagem
from apps.bot.orquestrador import ConversationOrchestrator
from apps.bot.tests.test_orquestrador import CENTRAL_TESTE, IDENT, HorarioFixo
from apps.canais import WebChannel
from apps.chamados.models import Chamado


@override_settings(CENTRAL=CENTRAL_TESTE, WHATSAPP_ATIVO=False)
class PainelTest(TestCase):
    def setUp(self):
        call_command("popular_orientacoes", verbosity=0)
        call_command("configurar_perfis", stdout=io.StringIO())
        orq = ConversationOrchestrator(WebChannel(), horario=HorarioFixo())
        for t in (*IDENT, "0", "O ERP fecha sozinho"):
            orq.receber("u1", t)
        self.chamado = Chamado.objects.get()
        self.url = f"/painel/chamado/{self.chamado.protocolo}/"
        self.analista = User.objects.create_user("ana", password="senha-forte-123")
        self.analista.groups.add(Group.objects.get(name="Analista de TI"))

    def acao(self, **dados):
        return self.client.post(self.url + "acao/", dados)

    def test_exige_login(self):
        r = self.client.get("/painel/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/painel/login/", r["Location"])

    def test_usuario_sem_perfil_nao_acessa(self):
        User.objects.create_user("curioso", password="x")
        self.client.login(username="curioso", password="x")
        self.assertEqual(self.client.get("/painel/").status_code, 403)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.get(self.url + "mensagens/").status_code, 403)

    def test_analista_ve_fila_e_historico(self):
        self.client.login(username="ana", password="senha-forte-123")
        r = self.client.get("/painel/")
        self.assertContains(r, self.chamado.protocolo)
        r = self.client.get(self.url)
        self.assertContains(r, "O ERP fecha sozinho")
        self.assertContains(r, "Maria Silva")

    def test_atender_responder_e_resolver(self):
        self.client.login(username="ana", password="senha-forte-123")
        self.acao(acao="assumir")
        self.chamado.refresh_from_db()
        self.assertEqual((self.chamado.status, self.chamado.responsavel), (Chamado.Status.EM_ATENDIMENTO, self.analista))

        self.acao(acao="responder", texto="Pode tentar agora?", aguardar="1")
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.Status.AGUARDANDO_USUARIO)
        self.assertTrue(Mensagem.objects.filter(autor="analista", texto="Pode tentar agora?").exists())

        # O colaborador responde pelo portal: volta para "em atendimento".
        ConversationOrchestrator(WebChannel(), horario=HorarioFixo()).receber("u1", "Funcionou!")
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.Status.EM_ATENDIMENTO)

        self.acao(acao="resolver", solucao="")  # solução obrigatória
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.Status.EM_ATENDIMENTO)

        self.acao(acao="resolver", solucao="ERP reinstalado.")
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.Status.RESOLVIDO)
        self.assertFalse(Conversa.objects.get().ativa)

        self.acao(acao="reabrir", nota="Voltou a fechar")
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.Status.EM_FILA)
        self.assertTrue(self.chamado.eventos.filter(tipo="reaberto").exists())
