param(
    [Parameter(Mandatory = $true)]
    [string]$Fuentes,

    [Parameter(Mandatory = $true)]
    [string]$Planeacion,

    [Parameter(Mandatory = $true)]
    [string]$Salida,

    [string]$Motor = "anthropicfoundry",
    [switch]$Recursivo,
    [switch]$ProbarConfig,
    [int]$PlaneacionConceptos = 20,
    [int]$TopK = 12,
    [int]$MaxCitas = 8
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. .\.venv\Scripts\Activate.ps1

$recArg = if ($Recursivo) { '--recursivo' } else { '--no-recursivo' }
$probeArg = if ($ProbarConfig) { '--probar-config' } else { $null }

python run.py `
  --motor $Motor `
  --auto-conceptos-motor $(if ($Motor -eq 'anthropicfoundry') { 'anthropic-chat' } else { 'local' }) `
  --fuentes $Fuentes `
  --planeacion $Planeacion `
  --salida $Salida `
  $recArg `
  $probeArg `
  --planeacion-conceptos $PlaneacionConceptos `
  --top-k $TopK `
  --max-citas $MaxCitas
