# Central de TI - prepara (na primeira vez) e inicia o servidor local.
# Uso, na pasta do projeto:
#   powershell -ExecutionPolicy Bypass -File .\iniciar.ps1
# Depois abra http://127.0.0.1:8000/ (chat), /painel/ (equipe) e /admin/ (administração).

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "1/5 Criando o ambiente virtual (.venv)..." -ForegroundColor Green
    python -m venv .venv
    Write-Host "2/5 Instalando as dependências..." -ForegroundColor Green
    & $py -m pip install --upgrade pip --quiet
    & $py -m pip install -r requirements.txt
} else {
    Write-Host "Ambiente virtual já existe." -ForegroundColor Green
}

if (-not (Test-Path ".env")) {
    Write-Host "3/5 Criando o .env a partir do .env.example..." -ForegroundColor Green
    Copy-Item .env.example .env
}

Write-Host "4/5 Atualizando o banco e a base de conhecimento..." -ForegroundColor Green
& $py manage.py migrate --noinput
& $py manage.py popular_orientacoes
& $py manage.py configurar_perfis

$temAdmin = & $py manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.filter(is_superuser=True).exists())"
if ($temAdmin -notmatch "True") {
    Write-Host ""
    Write-Host "Nenhum administrador cadastrado ainda. Crie um agora (usuário, e-mail e senha):" -ForegroundColor Yellow
    & $py manage.py createsuperuser
}

Write-Host ""
Write-Host "5/5 Servidor no ar. Deixe esta janela aberta; Ctrl+C para parar." -ForegroundColor Green
Write-Host "  Chat do colaborador: http://127.0.0.1:8000/"
Write-Host "  Painel da TI:        http://127.0.0.1:8000/painel/"
Write-Host "  Administração:       http://127.0.0.1:8000/admin/"
& $py manage.py runserver 127.0.0.1:8000
