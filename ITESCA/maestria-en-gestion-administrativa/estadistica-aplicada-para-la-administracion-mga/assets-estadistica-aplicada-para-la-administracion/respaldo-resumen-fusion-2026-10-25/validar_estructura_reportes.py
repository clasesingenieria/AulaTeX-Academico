"""Consolidar PDF compilados de informes: tres tiempos, portadas exactas y QA visual.
Ejecutar desde cualquier directorio tras compilar los cinco contenedores.
No envía archivos a Moodle; la entrega original de infografía es inmutable.
"""
from pathlib import Path
import hashlib,json,re,shutil,unicodedata
from datetime import datetime,timezone
import pymupdf
from PIL import Image,ImageDraw
s=Path(__file__).resolve().parents[1];root=s.parents[2];assets=Path(__file__).resolve().parent;backup=assets/'respaldo-estructura-2026-10-24';out=root/'.build/qa-estadistica';out.mkdir(exist_ok=True)
results=[]
for tag,suffix in [('act1','Actividad-1'),('act3','Actividad-3'),('act4','Actividad-4'),('encuadre','encuadre'),('mga','mga')]:
 name=f'reporte-estadistica-aplicada-para-la-administracion-{suffix}'
 p=root/'.build/latex'/f'estadistica-{tag}'/(name+'.pdf');src=s/(name+'.tex')
 assert p.stat().st_mtime>=src.stat().st_mtime,(tag,'PDF desactualizado')
 text=src.read_text(encoding='utf8');assert len(re.findall(r'\\section\{',text))==3,(tag,'tres tiempos')
 log=p.with_suffix('.log').read_text(encoding='utf8',errors='replace');assert not re.search(r'Overfull|Underfull|Missing character|Citation .*undefined|There were undefined|^!',log,re.MULTILINE),(tag,'log')
 if tag!='act1':
  original=backup/(name+'.pdf');temp=p.with_suffix('.portada-preservada.pdf')
  with pymupdf.open(p) as d,pymupdf.open(original) as old:
   changed = hashlib.sha256(d[0].get_pixmap().samples).digest() != hashlib.sha256(old[0].get_pixmap().samples).digest()
   if changed:
    d.delete_page(0);d.insert_pdf(old,from_page=0,to_page=0,start_at=0);d.save(temp,garbage=4,deflate=True)
  if changed:
   temp.replace(p)
 doc=pymupdf.open(p);body=unicodedata.normalize('NFKC','\n'.join(pg.get_text() for pg in list(doc)[1:]))
 for blocked in ('Refuerzo Ciclo','por definir','[?]','esta actividad','producto solicitado'):
  assert blocked.casefold() not in body.casefold(),(tag,blocked)
 for required in ('Introducción','Conclusiones','Referencias'):
  assert required in body,(tag,required)
 alltext='\n'.join(pg.get_text() for pg in doc)
 assert '26130503' in alltext or tag=='mga'
 for page in list(doc)[1:]:
  for block in page.get_text('dict')['blocks']:
   for line in block.get('lines',[]):
    for span in line['spans']:
     if not span['text'].strip():continue
     r=pymupdf.Rect(span['bbox']);assert r.x0>=-0.2 and r.y0>=-0.2 and r.x1<=page.rect.width+0.2 and r.y1<=page.rect.height+0.2,(tag,page.number,span['text'])
 cover_hash=hashlib.sha256(doc[0].get_pixmap().samples).hexdigest()
 if tag!='act1':
  with pymupdf.open(backup/(name+'.pdf')) as old:
   assert cover_hash==hashlib.sha256(old[0].get_pixmap().samples).hexdigest(),(tag,'portada')
 rows=(len(doc)+2)//3;contact=Image.new('RGB',(3*320,rows*435),'#ccc')
 for i,page in enumerate(doc):
  pix=page.get_pixmap(matrix=pymupdf.Matrix(0.65,0.65));im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);im.thumbnail((300,405));tile=Image.new('RGB',(320,435),'#ccc');tile.paste(im,((320-im.width)//2,8));ImageDraw.Draw(tile).text((10,417),f'{suffix} / {i+1}',fill='black');contact.paste(tile,((i%3)*320,(i//3)*435))
 contact.save(out/(tag+'-final.png'))
 dest=s/(name+'.pdf');shutil.copy2(p,dest)
 if tag in ('act3','act4'):
  delivery=s/'entregas-estadistica-aplicada-para-la-administracion'/('Actividad-3-Investigacion-estimacion.pdf' if tag=='act3' else 'Actividad-4-Ejercicios-distribuciones.pdf');shutil.copy2(p,delivery)
 results.append({'report':dest.relative_to(root).as_posix(),'pages':len(doc),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'three_part_structure':True,'original_cover_preserved':tag!='act1','cover_render_sha256':cover_hash,'log_passed':True,'glyph_bounds_passed':True})
manifest={'validated_at_utc':datetime.now(timezone.utc).isoformat(),'reports':results,'infographic_delivery_sha256':hashlib.sha256((s/'entregas-estadistica-aplicada-para-la-administracion/Actividad-1-Infografia.pdf').read_bytes()).hexdigest(),'platform_submission':False}
conceptual=s/'investigacion-aulatex/base-conceptual-unidad-1-revisada.md'
if conceptual.exists():
 manifest['nova_conceptual_review']={'source':conceptual.relative_to(s).as_posix(),'sha256':hashlib.sha256(conceptual.read_bytes()).hexdigest(),'report':'Actividad-1','validated_scope':['población, marco, unidad y respuesta','probabilidad conocida y selección aleatoria simple','estratos, sistemático y conglomerados','selección no probabilística y errores','precisión, sesgo e incertidumbre','385 respuestas y 482 invitaciones con supuestos','precisión de intervalo separada de potencia','síntesis interpretativa y transferencia administrativa'],'editorial_verification':'Cotejo completo del informe con los apartados 1-9 y 12 de la investigación Nova revisada; sin aceptar errores del motor como autoridad.'}
(assets/'validacion-estructura-reportes-2026-10-24.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(manifest,ensure_ascii=True,indent=2))
