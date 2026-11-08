# Planeación Académica: Evidencia 2.6: mapa cognitivo de algoritmo

**Unidad de Aprendizaje:** Álgebra Lineal (`REF-7d11b19007`)
**Programa Educativo:** Ingeniero Agronomo
**Institución:** UANL
**Docente Titular:** Dr. Miguel Ángel Dector Carrillo
**Estudiante:** Diego de la Cruz Muñoz
**Actividad Contractual:** evidencia-2-6
**Fase / Unidad:** Unidad-1
**Ponderación:** 10.0 pts
**Estado de Revisión:** `needs_review` (Validación semántica: `passed`)

---

## 1. Identificación y Contrato de Artefactos

```json
{
  "schema_version": "1.0.0",
  "plan_id": "pca-uanl-algebra-lineal-evidencia-2-6",
  "subject_id": "algebra-lineal",
  "offering_id": "REF-7d11b19007",
  "deliverables_directory": "entregas-algebra-lineal"
}
```

---

## 2. Instrucción y Consigna Formativa

1. Identificar la evidencia como Evidencia 2.6: mapa cognitivo de algoritmo, de Álgebra Lineal, programa Ingeniero Agrónomo, UANL. Registrar a Diego de la Cruz Muñoz, matrícula 1977875, y al docente Dr. Miguel Ángel Dector Carrillo. No confundir esta evidencia con el laboratorio EJ25 ni con el PIA. 2. Revisar la guía EV2, la metodología y la hoja Problemas evidencia 2 AL AD26.pdf, conservando la trazabilidad documental proporcionada. Tomar el Sistema 11 de la primera página: -4x+2y+6z=-6; 10x+3y+2z=-6; -9x-7y+10z=-7. No reutilizar el caso provisional N-P-K ni inventar datos o unidades. 3. Registrar la discrepancia de plazos: la hoja señala 16 de octubre de 2026 y la consulta Nexus del 20 de octubre muestra cierre el 23 de octubre de 2026 a las 23:42, según la hora de la plataforma. Solicitar aclaración al docente; no presentar esta diferencia como una prórroga acreditada ni garantizar aceptación. 4. Confirmar cuáles fueron los tres métodos vistos en clase. Si Cramer está incluido, seleccionarlo y justificar que resulta aplicable porque la matriz de coeficientes es cuadrada y su determinante no es cero; de lo contrario, utilizar un método permitido y conservar la verificación exacta como control. 5. Plantear A=[[-4,2,6],[10,3,2],[-9,-7,10]], el vector de incógnitas (x,y,z)^T y b=(-6,-6,-7)^T. Identificar claramente cada elemento y escribir AX=b. 6. Calcular det(A)=-4(44)-2(118)+6(-43)=-670. Concluir que las filas y columnas son linealmente independientes, rango(A)=3 y el sistema tiene solución única. 7. Para Cramer, formar Ax, Ay y Az reemplazando únicamente la columna correspondiente por b. Desarrollar sus determinantes sin omitir operaciones esenciales y comprobar Dx=206, Dy=148 y Dz=758. Obtener x=206/(-670)=-103/335, y=148/(-670)=-74/335 y z=758/(-670)=-379/335. 8. Sustituir las fracciones exactas en las tres ecuaciones: (412-148-2274)/335=-6; (-1030-222-758)/335=-6; (927+518-3790)/335=-7. Registrar residuos iguales a cero. 9. Redactar una conclusión que explique la unicidad y el cumplimiento simultáneo de las ecuaciones. Señalar que, al no existir contexto físico ni unidades en el enunciado, la interpretación es algebraica y numérica; no forzar una interpretación agronómica. 10. Diseñar un cuadro superior con el tema principal y dos secciones: procedimiento y ejemplo con matemáticas. Colocar cada instrucción en un cuadro de la primera sección y su operación correspondiente en la segunda, enlazándolas mediante flechas inequívocas. Mantener un orden visual consistente desde el planteamiento hasta la conclusión. 11. Usar el reporte digital únicamente como apoyo de organización y comprobación. Elaborar personalmente y a mano el desarrollo y el mapa; no copiar el trabajo de otro compañero, simular escritura manual ni declarar realizado un manuscrito inexistente. 12. Escanear o fotografiar el trabajo completo, revisar legibilidad, orden, orientación y ausencia de recortes, y reunir las imágenes en PDF. El PDF es el formato final recomendado porque satisface tanto la instrucción de imágenes ordenadas como la opción PNG/PDF indicada en la plataforma. 13. Autoevaluar el archivo con los doce criterios de la guía, cuya escala de 100 equivale a una ponderación de 10 puntos. Mantener pendientes los criterios de manuscrito, digitalización, envío y plazo hasta contar con evidencia verificable. 14. Seleccionar manualmente el archivo final, cargarlo y confirmar el envío en Nexus. Conservar el comprobante y la hora registrada. No efectuar envíos automáticos ni considerar que la preparación del archivo equivale a una entrega aceptada.

### Requisitos Contractuales
- **req-1:** Utilizar exclusivamente el Sistema 11 de la hoja docente: -4x+2y+6z=-6; 10x+3y+2z=-6; -9x-7y+10z=-7. Identificarlo como problema de la lista del profesor.
- **req-2:** Presentar el modelo AX=b con matriz de coeficientes, vector de incógnitas y términos independientes correctos, sin contexto físico ni unidades inventadas.
- **req-3:** Seleccionar y justificar uno de los tres métodos vistos en clase. Confirmar la admisibilidad de Cramer antes de adoptarlo y explicar la independencia lineal a partir de det(A)=-670.
- **req-4:** Mostrar un algoritmo ordenado desde la identificación del sistema hasta la verificación y la conclusión, sin saltos que impidan reproducir el procedimiento.
- **req-5:** Desarrollar operaciones correctas y comprobar la solución exacta (-103/335,-74/335,-379/335). Si se usa Cramer, mostrar D=-670, Dx=206, Dy=148 y Dz=758.
- **req-6:** Interpretar la solución como única y verificar las tres ecuaciones con residuos cero. Explicar que no procede una interpretación física porque el problema no proporciona contexto ni unidades.
- **req-7:** Elaborar a mano el desarrollo de la solución y el mapa. El reporte digital no sustituye este requisito; no simular manuscrito ni dar por existente un escaneo no recibido.
- **req-8:** Realizar la actividad individualmente y conservar la responsabilidad personal sobre razonamiento, escritura, revisión y entrega.
- **req-9:** Digitalizar el manuscrito en un PDF de imágenes ordenadas, completas y legibles, y realizar manualmente la carga y confirmación del envío en Nexus, conservando el comprobante.
- **req-10:** Incluir un cuadro superior con el tema principal y dos secciones, procedimiento y ejemplo con matemáticas; enlazar cada cuadro de procedimiento con sus operaciones mediante flechas.
- **req-11:** Presentar organización y redacción propias; no copiar parcial o totalmente el trabajo de otro compañero.
- **req-12:** Registrar ambas fechas: 16 de octubre de 2026 en la hoja y 23 de octubre de 2026 a las 23:42 en Nexus según la consulta proporcionada. Solicitar aclaración y no acreditar puntualidad ni prórroga sin respaldo verificable.
- **req-13:** Incluir identificación institucional y académica: UANL; Ingeniero Agrónomo; Álgebra Lineal; Evidencia 2.6; Diego de la Cruz Muñoz; matrícula 1977875; Dr. Miguel Ángel Dector Carrillo. Distinguir la fecha de entrega informada de la controversia documental del plazo.
- **req-14:** Distinguir estados de cumplimiento: el desarrollo digital y la solución están reportados como preparados y comprobados en la consigna; manuscrito, escaneo, selección del archivo final, envío y aceptación requieren verificación posterior.

### Preguntas Guía de Investigación
- **[Modelación algebraica] **¿Cómo se conserva la correspondencia entre los coeficientes del Sistema 11 y las filas y columnas de AX=b?
- **[Selección del método] **¿Cuál de los métodos vistos en clase se utilizará y qué condiciones matemáticas justifican su aplicación a este sistema?
- **[Independencia lineal] **¿Por qué det(A)=-670 permite concluir independencia lineal, rango completo y solución única?
- **[Control del algoritmo] **¿Cómo se evita reemplazar una columna incorrecta o perder signos al construir y evaluar los determinantes de Cramer?
- **[Verificación e interpretación] **¿Qué demuestra la sustitución exacta con residuos cero y por qué no autoriza a atribuir un significado físico a las incógnitas?
- **[Comunicación visual] **¿Puede un lector reconstruir toda la solución siguiendo los cuadros y flechas de las dos secciones del mapa?
- **[Integridad y aceptación] **¿Qué requisitos siguen pendientes aunque exista un reporte digital correcto y qué evidencia se necesita para acreditar manuscrito, envío y cumplimiento del plazo?

---

## 3. Entregables y Productos Verificados

### Producto: `prod-evidencia-2-6`
- **Denominación:** mapa_cognitivo_de_algoritmo_manuscrito_escaneado
- **Formato editable:** `application/x-tex` -> `reporte-algebra-lineal-evidencia-2-6.tex`
- **Formato de entrega:** `application/pdf` -> `entregas-algebra-lineal/reporte-algebra-lineal-evidencia-2-6.pdf`
- **Extensión presupuestada:** Sin extensión fija indicada; las páginas necesarias para presentar el mapa y las operaciones de forma completa y legible en un PDF de imágenes ordenadas.
- **Patrón de nomenclatura:** `reporte-algebra-lineal-evidencia-2-6.pdf`

---

## 4. Criterios de Evaluación y Rúbrica Oficial

- **Ponderación total:** 10.0 pts
- **crit-1:** Problema de la lista del profesor: 5 de 100 en la guía, equivalentes a 0.5 de 10. (0.5 pts)
- **crit-2:** Modelo matemático adecuado: 10 de 100 en la guía, equivalentes a 1 de 10. (1.0 pts)
- **crit-3:** Método e identificación de dependencia lineal: 5 de 100 en la guía, equivalentes a 0.5 de 10. (0.5 pts)
- **crit-4:** Orden de pasos: 17 de 100 en la guía, equivalentes a 1.7 de 10. (1.7 pts)
- **crit-5:** Corrección de pasos: 17 de 100 en la guía, equivalentes a 1.7 de 10. (1.7 pts)
- **crit-6:** Interpretación numérica y física: 10 de 100 en la guía, equivalentes a 1 de 10. (1.0 pts)
- **crit-7:** Procedimiento a mano: 8 de 100 en la guía, equivalentes a 0.8 de 10. (0.8 pts)
- **crit-8:** Elaboración individual: 5 de 100 en la guía, equivalentes a 0.5 de 10. (0.5 pts)
- **crit-9:** PDF en la plataforma: 5 de 100 en la guía, equivalentes a 0.5 de 10. (0.5 pts)
- **crit-10:** Mapa con dos secciones: 8 de 100 en la guía, equivalentes a 0.8 de 10. (0.8 pts)
- **crit-11:** Originalidad: 5 de 100 en la guía, equivalentes a 0.5 de 10. (0.5 pts)
- **crit-12:** Entrega en tiempo y forma: 5 de 100 en la guía, equivalentes a 0.5 de 10. (0.5 pts)
- **Comprobaciones editoriales obligatorias:** La suma de máximos es 10.0 puntos, equivalente proporcionalmente a los 100 puntos de la guía; no constituye una calificación otorgada., Los descriptores desarrollan únicamente el cumplimiento completo informado; no se inventan niveles parciales de la rúbrica docente., Identificación correcta de institución, programa, asignatura, evidencia, estudiante, matrícula y docente., Sistema 11 transcrito exactamente y sin referencias al caso provisional N-P-K., Notación matricial coherente, fracciones legibles y signos revisados., Determinante -670, solución exacta y tres residuos cero comprobados., Cuadro superior, dos secciones y correspondencia inequívoca entre pasos y operaciones., Sin contexto físico, unidades o interpretaciones agronómicas inventadas., Imágenes del manuscrito completas, ordenadas, orientadas y sin recortes, sombras que oculten información o pérdida de legibilidad., El PDF abre correctamente y no presenta operaciones o flechas fuera de los límites de página., El reporte digital de apoyo no se confunde con el manuscrito escaneado., Las dos fechas de vencimiento se conservan diferenciadas, sin declarar prórroga ni aceptación garantizada., Manuscrito, escaneo y envío permanecen pendientes hasta contar con evidencia verificable., No se imponen extensión de reporte, aparato APA 7 o compilación LaTeX como requisitos adicionales del mapa..

---

## 5. Políticas Académicas y Éticas

- **Uso de Inteligencia Artificial:** Declaración transparente de asistencia algorítmica en nota al pie institucional
- **Integridad Científica:** Cero tolerancia al plagio; literatura científica verificable indexada en JCR/Scopus
- **Citación:** APA 7ma edición
