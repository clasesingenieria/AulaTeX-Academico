# Plantilla local de preparación UAdeC

[reporte-uadec.tex](reporte-uadec.tex) es el preámbulo compartido por los ocho reportes de preparación. No es un formato institucional aprobado.

Cada reporte define `\uadectitulo`, carga el preámbulo desde la raíz del repositorio y llama `\portadaUAdeC` después de `\begin{document}`. Reutiliza tipografía de 12 puntos, tamaño carta, márgenes de 2,5 cm, interlineado 1,5 y soporte de tablas, fórmulas y esquemas TikZ. No incluye marcas de otra universidad ni datos personales supuestos.

Compilación desde la raíz: `./aulaTEX/latexmk-build.ps1 'UAdeC/medico-cirujano/<area>/reporte-<area>.tex'`.

La carpeta anterior `plantilla` se conserva como recurso genérico histórico de Informe LaTeX; sus logos y ejemplos no deben usarse como identidad UAdeC. Se conservan su licencia y atribuciones originales.