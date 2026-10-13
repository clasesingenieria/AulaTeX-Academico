from pathlib import Path
import json,sys,shutil
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor,white,black
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1]
COURSE=ROOT/'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga'
ASSET=COURSE/'assets-plan-de-negocios/actividad-11-2026-10-01';ASSET.mkdir(parents=True,exist_ok=True)
data=json.loads((ROOT/'.tmp-itesca-20260928/actividad11-proceso.json').read_text(encoding='utf-8'))
(ASSET/'proceso.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
pdfmetrics.registerFont(TTFont('Arial','C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialB','C:/Windows/Fonts/arialbd.ttf'))
c=canvas.Canvas(str(ASSET/'flujo-vectorial.pdf'),pagesize=(468,575))
c.setTitle('Flujo de cambio de aceite y filtro en AM Taller')
c.setAuthor('Martín Jonathan de la Cruz Muñoz')
style=ParagraphStyle('node',fontName='Arial',fontSize=10.5,leading=12.1,alignment=1,textColor=black)
def txt(x,y,t,size=9,bold=False):
 c.setFont('ArialB' if bold else 'Arial',size);c.setFillColor(black);c.drawCentredString(x,y,t)
def arrow(points,label='',lx=None,ly=None):
 c.setStrokeColor(HexColor('#465968'));c.setLineWidth(.9)
 p=c.beginPath();p.moveTo(*points[0])
 for x,y in points[1:]:p.lineTo(x,y)
 c.drawPath(p)
 import math
 x,y=points[-1];a=math.atan2(y-points[-2][1],x-points[-2][0]);length=5
 p=c.beginPath();p.moveTo(x,y);p.lineTo(x-length*math.cos(a-.45),y-length*math.sin(a-.45));p.lineTo(x-length*math.cos(a+.45),y-length*math.sin(a+.45));p.close()
 c.setFillColor(HexColor('#465968'));c.drawPath(p,fill=1,stroke=0)
 if label:txt(lx if lx is not None else x+15,ly if ly is not None else y+10,label)
def circle(x,y,label):
 c.setStrokeColor(HexColor('#465968'));c.setFillColor(white);c.circle(x,y,13,stroke=1,fill=1);txt(x,y-3.5,label,11,True)
def node(i,y,x=208,w=268):
 st=data['steps'][i-1];c.setStrokeColor(HexColor('#8B98A4'));c.setFillColor(HexColor('#E7EEF4') if '?' in st['title'] else HexColor('#F7F9FA'))
 c.roundRect(x-w/2,y-20,w,40,3,stroke=1,fill=1)
 par=Paragraph(f'<b>{i}.</b> '+escape(st['title']),style);pw,ph=par.wrap(w-14,40);assert ph<=36,(i,ph)
 par.drawOn(c,x-w/2+7,y-ph/2)
def pill(y,t):
 c.setFillColor(white);c.setStrokeColor(HexColor('#465968'));c.roundRect(167,y-9,82,18,8,fill=1,stroke=1);txt(208,y-3,t,9,True)
# Page 1. Repeated lettered connectors avoid crossing the main process.
ys={i:520-(i-1)*54 for i in range(1,10)}
pill(558,'Inicio');arrow([(208,549),(208,540)])
for i,y in ys.items():node(i,y)
for i in range(1,9):
 arrow([(208,ys[i]-20),(208,ys[i+1]+20)],'Sí' if i in [3,5,8] else '',230,(ys[i]+ys[i+1])/2-3)
for i in [3,5,9]:
 circle(419,ys[i],'C');arrow([(342,ys[i]),(406,ys[i])],'No',369,ys[i]+8);txt(419,ys[i]-26,'a paso 15',8.5)
circle(22,ys[8],'A');arrow([(35,ys[8]),(74,ys[8])]);txt(22,ys[8]-26,'de 12/13',8)
circle(208,24,'B');arrow([(208,ys[9]-20),(208,37)],'Sí',230,53)
arrow([(74,ys[8]-10),(52,ys[8]-10),(52,24),(195,24)],'No',65,ys[8]-23)
txt(280,20,'B continúa en paso 10',9)
c.showPage()
# Page 2. A returns to step 8; C converges at step 15.
ys2={i:500-(i-10)*75 for i in range(10,17)}
circle(208,556,'B');arrow([(208,543),(208,520)])
for i,y in ys2.items():node(i,y)
for i in range(10,16):
 lab={10:'Sí',12:'Concluido',13:'Sí'}.get(i,'')
 arrow([(208,ys2[i]-20),(208,ys2[i+1]+20)],lab,240,(ys2[i]+ys2[i+1])/2-3)
circle(419,500,'C');arrow([(342,500),(406,500)],'No',368,508);txt(419,474,'a paso 15',8.5)
for i in [12,13]:
 y=ys2[i];circle(419,y,'A');arrow([(342,y),(406,y)])
 txt(376,y+18,'Hallazgo' if i==12 else 'Otro trabajo',8.5);txt(376,y+7,'adicional' if i==12 else 'necesario',8.5)
 txt(419,y-26,'a paso 8',8.5)
arrow([(74,275),(30,275),(30,350),(74,350)])
c.saveState();c.translate(18,312);c.rotate(90);txt(0,0,'No: corregir lo autorizado',8.5);c.restoreState()
circle(419,125,'C');arrow([(406,125),(342,125)]);txt(419,98,'de 3/5/9/10',8)
pill(10,'Fin');arrow([(208,30),(208,19)])
c.save()
print(ASSET/'flujo-vectorial.pdf')
