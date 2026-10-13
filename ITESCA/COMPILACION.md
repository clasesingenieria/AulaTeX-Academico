# Compilacion global - ITESCA

Ejecutar siempre desde la raiz del proyecto.

## Carrera ISC

```powershell
.\aulaTEX\latexmk-build.ps1 .\ITESCA\ingenieria-en-sistemas-computacionales\reporte-itesca-isc.tex
.\aulaTEX\latexmk-build.ps1 .\ITESCA\ingenieria-en-sistemas-computacionales\presentacion-itesca-isc.tex
.\aulaTEX\latexmk-build.ps1 .\ITESCA\ingenieria-en-sistemas-computacionales\primer-ingreso\reporte-primer-ingreso.tex
.\aulaTEX\latexmk-build.ps1 .\ITESCA\ingenieria-en-sistemas-computacionales\primer-ingreso\reporte-primer-ingreso-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\ITESCA\ingenieria-en-sistemas-computacionales\primer-ingreso\presentacion-primer-ingreso.tex
```

## Carrera MGA

```powershell
.\aulaTEX\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\reporte-itesca-mga.tex
.\aulaTEX\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\presentacion-itesca-mga.tex
.\aulaTEX\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\primer-ingreso\reporte-primer-ingreso.tex
.\aulaTEX\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\primer-ingreso\reporte-primer-ingreso-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\primer-ingreso\presentacion-primer-ingreso.tex
```

## Contrato editorial

- Los contenedores de carrera y materia declaran metadatos institucionales.
- Los reportes heredan ficha editorial, matriz de cumplimiento, producto
  visible, transferencia profesional y lista de verificacion ITESCA.
- Las presentaciones heredan portada, narrativa, control de evidencia y cierre
  con consecuencia academica.
- Los archivos `_shared/` son plantillas maestras; los ejecutables canonicos son
  los `.tex` de carrera y materia listados arriba.
