import json
import re
from pathlib import Path
import pymupdf
from revisar_reactivos import CAREER, normal

SEARCH = {
    "anatomia": {1:"radio|lateral",2:"peritoneo|parietal",3:"plano sagital",4:"esfenoides|impar",5:"costillas|falsas",6:"diafragma|inspiracion",10:"atlas|sin cuerpo",12:"rotula|sesamoideo",18:"abduccion|linea",19:"perone|tibia"},
    "biologia-celular": {1:"endosimbiosis",2:"atpasa|sodio",6:"grampositivas|peptidoglucano",7:"crenacion",8:"reticulo endoplasmico liso|lipidos",9:"protozoarios|eucariotas",11:"46 cromosomas",12:"endocitosis|membrana",13:"vih|rna",18:"comensalismo",19:"citocinesis|actina",20:"bacilos|forma"},
    "bioquimica": {1:"proteinas|aminoacidos",2:"enlace glucosidico",3:"sacarosa|fructosa",5:"glucolisis|dos atp",7:"oxigeno|aceptor final",11:"transcripcion|arn",12:"chargaff",14:"traduccion|ribosoma",17:"hidrolisis|atp",18:"polimerasa|correccion",19:"codon|triplete"},
    "fisiologia": {1:"retroalimentacion negativa",3:"primer ruido",6:"volumen corriente|500",8:"vasopresina|hipotalamo",11:"pepsinogeno|pepsina",12:"celulas alfa|glucagon",13:"bilis|emulsion",14:"acetilcolina|placa",15:"hemoglobina|oxigeno",16:"simpatico|frecuencia cardiaca",17:"respiracion interna",18:"tiroides|metabolismo",19:"reflejo|rotuliano"},
    "salud-publica": {4:"signos|sintomas",8:"bienestar fisico",11:"primaria|vacunacion",12:"endemia",14:"pandemia",15:"transmision vertical",17:"agentes|fisicos",19:"nosocomial"}
}

ACCEPTED = {
    "anatomia": {1: 0, 2: 1, 3: 0, 5: 0, 6: 1, 18: 1},
    "biologia-celular": {1: 0, 2: 0, 6: 0, 7: 0, 8: 1, 9: 1, 11: 0, 18: 1, 19: 1},
    "bioquimica": {1: 1, 2: 0, 5: 1, 7: 0, 11: 1, 12: 1, 14: 0, 17: 1},
    "fisiologia": {3: 1, 6: 1, 11: 0, 12: 0, 13: 0, 14: 1, 15: 0, 16: 1, 17: 0, 18: 1, 19: 1},
    "salud-publica": {17: 0, 19: 0},
}


def main():
    directory = Path(__file__).parent / "revision-2026-10-10"
    records = json.loads((directory / "revision-reactivos.json").read_text(encoding="utf-8"))
    pages = []
    for path in CAREER.glob("examen-*/referencias-*/libros-*/*.pdf"):
        with pymupdf.open(path) as pdf:
            for index, page in enumerate(pdf):
                text = normal(page.get_text())
                if index < 25 or len(text) < 400 or "indice alfabetico" in text[:100] or "contenido detallado" in text[:100]:
                    continue
                pages.append((path.relative_to(CAREER).as_posix(), index + 1, text))
    output = []
    for record in records:
        if record["respaldo_clave_confirmado"]:
            continue
        short = record["area"].removeprefix("examen-ingreso-")
        terms = SEARCH[short][record["numero"]].split("|")
        candidates = []
        for path, number, text in pages:
            positions = [list(re.finditer(re.escape(term), text)) for term in terms]
            if not all(positions):
                continue
            for first in positions[0]:
                nearest = [min(matches, key=lambda match: abs(match.start() - first.start())) for matches in positions]
                distance = max(match.start() for match in nearest) - min(match.start() for match in nearest)
                if distance > 850:
                    continue
                offset = min(match.start() for match in nearest)
                extract = text[max(0, offset - 100):max(match.end() for match in nearest) + 450]
                score = distance + (5000 if "vease" in extract and extract.count(",") > 20 else 0)
                candidates.append((score, path, number, extract))
        candidates.sort(key=lambda item: item[0])
        output.append({"area": record["area"], "numero": record["numero"], "clave": record["clave"], "candidatos": [{"archivo": path, "pagina_pdf": number, "extracto": extract} for _, path, number, extract in candidates[:2]]})
    (directory / "localizadores-adicionales.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    by_question = {(item["area"], item["numero"]): item for item in output}
    for record in records:
        short = record["area"].removeprefix("examen-ingreso-")
        accepted_index = ACCEPTED.get(short, {}).get(record["numero"])
        if accepted_index is not None:
            candidate = by_question[(record["area"], record["numero"])]["candidatos"][accepted_index]
            record["localizador_confirmado"] = candidate
            record["respaldo_clave_confirmado"] = True
            record["cotejo_documental"] = "Pasaje leído y pertinente al concepto de la clave; no implica lectura íntegra del libro ni validación psicométrica."
    (directory / "revision-reactivos.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pendientes":len(output),"con_candidatos":sum(bool(item['candidatos']) for item in output)}))


if __name__ == "__main__":
    main()