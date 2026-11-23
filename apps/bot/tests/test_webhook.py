import unittest

from apps.digisac.webhook import interpretar


class InterpretarWebhook(unittest.TestCase):
    def payload(self, **data):
        base = {"id": "m1", "contactId": "c1", "ticketId": "t1", "type": "chat",
                "text": " oi ", "isFromMe": False}
        base.update(data)
        return {"event": "message.created", "data": base}

    def test_mensagem_do_colaborador(self):
        [m] = interpretar(self.payload())
        self.assertEqual((m.contato_id, m.texto, m.eh_do_contato), ("c1", "oi", True))

    def test_mensagem_do_atendente_ou_bot(self):
        self.assertFalse(interpretar(self.payload(isFromMe=True))[0].eh_do_contato)
        self.assertFalse(interpretar(self.payload(isFromBot=True))[0].eh_do_contato)

    def test_fechamento_de_ticket(self):
        [m] = interpretar(self.payload(type="ticket", data={"ticketClose": True}))
        self.assertTrue(m.fechou_ticket)

    def test_outros_eventos_e_lixo(self):
        self.assertEqual(interpretar({"event": "contact.updated", "data": {}}), [])
        self.assertEqual(interpretar({"event": "message.created", "data": {"text": "sem contato"}}), [])
        self.assertEqual(interpretar("x"), [])

    def test_lista_de_mensagens(self):
        p = self.payload()
        p["data"] = [p["data"], dict(p["data"], id="m2")]
        self.assertEqual(len(interpretar(p)), 2)


if __name__ == "__main__":
    unittest.main()
