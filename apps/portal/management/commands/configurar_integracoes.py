"""
Configura o WhatsApp (Digisac) e o e-mail dos links de aprovação, sem PowerShell.

    python manage.py configurar_integracoes              WhatsApp e e-mail
    python manage.py configurar_integracoes --so-email   só o e-mail
    python manage.py configurar_integracoes --so-whatsapp só o WhatsApp

No VS Code: Terminal > Run Task... > "Central: configurar WhatsApp e e-mail".
Pergunta no terminal (senhas e tokens não aparecem na tela), grava no .env, testa e reinicia
a Central. Nada passa por chat, e-mail ou GitHub: o .env fica só neste computador.
Enter numa pergunta mantém o valor que já está no .env.
"""
from __future__ import annotations

import getpass
import secrets
import socket
import subprocess
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.portal import arquivo_env


class Command(BaseCommand):
    help = "Configura o WhatsApp (Digisac) e o e-mail das aprovações no .env, perguntando no terminal."

    def add_arguments(self, parser):
        parser.add_argument("--so-email", action="store_true", help="Configura só o e-mail.")
        parser.add_argument("--so-whatsapp", action="store_true", help="Configura só o WhatsApp.")

    # --- perguntas ---------------------------------------------------------
    def valor(self, pergunta, chave, padrao=""):
        sugestao = arquivo_env.ler(chave) or padrao
        resposta = input(f"{pergunta}{f' [{sugestao}]' if sugestao else ''}: ").strip() or sugestao
        arquivo_env.gravar(chave, resposta)
        return resposta

    def segredo(self, pergunta, chave):
        tem = bool(arquivo_env.ler(chave))
        resposta = getpass.getpass(f"{pergunta}{' [Enter mantém o atual]' if tem else ''}: ").strip()
        if resposta:
            arquivo_env.gravar(chave, resposta)
        elif not tem:
            self.stdout.write(self.style.WARNING("   (ficou vazio)"))

    def sim(self, pergunta, padrao=False):
        resposta = input(f"{pergunta} ({'S/n' if padrao else 's/N'}): ").strip().lower()
        return padrao if not resposta else resposta.startswith("s")

    def manage(self, *args):
        # Processo novo: lê o .env recém-gravado.
        return subprocess.run([sys.executable, "manage.py", *args], cwd=settings.BASE_DIR).returncode == 0

    def titulo(self, texto):
        self.stdout.write(self.style.HTTP_INFO(f"\n=== {texto} ==="))

    # --- fluxo -------------------------------------------------------------
    def handle(self, *args, so_email=False, so_whatsapp=False, **opts):
        if not arquivo_env.ARQUIVO.exists():
            raise CommandError("Não achei o .env. Rode antes: python preparar.py")
        if not sys.stdin or not sys.stdin.isatty():
            raise CommandError("Este comando faz perguntas: rode num terminal (ou pela tarefa do VS Code).")

        self.titulo("Endereço da Central")
        self.stdout.write("É o endereço que os colegas e os aprovadores abrem (precisa do firewall liberado).")
        porta = arquivo_env.ler("SERVIDOR_PORTA") or "8000"
        self.valor("Endereço da Central", "CENTRAL_URL", f"http://{socket.gethostname().lower()}:{porta}")

        if not so_whatsapp:
            self.email()
        if not so_email:
            self.whatsapp()

        self.titulo("Reiniciando a Central para valer a nova configuração")
        if not self.manage("servico", "reiniciar"):
            self.stdout.write(self.style.WARNING("Não religuei em segundo plano. Se você usa o runserver, "
                                                 "pare (Ctrl+C) e ligue de novo."))
        self.stdout.write(self.style.SUCCESS("\nPronto. Para refazer só uma parte: --so-email ou --so-whatsapp."))

    def email(self):
        self.titulo("E-mail dos links de aprovação")
        self.stdout.write("Use uma conta de serviço (ex.: central-ti@empresa.com.br), não o seu e-mail pessoal.\n"
                          "Microsoft 365: servidor smtp.office365.com, porta 587, TLS. A conta precisa ter o\n"
                          "'SMTP autenticado' liberado pelo administrador do Microsoft 365.")
        self.valor("Servidor SMTP", "EMAIL_HOST", "smtp.office365.com")
        self.valor("Porta", "EMAIL_PORT", "587")
        self.valor("Usar TLS (true/false)", "EMAIL_USE_TLS", "true")
        usuario = self.valor("Conta que envia (usuário SMTP)", "EMAIL_HOST_USER")
        self.segredo("Senha da conta (não aparece na tela)", "EMAIL_HOST_PASSWORD")
        self.valor("Remetente que aparece no e-mail", "EMAIL_REMETENTE", usuario)
        if self.sim("Enviar um e-mail de teste agora?", True):
            para = input("Para qual endereço: ").strip()
            if para:
                self.manage("testar_email", "--para", para)
        else:
            self.manage("testar_email")

    def whatsapp(self):
        self.titulo("WhatsApp (Digisac)")
        self.stdout.write("Os dados ficam no Digisac: Conta > API > Tokens de acesso pessoal (token) e\n"
                          "Conexões (ID da conexão de WhatsApp que o bot usa).")
        self.valor("Endereço da conta Digisac (ex.: https://empresa.digisac.app)", "DIGISAC_URL")
        self.segredo("Token de acesso do Digisac (não aparece na tela)", "DIGISAC_TOKEN")
        self.valor("ID da conexão de WhatsApp (opcional)", "DIGISAC_SERVICE_ID")
        self.valor("ID do departamento da TI no Digisac (opcional)", "DIGISAC_DEPARTAMENTO_TI_ID")
        if not arquivo_env.ler("DIGISAC_WEBHOOK_TOKEN"):
            arquivo_env.gravar("DIGISAC_WEBHOOK_TOKEN", secrets.token_urlsafe(24))
            self.stdout.write(self.style.SUCCESS("   Segredo do webhook gerado e gravado no .env."))
        if self.manage("testar_digisac") and self.sim(
                "Ligar o WhatsApp agora (o bot passa a responder e a enviar mensagens)?", False):
            arquivo_env.gravar("WHATSAPP_ATIVO", "true")
            arquivo_env.gravar("DIGISAC_ENVIAR_MENSAGENS", "true")
            self.stdout.write(self.style.SUCCESS("   WhatsApp ligado."))
            contato = input("ID de um contato do Digisac para uma mensagem de teste (Enter pula): ").strip()
            if contato:
                self.manage("testar_digisac", "--enviar-para", contato)
        self.stdout.write(self.style.HTTP_INFO("\nNo Digisac, cadastre o webhook (evento message.created) com esta URL:"))
        self.stdout.write(f"   https://SEU_ENDERECO_PUBLICO/webhooks/digisac/?token={arquivo_env.ler('DIGISAC_WEBHOOK_TOKEN')}")
        self.stdout.write("O Digisac fica na internet: SEU_ENDERECO_PUBLICO precisa ser um endereço HTTPS público\n"
                          "(servidor da empresa, porta pública do Codespaces ou ngrok). O nome da máquina na\n"
                          "rede interna não funciona para o webhook. Veja o README.")
