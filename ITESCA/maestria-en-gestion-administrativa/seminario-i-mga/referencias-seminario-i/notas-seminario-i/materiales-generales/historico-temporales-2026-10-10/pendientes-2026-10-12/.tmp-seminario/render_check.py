from pathlib import Path
from pypdf import PdfReader
from pdf2image import convert_from_path
from PIL import Image,ImageDraw
import json
ROOT=Path(__file__).resolve().parent
POP=r'C:\Users\Sysx\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin'
reports={}
for folder in ['qa8','qa9','qa-registro']:
    p=next((ROOT/folder).glob('*.pdf'))
    r=PdfReader(p)
    texts=[x.extract_text() for x in r.pages]
    (ROOT/folder/'text.txt').write_text('\n\n'.join(f'PAGE {i+1}\n{x}' for i,x in enumerate(texts)),encoding='utf8')
    pages=convert_from_path(p,dpi=100,poppler_path=POP)
    for i,page in enumerate(pages):page.save(ROOT/folder/f'page-{i+1}.png')
    for k in range(0,len(pages),6):
        contact=Image.new('RGB',(3*425,2*570),'#CCCCCC')
        for j,im in enumerate(pages[k:k+6]):
            im=im.copy();im.thumbnail((415,537));x=(j%3)*425+5;y=(j//3)*570+25
            contact.paste(im,(x,y));ImageDraw.Draw(contact).text((x,y-18),f'{folder} page {k+j+1}',fill='black')
        contact.save(ROOT/folder/f'contact-{k//6+1}.png')
    reports[folder]=[{'page':i+1,'chars':len(t),'first':t[:120],'last':t[-100:]} for i,t in enumerate(texts)]
    print(folder,len(pages))
(ROOT/'pages.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf8')
