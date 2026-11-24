"""
Liga a Central de TI com o Waitress (servidor de produção que funciona no Windows).

Diferente do `manage.py runserver`, roda sem janela aberta: é o que a tarefa agendada
criada por `instalar_servico.ps1` executa (com pythonw.exe) sempre que você entra no Windows.

Uso manual:  .venv\\Scripts\\python.exe servir.py
Endereço e porta: SERVIDOR_HOST e SERVIDOR_PORTA no .env (padrão 127.0.0.1:8000).
O log fica em logs\\servidor.log.
"""
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
logging.basicConfig(level=logging.INFO, handlers=[arquivo], force=True)
if sys.stdout is None or sys.stderr is None:  # pythonw.exe
    sys.stdout = sys.stderr = open(BASE_DIR / "logs" / "saida.log", "a", encoding="utf-8", buffering=1)


def main() -> None:
    from decouple import AutoConfig
    from django.core.wsgi import get_wsgi_application
    from waitress import serve

    env = AutoConfig(search_path=BASE_DIR)
    host = env("SERVIDOR_HOST", default="127.0.0.1")
    porta = env("SERVIDOR_PORTA", default=8000, cast=int)

    app = get_wsgi_application()
    logging.getLogger("servir").info("Central de TI no ar em http://%s:%s/", host, porta)
    serve(app, host=host, port=porta, threads=8, ident="CentralTI")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.getLogger("servir").exception("O servidor parou com erro")
        raise
