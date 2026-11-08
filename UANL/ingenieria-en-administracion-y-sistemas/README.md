# Ingeniería en Administración y Sistemas - UANL (Facultad de Ingeniería Mecánica y Eléctrica)

Este directorio contiene las plantillas canónicas, la configuración de compilación y las materias correspondientes al programa educativo de **Ingeniería en Administración y Sistemas** de la **Facultad de Ingeniería Mecánica y Eléctrica** en la Universidad Autónoma de Nuevo León.

## Entregables Canónicos
- **Reporte Técnico:** [`reporte-ingenieria-en-administracion-y-sistemas.tex`](reporte-ingenieria-en-administracion-y-sistemas.tex)
- **Defensa Oral Beamer:** [`presentacion-ingenieria-en-administracion-y-sistemas.tex`](presentacion-ingenieria-en-administracion-y-sistemas.tex)
- **Compilación:** wrapper común [`aulaTEX/latexmk-build.ps1`](../../aulaTEX/latexmk-build.ps1)

## Compilación Oficial
Desde la raíz del repositorio, los auxiliares se aíslan por documento en `.build/latex/`:

```powershell
# Compilar reporte
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingenieria-en-administracion-y-sistemas\reporte-ingenieria-en-administracion-y-sistemas.tex

# Compilar presentación
powershell -ExecutionPolicy Bypass -File .\aulaTEX\latexmk-build.ps1 .\UANL\ingenieria-en-administracion-y-sistemas\presentacion-ingenieria-en-administracion-y-sistemas.tex
```
