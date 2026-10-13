Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. .\.venv\Scripts\Activate.ps1

python run.py `
  --motor azure `
  --fuentes "../../UnADM/etica-y-moral-juridica/referencias-etica-y-moral-juridica" `
  --planeacion "../../UnADM/etica-y-moral-juridica/planeaciones-etica-y-moral-juridica/Planificacion-S8-extraida.txt" `
  --salida "../../salidas/fichas/etica-y-moral-juridica/semana-08" `
  --recursivo `
  --planeacion-conceptos 20 `
  --top-k 12 `
  --max-citas 8
