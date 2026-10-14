# Borrador y Plan de Diseño: Producto Integrador de Aprendizaje (PIA) - Álgebra Lineal (Ingeniero Agrónomo, UANL)

## 1. Portada
- **Institución:** Universidad Autónoma de Nuevo León (UANL)
- **Dependencia:** Facultad de Agronomía (FAGRO)
- **Programa Educativo:** Ingeniero Agrónomo
- **Unidad de Aprendizaje:** Álgebra Lineal
- **Actividad:** Producto Integrador de Aprendizaje (PIA) — Optimización de una Mezcla de Fertilización N-P-K para Cultivo de Maíz en Nuevo León mediante Sistemas de Ecuaciones Lineales de $3 \times 3$
- **Semestre:** Agosto – Diciembre 2026
- **Fecha de entrega:** 11 de noviembre de 2026
- **Tabla de Integrantes del Equipo (Plantilla editable para máximo 4 integrantes):**
  - Integrante 1: [Nombre Completo del Estudiante 1] | Matrícula: [Matrícula] | Grupo: [Grupo] | Carrera: Ingeniero Agrónomo
  - Integrante 2: [Nombre Completo del Estudiante 2] | Matrícula: [Matrícula] | Grupo: [Grupo] | Carrera: Ingeniero Agrónomo
  - Integrante 3: [Nombre Completo del Estudiante 3] | Matrícula: [Matrícula] | Grupo: [Grupo] | Carrera: Ingeniero Agrónomo
  - Integrante 4: [Nombre Completo del Estudiante 4] | Matrícula: [Matrícula] | Grupo: [Grupo] | Carrera: Ingeniero Agrónomo

## 2. Introducción
### 2.1. Justificación
La nutrición vegetal precisa constituye uno de los pilares estratégicos en la Ingeniería Agronómica moderna para incrementar la productividad de los agroecosistemas sin comprometer la fertilidad química del suelo ni la rentabilidad del productor (Secretaría de Agricultura y Desarrollo Rural [SADER], 2023). En el estado de Nuevo León, donde se cultivan alrededor de 34,916 hectáreas de maíz —concentradas principalmente en los municipios del sur como Galeana y Doctor Arroyo bajo condiciones de clima estepario semiseco—, el uso eficiente de los insumos agrícolas resulta determinante frente al encarecimiento internacional de los fertilizantes minerales (SADER e Instituto Nacional de Investigaciones Forestales, Agrícolas y Pecuarias [INIFAP], 2024).

Desde la perspectiva de las ciencias exactas aplicadas al perfil del Ingeniero Agrónomo de la Universidad Autónoma de Nuevo León (UANL, 2025), el Álgebra Lineal proporciona las herramientas formales para modelar problemas de mezclas y balance nutricional mediante sistemas de ecuaciones lineales simultáneas. Cuando se requiere satisfacer de manera exacta una dosis de fertilización para los tres macronutrientes primarios —Nitrógeno ($\text{N}$), Fósforo expresado como pentóxido de difósforo ($\text{P}_2\text{O}_5$) y Potasio expresado como óxido de potasio ($\text{K}_2\text{O}$)— a partir de tres fertilizantes compuestos comerciales con distintas concentraciones porcentuales, el planteamiento y resolución de un sistema lineal de $3 \times 3$ garantiza determinar la combinación única de insumos que evita tanto subdosificaciones (que limitan el rendimiento) como sobredosificaciones (que provocan lixiviación, salinización edáfica y pérdidas económicas).

### 2.2. Planteamiento del problema
En una unidad de producción agrícola dedicada al cultivo de maíz bajo riego de auxilio en el municipio de Galeana, Nuevo León, el diagnóstico de fertilidad edáfica y la meta de rendimiento establecen un requerimiento nutricional neto por hectárea de **$99\text{ kg de Nitrógeno (N)}$**, **$83\text{ kg de Fósforo (P}_2\text{O}_5\text{)}$** y **$84\text{ kg de Potasio (K}_2\text{O)}$**.

El almacén técnico de la unidad de producción dispone de tres fórmulas de fertilizantes compuestos ternarios ($\text{N-P-K}$) de uso comercial (Área de Agronomía, 2024):
1. **Fórmula A (Complejo Arrancador 12-24-12):** contiene $12\%$ de $\text{N}$, $24\%$ de $\text{P}_2\text{O}_5$ y $12\%$ de $\text{K}_2\text{O}$.
2. **Fórmula B (Complejo de Desarrollo 20-10-10):** contiene $20\%$ de $\text{N}$, $10\%$ de $\text{P}_2\text{O}_5$ y $10\%$ de $\text{K}_2\text{O}$.
3. **Fórmula C (Complejo de Llenado de Grano 15-05-30):** contiene $15\%$ de $\text{N}$, $5\%$ de $\text{P}_2\text{O}_5$ y $30\%$ de $\text{K}_2\text{O}$.

**Pregunta de investigación:** ¿Cuántos kilogramos por hectárea de cada fertilizante compuesto ($x_1, x_2, x_3$) deben mezclarse y aplicarse en el ciclo agrícola para cubrir exactamente la demanda de $99\text{ kg/ha de N}$, $83\text{ kg/ha de P}_2\text{O}_5$ y $84\text{ kg/ha de K}_2\text{O}$ sin excedentes ni déficits nutricionales?

## 3. Recolección de datos
La recolección de datos se realizó mediante revisión documental de fichas técnicas de fertilizantes minerales (Área de Agronomía, 2024) y paquetes tecnológicos publicados por SADER e INIFAP (2024) para el cultivo de maíz en Nuevo León:
- **Contexto agroecológico regional:** Superficie estatal sembrada de maíz de $34,916\text{ ha}$ ($22,000\text{ ha}$ en Galeana y Doctor Arroyo), precipitación media de $650\text{ mm}$ y temperatura media anual de $20\,^\circ\text{C}$ (SADER & INIFAP, 2024).
- **Tabla de composición nutrimental de los insumos y requerimiento por hectárea:**
  - Nutriente N: Fórmula A = 12% (0.12 kg/kg), Fórmula B = 20% (0.20 kg/kg), Fórmula C = 15% (0.15 kg/kg) -> Meta: 99 kg/ha.
  - Nutriente P2O5: Fórmula A = 24% (0.24 kg/kg), Fórmula B = 10% (0.10 kg/kg), Fórmula C = 5% (0.05 kg/kg) -> Meta: 83 kg/ha.
  - Nutriente K2O: Fórmula A = 12% (0.12 kg/kg), Fórmula B = 10% (0.10 kg/kg), Fórmula C = 30% (0.30 kg/kg) -> Meta: 84 kg/ha.

## 4. Metodología
### 4.1. Planteamiento del sistema de ecuaciones
Definición de las incógnitas del sistema:
- $x_1$: Cantidad requerida del fertilizante compuesto **Fórmula A (12-24-12)** en $\text{kg/ha}$.
- $x_2$: Cantidad requerida del fertilizante compuesto **Fórmula B (20-10-10)** en $\text{kg/ha}$.
- $x_3$: Cantidad requerida del fertilizante compuesto **Fórmula C (15-05-30)** en $\text{kg/ha}$.

Sistema expresado en proporciones másicas ($\text{kg}$ de nutriente por $\text{kg}$ de fertilizante):
$$0.12\,x_1 + 0.20\,x_2 + 0.15\,x_3 = 99$$
$$0.24\,x_1 + 0.10\,x_2 + 0.05\,x_3 = 83$$
$$0.12\,x_1 + 0.10\,x_2 + 0.30\,x_3 = 84$$

Multiplicando cada ecuación por $100$ para trabajar con coeficientes enteros exactos:
$$12\,x_1 + 20\,x_2 + 15\,x_3 = 9900$$
$$24\,x_1 + 10\,x_2 + 5\,x_3 = 8300$$
$$12\,x_1 + 10\,x_2 + 30\,x_3 = 8400$$

Representación matricial $A\mathbf{x} = \mathbf{b}$ y matriz aumentada $[A \mid \mathbf{b}]$.

### 4.2. Justificación del método visto en clase que se usará en la solución
Se seleccionó como método principal la **Eliminación de Gauss-Jordan** y como método de verificación la **Regla de Cramer** (Grossman & Flores Godoy, 2012):
1. **Exactitud y reducción escalonada reducida:** El método de Gauss-Jordan transforma la matriz aumentada $[A \mid \mathbf{b}]$ en su forma escalonada reducida por renglones $[I_3 \mid \mathbf{x}]$ mediante operaciones elementales de renglón, permitiendo leer directamente los valores únicos de $x_1, x_2, x_3$ sin necesidad de sustitución regresiva.
2. **Estabilidad aritmética y claridad expositiva:** Al escalar el sistema a coeficientes enteros donde la primera columna contiene múltiplos directos ($12, 24, 12$), las operaciones elementales de eliminación producen múltiplos enteros exactos en cada etapa, facilitando tanto el desarrollo escrito como la explicación paso a paso en pizarrón para el video integrador.
3. **Criterio de existencia y unicidad mediante el determinante (Regla de Cramer):** El cálculo del determinante del sistema ($\Delta = \det(A) = -8400 \neq 0$) demuestra formalmente que las tres ecuaciones son linealmente independientes y que existe una solución única en el espacio $\mathbb{R}^3$.

## 5. Procedimientos
### 5.1. Solución paso a paso del sistema (Eliminación de Gauss-Jordan y verificación por Regla de Cramer)
Desarrollo detallado de las 6 etapas de operaciones por renglón sobre la matriz aumentada hasta obtener $x_1 = 200$, $x_2 = 300$, $x_3 = 100$, seguido de la verificación por determinantes de $3 \times 3$ (Regla de Cramer) y la comprobación algebraica por sustitución directa en las 3 ecuaciones.

### 5.2. Herramientas utilizadas para elaborar el proyecto
- **Microsoft Word y Editor de Ecuaciones nativo (OMML):** Redacción digital 100% conforme a la rúbrica y normativa APA 7.ª edición, empleando bloques matemáticos nativos para matrices, determinantes y sistemas lineales.
- **Python 3 (`numpy` y `matplotlib`):** Validación computacional de la solución matricial y generación de gráficos de barras apiladas del aporte nutricional.
- **Fuentes técnicas oficiales (SADER, INIFAP, UANL):** Consulta de paquetes tecnológicos regionales y manuales agronómicos de cálculo de fertilización.

## 6. Resultados
- $x_1 = 200\text{ kg/ha}$ de Fórmula A (12-24-12), equivalentes a $4\text{ bultos de } 50\text{ kg}$.
- $x_2 = 300\text{ kg/ha}$ de Fórmula B (20-10-10), equivalentes a $6\text{ bultos de } 50\text{ kg}$.
- $x_3 = 100\text{ kg/ha}$ de Fórmula C (15-05-30), equivalentes a $2\text{ bultos de } 50\text{ kg}$.
- Mezcla física total: $600\text{ kg/ha}$ ($12\text{ bultos de } 50\text{ kg/ha}$).
- Tabla de desglose de aporte nutricional y gráfica comparativa.

## 7. Análisis de resultados
Interpretación agronómica detallada del aporte porcentual de cada insumo y recomendaciones de aplicación fraccionada (50% del N y 100% de P y K en la siembra; 50% restante del N en la escarda en etapa V5-V6 conforme a SADER & INIFAP, 2024).

## 8. Conclusión
Conclusiones técnicas sobre la utilidad del Álgebra Lineal en la Ingeniería Agronómica.

## 9. Referencias (Normativa APA 7.ª edición)
Referencias bibliográficas completas con enlaces verificados.

## 10. Enlace al Video y Guía de Exposición para el Equipo
- Campo destacado para insertar el enlace público del video para la entrega en Nexus.
- Estructura sugerida de exposición paso a paso sin acordeón para los integrantes del equipo.

## Design Plan (Word .docx & PDF)
- **Document Archetype:** Academic & Technical Report (APA 7th Edition compliant structure with clean academic formatting, formal cover page, native OMML equations in `.docx`, and clean continuous flow in `.pdf`).
- **Palette:**
  - `--primary`: `#1B4332` (Deep Agronomic Forest Green)
  - `--accent`: `#2D6A4F` (Botanical Emerald Green)
  - `--light-fill`: `#F0F7F4` (Soft Mint Tint for alternating table rows)
  - `--text`: `#1F2937` (Charcoal Slate for high WCAG contrast)
  - `--bg`: `#FFFFFF` (Crisp White page background)
- **Typography:**
  - Word (`.docx`): `Calibri` / `Cambria Math` (11pt body, 16pt H1, 13pt H2, 22pt Title, 10pt–10.5pt Tables, 1.15–1.5 line spacing, 1-inch margins).
  - PDF (`.pdf`): `'Merriweather'` / `'Liberation Serif'` display headings + `'Inter'` / `'Liberation Sans'` body text (10.5pt body, 1.6 line-height, A4/Letter with 22mm/20mm margins).
- **Visual Assets:**
  - High-resolution Matplotlib chart (`balance_nutricional_npk.png`, 300 DPI) showing the exact contribution of Formulas A, B, and C to the N, P2O5, and K2O targets.
