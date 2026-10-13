# Compilacion - Primer ingreso MGA

Ejecutar siempre desde la raiz del proyecto:

```powershell
.\aulaTEX\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\primer-ingreso-mga\reporte-primer-ingreso-mga.tex
.\aulaTEX\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\primer-ingreso-mga\reporte-primer-ingreso-mga-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\primer-ingreso-mga\reporte-primer-ingreso-mga-Actividad-2.tex
.\aulaTEX\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\primer-ingreso-mga\presentacion-primer-ingreso-mga.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo `.tex`.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en `primer-ingreso-mga.bib`.
- `primer-ingreso-mga` es materia semilla no curricular; sirve como induccion
  academica para productos de ingreso, diagnostico y nivelacion de posgrado.
- La identidad institucional se hereda desde `ITESCA/_shared/` y usa los assets
	oficiales descargados en `ITESCA/assets-itesca/web/`.

## Checklist editorial

- Los metadatos deben declarar actividad, periodo, modalidad y producto.
- Cada actividad debe convertir la consigna en problema, evidencia y cierre.
- Si se usa cuestionario, cada respuesta debe incluir justificacion o procedimiento.
- Toda cita o fuente institucional debe existir en `primer-ingreso-mga.bib`.
- La carpeta `referencias-primer-ingreso-mga/` resguarda notas, fuentes y
  evidencia auxiliar de la materia.
