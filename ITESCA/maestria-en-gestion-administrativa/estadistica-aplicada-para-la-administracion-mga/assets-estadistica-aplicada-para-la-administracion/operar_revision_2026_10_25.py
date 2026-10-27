"""Reemplazar solo los cuatro PDF autorizados, después de su QA final local.

Los borrados afectan exclusivamente la copia en borrador del selector Moodle;
la entrega vigente permanece hasta guardar el formulario. Sin credenciales en disco.
Interfaz draft list/delete cotejada con Moodle MOODLE_405_STABLE.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

from operar_entregas_2026_10_24 import Portal

SUBJECT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).resolve().parent
DELIVERIES = SUBJECT / 'entregas-estadistica-aplicada-para-la-administracion'
NOTES = SUBJECT / 'referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/revision-resumen-fusion-2026-10-25'
ASSIGNMENTS = {1747: (1, 'Actividad-1-Infografia.pdf'), 1748: (2, 'Actividad-2-Investigacion.pdf'),
               1754: (3, 'Actividad-3-Investigacion-estimacion.pdf'), 1755: (4, 'Actividad-4-Ejercicios-distribuciones.pdf')}


class RevisionPortal(Portal):
    qa_manifest = ASSETS / 'validacion-resumen-fusion-2026-10-25.json'
    evidence_dir = NOTES
    revision_name = 'resumen_indice_declaracion_ia_fusion_visual'

    def draft_request(self, form, action, **extra):
        data = self.formdata(form)
        if 'files_filemanager' not in data or 'sesskey' not in data:
            raise RuntimeError('not_submission_filemanager')
        fields = {'action': action, 'itemid': data['files_filemanager'],
                  'sesskey': data['sesskey'], 'filepath': '/'}
        fields.update(extra)
        previous = self.soup, self.url, self.raw
        try:
            result = json.loads(self.send('/repository/draftfiles_ajax.php', fields))
        finally:
            self.soup, self.url, self.raw = previous
        if isinstance(result, dict) and result.get('error'):
            raise RuntimeError('draft_operation_failed')
        return result

    def file_options(self):
        options = super().file_options()
        if getattr(self, '_empty_draft_verified', False):
            options = dict(options, filecount=0)
        return options

    def revise(self, assignment):
        activity, name = ASSIGNMENTS[int(assignment)]
        local = DELIVERIES / name
        expected_hash = hashlib.sha256(local.read_bytes()).hexdigest()
        qa = json.loads(self.qa_manifest.read_text(encoding='utf-8'))
        if not qa.get('passed') or not qa.get('visual_review_completed'):
            raise RuntimeError('final_local_qa_required')
        records = [item for item in qa['deliveries'] if item['activity'] == activity]
        if len(records) != 1 or records[0]['sha256'] != expected_hash:
            raise RuntimeError('delivery_hash_not_approved')
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
        if listed.get('filecount') != 1 or len(files) != 1 or files[0].get('filename') != name or files[0].get('filepath') != '/':
            raise RuntimeError('expected_single_draft_file_required')
        result = self.draft_request(form, 'delete', filename=name)
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
        if listed.get('filecount') != 1 or len(listed.get('list', [])) != 1 or listed['list'][0].get('filename') != name:
            raise RuntimeError('new_draft_pdf_not_present')
        if not form.find(attrs={'name': 'submitbutton'}):
            raise RuntimeError('save_button_not_observed')
        state = super().command({'op': 'form', 'index': index, 'button': 'submitbutton'})
        if 'Enviado para calificar' not in state['text']:
            raise RuntimeError('submitted_state_not_confirmed')
        verify = super().command({'op': 'verify_file', 'path': str(local)})
        if not verify['matches_local']:
            raise RuntimeError('download_hash_mismatch')
        evidence = {'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'assignment': int(assignment),
                    'activity': activity, 'revision': self.revision_name,
                    'state': state, 'verification': verify}
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        (self.evidence_dir / f'{assignment}-estado-final.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
        return {'assignment': int(assignment), 'filename': name, 'status': 'Enviado para calificar',
                'download_matches_local': True, 'sha256': verify['sha256']}


if __name__ == '__main__':
    try:
        portal = RevisionPortal()
        print(json.dumps({'authenticated': True}), flush=True)
        for line in sys.stdin:
            try:
                command = json.loads(line)
                result = portal.revise(command['assignment']) if command['op'] == 'revise' else portal.command(command)
                print(json.dumps(result, ensure_ascii=True), flush=True)
            except Exception as error:
                print(json.dumps({'operation_failed': True, 'error_type': type(error).__name__, 'reason': str(error) if isinstance(error, RuntimeError) else 'operation_error'}), flush=True)
    except Exception as error:
        print(json.dumps({'authenticated': False, 'error_type': type(error).__name__}), flush=True)
        raise SystemExit(1)
