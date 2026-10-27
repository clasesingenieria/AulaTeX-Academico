"""Publish S1 reports and trace the user's lesson records without submitting."""
from pathlib import Path
import hashlib
import json
import re
import shutil

import pymupdf
from PIL import Image
from io import BytesIO


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    subject = root / "UAS/licenciatura-en-contaduria-uas/herramientas-digitales"
    notes = subject / "referencias-herramientas-digitales/notas-herramientas-digitales/semana-01"
    notes.mkdir(exist_ok=True)
    deliveries = subject / "entregas-herramientas-digitales"
    folder_pdf = deliveries / "S1_MartinJonathanDeLaCruzMunoz.pdf"
    folder_hash = digest(folder_pdf)
    sources = []
    for filename in ["Lecciones S1.md.txt", "Lecciones S1.md - Justificación.txt"]:
        original = subject / filename
        target = notes / filename
        if target.exists():
            assert digest(target) == digest(original)
        else:
            shutil.copy2(original, target)
        sources.append({"path":target.relative_to(subject).as_posix(),"sha256":digest(target)})
    source = (subject / "Lecciones S1.md - Justificación.txt").read_text(encoding="utf-8-sig")
    blocks = re.split(r"(?m)^(?=\d+\. )", source)
    questions = []
    for block in blocks:
        number = re.match(r"(\d+)\. ", block)
        if not number:
            continue
        answer = re.search(r"(?m)^\s*Respuesta:\s*(.+)$", block)
        questions.append({"number":int(number.group(1)),"lesson_id":50100 if int(number.group(1)) <= 10 else 50101,"assignment_basis":"Agrupacion tematica local, no identificador de pregunta Moodle","answer":answer.group(1) if answer else None,"original_block":block.strip()})
    assert len(questions) == 43
    activities = []
    names = {1:"Leccion-1-TIC-S1_MartinJonathanDeLaCruzMunoz.pdf",2:"Leccion-2-Topicos-TIC-S1_MartinJonathanDeLaCruzMunoz.pdf",3:folder_pdf.name,4:"Examen-Teorico-S1_MartinJonathanDeLaCruzMunoz.pdf"}
    for number, module in [(1,50100),(2,50101),(3,50102),(4,50103)]:
        name = f"reporte-herramientas-digitales-Actividad-{number}"
        compiled = root / ".build/latex/uas-herramientas-reporte" / (name + ".pdf")
        report = subject / (name + ".pdf")
        shutil.copy2(compiled, report)
        if number != 3:
            shutil.copy2(report, deliveries / names[number])
        with pymupdf.open(report) as document:
            assert all(page.get_text().strip() for page in document)
            text = " ".join(page.get_text() for page in document)
            assert "26031061" in text and "Dámaso Ruiz Gonzáles" in text
            assert "Por confirmar" not in text
            assert all(term in text for term in ["Resumen","Introducción","Conclusiones","Referencias"])
            pages = len(document)
            preview = root / ".build/latex/uas-herramientas-reporte/revision-S1"
            tiles = []
            for page in document:
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(.5,.5), alpha=False)
                tiles.append(Image.open(BytesIO(pixmap.tobytes("png"))))
            columns = 4
            rows = (len(tiles) + columns - 1) // columns
            sheet = Image.new("RGB", (tiles[0].width * columns, tiles[0].height * rows), "white")
            for position, tile in enumerate(tiles):
                sheet.paste(tile, ((position % columns) * tile.width, (position // columns) * tile.height))
            sheet.save(preview / f"reporte-{number}-revision.png")
        activities.append({"activity":number,"module":module,"report_tex":name+'.tex',"report_pdf":report.name,"deliverable":"entregas-herramientas-digitales/"+names[number],"deliverable_sha256":digest(deliveries/names[number]),"pages":pages,"generated_submission":False})
    assert folder_hash == digest(folder_pdf), "Existing S1 deliverable changed"
    contract = {"course_id":635,"sources":sources,"questions":questions,"activities":activities,"grades_from_user_screenshot":{"50100":{"grade":1.33,"maximum":2},"50101":{"grade":4.50,"maximum":5},"50103":{"grade":10,"maximum":10}},"platform_changed":False,"folder_deliverable_preserved":True,"remaining_scope":["Leccion nube 50107: estado no acreditado","Diagnostico 50085: estado no acreditado","Archivo remoto 50102 distinto del PDF local en ultima comprobacion" ]}
    (notes / "contrato-semana-01.json").write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"reports":len(activities),"lesson_records":len(questions),"S1_preserved":True,"pages":[item['pages'] for item in activities]},ensure_ascii=True))


if __name__ == "__main__":
    main()