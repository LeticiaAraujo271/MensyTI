#!/usr/bin/env bash
# Liga a Central de TI no Codespaces (roda toda vez que o codespace é aberto; pode rodar à mão).
# Portas: 8000 = chat · 8001 = Painel da TI · 8002 = Administração (as duas redirecionam para a 8000,
# onde fica o login: assim os cookies de segurança ficam sempre num endereço só).
cd "$(dirname "$0")/.."

# Acerta o .env do codespace (também nos codespaces criados antes destas opções).
python - <<'PY'
from apps.portal import arquivo_env as env

valores = {
    "SERVIDOR_HOST": "0.0.0.0",
    "SERVIDOR_ATALHOS": "8001:/painel/,8002:/admin/",
    "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,.app.github.dev",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://*.app.github.dev",
    # Nomes próprios: não se misturam com os de outra Central aberta em localhost no seu computador.
    "DJANGO_COOKIE_SESSAO": "central_sessao",
    "DJANGO_COOKIE_CSRF": "central_csrf",
    # O VS Code instalado no computador abre as portas em http://localhost: cookie sem "só HTTPS".
    "DJANGO_COOKIES_SEGUROS": "false",
}
for chave, valor in valores.items():
    if env.ler(chave) != valor:
        env.gravar(chave, valor)
PY

# Para o servidor antigo (se houver) e liga de novo com a configuração atual.
if pkill -f "python servir.py"; then
  echo "Religando a Central de TI com a configuração atual..."
  sleep 2
fi
python manage.py migrate --noinput --verbosity 0
echo "Ligando a Central de TI: chat na porta 8000, Painel da TI na 8001, Administração na 8002."
echo "Deixe este terminal aberto."
exec python servir.py
