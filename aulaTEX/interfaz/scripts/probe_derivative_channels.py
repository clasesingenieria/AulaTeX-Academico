from __future__ import annotations

from src.bot import _build_channel_text, _build_note_action_messages, _parse_derivative_markdown
from src.notes import build_derivative_markdown


def main() -> None:
    text = (
        "Veo la deuda como un instrumento de dominacion que asocio con el ascenso de Inglaterra y con la formacion "
        "de un imperio esclavista y clasista. Quiero investigar si ese sistema tambien se apoyo en ciertas ideas "
        "religiosas o culturales, y por que logro imponerse sobre otros grandes imperios, como el romano, el espanol, "
        "el egipcio y el griego, quiza menos injustos. Tambien me interesa analizar si el socialismo intento evitar "
        "ese mecanismo, pero no pudo sostenerse sin una base minima de explotacion legitimada por la idea del merito. "
        "Habra que ver como se sostiene el actual imperio y como hacerlo evolucionar para disminuir la base de la explotacion."
    )

    note_context = {
        "title": "Deuda, imperio y explotacion",
        "corrected_text": text,
        "concepts": [
            {"term": "deuda", "definition": "mecanismo economico y politico"},
            {"term": "imperio", "definition": "estructura de poder y expansion"},
            {"term": "merito", "definition": "marco de legitimacion social"},
        ],
        "related_terms": ["capitalismo", "socialismo", "dominio"],
    }

    messages = _build_note_action_messages("research", note_context)
    print("=== PROMPT USER (extracto) ===")
    print(messages[1]["content"][:1200])
    print("\n=== VERIFICACION CONTRATO ===")
    print("Contiene contrato de salida:", "Contrato de salida:" in messages[1]["content"])
    print("Contiene objetivo audio ~80%:", "audio ~80%" in messages[1]["content"])
    print("Contiene objetivo telegram ~60%:", "telegram ~60%" in messages[1]["content"])
    print("Contiene objetivo clipboard ~20%:", "clipboard ~20%" in messages[1]["content"])

    simulated_model_output = """
La deuda funciona como arquitectura de subordinacion cuando coordina coercion fiscal, monopolios comerciales y justificacion moral del sacrificio desigual.

En el caso ingles, el credito publico, la expansion naval y la financiarizacion de rentas coloniales permitieron concentrar poder y sostener un orden clasista con respaldo institucional. La comparacion con Roma, Espana, Egipto y Grecia exige cautela: cada imperio tuvo matrices distintas de extraccion, ciudadania y legitimidad; por eso la pregunta no es cual fue "menos injusto" en abstracto, sino que tecnologia politica de explotacion resulto mas escalable y estable. La hipotesis religiosa-cultural apunta a eticas del trabajo, disciplina social y narrativas de eleccion moral que convirtieron desigualdades historicas en meritos individuales aparentes.

1. Separar mecanismos: deuda soberana, deuda privada y deuda colonial.
2. Construir una matriz comparativa entre imperios con variables: forma de tributo, movilidad social, violencia legal y propaganda moral.
3. Contrastar la hipotesis del merito con series historicas de propiedad, salario y acceso politico.
4. Analizar por que experimentos socialistas redujeron ciertos abusos pero reprodujeron jerarquias burocraticas.
5. Diseñar criterios de transicion para disminuir explotacion sin colapsar coordinacion economica.

La tesis requiere validacion documental sobre banca, legislacion mercantil, esclavitud, teologia politica y fiscalidad comparada. Tambien supone que la legitimidad cultural modifica la persistencia de estructuras economicas.

La clave no es negar toda deuda, sino desactivar su uso como tecnologia de dominio: limitar captura oligopolica, redistribuir poder de decision y reemplazar la moral del merito aislado por responsabilidad institucional verificable.
""".strip()

    md = build_derivative_markdown(note_path=__import__("pathlib").Path("demo.md"), action="research", content=simulated_model_output, note_title=note_context["title"])
    payload = _parse_derivative_markdown(md)

    audio_text = _build_channel_text(payload, "audio")
    telegram_text = _build_channel_text(payload, "telegram")
    clipboard_text = _build_channel_text(payload, "clipboard")

    print("\n=== LONGITUDES (aprox por efecto) ===")
    print("audio chars:", len(audio_text))
    print("telegram chars:", len(telegram_text))
    print("clipboard chars:", len(clipboard_text))

    print("\n=== RATIO VS AUDIO ===")
    base = max(len(audio_text), 1)
    print("telegram/audio:", round(len(telegram_text) / base, 2))
    print("clipboard/audio:", round(len(clipboard_text) / base, 2))

    print("\n=== SALIDA TELEGRAM (extracto) ===")
    print(telegram_text[:900])

    print("\n=== SALIDA CLIPBOARD ===")
    print(clipboard_text)


if __name__ == "__main__":
    main()
