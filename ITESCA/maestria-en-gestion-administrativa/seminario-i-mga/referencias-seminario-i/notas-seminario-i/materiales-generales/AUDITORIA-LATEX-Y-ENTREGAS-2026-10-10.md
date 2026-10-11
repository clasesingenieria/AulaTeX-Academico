# Auditoria de LaTeX y Entregas

Consulta autenticada de solo lectura del 10 de octubre de 2026, mediante la boveda de AulaTeX. [Consignas, estados y hashes remotos](auditoria-entregables-2026-10-10.json). No se hicieron envios, sustituciones ni cambios a los documentos ya entregados.

## Hallazgos

1. Los PDF actuales de actividades 1, 2 y 3 no son los archivos enviados: difieren tanto por SHA256 como por texto normalizado NFKC. Se recuperaron los PDF exactos de Moodle en Entregas, sin sobrescribir los de la raiz. Compilar un TEX posterior no reproduce ni acredita el contenido evaluado anteriormente.
2. Actividad 2 exige documento elaborado en Word y exportado a PDF, Arial 11 o Times New Roman 12, doble espacio y formato APA. La fuente LaTeX usa Helvetica y genera siete paginas: la compilacion no acredita el requisito de herramienta/fuente ni la extension aproximada de 2-3 cuartillas. El PDF historico fue recibido y figura calificado; no implica aprobacion de la version local actual.
3. Actividad 4: PDF de dos paginas, portada e infografia; semestre `Por confirmar` y aviso de revision visibles. No esta certificado listo para entregar. Moodle muestra sin envios y simultaneamente Calificado: se registran ambos campos, sin inferir una entrega ni nota numerica.
4. Actividad 6 exige un solo DOCX con indice automatizado de Word. El PDF LaTeX de 25 paginas es complementario, no sustituto. Moodle muestra sin envios y Calificado; no equivale a entrega confirmada. Se conserva el DOCX preparado.
5. Actividad 10 exige el Word acumulativo de T8/T9 con objetivos. El DOCX revisado de Entregas coincide exactamente con el recuperado de Moodle; enviado para calificar, sin calificar. Reporte y presentacion LaTeX son auxiliares.
6. Las entradas genericas `reporte-seminario-i.tex` y `presentacion-seminario-i.tex` incluyen identidad grafica UnADM; el reporte ademas contiene marcadores pendientes. No son entregables ITESCA validos. No se modificaron ni se eliminaron en esta auditoria.

## Correspondencia de productos

| Fuente en la raiz | Compilacion actual | Papel frente al archivo oficial |
| --- | --- | --- |
| reporte-seminario-i-Actividad-1.tex | Correcta; PDF 9 paginas | Revision local posterior. PDF historico recuperado en Entregas, enviado y calificado. La consigna exige cuadro de 12 ideas y ensayo de 400-600 palabras; no se certifica cumplimiento semantico exhaustivo del reporte actual. |
| reporte-seminario-i-Actividad-2.tex | Correcta; PDF 7 paginas | Revision local posterior con discrepancias de formato indicadas; PDF enviado recuperado en Entregas. |
| reporte-seminario-i-Actividad-3.tex | Correcta; PDF 10 paginas | Revision local posterior, distinta del PDF enviado recuperado. La consigna exige formato docente, diez registros y sintesis de 500-800 palabras; requiere cotejo editorial antes de un eventual reemplazo. |
| reporte-seminario-i-Actividad-4.tex | Correcta; PDF 2 paginas | Candidato PDF local, con datos pendientes y sin envio registrado. |
| reporte-seminario-i-Actividad-6.tex | Correcta; PDF 25 paginas | Complemento del DOCX preparado; no entregable sustitutivo. |
| reporte-seminario-i-Actividad-10.tex | Correcta; PDF 12 paginas | Complemento del Word revisado confirmado en plataforma. |
| presentacion-seminario-i-Actividad-10.tex | Correcta; PDF 19 diapositivas | Complemento de T10; no sustituye el Word ni constituye por si sola entrega de exposicion final. |
| reporte-seminario-i-mga.tex | Correcta; PDF 6 paginas | Encuadre de materia, no tarea enviada. |
| presentacion-seminario-i-mga.tex | Plantilla base identificada; no recompilada en esta auditoria | Entrada reutilizable, no evidencia de una entrega especifica. |
| reporte-seminario-i-plantilla-actividad.tex | Plantilla contenedora usada por reportes | No compilar ni enviar como actividad independiente. |
| template.tex | Nucleo local usado en las compilaciones | Dependencia, no entregable. |
| reporte-seminario-i.tex y presentacion-seminario-i.tex | No certificados; entradas genericas | No enviar por identidad ajena y/o marcadores de relleno. |

Los ocho PDF compilados terminaron sin errores bloqueantes, citas indefinidas ni desbordamientos en los registros revisados. Esto no certifica APA completo, correspondencia literal con Word, cumplimiento de rubrica ni calificacion. T8 y T9 tienen Word en Entregas y evidencia historica de envio; no hay fuentes LaTeX de actividades 8 y 9 en la raiz. No se reconstruyeron ni se afirmo consulta actual de esos modulos o del registro del tema.

## Carpeta Entregas

Se normalizo la capitalizacion de la carpeta y las referencias locales. Los archivos existentes conservaron SHA256. Se agregaron solo copias exactas recuperadas de Moodle de los PDF de actividades 1-3. El archivo `~$rea8_DeLaCruzMunoz.docx` es un archivo temporal de bloqueo de Office, no un entregable; no se elimino para evitar interferir con un documento abierto. El Word y PDF antiguos de T10 se conservan, pero no son la version enviada confirmada del 4 de octubre.

Para la entrega T10 vigente, usar exclusivamente `Tarea10_DeLaCruzMunoz_Revision-2026-10-04.docx`; no reenviar sin autorizacion. Para T6, el candidato es `Tarea6_DeLaCruzMunoz.docx`, sujeto a revision personal y disponibilidad docente. No copiar automaticamente PDF locales posteriores sobre archivos recuperados.