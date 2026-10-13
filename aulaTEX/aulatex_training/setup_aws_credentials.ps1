<#
.SYNOPSIS
    Configura y verifica las credenciales de AWS para los jobs de entrenamiento.

.DESCRIPTION
    Cierra el ciclo de credenciales sin exponer secretos en el historial ni en
    el chat:

      1. Pide las llaves con Read-Host -AsSecureString (no quedan en el
         historial de PowerShell ni se muestran en pantalla).
      2. Las escribe en el perfil de AWS CLI (%USERPROFILE%\.aws\credentials).
      3. Verifica identidad (STS), permisos de SageMaker y cuotas de GPU.
      4. Opcionalmente las cifra en el .env del hub con la clave Fernet
         derivada del PIN (parametro -EncryptToEnv).

    CONTEXTO (verificado el 2026-07-30):
      * Las credenciales cifradas previas son IRRECUPERABLES: se cifraron con
        una clave aleatoria que se perdio (0 de 108 valores descifrables).
      * Las credenciales halladas en el historial de git (commit c3af78d) las
        rechaza AWS con InvalidClientTokenId: estan revocadas.
      * Por eso hace falta ROTAR las llaves en la consola de AWS:
        IAM -> Users -> tu usuario -> Security credentials -> Create access key
        (y desactivar la anterior).

    CUOTAS DE GPU (segun los laboratorios del hub, 2026-07-24):
      * G/VT vCPU = 8   -> ml.g5.2xlarge VIABLE (A10G/L4, 24 GB)
      * P   vCPU = 8    -> INSERVIBLE: p4d.24xlarge exige 96 vCPU
      * Azure GPU       -> bloqueado por API en PayAsYouGo (requiere ticket)

.PARAMETER Region
    Region de AWS. Por defecto us-east-1 (donde estan las cuotas aprobadas).

.PARAMETER EncryptToEnv
    Ademas del perfil de AWS CLI, cifra las llaves en el .env indicado usando
    la clave Fernet del hub (derivada del PIN). Requiere AULATEX_MASTER_PIN o el
    archivo secret.key presente.

.PARAMETER SkipConfigure
    Omite la captura de llaves y solo ejecuta la verificacion (util si ya
    corriste 'aws configure' por tu cuenta).

.EXAMPLE
    .\aulaTEX\aulatex_training\setup_aws_credentials.ps1

.EXAMPLE
    # Solo verificar, sin capturar llaves:
    .\aulaTEX\aulatex_training\setup_aws_credentials.ps1 -SkipConfigure

.EXAMPLE
    # Capturar, verificar y cifrar en el .env del hub:
    .\aulaTEX\aulatex_training\setup_aws_credentials.ps1 `
        -EncryptToEnv 'C:\ahk-Autohokey\aulaTEX\agentes.env'
#>
[CmdletBinding()]
param(
    [string]$Region = 'us-east-1',
    [string]$EncryptToEnv = '',
    [switch]$SkipConfigure
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw "No existe el entorno virtual: $python. Crealo con: py -3.12 -m venv .venv"
}

# El AWS CLI recien instalado puede no estar en el PATH de la sesion actual.
$awsExe = 'C:\Program Files\Amazon\AWSCLIV2\aws.exe'
if (-not (Test-Path $awsExe)) {
    $cmd = Get-Command aws -ErrorAction SilentlyContinue
    if ($cmd) { $awsExe = $cmd.Source } else { $awsExe = '' }
}

function Convert-SecureToPlain {
    param([System.Security.SecureString]$Secure)
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

# ------------------------------------------------------- 1. capturar las llaves
if (-not $SkipConfigure) {
    Write-Host ''
    Write-Host '  Configuracion de credenciales AWS' -ForegroundColor Cyan
    Write-Host '  ---------------------------------' -ForegroundColor DarkCyan
    Write-Host '  Obtenlas en: IAM -> Users -> Security credentials -> Create access key'
    Write-Host '  Se piden de forma oculta: no quedan en el historial.' -ForegroundColor DarkGray
    Write-Host ''

    $keyIdSecure = Read-Host '  AWS Access Key ID' -AsSecureString
    $secretSecure = Read-Host '  AWS Secret Access Key' -AsSecureString

    $keyId = (Convert-SecureToPlain $keyIdSecure).Trim()
    $secret = (Convert-SecureToPlain $secretSecure).Trim()

    if (-not $keyId -or -not $secret) {
        throw 'No se capturaron las credenciales (valores vacios).'
    }
    if ($keyId -notmatch '^[A-Z0-9]{16,128}$') {
        Write-Host '  AVISO: el Access Key ID no tiene el formato tipico (AKIA...).' -ForegroundColor Yellow
    }

    if (-not $awsExe) {
        throw 'No se encontro aws.exe. Instala AWS CLI: winget install Amazon.AWSCLI'
    }

    & $awsExe configure set aws_access_key_id $keyId
    & $awsExe configure set aws_secret_access_key $secret
    & $awsExe configure set region $Region
    & $awsExe configure set output json

    Write-Host "  Perfil escrito en $env:USERPROFILE\.aws\credentials (region $Region)." -ForegroundColor Green

    # Cifrado opcional en el .env del hub con la clave Fernet del proyecto.
    if ($EncryptToEnv) {
        $env:AULATEX_TMP_AKID = $keyId
        $env:AULATEX_TMP_SECRET = $secret
        try {
            & $python (Join-Path $PSScriptRoot 'encrypt_aws_into_env.py') --env-file $EncryptToEnv --region $Region
        } finally {
            Remove-Item Env:\AULATEX_TMP_AKID -ErrorAction SilentlyContinue
            Remove-Item Env:\AULATEX_TMP_SECRET -ErrorAction SilentlyContinue
        }
    }

    # Limpiar las variables en claro de la sesion.
    Remove-Variable keyId, secret, keyIdSecure, secretSecure -ErrorAction SilentlyContinue
    [System.GC]::Collect()
}

# ---------------------------------------------------------- 2. verificar acceso
Write-Host ''
Write-Host '  Verificacion de acceso (read-only)' -ForegroundColor Cyan
Write-Host '  ----------------------------------' -ForegroundColor DarkCyan

$env:AWS_REGION = $Region
& $python (Join-Path $PSScriptRoot 'submit_cloud_job.py') --backend aws --check
$checkExit = $LASTEXITCODE

Write-Host ''
if ($checkExit -eq 0) {
    Write-Host '  LISTO: credenciales validas y permisos de entrenamiento confirmados.' -ForegroundColor Green
    Write-Host '  Siguiente paso: lanzar el job de entrenamiento a la GPU.' -ForegroundColor Green
} else {
    Write-Host '  Verificacion incompleta. Revisa los mensajes anteriores.' -ForegroundColor Yellow
    Write-Host '  Causas frecuentes:' -ForegroundColor DarkGray
    Write-Host '    - Llaves revocadas o mal escritas -> vuelve a crearlas en IAM.' -ForegroundColor DarkGray
    Write-Host '    - Falta politica IAM de SageMaker -> anade AmazonSageMakerFullAccess.' -ForegroundColor DarkGray
    Write-Host '    - Falta SAGEMAKER_ROLE_ARN -> crea el rol de ejecucion.' -ForegroundColor DarkGray
}

exit $checkExit
