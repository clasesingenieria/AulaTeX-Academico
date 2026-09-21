# Ejecucion de actividades - Plan de Negocios

**Estado de esta carpeta: módulos 6545 (NexoTeX), 6546, 6547, 6548 y 6549 (AM Taller) generados y exportados; pendientes de revisión editorial. Nueve módulos del lote original no se ejecutaron mediante este ejecutor.**

Se solicito ejecutar `realizar-actividad` para las 14 [planeaciones del lote original](../../../planeaciones-generadas/2026-II/revision-2026-09-20/README.md). El primer intento del modulo 6545 recibio HTTP 401 de `Auto (model-router)`. Tras el cambio de configuracion del usuario, se verifico el motor **GPT-5.6-SOL**, deployment **gpt-5.6-sol**, con una solicitud breve exitosa. El ejecutor ya no fuerza el motor anterior: respeta la seleccion vigente y la restriccion global cuando corresponda.

El reintento completo supero sus tres etapas de `AulaTeXAgent` y materializo el TEX. Se aplico la plantilla local y se exportaron los siguientes borradores:

- [Word del piloto 6545](reporte-plan-de-negocios-Actividad-6545.docx): formato solicitado por la consigna; caso hipotetico por confirmar.
- [PDF de revision, cinco paginas](reporte-plan-de-negocios-Actividad-6545.pdf): no sustituye el Word solicitado.
- [Fuente TEX](reporte-plan-de-negocios-Actividad-6545.tex): conserva la salida generada con la plantilla institucional aplicada.

La autenticacion y la exportacion estan verificadas, no la aprobacion academica. El texto todavia incluye diagnosticos de etapas y metadiscurso operativo que deben depurarse antes de una entrega. No se inventaron resultados de campo ni se publico el documento en Moodle.

La revisión posterior eligió AM Taller Autocentro como caso de referencia documentado. Se generaron los siguientes borradores adicionales:

- La variante AM Taller del modulo 6545 compilo con XeLaTeX, pero se retiro de esta carpeta durante cambios paralelos. No se recrea; el 6545 de esta carpeta conserva NexoTeX. Consultar los reportes canonicos de la materia antes de reutilizarlo.
- [Mercadotecnia y publicidad](reporte-plan-de-negocios-Actividad-6546.docx), con [PDF de revisión](reporte-plan-de-negocios-Actividad-6546.pdf). No afirma precios, stock, clientes, demanda ni catálogo vendible.
- [Área geográfica de impacto](reporte-plan-de-negocios-Actividad-6547.docx), con [PDF de revisión](reporte-plan-de-negocios-Actividad-6547.pdf). No asigna territorio, mercado potencial ni mercado meta sin estadística y trabajo de campo.
- [Preguntas para demanda y oferta](reporte-plan-de-negocios-Actividad-6548.docx), con [PDF de revisión](reporte-plan-de-negocios-Actividad-6548.pdf). Contiene instrumentos de recolección; no contiene respuestas, muestras ni resultados de campo.
- [Resultados de investigación de mercados](reporte-plan-de-negocios-Actividad-6549.docx), con [PDF de revisión](reporte-plan-de-negocios-Actividad-6549.pdf). Define cómo registrar y analizar resultados reales; no contiene encuesta aplicada, porcentajes ni competidores ficticios.

## Preparacion validada

- [Formato ITESCA adaptado](formato-itesca-plan-negocios.tex): Arial 12, carta, interlineado 1.5, portada con logo oficial y referencias APA 7 cuando procedan.
- Se revisaron el [ejemplo de Actividad 6](../../../../fundamentos-de-gestion-administrativa-mga/reporte-fundamentos-de-gestion-administrativa-Actividad-6.tex), su [formato local](../../../../fundamentos-de-gestion-administrativa-mga/formato-itesca-actividad-6.tex) y la [base reutilizable](../../../../fundamentos-de-gestion-administrativa-mga/reporte-fundamentos-de-gestion-administrativa-plantilla-actividad.tex). No se copiaron materia, codigo GGFG02, fechas, pesos ni contenidos de esos productos.
- La [prueba minima de plantilla](../../../../../../.aulatex-temp/realizar-plan-negocios-2026-09-20/prueba-plantilla.pdf) compilo en dos paginas con XeLaTeX. Portada y contenido se revisaron visualmente. Se resolvio una incompatibilidad local de pies de figura cargando `caption`.
- [Caso provisional NexoTeX](caso-provisional.json): servicio hipotetico de maquetacion y capacitacion LaTeX; no representa una empresa existente ni una eleccion confirmada del estudiante.
- [Marca grafica propuesta](marca-nexotex.svg) y [version PNG](marca-nexotex.png): propuesta asistida por IA para revisar, sin registro de marca ni validacion de mercado. No es una actividad entregada.
- La exportacion del piloto se verifico con Pandoc, python-docx y XeLaTeX: DOCX integro, dos imagenes, salto de portada y estilo normal Arial; PDF de cinco paginas con texto. Se corrigio el salto de pagina usando `WD_BREAK.PAGE`. La reanudacion reutilizo el TEX sin nuevas llamadas al modelo.

## Limites del lote

Los IDs son identificadores Moodle, no una numeracion institucional inventada. Las salidas futuras deben conservar el formato de la consigna: Word para el modulo 6545 y PDF para el integrador. Los PDF adicionales serian copias de revision, no sustitutos de Word ni del enlace de video.

| Modulos | Tratamiento previsto | Estado actual |
| --- | --- | --- |
| 6530, 6552, 6553 | Guias de preparacion; sin respuestas ni intentos | No ejecutados |
| 6539 | Caracterizacion hipotetica de apoyo al capitulo; sin acceder a seis reactivos | No ejecutado |
| 6534 | Pauta personalizable; sin empleo, experiencia, expectativas ni respuestas a companeros inventados | No ejecutado |
| 6545 | Imagen propuesta con nombre, logotipo, lema y justificacion; Word | Generado y exportado; revision editorial pendiente |
| 6546 | Mercadotecnia y publicidad para AM Taller; sin precios, stock ni demanda afirmados | Generado y exportado; revisión editorial pendiente |
| 6547 | Área geográfica y diseño de investigación; territorio y mercado meta pendientes | Generado y exportado; revisión editorial pendiente |
| 6548 | Dos instrumentos para oferta y demanda, sin respuestas ni resultados | Generado y exportado; revisión editorial pendiente |
| 6550, 6551 | Borradores AM Taller con datos pendientes claramente identificados | No ejecutados |
| 6549 | Estructura de analisis; requiere resultados reales de campo | No ejecutado |
| 6557 | Borrador integrador con las secciones exigidas; no afirmar viabilidad validada | No ejecutado |
| 6555 | Guion y apoyos; requiere grabacion y aparicion del estudiante | No ejecutado |

No se enviaron actividades, publicaron mensajes ni iniciaron cuestionarios. Se uso el nuevo motor configurado por el usuario sin modificar credenciales ni endpoints. El 401 queda registrado como antecedente.

## Reanudar

Desde la raiz del repositorio, comprobar la seleccion efectiva sin llamar al modelo:

```powershell
.\.venv\Scripts\python.exe .\.aulatex-temp\realizar-plan-negocios-2026-09-20\ejecutar.py --module 6545 --check
```

La comprobacion muestra motor y deployment, nunca claves. No usar la contrasena de Moodle como clave del proveedor. El comando `llm-config` de la suite esta orientado a model-router; no ejecutarlo para cambiar inadvertidamente el proveedor SOL que ahora funciona.

El piloto puede reexportarse reutilizando el contenido ya generado:

```powershell
.\.venv\Scripts\python.exe .\.aulatex-temp\realizar-plan-negocios-2026-09-20\ejecutar.py --module 6545
```

La rutina temporal usa el agente real de AulaTeX con contexto aislado y tres etapas, sin bucles de optimizacion ilimitados. Rechaza reemplazar un TEX existente que difiera del generado. Reexportar actualiza PDF y DOCX: no usar ese comando sobre ediciones manuales de Word sin preservarlas antes. Validar el piloto y el caso empresarial antes de extenderlo al resto; los pendientes personales, de campo y de video necesitan intervencion del estudiante.

Registro sin secretos: [ejecucion.json](ejecucion.json). Las trazas tecnicas quedan en `.aulatex-temp/`, excluidas de Git.