# Infografía fusionada activa y versiones previas

La revisión posterior del 25/10/2026 integra las dos propuestas en [la fusión A3 activa](infografia-muestreo-fusionada.pdf), cuya [fuente editable](infografia-muestreo-fusionada.tex) reutiliza el mismo adaptador y núcleo AulaTeX. Incluye gráfica vectorial teórica, imagen conceptual, tres referencias APA y declaración de IA. Su verificación actual está en [el manifiesto de revisión](../validacion-resumen-fusion-2026-10-25.json). La fusión está incluida en el informe raíz y se utiliza para la entrega revisada.

La [ilustración](ilustracion-muestreo-administrativo.png) se generó con ImageGen integrado. El [prompt y la procedencia](imagen-procedencia.json) están disponibles. La gráfica usa `98/sqrt(n)` en puntos porcentuales: 95 %, proporción 0.5, muestreo aleatorio simple y población grande; no representa datos observados.

La lámina original TikZ y el prototipo siguiente permanecen sin cambios. Las comprobaciones de conservación de 96 archivos en `validacion-poster.json` describen el estado anterior a la nueva revisión, no los hashes actuales de los reportes.

# Póster local de Estadística: alternativa de muestra

Esta alternativa reutiliza el núcleo real `aulaTEX/base/Plantilla-Informe/template_poster.tex`.
No sustituye el PDF enviado, la lámina incluida en el informe raíz ni sus portadas.
Su fecha es el 25 de octubre de 2026 y está marcada como variante local sin envío.

## Archivos y uso

- `adaptador-poster-estadistica-itesca.tex`: adaptador reutilizable para un documento
  independiente de clase Beamer. Define A3 vertical, Arial, identidad ITESCA,
  cabecera y pie, datos del estudiante/docente y citas autor-año.
- `muestra-infografia-muestreo-alternativa.tex`: infografía de prueba con diagrama
  TikZ, diseños de selección, cálculo 385/482 y aplicaciones administrativas.
- `muestra-infografia-muestreo-alternativa.pdf`: único PDF nuevo de esta alternativa.
- `compilar_validar_poster.py`: compilación aislada, control de integridad y render.
- `conservacion-antes.json`: SHA-256 anteriores de entregas, informes y núcleo.
- `validacion-poster.json`: evidencia de tamaño, contenido, fuentes y preservación.

Desde la raíz del repositorio, después de modificar únicamente esta alternativa:

```powershell
& .\.venv\Scripts\python.exe ITESCA/maestria-en-gestion-administrativa/estadistica-aplicada-para-la-administracion-mga/assets-estadistica-aplicada-para-la-administracion/poster/compilar_validar_poster.py --build
```

Sin `--build`, solo valida el PDF existente y actualiza el render de inspección.
La salida temporal se mueve a esta carpeta; no se copia a entregas ni se sube a
Moodle. Los auxiliares se mantienen en `.build/latex/estadistica-poster-local` y
el PNG de revisión en `.build/qa-estadistica-poster`.

## Cómo hereda la plantilla

El núcleo carga `src/config`, `src/config_poster`, imports, comandos y configuración
final. Esas configuraciones usan `def` y sobrescriben valores anteriores. Por ello,
el adaptador registra `AddToHookNext{file/config_poster.tex/after}` para aplicar
valores locales después de la configuración, antes de cargar `beamerposter` y
calcular los anchos de columna. Otro hook carga Arial, natbib y TikZ después de
imports. Los hooks usan el nombre base del archivo, sin `src/`.

No se copia ni modifica el núcleo global. El adaptador utiliza el marco local
`itescaposter` con márgenes `sepwidth` y ancho útil `colwidth`. Evita así la fila
exterior de columnas vacías del entorno original, que con XeLaTeX y sus especiales
de color añadía espacios al ancho completo. La composición reutiliza el tamaño
beamerposter, la cabecera, el pie, los bloques y comandos del núcleo sin parchearlo.

El adaptador expone título, autor,
matrícula, fecha, materia, docente, anchura, altura, número de columnas y tamaño de
fuente como macros `itescaposter...`. La muestra usa un marco de ancho completo y dos
paneles interiores para combinar apertura, diagrama y cierre de anchura completa.
Es una composición Beamer independiente; no se carga dentro del article del informe.

## Dictamen de pertinencia

La plantilla de póster ofrece flujo de bloques y columnas, controles reutilizables
para logos y pie, y comandos comunes de imágenes, tablas y ecuaciones. Es útil como
base futura cuando el contenido cambie con frecuencia: evita recolocar cada párrafo
mediante coordenadas absolutas. Para una lámina ya validada, el TikZ A3 actual sigue
siendo una entrega adecuada y no existe necesidad concreta de reemplazarlo.

El ejemplo original es un póster de conferencia de 65 por 82 cm, con datos de ejemplo,
tipografía Raleway de 23 pt y referencias numéricas IEEE. La integración compartida
usa configuración general distinta, de 12 pt. Ninguno de esos valores debe trasladarse
sin adaptación a A3 o a las referencias APA de esta materia. El adaptador resuelve
estas diferencias localmente y usa datos e identidad ITESCA.

La consigna 1747 acepta PDF de formato libre, sin portada, y pide conceptos, tipos,
tamaño, aplicaciones y al menos tres fuentes APA. La muestra mantiene esos puntos.
Conserva un diagrama TikZ para dar protagonismo al producto visual y organiza tres
tiempos conceptuales mediante bloques: introducción, núcleo temático y conclusiones.
La conclusión derivada de los ejemplos aparece también de forma natural en el núcleo.

## Límites verificados

Los validadores canónicos del informe exigen tres secciones LaTeX y una lámina
original A3 de hash/render fijo. Esta alternativa tiene su propio validador y no se
registra como informe ni como reemplazo de entrega. Los comandos de sección del
núcleo compartido incorporan supuestos de article; el póster usa sus bloques nativos,
sin parchear globalmente esa capa. La estructura de tres actos del informe original
permanece intacta.

El catálogo detecta poster/póster como cartel y no registra un rol `poster` en el
selector de plantillas. Por tanto, la integración es explícita mediante el adaptador,
no una nueva selección automática. Solo se ha validado esta composición A3; cambiar
contenido, tamaño o columnas requiere render y revisión nuevamente.
