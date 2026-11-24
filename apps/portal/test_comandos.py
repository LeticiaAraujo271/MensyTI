"""Comandos que substituem os antigos scripts do PowerShell (sem tocar no Windows de verdade)."""
import io
import tempfile
from pathlib import Path
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase

from apps.portal import arquivo_env
from apps.portal.management.commands import servico


class ArquivoEnv(SimpleTestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.env = Path(self.pasta.name) / ".env"
        self.env.write_text("# comentário\nDJANGO_DEBUG=true\nDIGISAC_URL=https://suaempresa.digisac.app\n",
                            encoding="utf-8")

    def tearDown(self):
        self.pasta.cleanup()

    def test_le_valor_e_ignora_texto_de_exemplo(self):
        self.assertEqual(arquivo_env.ler("DJANGO_DEBUG", self.env), "true")
        self.assertEqual(arquivo_env.ler("DIGISAC_URL", self.env), "")
        self.assertEqual(arquivo_env.ler("NAO_EXISTE", self.env), "")

    def test_grava_mantendo_comentarios_e_acrescenta_no_fim(self):
        arquivo_env.gravar("DJANGO_DEBUG", "false", self.env)
        arquivo_env.gravar("CENTRAL_URL", "http://nb332:8000", self.env, comentario="Links")
        texto = self.env.read_text(encoding="utf-8")
        self.assertTrue(texto.startswith("# comentário\nDJANGO_DEBUG=false\n"))
        self.assertTrue(texto.endswith("\n# Links\nCENTRAL_URL=http://nb332:8000\n"))


class ServicoWindows(SimpleTestCase):
    def test_tarefa_liga_ao_entrar_e_religa_se_cair(self):
        with tempfile.TemporaryDirectory() as pasta:
            python = Path(pasta) / "python.exe"
            (Path(pasta) / "pythonw.exe").write_text("")
            with mock.patch.object(servico.sys, "executable", str(python)), \
                    mock.patch.dict(servico.os.environ, {"USERDOMAIN": "EMPRESA", "USERNAME": "ana"}):
                xml = servico._xml_da_tarefa()
        self.assertIn("<LogonTrigger><Enabled>true</Enabled><UserId>EMPRESA" + chr(92) + "ana</UserId>", xml)
        self.assertIn("pythonw.exe</Command>", xml)
        self.assertIn("servir.py", xml)
        self.assertIn("<RestartOnFailure><Interval>PT1M</Interval><Count>999</Count>", xml)
        self.assertIn("<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>", xml)
        self.assertIn("<RunLevel>LeastPrivilege</RunLevel>", xml)

    def test_fora_do_windows_explica_o_que_fazer(self):
        with mock.patch.object(servico, "WINDOWS", False):
            with self.assertRaisesMessage(CommandError, "servir.py"):
                call_command("servico", "status", stdout=io.StringIO())


class ConfigurarIntegracoes(SimpleTestCase):
    def test_exige_terminal_interativo(self):
        with mock.patch("sys.stdin", io.StringIO("")):
            with self.assertRaisesMessage(CommandError, "terminal"):
                call_command("configurar_integracoes", stdout=io.StringIO())
