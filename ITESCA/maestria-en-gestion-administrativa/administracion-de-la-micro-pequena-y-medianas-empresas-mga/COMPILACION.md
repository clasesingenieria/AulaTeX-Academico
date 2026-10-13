# Compilacion - Administracion de la Micro, Pequena y Medianas Empresas

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\administracion-de-la-micro-pequena-y-medianas-empresas-mga\\reporte-administracion-de-la-micro-pequena-y-medianas-empresas-mga.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\administracion-de-la-micro-pequena-y-medianas-empresas-mga\\presentacion-administracion-de-la-micro-pequena-y-medianas-empresas-mga.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en administracion-de-la-micro-pequena-y-medianas-empresas.bib.
- Esta carpeta corresponde a la categoria LGAC gestion e innovacion de las organizaciones.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.

## Checklist editorial

- Usar la bibliografia local para fuentes sobre MIPYMES, emprendimiento,
  competitividad y politica publica.
- Conectar cada producto con diagnostico empresarial, evidencia y decision.
- Cuando se trabaje un caso, incluir contexto, problema, indicadores, decision y mejora.
- Evitar definiciones sueltas: cada concepto debe explicar funcion, limite o consecuencia.
- La carpeta `referencias-administracion-de-la-micro-pequena-y-medianas-empresas/`
  resguarda fuentes oficiales, notas y evidencia auxiliar.
