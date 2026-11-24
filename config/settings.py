"""
Configurações do Chatbot de TI (Digisac + Django).
Todos os valores sensíveis vêm de variáveis de ambiente ou do arquivo .env
(lidos com python-decouple; veja .env.example).
"""
import os
from pathlib import Path

from decouple import AutoConfig, Csv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Lê as variáveis do ambiente do sistema ou, se não existirem, do arquivo .env na raiz.
env = AutoConfig(search_path=BASE_DIR)

# Obrigatória: sem DJANGO_SECRET_KEY no .env o Django não sobe (veja o README).
SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY não definida. Copie o .env.example para .env e gere uma chave "
        "(passo a passo no README.md)."
    )
DEBUG = env("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS", default="", cast=Csv())
# Falha de CSRF em português, com o motivo e o que fazer (e registrada em logs/servidor.log).
CSRF_FAILURE_VIEW = "apps.portal.erros.falha_csrf"

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
    "whitenoise.middleware.WhiteNoiseMiddleware",  # arquivos estáticos (CSS/JS) no Waitress
    "apps.portal.atalhos.AtalhoPorPorta",  # uma porta por tela (SERVIDOR_ATALHOS), usado no Codespaces
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Portas extras que abrem direto numa tela (ex.: no Codespaces, 8001 = painel e 8002 = admin).
SERVIDOR_ATALHOS = env("SERVIDOR_ATALHOS", default="")
SERVIDOR_PORTA = env("SERVIDOR_PORTA", default=8000, cast=int)

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
                "apps.portal.contexto.marca",  # logo da marca d'água (opcional)
            ],
        },
    },
]

# Banco: SQLite por padrão; PostgreSQL se DB_NAME estiver definido.
if env("DB_NAME", default=""):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME"),
            "USER": env("DB_USER", default="postgres"),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default="localhost"),
            "PORT": env("DB_PORT", default="5432"),
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
# Serve os estáticos direto das pastas dos apps: funciona mesmo sem rodar collectstatic.
WHITENOISE_USE_FINDERS = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Painel de TI (login da equipe)
LOGIN_URL = "painel:login"
LOGIN_REDIRECT_URL = "painel:fila"
LOGOUT_REDIRECT_URL = "painel:login"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env("DJANGO_COOKIES_SEGUROS", default=not DEBUG, cast=bool)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
# Nomes dos cookies (o Codespaces usa nomes próprios para não misturar com outra Central em localhost)
SESSION_COOKIE_NAME = env("DJANGO_COOKIE_SESSAO", default="sessionid")
CSRF_COOKIE_NAME = env("DJANGO_COOKIE_CSRF", default="csrftoken")

# GitHub Codespaces: libera os endereços exatos das portas (pelo navegador ou pelo VS Code instalado,
# que encaminha as portas para localhost).
_CODESPACE = os.environ.get("CODESPACE_NAME", "")
_DOMINIO_CODESPACE = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "")
if _CODESPACE and _DOMINIO_CODESPACE:
    _portas_extras = [int(i.split(":")[0]) for i in SERVIDOR_ATALHOS.split(",") if i.split(":")[0].strip().isdigit()]
    for _p in [SERVIDOR_PORTA, *_portas_extras]:
        for _origem in (f"https://{_CODESPACE}-{_p}.{_DOMINIO_CODESPACE}", f"http://localhost:{_p}",
                        f"http://127.0.0.1:{_p}"):
            if _origem not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(_origem)
    for _h in (f".{_DOMINIO_CODESPACE}", "localhost", "127.0.0.1"):
        if _h not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_h)
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True

# --------------------------------------------------------------------------
# Central de TI (portal web: canal principal)
# --------------------------------------------------------------------------
CENTRAL = {
    "NOME": env("CENTRAL_NOME", default="Central de TI"),
    # Campos pedidos na identificação, na ordem: nome, setor, centro_custo, email, matricula
    "IDENTIFICACAO": env("CENTRAL_IDENTIFICACAO", default="nome,setor,centro_custo,email", cast=Csv()),
    # Domínios aceitos no e-mail corporativo (vazio = qualquer). Ex.: empresa.com.br
    "DOMINIOS_EMAIL": env("CENTRAL_DOMINIOS_EMAIL", default="", cast=Csv(str.lower)),
    # Limite de mensagens por minuto por navegador (proteção contra abuso)
    "LIMITE_MENSAGENS_MINUTO": env("CENTRAL_LIMITE_MENSAGENS_MINUTO", default=20, cast=int),
    # Endereço da Central que vai nos links de aprovação enviados por e-mail. Ex.: http://nb332:8000
    "URL": env("CENTRAL_URL", default="").rstrip("/"),
}

# --------------------------------------------------------------------------
# E-mail (links de aprovação para o coordenador e o gerente da área)
# Sem EMAIL_HOST, nada é enviado: a TI copia o link no painel e manda pelo Teams/e-mail.
# --------------------------------------------------------------------------
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = env("EMAIL_REMETENTE", default=EMAIL_HOST_USER or "central-ti@localhost")
APROVACAO_ENVIAR_EMAIL = env("APROVACAO_ENVIAR_EMAIL", default=bool(EMAIL_HOST), cast=bool)

# Canal WhatsApp (opcional). Desligado: o webhook ignora as mensagens e nada é enviado.
WHATSAPP_ATIVO = env("WHATSAPP_ATIVO", default=False, cast=bool)

# --------------------------------------------------------------------------
# Digisac
# --------------------------------------------------------------------------
DIGISAC = {
    # Endereço da sua conta, ex.: https://suaempresa.digisac.app
    "URL": env("DIGISAC_URL", default="").rstrip("/"),
    # Conta > API > Tokens de acesso pessoal
    "TOKEN": env("DIGISAC_TOKEN", default=""),
    # ID da conexão (WhatsApp) usada pelo bot — opcional
    "SERVICE_ID": env("DIGISAC_SERVICE_ID", default=""),
    # ID do departamento (fila) da TI para onde o bot transfere
    "DEPARTAMENTO_TI_ID": env("DIGISAC_DEPARTAMENTO_TI_ID", default=""),
    # Segredo que vai na URL do webhook: /webhooks/digisac/?token=XYZ
    "WEBHOOK_TOKEN": env("DIGISAC_WEBHOOK_TOKEN", default=""),
    # Se False, o bot só registra as respostas no log (útil para testes)
    "ENVIAR_MENSAGENS": env("DIGISAC_ENVIAR_MENSAGENS", default=True, cast=bool),
    "TIMEOUT_SEGUNDOS": env("DIGISAC_TIMEOUT_SEGUNDOS", default=10, cast=int),
}

# --------------------------------------------------------------------------
# Regras do bot
# --------------------------------------------------------------------------
BOT = {
    # Depois de quantos minutos sem resposta a conversa recomeça do início
    "TIMEOUT_MINUTOS": env("BOT_TIMEOUT_MINUTOS", default=30, cast=int),
    # Horário de atendimento humano. Dias: 0=segunda ... 6=domingo
    "HORARIO_DIAS": env("BOT_HORARIO_DIAS", default="0,1,2,3,4", cast=Csv(int)),
    "HORARIO_INICIO": env("BOT_HORARIO_INICIO", default="08:00"),
    "HORARIO_FIM": env("BOT_HORARIO_FIM", default="18:00"),
    "TEXTO_HORARIO": env("BOT_TEXTO_HORARIO", default="segunda a sexta, das 8h às 18h"),
    # Por quanto tempo a pesquisa de satisfação fica esperando a resposta do colaborador
    "PESQUISA_HORAS": env("BOT_PESQUISA_HORAS", default=72, cast=int),
}

# --------------------------------------------------------------------------
# Chamados: sempre ficam na Central de TI. Opcionalmente, também em um sistema externo.
# --------------------------------------------------------------------------
CHAMADOS_BACKEND = env("CHAMADOS_BACKEND", default="apps.chamados.backends.BackendLocal")
# SLA de quem não tem categoria (ex.: "Falar com a equipe de TI" direto do menu) = o de "Outros".
# O SLA de cada categoria é editado no Admin, em Categorias. Contado em horas úteis (horário acima).
SLA_PADRAO_HORAS = env("SLA_PADRAO_HORAS", default=72, cast=int)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simples": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simples"}},
    "loggers": {
        "apps": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    },
}
