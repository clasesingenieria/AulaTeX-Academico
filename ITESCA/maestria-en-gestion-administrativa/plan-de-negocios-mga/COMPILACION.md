# Compilacion - Plan de Negocios

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\scripts\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\plan-de-negocios-mga\reporte-plan-de-negocios-mga.tex
.\scripts\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\plan-de-negocios-mga\presentacion-plan-de-negocios-mga.tex
```

Los reportes de actividades usan la plantilla institucional local y deben compilarse con XeLaTeX:

```powershell
.\scripts\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\plan-de-negocios-mga\reporte-plan-de-negocios-Actividad-1-Foro-Bienvenida.tex -xelatex
.\scripts\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\plan-de-negocios-mga\reporte-plan-de-negocios-Actividad-6-Imagen-Empresa.tex -xelatex
```

## Contrato de compilacion

La [numeración cronológica](ORDEN-ACTIVIDADES.md) distingue el número local del ID Moodle. Para recompilar todos los reportes de actividad existentes, incluidas las variantes conservadas:

```powershell
$materia = 'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga'
Get-ChildItem -LiteralPath $materia -Filter 'reporte-plan-de-negocios-Actividad-*.tex' -File | ForEach-Object {
	.\scripts\latexmk-build.ps1 $_.FullName -xelatex
	if ($LASTEXITCODE -ne 0) { throw "Error de compilación: $($_.Name)" }
}
```

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en plan-de-negocios.bib.
- Esta carpeta corresponde a la categoria LGAC gestion economica y financiera de las organizaciones.
- La identidad institucional se hereda desde `ITESCA/maestria-en-gestion-administrativa/reporte-itesca-mga.tex` y usa los recursos oficiales de `ITESCA/assets-itesca/web/`.
- `pdflatex` no puede compilar documentos que cargan `fontspec`; usar `-xelatex` o `-lualatex` según su preámbulo.
