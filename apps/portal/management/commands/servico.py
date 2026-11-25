"""
Central de TI em segundo plano no Windows (sem PowerShell e sem janela aberta).

    python manage.py servico instalar    prepara e cria a tarefa "Central de TI": liga ao entrar no
                                         Windows e religa sozinha se o servidor cair
    python manage.py servico status      mostra se está no ar
    python manage.py servico reiniciar   religa (depois de mudar o .env ou atualizar o código)
    python manage.py servico remover     desliga e tira da inicialização
    python manage.py servico rede        libera o acesso dos colegas da rede

No VS Code: Terminal > Run Task... > "Central: segundo plano - ...".
A tarefa roda o servir.py com o pythonw.exe do .venv. O log fica em logs\\servidor.log.
"""
from __future__ import annotations

import ctypes
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.portal import arquivo_env
from apps.portal.atalhos import ler_atalhos

TAREFA = "Central de TI"
BASE_DIR = Path(settings.BASE_DIR)
ARQUIVO_PID = BASE_DIR / "logs" / "servidor.pid"
WINDOWS = os.name == "nt"
SAIDA_CONSOLE = "oem" if WINDOWS else "utf-8"  # schtasks/netsh escrevem na página de código do console


def _cmd(*args) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), capture_output=True, text=True, encoding=SAIDA_CONSOLE, errors="replace")


def _porta() -> int:
    valor = arquivo_env.ler("SERVIDOR_PORTA")
    return int(valor) if valor.isdigit() else 8000


def _portas() -> list[int]:
    return [_porta(), *ler_atalhos(arquivo_env.ler("SERVIDOR_ATALHOS"))]


def _no_ar(porta: int, segundos: float = 1) -> bool:
    limite = time.monotonic() + segundos
    while True:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{porta}/", timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        if time.monotonic() >= limite:
            return False
        time.sleep(0.7)


def _tarefa_existe() -> bool:
    return _cmd("schtasks", "/Query", "/TN", TAREFA).returncode == 0


def _processo_python(pid: int) -> bool:
    r = _cmd("tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH")
    return r.stdout.strip().lower().startswith('"python')


def _pids_nas_portas(portas: list[int]) -> set[int]:
    """Processos escutando nas portas da Central (netstat funciona em qualquer idioma do Windows)."""
    pids = set()
    for linha in _cmd("netstat", "-ano", "-p", "TCP").stdout.splitlines():
        partes = linha.split()
        if len(partes) >= 5 and partes[0].upper() == "TCP" and partes[2] in ("0.0.0.0:0", "[::]:0"):
            if any(partes[1].endswith(f":{p}") for p in portas) and partes[-1].isdigit():
                pids.add(int(partes[-1]))
    return pids


def _arquivos_pid() -> list[Path]:
    # servidor-<pid>.pid: um por processo, gravado logo no início do servir.py (pega até os que
    # travaram ao ligar, sem abrir a porta). servidor.pid: formato antigo.
    return [*ARQUIVO_PID.parent.glob("servidor-*.pid"), ARQUIVO_PID]


def _parar() -> None:
    if _tarefa_existe():
        _cmd("schtasks", "/End", "/TN", TAREFA)
    pids = _pids_nas_portas(_portas())
    for arquivo in _arquivos_pid():
        try:
            pids.add(int(arquivo.read_text().strip()))
        except (OSError, ValueError):
            pass
    for pid in pids:
        if pid != os.getpid() and _processo_python(pid):  # só encerra servidores Python desta Central
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    time.sleep(1)
    for arquivo in _arquivos_pid():
        arquivo.unlink(missing_ok=True)


def _xml_da_tarefa() -> str:
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        raise CommandError(f"Não achei {pythonw}. Rode este comando com o Python do .venv do projeto.")
    usuario = escape(f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}".lstrip("\\"))
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>{escape(f"Servidor da Central de TI (chat + painel). Pasta: {BASE_DIR}")}</Description></RegistrationInfo>
  <Triggers><LogonTrigger><Enabled>true</Enabled><UserId>{usuario}</UserId></LogonTrigger></Triggers>
  <Principals>
    <Principal id="Author"><UserId>{usuario}</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <!-- 4 = prioridade normal. O padrão das tarefas (7) deixa processador e disco em prioridade
         baixa: o Django levava de 15 s a mais de 1 min para ligar e às vezes parecia travado. -->
    <Priority>4</Priority>
    <RestartOnFailure><Interval>PT1M</Interval><Count>999</Count></RestartOnFailure>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(str(pythonw))}</Command>
      <Arguments>"{escape(str(BASE_DIR / "servir.py"))}"</Arguments>
      <WorkingDirectory>{escape(str(BASE_DIR))}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def _ip_da_rede() -> str:
    """IP da placa ligada à rede (não envia nada: só pergunta ao sistema qual seria a rota)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return ""


def _admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


class Command(BaseCommand):
    help = "Central de TI em segundo plano no Windows: instalar, status, reiniciar, remover, rede."

    def add_arguments(self, parser):
        parser.add_argument("acao", choices=["instalar", "status", "reiniciar", "remover", "rede"])

    def handle(self, *args, acao, **opts):
        if not WINDOWS:
            raise CommandError("Este comando é para o Windows. No Codespaces/Linux a Central liga com "
                               "'python servir.py' (o Codespaces já faz isso sozinho).")
        getattr(self, f"_{acao}")()

    # --- ações -------------------------------------------------------------
    def _status(self):
        porta = _porta()
        if not _tarefa_existe():
            self.stdout.write(self.style.WARNING(f"A tarefa '{TAREFA}' não está instalada "
                                                 "(python manage.py servico instalar)."))
        else:
            linha = _cmd("schtasks", "/Query", "/TN", TAREFA, "/FO", "CSV", "/NH").stdout.strip()
            estado = linha.split('","')[-1].strip('"') if linha else "?"
            self.stdout.write(f"Tarefa '{TAREFA}': {estado}")
        if _no_ar(porta):
            self.stdout.write(self.style.SUCCESS(f"Central no ar: http://127.0.0.1:{porta}/"))
        else:
            self.stdout.write(self.style.ERROR("A Central não está respondendo. Rode o reiniciar (tarefa \"Central: "
                                               "segundo plano - reiniciar\"); se continuar, veja logs\\servidor.log."))

    def _reiniciar(self):
        if not _tarefa_existe():
            raise CommandError(f"A tarefa '{TAREFA}' não está instalada: rode 'python manage.py servico instalar'.")
        _parar()
        _cmd("schtasks", "/Run", "/TN", TAREFA)
        porta = _porta()
        if _no_ar(porta, 60):
            self.stdout.write(self.style.SUCCESS(f"Central religada: http://127.0.0.1:{porta}/"))
        else:
            raise CommandError("A Central não respondeu. Veja logs\\servidor.log e logs\\saida.log.")

    def _remover(self):
        _parar()
        if _tarefa_existe():
            _cmd("schtasks", "/Delete", "/TN", TAREFA, "/F")
        self.stdout.write(self.style.SUCCESS("Central de TI desligada e removida da inicialização."))

    def _instalar(self):
        self.stdout.write("Preparando (dependências, .env, banco)...")
        if subprocess.run([sys.executable, str(BASE_DIR / "preparar.py")], cwd=BASE_DIR).returncode != 0:
            raise CommandError("O preparo falhou (veja a mensagem acima).")
        _parar()
        with tempfile.TemporaryDirectory() as pasta:
            xml = Path(pasta) / "tarefa.xml"
            xml.write_text(_xml_da_tarefa(), encoding="utf-16")
            r = _cmd("schtasks", "/Create", "/TN", TAREFA, "/XML", str(xml), "/F")
        if r.returncode != 0:
            raise CommandError(f"O Windows não criou a tarefa: {r.stderr.strip() or r.stdout.strip()}")
        _cmd("schtasks", "/Run", "/TN", TAREFA)
        porta = _porta()
        if not _no_ar(porta, 60):
            raise CommandError("A tarefa foi criada, mas a Central não respondeu. Veja logs\\servidor.log.")
        self.stdout.write(self.style.SUCCESS(
            "\nPronto! A Central está rodando em segundo plano e liga sozinha ao entrar no Windows."))
        self.stdout.write(f"  Chat do colaborador: http://127.0.0.1:{porta}/\n"
                          f"  Painel da TI:        http://127.0.0.1:{porta}/painel/\n"
                          f"  Administração:       http://127.0.0.1:{porta}/admin/\n"
                          "Pode fechar o VS Code: ela continua no ar.")

    def _rede(self):
        if not arquivo_env.ARQUIVO.exists():
            raise CommandError("Não achei o .env. Rode antes: python preparar.py")
        ip = _ip_da_rede()
        if not ip or ip.startswith("127."):
            raise CommandError("Não encontrei a rede deste computador. Ele está conectado?")
        nome = socket.gethostname().lower()
        porta = _porta()

        # 1) .env: aceita conexões da rede e os endereços pelos quais os colegas vão chegar
        hosts = [h.strip() for h in arquivo_env.ler("DJANGO_ALLOWED_HOSTS").split(",") if h.strip()]
        for h in ("localhost", "127.0.0.1", ip, nome):
            if h not in hosts:
                hosts.append(h)
        arquivo_env.gravar("SERVIDOR_HOST", "0.0.0.0")
        arquivo_env.gravar("DJANGO_ALLOWED_HOSTS", ",".join(hosts))
        arquivo_env.gravar("DJANGO_DEBUG", "false")            # ninguém vê detalhes técnicos de erro
        arquivo_env.gravar("DJANGO_COOKIES_SEGUROS", "false")  # o login funciona em http:// na rede
        if not arquivo_env.ler("CENTRAL_URL"):
            arquivo_env.gravar("CENTRAL_URL", f"http://{nome}:{porta}", comentario="Endereço que vai nos links de aprovação")
        self.stdout.write(self.style.SUCCESS(f"1/3 .env ajustado para a rede ({ip})."))

        # 2) Firewall do Windows: só nas redes do domínio e privadas (nunca em Wi-Fi público)
        regra = (f'netsh advfirewall firewall add rule name="{TAREFA}" dir=in action=allow '
                 f"protocol=TCP localport={porta} profile=domain,private")
        if _cmd("netsh", "advfirewall", "firewall", "show", "rule", f"name={TAREFA}").returncode == 0:
            self.stdout.write(self.style.SUCCESS(f"2/3 A porta {porta} já está liberada no firewall."))
        elif _admin():
            r = _cmd("netsh", "advfirewall", "firewall", "add", "rule", f"name={TAREFA}", "dir=in",
                     "action=allow", "protocol=TCP", f"localport={porta}", "profile=domain,private")
            if r.returncode == 0:
                self.stdout.write(self.style.SUCCESS(f"2/3 Porta {porta} liberada no firewall."))
            else:
                self.stdout.write(self.style.ERROR(f"2/3 O firewall recusou: {r.stdout.strip()}"))
        else:
            self.stdout.write(self.style.WARNING(
                "2/3 Liberar a porta no firewall exige administrador, e este usuário não é.\n"
                "    Peça a quem tem acesso de administrador para rodar, no Prompt de Comando como administrador:\n"
                f"    {regra}"))

        # 3) Religa (ou instala) com a nova configuração
        self.stdout.write("3/3 Religando a Central...")
        self._reiniciar() if _tarefa_existe() else self._instalar()
        self.stdout.write(self.style.SUCCESS(
            "\nEndereços para os colegas (na mesma rede, depois do firewall liberado):"))
        self.stdout.write(f"  Chat:          http://{nome}:{porta}/   ou  http://{ip}:{porta}/\n"
                          f"  Painel da TI:  http://{nome}:{porta}/painel/\n"
                          f"  Administração: http://{nome}:{porta}/admin/")
