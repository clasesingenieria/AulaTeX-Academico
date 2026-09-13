"""Actualiza el índice con el motor de paginación de LibreOffice y exporta.

Requiere LibreOffice escuchando exclusivamente en localhost:20106 y python3-uno.
El DOCX final conserva un campo TOC editable; el PDF es solo control visual.
"""

from pathlib import Path
import json
import sys

# Puente UNO de la instalación de LibreOffice del sistema (CPython 3.12).
sys.path.append("/usr/lib/python3/dist-packages")
import uno  # type: ignore[import-not-found]  # noqa: E402


ROOT = Path(__file__).resolve().parent
COURSE = ROOT.parent
NAME = "Tarea6_DeLaCruzMunoz.docx"


def prop(name, value):
    item = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    item.Name, item.Value = name, value
    return item


def main():
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    context = resolver.resolve("uno:socket,host=localhost,port=20106;urp;StarOffice.ComponentContext")
    desktop = context.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", context)
    document = desktop.loadComponentFromURL(
        uno.systemPathToFileUrl(str(ROOT / "construccion" / NAME)), "_blank", 0,
        (prop("Hidden", True), prop("UpdateDocMode", 3), prop("ReadOnly", False)),
    )
    assert document is not None, "No se pudo cargar el Word"
    try:
        indexes = document.getDocumentIndexes()
        assert indexes.Count == 1, f"Se esperaba un índice, se encontraron {indexes.Count}"
        index = indexes.getByIndex(0)
        index.Level = 3
        styles = document.StyleFamilies.getByName("ParagraphStyles")
        for level in (1, 2, 3):
            style = styles.getByName(f"Contents {level}")
            style.CharFontName = "Arial"
            style.CharHeight = 11.0
            style.CharColor = 0
            style.ParaLeftMargin = (level - 1) * 635
            style.ParaFirstLineIndent = 0
            style.ParaTopMargin = style.ParaBottomMargin = 0
            spacing = uno.createUnoStruct("com.sun.star.style.LineSpacing")
            spacing.Mode = 0
            spacing.Height = 200
            style.ParaLineSpacing = spacing
        for _ in range(3):
            document.refresh()
            index.update()
            document.getTextFields().refresh()
        destination = COURSE / "entregas" / NAME
        destination.parent.mkdir(parents=True, exist_ok=True)
        validation = ROOT / "validacion"
        validation.mkdir(parents=True, exist_ok=True)
        document.storeAsURL(uno.systemPathToFileUrl(str(destination)),
                            (prop("FilterName", "Office Open XML Text"), prop("Overwrite", True)))
        pdf = validation / "Tarea6_DeLaCruzMunoz_revision.pdf"
        document.storeToURL(uno.systemPathToFileUrl(str(pdf)),
                            (prop("FilterName", "writer_pdf_Export"), prop("Overwrite", True)))
        cursor = document.getCurrentController().getViewCursor()
        cursor.jumpToLastPage()
        report = {"motor": "LibreOffice Writer 24.2", "paginas": cursor.getPage(),
                  "indices": indexes.Count, "niveles_indice": index.Level,
                  "docx": str(destination.relative_to(COURSE)),
                  "pdf_revision": str(pdf.relative_to(COURSE)),
                  "indice_visible": index.Anchor.String}
        (validation / "paginacion.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(f"DOCX final: {destination}\nPDF de revisión: {pdf}\nPáginas: {report['paginas']}")
    finally:
        document.close(True)


if __name__ == "__main__":
    main()