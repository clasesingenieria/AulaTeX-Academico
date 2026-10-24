# Álgebra Lineal — Ingeniero Agrónomo

## Evidencia vigente 2.6: revision del 20 de octubre de 2026

La evidencia **2.6**, mapa cognitivo de algoritmo de un problema de sistemas
lineales, es individual, vale 10 puntos y cierra el **23 de octubre de 2026
a las 23:42**, segun Nexus. Esta clave institucional no debe confundirse con
la numeracion interna de los trabajos anteriores.

Se verifico el acceso con AulaTeX y se descargaron la guia EV2 y la metodologia.
El [contrato y recursos verificados](planeaciones-algebra-lineal/consigna-Evidencia-2-6.md)
recogen la rubrica vigente. La consigna exige desarrollo individual **a mano**
y mapa escaneado, con procedimiento y ejemplo matematico enlazados por flechas.

El [reporte digital con mapa](reporte-algebra-lineal-Evidencia-2-6.pdf) y su
[fuente editable](reporte-algebra-lineal-Evidencia-2-6.tex) están preparados
con plantilla AulaTeX, referencias APA, Gauss-Jordan, independencia lineal,
comprobación por Cramer y sustitución. El mapa ocupa una página horizontal.
El caso provisional N-P-K fue sustituido por el **Sistema 11** de la hoja
docente aportada el 22 de octubre. Solución exacta: `(-103,-74,-379)/335`.
El sistema fue cotejado con la primera página; no tiene unidades físicas.

Los recursos de Nexus están en las
[notas de esta evidencia](referencias-algebra-lineal/notas-algebra-lineal/evidencia-2-6/CONTROL.md),
con originales e inventario SHA-256. No se citan como autoridad matemática.
Por instrucción del usuario, **manuscrito, escaneo y envío serán manuales**.
No se ha enviado esta evidencia ni se ha presentado el PDF digital como un
manuscrito. El archivo que finalmente se seleccione para entregar corresponde
a `entregas-algebra-lineal`.

La hoja docente indica vencimiento el 16 de octubre; Nexus mostraba cierre
el 23 de octubre a las 23:42 en la consulta del 20 de octubre. Confirmar esta
discrepancia con el profesor: no se declara una prórroga ni aceptación garantizada.

## Actividad 1: mapa cognitivo

- **Actividad 1 / Fase 1:** mapa cognitivo de telaraña sobre aplicaciones del álgebra lineal en la vida cotidiana.
- Fuente de la consigna: [guía docente](planeaciones-algebra-lineal/originales-docentes/guia-Actividad-1-mapa-cognitivo.ppsx).
- Entregable: `reporte-algebra-lineal-Actividad-1.pdf`.
- Modalidad indicada: equipo de 2 a 3 personas.
- Medio de entrega indicado: Nexus.
- Valor informado por la guía: 10 puntos.

## Ejecución con AulaTeX

Desde la raíz del repositorio:

```powershell
.\aulaTEX\aulatex.ps1 agent --target .\UANL\ingeniero-agronomo\algebra-lineal --level materia --action realizar-actividad --activity 1 --run-extractor
```

Para el motor inteligente con monitor:

```powershell
.\aulaTEX\aulatex.ps1 monitor-inteligente -Target '.\UANL\ingeniero-agronomo\algebra-lineal' -Activity 1 -Actions realizar-actividad -MaxTargets 1 -Engines 'Auto (model-router)' -Backend langgraph -Console
```

Los nombres de estudiantes, matrículas, grupo, docente y fechas deben completarse antes de la entrega.

## Actividad 2: Segundo Laboratorio

El Segundo Laboratorio es una actividad de la materia, no material general.
Su [reporte PDF](reporte-algebra-lineal-Actividad-2.pdf) y
[fuente LaTeX](reporte-algebra-lineal-Actividad-2.tex) están en la raíz.
Se conserva el periodo original **enero-junio de 2025 (EJ25)** y el contenido
de la solución existente; no se le atribuye la fecha de entrega del PIA.

- [Consigna](planeaciones-algebra-lineal/consigna-Actividad-2.md) y [original docente](planeaciones-algebra-lineal/originales-docentes/actividad-02-segundo-laboratorio/segundo-laboratorio-ej25.pdf).
- [Notas y archivos asociados](referencias-algebra-lineal/notas-algebra-lineal/actividad-02-segundo-laboratorio/INTEGRACION.md): DOCX previo y auxiliares conservados.
- Equipo de hasta tres integrantes; entrega el día del segundo examen parcial, según el original.

## Actividad 3: Producto Integrador de Aprendizaje

El PIA se registra como **Actividad 3 interna de AulaTeX**, después del laboratorio,
sin cambiar el nombre institucional de la evidencia. Corresponde al
semestre agosto-diciembre de 2026; fecha límite: **11 de noviembre de 2026**;
equipo de hasta cuatro integrantes.

- [Reporte PDF](reporte-algebra-lineal-Actividad-3.pdf) y [fuente LaTeX](reporte-algebra-lineal-Actividad-3.tex).
- [Ficha PDF del video](reporte-algebra-lineal-Actividad-3-video.pdf) y [fuente editable](reporte-algebra-lineal-Actividad-3-video.tex): pendiente de URL e integrantes, no entregar todavía.
- [Consigna y rúbrica](planeaciones-algebra-lineal/consigna-Actividad-3.md) y [PDF institucional original](planeaciones-algebra-lineal/originales-docentes/consigna-PIA-algebra-lineal-2026.pdf).
- [Fuentes verificadas y alcance](referencias-algebra-lineal/fuentes-consultadas/actividad-03-pia/FUENTES.md).
- [Notas de integración, originales y pendientes](referencias-algebra-lineal/notas-algebra-lineal/actividad-03-pia/INTEGRACION.md).
- [Compilación](COMPILACION-algebra-lineal.md).

El reporte usa la plantilla institucional y bibliografía APA 7 mediante un
adaptador local BibLaTeX/Biber, sin modificar la plantilla común. Los datos de
fertilización se declaran didácticos: el paquete no acredita un diagnóstico de
campo ni fichas comerciales de las tres fórmulas. Antes de entregar, incorporar
datos verificables o confirmar con el docente que acepta el caso simulado;
completar integrantes, matrículas y grupo; confirmar el método visto en clase y
la aceptación de LaTeX; grabar y comprobar el video público. No se ha enviado
ningún archivo a Nexus.

## Organización de la materia

La raíz conserva los reportes canónicos TEX/PDF, la bibliografía y los índices.
Las consignas y los originales docentes están en `planeaciones-algebra-lineal`;
las fuentes consultadas en `referencias-algebra-lineal/fuentes-consultadas`;
las notas, borradores y antecedentes en
`referencias-algebra-lineal/notas-algebra-lineal`, agrupados por actividad.
Los registros de movimientos conservan las rutas históricas como trazabilidad,
no como rutas vigentes de entrega. Los archivos originales del paquete del PIA
mantienen sus nombres y contenido dentro de las notas de la Actividad 3.
