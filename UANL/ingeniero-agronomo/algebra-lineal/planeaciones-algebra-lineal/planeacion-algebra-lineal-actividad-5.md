# Planeación Académica: Producto Integrador de Aprendizaje (PIA)

**Unidad de Aprendizaje:** Álgebra Lineal (`REF#261013755137`)  
**Programa Educativo:** Ingeniero Agrónomo  
**Institución:** Universidad Autónoma de Nuevo León (Facultad de Agronomía)  
**Docente Titular:** Miranda Vázquez José de Jesús  
**Estudiante:** Diego de la Cruz Muñoz (Matrícula: 1977875)  
**Entregable Contractual:** Producto Integrador de Aprendizaje (Reporte y Presentación Beamer)  
**Fecha de Entrega Oficial:** 11 de noviembre de 2026  
**Ponderación:** 25.0 puntos (15 pts Reporte Escrito + 10 pts Video y Presentación)  
**Estado Editorial:** Aprobado / Banda Maestro (EMS $\ge 90$)  

---

## 1. Identificación y Contrato de Artefactos

```json
{
  "schema_version": "1.0.0",
  "plan_id": "pca-uanl-algebra-lineal-pia-2026",
  "subject_id": "algebra-lineal",
  "offering_id": "REF#261013755137",
  "deliverables_directory": "entregas-algebra-lineal"
}
```

---

## 2. Instrucción y Consigna Formativa Oficial
1. Desarrollar un caso de ingeniería agronómica regional en Nuevo León (cultivo de cítricos en General Terán/Montemorelos), formulando un sistema de al menos 3 ecuaciones lineales con 3 incógnitas para la optimización de fertilización balanceada ($N$, $P_2O_5$, $K_2O$) a partir de fuentes comerciales acopladas.
2. Registrar como estudiante oficial a **Diego de la Cruz Muñoz**, matrícula 1977875, y como docente titular a **Miranda Vázquez José de Jesús**.
3. Erradicar todo metadiscurso escolar: no incluir palabras como "actividad", "evidencia", "consigna" o "Actividad 5" en los reportes o presentaciones; titular con enfoque temático sustantivo.
4. Generar dos productos:
   - Reporte técnico formal (`reporte-algebra-lineal-Actividad-5.tex` / `.pdf`) siguiendo las 9 secciones estipuladas en el programa oficial.
   - Presentación de diapositivas en Beamer 16:9 (`presentacion-algebra-lineal-Actividad-5.tex` / `.pdf`) para sustentar la exposición en video requerida de principio a fin sin omitir pasos.
5. Desarrollar y contrastar tres métodos analíticos: Eliminación de Gauss-Jordan con matrices aumentadas paso a paso, Regla de Cramer mediante determinantes, e Inversión Matricial con comprobación del residuo vectorial $\mathbf{r} = A\mathbf{x} - \mathbf{b} = \mathbf{0}$.
6. Garantizar compilación limpia con `latexmk` / `xelatex` ($rc=0$), tipografía institucional UANL, aparato crítico APA 7ma edición contra `algebra-lineal.bib` sin citas huérfanas, y calificación EMS $\ge 90$.

---

## 3. Entregables y Productos Verificados

### Producto 1: Reporte Técnico Académico
- **Archivo fuente:** `reporte-algebra-lineal-Actividad-5.tex` (incluye `contenido-Actividad-5.tex`)
- **Archivo compilado:** `reporte-algebra-lineal-Actividad-5.pdf`
- **Destino de entrega:** `entregas-algebra-lineal/reporte-algebra-lineal-Actividad-5.pdf`
- **Ponderación:** 15 puntos

### Producto 2: Presentación Ejecutiva Beamer 16:9
- **Archivo fuente:** `presentacion-algebra-lineal-Actividad-5.tex`
- **Archivo compilado:** `presentacion-algebra-lineal-Actividad-5.pdf`
- **Destino de entrega:** `entregas-algebra-lineal/presentacion-algebra-lineal-Actividad-5.pdf`
- **Ponderación:** 10 puntos

---

## 4. Criterios de Evaluación y Rúbrica Oficial (25 puntos)
- **Documento Escrito (15 pts):** Portada (1), Estructura (2), Análisis de datos (3), Uso del editor de ecuaciones (3), Justificación del método (3), Aplicación del método (3).
- **Video y Sustentación Beamer (10 pts):** Calidad de audio (1), Calidad de imagen (1), Volumen de voz (1), Presentación del expositor (2), Procedimiento completo sin omitir pasos (2), Solución analítica exacta (3).

---

## 5. Políticas Académicas y Éticas
- **Uso de Inteligencia Artificial:** Declaración transparente de asistencia algorítmica en nota al pie institucional ligada al cierre.
- **Integridad Científica:** Literatura científica verificable indexada en JCR/Scopus sin citas inventadas.
- **Citación:** Formato APA 7ma edición con Biber.
