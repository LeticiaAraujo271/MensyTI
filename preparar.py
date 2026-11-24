"""
Prepara a Central de TI neste computador (primeira vez ou depois de atualizar o código).

    python preparar.py

No VS Code: Terminal > Run Task... > "Central: preparar". Não usa PowerShell.

O que faz:
  1. confere se está rodando dentro do ambiente virtual (.venv) e instala as dependências;
  2. cria o .env a partir do .env.example, com uma DJANGO_SECRET_KEY aleatória (se ainda não existe);
  3. atualiza o banco (migrate), a base de conhecimento, os perfis da equipe e os arquivos estáticos;
  4. pede para criar o administrador, se ainda não há nenhum.

Roda de novo quantas vezes quiser: não apaga nem duplica nada.
"""
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from apps.portal import arquivo_env  # noqa: E402  (Python puro, não carrega o Django)


def etapa(n, total, texto):
    print(f"\n[{n}/{total}] {texto}", flush=True)


def rodar(*args, checar=True):
    return subprocess.run([sys.executable, *args], cwd=BASE_DIR, check=checar)


def dentro_do_venv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def main() -> int:
    total = 4
    if not dentro_do_venv():
        print("Este Python não é o do ambiente virtual do projeto.\n"
              "No VS Code: Ctrl+Shift+P > 'Python: Create Environment' > Venv (marque o requirements.txt)\n"
              "e depois rode esta tarefa de novo. Ou, no terminal: python -m venv .venv e use\n"
              "o Python de dentro dele (.venv\\Scripts\\python.exe no Windows, .venv/bin/python no Linux).")
        return 1

    etapa(1, total, "Instalando/conferindo as dependências")
    rodar("-m", "pip", "install", "-r", "requirements.txt", "--quiet", "--disable-pip-version-check")

    etapa(2, total, "Configuração (.env)")
    if not arquivo_env.ARQUIVO.exists():
        shutil.copyfile(arquivo_env.EXEMPLO, arquivo_env.ARQUIVO)
        print("   .env criado a partir do .env.example.")
    if not arquivo_env.ler("DJANGO_SECRET_KEY"):
        arquivo_env.gravar("DJANGO_SECRET_KEY", secrets.token_urlsafe(50))
        print("   DJANGO_SECRET_KEY gerada só para este computador.")
    else:
        print("   .env já existe (nada foi alterado).")

    etapa(3, total, "Banco, base de conhecimento, perfis e arquivos estáticos")
    rodar("manage.py", "migrate", "--noinput")
    rodar("manage.py", "popular_orientacoes")
    rodar("manage.py", "configurar_perfis")
    rodar("manage.py", "collectstatic", "--noinput", "--verbosity", "0")

    etapa(4, total, "Administrador")
    tem_admin = subprocess.run(
        [sys.executable, "manage.py", "shell", "-c",
         "from django.contrib.auth.models import User; print(User.objects.filter(is_superuser=True).exists())"],
        cwd=BASE_DIR, capture_output=True, text=True,
    ).stdout
    if "True" in tem_admin:
        print("   Já existe um administrador.")
    elif sys.stdin and sys.stdin.isatty():
        print("   Nenhum administrador ainda. Crie um agora (usuário, e-mail e senha):")
        rodar("manage.py", "createsuperuser", checar=False)
    else:
        print("   Nenhum administrador ainda. Rode no terminal: python manage.py createsuperuser")

    print("\nPronto! Para ligar:\n"
          "  - testando:          python manage.py runserver   (tarefa 'Central: ligar (desenvolvimento)')\n"
          "  - em segundo plano:  python manage.py servico instalar   (tarefa 'Central: segundo plano - instalar')\n"
          "Endereços: http://127.0.0.1:8000/ (chat) · /painel/ (equipe de TI) · /admin/ (administração)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        print(f"\nParou com erro no comando: {' '.join(map(str, e.cmd[1:]))}")
        sys.exit(e.returncode or 1)
