"""Materializa el cotejo editorial, sin modificar las respuestas reales de Nova."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

S = Path(__file__).resolve().parents[1]
K = S / "investigacion-aulatex"
E = S / "extractor-aulatex/conceptos-estadistica-unidad-1-nova"
N = S / "referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/unidad-1-muestreo"

DATA = [
    ("Población", "Conjunto de unidades sobre el que interesa producir conocimiento, delimitado en lugar, tiempo y elegibilidad.", "holmesDefiniciones2023:L50-L57", "Clientes distintos que compraron durante un trimestre.", "No confundir personas con transacciones."),
    ("Muestra", "Subconjunto de unidades observado para obtener información sobre una población.", "holmesDefiniciones2023:L50-L57", "Clientes seleccionados de un padrón trimestral.", "La selección y respuesta delimitan la inferencia."),
    ("Unidad de observación", "Elemento al que corresponde la variable medida; su definición determina qué constituye cada observación.", "holmesDefiniciones2023:L67-L96", "Una compra cuando interesa una experiencia de servicio.", "Una persona puede producir varias compras; no son unidades intercambiables."),
    ("Parámetro", "Característica numérica de toda la población; puede estimarse con datos muestrales.", "holmesDefiniciones2023:L58-L65", "Proporción de todos los clientes trimestrales satisfechos.", "El universo y denominador deben declararse."),
    ("Estadístico", "Característica numérica calculada con los datos de la muestra.", "holmesDefiniciones2023:L58-L65", "Proporción satisfecha entre los participantes observados.", "No equivale automáticamente al parámetro."),
    ("Marco muestral", "Dispositivo operativo de identificación y selección de unidades; su cobertura puede diferir de la población objetivo.", "bradley2021:L371-L442", "Registro de clientes con medios de contacto verificados.", "Duplicados o exclusiones pueden alterar oportunidades de inclusión."),
    ("Muestreo probabilístico", "Diseño con probabilidades de inclusión positivas y conocidas, que pueden ser desiguales.", "bradley2021:L371-L442", "Seleccionar según reglas probabilísticas registradas.", "La regla aleatoria dentro de un marco no corrige cobertura o no respuesta."),
    ("Muestreo aleatorio simple", "Todas las muestras posibles del mismo tamaño tienen igual probabilidad de selección.", "holmesMuestreo2023:L249-L258", "Elegir al azar identificadores de un padrón completo.", "La igualdad de probabilidades individuales por sí sola no caracteriza este diseño."),
    ("Muestreo estratificado", "Se forman estratos y se seleccionan unidades aleatoriamente dentro de ellos; el manual ilustra asignación proporcional.", "holmesMuestreo2023:L260-L264", "Seleccionar trabajadores dentro de cada departamento.", "Asignación proporcional no define todos los diseños estratificados."),
    ("Muestreo sistemático", "Se elige un inicio aleatorio y después unidades a intervalos de una lista.", "holmesMuestreo2023:L268-L273", "Contactar cada décimo registro desde un inicio sorteado.", "Revisar orden de la lista y posibles periodicidades; no omitir inicio aleatorio."),
    ("Muestreo por conglomerados", "Se seleccionan grupos; en el diseño de una etapa ilustrado por el manual se incluyen todos sus miembros.", "holmesMuestreo2023:L265-L267", "Seleccionar sucursales y observar unidades en las elegidas.", "No confundir selección de grupos con selección dentro de todos los estratos."),
    ("Muestreo por conveniencia", "Selección de unidades disponibles o de fácil acceso, sin un diseño probabilístico conocido.", "holmesMuestreo2023:L274-L277", "Entrevistar a visitantes disponibles de una tienda.", "No permite generalización probabilística automática; puede ser exploratorio."),
    ("No respuesta", "Unidades seleccionadas no aportan datos; si la participación se relaciona con la variable, puede sesgar la estimación.", "holmesMuestreo2023:L295-L306", "Comparar respuesta por canal o segmento de clientes.", "Aumentar invitaciones no elimina por sí mismo el sesgo."),
    ("Precisión", "Menor variabilidad del estimador bajo un procedimiento de muestreo, expresada mediante error estándar o amplitud del intervalo bajo supuestos.", "bradley2021:L93-L121", "Distinguir un intervalo estrecho de una estimación bien centrada.", "Puede haber gran precisión y sesgo importante; no equivale a exactitud."),
    ("Sesgo de estimación", "Desviación sistemática asociada al proceso que produce los datos; puede persistir con muestras grandes.", "bradley2021:L93-L121", "Revisar cobertura cuando una encuesta sobrestima la demanda.", "No es únicamente un problema de tamaño ni solo de selección inicial."),
    ("Ponderación", "Contribuciones desiguales de observaciones para reflejar diseño o calibrar características conocidas de un referente.", "barrero2023:L102-L120", "Calibrar edad, sexo, educación e ingresos de participantes.", "No garantiza corregir diferencias no observadas o unidades sin cobertura."),
    ("Tamaño para proporción", "La planificación aproximada bajo muestreo aleatorio simple depende de nivel de confianza, proporción prevista y margen de error.", "holmesProporcion2023:L24-L258", "Ejemplo: ceil(1.96²·0.5·0.5/0.05²)=385 respuestas.", "La fórmula se deriva del intervalo normal aproximado y no garantiza representatividad."),
    ("Potencia", "Probabilidad de rechazar una hipótesis nula bajo una alternativa concreta; depende del efecto y condiciones del diseño.", "nistTamano:L19-L61", "Planear detección de un deterioro relevante de calidad.", "El tamaño para detectar un cambio no es el mismo problema que fijar un margen de estimación."),
    ("Asignación aleatoria", "Distribución del tratamiento dentro de los participantes delimitados para sostener una comparación causal bajo condiciones del experimento.", "bloom2024:L486-L560", "Ensayar una política de trabajo híbrido dentro de áreas elegibles.", "No convierte a las empresas participantes en una muestra probabilística de todas las empresas."),
    ("Validez externa", "Alcance de transferencia de resultados a contextos y poblaciones distintos del estudiado.", "bloom2024:L464-L485", "Contrastar funciones y condiciones antes de adoptar una política.", "No se garantiza por la aleatorización interna."),
    ("Intervalo de confianza", "Procedimiento cuyo nivel expresa la proporción de intervalos que cubrirían el parámetro en repeticiones bajo los supuestos.", "holmesProporcion2023:L349-L506", "Expresar incertidumbre de una estimación de demanda.", "No asignar sin más probabilidad posterior al parámetro dentro de un intervalo fijo."),
    ("Puntos porcentuales y cambio relativo", "La resta de porcentajes produce diferencia absoluta en puntos porcentuales; dividirla por la base produce cambio relativo.", "bloom2024:L176-L230", "7.2% - 4.8% = 2.4 puntos; 2.4 / 7.2 = un tercio relativo.", "No presentar 33% relativo como 33 puntos porcentuales."),
    ("Cortes repetidos", "Observaciones de muestras en momentos diferentes para construir indicadores, sin afirmar seguimiento de las mismas personas.", "barrero2023:L1-L120", "Seguir la proporción de jornadas desde casa en el tiempo.", "Revisar filtros, preguntas y universos para comparar periodos."),
    ("Equivalencia", "Evaluación de diferencias frente a márgenes de interés previamente especificados.", "bloom2024:L560-L610", "Examinar si un cambio en desempeño queda dentro de límites pertinentes.", "Ausencia de significación estadística no demuestra igualdad exacta."),
]


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    fichas = []
    for i, (name, definition, loc, application, limit) in enumerate(DATA, 1):
        source, locator = loc.split(":", 1)
        fichas.append({"id": f"c{i:02}", "concepto": name,
                       "definicion_sintetica": definition,
                       "fuentes": [{"id": source, "localizador": locator}],
                       "aplicacion_administrativa_hipotetica": application,
                       "limite": limit, "estado": "cotejo editorial desde propuesta Nova; no revisión humana"})
    articles = [
        {"id": "bradley2021", "titulo": "Unrepresentative big surveys significantly overestimated US vaccine uptake",
         "autores": "Valerie C. Bradley; Shiro Kuriwaki; Michael Isakov; Dino Sejdinovic; Xiao-Li Meng; Seth Flaxman",
         "publicacion_anio": "Nature, 600(7890), 695-700 (2021); DOI 10.1038/s41586-021-04198-4",
         "poblacion_y_marco": "Adultos estadounidenses; tres marcos distintos: usuarios activos Facebook, domicilios con contacto electrónico y panel postal probabilístico.",
         "seleccion_muestreo": "Delphi: estratificado con probabilidades desiguales dentro de usuarios; Household Pulse: sistemático sobre domicilios contactables; Axios-Ipsos: reclutamiento probabilístico por direcciones y acceso a internet facilitado.",
         "tamano_y_disenio": "Aproximadamente 250000 respuestas por semana Delphi; 75000 por ronda Household Pulse; 1000 por ronda Axios-Ipsos. No confundir totales acumulados con tamaño por ronda.",
         "resultado_y_denominador": "En mayo de 2021: sobreestimación de vacunación de adultos de 17 y 14 puntos porcentuales en Delphi y Household Pulse frente al referente CDC; Axios siguió mejor el referente.",
         "uso_administrativo": "Revisar cobertura y respuesta antes de ampliar volumen; cifras infladas pueden ocultar necesidades.",
         "limites": "El referente CDC también tiene incertidumbre, examinada por autores. No demuestra superioridad universal de muestras pequeñas.",
         "localizadores": ["bradley2021:L93-L121", "bradley2021:L371-L442", "bradley2021:L506-L930"]},
        {"id": "barrero2023", "titulo": "The evolution of work from home",
         "autores": "José María Barrero; Nicholas Bloom; Steven J. Davis",
         "publicacion_anio": "Journal of Economic Perspectives, 37(4), 23-50 (2023); DOI 10.1257/jep.37.4.23",
         "poblacion_y_marco": "Universos específicos por encuesta; serie principal de 20 a 64 años con umbrales de ingresos previos.",
         "seleccion_muestreo": "Encuestas de cortes repetidos y series históricas; SWAA calibrada por edad, sexo, educación e ingresos contra CPS. No documenta un único MAS común.",
         "tamano_y_disenio": "No existe un único tamaño aplicable a todas las fuentes. 28% es resultado, no tamaño de muestra.",
         "resultado_y_denominador": "28% de días remunerados enteramente trabajados desde casa en junio de 2023, frente a cerca del 7% en 2019; no es porcentaje de empleados.",
         "uso_administrativo": "Planear espacios y arreglos laborales respetando denominadores y filtros.",
         "limites": "La calibración observada no garantiza corregir selección no observada; tendencias descriptivas no identifican causalidad sobre productividad.",
         "localizadores": ["barrero2023:L1-L120", "PDF publicado: páginas impresas 23-24, figura 1 y notas"]},
        {"id": "bloom2024", "titulo": "Hybrid working from home improves retention without damaging performance",
         "autores": "Nicholas Bloom; Ruobing Han; James Liang",
         "publicacion_anio": "Nature, 630(8018), 920-925 (2024); DOI 10.1038/s41586-024-07500-2",
         "poblacion_y_marco": "1612 elegibles de dos divisiones seleccionadas por Trip.com, Shanghái; excluye practicantes y personal en prueba.",
         "seleccion_muestreo": "Selección empresarial del grupo, no muestra probabilística de empresas; asignación interna por paridad del cumpleaños.",
         "tamano_y_disenio": "518 voluntarios y 1094 no voluntarios; 792 en tratamiento y 820 en control. Experimento de elegibilidad para dos días semanales desde casa.",
         "resultado_y_denominador": "Salidas: 7.2% en control y 4.8% en tratamiento, diferencia de 2.4 puntos porcentuales y un tercio relativo. Equivalencia de desempeño evaluada con márgenes; no igualdad absoluta.",
         "uso_administrativo": "Ensayar políticas de retención, seguir permanencia y desempeño y contrastar contexto.",
         "limites": "Transferencia no automática a otros sectores o trabajo totalmente remoto; tamaños de desempeño disminuyen en seguimiento; conflicto directivo/accionario declarado.",
         "localizadores": ["bloom2024:L176-L230", "bloom2024:L486-L610", "bloom2024:L661-L674"]},
    ]
    ideas = [
        ("La calidad de selección y respuesta debe examinarse antes de aumentar el volumen.", "hallazgo documental", "bradley2021:L93-L121"),
        ("Un intervalo estrecho puede acompañar una estimación sesgada.", "hallazgo documental", "bradley2021:L93-L121"),
        ("La selección aleatoria dentro de usuarios activos no elimina exclusión de quienes no pertenecen al marco.", "inferencia comparativa", "bradley2021:L371-L442"),
        ("La SWAA usa ponderaciones demográficas y de ingresos frente a CPS.", "hallazgo documental", "barrero2023:L102-L120"),
        ("28% se refiere a días remunerados, no a tamaño de muestra o empleados remotos.", "hallazgo documental", "barrero2023:L1-L120"),
        ("La asignación de tratamiento no equivale a seleccionar empresas probabilísticamente.", "inferencia comparativa", "bloom2024:L486-L560"),
        ("La reducción de 7.2% a 4.8% equivale a 2.4 puntos y un tercio relativo.", "hallazgo documental", "bloom2024:L176-L230"),
        ("La ausencia de significación no demuestra igualdad; las pruebas de equivalencia usan márgenes.", "hallazgo documental", "bloom2024:L560-L610"),
        ("El tamaño para detectar un cambio depende de efecto, significación y potencia.", "hallazgo documental", "nistTamano:L19-L61"),
        ("Planear 482 invitaciones para 385 respuestas con 80% esperado no elimina sesgo de no respuesta.", "ejemplo hipotético", "holmesMuestreo2023:L295-L306"),
        ("Comparar filtros y denominadores es necesario antes de trasladar indicadores a planeación de oficinas.", "inferencia comparativa", "barrero2023:L102-L120"),
        ("Una empresa debe declarar población, selección, variable, denominador e incertidumbre antes de adoptar una política.", "inferencia comparativa", "bradley2021:L371-L442"),
    ]
    ideas_out = []
    for i, (idea, kind, loc) in enumerate(ideas, 1):
        source, locator = loc.split(":",1)
        ideas_out.append({"id": f"i{i:02}", "idea": idea, "tipo": kind,
                          "fuentes": [{"id":source,"localizador":locator}]})
    for name, payload in (("fichas_conceptos",fichas),("conceptos_detectados",[x[0]for x in DATA]),("ideas_detectadas",ideas_out),("articulos",articles)):
        write(E/f"{name}.json",payload)
    locs = {}
    for ficha in fichas:
        for src in ficha["fuentes"]:
            item=locs.setdefault(src["id"],{"id":src["id"],"conceptos_o_resultados_sustentados":[],"localizadores":[]})
            item["conceptos_o_resultados_sustentados"].append(ficha["concepto"])
            item["localizadores"].append(f"{src['id']}:{src['localizador']}")
    for key, item in locs.items():
        text_path=N/f"{key}.txt"
        item["text_path"]=text_path.relative_to(S).as_posix()
        item["sha256"]=hashlib.sha256(text_path.read_bytes()).hexdigest()
        lines=len(text_path.read_text(encoding="utf-8").splitlines())
        for locator in item["localizadores"]:
            import re
            bounds=[int(x)for x in re.findall(r"L(\d+)",locator)]
            assert all(1<=x<=lines for x in bounds),locator
    write(E/"trazabilidad_fuentes.json",list(locs.values()))
    corrections = ["Precisión corregida: variabilidad, no exactitud.",
                   "Aleatorio simple: equiprobabilidad de muestras del mismo tamaño, no solo de individuos.",
                   "Sistemático: inicio aleatorio explícito; conglomerado de una etapa distinguido del caso general.",
                   "Clasificaciones erróneas de Bradley/Barrero/Bloom corregidas desde métodos originales.",
                   "Autores de Bradley completos y título publicado de Bloom restablecidos.",
                   "28% separado de tamaño de muestra; denominador días remunerados.",
                   "Retirados efecto placebo, muestreo de bolas y otras invenciones no sustentadas.",
                   "Localizadores del motor sustituidos por rangos cotejados.",
                   "No existe afirmación de revisión humana ni se usa Nova como autoridad."]
    write(E/"alertas.json",corrections)
    reviewed=(K/"base-conceptual-unidad-1-revisada.md").read_text(encoding="utf-8")
    (K/"base-conocimiento.md").write_text(reviewed,encoding="utf-8")
    canonical=json.loads((K/"base-conocimiento.json").read_text(encoding="utf-8"))
    canonical["reviewed_conceptual_path"]="base-conceptual-unidad-1-revisada.md"
    canonical["raw_conceptual_status"]="Salida Nova original conservada; usar copia revisada para autoridad conceptual"
    canonical["editorial_corrections"]=corrections
    canonical["reviewed_conceptual_markdown"]=reviewed
    write(K/"base-conocimiento.json",canonical)
    revision={"reviewed_at_utc":datetime.now(timezone.utc).isoformat(),"reviewer":"Codex","human_review_claimed":False,
              "fichas_revisadas":len(fichas),"ideas_revisadas":len(ideas_out),"articulos_revisados":len(articles),
              "conceptual_word_count":len(reviewed.split()),"corrections":corrections,
              "raw_response_preserved":"investigacion-aulatex/nova-pro-unidad-1-2026-10-24-r3/extraccion-documental.json",
              "new_editorial_source":"Holmes (2023), sección 1.1 recuperada para reparar definiciones; no enviada a Nova en esta corrida",
              "reviewed_conceptual_sha256":hashlib.sha256(reviewed.encode()).hexdigest()}
    write(E/"revision-editorial.json",revision)
    for p in (E/"manifest.json",K/"manifest-nova-unidad-1.json"):
        manifest=json.loads(p.read_text(encoding="utf-8"))
        manifest["editorial_review"]=revision
        write(p,manifest)
    print(json.dumps(revision,ensure_ascii=True,indent=2))


if __name__=="__main__":
    main()
