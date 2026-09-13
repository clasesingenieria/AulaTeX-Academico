# Compilación — Investigación aplicada a la contaduría

## Productos pendientes y foros: Linux

Desde la raíz del repositorio:

```bash
bash UAS/licenciatura-en-contaduria-uas/investigacion-aplicada-a-la-contaduria/compilar-pendientes.sh
```

El script compila S2, S3, S4, la ponencia y los cuatro foros con **LuaLaTeX y Biber**. Requiere Arial instalada, TeX Live con `biblatex-apa`, `latexmk` y las herramientas Poppler `pdfinfo`, `pdffonts` y `pdfdetach`. Copia los ocho PDF junto a sus fuentes; deja los auxiliares en `.build/pendientes`. No recompila ni altera la entrega S1 ya calificada.

Verifica límite de 2 000 000 bytes, presencia de Arial, ausencia de citas indefinidas y desbordamientos, dos adjuntos por foro e identidad de cada adjunto con el TXT original. No acredita entregas, aceptación tardía, participación en foros ni cumplimiento de lecciones aún no consultadas.

Los productos usan [plantillas/uas-base.tex](plantillas/uas-base.tex). Para nuevas actividades se puede redefinir `\fechaRealizacion` después de cargar la base; no utilizar una fecha dinámica en un entregable ya revisado. La ponencia conserva portada propia para cinco integrantes.

La [plantilla ForoBox](plantillas/plantilla-forobox-uas.tex) compila sin TXT mediante marcadores explícitos; al completarla deben crearse los dos textos o adaptarse sus nombres. Los reportes S2–S4 incluyen directamente los TXT como contenido de sus cajas para evitar divergencias. El reporte S1 conserva su composición previa; sus adjuntos se verifican por separado. Los textos usados mediante `\input` deben evitar caracteres reservados de LaTeX sin tratamiento adecuado.

Para comprobar la plantilla desde la carpeta de la asignatura:

```bash
latexmk -norc -lualatex -interaction=nonstopmode -halt-on-error -outdir=.build/pendientes plantillas/plantilla-forobox-uas.tex
```

## Plantillas históricas: PowerShell

Ejecutar desde la raíz de `AulaTeX-Academico`:

```powershell
.\scripts\latexmk-build.ps1 .\UAS\assets\marca-uas-provisional.tex
.\scripts\latexmk-build.ps1 .\UAS\licenciatura-en-contaduria-uas\investigacion-aplicada-a-la-contaduria\reporte-investigacion-aplicada-a-la-contaduria.tex
.\scripts\latexmk-build.ps1 .\UAS\licenciatura-en-contaduria-uas\investigacion-aplicada-a-la-contaduria\reporte-investigacion-aplicada-a-la-contaduria-Actividad-1.tex
.\scripts\latexmk-build.ps1 .\UAS\licenciatura-en-contaduria-uas\investigacion-aplicada-a-la-contaduria\actividad-investigacion-aplicada-a-la-contaduria.tex
.\scripts\latexmk-build.ps1 .\UAS\licenciatura-en-contaduria-uas\investigacion-aplicada-a-la-contaduria\presentacion-investigacion-aplicada-a-la-contaduria.tex
```

## Contrato

- Al script se entrega únicamente la ruta del `.tex`.
- `\input{template}` se resuelve desde `base/Plantilla-Informe` mediante `TEXINPUTS`.
- La bibliografía se declara como `\bibliography{investigacion-aplicada-a-la-contaduria}` y se resuelve mediante `BIBINPUTS`.
- El PDF final se copia junto al `.tex`; los auxiliares quedan en `.build/latex`.
- La marca provisional debe compilarse antes del reporte y la presentación.
- Antes de entregar, sustituir todos los textos `[POR COMPLETAR]`, confirmar metadatos y comprobar que cada cita tenga una entrada real en el `.bib`.
