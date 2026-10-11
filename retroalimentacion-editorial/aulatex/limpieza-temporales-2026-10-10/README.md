# Limpieza de temporales - 10 de octubre de 2026

## Resultado

Se revisaron 660 archivos de `tmp`, `.tmp-itesca-20260928` y `.tmp-seminario` en la raiz.

- 537 archivos reubicados en notas de las materias correspondientes: 135,41 MiB.
- 31 archivos eliminados: 86,93 MiB. Solo caches y auxiliares regenerables, o duplicados con SHA256 identico a una copia existente fuera de los temporales.
- 92 archivos conservados: 4,04 MiB. Su atribucion no es segura o mantienen dependencias de scripts.

Las tres carpetas no se eliminaron completas: conservan los archivos pendientes. No se modificaron entregables ni se realizaron envios, commits o push en esta limpieza.

## Estrategia aplicada

Los materiales unicos atribuibles quedaron bajo `materiales-generales/historico-temporales-2026-10-10`, dentro de las notas de Plan de Negocios, Seminario I, Antecedentes de los Derechos Humanos, Calculo Integral, Biologia Celular, Derecho Mercantil y Macroeconomia. Se conserva la ruta original como estructura de procedencia; no se renombraron fuentes ni se sustituyeron versiones academicas vigentes.

Las capturas, borradores, extracciones y registros tecnicos se conservaron como historia de trabajo. No constituyen por si mismos bibliografia verificada ni evidencia de entrega. Los libros y documentos identicos a copias ya organizadas se eliminaron solo de los temporales.

Los scripts trasladados son archivos historicos, no herramientas listas para ejecutar. Algunos fijan rutas antiguas o realizan operaciones de envio: no ejecutarlos sin revisar y adaptar. Los controladores compartidos, `moodle_common.py` y los scripts con dependencias detectadas se conservaron en su ubicacion original.

La referencia al subtitulo utilizado en el foro de UCNL fue actualizada a su nueva ubicacion. No se altero el texto publicado ni el hash de la fuente.

## Auditoria y pendientes

[Manifiesto de ejecucion](manifiesto.json): cada archivo incluye origen, accion, motivo, destino cuando corresponde, tamano y SHA256. El valor `destino` en una eliminacion por duplicado identifica la copia conservada, no una nueva copia. [Plan previo](plan.json).

Se verificaron las 660 decisiones: existencia y SHA256 de destinos y archivos conservados, ausencia de origenes movidos y archivos eliminados. Para consultar pendientes, filtrar `accion = conservar` en el manifiesto. No se borro ningun archivo de atribucion incierta.

El analisis de dependencias es conservador y textual; no certifica la ejecucion de todos los scripts. Antes de publicar los historicos de navegador debe revisarse su contenido por posibles datos de sesion. Esta limpieza no autoriza redistribuir material docente ni informacion privada.