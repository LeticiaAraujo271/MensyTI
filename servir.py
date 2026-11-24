"""
Liga a Central de TI com o Waitress (servidor de produção que funciona no Windows).

Diferente do `manage.py runserver`, roda sem janela aberta: é o que a tarefa agendada
criada por `python manage.py servico instalar` executa (com pythonw.exe) sempre que você entra no Windows.

Uso manual:  python servir.py   (com o Python do .venv; no VS Code: tarefa "Central: ligar como servidor")
Endereço e porta: SERVIDOR_HOST e SERVIDOR_PORTA no .env (padrão 127.0.0.1:8000).
Portas extras por tela (opcional): SERVIDOR_ATALHOS=8001:/painel/,8002:/admin/
O log fica em logs\\servidor.log.
"""
import atexit
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Com pythonw.exe não existe console: tudo vai para o arquivo de log.
(BASE_DIR / "logs").mkdir(exist_ok=True)
arquivo = RotatingFileHandler(BASE_DIR / "logs" / "servidor.log", maxBytes=5_000_000,
                              backupCount=3, encoding="utf-8")
arquivo.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
if sys.stdout is None or sys.stderr is None:  # pythonw.exe
    sys.stdout = sys.stderr = open(BASE_DIR / "logs" / "saida.log", "a", encoding="utf-8", buffering=1)
    handlers = [arquivo]
else:  # rodando num terminal (ex.: GitHub Codespaces): mostra o log na tela também
    tela = logging.StreamHandler()
    tela.setFormatter(arquivo.formatter)
    handlers = [arquivo, tela]
logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)


def main() -> None:
    from decouple import AutoConfig
    from django.core.wsgi import get_wsgi_application
    from waitress import serve

    env = AutoConfig(search_path=BASE_DIR)
    host = env("SERVIDOR_HOST", default="127.0.0.1")
    porta = env("SERVIDOR_PORTA", default=8000, cast=int)

    app = get_wsgi_application()
    from apps.portal.atalhos import ler_atalhos

    log = logging.getLogger("servir")
    # Portas extras que abrem direto numa tela (SERVIDOR_ATALHOS, ex.: 8001:/painel/,8002:/admin/)
    atalhos = {p: c for p, c in ler_atalhos(env("SERVIDOR_ATALHOS", default="")).items() if p != porta}
    log.info("Central de TI no ar em http://%s:%s/", host, porta)
    for p, caminho in atalhos.items():
        log.info("  atalho: http://%s:%s/ abre %s", host, p, caminho)
    portas = [porta, *atalhos]
    # PID para o "manage.py servico" saber qual processo parar ao reiniciar.
    arquivo_pid = BASE_DIR / "logs" / "servidor.pid"
    arquivo_pid.write_text(str(os.getpid()))
    atexit.register(lambda: arquivo_pid.unlink(missing_ok=True))
    serve(app, listen=" ".join(f"{host}:{p}" for p in portas), threads=8, ident="CentralTI")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.getLogger("servir").exception("O servidor parou com erro")
        raise
