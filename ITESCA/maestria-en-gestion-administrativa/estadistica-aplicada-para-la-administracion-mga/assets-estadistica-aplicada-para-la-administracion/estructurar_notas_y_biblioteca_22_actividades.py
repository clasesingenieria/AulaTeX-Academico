# -*- coding: utf-8 -*-
"""Estructura la biblioteca, notas por actividad (1 a 22) y corpus focalizados
para Estadística aplicada para la administración (ITESCA MGA)."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[4]
SUBJECT = Path(__file__).resolve().parents[1]
REF_DIR = SUBJECT / "referencias-estadistica-aplicada-para-la-administracion"
LIBROS_DIR = REF_DIR / "libros-estadistica-aplicada-para-la-administracion"
NOTAS_DIR = REF_DIR / "notas-estadistica-aplicada-para-la-administracion"
MAT_GEN_DIR = NOTAS_DIR / "materiales-generales"
CORPUS_LIBROS_DIR = MAT_GEN_DIR / "corpus-libros-base"
AULA_20261018 = NOTAS_DIR / "materiales-aula" / "2026-10-18"
ARCHIVOS_AULA = AULA_20261018 / "archivos"
PLANEACIONES_DIR = SUBJECT / "planeaciones-estadistica-aplicada-para-la-administracion"
EXTRACTOR_ROOT = SUBJECT / "extractor-aulatex"


ACTIVITIES_SPEC = [
    {
        "num": 1,
        "code": "A01",
        "module_id": "1747",
        "unit_num": 1,
        "unit_title": "1. Muestreo",
        "unit_folder": "unidad-1-muestreo",
        "folder": "actividad-01-infografia-muestreo",
        "moodle_title": "1.1 Infografía 5% Tarea",
        "report_title": "Muestreo aplicado a decisiones administrativas y de mercado",
        "report_subtitle": "Actividad 1: Infografía",
        "kind": "infografia",
        "weight": "5%",
        "due_date": "25 de octubre de 2026",
        "delivered": True,
        "deliverable_rel": "entregas-estadistica-aplicada-para-la-administracion/Actividad-1-Infografia.pdf",
        "teacher_files": ["1745-1d6cdf095c3e.pdf", "1745-1d6cdf095c3e.txt"],
        "keywords": ["muestreo", "población", "muestra", "marco muestral", "probabilístico", "estratificado", "conglomerados", "tamaño de muestra", "error de muestreo", "sesgo"],
        "seed_concepts": [
            "muestreo estadístico", "población objetivo", "marco muestral", "muestra representativa",
            "muestreo aleatorio simple", "muestreo sistemático", "muestreo estratificado",
            "muestreo por conglomerados", "muestreo por conveniencia", "muestreo por juicio",
            "muestreo por cuotas", "muestreo bola de nieve", "tamaño de muestra para la media",
            "tamaño de muestra para la proporción", "error de muestreo", "sesgo de selección y cobertura"
        ],
    },
    {
        "num": 2,
        "code": "A02",
        "module_id": "1748",
        "unit_num": 1,
        "unit_title": "1. Muestreo",
        "unit_folder": "unidad-1-muestreo",
        "folder": "actividad-02-investigacion-muestreo",
        "moodle_title": "1.2 Investigación 3% Tarea",
        "report_title": "Aplicación del muestreo en estudios administrativos y organizacionales",
        "report_subtitle": "Actividad 2: Investigación",
        "kind": "investigacion_articulos",
        "weight": "3%",
        "due_date": "25 de octubre de 2026",
        "delivered": True,
        "deliverable_rel": "entregas-estadistica-aplicada-para-la-administracion/Actividad-2-Investigacion.pdf",
        "teacher_files": ["1745-1d6cdf095c3e.pdf", "1745-1d6cdf095c3e.txt", "1748-df042baeb1b7.docx"],
        "keywords": ["muestreo", "encuesta", "cuotas", "aleatorio", "tamaño efectivo", "no respuesta", "ponderación", "representatividad"],
        "seed_concepts": [
            "aplicación empírica del muestreo", "marco muestral administrativo", "muestreo por cuotas estratificadas",
            "error total de encuesta", "paradoja de muestras masivas", "correlación por diseño defectuoso",
            "ponderación post-estratificación", "asignación experimental aleatoria", "validez interna y externa",
            "tamaño efectivo de muestra", "sesgo de autoselección", "inferencia en estudios empresariales"
        ],
    },
    {
        "num": 3,
        "code": "A03",
        "module_id": "1749",
        "unit_num": 1,
        "unit_title": "1. Muestreo",
        "unit_folder": "unidad-1-muestreo",
        "folder": "actividad-03-cuestionario-muestreo",
        "moodle_title": "1.3 Cuestionario 5 %",
        "report_title": "Muestreo y representatividad",
        "report_subtitle": "Actividad 3: Cuestionario",
        "kind": "cuestionario",
        "weight": "5%",
        "due_date": "25 de octubre de 2026",
        "delivered": True,
        "deliverable_rel": None,
        "teacher_files": ["1745-1d6cdf095c3e.pdf", "1745-1d6cdf095c3e.txt"],
        "keywords": ["parámetro", "estadístico", "estratificado", "sistemático", "conglomerados", "cuotas", "bola de nieve", "error muestral"],
        "seed_concepts": [
            "parámetro poblacional", "estadístico muestral", "equiprobabilidad en muestreo aleatorio simple",
            "afijación proporcional en estratos", "periodicidad en muestreo sistemático",
            "heterogeneidad interna en conglomerados", "inclusión desconocida en muestreo no probabilístico",
            "cálculo de tamaño muestral con varianza conocida", "varianza máxima en proporciones",
            "diferencia entre error aleatorio y sesgo sistemático"
        ],
    },
    {
        "num": 4,
        "code": "A04",
        "module_id": "1754",
        "unit_num": 2,
        "unit_title": "2. Distribuciones muestrales",
        "unit_folder": "unidad-2-distribuciones",
        "folder": "actividad-04-investigacion-distribuciones-estimacion",
        "moodle_title": "2.1 Investigación documental y aplicada 5% Tarea",
        "report_title": "Estimadores, propiedades e intervalos de confianza en decisiones administrativas",
        "report_subtitle": "Actividad 4: Investigación aplicada",
        "kind": "investigacion_aplicada",
        "weight": "5%",
        "due_date": "1 de noviembre de 2026",
        "delivered": True,
        "deliverable_rel": "entregas-estadistica-aplicada-para-la-administracion/Actividad-4-Investigacion-estimacion.pdf",
        "teacher_files": ["1752-e7f1fff540b1.pdf", "1752-e7f1fff540b1.txt", "1754-d684999bb340.docx"],
        "keywords": ["estimador", "estimación", "insesgamiento", "eficiencia", "consistencia", "intervalo de confianza", "margen de error", "distribución muestral"],
        "seed_concepts": [
            "estimador como variable aleatoria", "estimación puntual numérica", "propiedad de insesgamiento",
            "eficiencia relativa de estimadores", "consistencia en probabilidad", "error cuadrático medio",
            "estimación por intervalos", "nivel de confianza frecuentista", "margen de error administrativo",
            "error estándar de la media", "interpretación gerencial de intervalos de ventas"
        ],
    },
    {
        "num": 5,
        "code": "A05",
        "module_id": "1755",
        "unit_num": 2,
        "unit_title": "2. Distribuciones muestrales",
        "unit_folder": "unidad-2-distribuciones",
        "folder": "actividad-05-ejercicios-distribuciones-muestrales",
        "moodle_title": "2.2 Ejercicios 5% Tarea",
        "report_title": "Distribuciones muestrales en la gestión",
        "report_subtitle": "Actividad 5: Ejercicios",
        "kind": "ejercicios",
        "weight": "5%",
        "due_date": "1 de noviembre de 2026",
        "delivered": True,
        "deliverable_rel": "entregas-estadistica-aplicada-para-la-administracion/Actividad-5-Ejercicios-distribuciones.pdf",
        "teacher_files": ["1752-e7f1fff540b1.pdf", "1752-e7f1fff540b1.txt", "1755-56145a594468.pdf", "1755-56145a594468.txt"],
        "keywords": ["distribución muestral", "media muestral", "proporción muestral", "teorema central del límite", "error estándar", "corrección por continuidad"],
        "seed_concepts": [
            "distribución muestral de la media", "distribución muestral de la proporción",
            "teorema central del límite", "esperanza y varianza de la media muestral",
            "error estándar respecto a desviación individual", "muestreo con y sin reemplazo",
            "factor de corrección para población finita", "aproximación normal a la binomial",
            "corrección por continuidad de Yates", "estandarización Z para promedios"
        ],
    },
    {
        "num": 6,
        "code": "A06",
        "module_id": "1756",
        "unit_num": 2,
        "unit_title": "2. Distribuciones muestrales",
        "unit_folder": "unidad-2-distribuciones",
        "folder": "actividad-06-evaluacion-distribuciones-muestrales",
        "moodle_title": "2.3 Evaluación 6% Cuestionario",
        "report_title": "Evaluación sobre distribuciones muestrales y teorema central del límite",
        "report_subtitle": "Actividad 6: Evaluación (Cuestionario)",
        "kind": "cuestionario",
        "weight": "6%",
        "due_date": "1 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1752-e7f1fff540b1.pdf", "1752-e7f1fff540b1.txt", "1755-56145a594468.txt"],
        "keywords": ["distribución muestral", "teorema central del límite", "error estándar", "proporción muestral", "varianza muestral", "estandarización"],
        "seed_concepts": [
            "definición de distribución muestral", "comportamiento asintótico del promedio",
            "error estándar de la media muestral", "error estándar de la proporción muestral",
            "condiciones de validez del teorema central del límite", "corrección para poblaciones finitas",
            "diferencia entre dispersión poblacional y muestral", "probabilidades sobre medias muestrales",
            "distribución de diferencias de medias", "distribución de diferencias de proporciones"
        ],
    },
    {
        "num": 7,
        "code": "A07",
        "module_id": "1761",
        "unit_num": 3,
        "unit_title": "3. Estimación",
        "unit_folder": "unidad-3-estimacion",
        "folder": "actividad-07-investigacion-estimacion-intervalos",
        "moodle_title": "3.1 Investigación 5% Tarea",
        "report_title": "Métodos de estimación puntual y por intervalos para medias, proporciones y varianzas",
        "report_subtitle": "Actividad 7: Reporte de investigación",
        "kind": "investigacion_aplicada",
        "weight": "5%",
        "due_date": "8 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1759-e9435da5e497.pdf", "1759-e9435da5e497.txt", "1761-d684999bb340.docx"],
        "keywords": ["estimación puntual", "intervalo de confianza", "distribución t", "ji-cuadrada", "varianza poblacional", "proporción poblacional", "insesgamiento"],
        "seed_concepts": [
            "estimadores puntuales comunes", "insesgamiento eficiencia y consistencia",
            "intervalo de confianza para la media con sigma conocida",
            "intervalo de confianza para la media con distribución t de Student",
            "intervalo de confianza para una proporción poblacional",
            "intervalo de confianza para la varianza con distribución ji-cuadrada",
            "grados de libertad en estimación", "nivel de confianza y riesgo alfa",
            "precisión y amplitud del intervalo", "aplicaciones de estimación en finanzas y operaciones"
        ],
    },
    {
        "num": 8,
        "code": "A08",
        "module_id": "1762",
        "unit_num": 3,
        "unit_title": "3. Estimación",
        "unit_folder": "unidad-3-estimacion",
        "folder": "actividad-08-ejercicios-estimacion-intervalos",
        "moodle_title": "3.2 Ejercicios 5% Tarea",
        "report_title": "Resolución analítica de intervalos de confianza y tamaños de muestra en gestión",
        "report_subtitle": "Actividad 8: Ejercicios de estimación",
        "kind": "ejercicios",
        "weight": "5%",
        "due_date": "8 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1759-e9435da5e497.pdf", "1759-e9435da5e497.txt", "1762-cc8f3e7d854f.pdf", "1762-cc8f3e7d854f.txt"],
        "keywords": ["intervalo de confianza", "distribución t", "grados de libertad", "margen de error", "tamaño de muestra", "proporción muestral", "gasto promedio"],
        "seed_concepts": [
            "intervalos de confianza al 90 95 y 99 por ciento", "cuantiles de la distribución t con 16 grados de libertad",
            "determinación de tamaño muestral para media con margen fijo",
            "intervalo de confianza para proporción de tarjetahabientes",
            "estimación del gasto medio con desviación estándar muestral",
            "proyección del agregado poblacional a partir de la media muestral",
            "efecto de la asimetría derecha sobre la media y mediana",
            "tamaño de muestra conservador sin proporción planeada"
        ],
    },
    {
        "num": 9,
        "code": "A09",
        "module_id": "1763",
        "unit_num": 3,
        "unit_title": "3. Estimación",
        "unit_folder": "unidad-3-estimacion",
        "folder": "actividad-09-evaluacion-estimacion",
        "moodle_title": "3.3 Evaluación 5% Cuestionario",
        "report_title": "Evaluación sobre estimación puntual, intervalar y determinación de muestra",
        "report_subtitle": "Actividad 9: Evaluación (Cuestionario)",
        "kind": "cuestionario",
        "weight": "5%",
        "due_date": "8 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1759-e9435da5e497.pdf", "1759-e9435da5e497.txt", "1762-cc8f3e7d854f.txt"],
        "keywords": ["estimación puntual", "intervalo de confianza", "valor crítico", "t de Student", "ji-cuadrada", "margen de error"],
        "seed_concepts": [
            "criterio de selección entre estadístico Z y t de Student",
            "efecto del nivel de confianza sobre la amplitud del intervalo",
            "efecto del tamaño muestral sobre el margen de error",
            "intervalo de confianza para la varianza y desviación estándar",
            "propiedades asintóticas de los estimadores de máxima verosimilitud",
            "error estándar estimado de una proporción",
            "planificación muestral bajo restricción de error máximo"
        ],
    },
    {
        "num": 10,
        "code": "A10",
        "module_id": "1768",
        "unit_num": 4,
        "unit_title": "4. Pruebas de hipótesis para una y dos muestras",
        "unit_folder": "unidad-4-pruebas-hipotesis",
        "folder": "actividad-10-ensayo-pruebas-hipotesis",
        "moodle_title": "4.1 Ensayo 2% Tarea",
        "report_title": "Contrastación de hipótesis paramétricas, p-valor y riesgo decisional en la administración",
        "report_subtitle": "Actividad 10: Ensayo sobre pruebas de hipótesis",
        "kind": "ensayo",
        "weight": "2%",
        "due_date": "15 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": [
            "1766-3168caf318cf.pdf", "1766-3168caf318cf.txt",
            "1766-329ddfafc080.pdf", "1766-329ddfafc080.txt",
            "1766-2963a211c1c5.pdf", "1766-2963a211c1c5.txt",
            "1766-7c72ca48ddbc.pdf", "1766-7c72ca48ddbc.txt",
            "1768-d684999bb340.docx"
        ],
        "keywords": ["hipótesis nula", "hipótesis alternativa", "error tipo I", "error tipo II", "nivel de significancia", "p-valor", "potencia", "dos muestras"],
        "seed_concepts": [
            "hipótesis nula y alternativa en decisiones gerenciales",
            "error tipo I (riesgo del productor) y error tipo II (riesgo del consumidor)",
            "nivel de significancia alfa y potencia estadística (1 - beta)",
            "interpretación epistemológica y operativa del p-valor",
            "pruebas unilaterales y bilaterales para una y dos medias",
            "pruebas de hipótesis para una y dos proporciones",
            "pruebas para una y dos varianzas (ji-cuadrada y F de Snedecor)",
            "significancia estadística frente a relevancia administrativa"
        ],
    },
    {
        "num": 11,
        "code": "A11",
        "module_id": "1769",
        "unit_num": 4,
        "unit_title": "4. Pruebas de hipótesis para una y dos muestras",
        "unit_folder": "unidad-4-pruebas-hipotesis",
        "folder": "actividad-11-ejercicios-pruebas-hipotesis",
        "moodle_title": "4.2 Ejercicios Equipo 4% Tarea",
        "report_title": "Contrastes paramétricos de hipótesis y modelos de probabilidad en escenarios empresariales",
        "report_subtitle": "Actividad 11: Ejercicios en equipo",
        "kind": "ejercicios",
        "weight": "4%",
        "due_date": "15 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": [
            "1766-3168caf318cf.txt", "1766-329ddfafc080.txt",
            "1766-c09957b712d1.pdf", "1766-c09957b712d1.txt",
            "1769-2d2053c3020c.pdf", "1769-2d2053c3020c.txt",
            "1769-ca18564f58c2.pdf", "1769-ca18564f58c2.txt"
        ],
        "keywords": ["hipótesis nula", "valor-p", "error tipo II", "potencia", "prueba Z", "prueba t", "proporción", "Poisson", "hipergeométrica"],
        "seed_concepts": [
            "formulación de hipótesis para planes de bonos de ventas",
            "cálculo de valor-p en pruebas de cola izquierda con sigma conocida",
            "contraste salarial con estadístico Z de cola derecha",
            "prueba t bilateral para audiencia media con varianza desconocida",
            "contraste de proporción de preferencia de marca propia",
            "tamaño muestral controlado por error tipo I y error tipo II",
            "distribuciones discretas de apoyo (binomial, Poisson e hipergeométrica) en aceptación de lotes"
        ],
    },
    {
        "num": 12,
        "code": "A12",
        "module_id": "1770",
        "unit_num": 4,
        "unit_title": "4. Pruebas de hipótesis para una y dos muestras",
        "unit_folder": "unidad-4-pruebas-hipotesis",
        "folder": "actividad-12-evaluacion-pruebas-hipotesis",
        "moodle_title": "4.3 Evaluación 5% Cuestionario",
        "report_title": "Evaluación sobre pruebas de hipótesis paramétricas para una y dos muestras",
        "report_subtitle": "Actividad 12: Evaluación (Cuestionario)",
        "kind": "cuestionario",
        "weight": "5%",
        "due_date": "15 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1766-3168caf318cf.txt", "1766-329ddfafc080.txt", "1766-2963a211c1c5.txt", "1769-2d2053c3020c.txt"],
        "keywords": ["prueba de hipótesis", "región de rechazo", "estadístico de prueba", "error tipo I", "error tipo II", "dos muestras independientes", "muestras pareadas"],
        "seed_concepts": [
            "regla de decisión mediante valor crítico y mediante p-valor",
            "contraste t de Welch y varianza agrupada para dos medias independientes",
            "prueba t para muestras pareadas o relacionadas",
            "contraste Z con proporción combinada para dos poblaciones",
            "prueba F de igualdad de dos varianzas poblacionales",
            "relación de compromiso entre errores de tipo I y tipo II",
            "curva característica de operación y función de potencia"
        ],
    },
    {
        "num": 13,
        "code": "A13",
        "module_id": "1775",
        "unit_num": 5,
        "unit_title": "5. Pruebas de hipótesis no paramétricas",
        "unit_folder": "unidad-5-no-parametricas",
        "folder": "actividad-13-investigacion-no-parametricas",
        "moodle_title": "5.1 Investigación 5% Tarea",
        "report_title": "Fundamentos, taxonomía y aplicaciones administrativas de las pruebas no paramétricas",
        "report_subtitle": "Actividad 13: Investigación documental",
        "kind": "investigacion_aplicada",
        "weight": "5%",
        "due_date": "22 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1773-60656212941f.pdf", "1773-60656212941f.txt", "1773-799402727f9b.pdf", "1773-799402727f9b.txt", "1775-d684999bb340.docx"],
        "keywords": ["no paramétricas", "libre de distribución", "Kolmogorov-Smirnov", "Wilcoxon", "Mann-Whitney", "Kruskal-Wallis", "Ji-cuadrada", "rangos"],
        "seed_concepts": [
            "métodos de distribución libre y robustez ante asimetría",
            "escalas de medición nominal y ordinal en gestión",
            "diferencias estructurales entre pruebas paramétricas y no paramétricas",
            "prueba de bondad de ajuste de Kolmogorov-Smirnov",
            "prueba de los signos para datos pareados",
            "prueba de rangos con signo de Wilcoxon",
            "prueba U de Mann-Whitney para dos muestras independientes",
            "prueba H de Kruskal-Wallis como alternativa al ANOVA",
            "prueba Ji-cuadrada de bondad de ajuste e independencia",
            "prueba de rachas de Wald-Wolfowitz para aleatoriedad"
        ],
    },
    {
        "num": 14,
        "code": "A14",
        "module_id": "1776",
        "unit_num": 5,
        "unit_title": "5. Pruebas de hipótesis no paramétricas",
        "unit_folder": "unidad-5-no-parametricas",
        "folder": "actividad-14-ejercicios-equipo-no-parametricas",
        "moodle_title": "5.2 Ejercicios Equipo 5% Tarea",
        "report_title": "Contrastes no paramétricos de rangos, signos y grupos múltiples en decisiones empresariales (Ejercicios 1 a 6)",
        "report_subtitle": "Actividad 14: Ejercicios en equipo",
        "kind": "ejercicios",
        "weight": "5%",
        "due_date": "22 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1773-60656212941f.pdf", "1773-60656212941f.txt", "1773-799402727f9b.txt", "1776-9c622af3e4c6.pdf", "1776-9c622af3e4c6.txt"],
        "keywords": ["Wilcoxon", "prueba de signos", "Mann-Whitney", "Kruskal-Wallis", "rangos", "empates", "mediana"],
        "seed_concepts": [
            "prueba de rangos con signo de Wilcoxon para satisfacción laboral antes y después de adquisición (Ejercicio 1)",
            "prueba de los signos para series pareadas de temperaturas estacionales (Ejercicio 2)",
            "prueba U de Mann-Whitney para comparación de edades por género (Ejercicio 3)",
            "prueba H de Kruskal-Wallis para ventas por catálogo según método de pago (Ejercicio 4)",
            "prueba U de Mann-Whitney para efectividad de degustaciones en tiendas (Ejercicio 5)",
            "prueba U de Mann-Whitney para desempeño académico según procedencia rural o urbana (Ejercicio 6)",
            "corrección por empates en asignación de rangos"
        ],
    },
    {
        "num": 15,
        "code": "A15",
        "module_id": "1777",
        "unit_num": 5,
        "unit_title": "5. Pruebas de hipótesis no paramétricas",
        "unit_folder": "unidad-5-no-parametricas",
        "folder": "actividad-15-ejercicios-individuales-no-parametricas",
        "moodle_title": "5.3 Ejercicios individuales 5% Tarea",
        "report_title": "Pruebas de aleatoriedad por rachas y contrastes no paramétricos en operaciones y servicios (Ejercicios 7 a 12)",
        "report_subtitle": "Actividad 15: Ejercicios individuales",
        "kind": "ejercicios",
        "weight": "5%",
        "due_date": "22 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1773-60656212941f.pdf", "1773-60656212941f.txt", "1776-9c622af3e4c6.pdf", "1776-9c622af3e4c6.txt"],
        "keywords": ["prueba de rachas", "aleatoriedad", "Wald-Wolfowitz", "Kruskal-Wallis", "Mann-Whitney", "secuencia"],
        "seed_concepts": [
            "prueba de rachas para aleatoriedad en quejas de circulación periodística (Ejercicio 7)",
            "prueba de rachas para patrones horarios de llegada de clientes en restaurante (Ejercicio 8)",
            "prueba de rachas en afluencia bancaria por sexo (Ejercicio 9)",
            "prueba de rachas para detección de defectos agrupados en envíos de vidrio (Ejercicio 10)",
            "prueba H de Kruskal-Wallis para afluencia de compradores en tres sucursales (Ejercicio 11)",
            "prueba U de Mann-Whitney para evaluación del desempeño de enfermeras por universidad (Ejercicio 12)",
            "aproximación normal a la distribución del número de rachas R"
        ],
    },
    {
        "num": 16,
        "code": "A16",
        "module_id": "1783",
        "unit_num": 6,
        "unit_title": "6. Análisis de series de tiempo y pronósticos económicos",
        "unit_folder": "unidad-6-series-tiempo",
        "folder": "actividad-16-infografia-series-tiempo",
        "moodle_title": "6.1 Infografía Equipo 4% Tarea",
        "report_title": "Arquitectura visual del análisis de series de tiempo y pronósticos económicos en la planeación",
        "report_subtitle": "Actividad 16: Infografía en equipo",
        "kind": "infografia",
        "weight": "4%",
        "due_date": "22 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1781-d61034b50f0a.pdf", "1781-d61034b50f0a.txt", "1781-81c5af4f6959.pdf", "1781-81c5af4f6959.txt", "1780-4741f1ff1d1d.txt"],
        "keywords": ["serie de tiempo", "tendencia", "estacionalidad", "ciclo", "medias móviles", "suavizamiento exponencial", "índice estacional", "tasas de variación"],
        "seed_concepts": [
            "definición y representación gráfica de una serie de tiempo",
            "componentes clásicos: tendencia secular, variación estacional, fluctuación cíclica e irregular",
            "esquema aditivo frente a esquema multiplicativo de descomposición",
            "método de promedios móviles simples y ponderados",
            "suavizamiento exponencial simple y constante de atenuación alfa",
            "cálculo de índices estacionales y desestacionalización",
            "tasas de variación periódica e interanual",
            "métricas de error de pronóstico (MAD, MSE, MAPE)"
        ],
    },
    {
        "num": 17,
        "code": "A17",
        "module_id": "1784",
        "unit_num": 6,
        "unit_title": "6. Análisis de series de tiempo y pronósticos económicos",
        "unit_folder": "unidad-6-series-tiempo",
        "folder": "actividad-17-investigacion-series-tiempo",
        "moodle_title": "6.2 Investigación 4% Tarea",
        "report_title": "Aplicaciones empíricas del análisis de series de tiempo y pronósticos económicos en la gestión",
        "report_subtitle": "Actividad 17: Investigación",
        "kind": "investigacion_articulos",
        "weight": "4%",
        "due_date": "22 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1781-d61034b50f0a.txt", "1781-81c5af4f6959.txt", "1784-df042baeb1b7.docx"],
        "keywords": ["series de tiempo", "pronósticos económicos", "demanda", "estacionalidad", "ARIMA", "suavizamiento exponencial", "planeación financiera"],
        "seed_concepts": [
            "pronóstico de demanda e inventarios mediante descomposición estacional",
            "modelado de series macroeconómicas y financieras con promedios móviles y suavizamiento",
            "comparación empírica de exactitud predictiva en organizaciones",
            "horizonte de planeación de corto, mediano y largo plazo",
            "detección de quiebres estructurales y choques exógenos",
            "integración de pronósticos cuantitativos en presupuestos operativos"
        ],
    },
    {
        "num": 18,
        "code": "A18",
        "module_id": "1785",
        "unit_num": 6,
        "unit_title": "6. Análisis de series de tiempo y pronósticos económicos",
        "unit_folder": "unidad-6-series-tiempo",
        "folder": "actividad-18-ejercicios-series-tiempo",
        "moodle_title": "6.3 Ejercicios Equipo 5% Tarea",
        "report_title": "Modelado práctico de índices estacionales, promedios móviles, suavizamiento exponencial y regresión",
        "report_subtitle": "Actividad 18: Ejercicios en equipo",
        "kind": "ejercicios",
        "weight": "5%",
        "due_date": "22 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1781-d61034b50f0a.txt", "1781-81c5af4f6959.txt", "1780-4741f1ff1d1d.txt", "1785-17a17ca09207.docx", "1785-17a17ca09207.txt"],
        "keywords": ["índices estacionales", "promedio móvil", "promedio móvil ponderado", "suavizamiento exponencial", "modelo estacional multiplicativo", "pronóstico"],
        "seed_concepts": [
            "cálculo de índices estacionales trimestrales en parques temáticos Vacation World (Ejercicio 1)",
            "análisis de dispersión y correlación en tiempos de embarque logístico Bardi (Ejercicio 2)",
            "regresión simple y múltiple de ingresos por publicidad en Showtime Movie Theater (Ejercicio 3)",
            "error estándar de estimación en ventas de línea blanca y construcción (Ejercicio 4)",
            "estimación de función de demanda lineal por mínimos cuadrados en Bamsy (Ejercicio 5)",
            "pronóstico trimestral con modelo estacional multiplicativo de lanchas Cotteleer (Ejercicio 6)",
            "comparación de promedio móvil de 3 meses, ponderado de 6 meses y suavizamiento exponencial en Telco Batteries (Ejercicio 7)",
            "suavizamiento exponencial con alfa 0.30 para ventas anuales de automóviles (Ejercicio 8)"
        ],
    },
    {
        "num": 19,
        "code": "A19",
        "module_id": "1786",
        "unit_num": 6,
        "unit_title": "6. Análisis de series de tiempo y pronósticos económicos",
        "unit_folder": "unidad-6-series-tiempo",
        "folder": "actividad-19-cuestionario-series-tiempo",
        "moodle_title": "6.4 Cuestionario 5%",
        "report_title": "Evaluación sobre descomposición de series de tiempo y métodos de pronóstico económico",
        "report_subtitle": "Actividad 19: Cuestionario",
        "kind": "cuestionario",
        "weight": "5%",
        "due_date": "22 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1781-d61034b50f0a.txt", "1781-81c5af4f6959.txt", "1780-4741f1ff1d1d.txt", "1785-17a17ca09207.txt"],
        "keywords": ["serie de tiempo", "tendencia", "estacionalidad", "medias móviles centradas", "índice estacional", "suavizamiento exponencial", "tasas de variación"],
        "seed_concepts": [
            "identificación analítica de componentes de tendencia, ciclo, estacionalidad e irregularidad",
            "procedimiento de medias móviles centradas para periodos pares (4 trimestres o 12 meses)",
            "normalización de índices estacionales para que su suma sea igual al número de estaciones",
            "desestacionalización de ventas para evaluar desempeño real",
            "selección de la constante de suavizamiento alfa según estabilidad de la serie",
            "cálculo e interpretación de tasas de variación y números índice"
        ],
    },
    {
        "num": 20,
        "code": "A20",
        "module_id": "1791",
        "unit_num": 7,
        "unit_title": "7. Regresión lineal",
        "unit_folder": "unidad-7-regresion-lineal",
        "folder": "actividad-20-infografia-regresion-lineal",
        "moodle_title": "7.1 Infografía Equipo 3% Tarea",
        "report_title": "Síntesis visual de los modelos de regresión lineal simple y múltiple en la gestión empresarial",
        "report_subtitle": "Actividad 20: Infografía en equipo",
        "kind": "infografia",
        "weight": "3%",
        "due_date": "22 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1789-e26a34e06187.pdf", "1789-e26a34e06187.txt", "1793-9598fb7b1b53.txt"],
        "keywords": ["regresión lineal simple", "regresión lineal múltiple", "mínimos cuadrados", "correlación", "coeficiente de determinación", "ANOVA", "variables ficticias"],
        "seed_concepts": [
            "concepto de regresión y correlación lineal de Pearson",
            "ecuación del modelo de regresión lineal simple y método de mínimos cuadrados ordinarios",
            "interpretación económica del intercepto y la pendiente marginal",
            "descomposición de la suma de cuadrados (STC = SCR + SCE)",
            "coeficiente de determinación R cuadrado y R cuadrado ajustado",
            "modelo de regresión lineal múltiple y coeficientes parciales",
            "análisis de varianza (ANOVA) y prueba F de significancia global",
            "pruebas t individuales, multicolinealidad y variables indicadoras (dummy)"
        ],
    },
    {
        "num": 21,
        "code": "A21",
        "module_id": "1792",
        "unit_num": 7,
        "unit_title": "7. Regresión lineal",
        "unit_folder": "unidad-7-regresion-lineal",
        "folder": "actividad-21-investigacion-regresion-lineal",
        "moodle_title": "7.2 Investigación 4% Tarea",
        "report_title": "Investigación de aplicaciones empíricas de regresión lineal y modelado econométrico en organizaciones",
        "report_subtitle": "Actividad 21: Investigación",
        "kind": "investigacion_articulos",
        "weight": "4%",
        "due_date": "22 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1789-e26a34e06187.txt", "1792-df042baeb1b7.docx", "1793-9598fb7b1b53.txt"],
        "keywords": ["regresión lineal", "productividad", "rentabilidad", "ventas", "costos", "ANOVA", "mínimos cuadrados", "desempeño"],
        "seed_concepts": [
            "modelado de determinantes de ventas, precios y elasticidad comercial",
            "estimación de funciones de costos y productividad organizacional con regresión múltiple",
            "evaluación del desempeño financiero y compensación ejecutiva mediante modelos lineales",
            "diagnóstico de supuestos clásicos de Gauss-Markov (linealidad, homocedasticidad, normalidad, independencia)",
            "uso de variables dicotómicas para evaluar intervenciones administrativas"
        ],
    },
    {
        "num": 22,
        "code": "A22",
        "module_id": "1793",
        "unit_num": 7,
        "unit_title": "7. Regresión lineal",
        "unit_folder": "unidad-7-regresion-lineal",
        "folder": "actividad-22-ejercicios-regresion-lineal",
        "moodle_title": "7.3 Ejercicios Equipo 5% Tarea",
        "report_title": "Estimación por mínimos cuadrados, inferencia ANOVA y predicción en regresión simple y múltiple",
        "report_subtitle": "Actividad 22: Ejercicios en equipo",
        "kind": "ejercicios",
        "weight": "5%",
        "due_date": "22 de noviembre de 2026",
        "delivered": False,
        "deliverable_rel": None,
        "teacher_files": ["1789-e26a34e06187.pdf", "1789-e26a34e06187.txt", "1793-9598fb7b1b53.pdf", "1793-9598fb7b1b53.txt"],
        "keywords": ["mínimos cuadrados", "diagrama de dispersión", "pendiente", "predicción", "regresión múltiple", "variable ficticia", "fumador", "significancia"],
        "seed_concepts": [
            "regresión lineal simple de depreciación por kilometraje en Honda Accord (Ejercicio 1)",
            "modelo lineal de precios según rango térmico en equipo Bergans of Norway (Ejercicio 2)",
            "regresión entre edad y compensación salarial de directivos CEO (Ejercicio 3)",
            "regresión lineal múltiple con variable ficticia (dummy) de tabaquismo, edad y presión arterial sobre riesgo cardiovascular (Ejercicio 4)",
            "prueba t de significancia parcial para variables dicotómicas con alfa = 0.05",
            "predicción puntual y recomendación gerencial/clínica basada en el modelo ajustado"
        ],
    },
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _slugify(text: str) -> str:
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def step_1_extract_all_books_to_base_corpus() -> dict[str, Path]:
    """Extrae el texto de todos los PDFs de libros hacia materiales-generales/corpus-libros-base
    y migra cualquier archivo previo de extracciones-libros."""
    CORPUS_LIBROS_DIR.mkdir(parents=True, exist_ok=True)
    old_extracciones = NOTAS_DIR / "extracciones-libros"
    if old_extracciones.exists():
        for txt_file in old_extracciones.glob("*.txt"):
            target = CORPUS_LIBROS_DIR / txt_file.name
            if not target.exists():
                shutil.copy2(txt_file, target)

    book_txt_map: dict[str, Path] = {}
    for pdf_path in sorted(LIBROS_DIR.glob("*.pdf")):
        digest12 = _sha256(pdf_path)[:12]
        slug = _slugify(pdf_path.stem)[:65]
        existing = list(CORPUS_LIBROS_DIR.glob(f"*--{digest12}.txt"))
        if existing:
            txt_path = existing[0]
        else:
            txt_path = CORPUS_LIBROS_DIR / f"{slug}--{digest12}.txt"
            try:
                doc = pymupdf.open(str(pdf_path))
                pages_txt = []
                max_pages = min(len(doc), 450)
                for idx in range(max_pages):
                    t = doc[idx].get_text("text") or ""
                    if t.strip():
                        pages_txt.append(f"--- PÁGINA PDF {idx + 1} ---\n{t.strip()}")
                doc.close()
                if pages_txt:
                    txt_path.write_text("\n\n".join(pages_txt), encoding="utf-8")
                    print(f"Extraído libro: {pdf_path.name} -> {txt_path.name} ({len(pages_txt)} págs con texto)")
            except Exception as e:
                print(f"Aviso extrayendo {pdf_path.name}: {e}")
        if txt_path.exists() and txt_path.stat().st_size > 200:
            book_txt_map[pdf_path.name] = txt_path

    # Remove old loose extracciones-libros folder now that it is consolidated in materiales-generales/corpus-libros-base
    if old_extracciones.exists():
        shutil.rmtree(old_extracciones)
        print("Consolidada carpeta suelta extracciones-libros -> materiales-generales/corpus-libros-base")

    return book_txt_map


def _select_focused_excerpts(txt_path: Path, keywords: list[str], max_blocks: int = 12) -> str:
    """Selecciona bloques de un libro que contienen mayor densidad de palabras clave de la actividad."""
    try:
        raw = txt_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    if not raw.strip():
        return ""
    # Split by page markers or chunks of ~2200 chars
    pages = re.split(r"(?=(?:--- PÁGINA PDF \d+ ---|\bPagina \d+\b))", raw)
    if len(pages) <= 2:
        lines = raw.splitlines()
        pages = ["\n".join(lines[i : i + 55]) for i in range(0, len(lines), 55)]

    scored = []
    kw_lower = [k.lower() for k in keywords]
    for idx, block in enumerate(pages):
        low = block.lower()
        score = sum(low.count(k) * (2 if " " in k else 1) for k in kw_lower)
        if score > 0 and len(block.strip()) > 150:
            scored.append((score, idx, block.strip()[:2600]))
    scored.sort(key=lambda x: (-x[0], x[1]))
    chosen = sorted(scored[:max_blocks], key=lambda x: x[1])
    if not chosen:
        # Take first non-empty blocks
        non_empty = [b.strip()[:2000] for b in pages if len(b.strip()) > 150][:4]
        return "\n\n".join(non_empty)
    return "\n\n".join(f"[Bloque seleccionado #{idx + 1} | relevancia={sc}]\n{blk}" for sc, idx, blk in chosen)


def step_2_build_unit_and_activity_notes(book_txt_map: dict[str, Path]) -> None:
    """Construye las carpetas de notas para las 7 unidades y las 22 actividades con la estructura canónica."""
    inventario_aula = json.loads((AULA_20261018 / "inventario.json").read_text(encoding="utf-8"))
    modules_by_id = {m["id"]: m for m in inventario_aula.get("modules", [])}

    # Priority books for focused extraction across all statistical units
    priority_books = [
        "Estadística para negocios y economía - Anderson, Sweeney y Williams. 11.ª edición.pdf",
        "Estadística aplicada a los negocios y la economía - Lind, Marchal y Wathen. 15.ª edición.pdf",
        "Estadística para administración y economía - Levin y Rubin. 7.ª edición revisada.pdf",
        "Estadística matemática con aplicaciones - Wackerly, Mendenhall y Scheaffer. 7.ª edición.pdf",
        "Estadística - Spiegel y Stephens. 4.ª edición.pdf",
        "Probabilidad y estadística, aplicaciones y métodos - Canavos. Edición no verificada.pdf",
        "Estadística aplicada - Guarín Salazar. Universidad Nacional de Colombia.pdf",
        "Survey Methods and Practices - Statistics Canada. Cat. 12-587-X.pdf",
        "Introducción a la estadística empresarial (Compendio Unidades 1-7) - Holmes, Illowsky y Dean (OpenStax, 2023).pdf",
        "Engineering Statistics Handbook (Compendio Unidades 1-7) - NIST-SEMATECH (2013).pdf",
    ]

    # Ensure unit folders exist
    unit_folders = {}
    for act in ACTIVITIES_SPEC:
        uf = NOTAS_DIR / act["unit_folder"]
        uf.mkdir(parents=True, exist_ok=True)
        unit_folders[act["unit_num"]] = (act["unit_title"], uf)

    for act in ACTIVITIES_SPEC:
        act_dir = NOTAS_DIR / act["folder"]
        mat_doc_dir = act_dir / "material-docente"
        corpus_dir = act_dir / "corpus-extractor"
        focal_dir = act_dir / "corpus-extractor-focalizado"
        inv_dir = act_dir / "investigacion"
        for d in (act_dir, mat_doc_dir, corpus_dir, focal_dir, inv_dir):
            d.mkdir(parents=True, exist_ok=True)

        mod = modules_by_id.get(act["module_id"], {})
        plan_src = PLANEACIONES_DIR / f"planeacion-modulo-{act['module_id']}.md"
        plan_text = plan_src.read_text(encoding="utf-8") if plan_src.exists() else ""
        mod_txt_src = AULA_20261018 / f"modulo-{act['module_id']}.txt"
        mod_text = mod_txt_src.read_text(encoding="utf-8") if mod_txt_src.exists() else ""

        # 1. Copy teacher files into material-docente/ and unit folder
        copied_teacher_files = []
        for tf_name in act["teacher_files"]:
            src_tf = ARCHIVOS_AULA / tf_name
            if src_tf.exists():
                dst_tf = mat_doc_dir / tf_name
                if not dst_tf.exists():
                    shutil.copy2(src_tf, dst_tf)
                unit_tf = (NOTAS_DIR / act["unit_folder"]) / tf_name
                if not unit_tf.exists():
                    shutil.copy2(src_tf, unit_tf)
                copied_teacher_files.append(dst_tf)
                if dst_tf.suffix.lower() == ".txt":
                    shutil.copy2(dst_tf, corpus_dir / f"docente-{tf_name}")
                    shutil.copy2(dst_tf, focal_dir / f"docente-{tf_name}")

        # 2. Write consigna-aula, CONSIGNA-OFICIAL, planeacion-entrada-extractor, conceptos-semilla
        code = act["code"]
        (act_dir / f"consigna-aula-{code}.txt").write_text(mod_text or plan_text, encoding="utf-8")

        consigna_md = [
            f"# Consigna Oficial — Actividad {act['num']} ({act['moodle_title']})",
            "",
            f"- **Módulo Moodle**: `{act['module_id']}` ({mod.get('url', '')})",
            f"- **Unidad**: {act['unit_title']}",
            f"- **Ponderación**: {act['weight']}",
            f"- **Fechas oficiales**: {mod.get('dates_and_status', '').splitlines()[0] if mod.get('dates_and_status') else act['due_date']}",
            f"- **Estado de realización**: {'Realizada y validada en plataforma' if act['delivered'] else 'Plantilla, notas y extracción listas (realización posterior)'}",
            "",
            "## Instrucciones y requisitos del aula",
            "",
            "```text",
            mod.get("requirements", "").strip() or plan_text.strip(),
            "```",
            "",
            "## Criterios de evaluación y estado publicado",
            "",
            "```text",
            mod.get("dates_and_status", "").strip() or "Sin criterios adicionales publicados en la vista del módulo.",
            "```",
        ]
        (act_dir / f"CONSIGNA-OFICIAL-{code}.md").write_text("\n".join(consigna_md) + "\n", encoding="utf-8")

        # Planeación enriquecida para el extractor
        plan_extractor = [
            f"Materia: Estadística aplicada para la administración (GGEA01 - ITESCA MGA)",
            f"Unidad: {act['unit_title']}",
            f"Actividad {act['num']}: {act['moodle_title']} — {act['report_title']}",
            f"Subtítulo editorial: {act['report_subtitle']}",
            f"Tipo de producto: {act['kind']}",
            "",
            "Requisitos e instrucciones de la actividad:",
            mod.get("requirements", "").strip(),
            "",
            "Conceptos nucleares de la actividad:",
            *[f"- {c}" for c in act["seed_concepts"]],
        ]
        (act_dir / f"planeacion-{code}-entrada-extractor.txt").write_text("\n".join(plan_extractor) + "\n", encoding="utf-8")
        (act_dir / f"conceptos-semilla-{code}.txt").write_text("\n".join(act["seed_concepts"]) + "\n", encoding="utf-8")

        # 3. Populate corpus-extractor and corpus-extractor-focalizado with targeted book excerpts
        focal_inventory = []
        full_inventory = []

        # Include consigna & teacher files in focalized corpus
        consigna_corpus_file = focal_dir / f"00-consigna-y-planeacion-{code}.txt"
        consigna_corpus_file.write_text("\n".join(plan_extractor) + "\n\n" + mod_text, encoding="utf-8")

        for bname in priority_books:
            if bname not in book_txt_map:
                continue
            btxt = book_txt_map[bname]
            excerpts = _select_focused_excerpts(btxt, act["keywords"], max_blocks=10)
            if excerpts.strip():
                short_slug = _slugify(Path(bname).stem)[:48]
                focal_file = focal_dir / f"libro-{short_slug}-{code}.txt"
                header = f"Fuente bibliográfica: {bname}\nActividad: {act['num']} ({act['moodle_title']})\nPalabras clave: {', '.join(act['keywords'])}\n\n"
                focal_file.write_text(header + excerpts + "\n", encoding="utf-8")
                # Also place in corpus-extractor
                shutil.copy2(focal_file, corpus_dir / focal_file.name)
                focal_inventory.append(
                    {
                        "book": bname,
                        "focused_excerpt_path": focal_file.relative_to(SUBJECT).as_posix(),
                        "bytes": focal_file.stat().st_size,
                        "sha256": _sha256(focal_file),
                    }
                )
                full_inventory.append(
                    {
                        "book": bname,
                        "base_corpus_path": btxt.relative_to(SUBJECT).as_posix(),
                        "focused_corpus_path": (corpus_dir / focal_file.name).relative_to(SUBJECT).as_posix(),
                    }
                )

        (act_dir / "corpus-extractor-focalizado-inventario.json").write_text(
            json.dumps({"activity": act["num"], "code": code, "files": focal_inventory}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (act_dir / "corpus-extractor-inventario.json").write_text(
            json.dumps({"activity": act["num"], "code": code, "files": full_inventory}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 4. Write activity README.md
        conceptos_rel = f"../../../extractor-aulatex/conceptos-estadistica-aplicada-para-la-administracion-actividad-{act['num']}"
        report_rel = f"../../../reporte-estadistica-aplicada-para-la-administracion-Actividad-{act['num']}.tex"
        readme_lines = [
            f"# Notas de Actividad {act['num']}: {act['moodle_title']}",
            "",
            f"- **Unidad**: {act['unit_title']} (`{act['unit_folder']}`)",
            f"- **Módulo Moodle**: `{act['module_id']}`",
            f"- **Título del reporte**: *{act['report_title']}*",
            f"- **Subtítulo en portada**: `{act['report_subtitle']}`",
            f"- **Fecha de cierre en plataforma**: {act['due_date']}",
            f"- **Reporte fuente LaTeX**: [{Path(report_rel).name}]({report_rel})",
            f"- **Carpeta de extracción conceptual (`extractor-aulatex`)**: [`conceptos-estadistica-aplicada-para-la-administracion-actividad-{act['num']}`]({conceptos_rel})",
        ]
        if act["deliverable_rel"]:
            readme_lines.append(f"- **Entregable validado**: [`{Path(act['deliverable_rel']).name}`](../../../{act['deliverable_rel']})")
        else:
            readme_lines.append(
                "- **Entregable en `entregas-`**: "
                + ("No aplica (cuestionario en línea documentado en reporte raíz)" if act["kind"] == "cuestionario" else "Pendiente de realización posterior (plantilla y extracción preparadas)")
            )
        readme_lines.extend(
            [
                "",
                "## Estructura de la carpeta de notas de la actividad",
                "",
                f"- [`CONSIGNA-OFICIAL-{code}.md`](CONSIGNA-OFICIAL-{code}.md): transcripción íntegra de instrucciones, fechas y rúbrica de Moodle.",
                f"- [`planeacion-{code}-entrada-extractor.txt`](planeacion-{code}-entrada-extractor.txt): planeación estructurada de entrada para el extractor AulaTeX.",
                f"- [`conceptos-semilla-{code}.txt`](conceptos-semilla-{code}.txt): {len(act['seed_concepts'])} conceptos semilla específicos de la actividad.",
                "- `material-docente/`: copias locales y extracciones `.txt` de los recursos docentes del aula.",
                "- `corpus-extractor/` y `corpus-extractor-focalizado/`: extractos bibliográficos focalizados de la biblioteca de la materia con localizadores trazables.",
                "- `investigacion/`: base conceptual e insumos de extracción generados con **Amazon Nova Pro** (`AulaTeX`).",
            ]
        )
        (act_dir / "README.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

    # Write unit README.md and fuentes.json for Units 3 to 7 (preserving Units 1 & 2 files)
    for unit_num, (unit_title, uf) in sorted(unit_folders.items()):
        unit_acts = [a for a in ACTIVITIES_SPEC if a["unit_num"] == unit_num]
        u_readme = [
            f"# Notas de {unit_title}",
            "",
            "## Actividades de la unidad",
            "",
            "| Actividad | Módulo | Título en plataforma | Carpeta por actividad | Reporte raíz |",
            "| --- | --- | --- | --- | --- |",
        ]
        for a in unit_acts:
            u_readme.append(
                f"| Actividad {a['num']} | `{a['module_id']}` | {a['moodle_title']} | [`{a['folder']}`](../{a['folder']}/README.md) | `reporte-estadistica-aplicada-para-la-administracion-Actividad-{a['num']}.tex` |"
            )
        (uf / "README.md").write_text("\n".join(u_readme) + "\n", encoding="utf-8")
        fuentes_path = uf / "fuentes.json"
        if not fuentes_path.exists():
            fuentes_path.write_text(
                json.dumps(
                    {
                        "unit": unit_num,
                        "unit_title": unit_title,
                        "activities": [a["num"] for a in unit_acts],
                        "activity_folders": [a["folder"] for a in unit_acts],
                        "teacher_files": sorted({tf for a in unit_acts for tf in a["teacher_files"]}),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )


def step_3_update_unified_library_inventory() -> None:
    """Actualiza inventario-biblioteca-unificada.json y referencias-estadistica-verificadas.bib con los nuevos libros."""
    inv_path = REF_DIR / "inventario-biblioteca-unificada.json"
    inv = json.loads(inv_path.read_text(encoding="utf-8"))
    existing_paths = {b["path"] for b in inv.get("books", [])}

    new_books_meta = [
        (
            "Estadística aplicada - Guarín Salazar. Universidad Nacional de Colombia.pdf",
            "Estadística aplicada",
            "https://reneues.wordpress.com/wp-content/uploads/2010/01/libro-estadistica_aplicada-basico-guarin1.pdf",
            {"author": "Norberto Guarín Salazar", "institution": "Universidad Nacional de Colombia", "year": 2002},
        ),
        (
            "Survey Methods and Practices - Statistics Canada. Cat. 12-587-X.pdf",
            "Survey Methods and Practices (Catalogue no. 12-587-X)",
            "https://www150.statcan.gc.ca/n1/en/pub/12-587-x/12-587-x2003001-eng.pdf",
            {"author": "Statistics Canada", "catalogue": "12-587-X", "year": 2010},
        ),
        (
            "Introducción a la estadística empresarial (Compendio Unidades 1-7) - Holmes, Illowsky y Dean (OpenStax, 2023).pdf",
            "Introductory Business Statistics 2e (Compendio Unidades 1 a 7)",
            "https://openstax.org/details/books/introductory-business-statistics-2e",
            {"author": "Alexander Holmes, Barbara Illowsky, Susan Dean", "publisher": "OpenStax", "year": 2023},
        ),
        (
            "Engineering Statistics Handbook (Compendio Unidades 1-7) - NIST-SEMATECH (2013).pdf",
            "NIST/SEMATECH e-Handbook of Statistical Methods (Compendio Unidades 1 a 7)",
            "https://www.itl.nist.gov/div898/handbook/",
            {"author": "NIST/SEMATECH", "publisher": "National Institute of Standards and Technology", "year": 2013},
        ),
    ]

    for fname, title, url, meta in new_books_meta:
        fpath = LIBROS_DIR / fname
        rel = fpath.relative_to(SUBJECT).as_posix()
        if fpath.exists() and rel not in existing_paths:
            inv["books"].append(
                {
                    "title": title,
                    "path": rel,
                    "sha256": _sha256(fpath),
                    "bytes": fpath.stat().st_size,
                    "sources": [{"kind": "open-access-web", "url": url}],
                    "metadata": meta,
                    "display_name": fname,
                }
            )
    inv_path.write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")

    # Update notas README.md
    notas_readme = [
        "# Notas de Estadística aplicada para la administración",
        "",
        "Carpeta canónica de notas, consignas verificadas, materiales docentes y corpus de extracción organizados por unidad (Unidades 1 a 7) y por actividad (`actividad-01` a `actividad-22`).",
        "",
        "## Índice de carpetas por actividad",
        "",
        "| Act. | Módulo | Unidad | Actividad en plataforma | Carpeta de notas y corpus | Extracción conceptual (`extractor-aulatex`) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for a in ACTIVITIES_SPEC:
        notas_readme.append(
            f"| {a['num']} | `{a['module_id']}` | {a['unit_title']} | {a['moodle_title']} | [`{a['folder']}`]({a['folder']}/README.md) | [`conceptos-...-actividad-{a['num']}`](../../extractor-aulatex/conceptos-estadistica-aplicada-para-la-administracion-actividad-{a['num']}) |"
        )
    (NOTAS_DIR / "README.md").write_text("\n".join(notas_readme) + "\n", encoding="utf-8")


if __name__ == "__main__":
    bmap = step_1_extract_all_books_to_base_corpus()
    print(f"Total libros en corpus base: {len(bmap)}")
    step_2_build_unit_and_activity_notes(bmap)
    step_3_update_unified_library_inventory()
    print("Estructura de 22 carpetas de notas por actividad y 7 unidades completada.")
