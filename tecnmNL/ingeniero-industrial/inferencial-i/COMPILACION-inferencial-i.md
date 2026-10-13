# Compilación

Desde la raíz `C:\Users\delaCruz\Documents\AulaTeX-Academico`, ejecutar el script compartido `aulaTEX\latexmk-build.ps1` y pasar la ruta del archivo `.tex`.

Documento de la actividad:

`tecnmNL\ingeniero-industrial\inferencial-i\reporte-inferencial-i-Actividad-1.tex`

El script usa pdfLaTeX, ejecuta BibTeX cuando corresponde, guarda auxiliares en `.build\latex` y copia el PDF final junto al fuente. La plantilla depende de `aulaTEX/base\Plantilla-Informe` y de la configuración `.latexmkrc` de la raíz.
