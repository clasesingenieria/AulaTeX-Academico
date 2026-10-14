# Plan editorial fundacional - UANL

- Nodo: biologia-celular-fagro
- Nivel: institucion
- Padre: interinstitucional
- Modo: reforzar
- Destino: UANL
- Entrada futura del agente: UANL/maqueta.tex
- Ingesta textual: no
- Ingesta documental: no

## Objetivo editorial

- Consolidar un nodo institucional robusto para producir piezas académicas de alto rigor en la Universidad Autónoma de Nuevo León (UANL).
- Normalizar la suite de plantillas maestras (`reporte-uanl.tex`, `presentacion-uanl.tex`, `plantilla-actividad-uanl.tex`) bajo los contratos y estándares editoriales de AulaTeX.
- Dejar lista una arquitectura compilable y escalable para investigación, redacción y defensa oral síncrona sin rehacer estructura.
- Homogeneizar el nodo UANL con los estándares interinstitucionales (UnADM, UCNL, ITESCA) preservando la especificidad agronómica, técnica y científica de sus dependencias.

## Alcance

- Cubrir la estructura base de reportes técnicos, evidencias formativas y defensas en Beamer 16:9 con paleta institucional UANL.
- Garantizar compatibilidad técnica con `aulaTEX/latexmk-build.ps1`, `XeLaTeX`, `biber`, `natbib` y `bibliografia-uanl.bib`.
- Disponer de activos visuales y logotipos unificados en `UANL/assets-uanl/` y `aulaTEX/base/Plantilla-Informe/img/departamentos/`.
- Definir memoria operativa, plan y maqueta inicial verificada con compilación a PDF sin errores.

## Estructura base

- Portada institucional UANL con doble logotipo (UANL + Facultad/Dependencia).
- Resumen ejecutivo / Abstract y tabla de contenidos formal.
- Desarrollo temático con marco teórico, justificación y fundamentos científicos.
- Evidencia visual vectorial (cuadros en `booktabs` y diagramas en `TikZ`).
- Cierre con conclusiones argumentadas y transferencia profesional directa (agronómica, industrial o biotecnológica).
- Aparato crítico con referencias estandarizadas en APA 7ma edición.

## Criterios de evaluación

- Rigor conceptual y pertinencia técnica frente a los programas analíticos de la UANL.
- Trazabilidad y actualidad de las fuentes bibliográficas citadas.
- Coherencia argumentativa y estructura lógica sin relleno retórico.
- Cumplimiento técnico de formato LaTeX y compilación limpia a PDF con salida cero errores.

## Bibliografía requerida

- Normativa y planes de desarrollo institucional de la UANL (Ley Orgánica, Modelo Educativo, Visión 2030).
- Tratados y textos clásicos de referencia disciplinar (Alberts, Taiz, Nelson & Cox, Karp, Hernández-Sampieri).
- Repositorio bibliográfico centralizado en `bibliografia-uanl.bib`.

## Riesgos

- Inconsistencias cromáticas o tipográficas por el uso de fuentes no institucionales.
- Duplicación innecesaria de recursos o desalineación con las carpetas de asignaturas.
- Desconexión entre la evidencia académica y la transferencia profesional en el campo agronómico o ingenieril.
- Errores de compilación por rutas relativas mal resueltas; mitigado mediante unificación en `assets-uanl` y directivas `TEXINPUTS`.
