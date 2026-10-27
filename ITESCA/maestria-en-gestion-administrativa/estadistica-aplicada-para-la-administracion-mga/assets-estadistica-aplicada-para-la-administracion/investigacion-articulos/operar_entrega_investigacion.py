"""Actualizar exclusivamente la investigación 1748 con su PDF aprobado localmente."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import sys

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent
SUBJECT = ASSETS.parent
sys.path.insert(0, str(ASSETS))
from operar_revision_2026_10_25 import RevisionPortal


class InvestigacionPortal(RevisionPortal):
    qa_manifest = ASSETS / 'validacion-investigacion-fichas-2026-10-25.json'
    evidence_dir = SUBJECT / 'referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/revision-investigacion-fichas-2026-10-25'
    revision_name = 'investigacion_amplia_tres_tiempos_fichas_por_articulo'

    def revise(self, assignment):
        if int(assignment) != 1748:
            raise RuntimeError('only_research_assignment_authorized_in_this_revision')
        return super().revise(assignment)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submit', action='store_true', required=True)
    parser.parse_args()
    qa = json.loads(InvestigacionPortal.qa_manifest.read_text(encoding='utf-8'))
    if not qa.get('passed') or not qa.get('visual_review_completed'):
        raise RuntimeError('final_local_qa_required_before_login')
    portal = InvestigacionPortal()
    result = portal.revise(1748)
    qa['platform_submission'] = {'assignment': 1748, 'status': result['status'],
                                 'download_matches_local': result['download_matches_local'],
                                 'sha256': result['sha256'], 'verified_at_utc': datetime.now(timezone.utc).isoformat(),
                                 'evidence': (portal.evidence_dir / '1748-estado-final.json').relative_to(SUBJECT).as_posix()}
    InvestigacionPortal.qa_manifest.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'operation_failed': True, 'error_type': type(error).__name__,
                          'reason': str(error) if isinstance(error, RuntimeError) else 'operation_error'}), flush=True)
        raise SystemExit(1)
