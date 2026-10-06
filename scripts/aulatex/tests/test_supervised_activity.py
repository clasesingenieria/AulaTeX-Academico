import json
import unittest

from scripts.aulatex.supervised_activity import parse_object, validate_content, approved_review, content_digest


class StructuredActivityTests(unittest.TestCase):
    def setUp(self):
        self.baseline = {"title": "Caso documental", "problem": "Brecha documental", "general_question": "Pregunta general", "specific_questions": ["P1", "P2", "P3", "P4"]}
        self.data = dict(self.baseline, content={
            "general_objective": "Analizar la correspondencia documental del caso y sus componentes dentro del periodo delimitado.",
            "specific_objectives": [f"Identificar componentes observables del caso {i}." for i in range(4)],
            "verification_products": ["Matriz de evidencia documental verificada."]*4,
            "procedures": ["Revisión trazable de documentos del caso."]*4,
            "introduction": "Contexto", "methodological_alignment": "Método",
            "conclusion": "Cierre", "ai_assistance_note": "Redacción mediante GPT-5-mini."},
            references=[{"key": str(i)} for i in range(3)])

    def test_accepts_fenced_json_but_not_prose_or_array(self):
        self.assertEqual(parse_object('```json\n{"x":1}\n```'), {"x": 1})
        for value in ['[]', 'Ya está hecho: {"x":1}']:
            with self.assertRaises(ValueError):
                parse_object(value)

    def test_preservation_is_literal_not_semantic(self):
        self.assertTrue(validate_content(self.data, self.baseline)["passed"])
        self.data["problem"] += " alterado"
        self.assertIn("changed_baseline:problem", validate_content(self.data, self.baseline)["failures"])

    def test_questions_and_objectives_must_align_in_count(self):
        self.data["content"]["specific_objectives"].pop()
        self.assertIn("question_alignment:specific_objectives", validate_content(self.data, self.baseline)["failures"])

    def test_rejects_metaobjectives_and_foreign_identity(self):
        self.data["content"]["general_objective"] = "Formular objetivos de investigación para realizar esta actividad del Seminario I."
        self.data["content"]["conclusion"] = "Universidad Abierta UnADM ES2611202040"
        failures = validate_content(self.data, self.baseline)["failures"]
        self.assertIn("meta_objective_or_nonobservable_verb", failures)
        self.assertIn("foreign_identity_or_placeholder", failures)

    def test_spanish_todo_is_not_a_placeholder(self):
        self.data["content"]["conclusion"] = "En todo momento se mantiene el alcance documental."
        self.assertTrue(validate_content(self.data, self.baseline)["passed"])
        self.data["content"]["conclusion"] = "[TODO]"
        self.assertIn("foreign_identity_or_placeholder", validate_content(self.data, self.baseline)["failures"])

    def test_approval_is_bound_to_review_and_content(self):
        review = {'passed':True,'blocking_issues':[]}
        receipt = {'content_sha256':content_digest(self.data),'review_sha256':content_digest(review)}
        self.assertTrue(approved_review(review,receipt,self.data))
        self.data['content']['general_objective'] += ' Modificado.'
        self.assertFalse(approved_review(review,receipt,self.data))
        receipt['content_sha256'] = content_digest(self.data)
        review['passed'] = False
        receipt['review_sha256'] = content_digest(review)
        self.assertFalse(approved_review(review,receipt,self.data))


if __name__ == "__main__":
    unittest.main()
