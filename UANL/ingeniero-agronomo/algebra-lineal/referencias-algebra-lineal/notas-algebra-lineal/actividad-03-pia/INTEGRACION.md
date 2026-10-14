# Integracion del PIA en AulaTeX

Fecha: 2026-10-13.
Origen: `C:\Users\Sysx\Downloads\Paquete_Completo_PIA_Algebra_Lineal_Agronomia_UANL`.
Destino: `UANL/ingeniero-agronomo/algebra-lineal`.

## Organizacion

- El PIA se identifica como Actividad 3 por convencion interna. El Segundo Laboratorio ocupa la Actividad 2; la Actividad 1 se conserva.
- [Reporte editable](../../../reporte-algebra-lineal-Actividad-3.tex) y [PDF](../../../reporte-algebra-lineal-Actividad-3.pdf): documento academico integrado.
- [Ficha del video](../../../reporte-algebra-lineal-Actividad-3-video.tex): entrega independiente, aun incompleta.
- [Consigna](../../../planeaciones-algebra-lineal/consigna-Actividad-3.md): requisitos y rubrica; original docente en la subcarpeta originales-docentes.
- [Fuentes](../../fuentes-consultadas/actividad-03-pia/FUENTES.md): autoridades verificadas y limites de uso.
- [Inventario SHA-256](inventario-originales.csv): nueve originales archivados y comprobados byte por byte.
- [Paquete original](paquete-original): conserva las cuatro subcarpetas y sus nueve archivos sin modificarlos.

Los PDF y DOCX que el paquete llamaba finales permanecen en
`paquete-original/02_Entregables_Finales/` como antecedentes, no como entregas
canonicas AulaTeX. Los borradores, chat, HTML y scripts permanecen bajo notas;
no se ejecutaron sus scripts ni se transformaron los originales. La grafica
PNG original tambien se conserva alli; el reporte integrado contiene una
nueva grafica vectorial calculada en PGFPlots, sin la etiqueta de dosis optima.

## Ajustes editoriales y tecnicos

1. Se reemplazo la afirmacion de optimizacion por balance exacto: no existe
   funcion objetivo, precios ni restricciones economicas en el caso.
2. Se conservaron las tres formulas, metas y solucion del paquete, declaradas
   como supuestos didacticos, sin inventar muestreos, fichas ni diagnosticos.
3. Se verificaron mediante calculo independiente `det(A)=-8400` y los determinantes de Cramer
   `(-1680000,-2520000,-840000)`, con solucion `(200,300,100)` kg/ha.
4. Se distinguio la matriz entera de la decimal, cuyo determinante es `-0.0084`.
5. Se conservaron todos los pasos de Gauss-Jordan, Cramer y sustitucion.
6. Se corrigio el alcance agronomico: no negatividad no implica compatibilidad
   fisica ni seguridad ambiental; el balance no equivale a absorcion vegetal.
7. La pauta del paquete de aplicar A=200, B=50 y C=100 primero aporta
   `(49,58,59)` y deja `(50,25,25)` para despues. No aporta todo P y K en la
   primera aplicacion. El reporte lo expone como contraejemplo aritmetico,
   no como recomendacion de manejo.
8. Se mantuvo la plantilla Pizarror institucional, con un hook local para
   BibLaTeX APA 7/Biber. No se alteraron la plantilla compartida ni las
   entradas bibliograficas previas salvo agregar la URL verificada a Strang.
9. El PDF usa compresion de flujos y objetos; no se rasterizan ecuaciones.
   Las instrucciones de compilacion usan `-CleanMode none` para no borrar
   auxiliares historicos ajenos a esta integracion.

## Pendientes antes de entregar

- [ ] Completar nombres, matriculas y grupo en ambas fuentes; eliminar filas de integrantes que no correspondan.
- [ ] Incorporar evidencia de recoleccion de datos o confirmar con el docente la aceptacion del caso simulado.
- [ ] Confirmar que Gauss-Jordan fue visto en clase.
- [ ] Confirmar aceptacion de LaTeX como editor de ecuaciones y de la portada/maquetacion institucional; bibliografia APA 7 no equivale a formato APA integral.
- [ ] Grabar el video de hasta 20 minutos con todos los integrantes; no usar el guion como acordeon.
- [ ] Completar `\videourl` en la ficha y comprobar acceso publico y reproduccion sin suscripcion.
- [ ] Recompilar ambos archivos tras completar los datos y revisar la portada.
- [ ] Subir las evidencias por separado a Nexus. No se ha realizado ninguna carga.

## Guia de ensayo del video

Material de preparacion, no para leer durante la grabacion. Ajustar el reparto
al numero real de integrantes; todos se presentan con nombre, grupo y carrera.

| Tiempo orientativo | Contenido |
| --- | --- |
| 0-3 min | Presentaciones; problema; origen didactico o evidencia real de los datos; unidades e incognitas. |
| 3-6 min | Construir las tres ecuaciones y la matriz; justificar el metodo y los supuestos. |
| 6-13 min | Desarrollar las operaciones de Gauss-Jordan en orden, sin saltos ni partes previamente resueltas. |
| 13-17 min | Comprobar con sustitucion; explicar determinante y unicidad; Cramer si el tiempo permite mostrarlo completo. |
| 17-19 min | Interpretar kg/ha, no negatividad y limites; distinguir balance de optimizacion y recomendacion de campo. |

Usar pizarron legible, audio claro e imagen estable; aparecer de cintura hacia
arriba. No usar diapositivas ni rotafolio con el problema ya resuelto. Dejar
margen para no superar 20 minutos y probar el enlace antes de la entrega.