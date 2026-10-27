import hashlib
import json
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

from validar_unidad_2 import BASE, NOTES, ROOT, SUBJECT, validate

sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.activity_observer import ActivityObserver, ActivityObservationRequest
from aulaTEX.aulatex.extractor_adapter import CORE_EXTRACTOR_ARTIFACTS

CONCEPTS = {
    3: [
        ("parametro", "parámetro", "Característica fija de la población que se pretende estimar.", 414),
        ("estimador", "estimador", "Regla muestral aleatoria empleada para aproximar un parámetro.", 414),
        ("estimacion", "estimación", "Valor concreto obtenido al aplicar el estimador a una muestra.", 414),
        ("insesgamiento", "insesgamiento", "La esperanza del estimador coincide con el parámetro objetivo.", 417),
        ("ecm", "error cuadrático medio", "Esperanza del error al cuadrado, igual a varianza más sesgo al cuadrado.", 417),
        ("eficiencia", "eficiencia relativa", "Comparación de varianzas entre estimadores insesgados del mismo parámetro.", 469),
        ("consistencia", "consistencia", "Convergencia en probabilidad del estimador al parámetro.", 474),
        ("chebyshev", "Chebyshev", "La varianza decreciente de un estimador insesgado acota su probabilidad de error.", 474),
        ("error_estandar", "error estándar", "Desviación estándar de la distribución muestral del estimador.", 378),
        ("intervalo", "intervalo de confianza", "Intervalo aleatorio construido por un procedimiento de cobertura especificada.", 430),
        ("confianza", "95%", "Frecuencia de cobertura del procedimiento en muestreos repetidos, bajo supuestos.", 431),
        ("margen", "margen de error", "Semiamplitud de un intervalo simétrico, dependiente de confianza y precisión.", 435),
    ],
    4: [
        ("poblacion", "población", "Conjunto de unidades definido para la inferencia.", 370),
        ("distribucion_muestral", "distribución muestral", "Distribución del estadístico al repetir muestras bajo un diseño.", 371),
        ("parametro", "parámetro", "Cantidad fija de la población en el modelo.", 414),
        ("estadistico", "estadístico", "Función de observaciones que puede variar entre muestras.", 371),
        ("independencia", "independientes", "Condición que permite sumar varianzas sin términos de covarianza.", 378),
        ("error_estandar", "error estándar", "Desviación de la media: desviación poblacional dividida entre raíz de n.", 378),
        ("tlc", "teorema del límite central", "Normalidad asintótica de la media estandarizada bajo las condiciones indicadas.", 396),
        ("normalidad", "normal", "Con población normal, la media es normal para cualquier tamaño muestral.", 377),
        ("binomial", "binomial", "Conteo de éxitos en ensayos independientes con probabilidad constante.", 403),
        ("proporcion", "proporción", "Cociente entre número de éxitos y tamaño muestral.", 403),
        ("continuidad", "corrección de continuidad", "Ajuste de medio entero al aproximar un conteo discreto por una normal.", 404),
        ("colas", "cola superior", "Probabilidad de superar un umbral; se distingue de la acumulada inferior.", 379),
    ],
}


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).split())


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    NOTES.mkdir(parents=True, exist_ok=True)
    book = next((SUBJECT / "referencias-estadistica-aplicada-para-la-administracion/libros-estadistica-aplicada-para-la-administracion").glob("*Wackerly*"))
    book_hash = hashlib.sha256(book.read_bytes()).hexdigest()
    inspection_path = NOTES.parent / "materiales-aula/2026-10-23/inspection.json"
    inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
    manifest = {"method": "extraccion_pdf_local_con_indexacion_semantica_revisada", "llm_invoked": False,
                "created_at_utc": datetime.now(timezone.utc).isoformat(), "book": book.relative_to(SUBJECT).as_posix(),
                "book_sha256": book_hash, "activities": []}
    with pymupdf.open(book) as textbook:
        pages = sorted({6} | {item[3] for concepts in CONCEPTS.values() for item in concepts})
        extracted = {page: textbook[page - 1].get_text() for page in pages}
        assert "2010" in extracted[6] and "978-607-481-399-9" in extracted[6]
        (NOTES / "wackerly-pasajes-verificados.txt").write_text("\n\n".join(f"PAGINA PDF {page}\n{text}" for page, text in extracted.items()), encoding="utf-8")
    for number, module_id in ((3, 1754), (4, 1755)):
        checked = validate(number)
        pdf = ROOT / checked["pdf"]
        with pymupdf.open(pdf) as document:
            report_pages = [normalized(page.get_text()) for page in document]
        records = []
        for identifier, term, definition, book_page in CONCEPTS[number]:
            matches = [(index + 1, text, text.casefold().find(term.casefold())) for index, text in enumerate(report_pages) if term.casefold() in text.casefold()]
            assert matches, (number, term)
            page_number, text, position = matches[0]
            records.append({"id": identifier, "concepto": term, "definicion_revisada": definition,
                            "pagina_pdf_reporte": page_number, "fragmento_reporte": text[max(0, position - 80):position + 450],
                            "fuente": "wackerly2010", "pagina_pdf_fuente": book_page,
                            "fragmento_fuente": normalized(extracted[book_page]), "fuente_sha256": book_hash})
        activity = next(item for item in inspection["activities"] if item["module_id"] == module_id)
        output = SUBJECT / "extractor-aulatex" / f"conceptos-estadistica-actividad-{number}"
        output.mkdir(parents=True, exist_ok=True)
        criteria = ["PDF con portada institucional", "Arial 12, interlineado 1.5 y justificacion"]
        if number == 3:
            criteria.extend(["Cinco cuartillas incluidas portada y fuentes", "Minimo tres fuentes", "Introduccion, desarrollo, conclusiones y referencias APA 7", "Conceptos, propiedades, ejemplos e interpretacion administrativa"])
        else:
            criteria.append("Resolver todos los ejercicios del PDF enlazado por la consigna")
        plan = {"objetivo": "Comprender fundamentos de estimacion y su uso administrativo" if number == 3 else "Resolver e interpretar distribuciones muestrales bajo supuestos explicitos",
                "origen_objetivo": "sintesis editorial de la consigna, no cita literal", "criterios_entrega": criteria,
                "verbos_operativos": ["definir", "explicar", "ilustrar", "interpretar"] if number == 3 else ["encontrar", "calcular", "determinar"],
                "consigna_literal": activity["instructions"], "module_id": module_id, "llm_invoked": False}
        provenance = {"method": manifest["method"], "llm_invoked": False, "source_book": manifest["book"], "source_sha256": book_hash,
                      "instruction_path": inspection_path.relative_to(SUBJECT).as_posix(),
                      "instruction_sha256": hashlib.sha256(inspection_path.read_bytes()).hexdigest(),
                      "report_sha256": checked["sha256"], "concept_support": records}
        payloads = {"fichas_json": records, "conceptos": records,
                    "ideas": [{"concept_id": record["id"], "idea": record["definicion_revisada"], "fuente": "wackerly2010", "pagina_pdf_fuente": record["pagina_pdf_fuente"]} for record in records],
                    "trazabilidad": provenance, "planeacion": plan}
        for name, filename in CORE_EXTRACTOR_ARTIFACTS.items():
            save_json(output / filename, payloads[name])
        result = ActivityObserver().observe(ActivityObservationRequest(target=str(SUBJECT), activity_number=number, output=str(NOTES / "observador-motor")))
        evaluation = json.loads(result.evaluation_path.read_text(encoding="utf-8"))
        manifest["activities"].append({"number": number, "concepts": len(records), "pdf_sha256": checked["sha256"],
                                       "observer_passed": evaluation["passed"], "observer_score": evaluation["score"],
                                       "contract_score": evaluation["contract"]["score"], "contract_checks": evaluation["contract"]["checks"],
                                       "warnings": evaluation["warnings"], "findings": evaluation["critical_findings"],
                                       "observer_evaluation": result.evaluation_path.relative_to(SUBJECT).as_posix(),
                                       "compile_evidence": "validar_unidad_2.build/validate: XeLaTeX; observer compile_check=False"})
    save_json(NOTES / "auditoria-contrato.json", manifest)
    print(json.dumps(manifest, ensure_ascii=True, indent=2))
    assert all(item["observer_passed"] for item in manifest["activities"])


if __name__ == "__main__":
    main()