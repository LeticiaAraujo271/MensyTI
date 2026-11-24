# Central de TI - configura o WhatsApp (Digisac) e o e-mail dos links de aprovação.
#
# Pede os dados no próprio terminal (senhas e tokens ficam ocultos), grava no .env, testa e
# reinicia a Central. Nada passa por chat, e-mail ou GitHub: o .env fica só neste computador.
#
# Uso, na pasta do projeto (não precisa ser administrador):
#   powershell -ExecutionPolicy Bypass -File .\configurar_integracoes.ps1             WhatsApp e e-mail
#   powershell -ExecutionPolicy Bypass -File .\configurar_integracoes.ps1 -SoEmail    só o e-mail
#   powershell -ExecutionPolicy Bypass -File .\configurar_integracoes.ps1 -SoWhatsApp só o WhatsApp
#
# Enter numa pergunta mantém o valor que já está no .env.
param([switch]$SoEmail, [switch]$SoWhatsApp)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$envArquivo = Join-Path $PSScriptRoot ".env"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $envArquivo)) { throw "Não achei o .env. Rode antes: powershell -ExecutionPolicy Bypass -File .\iniciar.ps1" }
if (-not (Test-Path $python)) { throw "Não achei o ambiente virtual (.venv). Rode antes o iniciar.ps1." }

$EXEMPLOS = 'suaempresa|cole-aqui|gere-um|troque'

function Get-EnvValor([string]$Chave) {
    $linha = Get-Content $envArquivo -Encoding UTF8 | Where-Object { $_ -match "^\s*$Chave\s*=" } | Select-Object -First 1
    if (-not $linha) { return "" }
    $v = ($linha -split "=", 2)[1].Trim()
    if ($v -match $EXEMPLOS) { return "" }
    return $v
}

function Set-EnvValor([string]$Chave, [string]$Valor) {
    $linhas = @(Get-Content $envArquivo -Encoding UTF8)
    $achou = $false
    $linhas = $linhas | ForEach-Object {
        if ($_ -match "^\s*$Chave\s*=") { $achou = $true; "$Chave=$Valor" } else { $_ }
    }
    if (-not $achou) { $linhas = @($linhas) + "$Chave=$Valor" }
    [System.IO.File]::WriteAllLines($envArquivo, [string[]]$linhas, (New-Object System.Text.UTF8Encoding $false))
}

function Read-Valor([string]$Pergunta, [string]$Chave, [string]$Padrao = "") {
    $atual = Get-EnvValor $Chave
    $sugestao = if ($atual) { $atual } else { $Padrao }
    $texto = if ($sugestao) { "$Pergunta [$sugestao]" } else { $Pergunta }
    $v = (Read-Host $texto).Trim()
    if (-not $v) { $v = $sugestao }
    Set-EnvValor $Chave $v
    return $v
}

function Read-Segredo([string]$Pergunta, [string]$Chave) {
    $tem = [bool](Get-EnvValor $Chave)
    $texto = if ($tem) { "$Pergunta [Enter mantém o atual]" } else { $Pergunta }
    $seguro = Read-Host $texto -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)
    try { $v = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    if ($v) { Set-EnvValor $Chave $v.Trim() }
    elseif (-not $tem) { Write-Host "   (ficou vazio)" -ForegroundColor Yellow }
}

function Read-SimNao([string]$Pergunta, [bool]$Padrao) {
    $op = if ($Padrao) { "S/n" } else { "s/N" }
    $v = (Read-Host "$Pergunta ($op)").Trim().ToLower()
    if (-not $v) { return $Padrao }
    return $v.StartsWith("s")
}

function Invoke-Manage([string[]]$Argumentos) {
    & $python manage.py @Argumentos
    return ($LASTEXITCODE -eq 0)
}

# Endereço da Central na rede (vai nos links de aprovação)
$urlPadrao = "http://$($env:COMPUTERNAME.ToLower()):$((Get-EnvValor 'SERVIDOR_PORTA') -replace '^$','8000')"
Write-Host "`n=== Endereço da Central ===" -ForegroundColor Cyan
Write-Host "É o endereço que os colegas e os aprovadores abrem (precisa da regra do firewall liberada)."
$null = Read-Valor "Endereço da Central" "CENTRAL_URL" $urlPadrao

# ---------------------------------------------------------------- E-mail
if (-not $SoWhatsApp) {
    Write-Host "`n=== E-mail dos links de aprovação ===" -ForegroundColor Cyan
    Write-Host "Use uma conta de serviço (ex.: central-ti@empresa.com.br), não o seu e-mail pessoal."
    Write-Host "Microsoft 365: servidor smtp.office365.com, porta 587, TLS. A conta precisa ter o"
    Write-Host "'SMTP autenticado' liberado pelo administrador do Microsoft 365."
    $null = Read-Valor "Servidor SMTP" "EMAIL_HOST" "smtp.office365.com"
    $null = Read-Valor "Porta" "EMAIL_PORT" "587"
    $null = Read-Valor "Usar TLS (true/false)" "EMAIL_USE_TLS" "true"
    $usuario = Read-Valor "Conta que envia (usuário SMTP)" "EMAIL_HOST_USER"
    Read-Segredo "Senha da conta (não aparece na tela)" "EMAIL_HOST_PASSWORD"
    $null = Read-Valor "Remetente que aparece no e-mail" "EMAIL_REMETENTE" $usuario
    if (Read-SimNao "Enviar um e-mail de teste agora?" $true) {
        $para = Read-Host "Para qual endereço"
        if ($para) { $null = Invoke-Manage @("testar_email", "--para", $para.Trim()) }
    } else {
        $null = Invoke-Manage @("testar_email")
    }
}

# -------------------------------------------------------------- WhatsApp
if (-not $SoEmail) {
    Write-Host "`n=== WhatsApp (Digisac) ===" -ForegroundColor Cyan
    Write-Host "Os dados ficam no Digisac: Conta > API > Tokens de acesso pessoal (token) e"
    Write-Host "Conexões (ID da conexão de WhatsApp que o bot usa)."
    $null = Read-Valor "Endereço da conta Digisac (ex.: https://empresa.digisac.app)" "DIGISAC_URL"
    Read-Segredo "Token de acesso do Digisac (não aparece na tela)" "DIGISAC_TOKEN"
    $null = Read-Valor "ID da conexão de WhatsApp (opcional)" "DIGISAC_SERVICE_ID"
    $null = Read-Valor "ID do departamento da TI no Digisac (opcional)" "DIGISAC_DEPARTAMENTO_TI_ID"
    if (-not (Get-EnvValor "DIGISAC_WEBHOOK_TOKEN")) {
        $bytes = New-Object byte[] 24
        [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
        Set-EnvValor "DIGISAC_WEBHOOK_TOKEN" (([Convert]::ToBase64String($bytes)) -replace '[+/=]', '')
        Write-Host "   Segredo do webhook gerado e gravado no .env." -ForegroundColor Green
    }
    $ok = Invoke-Manage @("testar_digisac")
    if ($ok -and (Read-SimNao "Ligar o WhatsApp agora (o bot passa a responder e a enviar mensagens)?" $false)) {
        Set-EnvValor "WHATSAPP_ATIVO" "true"
        Set-EnvValor "DIGISAC_ENVIAR_MENSAGENS" "true"
        Write-Host "   WhatsApp ligado." -ForegroundColor Green
        $contato = Read-Host "ID de um contato do Digisac para receber uma mensagem de teste (Enter pula)"
        if ($contato) { $null = Invoke-Manage @("testar_digisac", "--enviar-para", $contato.Trim()) }
    }
    $token = Get-EnvValor "DIGISAC_WEBHOOK_TOKEN"
    Write-Host "`nNo Digisac, cadastre o webhook (evento message.created) com esta URL:" -ForegroundColor Cyan
    Write-Host "   https://SEU_ENDERECO_PUBLICO/webhooks/digisac/?token=$token"
    Write-Host "O Digisac fica na internet: SEU_ENDERECO_PUBLICO precisa ser um endereço HTTPS"
    Write-Host "público (servidor da empresa, porta pública do Codespaces ou ngrok). O nome da"
    Write-Host "máquina na rede interna não funciona para o webhook. Veja o README."
}

# ------------------------------------------------------------ Reinicia
Write-Host "`n=== Reiniciando a Central para valer a nova configuração ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "instalar_servico.ps1") -Reiniciar
Write-Host "`nPronto. Para refazer só uma parte: -SoEmail ou -SoWhatsApp." -ForegroundColor Green
