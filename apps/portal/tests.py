"""Critério de aceite: abrir a URL e registrar um problema completo sem WhatsApp configurado."""
import json
from unittest import mock

from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from apps.bot.horario import WorkingHoursService
from apps.bot.models import Mensagem
from apps.chamados.models import Chamado

CENTRAL_TESTE = {"NOME": "Central de TI", "IDENTIFICACAO": ["nome", "setor", "email"],
                 "DOMINIOS_EMAIL": [], "LIMITE_MENSAGENS_MINUTO": 100}


@override_settings(CENTRAL=CENTRAL_TESTE, WHATSAPP_ATIVO=False)
@mock.patch.object(WorkingHoursService, "dentro_do_horario", return_value=True)
class PortalTest(TestCase):
    def setUp(self):
        call_command("popular_orientacoes", verbosity=0)
        self._n = 0

    def enviar(self, client, texto, id_=None):
        self._n += 1
        corpo = {"texto": texto, "id": id_ or f"cliente-{self._n:06d}"}
        return client.post("/api/enviar/", json.dumps(corpo), content_type="application/json")

    def test_pagina_abre(self, _):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Central de TI")
        self.assertIn("csrftoken", r.cookies)

    def test_fluxo_completo_ate_o_protocolo(self, _):
        self.client.get("/")
        boas_vindas = self.client.get("/api/mensagens/").json()["mensagens"]
        self.assertEqual(boas_vindas[0]["autor"], "bot")
        for texto in ("Maria Silva", "Financeiro", "maria@empresa.com.br", "3", "1", "2",
                      "Continua sem internet depois de reiniciar"):
            r = self.enviar(self.client, texto)
            self.assertEqual(r.status_code, 200)
        dados = r.json()
        ch = Chamado.objects.get()
        self.assertEqual(dados["estado"]["chamado"]["protocolo"], ch.protocolo)
        self.assertIn(ch.protocolo, dados["mensagens"][-1]["texto"])
        self.assertEqual(ch.canal, "web")

    def test_colaborador_nao_ve_conversa_de_outro(self, _):
        a, b = Client(), Client()
        a.get("/"), b.get("/")
        self.enviar(a, "Maria Silva Confidencial")
        textos_b = [m["texto"] for m in b.get("/api/mensagens/").json()["mensagens"]]
        self.assertFalse(any("Confidencial" in t for t in textos_b))
        textos_a = [m["texto"] for m in a.get("/api/mensagens/").json()["mensagens"]]
        self.assertTrue(any("Confidencial" in t for t in textos_a))

    def test_clique_duplo_nao_duplica(self, _):
        self.client.get("/api/mensagens/")
        self.enviar(self.client, "Maria Silva", id_="mesmo-id-123")
        self.enviar(self.client, "Maria Silva", id_="mesmo-id-123")
        self.assertEqual(Mensagem.objects.filter(autor="colaborador").count(), 1)

    def test_validacao_de_entrada(self, _):
        self.assertEqual(self.enviar(self.client, "").status_code, 400)
        self.assertEqual(self.enviar(self.client, "x" * 2001).status_code, 400)
        r = self.client.post("/api/enviar/", "não é json", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    @override_settings(CENTRAL={**CENTRAL_TESTE, "LIMITE_MENSAGENS_MINUTO": 3})
    def test_limite_de_mensagens(self, _):
        codigos = [self.enviar(self.client, f"mensagem {i}").status_code for i in range(4)]
        self.assertEqual(codigos, [200, 200, 200, 429])

    def test_resposta_do_analista_aparece_no_chat(self, _):
        from django.contrib.auth.models import User

        from apps.bot.orquestrador import ConversationOrchestrator
        from apps.canais import WebChannel

        self.client.get("/api/mensagens/")  # o navegador sempre carrega a conversa antes
        for texto in ("Maria Silva", "Financeiro", "maria@empresa.com.br", "0", "ERP não abre"):
            self.enviar(self.client, texto)
        ultimo = self.client.get("/api/mensagens/").json()["mensagens"][-1]["id"]
        analista = User.objects.create_user("ana", password="x", first_name="Ana")
        ConversationOrchestrator(WebChannel()).responder_como_analista(Chamado.objects.get(), analista, "Já estou vendo!")
        novas = self.client.get(f"/api/mensagens/?depois={ultimo}").json()["mensagens"]
        self.assertEqual([(m["autor"], m["texto"], m["analista"]) for m in novas],
                         [("analista", "Já estou vendo!", "Ana")])
