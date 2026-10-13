# Compilacion - Derecho a la Seguridad Social

Comandos desde la raiz del repositorio:

```powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-a-la-seguridad-social-lde\reporte-derecho-a-la-seguridad-social.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-a-la-seguridad-social-lde\reporte-derecho-a-la-seguridad-social-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-a-la-seguridad-social-lde\presentacion-derecho-a-la-seguridad-social.tex
```

Validaciones:

- `\input{template}` debe resolver a la plantilla compartida.
- El archivo `.bib` local debe contener toda fuente citada.
- La salida final debe conservar portada institucional UnADM, desarrollo,
  producto solicitado, conclusion y bibliografia.
- Fuente consolidada: `referencias-derecho-a-la-seguridad-social/nota-bienvenida-derecho-a-la-seguridad-social.md`.
- Memoria local: `.memoria-aulatex/memoria-bienvenida-derecho-a-la-seguridad-social.json`.
- Memoria de unificación editorial: `.memoria-aulatex/memoria-unificacion-garantias-seguridad-social.json`.
- Los artefactos de los 11 ciclos iniciales y de los 100 ciclos de unificación del motor inteligente quedan en `.aulatex-temp/intelligent-engine/` y pueden eliminarse.
