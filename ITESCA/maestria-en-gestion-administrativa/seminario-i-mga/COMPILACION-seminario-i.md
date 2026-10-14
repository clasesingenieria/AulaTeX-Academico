# Compilación y contrato de Seminario I

Ejecutar desde la raíz del repositorio:

```powershell
& .\aulaTEX\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\seminario-i-mga\reporte-seminario-i-Actividad-12.tex -CleanMode none
```

## Cadena efectiva

1. [Reporte de actividad en raíz](reporte-seminario-i-Actividad-12.tex): representación íntegra del anteproyecto acumulativo de Entregas; conserva capítulos, referencias y anexos. No es un resumen auxiliar.
2. [Adaptador de materia](reporte-seminario-i-plantilla-actividad.tex): curso GGS102, estudiante, docente, MGA, periodo y contenido. No declara clase ni abre un documento independiente.
3. [Maestra MGA](../reporte-itesca-mga.tex): clase, identidad institucional ITESCA, portada, marca de agua, pie, estilo y ciclo del documento.
4. Núcleo compartido `aulaTEX/base/Plantilla-Informe/template.tex`, resuelto por la configuración LaTeX del repositorio. El registro FLS confirma que esta es la copia utilizada.

La maestra MGA reúne carrera e identidad institucional; no se duplicó su diseño en Seminario I ni se alteró la maestra compartida. La entrada de assets conserva compatibilidad y sólo delega en el adaptador de raíz. La configuración final se ejecuta una vez en la maestra; repetirla desde el adaptador provocaba bloqueo y fue corregido.

## Separación de productos

- Raíz: fuente y PDF del mismo anteproyecto acumulativo T12; 25 páginas con maquetación institucional LaTeX.
- Entregas: Word acumulativo T12, 31 páginas, requerido por la consigna; PDF de consulta del mismo Word. La diferencia de páginas corresponde al formato, no a una reducción del cuerpo o de los anexos.
- Notas de T12: consulta, revisión de fuentes, scripts, respaldos y evidencias. El respaldo anterior no es entrega vigente.

## Validación realizada

T12 compiló sin desbordamientos; portada identifica actividad, curso, matrícula, docente y fecha. El FLS incluye adaptador, maestra y núcleo. T11 se compiló por la entrada compatible en `.build/latex/validacion-seminario`, sin publicar encima del PDF anterior. El Word T12 no cambió (SHA-256 92769b873c325c393f52ebe640152a1120c8eec712341d3f666e222b8edfc930).

Esto valida T12 y una entrada anterior de la misma interfaz, no certifica la migración de todos los reportes autocontenidos de la materia. No se realizó envío a Moodle.

## Sincronización de contenido

El Word es la fuente del anteproyecto acumulativo. [Conversor estructurado](referencias-seminario-i/notas-seminario-i/actividad-12-hipotesis/sincronizar_reporte_t12.py): genera el reporte de raíz sin resumir sus párrafos y respeta el orden de las tres tablas, incluidas celdas combinadas. El auxiliar anterior se conserva en notas como histórico, no vigente.

```powershell
& .\.venv\Scripts\python.exe .\ITESCA\maestria-en-gestion-administrativa\seminario-i-mga\referencias-seminario-i\notas-seminario-i\actividad-12-hipotesis\sincronizar_reporte_t12.py
& .\aulaTEX\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\seminario-i-mga\reporte-seminario-i-Actividad-12.tex -CleanMode none
```

Cotejo final: 130 párrafos y tres tablas íntegros en el PDF de raíz. Se excluyeron encabezados/pies del cotejo y se normalizaron ligaduras, acentos separados y guiones de maquetación. No se alteró el Word. Los encabezados futuros vacíos de capítulos 6--9 se conservan como en la entrega; no se inventó contenido para completarlos. Portadas e índices se maquetan en cada formato. No se agregó un resumen o una conclusión ajenos al documento original.