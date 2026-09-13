# Auditoría de integridad y contratos — Actividad 6 / Moodle 3.1

Fecha: 13 de septiembre de 2026.

## Dictamen

**Documento corregido y recompilado con identidad institucional ITESCA.**
El observador AulaTeX devuelve `passed: true`, puntuación **100/100**, con todas
sus comprobaciones contractuales verdaderas y sin hallazgos críticos.

**No equivale a certificar el 100 % del proceso integral ni la autoría personal.**
Persisten las salvedades tipográficas, de ejecución del pipeline y de revisión
del estudiante indicadas al final. Esta auditoría sustituye como dictamen vigente
a la revisión inicial que describía un documento independiente de ocho páginas.

## Hallazgos y correcciones

| Hallazgo inicial | Corrección y evidencia |
|---|---|
| Documento independiente sin plantilla ITESCA | Se carga el núcleo real `template`, con portada oficial, logotipo, marca de agua, franja institucional, resumen, índice, encabezados y pie |
| Desarrollo fragmentado y conclusión como subsección | Tres secciones de primer nivel: Introducción; DECIDE: de la evidencia a la decisión organizacional; Conclusiones |
| Memoria clasificaba la propuesta como foro y refería Actividad 5 | Contrato activo corregido a propuesta de modelo, Actividad 6; clasificación antigua preservada expresamente como antecedente obsoleto |
| Observador rechazaba citas resueltas | Seleccionaba una bibliografía auxiliar por orden alfabético al no reconocer sufijo MGA; corregida resolución canónica, con prueba que fallaba antes y pasa después |
| No había extracción específica de actividad 6 | Extracción real TF-IDF de las cuatro lecturas y planeación: cinco artefactos nucleares completos |
| Cierre sin adopción ausente del diagrama | Incorporadas rutas «No: revisar» y «No: cerrar»; suspensión por riesgo crítico antes de decidir |
| Ventana de aceptación ambigua | Cumplimiento en semanas 5 y 6; auditoría en 7 y 8, sin ampliación automática |
| Denominadores cero y base nula insuficientemente tratados | Periodos sin demanda son no evaluables; tope absoluto de inventario aprobado antes del piloto |
| Alternativas potencialmente complementarias | Se delimitan como paquetes alternativos del primer piloto; combinaciones posteriores requieren otra evaluación |
| Matriz se recortaba pese a compilar | Reemplazada por tabla de ancho controlado; verificadas visualmente las cinco columnas y sus valores |

## Cumplimiento de la consigna

Posiciones físicas en el PDF final de **12 páginas**, incluida portada:

| Componente | Ubicación | Estado |
|---|---|---|
| Portada institucional | 1 | Verificada visualmente |
| Resumen e índice | 2–3 | Generados por el núcleo institucional |
| Introducción con problema, objetivo y tesis | 4 | Incluida |
| Sustento, modelos previos y aportaciones | 5 | Incluidos; citas visibles |
| Diagrama del proceso | 6 | Completo en una página, con retornos y cierre |
| Descripción práctica de seis etapas | 7 | Acciones, responsables y evidencias |
| Tres alternativas y sensibilidad | 8 | Matriz completa, cálculos contrastados y supuestos explícitos |
| Puesta en marcha | 9–10 | Recursos, calendario, precauciones, indicadores y reglas |
| Conclusiones | 11 | Página propia, posición, razones, consecuencias y transferencia |
| Fuentes de consulta | 12 | Cuatro obras en APA mediante Biber/biblatex-apa |

El cuerpo está en Arial de 12 pt LaTeX (11.955 pt PDF), con interlineado 1.5
y justificación. Los títulos de portada, encabezados, pie y nota al pie siguen
los tamaños de la plantilla institucional; no se afirma que todo elemento del
PDF tenga exactamente 12 pt. No se sustituyó Arial por Helvetica o Arimo.

## Evidencia de ejecución y comprobación

- Compilación exitosa con XeLaTeX y Biber mediante
  [compilar-actividad-6.sh](compilar-actividad-6.sh).
- Observador final: `20260913-015935-activity-06-observer`, conservado en
  retroalimentación editorial de AulaTeX; `passed: true`, score 100, cero críticos.
- Extractor: `20260913-012952-extractor`, motor TF-IDF; `ok: true`. Se evitaron
  llamadas a servicios LLM externos en esta extracción.
- Pruebas: **29 pasaron**, incluyendo cinco casos de selección bibliográfica y
  las regresiones de generación de actividades.
- Comprobación independiente del PDF: **12 páginas**, tres actos, cuatro claves
  citadas, cero palabras fuera de los límites físicos de página.
- PDF no anterior a ninguna de las **24 dependencias locales** TEX/BIB/PNG
  registradas en su archivo de compilación.
- Sin citas indefinidas, bibliografía vacía, caracteres ausentes ni
  desbordamientos `Overfull`/`Underfull` en el registro final.
- Fuentes de texto Arial regular, negrita y cursiva incrustadas; el núcleo
  también incorpora fuentes de símbolos matemáticos.
- Inspección visual de portada, diagrama, matriz, indicadores, conclusión y
  referencias; no se tomó el código de salida del compilador como único criterio.
- Revisión adversarial estática: detectó incoherencias de cierre y ventanas
  operativas; fueron corregidas antes de la compilación final.

Matriz: A = 4.15, B = 3.40, C = 3.20. Con pesos alternativos: A = 4.05,
B = 3.70, C = 3.20. Al reducir además el impacto de A: A = 3.60 y B pasa a
ser preferible. Se conserva esta fragilidad y no se afirma eficacia demostrada.

## Salvedades: lo que no debe declararse aprobado

1. **Advertencia tipográfica residual.** El núcleo emite
   `Font shape TS1/Arial(0)/m/n undefined`, con sustitución de esa forma de símbolo,
   y su aviso de resumen. No hay caracteres ausentes ni recortes detectados, pero
   no se certifica un registro libre de advertencias ni que absolutamente todos
   los símbolos sean Arial. No se ocultaron ni suprimieron esos mensajes.
2. **Pipeline integral no ejecutado como una sola corrida.** Se realizaron
   consulta de memorias, planeación, extracción, reparación, revisión adversarial,
   compilación y observación. No se ejecutó una campaña completa
   `agent --action realizar-actividad` con sus roles LLM y optimizador por
   convergencia; no se inventan manifiestos ni consenso de esa campaña.
3. **Límites del observador.** Su evaluación se ejecutó sin `--compile-check`:
   conserva compilación como `unknown`. La compilación efectiva y frescura se
   comprobaron separadamente con el motor compatible y las dependencias reales.
   Su 100/100 no sustituye la revisión visual ni demuestra por sí solo integridad.
4. **Revisión personal.** El texto identifica la elaboración asistida por GitHub
   Copilot. No puede certificarse que el estudiante ya haya contrastado y asumido
   personalmente el análisis. No se cambió esa salvedad por una declaración falsa.
5. **Plataforma y plazo.** No se realizó entrega ni se comprobó una prórroga.
   El cierre transcrito fue el 31 de agosto de 2026. La disponibilidad actual de
   todos los materiales del aula debe confirmarse en Moodle.

## Trazabilidad y fuente de verdad

- [reporte-fundamentos-de-gestion-administrativa-Actividad-6.tex](reporte-fundamentos-de-gestion-administrativa-Actividad-6.tex): contenido canónico.
- [reporte-fundamentos-de-gestion-administrativa-Actividad-6.pdf](reporte-fundamentos-de-gestion-administrativa-Actividad-6.pdf): PDF recompilado.
- [formato-itesca-actividad-6.tex](formato-itesca-actividad-6.tex): adaptación local del núcleo institucional.
- [planeaciones-fundamentos-de-gestion-administrativa/actividad-6-propuesta-modelo.md](planeaciones-fundamentos-de-gestion-administrativa/actividad-6-propuesta-modelo.md): consigna y decisiones editoriales diferenciadas.
- [planeaciones-fundamentos-de-gestion-administrativa/actividad-6-mapa-soporte.md](planeaciones-fundamentos-de-gestion-administrativa/actividad-6-mapa-soporte.md): afirmación, fuente y límite de atribución.
- [propuesta-modelo-DECIDE-actividad-6.tex](propuesta-modelo-DECIDE-actividad-6.tex): alias de compatibilidad, no un segundo documento independiente.

Las entradas específicas antiguas de bibliografía se conservan como antecedente;
el reporte usa la bibliografía canónica de la materia y la general del programa.
No se modificaron deliberadamente otras actividades ni se revirtieron sus cambios.