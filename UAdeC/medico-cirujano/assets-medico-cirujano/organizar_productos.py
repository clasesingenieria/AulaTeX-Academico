from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[3]
CAREER = ROOT / "UAdeC/medico-cirujano"
MODEL = Path(__file__).with_name("productos.json")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preserve(path, notes):
    if path.exists():
        target = notes / "materiales-generales/historico-2026-10-10" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise RuntimeError(f"Respaldo existente: {target}")
        shutil.copy2(path, target)
        assert digest(path) == digest(target)


def tex(value):
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "_": r"\_", "#": r"\#", "$": r"\$", "{": r"\{", "}": r"\}"}
    return "".join(replacements.get(character, character) for character in value)


def block(value, position):
    if value[position] != "{":
        raise ValueError("Se esperaba un grupo TeX")
    depth = 1
    start = position + 1
    position = start
    while depth:
        if value[position] == "{" and value[position - 1] != "\\":
            depth += 1
        elif value[position] == "}" and value[position - 1] != "\\":
            depth -= 1
        position += 1
    return value[start:position - 1], position


def existing_questions(source):
    markers = list(re.finditer(r"\\item\s+\\textbf\{", source))
    result = []
    for index, marker in enumerate(markers):
        part = source[marker.start():markers[index + 1].start() if index + 1 < len(markers) else len(source)]
        question, _ = block(part, part.index("{"))
        options = re.findall(r"\\item\[([A-D])\)\]\s*(.*?)(?=\\item\[|\\end\{enumerate\})", part, re.S)
        response = re.search(r"\\textit\{Respuesta(?: correcta)?:\s*([A-D])\.\s*", part)
        if len(options) == 4 and response:
            explanation, _ = block(part, part.index("{", response.start()))
            explanation = re.sub(r"^Respuesta(?: correcta)?:\s*[A-D]\.\s*", "", explanation)
            result.append([question, [value.strip() for _, value in options], ord(response[1]) - ord("A"), explanation])
    if len(result) < 10:
        raise RuntimeError("Banco existente insuficiente o no interpretable")
    return result


def representation(area):
    rows = "\n".join(tex(label) + " & " + tex(description) + r"\\" for label, description in area["esquema"])
    return r"""\subsection{Representación conceptual y cuadro de síntesis}
\begin{longtable}{p{0.27\linewidth}p{0.65\linewidth}}
\toprule Concepto & Relación o función\\\midrule
""" + rows + r"""
\bottomrule
\end{longtable}
\begin{figure}[htbp]
\centering
\begin{tikzpicture}[node distance=5mm, every node/.style={draw,rounded corners=2pt,text width=10cm,align=center,font=\small}]
""" + "\n".join(
        r"\node" + (f"[below=of step{index - 1}]" if index else "") + f" (step{index}) " + "{" + tex(label + ": " + description) + "};"
        + (f"\n\\draw[-{{Stealth}}] (step{index - 1}) -- (step{index});" if index else "")
        for index, (label, description) in enumerate(area["esquema"])
    ) + "\n" + r"""\end{tikzpicture}
\caption{Esquema didáctico original; las flechas indican orden de lectura o relación conceptual, no causalidad universal.}
\end{figure}
"""


def references(area):
    return r"\clearpage\section{Fuentes de apoyo y alcance de consulta}" + "\n" + "\n".join(
        tex(source["entidad"] + ". " + source["titulo"] + ". Consulta: 10 de octubre de 2026. ")
        + r"\url{" + source["url"] + "}" + r"\par " + tex(source["alcance"]) + r"\par\medskip"
        for source in area["fuentes"]
    ) + "\n" + r"Los originales bibliográficos disponibles se identifican por nombre de archivo y SHA256 en el inventario local. No se atribuyen ediciones, páginas ni lecturas no comprobadas."


def main():
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    registry = []
    for area in model["areas"]:
        slug = area["slug"]
        subject = CAREER / slug
        refs = subject / f"referencias-{slug}"
        notes = refs / f"notas-{slug}"
        books = refs / f"libros-{slug}"
        plans = subject / f"planeaciones-{slug}"
        for folder in (notes / "actividad-01-investigacion", notes / "actividad-02-cuestionario", books, subject / f"assets-{slug}", subject / "extractor-aulatex", subject / "Entregas", plans):
            folder.mkdir(parents=True, exist_ok=True)
        inventory = []
        for original in refs.glob("*.pdf"):
            target = books / original.name
            original_hash = digest(original)
            if target.exists():
                raise RuntimeError(f"Libro de destino existente: {target}")
            shutil.move(original, target)
            assert digest(target) == original_hash
            inventory.append({"origen": str(original.relative_to(CAREER)).replace("\\", "/"), "archivo": str(target.relative_to(subject)).replace("\\", "/"), "sha256": original_hash, "metadatos_editoriales": "pendientes de cotejo", "lectura_integra_acreditada": False})
        (refs / "inventario-libros.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        source = subject / f"reporte-{slug}.tex"
        preserve(source, notes)
        supplement = "\\section{Actividad 1: síntesis de investigación}\n" + "\n".join(
            r"\subsection{" + tex(title) + "}\n" + tex(paragraph) for title, paragraph in area["sintesis"]
        ) + "\n" + representation(area)
        if "preguntas" in area:
            questions = area["preguntas"]
            report = r"\def\uadectitulo{" + tex(area["titulo"]) + "}\n" + r"\input{UAdeC/medico-cirujano/assets-medico-cirujano/plantilla/reporte-uadec.tex}" + "\n\\begin{document}\n\\portadaUAdeC\n" + supplement
            report += "\\clearpage\\section{Actividad 2: cuestionario original resuelto}\n\\begin{enumerate}\n"
            for question, options, answer, reason in questions:
                report += r"\item\textbf{" + tex(question) + "}\n\\begin{enumerate}[label=\\Alph*)]\n"
                report += "\n".join(r"\item " + tex(option) for option in options)
                report += "\n\\end{enumerate}\n\\textbf{Respuesta: " + chr(65 + answer) + ".} " + tex(reason) + "\n"
            report += "\\end{enumerate}\n"
        else:
            report = source.read_text(encoding="utf-8")
            body = report.split(r"\begin{document}", 1)[1]
            if r"\portadaUAdeC" in body:
                body = body.split(r"\portadaUAdeC", 1)[1]
            else:
                body = body.split(r"\tableofcontents", 1)[1]
                body = body.replace(r"\newpage", "", 1)
            body = body.rsplit(r"\end{document}", 1)[0]
            body = body.replace("Simulación EXANI-II", "Actividad 2: banco original de práctica")
            body = body.replace("Dato EXANI-II", "Nota de estudio").replace("(EXANI-II)", "(repaso)")
            body = body.replace("Todo movimiento de flexión/extensión ocurre en este plano.", "La flexión y extensión se describen principalmente en este plano, con excepciones según la articulación.")
            body = body.replace("Exclusivo para las extremidades", "Frecuente en las extremidades")
            body = body.replace("El cardíaco es estriado pero uninucleado central.", "El cardíaco es estriado, habitualmente con uno y ocasionalmente dos núcleos centrales.")
            body = body.replace("El peroné está lateral a la tibia; no articula con el fémur ni soporta peso.", "El peroné está lateral a la tibia; no articula con el fémur, transmite una parte menor de la carga y estabiliza el tobillo.")
            body = body.replace("NO soporta el peso del cuerpo", "soporta una fracción menor de la carga que la tibia")
            body = body.replace("La citocinesis (separación del citoplasma) ocurre justo al finalizar la telofase de la mitosis.", "La citocinesis (separación del citoplasma) puede solaparse con anafase y telofase de la mitosis.")
            body = body.replace("El código genético se lee en tripletes (3 nucleótidos = 1 codón = 1 aminoácido).", "El código genético se lee en tripletes; los codones con sentido especifican aminoácidos y los codones de terminación no especifican uno.")
            body = body.replace("Prevalencia:} Número TOTAL (nuevos + acumulados viejos) de casos.", "Prevalencia:} Proporción de casos existentes en una población y momento o periodo definidos.")
            body = body.replace("Pandemia si cruza fronteras continentales.", "Una pandemia implica propagación extensa en múltiples países o continentes; cruzar una frontera por sí solo no basta.")
            body = body.replace("no comprobable matemáticamente", "registrable mediante relato y escalas, sin equivaler a una medición objetiva directa")
            body = re.sub(r"Toda infección que incuba o aparece a partir de las 48 hrs.*?(?=\})", "La clasificación de IAAS depende de criterios clínicos y epidemiológicos de vigilancia, no de un umbral temporal universal; debe descartarse que estuviera presente o incubándose al ingreso según la definición aplicable.", body)
            body = re.sub(r"Estas 20 preguntas.*?(?=\n)", "Estos reactivos son originales de práctica; no se ha verificado equivalencia con el examen oficial.", body)
            questions = existing_questions(body)
            report = r"\def\uadectitulo{" + tex(area["titulo"]) + "}\n" + r"\input{UAdeC/medico-cirujano/assets-medico-cirujano/plantilla/reporte-uadec.tex}" + "\n\\begin{document}\n\\portadaUAdeC\n" + supplement + "\n\\clearpage\n" + body
        report += "\n\\section{Conclusiones}\n" + tex("El material permite repasar conceptos y contrastar respuestas. La clave no acredita desempeño del aspirante ni aprobación institucional. Deben revisarse la convocatoria y el temario aplicables antes de usarlo como plan definitivo de ingreso.") + "\n" + references(area) + "\n\\end{document}\n"
        source.write_text(report, encoding="utf-8")
        guide = subject / "guia-de-estudio.md"
        preserve(guide, notes)
        guide.write_text("# " + area["titulo"] + "\n\nPreparación local; no es una guía oficial.\n\n" + "\n\n".join("## " + title + "\n\n" + paragraph for title, paragraph in area["sintesis"]) + "\n\n## Representación conceptual\n\n| Concepto | Relación o función |\n| --- | --- |\n" + "\n".join(f"| {label} | {description} |" for label, description in area["esquema"]) + "\n\n## Productos\n\n[Reporte con esquema y soluciones](reporte-" + slug + ".tex). [Cuestionario y justificaciones](referencias-" + slug + "/notas-" + slug + "/actividad-02-cuestionario/cuestionario-resuelto.md).\n", encoding="utf-8")
        bank = notes / "actividad-02-cuestionario/cuestionario-resuelto.md"
        bank.write_text("# Cuestionario resuelto - " + area["titulo"] + "\n\nReactivos locales; no son preguntas de un examen real. La clave no es una calificación del aspirante.\n\n" + "\n\n".join(
            f"## Pregunta {number}\n\n{question}\n\n" + "\n".join(f"{chr(65 + index)}. {option}" for index, option in enumerate(options)) + f"\n\n**Respuesta propuesta: {chr(65 + answer)}.** {reason}"
            for number, (question, options, answer, reason) in enumerate(questions, 1)
        ) + "\n", encoding="utf-8")
        (notes / "actividad-02-cuestionario/banco-reactivos.json").write_text(json.dumps({"origen": "practica local", "preguntas": questions, "respondido_por_aspirante": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (notes / "actividad-01-investigacion/fuentes-y-alcance.md").write_text("# Fuentes y alcance\n\n" + "\n\n".join(f"- {entry['entidad']}. [{entry['titulo']}]({entry['url']}). Consulta: 10 de octubre de 2026. {entry['alcance']}" for entry in area["fuentes"]) + "\n\nLa síntesis y los esquemas son originales. Libros locales: metadatos y lectura pendientes de cotejo; no se atribuyen páginas consultadas. La consulta web es parcial, no revisión integral de cada reactivo.\n", encoding="utf-8")
        for kind, number, title in (("investigacion", "01", "Síntesis y representación conceptual"), ("cuestionario", "02", "Cuestionario y soluciones justificadas")):
            plan = plans / f"consigna-{kind}.md"
            preserve(plan, notes)
            plan.write_text(f"# Actividad {number} - {title}\n\nConsigna local AulaTeX; no se presenta como instrucción oficial de UAdeC/CENEVAL.\n\n## Objetivo\n\n" + ("Relacionar los conceptos de la guía mediante una síntesis y un esquema o tabla." if number == "01" else "Resolver y justificar los reactivos de práctica, identificando errores y límites.") + "\n\n## Producto\n\n" + f"[Guía](../guia-de-estudio.md), [fuente del reporte](../reporte-{slug}.tex) y PDF compilado junto a esa fuente.\n\n## Criterios\n\n- Conceptos precisos y sin afirmaciones absolutas injustificadas.\n- Fuente y alcance de consulta identificados.\n- Esquema o tabla coherente con la síntesis.\n- Cada reactivo tiene cuatro opciones y una solución justificada.\n- Sin marcadores de contenido pendiente en el producto.\n- Compilación y revisión visual verificadas por separado.\n\nLa resolución modelo no acredita un intento personal; no hay envío ni calificación institucional.\n", encoding="utf-8")
        (subject / "README.md").write_text("# " + area["titulo"] + " - preparación UAdeC\n\nÁrea de preparación local, no asignatura curricular ni temario oficial cotejado.\n\n- [Guía de estudio](guia-de-estudio.md).\n- [Actividad 1](planeaciones-" + slug + "/consigna-investigacion.md).\n- [Actividad 2](planeaciones-" + slug + "/consigna-cuestionario.md).\n- [Reporte y productos](reporte-" + slug + ".tex).\n- [PDF de estudio](reporte-" + slug + ".pdf).\n- [Inventario de libros](referencias-" + slug + "/inventario-libros.json).\n- [Fuentes y límites](referencias-" + slug + "/notas-" + slug + "/actividad-01-investigacion/fuentes-y-alcance.md).\n\n`Entregas` queda reservado para exportaciones que exija una consigna real; no se inventa formato de envío. La bibliografía PDF local está en `libros-" + slug + "`; notas, soluciones y originales históricos en `notas-" + slug + "`. No se redistribuyen libros por el hecho de organizarlos.\n", encoding="utf-8")
        registry.append({"area": slug, "titulo": area["titulo"], "reactivos": len(questions), "libros": len(inventory), "fuente": str(source.relative_to(CAREER)).replace("\\", "/"), "alineacion_oficial_confirmada": False, "revision_cientifica_integral": False})
    (CAREER / "catalogo-productos.json").write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"areas": len(registry), "reactivos": sum(item["reactivos"] for item in registry), "libros_preservados": sum(item["libros"] for item in registry)}, ensure_ascii=True))


if __name__ == "__main__":
    main()