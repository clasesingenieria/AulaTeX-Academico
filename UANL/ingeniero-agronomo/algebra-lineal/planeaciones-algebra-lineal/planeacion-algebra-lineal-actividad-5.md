# Planeación Académica: Consigna Oficial: Actividad 5 — Producto Integrador de Aprendizaje (PIA)

**Unidad de Aprendizaje:** Álgebra Lineal (`REF-a30bbfeee2`)
**Programa Educativo:** Ingeniero Agronomo
**Institución:** UANL
**Docente Titular:** Dr. Miguel Ángel Dector Carrillo
**Estudiante:** Diego de la Cruz Muñoz
**Actividad Contractual:** actividad-5
**Fase / Unidad:** Unidad-1
**Ponderación:** 25.0 pts
**Estado de Revisión:** `needs_review` (Validación semántica: `failed`)

---

## 1. Identificación y Contrato de Artefactos

```json
{
  "schema_version": "1.0.0",
  "plan_id": "pca-uanl-algebra-lineal-actividad-5",
  "subject_id": "algebra-lineal",
  "offering_id": "REF-a30bbfeee2",
  "deliverables_directory": "entregas-algebra-lineal"
}
```

---

## 2. Instrucción y Consigna Formativa

1. Revisar la consigna, seleccionar la modalidad individual o de equipo de dos a tres integrantes y delimitar un caso agronómico que conecte un balance de masa o nutrientes con una dinámica poblacional o una distribución de flujos. 2. Registrar como datos de esta planeación a Diego de la Cruz Muñoz, matrícula 1977875, y al Dr. Miguel Ángel Dector Carrillo; señalar que el texto de la consigna contiene nombres diferentes y solicitar confirmación antes de emitir la portada definitiva. La entrega se ubica en noviembre de 2026; no asignar un día no proporcionado. 3. Recuperar fuentes académicas y técnicas verificables para los fundamentos y parámetros del caso. Diferenciar datos observados, datos de literatura y valores hipotéticos; si no se dispone de información real suficiente, declarar la simulación y confirmar su aceptación con el docente. 4. Definir variables, unidades, fronteras del sistema, supuestos y restricciones físicas. Formular Ax = b y mostrar la correspondencia entre cada ecuación y el balance agronómico. 5. Determinar rango(A) y rango([A|b]); clasificar la compatibilidad y unicidad. Si A es cuadrada, calcular det(A); si además es invertible, obtener A inversa como comprobación adicional. Si no es invertible o no es cuadrada, justificar por qué la inversa ordinaria no procede. 6. Resolver por eliminación gaussiana o Gauss-Jordan, documentando operaciones elementales y resultados intermedios. Verificar por sustitución, residuo y consistencia dimensional, distinguiendo exactitud simbólica de aproximación numérica. 7. Formular una matriz de transición T para evitar confundirla con la matriz A del balance. Si se adopta Leslie, identificar fecundidades, supervivencias, clases y paso temporal; no imponerle carácter estocástico, pues una matriz de Leslie no es necesariamente estocástica. Si se adopta una matriz estocástica, declarar la convención por filas o columnas y comprobar no negatividad y sumas unitarias; para vectores columna con z(t+1) = Tz(t), utilizar la convención por columnas. Si existen pérdidas hídricas, incorporarlas mediante un estado explícito o justificar un modelo subestocástico. 8. Desarrollar det(T - lambda I) = 0, obtener los autovalores y los autovectores relevantes y verificar Tv = lambda v. Presentar procedimientos analíticos y contrastarlos con software, sin sustituir las deducciones por capturas de pantalla. 9. Analizar la evolución z(t+1) = Tz(t) a partir de un estado inicial documentado. Interpretar el radio espectral y las condiciones de convergencia; en Leslie, distinguir crecimiento o decrecimiento de la población y distribución estable de clases; en matrices estocásticas, verificar las condiciones de existencia, unicidad y convergencia al estado estacionario. 10. Examinar la factibilidad del balance y la sensibilidad a variaciones justificadas de al menos un parámetro relevante. Identificar qué vínculos conectan los dos modelos y no afirmar un acoplamiento matemático inexistente. 11. Redactar el reporte con la estructura oficial, tablas legibles, ecuaciones numeradas cuando se referencien, figuras preferentemente vectoriales y citas APA 7 gestionadas con un archivo .bib. Elaborar una presentación Beamer 16:9 que sintetice problema, metodología, resultados, interpretación y recomendaciones. 12. Compilar ambos productos, comprobar referencias y correspondencia de cifras, corregir advertencias editoriales y preparar la sustentación. La rúbrica se aplica sobre 100 puntos y su contribución a la calificación final se obtiene multiplicando el resultado por 0.25; el máximo de esta actividad es 25 puntos.

### Requisitos Contractuales
- **req-1:** Delimitar un caso del sector agronómico que integre balance de masa o nutrientes y dinámica poblacional o distribución de flujos, explicando su relación y la decisión que se pretende fundamentar.
- **req-2:** Documentar fuentes, datos, parámetros, unidades, supuestos, estado inicial y restricciones físicas; identificar explícitamente cualquier información simulada.
- **req-3:** Formular Ax = b con dimensiones compatibles y significado agronómico explícito de variables, coeficientes y términos independientes.
- **req-4:** Comparar rango(A) y rango([A|b]), calcular el determinante cuando proceda y justificar la existencia de la inversa; no calcular una inversa ordinaria para matrices singulares o no cuadradas.
- **req-5:** Resolver el sistema mediante eliminación gaussiana o Gauss-Jordan, mostrar operaciones elementales y verificar la solución por sustitución y residuo, indicando tolerancia si se utilizan aproximaciones.
- **req-6:** Construir y justificar una matriz de transición T; distinguir Leslie de matriz estocástica y verificar las propiedades estructurales y la convención de actualización seleccionadas.
- **req-7:** Desarrollar el cálculo espectral mediante det(T - lambda I) = 0, obtener autovalores y autovectores relevantes, verificar sus ecuaciones y analizar el comportamiento de largo plazo bajo condiciones explícitas.
- **req-8:** Interpretar los resultados agronómicamente, comprobar factibilidad y examinar sensibilidad a por lo menos un parámetro, indicando limitaciones y recomendaciones derivadas del modelo.
- **req-9:** Generar el reporte PDF en la plantilla institucional UANL proporcionada o validada, con escudo UANL y emblema de la Facultad de Agronomía obtenidos de fuentes institucionales autorizadas y con todas las secciones de la consigna.
- **req-10:** Mantener citas y referencias APA 7 sincronizadas con el archivo .bib mediante una configuración compatible de BibTeX o Biber, sin fuentes inventadas ni citas huérfanas.
- **req-11:** Elaborar una presentación ejecutiva Beamer 16:9 para sustentación, consistente con el reporte y centrada en decisiones, procedimientos y evidencias verificables.
- **req-12:** Entregar fuentes LaTeX y archivos auxiliares de datos o cálculo, documentar la compilación reproducible y verificar metadatos: Diego de la Cruz Muñoz, matrícula 1977875, Dr. Miguel Ángel Dector Carrillo y noviembre de 2026, sujetos a confirmación de la discrepancia nominal de la consigna.

### Preguntas Guía de Investigación
- **[Delimitación y articulación del caso] **¿Qué decisión agronómica exige integrar el balance de nutrientes con la dinámica poblacional o hídrica, y qué relación verificable existe entre ambos modelos?
- **[Datos y validez del modelo] **¿Qué datos sustentan cada coeficiente y qué supuestos permiten aproximar el fenómeno mediante relaciones lineales?
- **[Compatibilidad del sistema] **¿Qué revelan los rangos de A y [A|b] sobre la existencia y unicidad de la solución, y cómo se interpreta ese resultado en el caso agronómico?
- **[Verificación y factibilidad] **¿La solución satisface los balances, las unidades y las restricciones físicas, y qué implican componentes negativas o residuos superiores a la tolerancia establecida?
- **[Estructura de la transición] **¿Por qué corresponde utilizar una matriz de Leslie, una matriz estocástica u otra estructura justificada, y qué magnitud se conserva o cambia en cada paso temporal?
- **[Análisis espectral] **¿Qué indica el autovalor dominante y bajo qué condiciones su autovector describe una distribución estable o un estado estacionario?
- **[Sensibilidad y decisiones] **¿Cómo cambia la recomendación al modificar un parámetro relevante y qué incertidumbres impiden extrapolar los resultados?
- **[Sustentación y reproducibilidad] **¿Qué evidencia permite al docente reconstruir el modelo, verificar los cálculos y comprobar que las recomendaciones se desprenden de los resultados?

---

## 3. Entregables y Productos Verificados

### Producto: `prod-actividad-5`
- **Denominación:** reporte_academico
- **Formato editable:** `application/x-tex` -> `reporte-algebra-lineal-actividad-5.tex`
- **Formato de entrega:** `application/pdf` -> `entregas-algebra-lineal/reporte-algebra-lineal-actividad-5.pdf`
- **Extensión presupuestada:** Extensión no especificada en la consigna; como orientación de planeación, 6 a 10 páginas de cuerpo principal, sin contar portada, referencias y anexos, sujeta a validación docente.
- **Patrón de nomenclatura:** `reporte-algebra-lineal-actividad-5.pdf`

---

## 4. Criterios de Evaluación y Rúbrica Oficial

- **Ponderación total:** 25.0 pts
- **crit-1:** Modelado Matemático (30.0 pts)
- **crit-2:** Resolución Analítica y Algorítmica (30.0 pts)
- **crit-3:** Interpretación Agronómica (20.0 pts)
- **crit-4:** Calidad Editorial y Normativa UANL (20.0 pts)
- **Comprobaciones editoriales obligatorias:** Portada con identidad UANL y Facultad de Agronomía mediante recursos institucionales autorizados., Discrepancia entre nombres de la consigna y datos del encargo registrada y sometida a confirmación antes de la entrega definitiva., Fecha expresada como noviembre de 2026, sin inventar un día de entrega., Todas las secciones oficiales presentes y jerarquía de títulos consistente., Sin citas huérfanas; citas y referencias sincronizadas con el archivo .bib y normalizadas en APA 7., Subtítulo entre 28 y 68 caracteres, si se utiliza como control editorial AulaTeX; no presentarlo como requisito oficial adicional de la consigna., Ecuaciones, tablas y figuras legibles, referenciadas y consistentes en unidades y notación., Figuras vectoriales cuando corresponda y ausencia de desbordes hbox visibles., Presentación Beamer con relación de aspecto 16:9 y cifras coincidentes con el reporte., Compilación reproducible de ambos documentos con código de retorno 0 y sin referencias pendientes..

---

## 5. Políticas Académicas y Éticas

- **Uso de Inteligencia Artificial:** Declaración transparente de asistencia algorítmica en nota al pie institucional
- **Integridad Científica:** Cero tolerancia al plagio; literatura científica verificable indexada en JCR/Scopus
- **Citación:** APA 7ma edición
