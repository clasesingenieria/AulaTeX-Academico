from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "extractor-conceptos-ideas" / "src"))

from fichador.api_client import chat_json_data, get_api_config
from fichador.cli import main


def response(text: str, ok: bool = True) -> SimpleNamespace:
    return SimpleNamespace(ok=ok, text=text, engine="GPT-5.6-SOL", requested_deployment="gpt-5.6-sol", provider_model="gpt-5.6-sol", finish_reason="completed", usage={})


class AulaTeXExtractorTests(unittest.TestCase):
    def test_selected_engine_and_receipt(self):
        config = get_api_config("aulatex", aulatex_engine="GPT-5.6-SOL")
        client = SimpleNamespace(call=Mock(return_value=response('{"kept":["Soberania"]}')))
        stream = io.StringIO()
        with redirect_stdout(stream):
            result = chat_json_data(client, config, "system", "user")
        self.assertEqual(result, {"kept": ["Soberania"]})
        self.assertEqual(client.call.call_args.args[0], "GPT-5.6-SOL")
        self.assertEqual(client.call.call_count, 1)
        receipt = json.loads(stream.getvalue().removeprefix("LLM_RECEIPT "))
        self.assertEqual(receipt["requested_deployment"], "gpt-5.6-sol")
        self.assertNotIn("api_key", receipt)

    def test_failure_and_invalid_json_stop_without_fallback(self):
        config = get_api_config("aulatex", aulatex_engine="GPT-5.6-SOL")
        for reply, exception in [(response("", False), RuntimeError), (response("not json"), ValueError)]:
            client = SimpleNamespace(call=Mock(return_value=reply))
            with redirect_stdout(io.StringIO()), self.assertRaises(exception):
                chat_json_data(client, config, "system", "user")
            self.assertEqual(client.call.call_count, 1)

    def test_full_cli_exports_literal_quotes_with_sol(self):
        def call(engine, prompt, **kwargs):
            self.assertEqual(engine, "GPT-5.6-SOL")
            if "CONCEPTO:" in prompt:
                return response('{"suficiente":true,"cobertura":{},"faltantes":[],"consultas":[],"nota":"evidencia de prueba"}')
            return response('{"kept":["Soberania"],"discarded":[],"notes":"prueba"}')

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "fuente.txt"
            source_text = "Soberania es la capacidad del Estado para ejercer su autoridad en un territorio. El poder publico se organiza mediante instituciones y normas. La soberania se relaciona con la independencia y con las decisiones de la comunidad politica."
            source.write_text(source_text, encoding="utf-8")
            concepts = root / "conceptos.txt"
            concepts.write_text("Soberania\n", encoding="utf-8")
            planning = root / "planeacion.txt"
            planning.write_text("Tema: Soberania\nObjetivo: Comprender la soberania del Estado.\nActividad: Valoracion de decisiones.\n", encoding="utf-8")
            output = root / "salida"
            with patch("aulatex.llm_bridge.AulaTeXLLMClient.call", side_effect=call) as mocked, redirect_stdout(io.StringIO()):
                main(["--fuentes", str(source), "--planeacion", str(planning), "--conceptos", str(concepts), "--salida", str(output), "--motor", "aulatex", "--aulatex-engine", "GPT-5.6-SOL", "--materia-slug", "teoria-del-estado-y-constitucion", "--no-planeacion-asistida-con-chat", "--no-normalizar-conceptos-con-chat", "--depurar-conceptos-por-materia", "--refinar-fichas-iterativamente", "--rondas-refinamiento", "1"])
            self.assertEqual(mocked.call_count, 2)
            for name in ["fichas_conceptos.md", "fichas_conceptos.docx", "fichas_conceptos.xlsx", "fichas_conceptos.csv", "fichas_conceptos.json", "conceptos_detectados.json", "ideas_detectadas.json", "trazabilidad_fuentes.json", "resumen_planeacion.json", "refinamiento_fichas.json", "depuracion_conceptos.json"]:
                self.assertTrue((output / name).is_file(), name)
            rows = json.loads((output / "fichas_conceptos.json").read_text(encoding="utf-8"))
            self.assertTrue(rows)
            for row in rows:
                self.assertEqual(row["ruta_fuente"], str(source))
                self.assertIn(row["cita_textual"], source_text)


if __name__ == "__main__":
    unittest.main()