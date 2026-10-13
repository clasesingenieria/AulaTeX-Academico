# Compilacion - Primer ingreso

Ejecutar siempre desde la raiz del proyecto:

```powershell
.\aulaTEX\latexmk-build.ps1 .\ITESCA\ingenieria-en-sistemas-computacionales\primer-ingreso\reporte-primer-ingreso.tex
.\aulaTEX\latexmk-build.ps1 .\ITESCA\ingenieria-en-sistemas-computacionales\primer-ingreso\reporte-primer-ingreso-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\ITESCA\ingenieria-en-sistemas-computacionales\primer-ingreso\presentacion-primer-ingreso.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo `.tex`.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en `primer-ingreso.bib`.
- Esta materia es la base para extender la estructura academica de ITESCA.
- La identidad institucional se hereda desde `ITESCA/_shared/` y usa los assets
	oficiales descargados en `ITESCA/assets-itesca/web/`.