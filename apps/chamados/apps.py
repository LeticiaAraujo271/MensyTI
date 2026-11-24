from django.apps import AppConfig
from django.db.models.signals import post_delete, post_save


class ChamadosConfig(AppConfig):
    name = "apps.chamados"
    verbose_name = "Solicitações / Chamados"

    def ready(self):
        from .models import Feriado
        from .sla import limpar_cache_feriados

        # Feriado criado, alterado ou apagado no Admin: o SLA passa a considerar na hora.
        post_save.connect(limpar_cache_feriados, sender=Feriado, dispatch_uid="sla_feriado_salvo")
        post_delete.connect(limpar_cache_feriados, sender=Feriado, dispatch_uid="sla_feriado_apagado")
