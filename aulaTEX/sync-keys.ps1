<#
.SYNOPSIS
    Sustituye las claves de aulaTEX/aulatex.env con las de tus suscripciones de
    Azure (az cli) y AWS (aws cli), cifradas con el PIN maestro $env:AULATEX_MASTER_PIN.

.DESCRIPTION
    Recorre TODAS las suscripciones visibles con `az account list`, inventaria las
    cuentas de Microsoft.CognitiveServices y asocia cada variable `*_API_KEY` del
    .env con la cuenta cuyo host coincide con la URL declarada en su `*_BASE_URL`,
    `*_ENDPOINT` o `*_HOST` hermano. Luego obtiene la clave con
    `az cognitiveservices account keys list` (o `regenerate` con -Rotate) y la
    escribe cifrada.

    AWS: obtiene la identidad con `aws sts get-caller-identity` y, si se indica
    -IamUserName, crea una access key nueva y retira la anterior.

    Las claves en claro viajan solo por stdin hacia secrets_local.py: no aparecen
    en argv, ni en el historial de PowerShell, ni en disco sin cifrar.

.PARAMETER Rotate
    Regenera la clave en el proveedor antes de guardarla (rotacion real).
    Sin este switch solo se sincroniza la clave vigente.

.EXAMPLE
    $env:AULATEX_MASTER_PIN = '<pin>'
    .\aulaTEX\sync-keys.ps1 -WhatIf          # inventario y plan, sin escribir

.EXAMPLE
    .\aulaTEX\sync-keys.ps1                  # sincroniza claves vigentes

.EXAMPLE
    .\aulaTEX\sync-keys.ps1 -Rotate          # regenera key1 y sustituye

.EXAMPLE
    .\aulaTEX\sync-keys.ps1 -IamUserName aulatex-polly -Rotate -DeactivateOld
#>

[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [switch]$Rotate,
    [ValidateSet('key1', 'key2')]
    [string]$KeyName = 'key1',

    # Limita el trabajo a estas suscripciones (id o nombre). Vacio = todas.
    [string[]]$Subscription,

    # Limita el trabajo a estas variables del .env. Vacio = todas las detectadas.
    [string[]]$Name,

    # --- AWS ---
    [string]$IamUserName,
    [string]$AwsProfile,
    [switch]$DeactivateOld,
    [switch]$DeleteOld,

    [string]$EnvFile = 'aulatex.env'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot   = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$secretsPy  = Join-Path $PSScriptRoot 'secrets_local.py'
$envPath    = if ([IO.Path]::IsPathRooted($EnvFile)) { $EnvFile } else { Join-Path $PSScriptRoot $EnvFile }
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$pythonCmd  = if (Test-Path $venvPython) { $venvPython } else { 'python' }

if ([string]::IsNullOrWhiteSpace($env:AULATEX_MASTER_PIN)) {
    throw "Define el PIN maestro antes de sincronizar: `$env:AULATEX_MASTER_PIN = '<pin>'"
}
if (-not (Test-Path $secretsPy)) { throw "No se encontro $secretsPy." }
if (-not (Test-Path $envPath))   { throw "No se encontro $envPath." }

function Assert-Cli {
    param([Parameter(Mandatory)][string]$CliName, [Parameter(Mandatory)][string]$Hint)
    if (-not (Get-Command $CliName -ErrorAction SilentlyContinue)) {
        throw "No se encontro '$CliName' en PATH. $Hint"
    }
}

function Invoke-CliJson {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$Arguments
    )
    $stdout = & $FilePath @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo '$FilePath $($Arguments -join ' ')' (exit $LASTEXITCODE): $stdout"
    }
    $text = ($stdout | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) { return $null }
    return $text | ConvertFrom-Json
}

function Save-EncryptedSecret {
    param(
        [Parameter(Mandatory)][string]$VarName,
        [Parameter(Mandatory)][string]$Value
    )
    # El valor viaja por stdin en UTF8 sin BOM: no aparece en argv ni en el historial.
    $prevEncoding = [Console]::OutputEncoding
    try {
        [Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
        $Value | & $pythonCmd $secretsPy set-value $envPath $VarName | Out-Null
    }
    finally { [Console]::OutputEncoding = $prevEncoding }
    if ($LASTEXITCODE -ne 0) { throw "No se pudo cifrar $VarName en $EnvFile." }
}

function Format-Masked {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Value)
    if ([string]::IsNullOrEmpty($Value)) { return '(vacio)' }
    if ($Value.Length -le 4) { return '****' }
    return ('*' * 8) + $Value.Substring($Value.Length - 4)
}

function Get-HostFromUrl {
    param([AllowEmptyString()][string]$Url)
    if ([string]::IsNullOrWhiteSpace($Url)) { return $null }
    $clean = $Url.Trim().Trim('"').Trim("'")
    try { return ([Uri]$clean).Host.ToLowerInvariant() } catch { return $null }
}

# ---------------------------------------------------------------------------
# 1. Leer el .env conservando el texto crudo
# ---------------------------------------------------------------------------
$envLines = Get-Content -LiteralPath $envPath -Encoding UTF8
$envMap   = [ordered]@{}
foreach ($line in $envLines) {
    $t = $line.Trim()
    if ($t.Length -eq 0 -or $t.StartsWith('#')) { continue }
    $i = $t.IndexOf('=')
    if ($i -lt 1) { continue }
    $envMap[$t.Substring(0, $i).Trim()] = $t.Substring($i + 1).Trim().Trim('"').Trim("'")
}

# Variables de clave detectadas en el .env.
$keyVars = @($envMap.Keys | Where-Object { $_ -match '_API_KEY$|_SPEECH_KEY$|_TRANSLATOR_KEY$' })
if ($Name) { $keyVars = @($keyVars | Where-Object { $Name -contains $_ }) }
if ($keyVars.Count -eq 0) { throw 'No se detectaron variables de clave en el .env.' }

# ---------------------------------------------------------------------------
# 2. Inventariar cuentas de Cognitive Services en todas las suscripciones
# ---------------------------------------------------------------------------
Assert-Cli -CliName 'az' -Hint 'Instala Azure CLI: winget install Microsoft.AzureCLI'

Write-Host 'Inventariando suscripciones de Azure...' -ForegroundColor Cyan
$subs = Invoke-CliJson -FilePath 'az' -Arguments @('account', 'list', '--query', '[].{id:id,name:name}', '--output', 'json')
if ($Subscription) {
    $subs = @($subs | Where-Object { $Subscription -contains $_.id -or $Subscription -contains $_.name })
}
if (-not $subs) { throw 'No hay suscripciones accesibles. Ejecuta: az login' }

# Indice host -> cuenta. Un mismo recurso expone varios hosts (openai.azure.com,
# cognitiveservices.azure.com, services.ai.azure.com), asi que se registran todos.
$accountsByHost = @{}
$inventory = New-Object System.Collections.Generic.List[object]

foreach ($sub in $subs) {
    $accounts = Invoke-CliJson -FilePath 'az' -Arguments @(
        'cognitiveservices', 'account', 'list',
        '--subscription', $sub.id,
        '--query', '[].{name:name,rg:resourceGroup,kind:kind,endpoint:properties.endpoint}',
        '--output', 'json')
    if (-not $accounts) { continue }

    foreach ($acc in $accounts) {
        $entry = [pscustomobject]@{
            Name           = $acc.name
            ResourceGroup  = $acc.rg
            Kind           = $acc.kind
            Endpoint       = $acc.endpoint
            SubscriptionId = $sub.id
            SubName        = $sub.name
        }
        $inventory.Add($entry)

        $hosts = New-Object System.Collections.Generic.List[string]
        $epHost = Get-HostFromUrl -Url $acc.endpoint
        if ($epHost) { [void]$hosts.Add($epHost) }
        # Hosts derivados del nombre del recurso: Azure los expone en paralelo.
        foreach ($suffix in @('openai.azure.com', 'cognitiveservices.azure.com', 'services.ai.azure.com')) {
            [void]$hosts.Add("$($acc.name.ToLowerInvariant()).$suffix")
        }
        foreach ($h in $hosts) {
            if (-not $accountsByHost.ContainsKey($h)) { $accountsByHost[$h] = $entry }
        }
    }
}

Write-Host "  $($inventory.Count) cuenta(s) en $($subs.Count) suscripcion(es)." -ForegroundColor DarkGray

# ---------------------------------------------------------------------------
# 3. Asociar cada variable de clave con su cuenta
# ---------------------------------------------------------------------------
function Resolve-AccountForVar {
    param([Parameter(Mandatory)][string]$VarName)

    # De mas especifico a menos: AZURE_SPEECH_KEY debe probar AZURE_SPEECH_ENDPOINT
    # antes de caer en AZURE_ENDPOINT, que apunta a otro recurso.
    $prefixes = New-Object System.Collections.Generic.List[string]
    $long = $VarName -replace '_KEY$', ''
    [void]$prefixes.Add($long)
    $short = $VarName -replace '_(API_KEY|SPEECH_KEY|TRANSLATOR_KEY)$', ''
    if ($short -ne $long) { [void]$prefixes.Add($short) }

    foreach ($prefix in $prefixes) {
        foreach ($cand in @("${prefix}_BASE_URL", "${prefix}_ENDPOINT", "${prefix}_HOST", "${prefix}S_ENDPOINT", "${prefix}_URL")) {
            if (-not $envMap.Contains($cand)) { continue }
            $h = Get-HostFromUrl -Url $envMap[$cand]
            if ($h -and $accountsByHost.ContainsKey($h)) { return $accountsByHost[$h] }
        }
    }

    # Ultimo recurso: otra variable con el mismo prefijo largo que sea URL conocida.
    foreach ($k in $envMap.Keys) {
        if (-not $k.StartsWith($long)) { continue }
        $v = [string]$envMap[$k]
        if (-not $v.StartsWith('http')) { continue }
        $h = Get-HostFromUrl -Url $v
        if ($h -and $accountsByHost.ContainsKey($h)) { return $accountsByHost[$h] }
    }

    # Speech y Translator usan endpoints regionales genericos que no identifican
    # al recurso; se resuelven por 'kind' cuando hay exactamente uno.
    $kind = switch -Regex ($VarName) {
        '_TRANSLATOR_KEY$' { 'TextTranslation'; break }
        '_SPEECH_KEY$'     { 'SpeechServices'; break }
        default            { $null }
    }
    if ($kind) {
        $byKind = @($inventory | Where-Object { $_.Kind -eq $kind })
        if ($byKind.Count -eq 1) { return $byKind[0] }
    }
    return $null
}

$plan = New-Object System.Collections.Generic.List[object]
$unmatched = New-Object System.Collections.Generic.List[string]
foreach ($var in $keyVars) {
    $acc = Resolve-AccountForVar -VarName $var
    if ($null -eq $acc) { $unmatched.Add($var); continue }
    $plan.Add([pscustomobject]@{ Variable = $var; Account = $acc })
}

Write-Host "`nPlan de sustitucion:" -ForegroundColor Cyan
foreach ($item in $plan) {
    Write-Host ("  {0,-42} <- {1} [{2}]" -f $item.Variable, $item.Account.Name, $item.Account.SubName)
}
if ($unmatched.Count -gt 0) {
    Write-Host "`nSin recurso accesible (se omiten):" -ForegroundColor Yellow
    foreach ($u in $unmatched) { Write-Host "  $u" -ForegroundColor Yellow }
}

# ---------------------------------------------------------------------------
# 4. Obtener/rotar y escribir cifrado
# ---------------------------------------------------------------------------
if ($plan.Count -gt 0 -and $PSCmdlet.ShouldProcess($envPath, 'Respaldar antes de sustituir')) {
    Copy-Item -LiteralPath $envPath -Destination "$envPath.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')" -Force
}

# Una sola llamada por cuenta: varias variables comparten el mismo recurso.
$keyCache = @{}
$applied = 0

foreach ($item in $plan) {
    $acc = $item.Account
    $cacheKey = "$($acc.SubscriptionId)/$($acc.ResourceGroup)/$($acc.Name)"

    if (-not $keyCache.ContainsKey($cacheKey)) {
        $verb = if ($Rotate) { 'regenerate' } else { 'list' }
        $azArgs = @('cognitiveservices', 'account', 'keys', $verb,
                    '--name', $acc.Name,
                    '--resource-group', $acc.ResourceGroup,
                    '--subscription', $acc.SubscriptionId,
                    '--output', 'json')
        if ($Rotate) { $azArgs += @('--key-name', $KeyName) }

        $action = if ($Rotate) { "Regenerar $KeyName" } else { "Leer clave" }
        if (-not $PSCmdlet.ShouldProcess("$($acc.Name) [$($acc.SubName)]", $action)) {
            Write-Host "  [WhatIf] az $($azArgs -join ' ')" -ForegroundColor DarkGray
            continue
        }

        $keys = Invoke-CliJson -FilePath 'az' -Arguments $azArgs
        $value = if ($KeyName -eq 'key1') { $keys.key1 } else { $keys.key2 }
        if ([string]::IsNullOrWhiteSpace($value)) { throw "Azure no devolvio $KeyName para $($acc.Name)." }
        $keyCache[$cacheKey] = $value
    }

    Save-EncryptedSecret -VarName $item.Variable -Value $keyCache[$cacheKey]
    Write-Host ("  {0,-42} = {1} (cifrado)" -f $item.Variable, (Format-Masked -Value $keyCache[$cacheKey])) -ForegroundColor Green
    $applied++
}

# ---------------------------------------------------------------------------
# 5. AWS
# ---------------------------------------------------------------------------
if (-not [string]::IsNullOrWhiteSpace($IamUserName)) {
    Assert-Cli -CliName 'aws' -Hint 'Instala AWS CLI v2: winget install Amazon.AWSCLI'
    $profileArgs = @()
    if (-not [string]::IsNullOrWhiteSpace($AwsProfile)) { $profileArgs = @('--profile', $AwsProfile) }

    Write-Host "`nAWS IAM: $IamUserName" -ForegroundColor Cyan
    $existing = Invoke-CliJson -FilePath 'aws' -Arguments (@('iam', 'list-access-keys', '--user-name', $IamUserName, '--output', 'json') + $profileArgs)
    $oldKeys = @($existing.AccessKeyMetadata | Where-Object { $_.Status -eq 'Active' })

    # IAM admite un maximo de 2 access keys por usuario.
    if ($oldKeys.Count -ge 2) {
        throw "El usuario '$IamUserName' ya tiene 2 access keys activas. Elimina una antes de rotar."
    }

    if ($PSCmdlet.ShouldProcess($IamUserName, 'Crear nueva access key IAM')) {
        $created = Invoke-CliJson -FilePath 'aws' -Arguments (@('iam', 'create-access-key', '--user-name', $IamUserName, '--output', 'json') + $profileArgs)
        $newId     = $created.AccessKey.AccessKeyId
        $newSecret = $created.AccessKey.SecretAccessKey
        if ([string]::IsNullOrWhiteSpace($newId) -or [string]::IsNullOrWhiteSpace($newSecret)) {
            throw 'AWS no devolvio la nueva access key completa.'
        }

        Save-EncryptedSecret -VarName 'AWS_ACCESS_KEY_ID'     -Value $newId
        Save-EncryptedSecret -VarName 'AWS_SECRET_ACCESS_KEY' -Value $newSecret
        Write-Host ("  {0,-42} = {1} (cifrado)" -f 'AWS_ACCESS_KEY_ID', (Format-Masked -Value $newId)) -ForegroundColor Green
        Write-Host ("  {0,-42} = {1} (cifrado)" -f 'AWS_SECRET_ACCESS_KEY', (Format-Masked -Value $newSecret)) -ForegroundColor Green
        $applied += 2

        foreach ($old in $oldKeys) {
            if ($old.AccessKeyId -eq $newId) { continue }
            if ($DeleteOld) {
                & aws iam delete-access-key --user-name $IamUserName --access-key-id $old.AccessKeyId @profileArgs
                if ($LASTEXITCODE -ne 0) { throw "No se pudo eliminar la access key $($old.AccessKeyId)." }
                Write-Host "  Eliminada clave anterior $($old.AccessKeyId)." -ForegroundColor Yellow
            }
            elseif ($DeactivateOld) {
                & aws iam update-access-key --user-name $IamUserName --access-key-id $old.AccessKeyId --status Inactive @profileArgs
                if ($LASTEXITCODE -ne 0) { throw "No se pudo desactivar la access key $($old.AccessKeyId)." }
                Write-Host "  Desactivada clave anterior $($old.AccessKeyId)." -ForegroundColor Yellow
            }
            else {
                Write-Host "  Clave anterior $($old.AccessKeyId) sigue ACTIVA. Usa -DeactivateOld tras validar." -ForegroundColor Yellow
            }
        }
    }
}

Write-Host "`n$applied clave(s) sustituida(s) y cifrada(s) en $EnvFile." -ForegroundColor Cyan
Write-Host "Verifica con: .\aulaTEX\aulatex.ps1 llm-check" -ForegroundColor Cyan
