param([switch]$Preview)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$sessions = @(
    @{slug='teoria-del-estado-y-constitucion';id='TEC';session='S1';date='2026-10-02';topic='Introduccion e historia y origen del Estado'},
    @{slug='teoria-del-estado-y-constitucion';id='TEC';session='S2';date='2026-10-09';topic='Historia y origen del Estado'},
    @{slug='antecedentes-de-los-derechos-humanos';id='ADH';session='Presentacion';date='2026-09-29';topic='Presentacion de la Experiencia Educativa'},
    @{slug='antecedentes-de-los-derechos-humanos';id='ADH';session='S2';date='2026-10-06';topic='Clase de semana 2'},
    @{slug='derecho-penal-especial-mexicano';id='DPEM';session='Sesion';date='2026-10-06';topic='Conferencias Web para el aprendizaje'}
)
$temporary = Join-Path $root 'tmp/composicion-grabaciones'
New-Item -ItemType Directory -Path $temporary -Force | Out-Null
$records = @()
foreach ($session in $(if($Preview){@($sessions[1])}else{$sessions})) {
    $slug = $session.slug
    $folder = Join-Path $root "UnADM/licenciatura-en-derecho-unadm/$slug-lde/referencias-$slug/grabaciones-$slug"
    $camera = Join-Path $folder "Grabacion - $($session.date) - Camara y audio.webm"
    $screen = Join-Path $folder "Grabacion - $($session.date) - Pantalla compartida.webm"
    if (-not (Test-Path -LiteralPath $camera) -or -not (Test-Path -LiteralPath $screen)) {
        throw 'Fuentes auxiliares retiradas tras limpieza autorizada. Usar el MP4 final; recuperar originales del aula solo si necesita recomponer.'
    }
    $cameraHash = (Get-FileHash -LiteralPath $camera).Hash.ToLowerInvariant()
    $screenHash = (Get-FileHash -LiteralPath $screen).Hash.ToLowerInvariant()
    $sourceInfo = (& ffprobe -v error -show_format -show_streams -of json $camera | ConvertFrom-Json)
    if($LASTEXITCODE -ne 0){throw 'No se pudo inspeccionar original'}
    $duration = [double]::Parse($sourceInfo.format.duration,[Globalization.CultureInfo]::InvariantCulture)
    if($Preview){$duration=30}
    $name = "UnADM - $($session.id) - $($session.session) $($session.date) - $($session.topic).mp4"
    $destination = if($Preview){Join-Path $temporary 'muestra-TEC-S2.mp4'}else{Join-Path $folder $name}
    $work = Join-Path $temporary "combinado-$($session.id)-$($session.date).mp4"
    if(-not(Test-Path -LiteralPath $destination)) {
        if(Test-Path -LiteralPath $work){throw 'Composicion parcial existente: revisar antes de sobrescribir'}
        $filter = '[1:v]setpts=PTS-STARTPTS,scale=960:720:force_original_aspect_ratio=decrease,pad=960:720:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=15[screen];[0:v]setpts=PTS-STARTPTS,scale=320:720:force_original_aspect_ratio=decrease,pad=320:720:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=15[camera];[screen][camera]hstack=inputs=2[video]'
        & ffmpeg -nostdin -v error -n -i $camera -i $screen -filter_complex $filter -map '[video]' -map '0:a:0' -c:v libx264 -preset veryfast -crf 23 -threads 4 -c:a aac -b:a 128k -t ($duration.ToString('0.000',[Globalization.CultureInfo]::InvariantCulture)) -movflags +faststart -metadata "title=$($session.topic)" -metadata "comment=Composicion local de componentes BigBlueButton; no exportacion oficial de diapositivas y chat" $work
        if($LASTEXITCODE -ne 0){throw 'Fallo de composicion FFmpeg'}
        Move-Item -LiteralPath $work -Destination $destination
    }
    $info = (& ffprobe -v error -show_format -show_streams -of json $destination | ConvertFrom-Json)
    if($LASTEXITCODE -ne 0){throw 'MP4 no validado'}
    $video = @($info.streams | Where-Object codec_type -eq 'video')
    $audio = @($info.streams | Where-Object codec_type -eq 'audio')
    $actualDuration=[double]::Parse($info.format.duration,[Globalization.CultureInfo]::InvariantCulture)
    if($video.Count -ne 1 -or $audio.Count -ne 1 -or $video[0].width -ne 1280 -or $video[0].height -ne 720 -or [Math]::Abs($actualDuration-$duration) -gt 2){throw 'Pistas, dimensiones o duracion incoherentes'}
    if((Get-FileHash -LiteralPath $camera).Hash.ToLowerInvariant() -ne $cameraHash -or (Get-FileHash -LiteralPath $screen).Hash.ToLowerInvariant() -ne $screenHash){throw 'Original alterado'}
    $frame = Join-Path $temporary "revision-$($session.id)-$($session.date).png"
    & ffmpeg -nostdin -v error -y -ss 15 -i $destination -frames:v 1 $frame
    if($LASTEXITCODE -ne 0){throw 'No se pudo revisar fotograma'}
    $record = [ordered]@{materia=$slug;identificador=$session.id;sesion=$session.session;fecha=$session.date;tema=$session.topic;archivo=[IO.Path]::GetRelativePath($root,$destination).Replace('\','/');sha256=(Get-FileHash -LiteralPath $destination).Hash.ToLowerInvariant();duracion_segundos=$actualDuration;video='H264 1280x720 15fps';audio='AAC 128k';fuentes=@(@{archivo=[IO.Path]::GetFileName($camera);sha256=$cameraHash},@{archivo=[IO.Path]::GetFileName($screen);sha256=$screenHash});limite='Pantalla compartida y camara/audio combinados localmente; no incluye diapositivas interactivas ni chat separados del reproductor; tema literal del aula cuando no hay titulo especifico'}
    $records += $record
    if(-not $Preview){$record | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $folder "UnADM - $($session.id) - $($session.session) $($session.date) - composicion.json") -Encoding utf8}
    "$($session.id) $($session.session) $($session.date): $actualDuration segundos; video y audio verificados."
}
if(-not $Preview){$records | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'grabaciones-combinadas.json') -Encoding utf8}