#!/usr/bin/env bash
# Liga a Central de TI no Codespaces (roda toda vez que o codespace é aberto).
# Portas: 8000 = chat · 8001 = Painel da TI · 8002 = Administração
cd "$(dirname "$0")/.."

# Codespaces criados antes das portas por tela: acrescenta a configuração no .env.
if [ -f .env ] && ! grep -q '^SERVIDOR_ATALHOS=' .env; then
  printf '\n# Uma porta por tela (aba PORTS): 8001 = painel, 8002 = administração\nSERVIDOR_ATALHOS=8001:/painel/,8002:/admin/\n' >> .env
fi

if curl -s -o /dev/null http://127.0.0.1:8000/; then
  if curl -s -o /dev/null http://127.0.0.1:8001/; then
    echo "A Central de TI já está no ar (portas 8000, 8001 e 8002)."
    exit 0
  fi
  echo "A Central está no ar sem as portas do painel e da administração: religando."
  pkill -f "python servir.py" || true
  sleep 2
fi
python manage.py migrate --noinput --verbosity 0
echo "Ligando a Central de TI: chat na porta 8000, Painel da TI na 8001, Administração na 8002."
echo "Deixe este terminal aberto."
exec python servir.py
