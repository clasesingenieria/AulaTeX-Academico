$ErrorActionPreference='Stop'
$root='C:/Users/Sysx/Documents/AulaTeX-Academico/ITESCA/maestria-en-gestion-administrativa/seminario-i-mga'
$notes=Join-Path $root 'referencias-seminario-i/notas-seminario-i'
foreach($number in 1..11){
 $folder=Get-ChildItem -LiteralPath $notes -Directory | Where-Object Name -like ("actividad-$number-*") | Select-Object -First 1
 $record=Get-Content -LiteralPath (Join-Path $folder.FullName 'cotejo-plataforma-2026-10-10.json') -Raw | ConvertFrom-Json
 $plan=Get-ChildItem -LiteralPath (Join-Path $root 'planeaciones-seminario-i') -Filter ("Planeacion - Tarea "+$number.ToString('00')+' - *.md') | Select-Object -First 1
 $history=Join-Path $folder.FullName 'planeacion-anterior-a-cotejo-2026-10-10.md'
 if(-not(Test-Path -LiteralPath $history)){Copy-Item -LiteralPath $plan.FullName -Destination $history}
 $relative=[IO.Path]::GetRelativePath($plan.DirectoryName,$folder.FullName).Replace('\','/')
 $content="# Planeacion - Tarea $number - Seminario I`n`nConsulta autenticada de solo lectura: 10 de octubre de 2026. Modulo $($record.modulo).`n`n## Consigna oficial consultada`n`n$($record.consigna)`n`n## Estado observado`n`n$($record.estado)`n`n## Retroalimentacion consultada`n`n"
 $feedback=if($record.retroalimentacion_completa.Count){$record.retroalimentacion_completa -join "`n`n"}else{$record.retroalimentacion_visible}
 if(-not $feedback){$feedback='No se recupero comentario docente en esta consulta; no implica aprobacion.'}
 $content+=$feedback+"`n`n## Control de trabajo`n`n- [Consulta estructurada]($relative/cotejo-plataforma-2026-10-10.json).`n- [Nota de cotejo]($relative/cotejo-actividad-2026-10-10.md).`n- La ficha anterior se conserva en notas como antecedente. Los requisitos oficiales anteriores prevalecen sobre propuestas locales incompatibles.`n- No se realizaron envios. La calificacion mostrada no certifica el producto local revisado.`n"
 [IO.File]::WriteAllText($plan.FullName,$content,[Text.UTF8Encoding]::new($false))
 $specific=switch($number){
 1 {'Retroalimentacion: 80/80, recomendacion de portada institucional. El reporte local usa identidad ITESCA; no equivale al PDF historico enviado. Confirmar semestre, y revisar cuadro de 12 ideas y ensayo de 400-600 palabras antes de sustituir.'}
 2 {'Retroalimentacion: 20/20. El requisito oficial incluye elaboracion en Word con Arial 11 o Times New Roman 12 y PDF. La version LaTeX de siete paginas es auxiliar y no certifica equivalencia de formato; no modificar la entrega historica para simular otra elaboracion.'}
 3 {'Matricula 26130503 ya incorporada. El campo semestre no es equivalente al periodo y debe confirmarse. La docente solicita fuentes regionales cuando existan y revisar DOI; 23.60/25 en campo nota y 23.625/25 en comentario se conservan sin corregirlos. No se atribuyen al corpus resultados de vTaxi ni se inventa bibliografia regional.'}
 4 {'0/25 por no entregar. Infografia local elaborada con ocho errores; matricula confirmada, semestre y fecha de entrega pendientes. No se envio. Revisar ejemplos contra el material docente antes de cualquier publicacion.'}
 5 {'0/15 por no entregar. Producto oficial: diez respuestas en Google Forms, no un PDF. Material descargado para estudio. No se inicio ni envio el formulario irreversible; preguntas y video internos requieren acceso por el alumno, sin fabricar respuestas.'}
 6 {'0/15 por no enviar. DOCX preparado con indice actualizado, tablas y figuras; validacion local previa correcta. PDF LaTeX auxiliar, no sustituto. No se envio en esta revision.'}
 7 {'Foro con contexto profesional, fragmento LGAC institucional, tres ideas, titulo y justificacion de 5-7 lineas; exige dos replicas reales de 80-120 palabras. No se acredita interaccion guiada completa ni lectura de compañeros en esta consulta. Registro de tema no sustituye participacion y replicas.'}
 8 {'Retroalimentacion exige foco administrativo y antecedentes de compliance y movilidad directamente pertinentes. T10 y T11 mantienen ese enfoque y dos apoyos conceptuales con alcance limitado; busqueda regional/especifica sigue pendiente. El Word historico se conserva, sin afirmar que se corrigio aquella entrega.'}
 9 {'Documento Word acumulativo conservado; no se recupero comentario de deficiencia. Problema y preguntas deben permanecer administrativos y congruentes con objetivos; no equivalen a dictamen juridico de autorizacion.'}
 10 {'Word revisado enviado y sin calificar; SHA256 confirmado previamente. Objetivos y procedimientos administrativos, cuatro especificos y anexos. Su contenido se conserva como base de T11; no se reenviaron versiones.'}
 11 {'Prioridad atendida: DOCX acumulativo nuevo, cinco subapartados 4.1-4.5, indice actualizado con Word y PDF de revision de 24 paginas. Anexos con mismo contenido; fase documental viable, acceso adicional condicionado. Reporte LaTeX auxiliar creado. No enviado; acceso a actores y presupuesto no confirmados impiden afirmar viabilidad empirica completa.'}
 }
 $note="# Cotejo de actividad $number - 10 de octubre de 2026`n`n## Resultado y accion`n`n$specific`n`n## Fuentes del cotejo`n`n[Consigna y comentarios recuperados](cotejo-plataforma-2026-10-10.json). La planeacion vigente contiene el texto docente completo y separa el estado de entrega de la validez local.`n`n## Estado de esta intervencion`n`nConsulta y preparacion local. No se publicaron respuestas, no se iniciaron cuestionarios y no se modificaron archivos enviados.`n"
 [IO.File]::WriteAllText((Join-Path $folder.FullName 'cotejo-actividad-2026-10-10.md'),$note,[Text.UTF8Encoding]::new($false))
}
Write-Output 'Once planeaciones actualizadas con consigna y retroalimentacion; once notas de cotejo creadas.'