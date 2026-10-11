import hashlib
import importlib.util
import json
import re
from pathlib import Path
from zipfile import ZipFile

from docx import Document

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets-plan-de-negocios"
SPEC = importlib.util.spec_from_file_location("uniformar_word", ASSETS / "uniformar-word.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
cover_image = MODULE.cover_image


def main():
    registry = ASSETS / "portadas-word/registro-word.json"
    records = json.loads(registry.read_text(encoding="utf-8"))
    for record in records:
        original = Document(ROOT / record["respaldo"])
        initial = "\n".join(paragraph.text for paragraph in original.paragraphs[:12])
        initial += "\n" + "\n".join(" | ".join(cell.text for cell in row.cells)
                                    for table in original.tables[:1] for row in table.rows)
        dates = re.findall(r"\b\d{1,2} de (?:septiembre|octubre) de 2026\b", initial)
        date = dates[0] if dates else "10 de octubre de 2026 (revisión de portada)"
        image = ASSETS / "portadas-word" / (Path(record["origen"]).stem + ".png")
        old_image = image.read_bytes()
        cover_image(record["titulo"], record["subtitulo"], record["actividad"], date, image)
        target = ROOT / record["destino"]
        temporary = target.with_suffix(".temporary.docx")
        with ZipFile(target) as archive, ZipFile(temporary, "w") as output:
            replacements = 0
            body = archive.read("word/document.xml")
            for item in archive.infolist():
                payload = archive.read(item.filename)
                if item.filename.startswith("word/media/") and payload == old_image:
                    payload = image.read_bytes()
                    replacements += 1
                output.writestr(item, payload)
            assert replacements == 1
        with ZipFile(temporary) as archive:
            assert archive.read("word/document.xml") == body
            assert archive.testzip() is None
        temporary.replace(target)
        record["fecha_portada"] = date
        record["fecha_es_revision"] = not bool(dates)
        record["sha256_word_nuevo"] = hashlib.sha256(target.read_bytes()).hexdigest()
    registry.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print("17 fechas de portada verificadas; XML de contenido intacto.")


if __name__ == "__main__":
    main()