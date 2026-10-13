<#
.SYNOPSIS
    Asistente seguro para configurar los LLM de AulaTeX.

.DESCRIPTION
    Solicita el PIN y las API keys como SecureString. Permite descubrir cuentas
    y deployments mediante Azure CLI o ingresar endpoint/deployment manualmente.
    Las claves se envían por stdin a secrets_local.py y se guardan cifradas.

    El asistente puede configurar uno o varios perfiles. Si el único perfil es
    model-router, activa AULATEX_MODEL_ROUTER_ONLY=1; con varios perfiles lo
    desactiva y conserva el orden elegido en AULATEX_LLM_ENGINE.
#>
[CmdletBinding()]
param(
    [string]$EnvFile = 'aulatex.env',
    [switch]$PersistPin,
    [switch]$SkipConnectionTest,
    [switch]$NonInteractive,
    [ValidateSet('keep', 'manual', 'azure-cli')]
    [string]$Mode = 'keep',
    [string[]]$LlmProfile = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$envPath = if ([IO.Path]::IsPathRooted($EnvFile)) { $EnvFile } else { Join-Path $scriptDir $EnvFile }
$envExample = Join-Path $scriptDir 'aulatex.env.example'
$secretsPy = Join-Path $scriptDir 'secrets_local.py'
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$python = if (Test-Path $venvPython) { $venvPython } else { (Get-Command python -ErrorAction Stop).Source }

$profiles = [ordered]@{
    'model-router' = [ordered]@{ Label='Auto (model-router)'; Prefix='MODEL_ROUTER'; DefaultDeployment='model-router'; DefaultVersion='2025-11-18'; Protocol='openai' }
    'codex' = [ordered]@{ Label='Codex'; Prefix='CODEX'; DefaultDeployment='gpt-5.3-codex'; DefaultVersion='2026-02-24'; Protocol='openai' }
    'gpt-pro' = [ordered]@{ Label='GPT-Pro'; Prefix='GPT_PRO'; DefaultDeployment='gpt-5.4-pro'; DefaultVersion='2026-03-05'; Protocol='openai' }
    'gpt-5.6-sol' = [ordered]@{ Label='GPT-5.6-SOL'; Prefix='AZURE_OPENAI_GPT_5_6_SOL'; DefaultDeployment='gpt-5.6-sol'; DefaultVersion='2026-07-09'; Protocol='openai' }
    'gpt-5.6-luna' = [ordered]@{ Label='GPT-5.6-Luna'; Prefix='AZURE_OPENAI_GPT_5_6_LUNA'; DefaultDeployment='gpt-5.6-luna'; DefaultVersion='2026-07-09'; Protocol='openai' }
    'gpt-5.6-terra' = [ordered]@{ Label='GPT-5.6-Terra'; Prefix='AZURE_OPENAI_GPT_5_6_TERRA'; DefaultDeployment='gpt-5.6-terra'; DefaultVersion='2026-07-09'; Protocol='openai' }
    'claude-foundry' = [ordered]@{ Label='Claude Foundry'; Prefix='ANTHROPIC_FOUNDRY'; DefaultDeployment='claude-opus'; DefaultVersion='2023-06-01'; Protocol='anthropic' }
    'deepseek-v4-pro' = [ordered]@{ Label='DeepSeek-V4-Pro'; Prefix='DEEPSEEK_V4_PRO'; DefaultDeployment='DeepSeek-V4-Pro'; DefaultVersion=''; Protocol='openai' }
    'grok' = [ordered]@{ Label='Grok-Pensamiento-Libre'; Prefix='GROK_PENSAMIENTO_LIBRE'; DefaultDeployment='Grok-Pensamiento-Libre'; DefaultVersion=''; Protocol='openai' }
    'gpt-5-mini' = [ordered]@{ Label='GPT-5-Mini'; Prefix='GPT_5_MINI'; DefaultDeployment='gpt-5-mini'; DefaultVersion=''; Protocol='openai' }
    'mistral-large-3' = [ordered]@{ Label='Mistral-Large-3'; Prefix='MISTRAL_LARGE_3'; DefaultDeployment='Mistral-Large-3'; DefaultVersion=''; Protocol='openai' }
}

function ConvertFrom-SecureStringPlain {
    param([Parameter(Mandatory)][Security.SecureString]$Secure)
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

function Read-RequiredValue {
    param([string]$Prompt, [string]$Default = '')
    while ($true) {
        $suffix = if ($Default) { " [$Default]" } else { '' }
        $value = (Read-Host "$Prompt$suffix").Trim()
        if (-not $value) { $value = $Default }
        if ($value) { return $value }
        Write-Host 'El valor es obligatorio.' -ForegroundColor Yellow
    }
}

function Read-MenuIndex {
    param([int]$Count, [string]$Prompt)
    while ($true) {
        $raw = (Read-Host $Prompt).Trim()
        $number = 0
        if ([int]::TryParse($raw, [ref]$number) -and $number -ge 1 -and $number -le $Count) {
            return $number - 1
        }
        Write-Host "Seleccion invalida. Usa un numero entre 1 y $Count." -ForegroundColor Yellow
    }
}

function Set-EnvValues {
    param([Parameter(Mandatory)][hashtable]$Values)
    $lines = if (Test-Path $envPath) { @(Get-Content -LiteralPath $envPath -Encoding UTF8) } else { @() }
    $remaining = @{}
    foreach ($key in $Values.Keys) { $remaining[$key] = [string]$Values[$key] }
    $written = @{}
    $updated = New-Object System.Collections.Generic.List[string]
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        $name = if ($trimmed -and -not $trimmed.StartsWith('#') -and $trimmed.Contains('=')) { $trimmed.Split('=', 2)[0].Trim() } else { '' }
        if ($name -and $Values.ContainsKey($name)) {
            if (-not $written.ContainsKey($name)) {
                $updated.Add("$name=$([string]$Values[$name])")
                $written[$name] = $true
                $remaining.Remove($name)
            }
        } else {
            $updated.Add($line)
        }
    }
    if ($remaining.Count) {
        $updated.Add('')
        $updated.Add('# --- Configuracion gestionada por configure-llms.ps1 ---')
        foreach ($key in $remaining.Keys) { $updated.Add("$key=$($remaining[$key])") }
    }
    [IO.File]::WriteAllLines($envPath, $updated, (New-Object Text.UTF8Encoding($false)))
}

function Save-EncryptedSecret {
    param([string]$Name, [string]$Value)
    $previous = [Console]::OutputEncoding
    try {
        [Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
        $Value | & $python $secretsPy set-value $envPath $Name | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "No se pudo guardar $Name." }
    } finally {
        [Console]::OutputEncoding = $previous
    }
}

function Test-PinWorks {
    $encryptedCount = if (Test-Path $envPath) { @(Select-String -Path $envPath -Pattern '=enc:' -SimpleMatch).Count } else { 0 }
    if ($encryptedCount -eq 0) { return $true }
    $decrypted = @(& $python $secretsPy decrypt-env $envPath)
    if ($LASTEXITCODE -ne 0) { return $false }
    $decryptedCount = @($decrypted | Where-Object { $_ -match "`t" }).Count
    return $decryptedCount -eq $encryptedCount
}

function Read-AndValidatePin {
    while ($true) {
        $pinSecure = Read-Host 'PIN maestro de AulaTeX (entrada oculta)' -AsSecureString
        $candidate = ConvertFrom-SecureStringPlain $pinSecure
        if (-not $candidate) {
            Write-Host 'El PIN no puede quedar vacio.' -ForegroundColor Yellow
            continue
        }

        $env:AULATEX_MASTER_PIN = $candidate
        if (Test-PinWorks) {
            Write-Host 'PIN verificado correctamente.' -ForegroundColor Green
            return $candidate
        }

        Write-Host ''
        Write-Host 'El PIN no descifra todos los secretos existentes.' -ForegroundColor Yellow
        Write-Host '  1. Reintentar el PIN'
        Write-Host '  2. Continuar y reemplazar la configuracion LLM seleccionada'
        Write-Host '  3. Cancelar'
        $choice = Read-MenuIndex -Count 3 -Prompt 'Selecciona una opcion'
        if ($choice -eq 0) { continue }
        if ($choice -eq 1) {
            Write-Warning 'Los secretos antiguos que usen otro PIN seguirán inaccesibles; los LLM configurados ahora se cifraran con este PIN.'
            return $candidate
        }
        throw 'Configuracion cancelada por el usuario.'
    }
}

function ConvertTo-NormalizedEndpoint {
    param([string]$Endpoint, [string]$Protocol)
    $base = $Endpoint.Trim().TrimEnd('/')
    if ($Protocol -eq 'anthropic') {
        if ($base -match '/v1/messages$') { return $base }
        if ($base -match '/anthropic$') { return "$base/v1/messages" }
        return "$base/anthropic/v1/messages"
    }
    if ($base -match '/openai/v1/(chat/completions|responses)$') { return $base }
    if ($base -match '/openai/v1$') { return "$base/chat/completions" }
    return "$base/openai/v1/chat/completions"
}

function Select-Profiles {
    if ($LlmProfile.Count -gt 0) {
        $invalid = @($LlmProfile | Where-Object { -not $profiles.Contains($_) })
        if ($invalid) { throw "Perfiles desconocidos: $($invalid -join ', ')" }
        return @($LlmProfile | Select-Object -Unique)
    }
    $keys = @($profiles.Keys)
    Write-Host "`nLLM disponibles:" -ForegroundColor Cyan
    for ($i = 0; $i -lt $keys.Count; $i++) {
        Write-Host ("  {0,2}. {1}" -f ($i + 1), $profiles[$keys[$i]].Label)
    }
    while ($true) {
        $raw = (Read-Host 'Indica numeros separados por coma (ejemplo: 1 o 1,2,3)').Trim()
        $indexes = New-Object System.Collections.Generic.List[int]
        $valid = $true
        foreach ($part in ($raw -split ',')) {
            $number = 0
            if (-not [int]::TryParse($part.Trim(), [ref]$number) -or $number -lt 1 -or $number -gt $keys.Count) {
                $valid = $false; break
            }
            if (-not $indexes.Contains($number - 1)) { $indexes.Add($number - 1) }
        }
        if ($valid -and $indexes.Count) { return @($indexes | ForEach-Object { $keys[$_] }) }
        Write-Host 'Seleccion invalida.' -ForegroundColor Yellow
    }
}

function Get-AzureContext {
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        throw 'Azure CLI no esta instalado. Instala con: winget install Microsoft.AzureCLI'
    }
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & az account show --output none 2>$null
        $accountExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $savedPreference
    }
    if ($accountExit -ne 0) {
        if ($NonInteractive) { throw 'Azure CLI no tiene sesion activa.' }
        Write-Host 'Azure CLI requiere autenticacion; se abrira el inicio de sesion.' -ForegroundColor Yellow
        & az login
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo autenticar Azure CLI.' }
    }
    $subscriptions = @(& az account list --query '[?state==`Enabled`].{id:id,name:name,isDefault:isDefault}' --output json | ConvertFrom-Json)
    if (-not $subscriptions) { throw 'No hay suscripciones Azure habilitadas.' }
    if ($subscriptions.Count -eq 1 -or $NonInteractive) { return $subscriptions[0] }
    Write-Host "`nSuscripciones:" -ForegroundColor Cyan
    for ($i = 0; $i -lt $subscriptions.Count; $i++) {
        $default = if ($subscriptions[$i].isDefault) { ' (predeterminada)' } else { '' }
        Write-Host ("  {0,2}. {1}{2}" -f ($i + 1), $subscriptions[$i].name, $default)
    }
    return $subscriptions[(Read-MenuIndex -Count $subscriptions.Count -Prompt 'Selecciona suscripcion')]
}

function Get-AzureAccount {
    param($Subscription)
    $accounts = @(& az cognitiveservices account list --subscription $Subscription.id --query '[].{name:name,rg:resourceGroup,kind:kind,endpoint:properties.endpoint}' --output json | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0 -or -not $accounts) { throw 'No se encontraron cuentas de AI Services/Cognitive Services.' }
    if ($accounts.Count -eq 1 -or $NonInteractive) { return $accounts[0] }
    Write-Host "`nCuentas Foundry/Cognitive Services:" -ForegroundColor Cyan
    for ($i = 0; $i -lt $accounts.Count; $i++) {
        Write-Host ("  {0,2}. {1} [{2}] - {3}" -f ($i + 1), $accounts[$i].name, $accounts[$i].kind, $accounts[$i].rg)
    }
    return $accounts[(Read-MenuIndex -Count $accounts.Count -Prompt 'Selecciona cuenta')]
}

function Get-AzureDeployments {
    param($Subscription, $Account)
    $items = @(& az cognitiveservices account deployment list --subscription $Subscription.id --resource-group $Account.rg --name $Account.name --query '[].{name:name,model:properties.model.name,version:properties.model.version}' --output json | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0 -or -not $items) { throw "No se encontraron deployments en $($Account.name)." }
    return $items
}

function Resolve-ProfileForDeployment {
    param($Deployment, [string[]]$Selected)
    $text = ("$($Deployment.name) $($Deployment.model)").ToLowerInvariant()
    foreach ($candidate in $Selected) {
        if ($candidate -eq 'model-router' -and $text -match 'model-router') { return $candidate }
        if ($candidate -eq 'codex' -and $text -match 'codex') { return $candidate }
        if ($candidate -eq 'gpt-pro' -and $text -match 'gpt-5\.4|gpt.*pro') { return $candidate }
        if ($candidate -eq 'gpt-5.6-sol' -and $text -match '5\.6.*sol') { return $candidate }
        if ($candidate -eq 'gpt-5.6-luna' -and $text -match '5\.6.*luna') { return $candidate }
        if ($candidate -eq 'gpt-5.6-terra' -and $text -match '5\.6.*terra') { return $candidate }
        if ($candidate -eq 'claude-foundry' -and $text -match 'claude') { return $candidate }
        if ($candidate -eq 'deepseek-v4-pro' -and $text -match 'deepseek') { return $candidate }
        if ($candidate -eq 'grok' -and $text -match 'grok') { return $candidate }
        if ($candidate -eq 'gpt-5-mini' -and $text -match 'gpt-5.*mini') { return $candidate }
        if ($candidate -eq 'mistral-large-3' -and $text -match 'mistral.*large') { return $candidate }
    }
    return $null
}

function Invoke-ManualConfiguration {
    param([string[]]$Selected)
    foreach ($id in $Selected) {
        $spec = $profiles[$id]
        Write-Host "`nConfigurando $($spec.Label)" -ForegroundColor Cyan
        $endpoint = ConvertTo-NormalizedEndpoint -Endpoint (Read-RequiredValue -Prompt 'Endpoint/base URL') -Protocol $spec.Protocol
        $deployment = Read-RequiredValue -Prompt 'Nombre del deployment' -Default $spec.DefaultDeployment
        $secureKey = Read-Host 'API key (entrada oculta)' -AsSecureString
        $apiKey = ConvertFrom-SecureStringPlain $secureKey
        if (-not $apiKey) { throw "La API key de $($spec.Label) no puede quedar vacia." }
        $values = @{
            "$($spec.Prefix)_BASE_URL" = $endpoint
            "$($spec.Prefix)_CHAT_DEPLOYMENT" = $deployment
        }
        if ($spec.DefaultVersion) { $values["$($spec.Prefix)_API_VERSION"] = $spec.DefaultVersion }
        Set-EnvValues -Values $values
        Save-EncryptedSecret -Name "$($spec.Prefix)_API_KEY" -Value $apiKey
        $apiKey = $null
    }
}

function Invoke-AzureCliConfiguration {
    param([string[]]$Selected)
    $subscription = Get-AzureContext
    $account = Get-AzureAccount -Subscription $subscription
    $deployments = Get-AzureDeployments -Subscription $subscription -Account $account
    $matched = @{}
    foreach ($deployment in $deployments) {
        $id = Resolve-ProfileForDeployment -Deployment $deployment -Selected $Selected
        if ($id -and -not $matched.ContainsKey($id)) { $matched[$id] = $deployment }
    }
    foreach ($id in $Selected) {
        if (-not $matched.ContainsKey($id)) {
            if ($NonInteractive) { throw "No se encontro deployment para el perfil $id." }
            Write-Host "`nDeployments de $($account.name):" -ForegroundColor Cyan
            for ($i = 0; $i -lt $deployments.Count; $i++) {
                Write-Host ("  {0,2}. {1} [{2}]" -f ($i + 1), $deployments[$i].name, $deployments[$i].model)
            }
            $matched[$id] = $deployments[(Read-MenuIndex -Count $deployments.Count -Prompt "Deployment para $($profiles[$id].Label)")]
        }
    }
    $keys = & az cognitiveservices account keys list --subscription $subscription.id --resource-group $account.rg --name $account.name --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or -not $keys.key1) { throw 'Azure CLI no pudo obtener key1 de la cuenta seleccionada.' }
    foreach ($id in $Selected) {
        $spec = $profiles[$id]
        $deployment = $matched[$id]
        $endpoint = ConvertTo-NormalizedEndpoint -Endpoint ([string]$account.endpoint) -Protocol $spec.Protocol
        $values = @{
            "$($spec.Prefix)_BASE_URL" = $endpoint
            "$($spec.Prefix)_CHAT_DEPLOYMENT" = [string]$deployment.name
        }
        if ($spec.DefaultVersion) { $values["$($spec.Prefix)_API_VERSION"] = $spec.DefaultVersion }
        Set-EnvValues -Values $values
        Save-EncryptedSecret -Name "$($spec.Prefix)_API_KEY" -Value ([string]$keys.key1)
        Write-Host "  $($spec.Label): $($deployment.name) configurado y cifrado." -ForegroundColor Green
    }
    $keys = $null
}

if (-not (Test-Path $secretsPy)) { throw "No existe $secretsPy." }
if (-not (Test-Path $envPath)) {
    if (-not (Test-Path $envExample)) { throw 'No existe aulatex.env ni su plantilla.' }
    Copy-Item $envExample $envPath
}

# Orden del asistente: modo -> LLMs -> PIN -> credenciales -> validacion.
# Así, conservar la configuración no solicita un PIN innecesario.
if (-not $NonInteractive) {
    Write-Host "`n=== Configuracion segura de LLMs AulaTeX ===" -ForegroundColor Cyan
    if (-not $PSBoundParameters.ContainsKey('Mode')) {
        Write-Host "`nModo de configuracion:"
        Write-Host '  1. Conservar configuracion actual (no solicita PIN)'
        Write-Host '  2. Descubrir cuentas y deployments con Azure CLI'
        Write-Host '  3. Ingresar endpoint, deployment y API key manualmente'
        $choice = Read-MenuIndex -Count 3 -Prompt 'Selecciona modo'
        $Mode = @('keep', 'azure-cli', 'manual')[$choice]
    }
}

if ($Mode -eq 'keep') {
    Write-Host 'Configuracion LLM conservada. No se solicitaron ni modificaron secretos.' -ForegroundColor Green
    exit 0
}
if ($NonInteractive -and $Mode -eq 'manual') {
    throw 'El modo manual requiere una consola interactiva para proteger la API key. Usa Azure CLI o ejecuta sin -NonInteractive.'
}

# La selección ocurre antes del PIN para explicar qué secretos se configurarán.
# El operador @() es imprescindible: PowerShell desempaqueta una salida única
# como string y, con StrictMode, ese objeto no expone la propiedad Count.
$selected = @(Select-Profiles)
if ($selected.Count -eq 0) { throw 'No se seleccionó ningún perfil LLM.' }
Write-Host "`nLLM seleccionados: $((@($selected | ForEach-Object { $profiles[$_].Label })) -join ', ')" -ForegroundColor Cyan

if (-not $NonInteractive) {
    Write-Host 'Se requiere el PIN para descifrar secretos existentes y cifrar las nuevas API keys.' -ForegroundColor DarkGray
    $pin = Read-AndValidatePin
    $env:AULATEX_MASTER_PIN = $pin
    if (-not $PSBoundParameters.ContainsKey('PersistPin')) {
        $answer = (Read-Host 'Guardar el PIN en la variable de usuario para futuras sesiones? [s/N]').Trim().ToLowerInvariant()
        $PersistPin = $answer -in @('s', 'si', 'sí', 'y', 'yes')
    }
    if ($PersistPin) {
        [Environment]::SetEnvironmentVariable('AULATEX_MASTER_PIN', $pin, 'User')
        Write-Warning 'El PIN queda disponible para procesos de tu cuenta de Windows.'
    }
} elseif (-not $env:AULATEX_MASTER_PIN) {
    throw 'En modo no interactivo define AULATEX_MASTER_PIN en el entorno.'
}

if ($Mode -eq 'azure-cli') { Invoke-AzureCliConfiguration -Selected $selected }
else { Invoke-ManualConfiguration -Selected $selected }

$onlyRouter = $selected.Count -eq 1 -and $selected[0] -eq 'model-router'
$primary = $profiles[$selected[0]].Label
Set-EnvValues -Values @{
    'AULATEX_MODEL_ROUTER_ONLY' = $(if ($onlyRouter) { '1' } else { '0' })
    'AULATEX_LLM_ENGINE' = $primary
    'AULATEX_LLM_PROVIDER' = $(if ($selected[0] -eq 'model-router') { 'model-router' } else { $selected[0] })
    'LLM_PROVIDER' = $(if ($selected[0] -eq 'model-router') { 'model-router' } else { $selected[0] })
    'TB_BOOKS_LLM_REVIEW_ENGINE' = $primary
}

Write-Host "`nConfigurados $($selected.Count) LLM(s): $((@($selected | ForEach-Object { $profiles[$_].Label })) -join ', ')" -ForegroundColor Green
Write-Host "Modo exclusivo model-router: $onlyRouter" -ForegroundColor Green

if (-not $SkipConnectionTest) {
    while ($true) {
        Write-Host "`nValidando que cada LLM responda..." -ForegroundColor Cyan
        $validationFailed = $false
        foreach ($id in $selected) {
            $label = $profiles[$id].Label
            $rawValidation = & $python (Join-Path $scriptDir 'aulatex_agent.py') llm-validate --engine $label --max-tokens 32 --timeout-seconds 45 2>&1
            $validationExit = $LASTEXITCODE
            $validation = $null
            try { $validation = (($rawValidation | Out-String).Trim() | ConvertFrom-Json) } catch { }

            if ($validationExit -eq 0 -and $null -ne $validation -and $validation.ok) {
                Write-Host ("  [OK] {0}: respondio en {1} ms ({2} caracteres)." -f $label, $validation.latency_ms, $validation.response_chars) -ForegroundColor Green
            } else {
                $validationFailed = $true
                $safeError = if ($null -ne $validation -and $validation.error) { [string]$validation.error } else { 'respuesta ausente o no reconocible' }
                Write-Host ("  [ERROR] {0}: {1}." -f $label, $safeError) -ForegroundColor Red
            }
        }

        if (-not $validationFailed) { break }
        if ($NonInteractive) { throw 'Uno o más LLM no respondieron correctamente.' }

        Write-Host ''
        Write-Host 'Uno o más LLM no superaron la prueba funcional.' -ForegroundColor Yellow
        Write-Host '  1. Reintentar validación'
        Write-Host '  2. Conservar configuración y salir con advertencia'
        Write-Host '  3. Volver a ejecutar el asistente'
        $validationChoice = Read-MenuIndex -Count 3 -Prompt 'Selecciona una opción'
        if ($validationChoice -eq 0) { continue }
        if ($validationChoice -eq 2) {
            & $PSCommandPath -EnvFile $EnvFile
            exit $LASTEXITCODE
        }
        Write-Warning 'Configuración guardada, pero existen LLM sin respuesta funcional verificada.'
        break
    }
}

$pin = $null
[GC]::Collect()
