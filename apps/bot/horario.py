"""WorkingHoursService: janela de atendimento humano, sempre a configurada (nunca inventada)."""
from __future__ import annotations

from datetime import datetime, time

from django.conf import settings
from django.utils import timezone


class WorkingHoursService:
    def __init__(self, config: dict | None = None):
        self.cfg = config or settings.BOT

    def dentro_do_horario(self, agora: datetime | None = None) -> bool:
        agora = timezone.localtime(agora or timezone.now())
        if agora.weekday() not in self.cfg["HORARIO_DIAS"]:
            return False
        inicio = time.fromisoformat(self.cfg["HORARIO_INICIO"])
        fim = time.fromisoformat(self.cfg["HORARIO_FIM"])
        return inicio <= agora.time() < fim

    def texto(self) -> str:
        return self.cfg["TEXTO_HORARIO"]
