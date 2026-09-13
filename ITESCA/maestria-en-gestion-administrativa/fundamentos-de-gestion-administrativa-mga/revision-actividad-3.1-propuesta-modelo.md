# Revisión de 3.1 Propuesta de Modelo — 20 %

> **Registro histórico, sustituido el 13 de septiembre de 2026.** El formato
> independiente aquí descrito no cumplía el contrato institucional completo.
> Consultar el dictamen vigente en
> [auditoria-integridad-actividad-6.md](auditoria-integridad-actividad-6.md).
> El PDF actual tiene 12 páginas y utiliza el núcleo ITESCA; las afirmaciones
> posteriores sobre ocho páginas, fuentes independientes y ausencia de avisos
> corresponden exclusivamente a la versión anterior.

Fecha de revisión: 12 de septiembre de 2026.

## Dictamen

**Estado inicial:** solo existía una plantilla pendiente, denominada Actividad 6
en la secuencia local. No se encontró un PDF específico de esta propuesta.

**Estado tras la revisión:** documento desarrollado y PDF generado de ocho páginas,
incluida la portada. Se propone DECIDE para decisiones administrativas, con una
aplicación hipotética a la reposición de inventario. Los datos, las metas y las
calificaciones del caso están expresamente identificados como simulados.

**Entrega en plataforma:** no verificada ni realizada. Los enlaces de Moodle
redirigen a inicio de sesión. La existencia del PDF no acredita una entrega.

## Consigna utilizada

La consigna fue proporcionada por el usuario: trabajo individual de Fundamentos
de Gestión Administrativa, grupo GGFG02, Unidad III. Toma de decisiones,
actividad **3.1 Propuesta de Modelo**, valor **20 %**.

- Apertura indicada: 24 de agosto de 2026, 00:00.
- Cierre indicado: 31 de agosto de 2026, 23:59.
- Entrega: PDF; Arial 12, interlineado 1.5, texto justificado y fuentes APA.
- Contenido: sustento del modelo y aportaciones; diagrama; descripción práctica
  de las etapas; recomendaciones de puesta en marcha; fuentes de consulta.
- [Curso GGFG02](https://cursos3.e-itesca.edu.mx/course/view.php?id=372).
- [Unidad III](https://cursos3.e-itesca.edu.mx/course/section.php?id=2724).

El cierre informado ya había transcurrido al realizar esta revisión. Es necesario
comprobar con el docente si existe prórroga, reapertura o aceptación extemporánea.
La fecha de portada corresponde a la elaboración actual; no se retrodató el trabajo.

## Cumplimiento del documento

Las páginas siguientes son posiciones físicas del PDF, contando la portada.

| Requisito | Evidencia | Resultado |
|---|---|---|
| Sustento y cambios | Página 2: procesos previos, alcance, aportaciones y límites | Incluido |
| Diagrama | Página 3: seis etapas, dos decisiones y retornos | Incluido y revisado visualmente |
| Descripción práctica | Página 4: acciones, responsables y productos de cada etapa | Incluido |
| Aplicación ilustrativa | Página 5: tres alternativas, filtro, matriz y sensibilidad | Incluido; cifras simuladas |
| Puesta en marcha | Páginas 6 y 7: recursos, ocho semanas, precauciones, indicadores y reglas de suspensión/adopción | Incluido |
| Fuentes APA | Página 8: cuatro referencias citadas en el texto, orden alfabético y sangría francesa | Generadas con biblatex-apa y Biber |
| Arial 12 | Clase de 12 pt y fontspec; PDF con ArialMT, Arial-BoldMT y Arial-ItalicMT incrustadas | Verificado |
| Interlineado 1.5 | Configuración onehalfspacing | Configurado y revisado visualmente |
| Texto justificado | Justificación del cuerpo; portada y etiquetas de diagrama centradas | Verificado visualmente |
| PDF legible | Ocho páginas tamaño carta; sin páginas vacías ni fragmentos aislados | Verificado |

Se recalcularon independientemente los valores de la matriz: A = 4.15,
B = 3.40 y C = 3.20. Con los pesos alternativos: A = 4.05, B = 3.70 y C = 3.20.
Si el impacto de A baja un punto en ese escenario, A = 3.60 y B pasa a ser
preferible. No se presenta el resultado como una decisión robusta ante toda incertidumbre.

## Material consultado y alcance de verificación

Se revisaron las copias locales de las cuatro lecturas siguientes. Durante el
trabajo fueron reorganizadas por cambios concurrentes; sus ubicaciones actuales son:

- [canos-y-colaboradores-toma-decisiones-empresa-proceso-clasificacion.pdf](referencias-fundamentos-de-gestion-administrativa/unidad-3-toma-de-decisiones/canos-y-colaboradores-toma-decisiones-empresa-proceso-clasificacion.pdf).
- [solano-toma-decisiones-gerenciales.pdf](referencias-fundamentos-de-gestion-administrativa/unidad-3-toma-de-decisiones/solano-toma-decisiones-gerenciales.pdf).
- [lopez-guaman-castro-2020-decisiones-eficacia-pymes-ambato.pdf](referencias-fundamentos-de-gestion-administrativa/unidad-3-toma-de-decisiones/lopez-guaman-castro-2020-decisiones-eficacia-pymes-ambato.pdf).
- [soto-chavez-y-colaboradores-2020-decision-gerencial-clima-organizacional.pdf](referencias-fundamentos-de-gestion-administrativa/unidad-3-toma-de-decisiones/soto-chavez-y-colaboradores-2020-decision-gerencial-clima-organizacional.pdf).

No se pudo confirmar que sean la totalidad de los materiales actualmente publicados
en Moodle. La consulta al repositorio UPV encontró una comprobación antirrobot.
La copia de Canós y colaboradores no muestra una fecha editorial: se registra
sin fecha, sin inferirla de los metadatos de creación del archivo. En Solano se
conserva el apellido impreso en el artículo; se contrastaron año, volumen y páginas
con la revista editora, ante una discrepancia del apellido en Dialnet.

## Archivos y recompilación

- [reporte-fundamentos-de-gestion-administrativa-Actividad-6.pdf](reporte-fundamentos-de-gestion-administrativa-Actividad-6.pdf): entregable.
- [reporte-fundamentos-de-gestion-administrativa-Actividad-6.tex](reporte-fundamentos-de-gestion-administrativa-Actividad-6.tex): entrada de compilación.
- [propuesta-modelo-DECIDE-actividad-6.tex](propuesta-modelo-DECIDE-actividad-6.tex): contenido y formato independientes de la plantilla compartida.
- [fundamentos-de-gestion-administrativa-actividad-6.bib](fundamentos-de-gestion-administrativa-actividad-6.bib): bibliografía específica.
- [compilar-actividad-6.sh](compilar-actividad-6.sh): ejecutar con Bash para recompilar.

El script usa latexmk con XeLaTeX y Biber, sin la configuración global que
selecciona pdfLaTeX. Comprueba Arial auténtica y publica el PDF junto a la fuente
solo tras una compilación exitosa. Los auxiliares quedan en la carpeta de
compilación de la raíz del proyecto, separados por actividad.

Arial se instaló en el perfil local del usuario a partir del paquete original
Microsoft Core Fonts distribuido por SourceForge; no se incorporaron fuentes
binarias al repositorio. En otro equipo deben estar instalados Arial, XeLaTeX,
latexmk, Biber y los paquetes LaTeX utilizados. Arimo o Helvetica no equivalen
al cumplimiento literal de Arial.

## Comprobaciones y revisión personal pendiente

- Compilación completa exitosa; sin citas indefinidas, caracteres ausentes ni
  desbordamientos reportados en el registro final.
- Comprobación de fuentes incrustadas y tamaño mediante pdffonts y MuPDF.
- Revisión visual de portada, diagrama, matriz, indicadores, conclusión y referencias.
- Validación de sintaxis del compilador Bash.
- Confirmar el nombre del estudiante de portada, tomado de la plantilla local;
  no se inventaron docente ni matrícula.
- Revisar y asumir el contenido de la propuesta individual antes de presentarla.
- Verificar materiales adicionales, datos institucionales exigidos y situación
  del plazo directamente en Moodle o con el docente.

No se modificaron deliberadamente otras actividades ni se revirtieron los cambios
concurrentes de organización de materiales.