# Álgebra Lineal — Ingeniero Agrónomo

## Actividad disponible

- **Actividad 1 / Fase 1:** mapa cognitivo de telaraña sobre aplicaciones del álgebra lineal en la vida cotidiana.
- Fuente de la consigna: `planeaciones-algebra-lineal/EV1_guia.ppsx`.
- Entregable: `reporte-algebra-lineal-Actividad-1.pdf`.
- Modalidad indicada: equipo de 2 a 3 personas.
- Medio de entrega indicado: Nexus.
- Valor informado por la guía: 10 puntos.

## Ejecución con AulaTeX

Desde la raíz del repositorio:

```powershell
.\aulaTEX\aulatex.ps1 agent --target .\UANL\ingeniero-agronomo\algebra-lineal --level materia --action realizar-actividad --activity 1 --run-extractor
```

Para el motor inteligente con monitor:

```powershell
.\aulaTEX\aulatex.ps1 monitor-inteligente -Target '.\UANL\ingeniero-agronomo\algebra-lineal' -Activity 1 -Actions realizar-actividad -MaxTargets 1 -Engines 'Auto (model-router)' -Backend langgraph -Console
```

Los nombres de estudiantes, matrículas, grupo, docente y fechas deben completarse antes de la entrega.
