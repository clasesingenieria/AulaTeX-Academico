<#
.SYNOPSIS
    Cambia el PIN maestro de AulaTeX y recifra los secretos de aulatex.env.

.DESCRIPTION
    Pide el PIN actual y el nuevo como SecureString, de modo que ninguno se
    teclea en claro ni queda en el historial de PSReadLine. Los entrega a
    secrets_local.py por stdin: tampoco pasan por argv.

    El proceso descifra cada valor `enc:` con el PIN actual, renueva el salt de
    derivacion y vuelve a cifrar con el PIN nuevo. Si algun token no descifra,
    se aborta sin escribir nada. Antes de sobrescribir se deja un respaldo
    `aulatex.env.bak-rotate`.

    Renovar el salt invalida las claves derivadas del PIN anterior, asi que una
    copia vieja del .env deja de ser util aunque se conozca el PIN antiguo.

.PARAMETER EnvFile
    Archivo .env a recifrar. Por defecto aulaTEX/aulatex.env.

.PARAMETER MinLength
    Longitud minima exigida al PIN nuevo. Por defecto 4. Por debajo de 16 el
    script advierte y pide confirmacion: los blobs enc: se versionan en un repo
    publico, asi que un PIN corto se agota por fuerza bruta pese a las 480 000
    iteraciones de PBKDF2.

.PARAMETER Persist
    Guarda el PIN nuevo en la variable de usuario AULATEX_MASTER_PIN. Comodo, pero
    lo deja legible por cualquier proceso de tu sesion; sin este switch solo se
    define para la consola actual.

.EXAMPLE
    .\aulaTEX\rotate-pin.ps1

.EXAMPLE
    .\aulaTEX\rotate-pin.ps1 -Persist
#>

[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [string]$EnvFile = 'aulatex.env',
    [int]$MinLength = 4,
    [switch]$Persist
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$secretsPy = Join-Path $scriptDir 'secrets_local.py'
$saltPath = Join-Path $scriptDir 'secret.salt'
$envPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) { $EnvFile } else { Join-Path $scriptDir $EnvFile }

function Get-PlainText([System.Security.SecureString]$Secure) {
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Resolve-Python {
    $venv = Join-Path $repoRoot '.venv\Scripts\python.exe'
    if (Test-Path $venv) { return $venv }
    $sys = Get-Command python -ErrorAction SilentlyContinue
    if ($sys) { return $sys.Source }
    throw 'No se encontro Python: crea el entorno .venv o instala python en PATH.'
}

foreach ($required in @($secretsPy, $envPath, $saltPath)) {
    if (-not (Test-Path $required)) { throw "No existe: $required" }
}
$python = Resolve-Python

$encCount = (Select-String -Path $envPath -Pattern '=enc:' -SimpleMatch).Count
if ($encCount -eq 0) { throw "No hay valores 'enc:' en $envPath." }
Write-Host "Secretos cifrados detectados: $encCount" -ForegroundColor Cyan

# --- Captura de los PIN -----------------------------------------------------
$currentSecure = Read-Host -AsSecureString 'PIN actual'
$current = Get-PlainText $currentSecure
if (-not $current) { throw 'El PIN actual no puede quedar vacio.' }

$newSecure = Read-Host -AsSecureString "PIN nuevo (minimo $MinLength caracteres)"
$new = Get-PlainText $newSecure
$confirmSecure = Read-Host -AsSecureString 'Confirma el PIN nuevo'
$confirm = Get-PlainText $confirmSecure

if ($new -ne $confirm) { throw 'Los PIN nuevos no coinciden.' }
if ($new.Length -lt $MinLength) { throw "El PIN nuevo debe tener al menos $MinLength caracteres." }
if ($new -eq $current) { throw 'El PIN nuevo es igual al actual.' }

# Un PIN debil no se rechaza, pero exige un reconocimiento explicito.
if ($new.Length -lt 16 -or $new -match '^\d+$') {
    $espacio = if ($new -match '^\d+$') { [math]::Pow(10, $new.Length) } else { $null }
    Write-Warning 'PIN debil: los blobs enc: viajan en un repositorio publico, asi que es lo unico que protege tus claves de Azure.'
    if ($espacio) {
        Write-Warning ("Solo numerico y de {0} digitos: {1:N0} combinaciones posibles." -f $new.Length, $espacio)
    }
    $ok = Read-Host 'Escribe ACEPTO para continuar de todos modos'
    if ($ok -ne 'ACEPTO') {
        Write-Host 'Cancelado: no se modifico nada.' -ForegroundColor Yellow
        return
    }
}

if (-not $PSCmdlet.ShouldProcess($envPath, "Recifrar $encCount secretos y renovar el salt")) {
    Write-Host 'Cancelado: no se modifico nada.' -ForegroundColor Yellow
    return
}

# --- Recifrado --------------------------------------------------------------
# El salt se respalda aparte: sin el, el .env previo queda irrecuperable.
$saltBackup = "$saltPath.bak-rotate"
Copy-Item $saltPath $saltBackup -Force

try {
    # Los dos PIN viajan por stdin, nunca por argv.
    $stdin = "$current`n$new"
    $output = $stdin | & $python $secretsPy rotate-pin $EnvFile 2>&1
    $code = $LASTEXITCODE
    $output | ForEach-Object { Write-Host $_ }
    if ($code -ne 0) { throw "secrets_local.py rotate-pin fallo (codigo $code)." }
}
catch {
    Copy-Item $saltBackup $saltPath -Force
    Write-Host 'Salt restaurado: el .env sigue accesible con el PIN actual.' -ForegroundColor Yellow
    throw
}
finally {
    $current = $null; $confirm = $null
    [GC]::Collect()
}

# --- Verificacion ------------------------------------------------------------
$env:AULATEX_MASTER_PIN = $new
$check = & $python $secretsPy decrypt-env $EnvFile 2>&1
$okCount = ($check | Where-Object { $_ -match "`t" }).Count

if ($okCount -lt $encCount) {
    Copy-Item $saltBackup $saltPath -Force
    throw "Verificacion fallida: solo $okCount de $encCount secretos descifran. Salt restaurado; recupera $envPath desde aulatex.env.bak-rotate."
}

Write-Host "Verificado: $okCount de $encCount secretos descifran con el PIN nuevo." -ForegroundColor Green
Remove-Item $saltBackup -Force

if ($Persist) {
    [Environment]::SetEnvironmentVariable('AULATEX_MASTER_PIN', $new, 'User')
    Write-Host 'PIN guardado en la variable de usuario AULATEX_MASTER_PIN.' -ForegroundColor Green
}
else {
    Write-Host 'PIN definido solo para esta consola. Usa -Persist para conservarlo.' -ForegroundColor Yellow
}

$new = $null
[GC]::Collect()

Write-Host ''
Write-Host 'Pendiente:' -ForegroundColor Cyan
Write-Host '  1. Confirma que AulaTeX opera y borra aulaTEX/aulatex.env.bak-rotate'
Write-Host '  2. Rota las claves en Azure si el PIN anterior estuvo expuesto:'
Write-Host '     .\aulaTEX\sync-keys.ps1 -Rotate'
Write-Host '  3. Haz commit del aulatex.env recifrado (el salt no se versiona).'
