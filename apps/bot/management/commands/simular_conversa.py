"""
Conversa com o assistente pelo terminal, usando o banco de verdade (canal web):
    python manage.py simular_conversa --novo
"""
from django.core.management.base import BaseCommand

from apps.bot.models import Conversa
from apps.bot.orquestrador import ConversationOrchestrator
from apps.canais import WebChannel


class Command(BaseCommand):
    help = "Simula uma conversa com o assistente no terminal."

    def add_arguments(self, parser):
        parser.add_argument("--contato", default="simulador", help="Identificador simulado.")
        parser.add_argument("--novo", action="store_true", help="Apaga as conversas anteriores do contato.")

    def handle(self, *args, contato, novo, **opts):
        if novo:
            Conversa.objects.filter(canal="web", identificador=contato).delete()
        orquestrador = ConversationOrchestrator(WebChannel())
        self.stdout.write("Digite as mensagens como se fosse o colaborador. Ctrl+C para sair.\n")
        for texto in orquestrador.iniciar(contato):
            self.stdout.write(f"\n🤖 {texto}\n")
        while True:
            try:
                entrada = input("\n🧑 ")
            except (EOFError, KeyboardInterrupt):
                self.stdout.write("\nFim da simulação.")
                return
            respostas = orquestrador.receber(contato, entrada)
            for texto in respostas or []:
                self.stdout.write(f"\n🤖 {texto}\n")
            if respostas == []:
                self.stdout.write("(mensagem anexada ao chamado: a TI responde pelo painel /painel/)")
