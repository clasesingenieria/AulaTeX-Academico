param([Parameter(Mandatory=$true)][string[]]$Paths)
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
 foreach ($item in $Paths) {
  $absolute = (Resolve-Path -LiteralPath $item).Path
  $pdf = [System.IO.Path]::ChangeExtension($absolute, '.pdf')
  $doc = $word.Documents.Open($absolute, $false, $false)
  try {
   foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
   $null = $doc.Fields.Update()
   $doc.Repaginate()
   $doc.Save()
   $doc.ExportAsFixedFormat($pdf, 17)
   Write-Output $pdf
  } finally { $doc.Close(0) }
 }
} finally { $word.Quit() }
