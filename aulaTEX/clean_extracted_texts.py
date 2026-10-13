from pathlib import Path
import re

folder = Path(r"D:\Documentos\AulaTeX-Academico\UANL\ingeniero-agronomo\responsabilidad-social-y-desarrollo-sustentable")
for f in folder.glob('*.txt'):
    if f.name.endswith('.txt') and not f.name.startswith('cleaned_'):
        s = f.read_text(encoding='utf-8')
        # remove xml tags
        s2 = re.sub(r'<[^>]+>', ' ', s)
        # replace multiple whitespace
        s2 = re.sub(r'\s+', ' ', s2).strip()
        out = folder / ('cleaned_' + f.name)
        out.write_text(s2, encoding='utf-8')
        print('WROTE', out)
print('done')
