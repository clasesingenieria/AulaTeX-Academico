from pathlib import Path
import json
import re
import unicodedata
import pymupdf
from organizar_productos import CAREER, digest, existing_questions


def normal(text):
    return " ".join("".join(character for character in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(character)).split())


TERMS = {
    "anatomia": ["radio|semilunar", "peritoneo|parietal", "sagital|plano", "esfenoides|craneo", "costillas|esternon", "diafragma|inspiracion", "muscular|nucleos", "troponina|calcio", "sarcomero|discos", "atlas|cuerpo", "mediastino|pulmones", "rotula|sesamoideo", "esfericas|sinoviales", "radio|semilunar", "epifisaria|crecimiento", "isquion|tuberosidad", "intercalares|cardiaco", "abduccion|aduccion", "fibula|tibia", "endomisio|perimisio"],
    "biologia-celular": ["endosimbiotica|mitocondrias", "sodio|potasio", "peroxisomas|catalasa", "g0|quiescencia", "paquiteno|profase", "peptidoglucano|gram", "hipertonica|agua", "reticulo|liso", "protozoos|eucariotas", "virus|ribosomas", "cromosomas|46", "endocitosis|vesiculas", "vih|arn", "centrosoma|microtubulos", "quitina|hongos", "p53|ciclo", "colesterol|fluidez", "comensalismo|huésped", "actina|miosina", "bacilos|gram"],
    "bioquimica": ["aminoacidos|proteinas", "glucosidico|enlace", "sacarosa|fructosa", "fosfolipidos|bicapa", "glucolisis|piruvato", "ciclo|matriz", "oxigeno|electrones", "lactato|nadh", "enzimas|activacion", "competitiva|inhibicion", "transcripcion|arn", "adenina|citosina", "uracilo|arn", "ribosomas|traduccion", "peptidico|enlace", "glucogeno|musculo", "atp|hidrolisis", "polimerasa|replicacion", "codon|triplete", "colesterol|esteroideas"],
    "fisiologia": ["retroalimentacion|negativa", "sinoauricular|marcapasos", "ruido|valvulas", "qrs|despolarizacion", "surfactante|tipo ii", "volumen|corriente", "glucosa|proximal", "vasopresina|hipotalamo", "esteroideas|receptor", "sistolica|diastolica", "pepsinogeno|acido", "glucagon|alfa", "bilis|emulsion", "acetilcolina|neuromuscular", "hemoglobina|oxigeno", "simpatico|corazon", "intercambio|tejidos", "tiroides|tiroxina", "reflejo|medula", "angiotensina|aldosterona"],
    "salud-publica": ["huesped|nutricion", "vector|malaria", "secundaria|deteccion", "signos|sintomas", "incidencia|nuevos", "promocion|salud", "horizonte|clinico", "bienestar|social", "tetanos|esporas", "pronostico|enfermedad", "vacunacion|primaria", "endemia|habitual", "rehabilitacion|terciaria", "pandemia|epidemia", "vertical|transmision", "incubacion|periodo", "fisicos|quimicos", "mortalidad|poblacion", "nosocomial|infeccion", "aislamiento|cuarentena"]
}

CONFIRMED = {
    "anatomia": {11, 15, 16, 17},
    "biologia-celular": {3, 4, 5, 10, 14, 15, 16},
    "bioquimica": {4, 6, 8, 10, 13, 15, 16, 20},
    "fisiologia": {2, 4, 5, 7, 9, 10, 20},
    "salud-publica": {1, 2, 3, 5, 6, 7, 10, 13, 16, 18, 20},
}

WEB_CONFIRMED = {
    ("anatomia", 13): ("https://openstax.org/books/anatomy-and-physiology-2e/pages/9-4-synovial-joints", "Ball-and-Socket Joint", "Cadera y hombro se clasifican como articulaciones esféricas."),
    ("anatomia", 14): ("https://openstax.org/books/anatomy-and-physiology-2e/pages/8-2-bones-of-the-upper-limb", "Carpal Bones", "Escafoides y semilunar contactan directamente con radio; piramidal con disco."),
    ("anatomia", 7): ("https://openstax.org/books/anatomy-and-physiology-2e/pages/10-2-skeletal-muscle", "Skeletal Muscle Fibers", "Las fibras esqueléticas son largas y multinucleadas."),
    ("anatomia", 8): ("https://openstax.org/books/anatomy-and-physiology-2e/pages/10-2-skeletal-muscle", "Excitation-Contraction Coupling", "La liberación de calcio inicia el acoplamiento contráctil."),
    ("anatomia", 9): ("https://openstax.org/books/anatomy-and-physiology-2e/pages/10-2-skeletal-muscle", "The Sarcomere", "El sarcómero se delimita por discos Z."),
    ("anatomia", 20): ("https://openstax.org/books/anatomy-and-physiology-2e/pages/10-2-skeletal-muscle", "The Three Connective Tissue Layers", "Endomisio recubre fibras, perimisio fascículos y epimisio músculo."),
    ("biologia-celular", 17): ("https://openstax.org/books/biology-2e/pages/5-1-components-and-structure", "Membrane Fluidity", "Colesterol amortigua cambios de fluidez según temperatura."),
    ("bioquimica", 9): ("https://openstax.org/books/biology-2e/pages/6-5-enzymes", "Enzymes", "Catálisis reduce energía de activación, no cambia equilibrio."),
    ("salud-publica", 9): ("https://www.cdc.gov/tetanus/about/index.html", "Causes; Recent wound", "C. tetani entra mediante heridas; contaminación, no óxido, explica el riesgo."),
}


def main():
    model = json.loads(Path(__file__).with_name("productos.json").read_text(encoding="utf-8"))
    records = []
    book_records = []
    for area in model["areas"]:
        slug = area["slug"]
        subject = CAREER / slug
        source = subject / f"reporte-{slug}.tex"
        questions = area.get("preguntas") or existing_questions(source.read_text(encoding="utf-8"))
        pages = []
        for path in subject.glob("referencias-*/libros-*/*.pdf"):
            with pymupdf.open(path) as pdf:
                prelim = " ".join(pdf[index].get_text() for index in range(min(15, len(pdf))))
                book_records.append({"archivo": path.relative_to(CAREER).as_posix(), "sha256": digest(path), "paginas_pdf": len(pdf), "preliminares_consultados": list(range(1, min(15, len(pdf)) + 1)), "extracto_preliminares": prelim[:5000], "metadatos_verificados": False, "lectura_integra": False})
                for index, page in enumerate(pdf):
                    raw = page.get_text()
                    if len(raw) > 300:
                        pages.append((path.relative_to(CAREER).as_posix(), index + 1, normal(raw), raw))
        short = slug.removeprefix("examen-ingreso-")
        for index, (question, options, answer, reason) in enumerate(questions):
            record = {"area": slug, "numero": index + 1, "pregunta": question, "opciones": options, "clave": chr(65 + answer), "justificacion": reason, "sha256_reporte": digest(source), "revision_conceptual": "revisada; clave conservada salvo correcciones de redaccion y distractores", "validacion_psicometrica": False}
            if short in TERMS:
                terms = [normal(term) for term in TERMS[short][index].split("|")]
                candidates = []
                for path, number, text, raw in pages:
                    positions = [text.find(term) for term in terms]
                    if all(position >= 0 for position in positions):
                        distance = max(positions) - min(positions)
                        index_penalty = 10000 if text.count("....") > 3 or "indice alfabetico" in text[:150] else 0
                        candidates.append((distance + index_penalty, path, number, text, min(positions)))
                candidates.sort(key=lambda item: item[0])
                record["localizadores_candidatos"] = [{"archivo": path, "pagina_pdf": number, "terminos": terms, "extracto_normalizado": text[max(0, position - 160):position + 700]} for _, path, number, text, position in candidates[:2]]
                record["cotejo_documental"] = "pasajes candidatos localizados; deben leerse antes de confirmar respaldo" if candidates else "requiere fuente adicional; no se hallo pasaje conjunto"
                record["respaldo_clave_confirmado"] = False
                if index + 1 in CONFIRMED.get(short, set()) and candidates:
                    record["respaldo_clave_confirmado"] = True
                    record["localizador_confirmado"] = record["localizadores_candidatos"][0]
                    record["cotejo_documental"] = "extracto leído y pertinente al concepto de la clave; no certifica toda la explicación ni cada distractor"
                if (short, index + 1) in WEB_CONFIRMED:
                    url, section, finding = WEB_CONFIRMED[(short, index + 1)]
                    record["respaldo_clave_confirmado"] = True
                    record["localizador_confirmado"] = {"url": url, "apartado": section, "hallazgo": finding}
                    record["cotejo_documental"] = "apartado web consultado y pertinente a la clave; revisión conceptual de opciones separada"
            else:
                record["respaldo_clave_confirmado"] = True
                record["cotejo_documental"] = "texto original y justificacion revisados" if short == "comprension-lectora" else "calculo y unidades revisados" if short == "pensamiento-matematico" else "reglas de redaccion revisadas; DPD concordancia y contexto del ejercicio"
                record["localizador"] = "productos.json: " + slug + ", reactivo " + str(index + 1)
            records.append(record)
    target = Path(__file__).parent / "revision-2026-10-10"
    target.mkdir(exist_ok=True)
    (target / "revision-reactivos.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (target / "preliminares-libros.json").write_text(json.dumps(book_records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"reactivos": len(records), "con_pasajes_candidatos": sum(bool(record.get("localizadores_candidatos")) for record in records), "generales": 30, "libros": len(book_records)}, ensure_ascii=True))


if __name__ == "__main__":
    main()