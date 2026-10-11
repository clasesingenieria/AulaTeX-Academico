& {
    $root = 'C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga'
    $evidence = Join-Path $root 'referencias-plan-de-negocios/notas-plan-de-negocios/actividad-13-examen-capitulos-1-4/evidencias/2026-10-10'
    $source = Join-Path $root 'reporte-plan-de-negocios-Actividad-13-Examen-1-4.tex'
    $answers = @('Descripción de la Empresa','Definición del nombre','Factores Claves de Éxito','Análisis de Mercado','Plan de promoción','Producto','Verdadero','Falso','Verdadero','Falso','Falso','Verdadero','Infraestructura Tecnológica','Verdadero','Localización de la empresa','Verdadero','Falso','Control de calidad')
    $values = @(2,2,1,2,0,0,1,0,1,0,0,1,3,1,2,1,0,2)
    $reasons = @(
        'La descripción presenta una semblanza integral: historia, conformación, objetivos, industria y rasgos distintivos. La misión y la visión expresan aspectos estratégicos específicos, no toda esa caracterización.',
        'El nombre identifica a la empresa y genera una primera impresión. Puede ser evocativo o arbitrario sin describir literalmente su actividad; el logotipo es su representación gráfica y el lema es una frase comunicativa.',
        'Los factores clave de éxito son elementos críticos para alcanzar los objetivos y diferenciarse de la competencia. No equivalen a los objetivos mismos ni al diagnóstico FODA.',
        'El análisis de mercado recopila, registra y analiza información para comprender problemas de comercialización. Oferta y demanda son dimensiones particulares de ese análisis.',
        'El plan de promoción coordina ventas personales, publicidad, promoción de ventas y relaciones públicas para comunicar un mensaje coherente e incentivar ventas.',
        'El producto reúne atributos tangibles e intangibles que ofrecen satisfacción de necesidades. El precio es solo un atributo económico; un servicio es una modalidad de oferta. El cuestionario presenta dos opciones idénticas llamadas Oferta.',
        'La misión explica la razón de ser de la organización: qué hace, para quién y con qué propósito. La afirmación corresponde a esa definición.',
        'La definición del rumbo futuro a largo plazo corresponde a la visión. Los objetivos señalan resultados que se pretende alcanzar y permiten orientar y evaluar acciones.',
        'FODA examina fortalezas y debilidades internas, así como oportunidades y amenazas del contexto externo. Por ello estudia la situación organizativa en ambas dimensiones.',
        'La descripción corresponde a fuentes primarias. Las secundarias reelaboran, sintetizan, interpretan o analizan información previamente producida.',
        'El enunciado describe comercialización o distribución. La demanda expresa las cantidades que los compradores desean y pueden adquirir bajo determinadas condiciones de precio y tiempo.',
        'La mercadotecnia desarrolla estrategias orientadas a satisfacer necesidades mediante propuestas de valor y alcanzar objetivos comerciales, como ventas, rentabilidad y participación de mercado.',
        'La infraestructura tecnológica integra hardware, software y servicios para almacenar, gestionar y proteger información. No se limita a maquinaria productiva ni al acomodo físico del local.',
        'Producción y operación coordinan mano de obra, materias primas, maquinaria y equipo para fabricar bienes o prestar servicios. La anticipación y sistematización de recursos forman parte de esa función.',
        'La localización es la ubicación geográfica de la empresa y afecta acceso a clientes y costos. El layout se refiere a la distribución interna de instalaciones.',
        'El proceso productivo relaciona acciones que transforman entradas en salidas y agregan valor. Un diagrama representa esas relaciones; no sustituye la ejecución del proceso.',
        'El volumen producido por unidad de tiempo describe capacidad de producción. El costo de producción es el valor de recursos consumidos para producir; no es una medida de volumen.',
        'El control de calidad identifica errores y no conformidades para impedir la entrega de productos o servicios defectuosos. Según el caso, se corrigen, retrabajan o rechazan; eliminar no implica necesariamente desecharlos.'
    )
    function Escape-Tex([string]$value) {
        $value.Replace('\','\textbackslash{}').Replace('&','\&').Replace('%','\%').Replace('#','\#').Replace('_','\_').Replace('$','\$')
    }
    $records = @()
    $sections = @('\section{Registro del intento realizado}', 'El intento 1, identificador 5058 del módulo 6553, fue finalizado el 10 de octubre de 2026. Moodle muestra inicio a las 19:25, finalización a las 19:32, duración de 7 minutos 14 segundos y calificación de 100,00 sobre 100,00. Las capturas locales se registraron entre las 20:25 y las 20:32 con zona horaria -06:00; no se equiparan esas horas con la hora mostrada por el aula.', 'Se observaron y guardaron 18 preguntas y sus respuestas durante el intento. El resumen previo al envío confirmó las 18 respuestas guardadas. La revisión posterior no está permitida: las justificaciones siguientes son razonamientos documentados, no retroalimentación oficial por pregunta. No se inició un segundo intento.')
    for ($index=0; $index -lt 18; $index++) {
        $number = $index + 1
        $snapshot = Get-Content -LiteralPath (Join-Path $evidence ('intento-5058-pregunta-{0:00}-respuesta.json' -f $number)) -Raw | ConvertFrom-Json
        $frame = $snapshot.frames | Where-Object { $_.text -match 'Enunciado de la pregunta' } | Select-Object -First 1
        $pattern = '(?s)Enunciado de la pregunta\s*(.*?)\s*Pregunta '+$number+'\s*Seleccione una:'
        $match = [regex]::Match($frame.text, $pattern)
        if (-not $match.Success) { throw "Enunciado ausente: $number" }
        $question = ($match.Groups[1].Value -replace '\s+',' ').Trim()
        $selected = @($frame.controls | Where-Object { $_.type -eq 'radio' -and $_.checked -and $_.value -ne '-1' })
        if ($selected.Count -ne 1 -or [int]$selected[0].value -ne $values[$index]) { throw "Selección no confirmada: $number" }
        $records += [ordered]@{numero=$number;pregunta=$question;respuesta=$answers[$index];valor_seleccionado=$values[$index];justificacion=$reasons[$index];evidencia=('intento-5058-pregunta-{0:00}-respuesta.json' -f $number)}
        $sections += '\subsection{Pregunta '+$number+'}'
        $sections += '\textbf{Pregunta:} '+(Escape-Tex $question)
        $sections += '\par\textbf{Respuesta seleccionada:} '+(Escape-Tex $answers[$index])+'.'
        $sections += '\par\textbf{Justificación:} '+(Escape-Tex $reasons[$index])
    }
    $text = Get-Content -LiteralPath $source -Raw
    $text = $text.Replace('\def\actividadproducto{Guía de estudio; no examen contestado}','\def\actividadproducto{Registro del examen: preguntas, respuestas y justificaciones}')
    $text = $text.Replace('\def\actividadfecha{23 de septiembre de 2026}','\def\actividadfecha{10 de octubre de 2026}')
    $text = $text.Replace('Esta guía no contiene preguntas observadas del examen ni acredita su realización.','El registro que sigue documenta el intento real del examen y conserva el repaso previo como contexto de estudio.')
    $text = $text.Replace('\section{Relaciones entre los cuatro capítulos}',($sections -join "`n")+"`n\section{Repaso previo: relaciones entre los cuatro capítulos}")
    $start = $text.IndexOf('\section{Conclusiones}')
    $text = $text.Substring(0,$start) + @'
\section{Conclusiones}
El intento 1 quedó finalizado con 100,00 sobre 100,00. Se documentaron las 18 preguntas observadas, las respuestas seleccionadas y su justificación conceptual. La calificación es global: Moodle no habilita revisión posterior ni retroalimentación individual. El repaso previo se conserva como contexto y no se confunde con los reactivos reales.\footnote{Se utilizó asistencia de inteligencia artificial para resolver el intento autorizado por el estudiante, registrar las selecciones y redactar sus justificaciones. El resultado y el estado de finalización proceden de la plataforma; las justificaciones no se atribuyen al docente.}
}
\input{reporte-plan-de-negocios-plantilla-actividad.tex}
'@
    [IO.File]::WriteAllText($source,$text,[Text.UTF8Encoding]::new($false))
    $record = [ordered]@{modulo=6553;intento_id=5058;intento_numero=1;estado='Finalizado';fecha_aula='2026-10-10';inicio_aula='19:25';fin_aula='19:32';duracion='7 minutos 14 segundos';calificacion=100;calificacion_maxima=100;revision_permitida=$false;resultado_evidencia='intento-5058-resultado.json';preguntas=$records}
    [IO.File]::WriteAllText((Join-Path $evidence 'registro-intento-5058.json'),($record | ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
    $readme = Join-Path $root 'Readme - Seminario I.md'
    $text = Get-Content -LiteralPath $readme -Raw
    $text = "## Estado vigente del examen de capítulos 1 al 4`n`nEl 10 de octubre de 2026 se finalizó el intento 1 (5058, módulo 6553): **100/100**, duración 7 minutos 14 segundos. [Reporte del examen](reporte-plan-de-negocios-Actividad-13-Examen-1-4.tex), [PDF](reporte-plan-de-negocios-Actividad-13-Examen-1-4.pdf) y [registro de las 18 preguntas, respuestas y justificaciones](referencias-plan-de-negocios/notas-plan-de-negocios/actividad-13-examen-capitulos-1-4/evidencias/2026-10-10/registro-intento-5058.json). Revisión posterior no permitida. Los estados de preparación que aparecen abajo son históricos.`n`n"+$text
    [IO.File]::WriteAllText($readme,$text,[Text.UTF8Encoding]::new($false))
    '18 preguntas y selecciones verificadas; reporte y registro del resultado actualizados.'
}