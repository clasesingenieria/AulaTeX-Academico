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
