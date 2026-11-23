"""
Cliente da API do Digisac.

Autenticação: token pessoal (Conta > API > Tokens de acesso pessoal), enviado
como "Authorization: Bearer <token>" para <sua URL>/api/v1/...

ATENÇÃO: confirme os caminhos de TRANSFERIR e ENCERRAR na documentação
Postman da sua conta Digisac antes de ir para produção. Eles estão isolados
nas constantes abaixo para facilitar o ajuste.
"""
import logging

import requests
from django.conf import settings

log = logging.getLogger(__name__)

ROTA_ENVIAR_MENSAGEM = "/api/v1/messages"
ROTA_TRANSFERIR = "/api/v1/contacts/{contato_id}/ticket/transfer"   # confirmar na doc
ROTA_ENCERRAR = "/api/v1/contacts/{contato_id}/ticket/close"         # confirmar na doc


class ErroDigisac(Exception):
    pass


class ClienteDigisac:
    def __init__(self, url=None, token=None, service_id=None, timeout=None, enviar=None):
        cfg = settings.DIGISAC
        self.url = (url or cfg["URL"]).rstrip("/")
        self.token = token or cfg["TOKEN"]
        self.service_id = service_id if service_id is not None else cfg["SERVICE_ID"]
        self.timeout = timeout or cfg["TIMEOUT_SEGUNDOS"]
        self.enviar = cfg["ENVIAR_MENSAGENS"] if enviar is None else enviar
        self.sessao = requests.Session()
        self.sessao.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })

    def _post(self, rota: str, corpo: dict | None = None) -> dict | None:
        if not self.enviar:
            log.info("[simulação] POST %s %s", rota, corpo)
            return None
        if not self.url or not self.token:
            raise ErroDigisac("Configure DIGISAC_URL e DIGISAC_TOKEN no .env")
        resp = self.sessao.post(f"{self.url}{rota}", json=corpo or {}, timeout=self.timeout)
        if resp.status_code >= 400:
            raise ErroDigisac(f"{rota} -> HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json() if resp.content else None

    def enviar_texto(self, contato_id: str, texto: str):
        corpo = {"contactId": contato_id, "text": texto}
        if self.service_id:
            corpo["serviceId"] = self.service_id
        return self._post(ROTA_ENVIAR_MENSAGEM, corpo)

    def transferir(self, contato_id: str, departamento_id: str, comentario: str = ""):
        corpo = {"departmentId": departamento_id, "comments": comentario}
        return self._post(ROTA_TRANSFERIR.format(contato_id=contato_id), corpo)

    def encerrar(self, contato_id: str, comentario: str = ""):
        return self._post(ROTA_ENCERRAR.format(contato_id=contato_id), {"comments": comentario})
