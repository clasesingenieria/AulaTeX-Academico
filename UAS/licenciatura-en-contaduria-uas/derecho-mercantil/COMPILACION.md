# Compilación

Desde la raíz del repositorio, con MiKTeX, Arial, XeLaTeX, Biber y latexmk disponibles:

```powershell
.\aulaTEX\latexmk-build.ps1 UAS/licenciatura-en-contaduria-uas/derecho-mercantil/reporte-derecho-mercantil.tex -CleanMode none -xelatex
.\aulaTEX\latexmk-build.ps1 UAS/licenciatura-en-contaduria-uas/derecho-mercantil/actividad-derecho-mercantil.tex -CleanMode none -xelatex
.\aulaTEX\latexmk-build.ps1 UAS/licenciatura-en-contaduria-uas/derecho-mercantil/presentacion-derecho-mercantil.tex -CleanMode none -xelatex
```

Los tres ejemplos se compilaron el 22/09/2026. Los PDF quedan junto al TEX y los auxiliares en `.build/latex`. El adaptador local carga explícitamente la base institucional UAS; los logos se resuelven desde los assets de la materia. Los reportes usan APA mediante biblatex/Biber, no BibTeX.

Para una actividad nueva, definir título, datos confirmados y contenido antes de cargar el adaptador de materia. La portada usa fecha de realización, no vence ni incorpora identificadores técnicos del aula. Las fechas de ejemplo son dinámicas; fijarlas al generar una versión final.

La compilación sólo valida el documento técnico. No satisface por sí misma el requisito manuscrito de S1–S3, la extensión del ensayo ni acredita una entrega. Los PDF de muestra conservan campos por completar.

## Reporte de lectura S1

Procedimiento histórico de preparación: la consulta del 12/10/2026 ya confirma entrega y calificación 5/5. No volver a enviar la maqueta ni sustituir el archivo entregado siguiendo estos ejemplos.

Punto de entrada de la actividad 1 (independiente de las plantillas y de los borradores anteriores):

```powershell
.\aulaTEX\latexmk-build.ps1 UAS/licenciatura-en-contaduria-uas/derecho-mercantil/reporte-derecho-mercantil-Actividad-1.tex -CleanMode none -xelatex
Copy-Item -LiteralPath 'UAS/licenciatura-en-contaduria-uas/derecho-mercantil/reporte-derecho-mercantil-Actividad-1.pdf' -Destination 'UAS/licenciatura-en-contaduria-uas/derecho-mercantil/ReporteLectura_S1_MartinJonathanDeLaCruzMunoz.pdf'
```

La actividad reutiliza `UAS/plantilla-actividad-uas.tex`, los logos de la materia y `derecho-mercantil-actividad-1.bib`. Biber resuelve las cinco citas a una obra asignada. El PDF con nomenclatura de entrega es una copia del PDF compilado; aún requiere sustituir el cuerpo tipográfico por el manuscrito personal para cumplir la consigna. El soporte de páginas, las excepciones justificadas al contrato genérico y el resultado de la revisión se guardan en `investigacion-aulatex/actividad-1/`.

## Semana 3: revisión del 9 de octubre

El mapa tiene portada y dos páginas de contenido; el foro tiene cuatro páginas. Ambos cargan la base UAS sin modificarla. El mapa es apoyo para escribir a mano, no archivo final de entrega. Consulta [las decisiones contractuales](investigacion-aulatex/actividad-3/memoria-y-validacion.md).

En esta revisión el lanzador latexmk falló al iniciar XeLaTeX. Se completó la compilación directa con TeX Live 2026, Biber y dos pasadas finales, sin cambiar la configuración compartida. Desde la raíz, con `xelatex` y `biber` disponibles en PATH:

```powershell
foreach ($name in @('reporte-derecho-mercantil-Actividad-3', 'reporte-foro-S3')) {
    $source = "UAS/licenciatura-en-contaduria-uas/derecho-mercantil/$name.tex"
    & xelatex '-interaction=nonstopmode' '-halt-on-error' '-output-directory=.build/latex' $source
    if ($LASTEXITCODE -ne 0) { throw "Fallo XeLaTeX: $name" }
    & biber ".build/latex/$name"
    if ($LASTEXITCODE -ne 0) { throw "Fallo Biber: $name" }
    foreach ($pass in 1..2) {
        & xelatex '-interaction=nonstopmode' '-halt-on-error' '-output-directory=.build/latex' $source
        if ($LASTEXITCODE -ne 0) { throw "Fallo pasada final: $name" }
    }
}
```

Los argumentos con `=` se conservan entre comillas en PowerShell. Antes de promover el PDF, comprobar citas, referencias, páginas, imágenes y ausencia de desbordamientos. Los PDF validados se copian desde `.build/latex` a la raíz de la materia. Si la automatización del editor limpia auxiliares durante otra compilación, repetir el recorrido completo con Biber; la mera existencia del PDF no acredita su frescura ni sus citas.

## Integrador S4

[Fuente](PI_MOD_MartinJonathanDeLaCruzMunoz.tex), [PDF de borrador](PI_MOD_MartinJonathanDeLaCruzMunoz.pdf) y [bibliografía](integrador-S4.bib). Compilación verificada con TeX Live 2026 el 12/10/2026. Auxiliares exclusivos para no interferir con otras materias. Ejecutar desde la raíz del repositorio, con XeLaTeX y Biber de TeX Live disponibles en PATH:

```powershell
$output = '.build/latex/uas-integrador-S4'
$stem = 'PI_MOD_MartinJonathanDeLaCruzMunoz'
$course = 'UAS/licenciatura-en-contaduria-uas/derecho-mercantil'
New-Item -ItemType Directory -Path $output -Force | Out-Null
& xelatex '-interaction=nonstopmode' '-halt-on-error' "-output-directory=$output" "$course/$stem.tex"
if ($LASTEXITCODE -ne 0) { throw 'Fallo XeLaTeX' }
& biber "$output/$stem"
if ($LASTEXITCODE -ne 0) { throw 'Fallo Biber' }
foreach ($pass in 1..2) {
    & xelatex '-interaction=nonstopmode' '-halt-on-error' "-output-directory=$output" "$course/$stem.tex"
    if ($LASTEXITCODE -ne 0) { throw 'Fallo pasada final' }
}
& pdfinfo "$output/$stem.pdf"
```

Después de revisar páginas, citas, tamaño y presentación, actualizar el PDF de esta misma actividad:

```powershell
Copy-Item -LiteralPath "$output/$stem.pdf" -Destination "$course/$stem.pdf"
Get-FileHash -Algorithm SHA256 -LiteralPath "$output/$stem.pdf", "$course/$stem.pdf"
```

Resultado validado: siete páginas, 255 479 bytes, dos referencias resueltas y sin desbordamientos. [Detalle y límites de validación](referencias-derecho-mercantil/notas-derecho-mercantil/actividad-04-integrador/README.md#validación-del-borrador). La base institucional no se modificó: esta actividad define su bibliografía y carga directamente la plantilla compartida para evitar la bibliografía general del adaptador histórico. Compilar no retira la condición de borrador ni realiza el envío.

## Ishikawa S2

[Fuente](reporte-derecho-mercantil-Actividad-2.tex), [PDF](reporte-derecho-mercantil-Actividad-2.pdf) y [bibliografía](sujetos-S2.bib). Reutiliza la base UAS y carga TikZ con las bibliotecas `arrows.meta,babel` para que las flechas funcionen con español.

Aplicar la misma secuencia XeLaTeX, Biber y dos pasadas finales del integrador, sustituyendo las variables antes de ejecutar los comandos:

```powershell
$output = '.build/latex/uas-sujetos-S2'
$stem = 'reporte-derecho-mercantil-Actividad-2'
$course = 'UAS/licenciatura-en-contaduria-uas/derecho-mercantil'
```

Resultado verificado: tres páginas carta, 248 303 bytes, cuatro diagramas, dos referencias, sin citas pendientes ni desbordamientos. Se revisaron visualmente las tres páginas y el hash de la copia. [Fuentes, localizadores y límites](referencias-derecho-mercantil/notas-derecho-mercantil/actividad-02-ishikawa/README.md). El PDF es una maqueta digital y no se renombra como manuscrito terminado; el cuerpo personal y la autorización para entrega extemporánea siguen pendientes.

## Reporte del foro S2

[Fuente](reporte-foro-S2.tex), [PDF](reporte-foro-S2.pdf) y [bibliografía compartida de S2](sujetos-S2.bib). Usar la secuencia XeLaTeX, Biber y dos pasadas finales indicada para el integrador con `$output = '.build/latex/uas-foro-S2'` y `$stem = 'reporte-foro-S2'`.

Validado con TeX Live 2026: cuatro páginas carta (portada, aportación completa, estado/réplica pendiente y referencias), 245 920 bytes, dos referencias, sin desbordamientos ni citas pendientes; PDF promovido con SHA-256 `90b133897b1b5c25bc857769c8c48b928ed351980ae1d1020740d93246f68b33`. No se inventó una réplica: el foro de pregunta y respuesta oculta intervenciones hasta publicar la propia. El PDF no es evidencia de publicación ni de aceptación fuera del período evaluable.
