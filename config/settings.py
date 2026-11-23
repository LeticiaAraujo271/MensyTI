"""
Configurações do Chatbot de TI (Digisac + Django).
Todos os valores sensíveis vêm de variáveis de ambiente (veja .env.example).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _carregar_env(caminho: Path) -> None:
    """Lê um arquivo .env simples (CHAVE=valor) sem depender de bibliotecas."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env(BASE_DIR / ".env")


def env(nome, padrao=None):
    return os.environ.get(nome, padrao)


def env_bool(nome, padrao=False):
    return str(env(nome, padrao)).lower() in {"1", "true", "sim", "yes"}


SECRET_KEY = env("DJANGO_SECRET_KEY", "troque-esta-chave-em-producao")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps do projeto
    "apps.orientacoes",
    "apps.bot",
    "apps.chamados",
    "apps.digisac",
    "apps.portal",
    "apps.painel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # templates/admin/base_site.html = tema Mensori do Admin
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Banco: SQLite por padrão; PostgreSQL se DB_NAME estiver definido.
if env("DB_NAME"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME"),
            "USER": env("DB_USER", "postgres"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Painel de TI (login da equipe)
LOGIN_URL = "painel:login"
LOGIN_REDIRECT_URL = "painel:fila"
LOGOUT_REDIRECT_URL = "painel:login"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env_bool("DJANGO_COOKIES_SEGUROS", not DEBUG)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True

# --------------------------------------------------------------------------
# Central de TI (portal web: canal principal)
# --------------------------------------------------------------------------
CENTRAL = {
    "NOME": env("CENTRAL_NOME", "Central de TI"),
    # Campos pedidos na identificação, na ordem: nome, setor, email, matricula
    "IDENTIFICACAO": [c.strip() for c in env("CENTRAL_IDENTIFICACAO", "nome,setor,email").split(",") if c.strip()],
    # Domínios aceitos no e-mail corporativo (vazio = qualquer). Ex.: empresa.com.br
    "DOMINIOS_EMAIL": [d.strip().lower() for d in env("CENTRAL_DOMINIOS_EMAIL", "").split(",") if d.strip()],
    # Limite de mensagens por minuto por navegador (proteção contra abuso)
    "LIMITE_MENSAGENS_MINUTO": int(env("CENTRAL_LIMITE_MENSAGENS_MINUTO", "20")),
}

# Canal WhatsApp (opcional). Desligado: o webhook ignora as mensagens e nada é enviado.
WHATSAPP_ATIVO = env_bool("WHATSAPP_ATIVO", False)

# --------------------------------------------------------------------------
# Digisac
# --------------------------------------------------------------------------
DIGISAC = {
    # Endereço da sua conta, ex.: https://suaempresa.digisac.app
    "URL": env("DIGISAC_URL", "").rstrip("/"),
    # Conta > API > Tokens de acesso pessoal
    "TOKEN": env("DIGISAC_TOKEN", ""),
    # ID da conexão (WhatsApp) usada pelo bot — opcional
    "SERVICE_ID": env("DIGISAC_SERVICE_ID", ""),
    # ID do departamento (fila) da TI para onde o bot transfere
    "DEPARTAMENTO_TI_ID": env("DIGISAC_DEPARTAMENTO_TI_ID", ""),
    # Segredo que vai na URL do webhook: /webhooks/digisac/?token=XYZ
    "WEBHOOK_TOKEN": env("DIGISAC_WEBHOOK_TOKEN", ""),
    # Se False, o bot só registra as respostas no log (útil para testes)
    "ENVIAR_MENSAGENS": env_bool("DIGISAC_ENVIAR_MENSAGENS", True),
    "TIMEOUT_SEGUNDOS": int(env("DIGISAC_TIMEOUT_SEGUNDOS", "10")),
}

# --------------------------------------------------------------------------
# Regras do bot
# --------------------------------------------------------------------------
BOT = {
    # Depois de quantos minutos sem resposta a conversa recomeça do início
    "TIMEOUT_MINUTOS": int(env("BOT_TIMEOUT_MINUTOS", "30")),
    # Horário de atendimento humano. Dias: 0=segunda ... 6=domingo
    "HORARIO_DIAS": [int(d) for d in env("BOT_HORARIO_DIAS", "0,1,2,3,4").split(",")],
    "HORARIO_INICIO": env("BOT_HORARIO_INICIO", "08:00"),
    "HORARIO_FIM": env("BOT_HORARIO_FIM", "18:00"),
    "TEXTO_HORARIO": env("BOT_TEXTO_HORARIO", "segunda a sexta, das 8h às 18h"),
}

# --------------------------------------------------------------------------
# Chamados: sempre ficam na Central de TI. Opcionalmente, também em um sistema externo.
# --------------------------------------------------------------------------
CHAMADOS_BACKEND = env("CHAMADOS_BACKEND", "apps.chamados.backends.BackendLocal")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simples": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simples"}},
    "loggers": {
        "apps": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    },
}
