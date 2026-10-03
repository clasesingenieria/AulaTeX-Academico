from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib
import build_documents as b
p=b.OUT/'Tarea9_DeLaCruzMunoz.docx'
old=(b.WORK/'covey.png').read_bytes()
new=b.covey_image().read_bytes()
with ZipFile(p) as z:
    records=[(i,z.read(i.filename)) for i in z.infolist()]
matches=[i.filename for i,x in records if x==old]
assert len(matches)==1,matches
with ZipFile(p,'w',ZIP_DEFLATED) as z:
    for i,x in records:z.writestr(i,new if i.filename in matches else x)
print('Updated diagram without changing pagination')
