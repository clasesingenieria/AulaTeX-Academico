# Contrato local: resena critica de video

## Identificacion y alcance

Fuente original cotejada: Lopez Martinez, A., Rojas Delgado, N. L., Alvarez Anaya, A. y Campos Hernandez, Y. I. (2023). 100 Tecnicas Didacticas de Ensenanza y Aprendizaje, fasciculo 2. UnADM. Seccion Resena, paginas impresas 185-195; ISBN 978-607-59731-2-8. Archivo original: referencias-aulatex/100tecnicasdidacticas Fasciculo 2 - Armando Lopez Martinez.pdf. La pagina 186 incluye expresamente libro, pelicula y documental; no establece otra tecnica independiente para video.

## Requisitos originales individualizados

Los cinco elementos esenciales de la pagina 187 se materializan en el producto, no solo en el reporte contenedor:

1. Ficha bibliografica: titulo completo, institucion, participante y fecha. Adaptacion audiovisual explicita: plataforma y formato en lugar de editorial/edicion; duracion 17:42 en lugar de numero de paginas. Lugar de produccion no acreditado: no inventarlo. El ejemplo de ficha de la pagina 188 es bibliografico, no una ficha audiovisual literal.
2. Titulo de la resena distinto al video: "Dignidad sin concesiones: del fundamento a la garantia".
3. Introduccion propia breve: identifica la leccion de Aliuska Duardo Sanchez y su enfoque, sin duplicar la introduccion externa.
4. Cuerpo: sintesis historica y conceptual, tres fundamentaciones, fortalezas y limites; separar datos, tesis de la profesora y valoraciones del resenista.
5. Conclusiones propias: recomendacion razonada de consulta con una limitacion concreta; no basta resumen ni postura sin razones.

Los ocho pasos de las paginas 190-191 se registran como: revision exploratoria (ficha del portal); observacion analitica (SRT del usuario y cotejo temporal, con visionado personal pendiente de confirmar); titulo distinto; autoria del resenista; ficha; introduccion; cuerpo con creditos; cierre valorativo. No afirmar dos visionados completos a partir de una transcripcion. La fuente permite ubicar la ficha segun preferencia del resenista. La caja no es obligacion del fasciculo: es materializacion local solicitada por el usuario.

Para una leccion expositiva, evaluar claridad, organizacion, precision y utilidad formativa; no importar criterios cinematograficos sobre planos o color sin evidencia ni pertinencia. No se identifica en esta seccion una rubrica numerica: la lista de cotejo siguiente es local, subordinada a la rubrica docente (7 puntos para la resena).

Tecnica 37, `resena`, familia `sintesis_lectura`, del catalogo de 100 tecnicas de AulaTeX. Producto: descripcion, sintesis y valoracion critica de una fuente audiovisual. No es foro ni reporte de investigacion.

Actividad local 2, semana 2; Moodle la denomina Actividad 1, modulo 211993. Mantener esta correspondencia al preparar el envio. Fuente principal: video de Canal UNED sobre concepto y fundamentacion de los derechos humanos; el SRT es auxiliar interno, no referencia bibliografica.

Referencia de implementacion: reporte de Seguridad Social, actividad 3, que distingue el reporte contenedor de una resena en `resenabox`. Adoptar su separacion conceptual y estilo institucional, no sus afirmaciones ni su extension. Este contrato es local y propuesto: no modifica el catalogo global ni representa una nueva exigencia docente.

## Estructura del reporte

1. Introduccion: problema de la fundamentacion y proteccion de derechos, pertinencia mexicana y criterio de lectura. Evitar repetir la ficha completa del video.
2. Desarrollo unico: titulo tematico "Dignidad, normas y proteccion efectiva". Subapartados: marco conceptual -> ficha audiovisual y resena enmarcada -> contraste juridico mexicano. El producto debe ocupar mas espacio que el marco y la interpretacion juntos.
3. Conclusiones: postura personal, razon y consecuencia profesional. No repetir literalmente el cierre de la resena. Declaracion de IA en nota al pie. Referencias aparte, sin convertirlas en un cuarto acto argumentativo.

## Materializacion del producto

- Usar `tcolorbox` con entorno semantico `resenabox`, inspirado en el estilo local de `forobox`, pero sin etiquetas de participacion, firma de foro, respuestas a companeros ni boton de publicacion.
- Caja divisible entre paginas, fondo claro, borde sobrio verde institucional, radio de 2 pt y texto seleccionable. No encerrar todo el desarrollo ni el reporte completo.
- Ficha audiovisual inmediatamente antes de la caja: titulo completo, institucion responsable, participante, publicacion, duracion, enlace y alcance. Presentarla como campos tipograficos compactos, sin otra caja dentro de `resenabox`.
- Dentro de la caja: titulo breve de la resena, sintesis historica y conceptual, las tres fundamentaciones efectivamente expuestas y valoracion critica con cierre. Usar parrafos y rotulos breves, no nuevas secciones de primer nivel.
- La resena debe poder leerse como pieza coherente: identifica su objeto y distingue lo expuesto de lo valorado. Evitar duplicar introduccion y conclusion completas dentro y fuera.
- Fuera de la caja, antes: definir brevemente dignidad, reconocimiento positivo y garantia con doctrina. Despues: interpretar articulo 1 y jurisprudencia con sus limites, sin convertir ese contraste en otra resena independiente.

## Fuentes y fidelidad

El video aborda fundamentaciones iusnaturalista, positivista y axiologica. Contractualismo y garantismo del cuadernillo pueden preparar o contrastar el producto, pero no atribuirse a la profesora como categorias expuestas en el video.

Toda afirmacion sustantiva debe tener soporte identificable. Mantener citas al video con tiempos; citar los libros por autoria o edicion real y los criterios judiciales por organo, identificador y registro. Las siete fuentes incorporadas deben conservar entrada BibTeX y referencia visible coherentes.

No exigir una cita textual solo por reutilizar el estilo de `forobox`: la consigna pide evitar copia literal. Preferir sintesis y parafrasis; no convertir errores del SRT en citas. El nombre de la participante se coteja con la ficha del portal, no con el reconocimiento automatico.

La consulta directa del Semanario estuvo bloqueada; los criterios se cotejaron en el Curso de derechos humanos de 2022. Documentar este limite y no afirmar que se recuperaron las fichas oficiales ni que se verifico su aplicabilidad actual exhaustiva.

## Extension y compuertas

- Portada AulaTeX, Arial 12, interlineado 1.5, margenes de 2.5 cm y texto justificado.
- Maximo tres paginas de contenido, incluyendo ficha, marco, caja, contraste y conclusiones; portada y referencias quedan fuera del conteo. No sumar tres paginas de resena a otras tres de reporte.
- Presupuesto orientativo: marco e introduccion 150-180 palabras; resena 400-500; contraste y cierre 180-220. Reducir duplicaciones si la compilacion excede el limite, no reducir Arial ni interlineado.
- Comprobar tres secciones principales, un `resenabox` con contenido sustantivo, ficha completa y siete referencias citadas. Verificar correspondencia de claves TEX/BibTeX.
- Compilar con `latexmk-build.ps1` y `-lualatex`; comprobar frescura del PDF, citas resueltas y ausencia de desbordamientos.
- Inspeccionar las tres paginas del cuerpo: caja legible, sin cortes de texto, encabezados huerfanos o paginas vacias. No forzar toda la caja a una pagina si perjudica la lectura.
- Ejecutar observacion contractual sobre el TEX exacto, sin confundir actividad local 2 con el modulo oficial del foro S2. La aprobacion automatica no reemplaza fidelidad audiovisual, rubrica docente ni revision personal.

## Secuencia propuesta

1. Reordenar el contenido ya sustentado sin ampliar su extension: doctrina al marco, sintesis y fundamentaciones a la caja, jurisprudencia al contraste.
2. Anadir ficha audiovisual compacta y `resenabox`; mantener la portada y las referencias.
3. Eliminar repeticiones y comprobar formato y paginas mediante compilacion inmediata.
4. Revisar visualmente y verificar citas, fidelidad y contrato local antes de actualizar el seguimiento.

## Resultado de aplicacion

Aplicado al reporte de actividad local 2. La ficha audiovisual precede a `resenabox`; dentro aparecen titulo propio, resenista, introduccion, sintesis con valoracion, tres fundamentaciones y conclusion con recomendacion y limite. Marco conceptual y contraste mexicano quedan fuera, como subsecciones del unico desarrollo. No se reutilizan obligaciones del foro.

Verificacion del 9 de octubre: LuaLaTeX compilado con Arial, margenes 2.5 cm e interlineado 1.5; cinco paginas totales (portada, tres de contenido, referencias). Las tres paginas de contenido fueron inspeccionadas visualmente: caja divisible sin recortes ni superposiciones; conclusion exterior en pagina propia. Registro sin desbordamientos, citas indefinidas ni errores de control. Siete fuentes citadas: video, cuadernillo, Constitucion, dos libros y dos jurisprudencias. La fuente de las 100 tecnicas se documenta en este contrato, no como fuente del contenido juridico de la resena.

Los metadatos, sintesis, teorias, contraste mexicano y conclusion personal solicitados por la planeacion estan materializados. No se asigna una calificacion docente ni se declara una nueva aprobacion global del motor: se verifica este contrato individual sobre el producto visible. Pendiente confirmar la observacion personal atenta y segunda observacion sugeridas por el fasciculo; el SRT no acredita esos actos. La presentacion de clase disponible no prueba haber visto una sesion grabada. Las jurisprudencias fueron cotejadas mediante doctrina; no se certifica su aplicabilidad actual exhaustiva.

Estado: contrato individual aplicado y maquetacion verificada; requiere revision personal antes de entrega. No se autoriza ni realiza envio.