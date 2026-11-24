#!/usr/bin/env bash
# Prepara a Central de TI no GitHub Codespaces (roda uma vez, quando o codespace é criado).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Instalando as dependências"
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

if [ ! -f .env ]; then
  echo "==> Criando o .env do codespace"
  cp .env.example .env
  chave=$(python -c "import secrets; print(secrets.token_urlsafe(50))")
  python - "$chave" <<'PY'
import sys
from pathlib import Path
p = Path(".env")
valores = {
    "DJANGO_SECRET_KEY": sys.argv[1],
    "DJANGO_DEBUG": "false",
    # O Codespaces entrega a página em https://<nome>-8000.app.github.dev
    "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,.app.github.dev",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://*.app.github.dev",
    "SERVIDOR_HOST": "0.0.0.0",
}
linhas = []
for linha in p.read_text(encoding="utf-8").splitlines():
    chave = linha.split("=", 1)[0].strip()
    linhas.append(f"{chave}={valores.pop(chave)}" if chave in valores and not linha.startswith("#") else linha)
linhas += [f"{k}={v}" for k, v in valores.items()]
p.write_text("\n".join(linhas) + "\n", encoding="utf-8")
PY
fi

echo "==> Preparando o banco e a base de conhecimento"
python manage.py migrate --noinput
python manage.py popular_orientacoes
python manage.py configurar_perfis
python manage.py collectstatic --noinput --verbosity 0

if [ ! -f ACESSO_CODESPACE.txt ]; then
  echo "==> Criando o administrador"
  senha=$(python -c "import secrets; print(secrets.token_urlsafe(12))")
  DJANGO_SUPERUSER_PASSWORD="$senha" python manage.py createsuperuser --noinput \
    --username admin --email admin@example.com || true
  cat > ACESSO_CODESPACE.txt <<TXT
Central de TI no GitHub Codespaces
==================================

A tela abre sozinha numa aba nova do navegador. Se não abrir: aba "PORTS"
(aqui embaixo) > linha "Central de TI (8000)" > clique no ícone do globo.

  Chat:          (endereço da porta 8000)/
  Painel de TI:  (endereço da porta 8000)/painel/
  Administração: (endereço da porta 8000)/admin/

Login do painel e da administração:
  Usuário: admin
  Senha:   $senha

Troque a senha em /admin/ > Usuários. Este arquivo fica só neste codespace
(não vai para o GitHub).
TXT
fi

echo "==> Pronto. Veja o usuário e a senha em ACESSO_CODESPACE.txt"
