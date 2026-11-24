import json

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.bot.models import Conversa, Mensagem

DIGISAC_TESTE = {"URL": "", "TOKEN": "", "SERVICE_ID": "", "DEPARTAMENTO_TI_ID": "",
                 "WEBHOOK_TOKEN": "segredo", "ENVIAR_MENSAGENS": False, "TIMEOUT_SEGUNDOS": 5}


def payload(texto="oi", id_="m1"):
    return json.dumps({"event": "message.created", "data": {
        "id": id_, "contactId": "c1", "ticketId": "t1", "type": "chat", "text": texto, "isFromMe": False}})


@override_settings(DIGISAC=DIGISAC_TESTE)
class WebhookTest(TestCase):
    def setUp(self):
        call_command("popular_orientacoes", verbosity=0)

    def post(self, corpo, token="segredo"):
        return self.client.post(f"/webhooks/digisac/?token={token}", corpo, content_type="application/json")

    def test_exige_token(self):
        self.assertEqual(self.post(payload(), token="errado").status_code, 403)

    @override_settings(WHATSAPP_ATIVO=False)
    def test_canal_desligado_ignora(self):
        r = self.post(payload())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["ignorado"], "canal WhatsApp desativado")
        self.assertFalse(Conversa.objects.exists())

    @override_settings(WHATSAPP_ATIVO=True)
    def test_reenvio_do_webhook_nao_duplica(self):
        self.post(payload(id_="abc"))
        self.post(payload(id_="abc"))
        c = Conversa.objects.get(canal="whatsapp", identificador="c1")
        self.assertEqual(Mensagem.objects.filter(conversa=c, autor="colaborador").count(), 1)
        self.assertTrue(Mensagem.objects.filter(conversa=c, autor="bot").exists())


class TestarDigisacTest(__import__("django.test", fromlist=["SimpleTestCase"]).SimpleTestCase):
    def _rodar(self, **digisac):
        import io

        from django.core.management import CommandError, call_command
        from django.test import override_settings

        cfg = {"URL": "", "TOKEN": "", "SERVICE_ID": "", "WEBHOOK_TOKEN": "", "ENVIAR_MENSAGENS": False,
               "TIMEOUT_SEGUNDOS": 5, "DEPARTAMENTO_TI_ID": "", **digisac}
        saida = io.StringIO()
        with override_settings(DIGISAC=cfg):
            try:
                call_command("testar_digisac", stdout=saida)
                return True, saida.getvalue()
            except CommandError:
                return False, saida.getvalue()

    def test_valores_de_exemplo_contam_como_faltando(self):
        ok, saida = self._rodar(URL="https://suaempresa.digisac.app", TOKEN="cole-aqui-o-token-pessoal",
                                WEBHOOK_TOKEN="gere-um-segredo-aleatorio")
        self.assertFalse(ok)
        self.assertIn("[FALTA] DIGISAC_URL", saida)

    def test_configuracao_completa(self):
        ok, saida = self._rodar(URL="https://empresa.digisac.app", TOKEN="abc123xyz", WEBHOOK_TOKEN="s3gr3d0")
        self.assertTrue(ok)
        self.assertIn("/webhooks/digisac/?token=s3gr", saida)
