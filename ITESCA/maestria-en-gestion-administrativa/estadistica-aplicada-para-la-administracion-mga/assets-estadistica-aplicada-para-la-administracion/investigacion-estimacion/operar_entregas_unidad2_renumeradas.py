"""Actualiza en Moodle las entregas renumeradas de la Unidad 2:
- Tarea 1754 (2.1 Investigación documental y aplicada) -> Actividad-4-Investigacion-estimacion.pdf (5 páginas)
- Tarea 1755 (2.2 Ejercicios) -> Actividad-5-Ejercicios-distribuciones.pdf (9 páginas)
La Actividad 3 (1.3 Cuestionario, módulo 1749) es un cuestionario en línea ya finalizado y solo tiene reporte en la raíz.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent
SUBJECT = ASSETS.parent
DELIVERIES = SUBJECT / 'entregas-estadistica-aplicada-para-la-administracion'
EVIDENCE_DIR = SUBJECT / 'referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/revision-renumeracion-2026-10-25'
MANIFEST = ASSETS / 'validacion-renumeracion-estimacion-2026-10-25.json'

sys.path.insert(0, str(ASSETS))
from operar_revision_2026_10_25 import RevisionPortal  # noqa: E402

TARGETS = {
    1754: (4, 'Actividad-4-Investigacion-estimacion.pdf'),
    1755: (5, 'Actividad-5-Ejercicios-distribuciones.pdf'),
}


class RenumberedUnit2Portal(RevisionPortal):
    qa_manifest = MANIFEST
    evidence_dir = EVIDENCE_DIR
    revision_name = 'renumeracion_actividades_3_4_5_y_fichas_estimacion'

    def replace_submission(self, assignment: int):
        activity, new_name = TARGETS[int(assignment)]
        local = DELIVERIES / new_name
        expected_hash = hashlib.sha256(local.read_bytes()).hexdigest()
        qa = json.loads(self.qa_manifest.read_text(encoding='utf-8'))
        if not qa.get('passed') or not qa.get('visual_review_completed'):
            raise RuntimeError('final_local_qa_required')

        self.get(f'/mod/assign/view.php?id={assignment}')
        choices = [(i, form) for i, form in enumerate(self.soup.find_all('form'))
                   if 'Editar entrega' in form.get_text(' ', strip=True)]
        if len(choices) != 1:
            raise RuntimeError('editable_submission_not_available')
        super().command({'op': 'form', 'index': choices[0][0]})
        forms = self.soup.find_all('form')
        choices = [(i, form) for i, form in enumerate(forms) if form.find(attrs={'name': 'files_filemanager'})]
        if len(choices) != 1:
            raise RuntimeError('unique_filemanager_form_required')
        index, form = choices[0]

        listed = self.draft_request(form, 'list')
        files = listed.get('list', [])
        if listed.get('filecount') != 1 or len(files) != 1 or files[0].get('filepath') != '/':
            raise RuntimeError('expected_single_draft_file_required')
        old_name = files[0]['filename']
        result = self.draft_request(form, 'delete', filename=old_name)
        if not result:
            raise RuntimeError('draft_replacement_failed')
        listed = self.draft_request(form, 'list')
        if listed.get('filecount') != 0 or listed.get('list'):
            raise RuntimeError('draft_not_empty')

        self._empty_draft_verified = True
        try:
            upload = super().command({'op': 'upload', 'path': str(local), 'form_index': index})
        finally:
            self._empty_draft_verified = False
        if not upload.get('upload_ok'):
            raise RuntimeError('new_pdf_upload_failed')

        listed = self.draft_request(form, 'list')
        if listed.get('filecount') != 1 or len(listed.get('list', [])) != 1 or listed['list'][0].get('filename') != new_name:
            raise RuntimeError('new_draft_pdf_not_present')
        if not form.find(attrs={'name': 'submitbutton'}):
            raise RuntimeError('save_button_not_observed')

        state = super().command({'op': 'form', 'index': index, 'button': 'submitbutton'})
        if 'Enviado para calificar' not in state['text']:
            raise RuntimeError('submitted_state_not_confirmed')
        verify = super().command({'op': 'verify_file', 'path': str(local)})
        if not verify['matches_local'] or verify['sha256'] != expected_hash:
            raise RuntimeError('download_hash_mismatch')

        evidence = {
            'verified_at_utc': datetime.now(timezone.utc).isoformat(),
            'assignment': int(assignment),
            'activity': activity,
            'previous_filename_replaced': old_name,
            'filename': new_name,
            'revision': self.revision_name,
            'state': state,
            'verification': verify,
        }
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        (self.evidence_dir / f'{assignment}-estado-final.json').write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        return {
            'assignment': int(assignment),
            'activity': activity,
            'previous_filename': old_name,
            'filename': new_name,
            'status': 'Enviado para calificar',
            'download_matches_local': True,
            'sha256': verify['sha256'],
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submit', action='store_true')
    args = parser.parse_args()
    if not args.submit:
        raise SystemExit('Este script requiere --submit explícito.')
    portal = RenumberedUnit2Portal()
    results = []
    for assignment in (1754, 1755):
        results.append(portal.replace_submission(assignment))
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    data['platform_submissions'] = results
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'updated': results}, ensure_ascii=True))


if __name__ == '__main__':
    main()
