from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/referencias-seminario-i/vtaxi-2026-09-27'
OUT.mkdir(parents=True,exist_ok=True)
urls={
'ley-movilidad-nl':'https://www.hcnl.gob.mx/trabajo_legislativo/leyes/leyes/ley_de_movilidad_sostenible_y_accesibilidad_para_el_estado_de_nuevo_leon/',
'icet':'https://icetnl.mx/',
'icet-plataformas':'https://www.somosicet.com/cursos/plataformas-digitales',
'omrani-metadatos':'https://api.crossref.org/works/10.1109/TEM.2022.3215727',
'troise-metadatos':'https://api.crossref.org/works/10.1016/j.techfore.2021.121227'
}
with sync_playwright() as p:
    b=p.chromium.launch(headless=True)
    page=b.new_page()
    for name,url in urls.items():
        try:
            page.goto(url,timeout=45000,wait_until='domcontentloaded')
            text=page.locator('body').inner_text()
            (OUT/(name+'.txt')).write_text(text,encoding='utf8')
            print(name,len(text),flush=True)
            if name=='ley-movilidad-nl':
                for start,end in [('Artículo 80.','Artículo 84.'),('Artículo 99.','Artículo 101.')]:
                    print(text[text.find(start):text.find(end)],flush=True)
            elif 'metadatos' in name:
                m=json.loads(text)['message']
                print({k:m.get(k) for k in ['title','published','published-print','published-online','volume','page']},flush=True)
        except Exception as e:
            print(name,'FAILED',type(e).__name__,flush=True)
    b.close()
(OUT/'urls.json').write_text(json.dumps(urls,ensure_ascii=False,indent=2),encoding='utf8')
