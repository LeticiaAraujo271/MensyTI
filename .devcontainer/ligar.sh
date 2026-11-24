#!/usr/bin/env bash
# Liga a Central de TI no Codespaces (roda toda vez que o codespace é aberto).
cd "$(dirname "$0")/.."
if curl -s -o /dev/null http://127.0.0.1:8000/; then
  echo "A Central de TI já está no ar (porta 8000)."
  exit 0
fi
python manage.py migrate --noinput --verbosity 0
echo "Ligando a Central de TI na porta 8000. Deixe este terminal aberto."
exec python servir.py
