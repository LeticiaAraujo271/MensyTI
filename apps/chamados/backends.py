"""
Integração opcional com um sistema de chamados externo (GLPI, Jira, etc.).

O chamado SEMPRE é criado na Central de TI (fila e painel próprios). Se houver um
sistema externo, crie uma classe que herda de BackendChamados, implemente
`abrir()` chamando a API dele e aponte CHAMADOS_BACKEND no .env para ela.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class BackendChamados:
    def abrir(self, chamado) -> str | None:
        """Cria o chamado no sistema externo e devolve o número/protocolo de lá."""
        raise NotImplementedError


class BackendLocal(BackendChamados):
    """Padrão: não há sistema externo; o chamado fica só na Central de TI."""

    def abrir(self, chamado) -> str | None:
        return None


# Exemplo de integração (preencher quando houver a API e as credenciais):
#
# class BackendMeuSistema(BackendChamados):
#     def abrir(self, chamado):
#         resp = requests.post(f"{URL}/api/chamados", json={
#             "solicitante": chamado.nome_colaborador,
#             "setor": chamado.setor,
#             "categoria": chamado.categoria,
#             "descricao": chamado.resumo,
#         }, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=10)
#         resp.raise_for_status()
#         return str(resp.json()["numero"])
