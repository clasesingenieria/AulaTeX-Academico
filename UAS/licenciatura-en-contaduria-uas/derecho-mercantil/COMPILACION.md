# Compilación

Desde la raíz del repositorio, con MiKTeX, Arial, XeLaTeX, Biber y latexmk disponibles:

```powershell
.\scripts\latexmk-build.ps1 UAS/licenciatura-en-contaduria-uas/derecho-mercantil/reporte-derecho-mercantil.tex -CleanMode none -xelatex
.\scripts\latexmk-build.ps1 UAS/licenciatura-en-contaduria-uas/derecho-mercantil/actividad-derecho-mercantil.tex -CleanMode none -xelatex
.\scripts\latexmk-build.ps1 UAS/licenciatura-en-contaduria-uas/derecho-mercantil/presentacion-derecho-mercantil.tex -CleanMode none -xelatex
```

Los tres ejemplos se compilaron el 22/09/2026. Los PDF quedan junto al TEX y los auxiliares en `.build/latex`. El adaptador local carga explícitamente la base institucional UAS; los logos se resuelven desde los assets de la materia. Los reportes usan APA mediante biblatex/Biber, no BibTeX.

Para una actividad nueva, definir título, datos confirmados y contenido antes de cargar el adaptador de materia. La portada usa fecha de realización, no vence ni incorpora identificadores técnicos del aula. Las fechas de ejemplo son dinámicas; fijarlas al generar una versión final.

La compilación sólo valida el documento técnico. No satisface por sí misma el requisito manuscrito de S1–S3, la extensión del ensayo ni acredita una entrega. Los PDF de muestra conservan campos por completar.

## Reporte de lectura S1

Punto de entrada de la actividad 1 (independiente de las plantillas y de los borradores anteriores):

```powershell
.\scripts\latexmk-build.ps1 UAS/licenciatura-en-contaduria-uas/derecho-mercantil/reporte-derecho-mercantil-Actividad-1.tex -CleanMode none -xelatex
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
