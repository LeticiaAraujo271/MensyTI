"""Uma porta por tela (SERVIDOR_ATALHOS), usado no Codespaces."""
import os
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings

from apps.portal.atalhos import ler_atalhos

ATALHOS = "8001:/painel/,8002:/admin/"


class LerAtalhos(SimpleTestCase):
    def test_le_e_ignora_itens_invalidos(self):
        self.assertEqual(ler_atalhos("8001:/painel/, 8002:/admin/ ,x:/y/,8003:sem-barra,"),
                         {8001: "/painel/", 8002: "/admin/"})
        self.assertEqual(ler_atalhos(""), {})


@override_settings(SERVIDOR_ATALHOS=ATALHOS, SERVIDOR_PORTA=8000)
class AtalhoPorPorta(TestCase):
    """8001/8002 só redirecionam para a 8000: o login e os cookies ficam num endereço só."""

    def location(self, caminho="/", porta="8001", **extra):
        r = self.client.get(caminho, SERVER_PORT=porta, **extra)
        self.assertEqual(r.status_code, 302)
        return r["Location"]

    def test_porta_do_painel_e_da_administracao_levam_para_a_8000(self):
        self.assertEqual(self.location(porta="8001"), "http://testserver:8000/painel/")
        self.assertEqual(self.location(porta="8002"), "http://testserver:8000/admin/")

    def test_qualquer_caminho_das_portas_extras_vai_para_a_8000(self):
        self.assertEqual(self.location("/painel/login/?next=/painel/", porta="8002"),
                         "http://testserver:8000/painel/login/?next=/painel/")

    def test_localhost_do_vscode_mantem_o_nome(self):
        self.assertEqual(self.location(porta="8001", HTTP_HOST="localhost:8001"), "http://localhost:8000/painel/")

    def test_no_codespaces_usa_o_endereco_publico_da_8000(self):
        with mock.patch.dict(os.environ, {"CODESPACE_NAME": "meu-cs",
                                          "GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN": "app.github.dev"}):
            self.assertEqual(self.location(porta="8001"), "https://meu-cs-8000.app.github.dev/painel/")
            self.assertEqual(self.location(porta="8002"), "https://meu-cs-8000.app.github.dev/admin/")

    def test_porta_principal_continua_no_chat(self):
        self.assertEqual(self.client.get("/", SERVER_PORT="8000").status_code, 200)


@override_settings(SERVIDOR_ATALHOS=ATALHOS, SERVIDOR_PORTA=8000, CSRF_COOKIE_NAME="central_csrf",
                   SESSION_COOKIE_NAME="central_sessao")
class LoginComCookiesProprios(TestCase):
    def test_login_no_painel_com_verificacao_csrf(self):
        from django.contrib.auth.models import User
        from django.test import Client

        User.objects.create_user("ana", password="senha-forte-123", is_staff=True)
        c = Client(enforce_csrf_checks=True)
        r = c.get("/painel/login/", SERVER_PORT="8000")
        self.assertIn("central_csrf", r.cookies)
        self.assertContains(r, 'content="central_csrf"')  # o JavaScript lê o cookie por este nome
        token = r.cookies["central_csrf"].value
        r = c.post("/painel/login/", {"username": "ana", "password": "senha-forte-123",
                                     "csrfmiddlewaretoken": token}, SERVER_PORT="8000")
        self.assertEqual(r.status_code, 302)
        self.assertIn("central_sessao", r.cookies)
        # Mesmo login vale para a administração
        self.assertEqual(c.get("/admin/", SERVER_PORT="8000").status_code, 200)


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
