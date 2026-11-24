"""Uma porta por tela (SERVIDOR_ATALHOS), usado no Codespaces."""
from django.test import SimpleTestCase, TestCase, override_settings

from apps.portal.atalhos import ler_atalhos

ATALHOS = "8001:/painel/,8002:/admin/"


class LerAtalhos(SimpleTestCase):
    def test_le_e_ignora_itens_invalidos(self):
        self.assertEqual(ler_atalhos("8001:/painel/, 8002:/admin/ ,x:/y/,8003:sem-barra,"),
                         {8001: "/painel/", 8002: "/admin/"})
        self.assertEqual(ler_atalhos(""), {})


@override_settings(SERVIDOR_ATALHOS=ATALHOS)
class AtalhoPorPorta(TestCase):
    def test_porta_do_painel_e_da_administracao(self):
        self.assertRedirects(self.client.get("/", SERVER_PORT="8001"), "/painel/", fetch_redirect_response=False)
        self.assertRedirects(self.client.get("/", SERVER_PORT="8002"), "/admin/", fetch_redirect_response=False)

    def test_porta_principal_continua_no_chat(self):
        self.assertEqual(self.client.get("/", SERVER_PORT="8000").status_code, 200)

    def test_so_a_raiz_e_redirecionada(self):
        r = self.client.get("/painel/login/", SERVER_PORT="8002")
        self.assertEqual(r.status_code, 200)


@override_settings(SERVIDOR_ATALHOS="")
class SemAtalhos(TestCase):
    def test_desligado_por_padrao(self):
        self.assertEqual(self.client.get("/", SERVER_PORT="8001").status_code, 200)


class FalhaCsrf(TestCase):
    def test_mostra_o_motivo_em_portugues(self):
        from django.test import Client

        cliente = Client(enforce_csrf_checks=True)
        r = cliente.post("/painel/login/", {"username": "x", "password": "y"})
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, "Envio recusado", status_code=403)
        self.assertContains(r, "CSRF cookie not set", status_code=403)
        self.assertContains(r, "Recarregue a página", status_code=403)
