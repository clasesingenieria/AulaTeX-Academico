# Planeación Académica: Consigna de Evaluación: Producto Integrador de Aprendizaje (PIA)

**Unidad de Aprendizaje:** Álgebra Lineal (`REF-9b66e5359c`)
**Programa Educativo:** Ingeniero Agronomo
**Institución:** UANL
**Docente Titular:** Dr. Miguel Ángel Dector Carrillo
**Estudiante:** Diego de la Cruz Muñoz
**Actividad Contractual:** pia
**Fase / Unidad:** Unidad-1
**Ponderación:** 25.0 pts
**Estado de Revisión:** `needs_review` (Validación semántica: `failed`)

---

## 1. Identificación y Contrato de Artefactos

```json
{
  "schema_version": "1.0.0",
  "plan_id": "pca-uanl-algebra-lineal-pia",
  "subject_id": "algebra-lineal",
  "offering_id": "REF-9b66e5359c",
  "deliverables_directory": "entregas-algebra-lineal"
}
```

---

## 2. Instrucción y Consigna Formativa

1. Revisar la consigna REF#261013755137 y registrar que el PIA se evalúa con una rúbrica de 100 puntos y aporta hasta 25 puntos a la calificación final: aporte = calificación del PIA × 0.25. Elegir modalidad individual o equipo de 2 a 3 integrantes. Usar como datos de trabajo los proporcionados en la solicitud: Diego de la Cruz Muñoz, matrícula 1977875, y Dr. Miguel Ángel Dector Carrillo. La consigna transcrita contiene otro estudiante y otro docente; confirmar esta discrepancia antes de la entrega, sin mezclar identidades. Confirmar también el día exacto de entrega dentro de noviembre de 2026. 2. Seleccionar un caso real del sector agronómico que permita desarrollar un balance de masa o nutrientes y un modelo de transición poblacional o distribución hídrica. Explicar la conexión entre ambos componentes; si no existe acoplamiento cuantitativo directo, no inventarlo y justificar su integración en la misma decisión agronómica. 3. Revisar literatura pertinente y reunir datos trazables. Registrar fuentes, unidades, condiciones de medición, supuestos y límites de validez. Distinguir datos observados, parámetros estimados y escenarios simulados; no presentar simulaciones como observaciones reales. 4. Definir variables y formular Bx = b. Reservar B para el balance y T para la transición, evitando confundir matrices con funciones distintas. Comprobar dimensiones, homogeneidad de unidades y restricciones físicas. 5. Resolver el sistema con eliminación gaussiana o Gauss-Jordan, mostrando las operaciones elementales. Comparar rango(B) y rango([B|b]) para establecer compatibilidad y unicidad. Calcular det(B) si B es cuadrada; obtener y verificar B inversa únicamente si existe. En casos no cuadrados o singulares, justificar por qué el determinante o la inversa no son aplicables y utilizar el análisis de rangos. Verificar la solución por sustitución y mediante el residuo Bx - b; declarar las tolerancias numéricas empleadas. 6. Construir T y especificar z(t+1) = Tz(t), el estado inicial y la unidad temporal. Si se utiliza una matriz de Leslie, documentar fecundidades y supervivencias: una matriz de Leslie no es, en general, estocástica. Si se utiliza una matriz estocástica con vectores columna, verificar entradas no negativas y columnas con suma uno; explicar cualquier otra convención. Si el flujo hídrico incluye pérdidas o aportes, representar estos explícitamente y no imponer conservación artificial. 7. Obtener el polinomio característico det(T - λI), calcular autovalores y autovectores y comprobar Tv = λv. Interpretar el radio espectral y presentar una proyección temporal. Para Leslie, distinguir crecimiento o decrecimiento de la abundancia respecto de una distribución estable de etapas; justificar las condiciones que permiten convergencia. Para matrices estocásticas, calcular y normalizar un vector estacionario cuando corresponda, sin asumir unicidad o convergencia sin verificar sus condiciones. 8. Integrar resultados y discutir factibilidad, sensibilidad y limitaciones. Evaluar al menos una variación justificada de un parámetro relevante y explicar su efecto sobre la solución o la dinámica. Formular recomendaciones vinculadas a los resultados, sin atribuir validez predictiva fuera de los supuestos del modelo. 9. Redactar el reporte con la estructura requerida, plantilla y tipografía institucional UANL disponibles, escudo y emblema oficiales autorizados, ecuaciones legibles, tablas con unidades, figuras preferentemente vectoriales y citas APA 7 mediante un flujo bibliográfico compatible con BibTeX o Biber. No afirmar certificación institucional si no existe un proceso formal de validación. 10. Elaborar una presentación Beamer 16:9 que sintetice problema, datos, modelos, procedimientos esenciales, resultados, limitaciones y recomendaciones. Preparar la defensa de los cálculos y supuestos. 11. Compilar ambos productos, revisar referencias cruzadas, correspondencia entre citas y bibliografía, ausencia de errores y desbordes tipográficos, y consistencia entre reporte y diapositivas. Conservar archivos fuente, bibliografía, datos y código utilizado para permitir la reproducción.

### Requisitos Contractuales
- **req-1:** Registrar institución UANL, Facultad de Agronomía, programa Ingeniero Agrónomo, asignatura Álgebra Lineal y referencia REF#261013755137. Usar provisionalmente Diego de la Cruz Muñoz, matrícula 1977875, y Dr. Miguel Ángel Dector Carrillo; confirmar la discrepancia con los nombres incluidos en la consigna transcrita y la fecha exacta de noviembre de 2026.
- **req-2:** Desarrollar el PIA individualmente o en equipo de 2 a 3 estudiantes; identificar a todos los integrantes y documentar sus contribuciones cuando corresponda.
- **req-3:** Seleccionar un caso agronómico real y documentar fuentes de datos, variables, unidades, restricciones y supuestos; señalar explícitamente parámetros estimados y escenarios simulados.
- **req-4:** Formular un balance Bx = b consistente y resolverlo mediante eliminación gaussiana o Gauss-Jordan con operaciones elementales visibles.
- **req-5:** Comparar rangos de B y [B|b], clasificar el sistema, calcular determinante e inversa cuando sean aplicables y comprobar la solución por sustitución y residuo.
- **req-6:** Construir un modelo dinámico z(t+1) = Tz(t) para plagas, cultivos o flujo hídrico, declarando estado inicial, intervalo temporal y convención de transición; distinguir rigurosamente matrices de Leslie y matrices estocásticas.
- **req-7:** Desarrollar det(T - λI) = 0, calcular y verificar autovalores y autovectores e interpretar comportamiento a largo plazo bajo condiciones explícitas.
- **req-8:** Relacionar ambos componentes matemáticos con decisiones agronómicas, evaluar factibilidad y limitaciones y analizar al menos una variación justificada de un parámetro relevante.
- **req-9:** Entregar un reporte técnico PDF con portada institucional, resumen y palabras clave, introducción y marco teórico, metodología y desarrollo, resultados y discusión, conclusiones y recomendaciones, y referencias APA 7.
- **req-10:** Utilizar plantilla y tipografía institucional UANL disponibles, emblemas oficiales autorizados, ecuaciones y tablas legibles y figuras vectoriales cuando sea viable; sincronizar citas y bibliografía mediante BibTeX o Biber.
- **req-11:** Entregar una presentación ejecutiva Beamer en formato 16:9, coherente con el reporte y preparada para sustentación ante el docente.
- **req-12:** Conservar fuentes LaTeX, archivo bibliográfico, datos y código utilizado; verificar compilación exitosa de reporte y presentación y reproducibilidad de los resultados.
- **req-13:** Aplicar la rúbrica original sobre 100 puntos: modelado matemático 30, resolución analítica y algorítmica 30, interpretación agronómica 20 y calidad editorial y normativa UANL 20; convertir el resultado a un aporte máximo de 25 puntos mediante multiplicación por 0.25.

### Preguntas Guía de Investigación
- **[Delimitación del caso y calidad de datos] **¿Qué decisión agronómica se busca sustentar y qué datos permiten representar el problema sin confundir mediciones reales con estimaciones?
- **[Balance de masa o nutrientes] **¿Qué representa cada coeficiente de B, cada componente de x y cada término de b, y cómo se comprueba la consistencia de sus unidades?
- **[Compatibilidad y unicidad] **¿Qué indican rango(B), rango([B|b]) y, cuando corresponde, det(B) sobre la existencia y unicidad de una solución físicamente factible?
- **[Elección del modelo dinámico] **¿El fenómeno requiere una matriz de Leslie, una matriz estocástica u otro modelo lineal con pérdidas o aportes, y qué propiedades justifican esa elección?
- **[Análisis espectral] **¿Cómo se relacionan el autovalor dominante y su autovector con el crecimiento, la distribución estable o el estado estacionario, y bajo qué condiciones es válida esa interpretación?
- **[Sensibilidad y decisiones] **¿Qué parámetro influye de manera relevante en los resultados y cómo cambia la recomendación agronómica al modificarlo dentro de un escenario justificado?
- **[Reproducibilidad y sustentación] **¿Qué cálculos, fuentes y archivos permiten que otra persona reproduzca los resultados y cuestione razonadamente los supuestos del modelo?

---

## 3. Entregables y Productos Verificados

### Producto: `prod-pia`
- **Denominación:** reporte_academico_con_presentacion_beamer
- **Formato editable:** `application/x-tex` -> `reporte-algebra-lineal-pia.tex`
- **Formato de entrega:** `application/pdf` -> `entregas-algebra-lineal/reporte-algebra-lineal-pia.pdf`
- **Extensión presupuestada:** La consigna no fija extensión ni número de diapositivas. Se recomienda un reporte de 6 a 10 páginas de contenido, más portada, referencias y anexos necesarios; ajustar la presentación al tiempo de sustentación que confirme el docente.
- **Patrón de nomenclatura:** `reporte-algebra-lineal-pia.pdf`

---

## 4. Criterios de Evaluación y Rúbrica Oficial

- **Ponderación total:** 25.0 pts
- **crit-1:** Modelado matemático. Máximo: 30 puntos de la rúbrica; equivalente a 7.5 puntos de la calificación final. Los puntos de los descriptores indican el límite superior de cada banda original. (30.0 pts)
- **crit-2:** Resolución analítica y algorítmica. Máximo: 30 puntos de la rúbrica; equivalente a 7.5 puntos de la calificación final. Los puntos de los descriptores indican el límite superior de cada banda original. (30.0 pts)
- **crit-3:** Interpretación agronómica. Máximo: 20 puntos de la rúbrica; equivalente a 5 puntos de la calificación final. Los puntos de los descriptores indican el límite superior de cada banda original. (20.0 pts)
- **crit-4:** Calidad editorial y normativa UANL. Máximo: 20 puntos de la rúbrica; equivalente a 5 puntos de la calificación final. Los puntos de los descriptores indican el límite superior de cada banda original. (20.0 pts)
- **Comprobaciones editoriales obligatorias:** Identidad del estudiante y docente confirmada ante la discrepancia de la consigna., Portada con datos institucionales y emblemas oficiales autorizados., Estructura completa del reporte, incluidos resumen y palabras clave., Notación diferenciada y consistente para matriz de balance y matriz de transición., Ecuaciones, tablas y figuras numeradas y referidas en el texto; unidades explícitas., Sin citas huérfanas ni referencias bibliográficas sin correspondencia., Aparato crítico APA 7 sincronizado con el archivo .bib y el procesador bibliográfico elegido., Subtítulo entre 28 y 68 caracteres cuando lo requiera la plantilla AulaTeX utilizada., Maquetación balanceada sin desbordes hbox ni elementos ilegibles., Presentación Beamer en proporción 16:9 y consistente con el reporte., Compilación reproducible de ambos productos con rc=0 y sin referencias indefinidas., Sin afirmaciones de certificación institucional no respaldadas..

---

## 5. Políticas Académicas y Éticas

- **Uso de Inteligencia Artificial:** Declaración transparente de asistencia algorítmica en nota al pie institucional
- **Integridad Científica:** Cero tolerancia al plagio; literatura científica verificable indexada en JCR/Scopus
- **Citación:** APA 7ma edición
