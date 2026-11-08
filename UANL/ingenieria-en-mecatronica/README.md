# Ingeniería en Mecatrónica - UANL (Facultad de Ingeniería Mecánica y Eléctrica)

Este directorio contiene las plantillas canónicas, la configuración de compilación y las materias correspondientes al programa educativo de **Ingeniería en Mecatrónica** de la **Facultad de Ingeniería Mecánica y Eléctrica** en la Universidad Autónoma de Nuevo León.

## Entregables Canónicos
- **Reporte Técnico:** [`reporte-ingenieria-en-mecatronica.tex`](reporte-ingenieria-en-mecatronica.tex)
- **Defensa Oral Beamer:** [`presentacion-ingenieria-en-mecatronica.tex`](presentacion-ingenieria-en-mecatronica.tex)
- **Compilación:** wrapper común [`aulaTEX/latexmk-build.ps1`](../../aulaTEX/latexmk-build.ps1)

## Compilación Oficial
Desde la raíz del repositorio, los auxiliares se aíslan por documento en `.build/latex/`:

```powershell
# Compilar reporte
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingenieria-en-mecatronica\reporte-ingenieria-en-mecatronica.tex

# Compilar presentación
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingenieria-en-mecatronica\presentacion-ingenieria-en-mecatronica.tex
```
