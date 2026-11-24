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
        self.assertEqual(Conversa.objects.get().etapa, "pesquisa")  # pesquisa enviada ao colaborador
        self.assertTrue(Mensagem.objects.filter(texto__contains="Pesquisa de satisfação").exists())

        self.acao(acao="reabrir", nota="Voltou a fechar")
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.Status.EM_FILA)
        self.assertTrue(self.chamado.eventos.filter(tipo="reaberto").exists())

    # --- SLA ----------------------------------------------------------------
    def test_fila_e_detalhe_mostram_sla(self):
        self.client.login(username="ana", password="senha-forte-123")
        r = self.client.get("/painel/")
        self.assertContains(r, 'class="sla verde"')
        r = self.client.get(self.url)
        self.assertContains(r, "SLA: 72h úteis")  # opção 0 sem categoria = SLA de "Outros"

    def test_filtro_e_alerta_de_sla_vencido(self):
        from datetime import timedelta

        from django.utils import timezone

        Chamado.objects.update(criado_em=timezone.now() - timedelta(days=30))
        self.client.login(username="ana", password="senha-forte-123")
        r = self.client.get("/painel/")
        self.assertContains(r, "1 com SLA vencido")
        self.assertContains(self.client.get("/painel/?sla=vermelho"), self.chamado.protocolo)
        self.assertNotContains(self.client.get("/painel/?sla=verde"), f">{self.chamado.protocolo}<")

    def test_reclassificar_muda_o_sla(self):
        self.client.login(username="ana", password="senha-forte-123")
        self.acao(acao="reclassificar", categoria="Acesso e login")
        self.chamado.refresh_from_db()
        self.assertEqual((self.chamado.categoria, self.chamado.sla_horas), ("Acesso e login", 8))
        self.assertTrue(self.chamado.eventos.filter(tipo="reclassif", descricao__contains="72h → 8h").exists())

    def test_detalhe_mostra_pesquisa_respondida(self):
        from apps.chamados.servicos import TicketService

        TicketService().registrar_pesquisa(self.chamado, "insatisfeito", "Demorou muito")
        self.client.login(username="ana", password="senha-forte-123")
        r = self.client.get(self.url)
        self.assertContains(r, "Insatisfeito")
        self.assertContains(r, "Demorou muito")

    # --- Excel ---------------------------------------------------------------
    def test_exportar_excel_com_os_campos_pedidos(self):
        from io import BytesIO

        from openpyxl import load_workbook

        from apps.chamados.servicos import TicketService

        self.chamado.nome_colaborador = "=HYPERLINK(\"http://x\")"  # texto do usuário nunca vira fórmula
        self.chamado.save()
        TicketService().registrar_pesquisa(self.chamado, "insatisfeito", "Demorou muito")
        self.client.login(username="ana", password="senha-forte-123")
        r = self.client.get("/painel/exportar.xlsx?status=todos")
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheetml", r["Content-Type"])
        self.assertIn("attachment", r["Content-Disposition"])

        ws = load_workbook(BytesIO(r.content)).active
        cab = [c.value for c in ws[1]]
        for campo in ("Número do chamado", "Colaborador", "Assunto", "Status", "SLA", "Responsável", "Canal",
                      "Aberto em", "Data do fechamento", "Pesquisa de satisfação", "Observação da pesquisa"):
            self.assertIn(campo, cab)
        linha = {cab[i]: c.value for i, c in enumerate(ws[2])}
        self.assertEqual(linha["Número do chamado"], self.chamado.protocolo)
        self.assertEqual(linha["Status"], "Em fila")
        self.assertEqual(linha["SLA"], "No prazo")
        self.assertEqual(linha["Canal"], "Portal web")
        self.assertIn("Centro de custo", cab)
        self.assertEqual(cab.index("Centro de custo"), cab.index("Colaborador") + 1)
        self.assertEqual(linha["Pesquisa de satisfação"], "Insatisfeito")
        self.assertEqual(linha["Observação da pesquisa"], "Demorou muito")
        self.assertIsNone(linha["Data do fechamento"])
        self.assertEqual(ws.cell(row=2, column=cab.index("Colaborador") + 1).data_type, "s")

    def test_exportar_respeita_filtro_e_permissao(self):
        self.assertEqual(self.client.get("/painel/exportar.xlsx").status_code, 302)  # exige login
        from io import BytesIO

        from openpyxl import load_workbook

        self.client.login(username="ana", password="senha-forte-123")
        ws = load_workbook(BytesIO(self.client.get("/painel/exportar.xlsx?status=fechado").content)).active
        self.assertEqual(ws.max_row, 1)  # só o cabeçalho: nenhum chamado fechado

    def test_painel_mostra_centro_de_custo(self):
        Chamado.objects.update(centro_custo="1105 - Financeiro")
        self.client.login(username="ana", password="senha-forte-123")
        self.assertContains(self.client.get("/painel/"), "1105 - Financeiro")
        self.assertContains(self.client.get("/painel/?q=1105&status=todos"), self.chamado.protocolo)
        self.assertContains(self.client.get(self.url), "Centro de custo")


@override_settings(CENTRAL=CENTRAL_TESTE, WHATSAPP_ATIVO=True)
class SimuladorWhatsAppTest(TestCase):
    def setUp(self):
        call_command("popular_orientacoes", verbosity=0)
        call_command("configurar_perfis", stdout=io.StringIO())
        self.analista = User.objects.create_user("ana", password="senha-forte-123")
        self.analista.groups.add(Group.objects.get(name="Analista de TI"))
        self.client.login(username="ana", password="senha-forte-123")

    def falar(self, *textos):
        for t in textos:
            self.assertEqual(self.client.post("/painel/whatsapp/enviar/", {"texto": t}).status_code, 200)
        return self.client.get("/painel/whatsapp/mensagens/").json()

    def test_exige_login(self):
        self.client.logout()
        self.assertEqual(self.client.get("/painel/whatsapp/").status_code, 302)

    def test_ciclo_completo_sem_enviar_nada_ao_digisac(self):
        from unittest import mock

        with mock.patch("apps.digisac.client.ClienteDigisac.enviar_texto") as enviar:
            self.assertContains(self.client.get("/painel/whatsapp/"), "Simulador do WhatsApp")
            d = self.falar(*IDENT, "0", "O ERP fecha sozinho")
            textos = [m["texto"] for m in d["mensagens"]]
            self.assertTrue(d["mensagens"][0]["de_mim"])
            self.assertTrue(any("nome completo" in t for t in textos))
            ch = Chamado.objects.get()
            self.assertEqual(ch.canal, "whatsapp")
            self.assertEqual(d["chamado"]["protocolo"], ch.protocolo)
            self.assertContains(self.client.get("/painel/"), "simulador")

            # O analista responde e resolve pelo painel: tudo chega no "celular".
            url = f"/painel/chamado/{ch.protocolo}/acao/"
            self.client.post(url, {"acao": "responder", "texto": "Pode tentar agora?"})
            self.client.post(url, {"acao": "resolver", "solucao": "ERP atualizado."})
            textos = [m["texto"] for m in self.client.get("/painel/whatsapp/mensagens/").json()["mensagens"]]
            self.assertTrue(any(t.startswith("🙋 *ana* (TI): Pode tentar agora?") for t in textos))
            self.assertTrue(any("ERP atualizado." in t for t in textos))
            self.assertTrue(any("Pesquisa de satisfação" in t for t in textos))
            self.falar("3", "Demorou")
            self.assertEqual(ch.pesquisas.get().resposta, "insatisfeito")
            enviar.assert_not_called()

    def test_novo_contato_e_apagar_testes(self):
        self.falar(*IDENT, "0", "O ERP fecha sozinho")
        self.client.post("/painel/whatsapp/nova/")
        d = self.falar("oi")
        self.assertTrue(any("nome completo" in m["texto"] for m in d["mensagens"]))  # outro "número"
        r = self.client.post("/painel/whatsapp/apagar/").json()
        self.assertEqual(r["chamados"], 1)
        self.assertFalse(Chamado.objects.exists())
        self.assertFalse(Conversa.objects.exists())
