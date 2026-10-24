param([switch]$Preview, [string]$InputJson = 'grabaciones-combinadas.json', [string]$OutputJson = 'transcripciones-grabaciones.json')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$engine = Join-Path $env:APPDATA 'Subtitle Edit/SpeechToText/Purfview-Faster-Whisper-XXL/faster-whisper-xxl.exe'
$models = Join-Path (Split-Path $engine) '_models'
$inputs = @(Get-Content -LiteralPath (Join-Path $PSScriptRoot $InputJson) -Raw | ConvertFrom-Json)
$records = @()
function RepairZeroDuration($path) {
    $text = [IO.File]::ReadAllText($path)
    $blocks = [regex]::Split($text.Trim(),'\r?\n\s*\r?\n')
    $repairs = @()
    for ($index = 0; $index -lt $blocks.Count; $index++) {
        $match = [regex]::Match($blocks[$index],'^(\d+)\r?\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})')
        if ($match.Success -and $match.Groups[2].Value -eq $match.Groups[3].Value) {
            $start = [TimeSpan]::Parse($match.Groups[2].Value.Replace(',','.'),[Globalization.CultureInfo]::InvariantCulture)
            $end = $start.Add([TimeSpan]::FromMilliseconds(100))
            $overlap = $false
            if ($index + 1 -lt $blocks.Count) {
                $next = [regex]::Match($blocks[$index+1],'\d{2}:\d{2}:\d{2},\d{3}')
                $nextStart = [TimeSpan]::Parse($next.Value.Replace(',','.'),[Globalization.CultureInfo]::InvariantCulture)
                if ($end -gt $nextStart) {
                    if ($nextStart -gt $start) { $end = $nextStart } else { $overlap = $true }
                }
            }
            $newEnd = $end.ToString('hh\:mm\:ss\,fff')
            $blocks[$index] = $blocks[$index].Replace($match.Groups[2].Value+' --> '+$match.Groups[3].Value,$match.Groups[2].Value+' --> '+$newEnd)
            $repairs += @{segmento=$match.Groups[1].Value;inicio=$match.Groups[2].Value;fin_original=$match.Groups[3].Value;fin_corregido=$newEnd;solapamiento_minimo=$overlap;motivo='Duracion nula generada por motor; texto intacto; revisar segmentos simultaneos'}
        }
    }
    if ($repairs.Count) {
        $backup = Join-Path (Split-Path $path) 'salida-original-motor.srt'
        if (-not (Test-Path -LiteralPath $backup)) { Copy-Item -LiteralPath $path -Destination $backup }
        [IO.File]::WriteAllText($path,($blocks -join "`r`n`r`n")+"`r`n",[Text.UTF8Encoding]::new($false))
        $repairs | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path (Split-Path $path) 'reparaciones-tiempos-srt.json') -Encoding utf8
    }
}
function ValidateSrt($path,$duration) {
    $text = [IO.File]::ReadAllText($path)
    $blocks = [regex]::Split($text.Trim(),'\r?\n\s*\r?\n')
    $previous = -1.0
    $last = 0.0
    $number = 0
    foreach ($block in $blocks) {
        $match = [regex]::Match($block,'^(\d+)\r?\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\r?\n([\s\S]+)$')
        if (-not $match.Success) { throw 'Bloque SRT no valido' }
        $number++
        if ([int]$match.Groups[1].Value -ne $number) { throw 'Numeracion SRT incoherente' }
        $start = [TimeSpan]::Parse($match.Groups[2].Value.Replace(',','.'),[Globalization.CultureInfo]::InvariantCulture).TotalSeconds
        $end = [TimeSpan]::Parse($match.Groups[3].Value.Replace(',','.'),[Globalization.CultureInfo]::InvariantCulture).TotalSeconds
        if ($start -lt $previous -or $end -le $start -or $end -gt $duration+2) { throw 'Tiempos SRT fuera de rango' }
        $previous=$start
        $last=$end
    }
    if ($number -eq 0) { throw 'Transcripcion vacia' }
    return @{segmentos=$number;ultimo_fin=$last}
}
foreach ($item in $(if($Preview){@($inputs[0])}else{$inputs})) {
    $video = Join-Path $root $item.archivo
    if ((Get-FileHash -LiteralPath $video).Hash.ToLowerInvariant() -ne $item.sha256) { throw 'Video no coincide con version registrada' }
    $srt = [IO.Path]::ChangeExtension($video,'.srt')
    $temporary = Join-Path $root "tmp/transcripcion-$($item.identificador)-$($item.fecha)"
    New-Item -ItemType Directory -Path $temporary -Force | Out-Null
    $audio = Join-Path $temporary 'entrada.wav'
    $duration = if($Preview){60.0}else{[double]$item.duracion_segundos}
    $engineExit = $null
    $cached = $false
    if ($Preview -or -not(Test-Path -LiteralPath $srt)) {
        $generated = Join-Path $temporary 'entrada.srt'
        $cached = $false
        if (-not $Preview -and (Test-Path -LiteralPath $generated) -and (Test-Path -LiteralPath $audio)) {
            $audioInfo = (& ffprobe -v error -show_entries format=duration -of json $audio | ConvertFrom-Json)
            $audioDuration = [double]::Parse($audioInfo.format.duration,[Globalization.CultureInfo]::InvariantCulture)
            if ([Math]::Abs($audioDuration-$duration) -lt 2) { RepairZeroDuration $generated; $validation = ValidateSrt $generated $duration; $cached = $true }
        }
        if (-not $cached) {
        & ffmpeg -nostdin -v error -y -i $video -vn -ac 1 -ar 16000 -t ($duration.ToString('0.000',[Globalization.CultureInfo]::InvariantCulture)) $audio
        if ($LASTEXITCODE -ne 0) { throw 'Extraccion temporal de audio fallida' }
        $log = Join-Path $PSScriptRoot "transcripcion-$($item.identificador)-$($item.fecha).log"
        & $engine $audio --model large-v3 --model_dir $models --language Spanish --task transcribe --output_dir $temporary --output_format srt --standard --beep_off *> $log
        $engineExit = $LASTEXITCODE
        if ($engineExit -ne 0 -and (-not(Test-Path -LiteralPath $generated) -or -not([IO.File]::ReadAllText($log).Contains('Operation finished')))) { throw 'Motor fallo sin completar salida' }
        }
        if (-not(Test-Path -LiteralPath $generated)) { throw 'Motor no genero SRT' }
        RepairZeroDuration $generated
        $validation = ValidateSrt $generated $duration
        if($Preview){
            "Prueba: $($validation.segmentos) segmentos SRT validos."
            Get-Content -LiteralPath $generated -TotalCount 18
            return
        }
        if (Test-Path -LiteralPath $srt) { throw 'SRT creado durante proceso: no sobrescribir' }
        Copy-Item -LiteralPath $generated -Destination $srt
    }
    $validation = ValidateSrt $srt $duration
    $notes = Join-Path $root "UnADM/licenciatura-en-derecho-unadm/$($item.materia)-lde/referencias-$($item.materia)/notas-$($item.materia)/materiales-generales/control-grabaciones"
    New-Item -ItemType Directory -Path $notes -Force | Out-Null
    $transcript = Join-Path $notes ([IO.Path]::GetFileNameWithoutExtension($video) + ' - Transcripcion.txt')
    $blocks = [regex]::Split([IO.File]::ReadAllText($srt).Trim(),'\r?\n\s*\r?\n')
    $paragraphs = @($blocks | ForEach-Object { [regex]::Replace($_,'^\d+\r?\n[^\r\n]+\r?\n','').Replace("`r`n",' ').Replace("`n",' ') })
    [IO.File]::WriteAllText($transcript,($paragraphs -join "`r`n`r`n")+"`r`n",[Text.UTF8Encoding]::new($false))
    foreach ($auxiliary in @('salida-original-motor.srt','reparaciones-tiempos-srt.json')) {
        $source = Join-Path $temporary $auxiliary
        if (Test-Path -LiteralPath $source) { Copy-Item -LiteralPath $source -Destination (Join-Path $notes "$($item.identificador) - $($item.fecha) - $auxiliary") }
    }
    $records += [ordered]@{mp4=$item.archivo;sha256_mp4=$item.sha256;srt=[IO.Path]::GetRelativePath($root,$srt).Replace('\','/');sha256_srt=(Get-FileHash -LiteralPath $srt).Hash.ToLowerInvariant();motor='Purfview Faster Whisper XXL';modelo='large-v3';idioma='Spanish';tarea='transcribe';ajuste='--standard';codigo_motor=$engineExit;salida_reutilizada=$cached;validacion=$validation;fecha=[DateTimeOffset]::Now.ToString('o');estado='Transcripcion automatica; estructura y tiempos verificados; exactitud juridica y revision personal pendientes';postprocesamiento='Segmentacion standard del motor; no acredita equivalencia con todos los ajustes GUI de Subtitle Edit'}
    $records[-1]['texto'] = [IO.Path]::GetRelativePath($root,$transcript).Replace('\','/')
    $records | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $PSScriptRoot $OutputJson) -Encoding utf8
    Remove-Item -LiteralPath $temporary -Recurse -Force
    "$($item.identificador) $($item.fecha): $($validation.segmentos) segmentos; SRT guardado junto al MP4."
}