# Central de TI - deixa o servidor rodando sozinho, em segundo plano, neste computador.
#
# Cria a tarefa agendada "Central de TI" do Windows, que:
#   - liga a Central sempre que você entra no Windows (sem janela aberta);
#   - religa sozinha se o servidor cair;
#   - não depende de nenhum terminal, editor ou sessão ficar aberto.
#
# Uso, na pasta do projeto (não precisa ser administrador):
#   powershell -ExecutionPolicy Bypass -File .\instalar_servico.ps1            instala e liga
#   powershell -ExecutionPolicy Bypass -File .\instalar_servico.ps1 -Status    mostra se está no ar
#   powershell -ExecutionPolicy Bypass -File .\instalar_servico.ps1 -Reiniciar religa (depois de mudar o .env ou atualizar o código)
#   powershell -ExecutionPolicy Bypass -File .\instalar_servico.ps1 -Remover   desliga e remove
#   powershell -ExecutionPolicy Bypass -File .\instalar_servico.ps1 -Rede      libera o acesso para os colegas da rede
param([switch]$Remover, [switch]$Status, [switch]$Reiniciar, [switch]$Rede)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$nomeTarefa = "Central de TI"

function Get-Porta {
    $linha = Get-Content (Join-Path $PSScriptRoot ".env") -ErrorAction SilentlyContinue |
        Where-Object { $_ -match '^\s*SERVIDOR_PORTA\s*=\s*(\d+)' } | Select-Object -First 1
    if ($linha -and $linha -match '(\d+)\s*$') { return [int]$Matches[1] }
    return 8000
}

function Set-EnvValor {
    param([string]$Chave, [string]$Valor)
    $arquivo = Join-Path $PSScriptRoot ".env"
    $linhas = @(Get-Content $arquivo -Encoding UTF8)
    $achou = $false
    $linhas = $linhas | ForEach-Object {
        if ($_ -match "^\s*$Chave\s*=") { $achou = $true; "$Chave=$Valor" } else { $_ }
    }
    if (-not $achou) { $linhas = @($linhas) + "$Chave=$Valor" }
    [System.IO.File]::WriteAllLines($arquivo, [string[]]$linhas, (New-Object System.Text.UTF8Encoding $false))
}

function Get-EnvValor {
    param([string]$Chave)
    $linha = Get-Content (Join-Path $PSScriptRoot ".env") -Encoding UTF8 -ErrorAction SilentlyContinue |
        Where-Object { $_ -match "^\s*$Chave\s*=" } | Select-Object -First 1
    if ($linha) { return ($linha -split "=", 2)[1].Trim() }
    return ""
}

function Get-IpDaRede {
    # IP da placa de rede que tem gateway (a que está ligada à rede da empresa)
    $ip = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq "Up" } |
        ForEach-Object { $_.IPv4Address.IPAddress } | Select-Object -First 1
    return $ip
}

function Test-NoAr {
    param([int]$Porta, [int]$Segundos = 1)
    $limite = (Get-Date).AddSeconds($Segundos)
    do {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Porta/" -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -eq 200) { return $true }
        } catch { }
        Start-Sleep -Milliseconds 700
    } while ((Get-Date) -lt $limite)
    return $false
}

function Stop-Central {
    $tarefa = Get-ScheduledTask -TaskName $nomeTarefa -ErrorAction SilentlyContinue
    if ($tarefa) { Stop-ScheduledTask -TaskName $nomeTarefa -ErrorAction SilentlyContinue }
    # Garante que nenhum servir.py deste projeto ficou para trás
    $script = (Join-Path $PSScriptRoot "servir.py")
    Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
        Where-Object { $_.CommandLine -and $_.CommandLine -like "*$script*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

$porta = Get-Porta

if ($Status) {
    $tarefa = Get-ScheduledTask -TaskName $nomeTarefa -ErrorAction SilentlyContinue
    if (-not $tarefa) { Write-Host "A tarefa '$nomeTarefa' não está instalada." -ForegroundColor Yellow; return }
    Write-Host "Tarefa '$nomeTarefa': $($tarefa.State)"
    if (Test-NoAr -Porta $porta) { Write-Host "Central no ar: http://127.0.0.1:$porta/" -ForegroundColor Green }
    else { Write-Host "A Central não está respondendo. Veja logs\servidor.log e logs\saida.log." -ForegroundColor Red }
    return
}

if ($Remover) {
    Stop-Central
    if (Get-ScheduledTask -TaskName $nomeTarefa -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $nomeTarefa -Confirm:$false
    }
    Write-Host "Central de TI desligada e removida da inicialização." -ForegroundColor Green
    return
}

if ($Reiniciar) {
    Stop-Central
    Start-ScheduledTask -TaskName $nomeTarefa
    if (Test-NoAr -Porta $porta -Segundos 30) { Write-Host "Central religada: http://127.0.0.1:$porta/" -ForegroundColor Green }
    else { Write-Host "A Central não respondeu. Veja logs\servidor.log e logs\saida.log." -ForegroundColor Red }
    return
}

if ($Rede) {
    if (-not (Test-Path (Join-Path $PSScriptRoot ".env"))) { & (Join-Path $PSScriptRoot "iniciar.ps1") -SoPreparar }
    $ip = Get-IpDaRede
    if (-not $ip) { Write-Host "Não encontrei a rede deste computador. Ele está conectado?" -ForegroundColor Red; return }
    $nome = $env:COMPUTERNAME.ToLower()

    # 1) .env: aceita conexões da rede e os endereços pelos quais os colegas vão chegar
    $hosts = @((Get-EnvValor "DJANGO_ALLOWED_HOSTS") -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    foreach ($h in @("localhost", "127.0.0.1", $ip, $nome)) { if ($hosts -notcontains $h) { $hosts += $h } }
    Set-EnvValor "SERVIDOR_HOST" "0.0.0.0"
    Set-EnvValor "DJANGO_ALLOWED_HOSTS" ($hosts -join ",")
    Set-EnvValor "DJANGO_DEBUG" "false"            # não mostra detalhes de erro para outras pessoas
    Set-EnvValor "DJANGO_COOKIES_SEGUROS" "false"  # o login funciona em http:// dentro da rede
    Write-Host "1/3 .env ajustado para a rede ($ip)." -ForegroundColor Green

    # 2) Firewall do Windows: libera a porta só nas redes do domínio e privadas (nunca em rede pública)
    $porta = Get-Porta
    if (Get-NetFirewallRule -DisplayName "Central de TI" -ErrorAction SilentlyContinue) {
        Write-Host "2/3 A porta $porta já está liberada no firewall." -ForegroundColor Green
    } else {
        Write-Host "2/3 Liberando a porta $porta no firewall. O Windows vai pedir permissão de administrador..." -ForegroundColor Yellow
        $regra = "New-NetFirewallRule -DisplayName 'Central de TI' -Direction Inbound -Protocol TCP -LocalPort $porta -Action Allow -Profile Domain,Private"
        try {
            Start-Process powershell -Verb RunAs -Wait -ArgumentList "-NoProfile", "-Command", $regra
        } catch { }
        if (Get-NetFirewallRule -DisplayName "Central de TI" -ErrorAction SilentlyContinue) {
            Write-Host "    Porta liberada." -ForegroundColor Green
        } else {
            Write-Host "    Não foi possível liberar. Peça para alguém com acesso de administrador rodar:" -ForegroundColor Red
            Write-Host "    $regra"
        }
    }

    # 3) Religa (ou instala) a Central com a nova configuração
    Write-Host "3/3 Religando a Central..." -ForegroundColor Green
    if (Get-ScheduledTask -TaskName $nomeTarefa -ErrorAction SilentlyContinue) {
        Stop-Central
        Start-ScheduledTask -TaskName $nomeTarefa
        $null = Test-NoAr -Porta $porta -Segundos 30
    } else {
        & $PSCommandPath
    }
    Write-Host ""
    Write-Host "Pronto! Envie estes endereços para os colegas (eles precisam estar na mesma rede):" -ForegroundColor Green
    Write-Host "  Chat:   http://${ip}:$porta/      ou  http://${nome}:$porta/"
    Write-Host "  Painel: http://${ip}:$porta/painel/"
    return
}

# --- Instalação ---
# 1) Ambiente, dependências, .env e banco (mesmo preparo do iniciar.ps1, sem ligar o runserver)
& (Join-Path $PSScriptRoot "iniciar.ps1") -SoPreparar

# 2) Para qualquer servidor antigo desta pasta antes de registrar o novo
Stop-Central

# 3) Tarefa agendada: roda o servir.py com pythonw.exe (sem janela) ao entrar no Windows
$pythonw = Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe"
$acao = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$(Join-Path $PSScriptRoot 'servir.py')`"" -WorkingDirectory $PSScriptRoot
$gatilho = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$config = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew
$usuario = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $nomeTarefa -Action $acao -Trigger $gatilho -Settings $config -Principal $usuario `
    -Description "Servidor da Central de TI (chatbot + painel). Pasta: $PSScriptRoot" -Force | Out-Null

# 4) Liga agora, sem esperar o próximo login
Start-ScheduledTask -TaskName $nomeTarefa
Write-Host ""
if (Test-NoAr -Porta $porta -Segundos 30) {
    Write-Host "Pronto! A Central de TI está rodando em segundo plano e liga sozinha ao entrar no Windows." -ForegroundColor Green
    Write-Host "  Chat do colaborador: http://127.0.0.1:$porta/"
    Write-Host "  Painel da TI:        http://127.0.0.1:$porta/painel/"
    Write-Host "  Administração:       http://127.0.0.1:$porta/admin/"
    Write-Host "Pode fechar esta janela."
} else {
    Write-Host "A tarefa foi criada, mas a Central não respondeu. Veja logs\servidor.log e logs\saida.log." -ForegroundColor Red
}
