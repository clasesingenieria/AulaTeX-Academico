# Control editorial: Evidencia 2.6

- [Fuente del reporte](../../../reporte-algebra-lineal-Evidencia-2-6.tex).
- [PDF digital](../../../reporte-algebra-lineal-Evidencia-2-6.pdf).
- [Contrato docente](../../../planeaciones-algebra-lineal/consigna-Evidencia-2-6.md).
- [Guia EV2 de Nexus](recursos-nexus/EV2_%20guia.ppsx).
- [Metodologia de Nexus](recursos-nexus/Metodologia.pdf).
- [Inventario de originales SHA-256](inventario-recursos-nexus.csv).
- [Hoja docente con el Sistema 11](Problemas%20evidencia%202%20AL%20AD26.pdf), aportada desde Downloads/Telegram Desktop el 22 de octubre de 2026; SHA-256 `921ed6afeb18634afb55dffd3040408364ae84328c2be31b8d0e135fd28cc169`.

Los originales se movieron a estas notas por solicitud del usuario, sin
modificar sus nombres o contenido. La consigna resumida sigue en planeaciones.
La guia y metodologia son instrucciones docentes, no autoridad matematica;
no se citan chats, borradores o reportes anteriores en la bibliografia.

## Referencias verificadas

Consulta web: 20 de octubre de 2026.

- `strang2016`, *Introduction to Linear Algebra*: la pagina del autor en
  https://math.mit.edu/~gs/linearalgebra/ confirma la quinta edicion de 2016.
  La entrada ya existe en la bibliografia local. Se usa para sistemas,
  operaciones elementales e invertibilidad; no se declara una nueva lectura
  completa del libro ni se le atribuyen las cifras del caso.

La referencia UMN usada por el caso provisional N-P-K permanece en la
bibliografia de la materia, pero no se cita ni se imprime en este reporte.

Las referencias se imprimen con BibLaTeX APA/Biber desde la bibliografia
local. El enunciado del Sistema 11 se conserva en notas como consigna,
no se usa como autoridad teorica ni se le inventa un contexto agronomico.

## Verificacion matematica

Matriz `[[-4,2,6],[10,3,2],[-9,-7,10]]`, vector `[-6,-6,-7]`.
Solucion exacta `[-103,-74,-379]/335`. Comprobacion independiente
en PowerShell: determinante `-670`; determinantes de Cramer `[206,148,758]`;
tres residuos exactamente cero. Gauss-Jordan conserva fracciones exactas.

El mapa tiene siete pasos en dos columnas, procedimiento y ejemplo
matematico, enlazados mediante flechas. La conclusion interpreta la
interseccion unica de tres planos y explica por que los valores negativos
son validos: el enunciado no establece unidades ni no negatividad.

Verificacion final: compilacion latexmk/Biber completada sin advertencias,
desbordamientos ni caracteres perdidos. Portada y mapa revisados en imagen
renderizada del PDF; se revisa nuevamente tras sustituir el caso por el
Sistema 11. Los recursos Nexus y la hoja docente conservan sus huellas.
Este control acredita el desarrollo digital, no un manuscrito ni un envio.

## Alcance de aceptacion

El reporte digital usa la plantilla institucional, identidad del estudiante,
ecuaciones nativas y referencias APA. La hoja docente fue recibida y el
Sistema 11 se cotejo con la primera pagina. Se sustituyo completamente el
caso provisional N-P-K. No se acredita cumplimiento total de la rubrica docente.
Manuscrito, escaneo y envio quedan a cargo del usuario por instruccion expresa.
No se simula escritura ni se publica nada en Nexus.

El PDF digital permanece en la raiz como producto editorial. La carpeta
entregas-algebra-lineal se reserva para el escaneo que el usuario seleccione
finalmente. Fecha de la hoja: 16 de octubre de 2026. Fecha observada en
Nexus el 20 de octubre: 23 de octubre de 2026 a las 23:42. Conservar ambas
como discrepancia; confirmar el plazo con el profesor, sin asumir prorroga.

## Compilacion

```powershell
.\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\algebra-lineal\reporte-algebra-lineal-Evidencia-2-6.tex -CleanMode none
```

Ejecutar desde la raiz. Hook local `file/config.tex/after` para bibliografia
custom; BibLaTeX APA/Biber; TikZ con babel. Auxiliares en `.build/latex`.