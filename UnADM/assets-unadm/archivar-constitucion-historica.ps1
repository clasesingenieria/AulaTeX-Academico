$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../licenciatura-en-derecho-unadm/teoria-del-estado-y-constitucion-lde')).Path
$refs = Join-Path $root 'referencias-teoria-del-estado-y-constitucion'
$books = Join-Path $refs 'libros-teoria-del-estado-y-constitucion'
$archive = Join-Path $refs 'notas-teoria-del-estado-y-constitucion/materiales-generales/normativa-historica'
New-Item -ItemType Directory -Path $archive -Force | Out-Null
$records = @()
foreach ($extension in @('.pdf','.txt')) {
    $source = Join-Path $books ('Constitucion Politica de los Estados Unidos Mexicanos (copia biblioteca) - Camara de Diputados'+$extension)
    $target = Join-Path $archive ('Constitucion Politica de los Estados Unidos Mexicanos (reforma 2026-06-02) - Camara de Diputados'+$extension)
    if (Test-Path -LiteralPath $target) { throw 'Destino historico existente' }
    $hash = (Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant()
    Move-Item -LiteralPath $source -Destination $target
    if ((Get-FileHash -LiteralPath $target).Hash.ToLowerInvariant() -ne $hash) { throw 'Hash alterado' }
    $records += @{origen=[IO.Path]::GetRelativePath($root,$source).Replace('\','/');destino=[IO.Path]::GetRelativePath($root,$target).Replace('\','/');sha256=$hash}
}
$inventory = Join-Path $books 'inventario-libros.json'
Copy-Item -LiteralPath $inventory -Destination (Join-Path $archive 'inventario-libros-antes-archivo.json')
$data = Get-Content -LiteralPath $inventory -Raw | ConvertFrom-Json
foreach ($entry in $data) {
    if ($entry.sha256 -eq 'ca63a23a4b7444ebdbdad93759fbf46bd14c069e587c5878decf89fc9c12ca8e') {
        $entry.archivo = [IO.Path]::GetRelativePath($books,(Join-Path $root $records[0].destino)).Replace('\','/')
        $entry.estado = 'Version historica archivada; no usar como consolidacion mas reciente'
        $entry.vigencia_normativa = 'Ultimas reformas DOF 02-06-2026 indicadas en el documento'
    }
}
$data | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $inventory -Encoding utf8
@{fecha='2026-10-11';movimientos=$records;eliminados=0;motivo='Versiones no identicas: reforma 02-06-2026 archivada; reforma 07-10-2026 permanece en libros.'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $archive 'registro-archivo.json') -Encoding utf8
foreach ($entry in $data) { if(-not(Test-Path -LiteralPath (Join-Path $books $entry.archivo))){throw 'Inventario roto'} }
'PDF/TXT historicos archivados; una sola version de Constitucion en libros; hashes e inventario verificados.'