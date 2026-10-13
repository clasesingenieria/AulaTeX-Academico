param([string]$InputPath, [string]$OutputDir, [switch]$Update)
$ErrorActionPreference='Stop'
$resolvedInput=(Resolve-Path -LiteralPath $InputPath).Path
$resolvedOutput=[System.IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Path $resolvedOutput -Force | Out-Null
$word=New-Object -ComObject Word.Application
$word.Visible=$false
$word.DisplayAlerts=0
try {
  $doc=$word.Documents.Open($resolvedInput,$false,(-not $Update.IsPresent))
  if ($Update) {
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Fields.Update() | Out-Null
    $doc.Repaginate()
    foreach ($toc in $doc.TablesOfContents) { $toc.UpdatePageNumbers() }
    $doc.Save()
  }
  $pdf=Join-Path $resolvedOutput ([System.IO.Path]::GetFileNameWithoutExtension($resolvedInput)+'.pdf')
  $doc.ExportAsFixedFormat($pdf,17)
  Write-Output ('Exported: '+[System.IO.Path]::GetFileName($pdf)+'; pages: '+$doc.ComputeStatistics(2))
  $doc.Close(0)
} finally {
  $word.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
