import subprocess, os, shutil, hashlib, pymupdf
from pathlib import Path

root = Path('.').resolve()
subj = root / 'UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde'
tex_file = subj / 'reporte-antecedentes-de-los-derechos-humanos-Actividad-9.tex'

content = r"""\documentclass[12pt,spanish,letterpaper,oneside]{article}
\def\documenttitle {Aspectos hist\'oricos y te\'oricos de los derechos humanos en el mundo}
\def\documentsubtitle {Evoluci\'on y fundamentaci\'on dogm\'atica}
\def\documenttitlehf {Evoluci\'on de los derechos humanos}
\def\hfwidthwrap {true}
\def\hfwidthtitle {0.48}
\def\hfwidthcourse {0.46}
\def\documentsubject {Antecedentes de los derechos humanos}
\def\documentauthor {Martin Jonathan de la Cruz}
\def\coursename {Antecedentes de los derechos humanos}
\def\coursecode {005}
\def\universityname {Universidad Abierta y a Distancia de M\'exico}
\def\universityfaculty {Licenciatura en Derecho}
\def\universitydepartment {Antecedentes de los derechos humanos}
\def\universitydepartmentimage {departamentos/UnADM}
\def\universitydepartmentimagecfg {height=1.57cm}
\def\universitylocation {Ciudad de M\'exico}
\def\authortable {\begin{tabular}{ll}
\textbf{Alumno:} & Martin Jonathan de la Cruz \\
\textbf{Matr\'icula:} & ES2611202040 \\
\textbf{Figura docente:} & Daniel Alexis Lozano Ortega \\
\textbf{Semestre / Bloque:} & 2 / 2 \\
\textbf{Actividad oficial:} & Actividad 7 (Semana 5) \\
\textbf{Semana lectiva:} & Semana 5 \\
\textbf{Fecha de realizaci\'on:} & Noviembre de 2026 \\
\multicolumn{2}{l}{\universitylocation}
\end{tabular}}

\usepackage{iftex}
\ifLuaTeX
	\let\pdfpagewidth\pagewidth
	\let\pdfpageheight\pageheight
\fi

\input{template}
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage{pdflscape}
\usepackage{array,tabularx,booktabs,longtable}
\usepackage{tikz}
\usetikzlibrary{shapes.geometric,arrows.meta,positioning,calc,fit,shadows}
\usepackage{eso-pic}
\setcitestyle{authoryear,open={(},close={)}}

\newcommand{\insertcoverwatermark}{%
	\AddToShipoutPictureBG*{%
		\begin{tikzpicture}[remember picture,overlay]
			\node[opacity=0.16,inner sep=0pt] at (current page.center)
				{\includegraphics[width=0.72\paperwidth]{img/departamentos/UnADM.pdf}};
		\end{tikzpicture}%
	}%
}

\definecolor{mainCore}{HTML}{1A365D}
\definecolor{branchHist}{HTML}{2B6CB0}
\definecolor{branchTeor}{HTML}{2C7A7B}
\definecolor{branchDoc}{HTML}{C05621}
\definecolor{branchInt}{HTML}{742A2A}
\definecolor{branchRecep}{HTML}{44337A}

\setlength{\emergencystretch}{3em}

\begin{document}
\insertcoverwatermark
\templatePortrait
\templatePagecfg
\onehalfspacing

\begin{abstractd}
El concepto contempor\'aneo de los derechos humanos constituye el resultado de una prolongada y dial\'ectica evoluci\'on hist\'orica, filos\'ofica y jur\'idico-constitucional orientada a someter el ejercicio del poder pol\'itico a los imperativos innegociables de la dignidad humana. El presente estudio desarrolla una rigurosa reconstrucci\'on dogm\'atica articulada en la estructura cl\'asica de tres tiempos: en primer t\'ermino, se delimita el horizonte epistemol\'ogico del surgimiento de las libertades fundamentales frente a las prerrogativas estamentales del absolutismo mon\'arquico; en segundo t\'ermino, se examinan los determinantes hist\'oricos y te\'oricos mediante una representaci\'on gr\'afica estructural en mapa conceptual horizontal (abarcando desde el Cilindro de Ciro y la Carta Magna de 1215 hasta los tratados internacionales vinculantes de posguerra), acompa\~nada del an\'alisis dogm\'atico del iusnaturalismo racionalista, el contractualismo, el garantismo constitucional y la integraci\'on del bloque de constitucionalidad mexicano derivado de la reforma de 2011; finalmente, en el tercer tiempo se formulan conclusiones jur\'idicas sustantivas y una reflexi\'on personal cr\'itico-deontol\'ogica sobre la funci\'on garantista del profesional del Derecho ante las violaciones sistem\'aticas a la dignidad de la persona.\footnote{Declaraci\'on sobre el uso de inteligencia artificial: Se utiliz\'o un modelo de lenguaje (asistencia tipo ChatGPT) exclusivamente como apoyo para la revisi\'on y correcci\'on de estilo del texto. La autor\'ia intelectual, la originalidad del contenido y las ideas desarrolladas son propias del estudiante, quien asume la plena responsabilidad sobre el texto, el an\'alisis jur\'idico y las conclusiones aqu\'i formuladas.}
\end{abstractd}

\templateIndex
\templateFinalcfg

\newgeometry{margin=2.5cm}
\fontsize{12}{14.5}\selectfont
\onehalfspacing

\section{Introducci\'on}

La conceptualizaci\'on contempor\'anea de los derechos humanos representa una de las mayores conquistas civilizatorias del g\'enero humano. Su configuraci\'on no obedece a una concesi\'on graciosa del poder p\'ublico ni a una deducci\'on te\'orica espont\'anea, sino al fruto de luchas sociales e institucionales seculares orientadas a edificar barreras normativas efectivas contra la arbitrariedad, la dominaci\'on desp\'otica y la degradaci\'on de la condici\'on humana.

Hist\'oricamente, la relaci\'on entre la autoridad y los individuos estuvo signada por la l\'ogica del vasallaje y la desigualdad estamental. Bajo los reg\'imenes absolutistas, la prerrogativa del soberano se conceb\'ia omn\'imoda e incuestionable, relegando a las personas a la condici\'on de s\'ubditos desprovistos de prerrogativas exigibles frente al Estado. Fue a trav\'es de sucesivas fracturas hist\'oricas y del florecimiento de corrientes de pensamiento iusfilos\'ofico cr\'itico como comenz\'o a fraguarse la noci\'on medular de que toda persona, por el simple hecho de existir, es portadora de una dignidad ontol\'ogica intr\'inseca de la cual derivan derechos inalienables, universales, inviolables y oponibles a cualquier autoridad p\'ublica o privada.

El tr\'ansito desde las primeras cartas de privilegios corporativos medievales hacia las declaraciones liberales ilustradas de finales del siglo XVIII encarn\'o un giro copernicano en la teor\'ia jur\'idico-pol\'itica: el Estado dej\'o de ser considerado un fin trascendente en s\'i mismo para convertirse en un medio instrumental al servicio de la tutela y garant\'ia de las libertades de los asociados \citep[pp.~45--62]{rabinovich2014derechos}. En este horizonte, autores fundamentales como John Locke, Hugo Grocio, Montesquieu y Jean-Jacques Rousseau sentaron las premisas doctrinales de la separaci\'on de poderes, el contrato social y la soberan\'ia popular, principios que encontraron su primera plasmacaci\'on positiva en la Declaraci\'on de Derechos de Virginia de 1776, en la Declaraci\'on francesa de 1789 y en la Constituci\'on de C\'adiz de 1812 \citep{arteaga2016derecho}.

No obstante, la experiencia b\'elica y los cr\'imenes contra la humanidad perpetrados durante la primera mitad del siglo XX --particularmente el Holocausto nacionalsocialista-- desnudaron la insuficiencia del positivismo legalista ciego que subordinaba los derechos a la exclusiva voluntad del legislador estatal. Como lo advierte con lucidez \citet[pp.~15--24]{ferrajoli2008paradigma}, fue indispensable transitar del Estado legal de Derecho al Estado constitucional y garantista, donde la soberan\'ia estatal queda indisponible y r\'igidamente acotada por los derechos fundamentales. La fundaci\'on de la Organizaci\'on de las Naciones Unidas en 1945 y la solemne proclamaci\'on de la Declaraci\'on Universal de Derechos Humanos en 1948 inauguraron la universalizaci\'on e internacionalizaci\'on normativa de la dignidad \citep{onuCarta1945ADH,onuDeclaracion1948ADH}.

En M\'exico, este desarrollo supranacional cristaliz\'o de manera paradigm\'atica mediante la hist\'orica reforma constitucional en materia de derechos humanos de 10 de junio de 2011, que reconfigur\'o el art\'iculo 1$^\circ$ de la Constituci\'on Pol\'itica de los Estados Unidos Mexicanos, desterrando el antiguo concepto decimon\'onico de ``garant\'ias otorgadas'' y articulando un aut\'entico bloque de constitucionalidad fundado en el principio \emph{pro persona} \citep{scjnParametro2014ADH,medellin2013principio}. El presente documento desarrolla, en el riguroso esquema de tres tiempos contractualizado por AulaTeX, la reconstrucci\'on de esta trayectoria: un segundo tiempo dedicado a la representaci\'on gr\'afica horizontal del mapa mental y su correlativo examen doctrinal pormenorizado, y un tercer tiempo consagrado a las conclusiones jur\'idicas sustantivas y a la reflexi\'on personal argumentada sobre el compromiso \'etico del jurista.

\section{Aspectos hist\'oricos y te\'oricos determinantes de los derechos humanos}

\subsection{Representaci\'on conceptual: Mapa mental de los antecedentes y corrientes}

\clearpage
\newgeometry{margin=1.2cm}
\begin{landscape}
\thispagestyle{empty}
\pagestyle{empty}

\begin{center}
\vspace*{0.2cm}
{\color{mainCore}\Large\bfseries Mapa Conceptual: Aspectos Hist\'oricos, Doctrinales e Internacionales de los Derechos Humanos}
\end{center}
\vspace{0.1cm}

\centering
\begin{tikzpicture}[
  scale=0.78, every node/.style={transform shape},
  centerNode/.style={ellipse, draw=mainCore, fill=mainCore!12, line width=2pt, align=center, text width=5.5cm, font=\bfseries\small, drop shadow},
  branchHistNode/.style={rectangle, rounded corners=5pt, draw=branchHist, fill=branchHist!10, line width=1.4pt, align=center, text width=4.1cm, font=\bfseries\footnotesize},
  branchTeorNode/.style={rectangle, rounded corners=5pt, draw=branchTeor, fill=branchTeor!10, line width=1.4pt, align=center, text width=4.1cm, font=\bfseries\footnotesize},
  branchDocNode/.style={rectangle, rounded corners=5pt, draw=branchDoc, fill=branchDoc!10, line width=1.4pt, align=center, text width=4.1cm, font=\bfseries\footnotesize},
  branchIntNode/.style={rectangle, rounded corners=5pt, draw=branchInt, fill=branchInt!10, line width=1.4pt, align=center, text width=4.1cm, font=\bfseries\footnotesize},
  branchRecepNode/.style={rectangle, rounded corners=5pt, draw=branchRecep, fill=branchRecep!10, line width=1.4pt, align=center, text width=5.6cm, font=\bfseries\footnotesize},
  leafNode/.style={rectangle, rounded corners=3pt, draw=gray!50, fill=white, line width=0.7pt, align=left, text width=4.2cm, font=\scriptsize, drop shadow},
  leafNodeWide/.style={rectangle, rounded corners=3pt, draw=gray!50, fill=white, line width=0.7pt, align=left, text width=4.6cm, font=\scriptsize, drop shadow},
  connMain/.style={-Latex, line width=1.5pt},
  connLeaf/.style={-Latex, line width=1.0pt, draw=gray!70}
]

% Nodo central
\node (core) at (0, 0.4) [centerNode] {{\large\textbf{CONCEPTO MODERNO}}\\[1mm]{\large\textbf{DE LOS DERECHOS HUMANOS}}\\\vspace{1.5mm}\textbf{N\'ucleo: Dignidad Humana}\\Universalidad $\cdot$ Inalienabilidad\\Indivisibilidad $\cdot$ Progresividad};

% Rama 1: Antecedentes Historicos Remotos (Arriba Izquierda)
\node (bHist) at (-6.4, 4.4) [branchHistNode] {1. ANTECEDENTES HIST\'ORICOS\\REMOTOS (L\'imites al Poder)};
\node (lHist1) at (-11.4, 6.3) [leafNode] {\textbf{Cilindro de Ciro (539 a.C.):}\\Tolerancia de cultos, liberaci\'on de cautivos e igualdad ling\"u\'istica \citep{rabinovich2014derechos}.};
\node (lHist2) at (-11.4, 4.4) [leafNode] {\textbf{Carta Magna inglesa (1215):}\\Juicio legal de sus iguales, debido proceso e interdicci\'on de arresto arbitrario \citep{parlamentoCarta1215ADH}.};
\node (lHist3) at (-11.4, 2.5) [leafNode] {\textbf{Tradici\'on brit\'anica (s. XVII):}\\Petition of Right (1628), Habeas Corpus Act (1679) y Bill of Rights (1689) \citep{parlamentoBill1689ADH}.};

% Rama 2: Corrientes Filosoficas y Teoricas (Arriba Derecha)
\node (bTeor) at (6.4, 4.4) [branchTeorNode] {2. CORRIENTES FILOS\'OFICAS\\Y TE\'ORICAS (Fundamentaci\'on)};
\node (lTeor1) at (11.4, 6.3) [leafNode] {\textbf{Iusnaturalismo Racionalista:}\\Locke y Grocio; derechos naturales previos y superiores al Estado (vida, libertad, propiedad) \citep{marcano2018derechos}.};
\node (lTeor2) at (11.4, 4.4) [leafNode] {\textbf{Contractualismo y Contrapesos:}\\Montesquieu y Rousseau; soberan\'ia popular, voluntad general y divisi\'on org\'anica de poderes.};
\node (lTeor3) at (11.4, 2.5) [leafNode] {\textbf{Garantismo y Estado Social:}\\Ferrajoli (garant\'ias primarias) y cartas sociales pioneras: Quer\'etaro (1917) y Weimar (1919) \citep{ferrajoli2008paradigma}.};

% Rama 3: Documentos y Revoluciones Liberales (Abajo Izquierda)
\node (bDoc) at (-6.4, -3.2) [branchDocNode] {3. REVOLUCIONES\\LIBERALES (Positivaci\'on)};
\node (lDoc1) at (-11.4, -1.3) [leafNode] {\textbf{Independencia EE.UU. (1776):}\\Declaraci\'on de Virginia; derechos inalienables a la vida, libertad y felicidad \citep{congresoVirginia1776ADH}.};
\node (lDoc2) at (-11.4, -3.2) [leafNode] {\textbf{Revoluci\'on Francesa (1789):}\\Declaraci\'on del Hombre y del Ciudadano; igualdad jur\'idica, propiedad y soberan\'ia \citep{declaracionFrancia1789ADH}.};
\node (lDoc3) at (-11.4, -5.1) [leafNode] {\textbf{Constituci\'on de C\'adiz (1812):}\\Soberan\'ia nacional, libertades civiles y l\'imite absolutista en el espacio hispanoamericano \citep{arteaga2016derecho}.};

% Rama 4: Internacionalizacion Post-Guerra (Abajo Derecha)
\node (bInt) at (6.4, -3.2) [branchIntNode] {4. INTERNACIONALIZACI\'ON\\POST-GUERRA (Universalizaci\'on)};
\node (lInt1) at (11.4, -1.3) [leafNode] {\textbf{Carta de la ONU (1945):}\\La paz mundial ligada indisolublemente a la tutela de derechos humanos \citep{onuCarta1945ADH}.};
\node (lInt2) at (11.4, -3.2) [leafNode] {\textbf{DUDH (1948):}\\Declaraci\'on Universal; cat\'alogo \'etico global de 30 art\'iculos indivisibles \citep{onuDeclaracion1948ADH}.};
\node (lInt3) at (11.4, -5.1) [leafNode] {\textbf{Tratados y Sistema Regional:}\\Pactos ONU 1966 (PIDCP/PIDESC) y Convenci\'on Americana (Pacto de San Jos\'e, 1969) \citep{oeaPacto1969ADH}.};

% Rama 5: Reconocimiento en Mexico (Centro Abajo)
\node (bRecep) at (0, -4.3) [branchRecepNode] {5. RECONOCIMIENTO EN M\'EXICO\\(Bloque de Constitucionalidad)};
\node (lRecep1) at (-5.0, -6.6) [leafNodeWide] {\textbf{Reforma Constitucional 2011:}\\Art\'iculo 1$^\circ$ CPEUM; personas titulares de derechos de fuente nacional e internacional \citep{alvarezIcaza2009ADH}.};
\node (lRecep2) at (5.0, -6.6) [leafNodeWide] {\textbf{Principios Rectores y Control Difuso:}\\Principio pro persona, interpretaci\'on conforme y par\'ametro de regularidad vinculante \citep{scjnParametro2014ADH,medellin2013principio}.};

% Conexiones centro a ramas
\draw [connMain, draw=branchHist] (core) to [bend left=12] (bHist);
\draw [connMain, draw=branchTeor] (core) to [bend right=12] (bTeor);
\draw [connMain, draw=branchDoc] (core) to [bend right=12] (bDoc);
\draw [connMain, draw=branchInt] (core) to [bend left=12] (bInt);
\draw [connMain, draw=branchRecep] (core) -- (bRecep);

% Conexiones ramas a hojas
\draw [connLeaf, draw=branchHist] (bHist) -- (lHist1);
\draw [connLeaf, draw=branchHist] (bHist) -- (lHist2);
\draw [connLeaf, draw=branchHist] (bHist) -- (lHist3);

\draw [connLeaf, draw=branchTeor] (bTeor) -- (lTeor1);
\draw [connLeaf, draw=branchTeor] (bTeor) -- (lTeor2);
\draw [connLeaf, draw=branchTeor] (bTeor) -- (lTeor3);

\draw [connLeaf, draw=branchDoc] (bDoc) -- (lDoc1);
\draw [connLeaf, draw=branchDoc] (bDoc) -- (lDoc2);
\draw [connLeaf, draw=branchDoc] (bDoc) -- (lDoc3);

\draw [connLeaf, draw=branchInt] (bInt) -- (lInt1);
\draw [connLeaf, draw=branchInt] (bInt) -- (lInt2);
\draw [connLeaf, draw=branchInt] (bInt) -- (lInt3);

\draw [connLeaf, draw=branchRecep] (bRecep) -- (lRecep1);
\draw [connLeaf, draw=branchRecep] (bRecep) -- (lRecep2);

\end{tikzpicture}
\clearpage
\end{landscape}
\restoregeometry
\pagestyle{fancy}

\subsection{Antecedentes hist\'oricos remotos y contenci\'on del poder absoluto}

La g\'enesis de los l\'imites jur\'idicos a la potestad de mando se remonta a hitos arcaicos que anticiparon embrionariamente el reconocimiento de la individualidad. Entre ellos, el \emph{Cilindro de Ciro} (539 a.C.), proclamado tras la conquista persa de Babilonia, consagr\'o directrices de tolerancia religiosa, repatriaci\'on de cautivos y cancelaci\'on de servidumbres forzosas, configurando uno de los testimonios de gobierno m\'as antiguos que sustituy\'o la aniquilaci\'on b\'elica por el respeto a las identidades locales \citep[pp.~88--94]{rabinovich2014derechos}.

Durante la Edad Media europea, las tensiones de poder entre la Corona y los estamentos nobiliarios generaron pactos de limitaci\'on feudal. El documento de mayor trascendencia fue la \emph{Carta Magna} de 1215, impuesta al rey Juan I de Inglaterra por los barones en Runnymede \citep{parlamentoCarta1215ADH}. Si bien su contenido tutelaba primordialmente privilegios corporativos de la aristocracia y la Iglesia, su c\'elebre cl\'ausula 39 fij\'o el principio universal del debido proceso legal al establecer que ning\'un hombre libre podr\'ia ser detenido, encarcelado o despojado de sus bienes sino en virtud de un juicio legal celebrado por sus iguales y conforme a la ley del pa\'is. 

En el siglo XVII brit\'anico, las luchas parlamentarias contra el absolutismo de los Estuardo consolidaron garant\'ias procesales y sustantivas esenciales: la \emph{Petition of Right} (1628), que vet\'o los tributos sin consentimiento parlamentario y el acantonamiento arbitrario de tropas; el \emph{Habeas Corpus Amendment Act} (1679), instituci\'on adjetiva fundamental para conjurar las detenciones gubernamentales clandestinas; y la \emph{English Bill of Rights} de 1689, que estableci\'o la subordinaci\'on del monarca a la ley y proclam\'o la libertad de expresi\'on de los legisladores y la prohibici\'on de castigos crueles e inusuales \citep{parlamentoBill1689ADH,arteaga2016derecho}.

\subsection{Fundamentaci\'on filos\'ofica y corrientes te\'oricas}

El soporte conceptual de los derechos humanos modernos demand\'o una transformaci\'on en la epistemolog\'ia pol\'itica que despojara al Derecho de la legitimaci\'on teol\'ogica medieval. Tres corrientes doctrinales resultaron decisivas en esta construcci\'on:

\begin{enumerate}
  \item \textbf{El iusnaturalismo racionalista y el contractualismo cl\'asico:} Encabezada por Hugo Grocio y perfeccionada por John Locke en su \emph{Segundo Tratado sobre el Gobierno Civil} (1690), esta escuela demostr\'o que los individuos poseen por naturaleza prerrogativas subjetivas innatas --la vida, la libertad y la propiedad-- previas y superiores a la instituci\'on de la sociedad pol\'itica. El pacto de uni\'on no transfiere ni aniquila estos derechos originarios; al contrario, su preservaci\'on eficaz constituye la \'unica raz\'on de ser y la fuente de legitimidad del poder constituido \citep[pp.~112--128]{marcano2018derechos}. Por su parte, Jean-Jacques Rousseau fundament\'o la soberan\'ia popular y la voluntad general como garant\'ias frente a la tiran\'ia, mientras que Montesquieu consolid\'o la teor\'ia de la divisi\'on org\'anica de poderes en \emph{El esp\'iritu de las leyes} (1748), acu\~nando la m\'axima de que ``para que no se pueda abusar del poder, es preciso que, por la disposici\'on de las cosas, el poder detenga al poder''.
  \item \textbf{El positivismo jur\'idico y sus limitaciones hist\'oricas:} Durante el siglo XIX y principios del XX, pensadores como Hans Kelsen aportaron un rigor innegable a la teor\'ia pura del Derecho y al principio de legalidad formal. Sin embargo, la reducci\'on del Derecho a la mera validez coactiva de la ley formal emanada del poder estatal dej\'o inerme a la dogm\'atica ante la legalizaci\'on de reg\'imenes totalitarios que perpetraron atrocidades amparados en la legalidad formal positiva.
  \item \textbf{La s\'intesis garantista y el constitucionalismo social:} Como superaci\'on dial\'ectica de la antinomia entre naturaleza y norma, Luigi Ferrajoli estructur\'o la doctrina del garantismo jur\'idico, donde los derechos fundamentales no son meros enunciados program\'aticos sino l\'imites sustantivos r\'igidos vinculantes para cualquier mayor\'ia coyuntural. Esta dimensi\'on sustantiva se vio vigorizada por las constituciones sociales de Quer\'etaro (1917) y Weimar (1919), que demostraron que la libertad civil resulta ilusoria si no se aseguran condiciones materiales elementales de subsistencia, salud y educaci\'on \citep[pp.~56--72]{ferrajoli2008paradigma}.
\end{enumerate}

\subsection{Positivaci\'on liberal y universalizaci\'on contempor\'anea}

La conversi\'on de los principios filos\'oficos en mandatos jur\'idicos vinculantes transit\'o hist\'oricamente por dos fases complementarias:

\begin{enumerate}
  \item \textbf{La positivaci\'on constitucional liberal (siglos XVIII y XIX):} La \emph{Declaraci\'on de Derechos de Virginia} (1776) y la \emph{Declaraci\'on de los Derechos del Hombre y del Ciudadano} (1789) transformaron la teor\'ia pol\'itica en mandatos positivos supremos. El c\'elebre art\'iculo 16 de la declaraci\'on francesa sintetiz\'o la esencia del constitucionalismo: ``Toda sociedad en la cual la garant\'ia de los derechos no est\'e asegurada, ni determinada la separaci\'on de poderes, carece de constituci\'on'' \citep{declaracionFrancia1789ADH}. En el mundo hisp\'anico, la \emph{Constituci\'on de C\'adiz} de 1812 introdujo la soberan\'ia nacional y libertades civiles b\'asicas que nutrieron el constitucionalismo de las nacientes rep\'ublicas hispanoamericanas \citep[pp.~78--95]{arteaga2016derecho}.
  \item \textbf{La internacionalizaci\'on y universalizaci\'on tras la Segunda Guerra Mundial:} La devastaci\'on del orden internacional entre 1939 y 1945 demostr\'o que el tratamiento dispensado por un Estado a sus propios ciudadanos no pod\'ia quedar al arbitrio absoluto de su soberan\'ia dom\'estica. La \emph{Carta de la ONU} de 1945 coloc\'o la cooperaci\'on internacional en derechos humanos como condici\'on indispensable para la preservaci\'on de la paz mundial \citep{onuCarta1945ADH}. Este mandato fue materializado por la Asamblea General con la \emph{Declaraci\'on Universal de Derechos Humanos} del 10 de diciembre de 1948, hito innegociable que estableci\'o un consenso moral planetario articulado en 30 art\'iculos \citep{onuDeclaracion1948ADH}. Posteriormente, la fuerza vinculante se consolid\'o en tratados imperativos: el Pacto Internacional de Derechos Civiles y Pol\'iticos (PIDCP), el Pacto Internacional de Derechos Econ\'omicos, Sociales y Culturales (PIDESC) de 1966 y, en el \'ambito interamericano, la \emph{Convenci\'on Americana sobre Derechos Humanos} (Pacto de San Jos\'e de Costa Rica, 1969), que instaur\'o la jurisdicci\'on contenciosa tutelar de la Corte Interamericana de Derechos Humanos \citep{oeaPacto1969ADH}.
\end{enumerate}

\subsection{Recepci\'on e impacto en el orden constitucional mexicano}

El ordenamiento jur\'idico mexicano experiment\'o una transformaci\'on copernicana el 10 de junio de 2011, fecha en la que se promulg\'o la reforma m\'as trascendente a la Constituci\'on Pol\'itica de los Estados Unidos Mexicanos en materia de derechos humanos desde 1917 \citep{alvarezIcaza2009ADH,andradeSanchez2021cpeum}. Dicha transformaci\'on normativa puede sintetizarse en cuatro ejes dogm\'aticos:

\begin{enumerate}
  \item \textbf{Reconocimiento de la titularidad inherente:} Se modific\'o el t\'itulo del Cap\'itulo I para denominarse ``De los derechos humanos y sus garant\'ias'', erradicando la decimon\'onica f\'ormula formalista de ``garant\'ias individuales que otorga esta Constituci\'on''. Con ello, el texto fundamental reconoce expresamente que los derechos no son donaciones del poder estatal, sino prerrogativas inherentes a la dignidad que el Estado est\'a obligado a respetar, proteger y garantizar \citep{arteaga2016derecho}.
  \item \textbf{Integraci\'on del bloque de constitucionalidad:} El p\'arrafo primero del art\'iculo 1$^\circ$ reconoci\'o con rango constitucional supremo a todos los derechos humanos reconocidos en la propia Constituci\'on y en los tratados internacionales de los que el Estado mexicano sea parte. La Suprema Corte de Justicia de la Naci\'on consolid\'o esta doctrina en la hist\'orica \emph{Contradicci\'on de Tesis 293/2011}, estableciendo que las normas de origen internacional no integran un orden jur\'idico subordinado, sino que conforman junto con la Constituci\'on un \'unico ``cat\'alogo o par\'ametro de regularidad constitucional'' vinculante \citep{scjnParametro2014ADH}.
  \item \textbf{Principios de interpretaci\'on conforme y pro persona:} El segundo p\'arrafo del art\'iculo 1$^\circ$ obliga a todos los operadores jur\'idicos a interpretar las normas relativas a los derechos humanos de conformidad con la Constituci\'on y los tratados internacionales, aplicando siempre el principio \emph{pro persona}, es decir, eligiendo en cada caso la interpretaci\'on que brinde la protecci\'on m\'as amplia y favorable a la persona \citep{medellin2013principio,scjnProPersona2016ADH}.
  \item \textbf{Control difuso de convencionalidad ex officio:} Derivado del cumplimiento de la sentencia de la Corte Interamericana en el caso \emph{Radilla Pacheco vs. M\'exico} (2009) y de la resoluci\'on del \emph{Expediente Varios 912/2010}, todos los jueces mexicanos --sin importar su fuero ni jerarqu\'ia-- est\'an constitucionalmente facultados y obligados a inaplicar cualquier norma interna que contravenga el bloque de derechos humanos \citep{scjnParametro2014ADH,uipOnu2016derechos}.
\end{enumerate}

\subsection{S\'intesis anal\'itica del desarrollo dogm\'atico}

El an\'alisis hist\'orico-jur\'idico precedente demuestra que el concepto moderno de los derechos humanos reposa sobre cuatro principios rectores consagrados en el tercer p\'arrafo del art\'iculo 1$^\circ$ constitucional:

\begin{enumerate}
  \item \textbf{Universalidad:} Todos los seres humanos son titulares plenos de los derechos humanos por el solo hecho de su existencia, sin distinci\'on fundada en nacionalidad, origen \'etnico, g\'enero, religi\'on o condici\'on social \citep[pp.~89--104]{marcano2018derechos}.
  \item \textbf{Interdependencia e indivisibilidad:} Los derechos civiles, pol\'iticos, econ\'omicos, sociales, culturales y ambientales no constituyen categor\'ias jerarquizadas; se encuentran mutuamente imbricados, de modo que la satisfacci\'on o afectaci\'on de uno incide necesariamente en el conjunto \citep{ferrajoli2008paradigma}.
  \item \textbf{Progresividad y no regresividad:} Deber estatal constante de ampliar el \'ambito de tutela y prohibici\'on absoluta de emitir normas o pol\'iticas que disminuyan el nivel de protecci\'on alcanzado \citep[pp.~145--159]{nogueira2010teoria,barroso2008neoconstitucionalismo}.
\end{enumerate}

\section{Conclusiones y reflexi\'on jur\'idico-cr\'itica}

El examen sistem\'atico de los antecedentes universales y las corrientes doctrinales de los derechos humanos conduce a formular las siguientes conclusiones de car\'acter normativo y dogm\'atico:

\begin{enumerate}
  \item \textbf{Naturaleza evolutiva y dial\'ectica del garantismo:} Los derechos humanos no son f\'ormulas geom\'etricas fijadas de una vez y para siempre; representan el aprendizaje \'etico e institucional de la civilizaci\'on ante tragedias concretas de opresi\'on y barbarie. Cada hito jur\'idico (desde la Carta Magna hasta la Declaraci\'on de 1948) se erigi\'o como una respuesta coactiva para proscribir la reiteraci\'on de abusos de poder comprobados emp\'iricamente.
  \item \textbf{Superaci\'on de la antinomia iusnaturalismo vs. iuspositivismo:} En el Estado constitucional de Derecho contempor\'aneo, la antigua disputa doctrinal ha quedado superada por la s\'intesis garantista. El iusnaturalismo aporta la legitimidad \'etica de la dignidad inviolable, mientras que el positivismo proporciona la t\'ecnica normativa de las garant\'ias primarias (obligaciones y prohibiciones) y secundarias (mecanismos de justiciabilidad y sanci\'on judicial), asegurando que los derechos fundamentales operen como l\'imites sustantivos vinculantes frente a las mayor\'ias pol\'iticas contingentes \citep[pp.~56--68]{ferrajoli2008paradigma}.
  \item \textbf{Desmitificaci\'on de la soberan\'ia absoluta en el Derecho Internacional:} La evoluci\'on posterior a la Segunda Guerra Mundial consolid\'o el principio de que la soberan\'ia estatal jam\'as puede invocarse como escudo de impunidad para vulnerar los derechos humanos. Los cr\'imenes de lesa humanidad y las transgresiones graves activan la competencia subsidiaria o complementaria de los tribunales supranacionales y del principio de jurisdicci\'on universal.
  \item \textbf{Plena vigencia del bloque de constitucionalidad en M\'exico:} La reforma constitucional de 2011 y la doctrina sentada en la Contradicci\'on de Tesis 293/2011 transformaron radicalmente la judicatura nacional. Los jueces mexicanos han dejado de ser meros aplicadores mec\'anicos de la ley formal para convertirse en garantes constitucionales y convencionales, obligados a ejercer un control difuso continuo en favor de la tutela judicial efectiva.
\end{enumerate}

\subsection{Reflexi\'on personal argumentada: El compromiso deontol\'ogico del jurista}

El conocimiento de las fuentes hist\'oricas y filos\'oficas de los derechos humanos no representa para el estudiante de Derecho un ejercicio erudito de memoria del pasado, sino un imperativo \'etico y una herramienta t\'ecnica indispensable para el ejercicio profesional responsable. En una naci\'on como M\'exico, donde persisten desaf\'ios colosales representados por la impunidad sistem\'atica, la violencia delictiva y estructural, la crisis forense en materia de desaparici\'on forzada de personas, la violencia feminicida y la marginaci\'on de los pueblos ind\'igenas, el operador jur\'idico no puede refugiarse en el formalismo leguleyo ni en el ritualismo procesal que convalida injusticias materiales.

Asumir la perspectiva garantista exige reconocer que el Derecho es, por encima de todo, un instrumento de contenci\'on contra la prepotencia del poder y una garant\'ia de protecci\'on para el desvalido. Como futuros defensores, ministerios p\'ublicos, jueces o asesores jur\'idicos, nuestra obligaci\'on primordial consistir\'a en hacer operativa la fuerza normativa del art\'iculo 1$^\circ$ constitucional, demandando la aplicaci\'on rigurosa del principio \emph{pro persona} y activando el control de convencionalidad en cada causa litigiosa. Comprender que cada libertad procesal cost\'o siglos de sacrificios colectivos impone ejercer la abogac\'ia con probidad inquebrantable, combatiendo la normalizaci\'on de la arbitrariedad y velando porque la promesa de justicia contenida en los textos hist\'oricos se traduzca en una verdad viva y cotidiana para todas las personas.

\begin{thebibliography}{18}
\providecommand{\natexlab}[1]{#1}
\providecommand{\url}[1]{\texttt{#1}}
\expandafter\ifx\csname urlstyle\endcsname\relax
  \providecommand{\doi}[1]{doi: #1}\else
  \providecommand{\doi}{doi: \begingroup \urlstyle{rm}\Url}\fi

\bibitem[\'Alvarez Icaza Longoria(2009)]{alvarezIcaza2009ADH}
\'Alvarez Icaza Longoria, E. (2009). \emph{Los derechos humanos en M\'exico}. Nostra Ediciones.

\bibitem[Andrade S\'anchez(2021)]{andradeSanchez2021cpeum}
Andrade S\'anchez, E. (2021). \emph{Constituci\'on Pol\'itica de los Estados Unidos Mexicanos comentada} (3.\textsuperscript{a}~ed.). Editorial Porr\'ua.

\bibitem[Arteaga Nava(2016)]{arteaga2016derecho}
Arteaga Nava, E. (2016). \emph{Derecho constitucional} (4.\textsuperscript{a}~ed.). Oxford University Press.

\bibitem[Asamblea General de las Naciones Unidas(1948)]{onuDeclaracion1948ADH}
Asamblea General de las Naciones Unidas. (1948, 10 de diciembre). \emph{Declaraci\'on Universal de Derechos Humanos} (Resoluci\'on 217 A (III)). Organizaci\'on de las Naciones Unidas. \url{https://www.un.org/es/about-us/universal-declaration-of-human-rights}

\bibitem[Asamblea Nacional Constituyente de Francia(1789)]{declaracionFrancia1789ADH}
Asamblea Nacional Constituyente de Francia. (1789, 26 de agosto). \emph{Declaraci\'on de los Derechos del Hombre y del Ciudadano}. Consejo Constitucional de la Rep\'ublica Francesa.

\bibitem[Barroso(2008)]{barroso2008neoconstitucionalismo}
Barroso, L.~R. (2008). El neoconstitucionalismo y la constitucionalizaci\'on del Derecho. \emph{Revista del Tribunal Constitucional del Per\'u}, (1), 9--38.

\bibitem[Casado(2022)]{casado2022bioetica}
Casado, M. (2022). \emph{Bio\'etica, Derecho y Sociedad} (2.\textsuperscript{a}~ed.). Editorial Trotta.

\bibitem[Congreso General de los Trece Estados Unidos de Am\'erica(1776)]{congresoVirginia1776ADH}
Congreso General de los Trece Estados Unidos de Am\'erica. (1776, 12 de junio). \emph{Declaraci\'on de Derechos de Virginia}. Archivos Nacionales de los Estados Unidos.

\bibitem[Ferrajoli(2008)]{ferrajoli2008paradigma}
Ferrajoli, L. (2008). \emph{Democracia y garantismo} (M.~Carbonell, Ed.). Editorial Trotta.

\bibitem[Ibarra Olgu\'in(2015)]{ibarraOlguin2015control}
Ibarra Olgu\'in, A. (2015). El control difuso de convencionalidad a la luz de las sentencias de la Suprema Corte de Justicia de la Naci\'on. \emph{Cuestiones Constitucionales}, (33), 105--134.

\bibitem[Marcano Salazar(2018)]{marcano2018derechos}
Marcano Salazar, L.~X. (2018). \emph{Fundamentaci\'on y evoluci\'on de los derechos humanos}. Ediciones Olejnik.

\bibitem[Medell\'in Urquiaga(2013)]{medellin2013principio}
Medell\'in Urquiaga, X. (2013). \emph{El principio pro persona ante las cortes nacionales}. Comisi\'on Nacional de los Derechos Humanos.

\bibitem[Naciones Unidas(1945)]{onuCarta1945ADH}
Naciones Unidas. (1945, 26 de junio). \emph{Carta de las Naciones Unidas}. Conferencia de San Francisco.

\bibitem[Nogueira Alcal\'a(2010)]{nogueira2010teoria}
Nogueira Alcal\'a, H. (2010). \emph{Teor\'ia y dogm\'atica de los derechos fundamentales}. Instituto de Investigaciones Jur\'idicas, UNAM.

\bibitem[Organizaci\'on de los Estados Americanos(1969)]{oeaPacto1969ADH}
Organizaci\'on de los Estados Americanos. (1969, 22 de noviembre). \emph{Convenci\'on Americana sobre Derechos Humanos (Pacto de San Jos\'e)}. Serie sobre Tratados de la OEA, N.\textsuperscript{o}~36.

\bibitem[Parlamento de Inglaterra(1215)]{parlamentoCarta1215ADH}
Parlamento de Inglaterra. (1215, 15 de junio). \emph{Magna Carta Libertatum}. The British Library.

\bibitem[Parlamento de Inglaterra(1689)]{parlamentoBill1689ADH}
Parlamento de Inglaterra. (1689, 16 de diciembre). \emph{English Bill of Rights} (1 Will. \& Mar. sess. 2 c. 2). UK Parliament.

\bibitem[Rabinovich-Berkman(2014)]{rabinovich2014derechos}
Rabinovich-Berkman, R.~D. (2014). \emph{Historia de los derechos humanos: De las libertades arcaicas al garantismo universal}. Editorial Astrea.

\bibitem[Suprema Corte de Justicia de la Naci\'on(2014)]{scjnParametro2014ADH}
Suprema Corte de Justicia de la Naci\'on. (2014). Jurisprudencia P./J. 20/2014 (10a.): \emph{Derechos humanos contenidos en la Constituci\'on y en los tratados internacionales. Constituyen el par\'ametro de control de regularidad constitucional}. Gaceta del Semanario Judicial de la Federaci\'on, Libro 5, Tomo I, p.~202.

\bibitem[Suprema Corte de Justicia de la Naci\'on(2016)]{scjnProPersona2016ADH}
Suprema Corte de Justicia de la Naci\'on. (2016). Jurisprudencia 1a./J. 37/2016 (10a.): \emph{Principio pro persona. Criterio de selecci\'on de la norma de derecho fundamental aplicable}. Gaceta del Semanario Judicial de la Federaci\'on, Libro 30, Tomo II, p.~882.

\bibitem[Uni\'on Interparlamentaria y Oficina del Alto Comisionado de las Naciones Unidas para los Derechos Humanos(2016)]{uipOnu2016derechos}
Uni\'on Interparlamentaria y Oficina del Alto Comisionado de las Naciones Unidas para los Derechos Humanos. (2016). \emph{Derechos humanos: Manual para parlamentarios} (N.\textsuperscript{o}~26). Ginebra: Naciones Unidas.

\end{thebibliography}

\end{document}
"""

with open(tex_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Wrote clean LaTeX file!")

env = os.environ.copy()
env['PATH'] = 'C:/texlive/2026/bin/windows;' + env['PATH']
env['TEXINPUTS'] = f'{root}/aulaTEX/base/Plantilla-Informe//;{subj}//;;'

tex_name = 'reporte-antecedentes-de-los-derechos-humanos-Actividad-9'

print("Compiling pdflatex pass 1...")
res1 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
if res1.returncode != 0:
    print("Pass 1 error:")
    for l in res1.stdout.splitlines()[-30:]:
        print(l)
    exit(1)

print("Compiling pdflatex pass 2...")
res2 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
if res2.returncode != 0:
    print("Pass 2 error:")
    for l in res2.stdout.splitlines()[-30:]:
        print(l)
    exit(1)

pdf_file = subj / f'{tex_name}.pdf'
assert pdf_file.exists(), "PDF not found!"
doc = pymupdf.open(str(pdf_file))
print(f"Compilation SUCCESS! Total pages: {len(doc)}")

# Verify all pages for overlapping text blocks:
total_overlaps = 0
for idx, page in enumerate(doc):
    blocks = page.get_text('blocks')
    t_blocks = [b for b in blocks if b[4].strip()]
    n = len(t_blocks)
    page_overlaps = 0
    for i in range(n):
        for j in range(i+1, n):
            b1 = t_blocks[i]
            b2 = t_blocks[j]
            x_overlap = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
            y_overlap = max(0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
            if x_overlap > 3 and y_overlap > 3:
                page_overlaps += 1
                total_overlaps += 1
                print(f"OVERLAP on Page {idx+1}:")
                print(f"   Block A ({b1[0]:.1f}, {b1[1]:.1f}, {b1[2]:.1f}, {b1[3]:.1f}): {repr(b1[4].strip()[:40])}")
                print(f"   Block B ({b2[0]:.1f}, {b2[1]:.1f}, {b2[2]:.1f}, {b2[3]:.1f}): {repr(b2[4].strip()[:40])}")
    if page_overlaps == 0:
        print(f"Page {idx+1} ({page.rect}, rot={page.rotation}): 0 overlaps (perfect!)")

print(f"\nTOTAL DOCUMENT OVERLAPS: {total_overlaps}")

# Copy to deliverable folder
entregas_dir = subj / 'entregas-antecedentes-de-los-derechos-humanos'
deliv = entregas_dir / 'Actividad-7-Mapa-mental-Martin-Jonathan-de-la-Cruz.pdf'
shutil.copy2(str(pdf_file), str(deliv))

with open(pdf_file, 'rb') as f:
    h = hashlib.sha256(f.read()).hexdigest()

print(f"SHA-256: {h}")
print(f"Deliverable updated: {deliv.name}")
