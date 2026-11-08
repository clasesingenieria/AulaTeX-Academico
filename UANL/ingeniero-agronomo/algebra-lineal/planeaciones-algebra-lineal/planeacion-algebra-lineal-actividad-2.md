# Planeación Académica: Actividad 2: Segundo Laboratorio de Algebra Lineal

**Unidad de Aprendizaje:** Álgebra Lineal (`REF-62bf547760`)
**Programa Educativo:** Ingeniero Agronomo
**Institución:** UANL
**Docente Titular:** Dr. Miguel Ángel Dector Carrillo
**Estudiante:** Diego de la Cruz Muñoz
**Actividad Contractual:** actividad-2
**Fase / Unidad:** Unidad-1
**Ponderación:** 10.0 pts
**Estado de Revisión:** `needs_review` (Validación semántica: `passed`)

---

## 1. Identificación y Contrato de Artefactos

```json
{
  "schema_version": "1.0.0",
  "plan_id": "pca-uanl-algebra-lineal-actividad-2",
  "subject_id": "algebra-lineal",
  "offering_id": "REF-62bf547760",
  "deliverables_directory": "entregas-algebra-lineal"
}
```

---

## 2. Instrucción y Consigna Formativa

1. Revisar el PDF original segundo-laboratorio-ej25.pdf y cotejarlo con la transcripción conservada. Las rutas proporcionadas identifican las fuentes, pero no permiten inferir los enunciados no reproducidos en la consigna; no inventar sistemas, cantidades de ejercicios ni resultados. Si el PDF no está disponible, solicitarlo antes de completar el inventario y la resolución. 2. Registrar en la identificación del trabajo: UANL; programa Ingeniero Agrónomo; asignatura Álgebra Lineal; Actividad 2: Segundo Laboratorio de Álgebra Lineal; Diego de la Cruz Muñoz, matrícula 1977875; docente Dr. Miguel Ángel Dector Carrillo; entrega informada: noviembre de 2026. Si se trabaja en equipo, incorporar los datos de los demás integrantes, sin exceder tres participantes. Conservar como antecedente documental el periodo EJ25 y confirmar con el docente el día de entrega, pues el original lo vincula al segundo examen parcial y no especifica una fecha exacta. 3. Elaborar un inventario de todos los ejercicios de los apartados I y II, manteniendo numeración, coeficientes, signos, variables y términos independientes. 4. Resolver cada sistema del apartado I por Gauss: formar la matriz aumentada, registrar las operaciones elementales, obtener una forma escalonada y realizar sustitución regresiva cuando corresponda. Resolver después por Gauss-Jordan: registrar las operaciones hasta obtener una forma escalonada reducida e interpretar el resultado. Finalmente, examinar la aplicabilidad de Cramer: comprobar que la matriz de coeficientes sea cuadrada y que su determinante sea distinto de cero; cuando proceda, calcular los determinantes de sustitución y las incógnitas. Si estas condiciones no se cumplen, documentar la limitación y no dividir entre cero ni presentar Cramer como procedimiento válido. 5. En el apartado II, elegir un método para cada problema y justificarlo antes de desarrollarlo, atendiendo a la estructura del sistema, sus condiciones de aplicabilidad y el trabajo algebraico requerido. 6. Verificar cada solución por sustitución en las ecuaciones originales; si aparecen sistemas incompatibles o con infinitas soluciones, justificar su clasificación con las ecuaciones o formas matriciales obtenidas. Comparar los resultados de los métodos del apartado I y corregir discrepancias. 7. Organizar la versión de entrega en hojas para máquina blancas y nuevas, con ejercicios en el orden indicado, sin grandes espacios en blanco y con notación legible. El reporte LaTeX y su PDF conservados son evidencia digital complementaria y no sustituyen ni modifican las instrucciones del original EJ25. Si se revisa ese respaldo, conservar sus ejercicios y comprobar su correspondencia con el trabajo; no declarar compilación o validación que no se haya realizado. 8. Auditar integridad, cálculos, justificaciones, limpieza y claridad antes de entregar. La actividad tiene una ponderación total de 10.0 puntos y no debe confundirse con el PIA, identificado como Actividad 3 y sujeto a su propio calendario.

### Requisitos Contractuales
- **req-1:** Utilizar el PDF docente como fuente de los enunciados completos y cotejar la transcripción. Conservar la totalidad, el orden y la numeración de los ejercicios; no inventar contenidos ausentes.
- **req-2:** Resolver cada sistema del apartado I por Gauss, Gauss-Jordan y Cramer, mostrando procedimientos. Verificar expresamente las condiciones de Cramer y documentar cualquier caso de inaplicabilidad.
- **req-3:** Seleccionar un método para cada problema del apartado II y justificar su elección mediante características concretas del sistema, no mediante preferencias sin fundamento.
- **req-4:** Mostrar operaciones algebraicas trazables, verificar las soluciones en las ecuaciones originales y justificar la clasificación del sistema cuando corresponda.
- **req-5:** Preparar la entrega en hojas para máquina blancas y nuevas, con orden, limpieza, claridad y sin grandes espacios en blanco, conforme al original.
- **req-6:** Identificar institución, programa, asignatura, actividad, estudiante, matrícula y docente. El equipo puede tener hasta tres integrantes; registrar a quienes efectivamente participen.
- **req-7:** Registrar noviembre de 2026 como mes de entrega informado para esta actividad, sin inventar día exacto. Distinguirlo del periodo documental enero-junio de 2025 y confirmar con el docente su relación con el segundo examen parcial. Mantener separado el calendario del PIA, Actividad 3.
- **req-8:** Tratar el reporte LaTeX y su PDF conservados como respaldo documental complementario, sin reescribir sus ejercicios ni asumir que sustituyen la entrega física. Cualquier revisión o compilación deberá reportarse únicamente si fue efectivamente realizada.

### Preguntas Guía de Investigación
- **[Equivalencia de sistemas] **¿Por qué las operaciones elementales utilizadas en Gauss y Gauss-Jordan preservan el conjunto solución del sistema?
- **[Comparación de métodos] **¿Qué diferencias de procedimiento existen entre Gauss y Gauss-Jordan y cómo se comprueba que conducen al mismo conjunto solución?
- **[Condiciones de Cramer] **¿Qué debe verificarse antes de aplicar Cramer y qué puede concluirse, y qué no, si el determinante de la matriz de coeficientes es cero?
- **[Elección metodológica en el apartado II] **¿Qué rasgos de cada sistema justifican la elección del método y qué ventaja ofrece frente a una alternativa?
- **[Verificación y control de errores] **¿Cómo permite la sustitución en las ecuaciones originales detectar errores de signo, cálculo o transcripción?

---

## 3. Entregables y Productos Verificados

### Producto: `prod-actividad-2`
- **Denominación:** laboratorio_resuelto
- **Formato editable:** `application/x-tex` -> `reporte-algebra-lineal-actividad-2.tex`
- **Formato de entrega:** `application/pdf` -> `entregas-algebra-lineal/reporte-algebra-lineal-actividad-2.pdf`
- **Extensión presupuestada:** La necesaria para resolver la totalidad de ejercicios del PDF original, sin grandes espacios en blanco; la consigna no establece un número de páginas.
- **Patrón de nomenclatura:** `reporte-algebra-lineal-actividad-2.pdf`

---

## 4. Criterios de Evaluación y Rúbrica Oficial

- **Ponderación total:** 10.0 pts
- **crit-1:** Resolución del apartado I y aplicación fundamentada de los tres métodos (4.0 pts)
- **crit-2:** Resolución del apartado II y justificación de la elección metodológica (3.0 pts)
- **crit-3:** Verificación de soluciones y coherencia de resultados (2.0 pts)
- **crit-4:** Integridad, orden, limpieza, claridad y cumplimiento documental (1.0 pts)
- **Comprobaciones editoriales obligatorias:** Total de la rúbrica: 10.0 puntos; propuesta de distribución curricular, no atribuida al PDF docente., Enunciados, coeficientes, signos y numeración cotejados con el PDF original., Apartado I con tres métodos por sistema o explicación fundamentada de la inaplicabilidad de Cramer., Apartado II con método elegido y justificación específica por problema., Operaciones, matrices, determinantes y resultados escritos con notación consistente., Soluciones verificadas y discrepancias corregidas., Hojas para máquina blancas y nuevas; orden, limpieza, claridad y ausencia de grandes espacios en blanco., Identificación de Diego de la Cruz Muñoz, matrícula 1977875, y del Dr. Miguel Ángel Dector Carrillo correctamente registrada., Noviembre de 2026 diferenciado del periodo EJ25; día exacto sujeto a confirmación docente., Reporte LaTeX y PDF conservados identificados como respaldo, sin sustituir las indicaciones de entrega ni afirmar validaciones no realizadas., PIA de la Actividad 3 y su calendario excluidos de esta entrega..

---

## 5. Políticas Académicas y Éticas

- **Uso de Inteligencia Artificial:** Declaración transparente de asistencia algorítmica en nota al pie institucional
- **Integridad Científica:** Cero tolerancia al plagio; literatura científica verificable indexada en JCR/Scopus
- **Citación:** APA 7ma edición
