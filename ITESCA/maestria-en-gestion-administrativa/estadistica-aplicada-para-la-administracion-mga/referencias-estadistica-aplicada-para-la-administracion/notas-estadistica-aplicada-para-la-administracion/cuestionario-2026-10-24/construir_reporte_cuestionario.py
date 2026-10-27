"""Materializa veinte reactivos reales sin alterar la evidencia del aula."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "respuestas-validadas.json"


def escape_tex(value: str) -> str:
    substitutions = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    text = "".join(substitutions.get(char, char) for char in value)
    text = text.replace("(Z·σ / E)\\textasciicircum{}2", r"\((Z\cdot\sigma/E)^2\)")
    return text


def main() -> None:
    original = SOURCE.read_bytes()
    data = json.loads(original.decode("utf-8-sig"))
    questions = data["preguntas"]
    assert len(questions) == 20
    assert [q["numero"] for q in questions] == list(range(1, 21))
    source_map = {
        1: ["statcanNoProb2021"],
        2: ["holmesBusiness2023", "statcanProb2021"],
        3: ["wackerly2010"],
        4: ["statcanProb2021"],
        5: ["holmesBusiness2023", "statcanProb2021"],
        6: ["holmesBusiness2023"],
        7: ["holmesBusiness2023"],
        8: ["holmesBusiness2023"],
        9: ["holmesBusiness2023"],
        10: ["holmesBusiness2023"],
        11: ["holmesBusiness2023", "bradley2021"],
        12: ["wackerly2010"],
        13: ["wackerly2010", "holmesBusiness2023"],
        14: ["holmesBusiness2023", "bradley2021"],
        15: ["holmesBusiness2023"],
        16: ["bradley2021", "holmesBusiness2023"],
        17: ["statcanNoProb2021"],
        18: ["statcanNoProb2021"],
        19: ["holmesBusiness2023"],
        20: ["holmesBusiness2023", "statcanNoProb2021"],
    }
    concise = {
        1: "Ambos distinguen grupos, pero cuotas completa cantidades prefijadas mediante selección no aleatoria. El estratificado selecciona unidades al azar dentro de cada estrato; esa diferencia impide atribuir automáticamente a cuotas el error de un diseño probabilístico.",
        17: "La selección depende del conocimiento y propósito del investigador. Es no probabilística: el criterio experto no establece por sí solo probabilidades de inclusión conocidas ni garantiza representatividad.",
        18: "Los contactos iniciales remiten a otros participantes y facilitan acceder a grupos poco visibles. La dificultad de localización es decisiva; el tamaño pequeño por sí solo no exige este método.",
        20: "Se selecciona a quienes resultan accesibles o disponibles, sin sorteo desde un marco. Esa facilidad puede excluir segmentos y limita la generalización de los resultados.",
    }
    locators = {
        1: "Statistics Canada, 3.2.3, Quota sampling; material del aula 1745, líneas 209–212.",
        2: "OpenStax 1.2, Stratified sample; Statistics Canada 3.2.2, Stratified sampling.",
        3: "Wackerly et al., capítulo 7, definición 7.1, p. 347; Levin y Rubin, glosario cap. 6, p. 267.",
        4: "Statistics Canada 3.2.2, Cluster sampling, párrafos 1–5.",
        5: "OpenStax 1.2, Systematic sample; Statistics Canada 3.2.2, Systematic sampling.",
        6: "OpenStax 1.1, Definitions of Statistics, Probability, and Key Terms; diseño descriptivo frente a contraste de hipótesis.",
        7: "OpenStax 8.4, Continuous Random Variables; 8.1, nivel de confianza y distribución normal.",
        8: "OpenStax 1.2, población frente a muestra; aplicación administrativa del concepto de subconjunto observado.",
        9: "OpenStax 1.2, Simple random sample; igualdad de todas las muestras posibles del mismo tamaño.",
        10: "OpenStax 8.4, Binary Random Variables, fórmula y elección conservadora p=0.5.",
        11: "OpenStax 1.2, Sampling bias; Bradley et al., Comparing study designs.",
        12: "Wackerly et al., capítulo 7, definición 7.1, p. 347.",
        13: "OpenStax 1.2, Sampling errors; Wackerly et al., capítulo 7, distribución de estadísticos.",
        14: "OpenStax 1.2, Problems with samples; Bradley et al., cobertura y selección.",
        15: "OpenStax 1.2, Sampling; diferencia entre proceso de selección y representatividad lograda.",
        16: "Bradley et al., The Big Data Paradox in vaccine uptake; OpenStax 1.2, muestras grandes sesgadas.",
        17: "Statistics Canada 3.2.3, Judgement sampling.",
        18: "Statistics Canada 3.2.3, Snowball or network sampling.",
        19: "OpenStax 1.1, Population; Wackerly et al., capítulo 1, población y muestra.",
        20: "OpenStax 1.2, Convenience sampling; Statistics Canada 3.2.3, Convenience or haphazard sampling.",
    }
    rows = []
    enriched = []
    for q in questions:
        number = q["numero"]
        assert q["respuesta"] in q["opciones"], f"Respuesta ajena a opciones: {number}"
        item = dict(q)
        item["fuentes"] = source_map[number]
        item["justificacion"] = concise.get(number, q["justificacion"])
        item["localizador"] = locators[number]
        enriched.append(item)
        rows.append("% Opciones originales: " + " | ".join(q["opciones"]))
        rows.append(
            f"{number} & {escape_tex(q['pregunta'])} & "
            + r"\textbf{" + escape_tex(q["respuesta"]) + "} & "
            + escape_tex(item["justificacion"])
            + r" \citep{" + ",".join(item["fuentes"]) + r"}.\\"
        )
        if number < 20:
            rows.append(r"\midrule")
    (HERE / "reactivos-validados.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (HERE / "respuestas-soporte-editorial.json").write_text(
        json.dumps({"schema": "aulatex.questionnaire.validated-support.v1", "source_file": SOURCE.name,
                    "source_sha256": hashlib.sha256(original).hexdigest(), "count": 20,
                    "preguntas": enriched}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    synthesis = r"""\subsection{Implicaciones para las decisiones administrativas}
Las respuestas distinguen tres cuestiones que deben resolverse juntas: qué población interesa, cómo se selecciona la evidencia y qué incertidumbre permanece. Asegurar presencia de departamentos mediante estratos, concentrar visitas por conglomerados y elegir cada unidad a un intervalo fijo son decisiones de diseño diferentes. La facilidad de reunir participantes por cuotas, juicio, redes de contacto o conveniencia tampoco convierte esas selecciones en muestras probabilísticas \citep{holmesBusiness2023}.

Las fórmulas de tamaño no sustituyen esas decisiones. Elegir un valor crítico de confianza o utilizar una proporción conservadora permite planificar precisión bajo supuestos explícitos; omitir clientes sin conexión o consultar solo a empleados disponibles puede mantener sesgos incluso con muchas observaciones. Por ello, una auditoría de transacciones o una encuesta de satisfacción debe justificar tanto su cantidad de datos como el mecanismo que produjo esos datos \citep{bradley2021}.

De esta relación se desprende que la representatividad es una condición que se examina, no un atributo automático del nombre del diseño. Una decisión defendible declara población, marco, reglas de selección y límites de respuesta, y mantiene separados los resultados muestrales de los parámetros que pretende estimar \citep{wackerly2010}.
"""
    conclusion = r"""El muestreo permite estudiar poblaciones mediante una parte de sus unidades, pero exige mantener una correspondencia explícita entre la población delimitada y la evidencia realmente obtenida. La diferencia entre parámetro y estadístico aclara qué se desea conocer y qué se observa; la diferencia entre variación de muestreo y sesgo aclara qué puede mejorar al aumentar el número de observaciones y qué requiere cambiar el procedimiento de recolección \citep{wackerly2010,bradley2021}.

La selección aleatoria simple, la estratificación, el muestreo sistemático y los conglomerados responden a necesidades distintas de cobertura, organización y costo. El criterio administrativo debe ser elegir el diseño que corresponda a la población y a la decisión, en lugar de aplicar una técnica solo porque resulta conocida o accesible. La presencia de grupos en una muestra merece evaluarse junto con la manera en que sus integrantes fueron elegidos y con la respuesta que efectivamente se obtuvo \citep{holmesBusiness2023}.

Considero que una práctica responsable debe priorizar la calidad del marco y la transparencia de la selección antes de interpretar la cantidad de registros como evidencia suficiente. En una encuesta al personal, ello implica incluir turnos y áreas con distintas condiciones de acceso; en una revisión de transacciones, delimitar el periodo, los registros elegibles y las reglas de selección. Si la cobertura excluye sistemáticamente un segmento, aumentar la muestra puede dar una impresión de precisión sin resolver el problema de fondo \citep{bradley2021}.

El tamaño se planifica con un nivel de confianza, una tolerancia y supuestos coherentes con la variable. Sin embargo, esa planificación debe acompañarse de seguimiento de la no respuesta, revisión de medición y comunicación de límites. Los resultados pueden orientar recursos o decisiones laborales cuando se respeta su alcance; extrapolarlos a otras poblaciones o atribuirles efectos causales requiere evidencia adicional \citep{bloom2024}.

Una conclusión útil para la administración vincula selección, medida y decisión: indica a quiénes describe, cuánta incertidumbre admite y qué limitaciones deben considerarse antes de actuar. Esa disciplina permite utilizar el muestreo como fundamento de decisiones proporcionales a la evidencia disponible.\footnote{Se utilizó inteligencia artificial para la corrección y organización del contenido, y Nova Pro de AulaTeX como apoyo al corpus conceptual de la materia y su extracción documental. El autor declara haber realizado y validado la investigación documental, el análisis y los resultados presentados, y asume su responsabilidad académica.}
"""
    (HERE / "sintesis-validada.tex").write_text(synthesis, encoding="utf-8")
    (HERE / "conclusion-validada.tex").write_text(conclusion, encoding="utf-8")
    composition_dir = HERE.parents[2] / "assets-estadistica-aplicada-para-la-administracion" / "cuestionario"
    composition_dir.mkdir(parents=True, exist_ok=True)
    for name in ("reactivos-validados.tex", "sintesis-validada.tex", "conclusion-validada.tex"):
        shutil.copy2(HERE / name, composition_dir / name)
    print(json.dumps({"questions": len(questions), "source_unchanged": SOURCE.read_bytes() == original,
                      "output": "reactivos-validados.tex", "source_sha256": hashlib.sha256(original).hexdigest()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
