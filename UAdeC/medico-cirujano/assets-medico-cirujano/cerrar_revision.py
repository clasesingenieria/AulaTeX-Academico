import json
from pathlib import Path
from organizar_productos import CAREER, digest, existing_questions


def main():
    directory = Path(__file__).parent / "revision-2026-10-10"
    records = json.loads((directory / "revision-reactivos.json").read_text(encoding="utf-8"))
    links = {
        ("biologia-celular", 13): ("https://ictv.global/report/chapter/coronaviridae/coronaviridae", "Summary; Nucleic acid; Biology", "SARS-CoV-2 pertenece a Coronaviridae, de genoma ARN positivo. Contrastado con ICTV Retroviridae: https://ictv.global/report/chapter/retroviridae/retroviridae, Summary, Nucleic acid y Figure 1: VIH es un lentivirus con genoma ARN y retrotranscripción."),
        ("anatomia", 4): ("https://openstax.org/books/anatomy-and-physiology-2e/pages/7-2-the-skull", "Bones of the Brain Case / Sphenoid Bone", "Esfenoides impar; parietales y temporales pares."),
        ("anatomia", 10): ("https://openstax.org/books/anatomy-and-physiology-2e/pages/7-3-the-vertebral-column", "Cervical Vertebrae", "Atlas sin cuerpo ni apófisis espinosa."),
        ("anatomia", 12): ("https://openstax.org/books/anatomy-and-physiology-2e/pages/8-4-bones-of-the-lower-limb", "Patella", "Rótula: mayor hueso sesamoideo."),
        ("anatomia", 19): ("https://openstax.org/books/anatomy-and-physiology-2e/pages/8-4-bones-of-the-lower-limb", "Fibula", "Maléolo lateral; articulación con tibia y talo, no fémur."),
        ("biologia-celular", 12): ("https://openstax.org/books/biology-2e/pages/5-4-bulk-transport", "Endocytosis / Pinocytosis", "Invaginación membranal y formación de vesículas."),
        ("bioquimica", 3): ("https://openstax.org/books/biology-2e/pages/3-2-carbohydrates", "Disaccharides; Figure 3.7", "Sacarosa formada por glucosa y fructosa."),
        ("bioquimica", 18): ("https://openstax.org/books/biology-2e/pages/14-6-dna-repair", "Proofreading; Figure 14.17", "ADN polimerasa y actividad exonucleasa correctora."),
        ("bioquimica", 19): ("https://openstax.org/books/biology-2e/pages/15-1-the-genetic-code", "The Genetic Code Is Degenerate and Universal", "Tripletes y codones de terminación."),
        ("salud-publica", 8): ("https://www.who.int/about/governance/constitution", "Principles", "Bienestar físico, mental y social; Constitución vigente desde 1948."),
        ("salud-publica", 15): ("https://www.who.int/news-room/fact-sheets/detail/syphilis", "Transmission", "Transmisión durante el embarazo a través de placenta; contrastada además con ficha OMS VIH, Transmission."),
    }
    local = {
        ("biologia-celular", 20): ("*Murray.pdf", 130, "Gram negativas: capa fina de peptidoglucano y tinción roja; morfología de bacilos contrastada con Higashida, página PDF 24."),
        ("fisiologia", 1): ("*BOOKSMEDICOS.ORG.pdf", 850, "Figura 21.14: retroalimentación negativa de presión arterial."),
        ("fisiologia", 8): ("*Boulpa*.pdf", 811, "Neuronas hipotalámicas sintetizan vasopresina y la transportan a hipófisis posterior para liberarla."),
        ("salud-publica", 4): ("*BOOKSMEDICOS.ORG.pdf", 42, "Síntomas subjetivos y signos objetivos, incluidos dolor y presión arterial."),
        ("salud-publica", 11): ("*Modulos*.pdf", 77, "Prevención primaria y protección específica: inmunizaciones."),
        ("salud-publica", 12): ("*Higashida.pdf", 241, "Endemia como frecuencia habitual a través del tiempo, no erradicación."),
        ("salud-publica", 14): ("*Higashida.pdf", 241, "Pandemia como epidemia de gran extensión geográfica."),
    }
    for record in records:
        short = record["area"].removeprefix("examen-ingreso-")
        key = (short, record["numero"])
        if key in links:
            url, section, finding = links[key]
            record["localizador_confirmado"] = {"url": url, "apartado": section, "hallazgo": finding}
            record["respaldo_clave_confirmado"] = True
        if key in local:
            pattern, number, finding = local[key]
            paths = list(CAREER.glob("examen-*/referencias-*/libros-*/" + pattern))
            if "BOOKSMEDICOS" in pattern:
                paths = [path for path in paths if "examen-ingreso-anatomia" in path.as_posix()]
            assert len(paths) == 1, (key, paths)
            record["localizador_confirmado"] = {"archivo": paths[0].relative_to(CAREER).as_posix(), "sha256": digest(paths[0]), "pagina_pdf": number, "hallazgo": finding}
            record["respaldo_clave_confirmado"] = True
        if key in links or key in local:
            record["cotejo_documental"] = "Localizador consultado que respalda la clave; no certifica cada afirmación secundaria de la explicación."
        if short in {"anatomia", "biologia-celular", "bioquimica", "fisiologia", "salud-publica"}:
            source = CAREER / record["area"] / f"reporte-{record['area']}.tex"
            question = existing_questions(source.read_text(encoding="utf-8"))[record["numero"] - 1]
            record.update(pregunta=question[0], opciones=question[1], clave=chr(65 + question[2]), justificacion=question[3], sha256_reporte=digest(source))
        if not record["respaldo_clave_confirmado"]:
            record["cotejo_documental"] = "Clave conceptual revisada; falta localizador conjunto específico para SARS-CoV-2 y VIH. Los textos de virus ARN recuperados no bastan para certificar toda la comparación."
    (directory / "revision-reactivos.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {"reactivos_revisados": len(records), "claves_con_localizador_confirmado": sum(record["respaldo_clave_confirmado"] for record in records), "pendientes_documentales": [{"area": record["area"], "numero": record["numero"]} for record in records if not record["respaldo_clave_confirmado"]], "cotejo_general_oficial": True, "campus_y_ciclo_personal_confirmados": False, "cobertura_oficial_completa": False, "revision_independiente_experta": False, "lectura_integra_libros": False}
    (directory / "estado-revision.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == "__main__":
    main()