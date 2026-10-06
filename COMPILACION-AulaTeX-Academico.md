# Compilacion - Aulatex Academico

Distribucion oficial en Windows: **TeX Live 2026**, instalada en
`C:\texlive\2026`, con el esquema `scheme-full` y `latexmk`.
El script `scripts/latexmk-build.ps1` (tambien usado por las recetas de
LaTeX Workshop) selecciona esta instalacion explicitamente y antepone sus
binarios al `PATH` para usar los motores y la bibliografia de la misma
distribucion. No cambia automaticamente a MiKTeX ni a TeX Live 2025.
El compilador Python `compile_contract_tex` usa la misma distribucion por
defecto; conserva su parametro `latexmk` para pruebas con otra ruta explicita.
Linux conserva su seleccion de herramientas mediante `PATH`.

Comandos desde la raiz del repositorio:

```powershell
.\scripts\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\AulaTeX-Academico\reporte-AulaTeX-Academico.tex
.\scripts\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\AulaTeX-Academico\reporte-AulaTeX-Academico-Actividad-1.tex
.\scripts\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\AulaTeX-Academico\presentacion-AulaTeX-Academico.tex
```

Validaciones:

- `\input{template}` debe resolver a la plantilla compartida.
- El archivo `.bib` local debe contener toda fuente citada.
- La salida final debe conservar portada institucional UnADM, desarrollo,
  producto solicitado, conclusion y bibliografia.
