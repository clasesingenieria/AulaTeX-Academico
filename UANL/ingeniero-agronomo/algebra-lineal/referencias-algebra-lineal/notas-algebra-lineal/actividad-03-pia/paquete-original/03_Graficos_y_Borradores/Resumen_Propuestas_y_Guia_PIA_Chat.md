# Resumen General del Proyecto Integrador de Aprendizaje (PIA) — Álgebra Lineal (UANL Agronomía)

## 1. Contenido de este Paquete Comprimido (.zip)
1. **`01_Indicaciones_Originales/PIA_Algebra_Lineal_EJ26.pdf`**: Archivo PDF original con las indicaciones y rúbrica oficial de la asignatura (15 puntos reporte escrito + 10 puntos video).
2. **`02_Entregables_Finales/Reporte_PIA_Algebra_Lineal_Agronomia_UANL.docx`**: Reporte escrito 100% editable en Microsoft Word con todas las ecuaciones elaboradas en el Editor de Ecuaciones nativo (OMML), tablas en formato APA 7.ª edición, referencias con enlaces verificados y anexo para el enlace del video.
3. **`02_Entregables_Finales/Reporte_PIA_Algebra_Lineal_Agronomia_UANL.pdf`**: Versión final en PDF lista para entrega en la plataforma Nexus.
4. **`03_Graficos_y_Borradores/balance_nutricional_npk.png`**: Gráfica en alta resolución (300 DPI) de la dosis óptima por fertilizante comercial y el aporte apilado de N, P₂O₅ y K₂O.
5. **`03_Graficos_y_Borradores/Borrador_y_Plan_PIA.md`**: Borrador estructurado con el planteamiento completo y plan de diseño del documento.
6. **`04_Codigo_y_Plantillas/document.html`**, **`generate_chart.py`**, **`build_docx.py`**: Scripts de verificación matemática con NumPy, generación de gráficas con Matplotlib y construcción automatizada de los documentos.

## 2. Propuestas de Problemas Agronómicos Analizadas en el Chat
| Caso de aplicación | Variables (x₁, x₂, x₃) | Restricciones del sistema (3 × 3) | Contexto agronómico regional |
| :--- | :--- | :--- | :--- |
| **1. Mezcla balanceada de fertilizantes N-P-K (Desarrollada en el Reporte)** | Kilogramos por hectárea de Fórmula A (12-24-12), Fórmula B (20-10-10) y Fórmula C (15-05-30) | Demanda neta de 99 kg/ha de N, 83 kg/ha de P₂O₅ y 84 kg/ha de K₂O | Nutrición de maíz en Galeana y Doctor Arroyo, Nuevo León |
| **2. Balanceo de ración forrajera para ganado bovino** | Kilogramos diarios de heno de alfalfa, maíz molido y pasta de soya | Requerimientos diarios de Proteína Cruda (PC), Energía Neta (EN) y Fibra (FDN) | Suplementación bovina en pastoreo semiárido |
| **3. Planificación de siembra y uso eficiente de agua** | Hectáreas asignadas a sorgo, maíz forrajero y alfalfa | Límite de volumen de riego (m³), horas de maquinaria y presupuesto operativo | Optimización hídrica en distritos de riego del norte de México |

## 3. Síntesis del Sistema Resuelto en el Reporte
- **Sistema en proporción decimal:**
  - `0.12 x₁ + 0.20 x₂ + 0.15 x₃ = 99`  (Balance de Nitrógeno N)
  - `0.24 x₁ + 0.10 x₂ + 0.05 x₃ = 83`  (Balance de Fósforo P₂O₅)
  - `0.12 x₁ + 0.10 x₂ + 0.30 x₃ = 84`  (Balance de Potasio K₂O)
- **Sistema entero equivalente (multiplicado por 100):**
  - `12 x₁ + 20 x₂ + 15 x₃ = 9900`
  - `24 x₁ + 10 x₂ +  5 x₃ = 8300`
  - `12 x₁ + 10 x₂ + 30 x₃ = 8400`
- **Solución única (por Eliminación de Gauss-Jordan y Regla de Cramer con Δ = -8400):**
  - `x₁ = 200 kg/ha` de Fórmula A (12-24-12) → **4 bultos de 50 kg**
  - `x₂ = 300 kg/ha` de Fórmula B (20-10-10) → **6 bultos de 50 kg**
  - `x₃ = 100 kg/ha` de Fórmula C (15-05-30) → **2 bultos de 50 kg**
  - **Total de la mezcla:** `600 kg/ha` (**12 bultos de 50 kg**).
