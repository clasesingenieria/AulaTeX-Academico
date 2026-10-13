# Plan editorial fundacional

- Nodo: IIIEPE
- Nivel: institucion
- Padre: interinstitucional
- Modo: reforzar
- Destino: IIIEPE
- Entrada futura del agente: IIIEPE/maqueta.tex
- Ingesta textual: no
- Ingesta documental: no

## Objetivo editorial

- Consolidar una base editorial IIIEPE uniforme, escalable y compatible con el flujo AulaTeX.
- Preparar documentos institucionales reutilizables para que el Agente investigue, redacte, evalúe y compile después.
- Reducir variabilidad entre materias mediante contratos de estructura, bibliografía y compilación.
- Normalizar propuesta de IIIEPE.
- Reforzar la base editorial IIIEPE con contrato estable, reusable y compilable.
- Dejar lista una maqueta institucional para investigación y redacción posterior por el Agente.
- Reducir variabilidad entre materias mediante reglas comunes de estructura y calidad.
- Reforzar una base editorial IIIEPE uniforme, escalable y compatible con el flujo AulaTeX.
- Dejar preparada una maqueta institucional para que el Agente investigue, redacte, evalúe y compile después.
- Reducir variabilidad entre materias mediante reglas comunes de estructura, bibliografía, evaluación y compilación.
- Preservar contratos existentes sin regresión de nombres, rutas ni artefactos canónicos.

## Alcance

- Reforzar memoria, plan y maqueta institucional sin redactar contenidos completos de asignaturas.
- Preparar artefactos reutilizables para reporte, actividad y presentación.
- Reforzar memoria, plan editorial y maqueta institucional sin redactar actividades completas.
- Preparar artefactos base para reporte, actividad, presentación y bibliografía.
- Orientar la organización por programa o carrera, materia y entregable.
- Dejar marcadores de investigación donde falten fuentes, criterios o datos oficiales.
- No ejecutar investigación profunda ni validar contenido externo en esta fase.
- Actualizar memoria fundacional, plan y maqueta inicial sin redactar actividades completas.
- Cubrir entradas canónicas institucionales y patrón de réplica por materia.
- Incluir marcadores [INV] para vacíos documentales y curriculares.
- Actualizar memoria fundacional, plan editorial y maqueta inicial sin redactar actividades completas.
- Cubrir entradas canónicas institucionales: reporte, actividad, presentación y bibliografía.
- Orientar réplica por programa, carrera, materia y entregable.
- Incluir marcadores [INV] para vacíos documentales, curriculares, normativos y bibliográficos.

## Estructura base

- Raíz IIIEPE con archivos canónicos institucionales y bibliografía central.
- Subestructura por carrera/programa > materia > entregables.
- Carpeta assets y referencias a plantillas compartidas en aulaTEX/base/.
- IIIEPE/reporte-iiiepe.tex como entrada institucional para reportes generales.
- IIIEPE/presentacion-iiiepe.tex como entrada institucional para presentaciones.
- IIIEPE/bibliografia-iiiepe.bib como bibliografía central verificable.
- IIIEPE/assets/ para recursos institucionales normalizados.
- IIIEPE/<programa-o-carrera>/<materia>/ para contenidos específicos.
- Cada materia con reporte-<materia>.tex, actividad-<materia>.tex opcional, bibliografia local opcional y COMPILACION.md.
- Uso de aulaTEX/base/ para plantillas compartidas mediante rutas resueltas por TEXINPUTS.
- IIIEPE/reporte-iiiepe.tex
- IIIEPE/presentacion-iiiepe.tex
- IIIEPE/bibliografia-iiiepe.bib
- IIIEPE/assets/
- IIIEPE/<programa-o-carrera>/<materia>/ con reporte, actividad opcional, .bib opcional y COMPILACION.md
- Cada materia debe contener reporte-<materia>.tex, actividad-<materia>.tex si aplica, bibliografía local opcional y COMPILACION.md.
- Las plantillas compartidas deben invocarse desde aulaTEX/base/ mediante rutas resueltas por TEXINPUTS.

## Criterios de evaluación

- Homogeneidad formal entre materias y documentos institucionales.
- Compilación reproducible con scripts oficiales.
- Cobertura de objetivos, competencias, evidencias y rúbrica básica.
- Trazabilidad de fuentes y ausencia de bibliografía no verificable.
- Homogeneidad formal entre documentos institucionales y de materia.
- Compilación reproducible con scripts oficiales de AulaTeX.
- Presencia de objetivo, competencias, resultados, evidencias, rúbrica y referencias.
- Claridad de instrucciones para el estudiante y de criterios para el docente.
- Trazabilidad de fuentes y ausencia de bibliografía inventada.
- Separación efectiva entre maqueta editorial, contenido investigado y redacción final.
- Compatibilidad con crecimiento futuro sin regresión de archivos existentes.
- Revisar estructura y consistencia antes de pasar al Agente.
- Consistencia formal entre documentos institucionales y de materia.
- Presencia explícita de objetivos, evidencias y rúbrica breve.
- Trazabilidad bibliográfica sin referencias inventadas.
- Consistencia formal entre documentos institucionales y documentos de materia.
- Presencia explícita de objetivos, competencias, resultados, evidencias, rúbrica y referencias.
- Claridad de instrucciones para el estudiante y criterios de revisión para el docente.
- Compatibilidad con crecimiento futuro sin romper archivos existentes.

## Bibliografía requerida

- Lineamientos oficiales IIIEPE (si disponibles).
- Programas analíticos o sílabos por materia.
- Fuentes académicas primarias/secundarias validadas para cada curso.
- Lineamientos oficiales IIIEPE disponibles y verificables.
- Programas analíticos, sílabos o mapas curriculares por materia.
- Bibliografía oficial indicada por cada asignatura.
- Fuentes académicas primarias o secundarias validadas por el curso.
- Normas de citación adoptadas por el proyecto o por la institución.
- Documentos internos de evaluación, si existen y pueden citarse.
- Lineamientos oficiales IIIEPE verificables.
- Programas analíticos/sílabos/mapas curriculares por materia.
- Bibliografía oficial de asignatura y normas de citación vigentes.
- Documentos internos de evaluación, si existen y son citables.
- Lineamientos oficiales IIIEPE verificables, si existen.
- Fuentes académicas primarias o secundarias validadas por docente o programa.
- Documentos internos de evaluación solo si son accesibles, citables y autorizados.

## Riesgos

- Heterogeneidad de formatos heredados entre materias.
- Falta de lineamientos institucionales explícitos documentados.
- Dependencia de fuentes no normalizadas o no citables.
- Ausencia de lineamientos institucionales explícitos o accesibles.
- Uso de fuentes no verificables, incompletas o no citables.
- Duplicación de plantillas locales que dificulte mantenimiento.
- Rutas duras que rompan compilación fuera del entorno del autor.
- Confusión entre marcadores editoriales y contenido académico definitivo.
- Cambios de nomenclatura institucional no validados.
- La propuesta requiere estructuración adicional.
- Heterogeneidad de formatos heredados.
- Ausencia o baja disponibilidad de lineamientos institucionales.
- Duplicación de plantillas locales y rutas duras.
- Confusión entre placeholders editoriales y contenido final.
- Ausencia o baja disponibilidad de lineamientos institucionales explícitos.
- Confusión entre placeholders editoriales y contenido académico definitivo.

## Fase siguiente del agente

- Levantar inventario real de carpetas y .tex existentes en IIIEPE.
- Mapear brechas contra estructura canónica y proponer migración mínima sin regresión.
- Generar esqueletos por materia con marcadores de investigación y rúbricas base.
- Validar compilación de al menos un reporte y una presentación institucional.
- Levantar inventario real de carpetas, archivos .tex, .bib, assets y COMPILACION.md en IIIEPE.
- Comparar la estructura existente contra el contrato canónico y proponer migración mínima sin regresión.
- Investigar datos institucionales oficiales y oferta académica vigente.
- Crear o normalizar esqueletos por materia con marcadores [INV] y rúbricas base.
- Validar compilación de al menos un reporte institucional y una presentación institucional.
- Validar que cada materia tenga comando de compilación documentado.
- Completar bibliografía solo con fuentes verificadas.
- Investigar y completar lagunas detectadas.
- Inventariar estructura real IIIEPE y detectar brechas contra contrato canónico.
- Normalizar esqueletos por materia sin renombrar artefactos ya estables.
- Validar compilación de reporte-iiiepe.tex y presentacion-iiiepe.tex.
- Completar bibliografía únicamente con fuentes verificadas.
- Inventariar estructura real de IIIEPE: carpetas, .tex, .bib, assets y COMPILACION.md.
- Normalizar esqueletos por materia con marcadores [INV] y rúbricas base.
- Verificar que cada materia tenga comando de compilación documentado.
