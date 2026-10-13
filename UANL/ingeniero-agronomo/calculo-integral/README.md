# Cálculo Integral — Ingeniero Agrónomo

Espacio académico de la unidad de aprendizaje **Cálculo Integral** para la carrera de Ingeniero Agrónomo de la Universidad Autónoma de Nuevo León.

## Alumno

- Diego de la Cruz.
- Matrícula, grupo y docente: por registrar.

## Organización

- `reporte-calculo-integral.tex`: portafolio maestro de la materia.
- `reporte-calculo-integral-Actividad-N.tex`: evidencia independiente por actividad.
- `calculo-integral.bib`: bibliografía común.
- `planeaciones-calculo-integral/`: consignas y documentos originales.
- `referencias-calculo-integral/`: material de consulta.
- `assets-calculo-integral/`: imágenes, gráficas y recursos propios.

Cada actividad debe resolver todos los ejercicios de su consigna, incluir una síntesis de fórmulas y procedimientos, y presentar las soluciones paso a paso en cajas de actividad AulaTeX.

## Actividades normalizadas

1. **Actividad ponderada:** integración por partes — 6 puntos.
2. **Evidencia 1:** aprendizaje basado en problemas — 20 puntos.
3. **Evidencia 2:** funciones racionales — 15 puntos.
4. **Actividad ponderada 2.2:** modelos de ganancia de peso — 6 puntos.
5. **PIA:** integrales algebraicas y racionales — 30 puntos.

Consulte `planeaciones-calculo-integral/INVENTARIO.md` para el vínculo entre consignas y documentos fuente.

## Ejecución con AulaTeX

Desde la raíz del repositorio:

```powershell
.\aulaTEX\aulatex.ps1 agent --target .\UANL\ingeniero-agronomo\calculo-integral --level materia --action realizar-actividad --activity 1 --run-extractor
```
