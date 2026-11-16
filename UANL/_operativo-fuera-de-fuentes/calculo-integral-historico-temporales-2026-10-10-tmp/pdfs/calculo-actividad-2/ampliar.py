from pathlib import Path
out = Path('UANL/ingeniero-agronomo/calculo-integral/contenido-actividad-2.tex')
parts = [r'''% Contenido específico de la Actividad 2 (Evidencia 1).
% Numeración cotejada con las cuatro imágenes de la consigna original.
\begin{abstractd}
Se desarrollan los 88 enunciados completos que aparecen en las cuatro imágenes de la Evidencia 1: 28 de antiderivación directa, 24 de sustitución y aplicación, y 36 de integración algebraica y trigonométrica. Cada solución muestra la elección del método, las transformaciones del integrando, los factores del diferencial, la integración y una comprobación por derivación. Se conservan los números de la fuente para facilitar el cotejo y se indican las restricciones de dominio pertinentes.
\end{abstractd}
\templateIndex

\section{Introducción y alcance}
Una antiderivada de $f$ es una función $F$ que satisface $F'(x)=f(x)$. En un intervalo de definición, todas las antiderivadas difieren en una constante; por ello se escribe $\int f(x)\,dx=F(x)+C$. Integrar exige reconocer la estructura de la expresión antes de aplicar una fórmula: distribuir productos, transformar radicales en potencias, dividir polinomios o identificar una función interna y su derivada \citep{stewart2016calculus,openstax2016calculus1}.

En Agronomía, una integral permite acumular una tasa de crecimiento, consumo de agua o costo marginal. La verificación por derivación comprueba que el resultado conserva la tasa de cambio original, incluidos sus signos y coeficientes.

\begin{sourcebox}{Correspondencia con la consigna}
Se resuelven los ejercicios 4.1.1--4.1.28, 4.2.1--4.2.14, 4.2.36--4.2.45 y los ejercicios 1--36 de las otras dos imágenes. Estos últimos se identifican como A.1--A.36 para evitar confundir las listas. Los ejercicios 4.1.29--4.1.30 y 4.2.15--4.2.35 no se ven completos en las capturas; de 4.2.46 sólo aparece el inicio del enunciado. No se reconstruyen expresiones ausentes. Las cuatro imágenes originales se conservan al final.

El cotejo corrige cuatro transcripciones anteriores: en 4.1.12 aparece $x^4(5-x^2)$; en 4.1.19, $(x^2+4x-4)/\sqrt{x}$; en 4.1.22, $(27t^3-1)/\sqrt[3]{t}$; y en 4.2.42 el numerador es $x^3$.
\end{sourcebox}

\section{Guía de fórmulas y pasos}
\subsection{Linealidad, potencias y logaritmos}
Las constantes multiplicativas salen de la integral y las sumas se integran término a término:
\[
 \int [af(x)+bg(x)]\,dx=a\int f(x)\,dx+b\int g(x)\,dx.
\]
La regla de la potencia aumenta el exponente en una unidad y divide entre el nuevo exponente:
\[
 \int x^n\,dx=\frac{x^{n+1}}{n+1}+C\quad(n\ne-1),
 \qquad \int\frac{dx}{x}=\ln|x|+C\quad(x\ne0).
\]
Por ejemplo, $\sqrt{x}=x^{1/2}$, $1/\sqrt{x}=x^{-1/2}$ y $x^a/x^b=x^{a-b}$, en el dominio donde estas expresiones estén definidas. Dividir entre $3/2$ equivale a multiplicar por $2/3$. Se escribe una sola constante $C$ porque la suma de constantes arbitrarias vuelve a ser una constante.

\subsection{Cambio de variable sin saltos}
Si $u=g(x)$, se calcula $du=g'(x)\,dx$ y se despeja el producto diferencial que aparece en la integral. Por ejemplo,
\[
 u=2x^2+1,\quad du=4x\,dx,\quad x\,dx=\frac{du}{4}.
\]
Después se reemplazan \emph{todos} los factores que contienen la variable original; no debe quedar una mezcla de $x$ y $u$. Se integra en $u$, se sustituye $u=g(x)$ en el resultado y se comprueba con la regla de la cadena:
\[
 \frac{d}{dx}H(g(x))=H'(g(x))g'(x).
\]
En particular, $\int g'(x)/g(x)\,dx=\ln|g(x)|+C$ en intervalos donde $g(x)\ne0$.

\subsection{División algebraica y funciones trigonométricas}
Si $P(x)=D(x)Q(x)+R(x)$, entonces $P/D=Q+R/D$. Esta igualdad se comprueba multiplicando y evita integrar una fracción impropia sin simplificar. También se usa
\[
 \int\frac{dx}{x^2+a^2}=\frac1a\arctan\!\left(\frac xa\right)+C\quad(a>0).
\]
Para funciones trigonométricas, los argumentos se consideran en radianes:
\begin{align*}
 \int\sen x\,dx&=-\cos x+C,&\int\cos x\,dx&=\sen x+C,\\
 \int\sec^2x\,dx&=\tan x+C,&\int\csc^2x\,dx&=-\cot x+C,\\
 \int\sec x\tan x\,dx&=\sec x+C,&\int\csc x\cot x\,dx&=-\csc x+C.
\end{align*}
Las integrales de secante, cosecante y tangente se justifican en los ejercicios A.30--A.36 mediante cambios de variable y derivadas de logaritmos.

\subsection{Dominio y comprobación}
Cada respuesta vale en intervalos donde el integrando sea real y esté definido. Se excluyen ceros de denominadores; una raíz cuadrada en un denominador exige radicando positivo. Las potencias con denominador impar se interpretan mediante raíces reales: $z^{1/3}=\sqrt[3]{z}$ y $z^{4/3}=(\sqrt[3]{z})^4$, incluso para $z<0$. La constante puede ser distinta en intervalos separados por singularidades.

En cada caja, $I$ representa la integral buscada y $F$ su resultado sin $C$. Se calcula $F'$ y se simplifica hasta recuperar el integrando. Así se revisan exponentes, signos, factores del diferencial y condiciones iniciales \citep{thomas2018calculus}.

\section{Ejercicios 4.1: antiderivación directa}
''']
count=0
def e(num,var,integrand,method,steps,result,check,domain=''):
 global count
 count+=1
 parts.append(r'\begin{examplebox}{Ejercicio '+num+'}\n'+r'\textbf{Integral:} $\displaystyle I=\int '+integrand+r'\,d'+var+'$.\n\n'+r'\textbf{1. Método y preparación.} '+method+'\n\n'+r'\textbf{2. Desarrollo.}'+ '\n'+r'\begin{align*}'+ '\n'+steps+'\n'+r'\end{align*}'+'\n'+r'\textbf{3. Resultado.}'+ '\n'+r'\['+'\n'+result+'+C.\n'+r'\]'+'\n'+r'\textbf{4. Verificación por derivación.}'+ '\n'+r'\begin{align*}'+'\n'+check+'\n'+r'\end{align*}'+'\n'+(r'\textbf{Dominio.} '+domain+'\n' if domain else '')+r'\end{examplebox}'+'\n')
def sec(title):parts.append('\n'+r'\section{'+title+'}\n')
# Cada cadena matemática es explícita y editable en el .tex generado.
e('4.1.1','x',r'3x^4',r'El coeficiente $3$ es constante; se aplica la regla de la potencia con $n=4$.',r'I&=3\int x^4\,dx=3\frac{x^{4+1}}{4+1}+C.',r'\frac35x^5',r'F\prime(x)&=\frac35(5x^4)=3x^4.')
e('4.1.2','x',r'2x^7',r'Se saca el factor $2$ y se aumenta el exponente de $7$ a $8$.',r'I&=2\int x^7\,dx=2\frac{x^8}{8}+C.',r'\frac14x^8',r'F\prime(x)&=\frac14(8x^7)=2x^7.')
e('4.1.3','x',r'\frac1{x^3}',r'Se escribe $1/x^3=x^{-3}$; el nuevo exponente es $-3+1=-2$.',r'I&=\int x^{-3}\,dx=\frac{x^{-2}}{-2}+C.',r'-\frac1{2x^2}',r'F\prime(x)&=-\frac12(-2)x^{-3}=\frac1{x^3}.',r'$x\ne0$.')
e('4.1.4','t',r'\frac3{t^5}',r'Se transforma el denominador en potencia negativa: $3/t^5=3t^{-5}$.',r'I&=3\int t^{-5}\,dt=3\frac{t^{-4}}{-4}+C.',r'-\frac3{4t^4}',r'F\prime(t)&=-\frac34(-4)t^{-5}=\frac3{t^5}.',r'$t\ne0$.')
e('4.1.5','u',r'5u^{3/2}',r'La letra $u$ ya es la variable original; no se necesita otro cambio. Se calcula $3/2+1=5/2$.',r'I&=5\frac{u^{5/2}}{5/2}+C=5\left(\frac25\right)u^{5/2}+C.',r'2u^{5/2}',r'F\prime(u)&=2\left(\frac52\right)u^{3/2}=5u^{3/2}.',r'$u\ge0$; la derivación usual se realiza para $u>0$.')
e('4.1.6','x',r'10\sqrt[3]{x^2}',r'La raíz cúbica se representa como $x^{2/3}$; $2/3+1=5/3$.',r'I&=10\int x^{2/3}\,dx=10\frac{x^{5/3}}{5/3}+C=10\left(\frac35\right)x^{5/3}+C.',r'6x^{5/3}',r'F\prime(x)&=6\left(\frac53\right)x^{2/3}=10\sqrt[3]{x^2}.',r'Todos los reales; en $x=0$ la derivada también vale $0$ por su definición.')
e('4.1.7','x',r'\frac2{\sqrt[3]{x}}',r'Se usa $2/\sqrt[3]{x}=2x^{-1/3}$ y $-1/3+1=2/3$.',r'I&=2\frac{x^{2/3}}{2/3}+C=2\left(\frac32\right)x^{2/3}+C.',r'3x^{2/3}',r'F\prime(x)&=3\left(\frac23\right)x^{-1/3}=\frac2{\sqrt[3]{x}}.',r'$x\ne0$.')
e('4.1.8','y',r'\frac3{\sqrt y}',r'Se escribe $3y^{-1/2}$ y se calcula $-1/2+1=1/2$.',r'I&=3\frac{y^{1/2}}{1/2}+C=3(2)y^{1/2}+C.',r'6\sqrt y',r'F\prime(y)&=6\left(\frac12\right)y^{-1/2}=\frac3{\sqrt y}.',r'$y>0$.')
e('4.1.9','t',r'6t^2\sqrt[3]t',r'En el producto se suman exponentes: $t^2t^{1/3}=t^{7/3}$.',r'I&=6\int t^{7/3}\,dt=6\frac{t^{10/3}}{10/3}+C=6\left(\frac3{10}\right)t^{10/3}+C.',r'\frac95t^{10/3}',r'F\prime(t)&=\frac95\left(\frac{10}3\right)t^{7/3}=6t^2\sqrt[3]t.',r'Todos los reales, con raíz cúbica real; en $t=0$ la derivada es $0$.')
e('4.1.10','u',r'(3u^5-2u^3)',r'La linealidad permite integrar cada monomio; $u$ es la variable original.',r'I&=3\int u^5\,du-2\int u^3\,du\\&=3\frac{u^6}{6}-2\frac{u^4}{4}+C.',r'\frac{u^6-u^4}{2}',r'F\prime(u)&=\frac12(6u^5)-\frac12(4u^3)=3u^5-2u^3.')
e('4.1.11','y',r'y^3(2y^2-3)',r'Primero se distribuye $y^3$: $y^3(2y^2-3)=2y^5-3y^3$.',r'I&=2\int y^5\,dy-3\int y^3\,dy\\&=2\frac{y^6}{6}-3\frac{y^4}{4}+C.',r'\frac{y^6}{3}-\frac{3y^4}{4}',r'F\prime(y)&=\frac63y^5-\frac{12}4y^3=2y^5-3y^3=y^3(2y^2-3).')
e('4.1.12','x',r'x^4(5-x^2)',r'La fuente contiene $x^2$ dentro del paréntesis. Al distribuir: $5x^4-x^{4+2}=5x^4-x^6$.',r'I&=5\int x^4\,dx-\int x^6\,dx\\&=5\frac{x^5}{5}-\frac{x^7}{7}+C.',r'x^5-\frac{x^7}{7}',r'F\prime(x)&=5x^4-\frac77x^6=x^4(5-x^2).')
e('4.1.13','x',r'(8x^4+4x^3-6x^2-4x+5)',r'Se aplica linealidad a los cinco términos, incluyendo la constante $5=5x^0$.',r'I&=8\frac{x^5}{5}+4\frac{x^4}{4}-6\frac{x^3}{3}-4\frac{x^2}{2}+5x+C.',r'\frac85x^5+x^4-2x^3-2x^2+5x',r'F\prime(x)&=\frac85(5x^4)+4x^3-2(3x^2)-2(2x)+5\\&=8x^4+4x^3-6x^2-4x+5.')
e('4.1.14','x',r'(2+3x^2-8x^3)',r'La integral de una constante $k$ es $kx$; los otros términos siguen la regla de la potencia.',r'I&=2\int1\,dx+3\int x^2\,dx-8\int x^3\,dx\\&=2x+3\frac{x^3}{3}-8\frac{x^4}{4}+C.',r'2x+x^3-2x^4',r'F\prime(x)&=2+3x^2-2(4x^3)=2+3x^2-8x^3.')
e('4.1.15','x',r'\sqrt x(x+1)',r'Se distribuye $x^{1/2}$: $x^{1/2}x+x^{1/2}=x^{3/2}+x^{1/2}$.',r'I&=\frac{x^{5/2}}{5/2}+\frac{x^{3/2}}{3/2}+C\\&=\frac25x^{5/2}+\frac23x^{3/2}+C.',r'\frac25x^{5/2}+\frac23x^{3/2}',r'F\prime(x)&=\frac25\frac52x^{3/2}+\frac23\frac32x^{1/2}\\&=x^{3/2}+x^{1/2}=\sqrt x(x+1).',r'$x\ge0$; se deriva en el interior $x>0$.')
e('4.1.16','x',r'\left(\sqrt x-\frac1{\sqrt x}\right)',r'Se expresan los radicales como $x^{1/2}-x^{-1/2}$.',r'I&=\frac{x^{3/2}}{3/2}-\frac{x^{1/2}}{1/2}+C.',r'\frac23x^{3/2}-2\sqrt x',r'F\prime(x)&=\frac23\frac32x^{1/2}-2\frac12x^{-1/2}=\sqrt x-\frac1{\sqrt x}.',r'$x>0$.')
e('4.1.17','x',r'\left(\frac2{x^3}+\frac3{x^2}+5\right)',r'El integrando es $2x^{-3}+3x^{-2}+5$; los exponentes resultantes son $-2$ y $-1$.',r'I&=2\frac{x^{-2}}{-2}+3\frac{x^{-1}}{-1}+5x+C.',r'-\frac1{x^2}-\frac3x+5x',r'F\prime(x)&=-(-2)x^{-3}-3(-1)x^{-2}+5=\frac2{x^3}+\frac3{x^2}+5.',r'$x\ne0$.')
e('4.1.18','x',r'\left(3-\frac1{x^4}+\frac1{x^2}\right)',r'Se conserva el signo negativo de $-x^{-4}$ al dividir entre $-3$.',r'I&=3x-\frac{x^{-3}}{-3}+\frac{x^{-1}}{-1}+C.',r'3x+\frac1{3x^3}-\frac1x',r'F\prime(x)&=3+\frac13(-3)x^{-4}-(-1)x^{-2}\\&=3-\frac1{x^4}+\frac1{x^2}.',r'$x\ne0$.')
e('4.1.19','x',r'\frac{x^2+4x-4}{\sqrt x}',r'El radical está en el denominador. Se divide cada término entre $x^{1/2}$ y se restan exponentes.',r'\frac{x^2+4x-4}{\sqrt x}&=x^{3/2}+4x^{1/2}-4x^{-1/2},\\I&=\frac{x^{5/2}}{5/2}+4\frac{x^{3/2}}{3/2}-4\frac{x^{1/2}}{1/2}+C.',r'\frac25x^{5/2}+\frac83x^{3/2}-8\sqrt x',r'F\prime(x)&=x^{3/2}+4x^{1/2}-4x^{-1/2}\\&=\frac{x^2+4x-4}{\sqrt x}.',r'$x>0$.')
e('4.1.20','y',r'\frac{y^4+2y^2-1}{\sqrt y}',r'Se divide término a término entre $y^{1/2}$: los exponentes son $7/2$, $3/2$ y $-1/2$.',r'I&=\int(y^{7/2}+2y^{3/2}-y^{-1/2})\,dy\\&=\frac{y^{9/2}}{9/2}+2\frac{y^{5/2}}{5/2}-\frac{y^{1/2}}{1/2}+C.',r'\frac29y^{9/2}+\frac45y^{5/2}-2\sqrt y',r'F\prime(y)&=y^{7/2}+2y^{3/2}-y^{-1/2}=\frac{y^4+2y^2-1}{\sqrt y}.',r'$y>0$.')
e('4.1.21','x',r'\left(\sqrt[3]x+\frac1{\sqrt[3]x}\right)',r'Se utilizan las potencias $x^{1/3}+x^{-1/3}$.',r'I&=\frac{x^{4/3}}{4/3}+\frac{x^{2/3}}{2/3}+C.',r'\frac34x^{4/3}+\frac32x^{2/3}',r'F\prime(x)&=\frac34\frac43x^{1/3}+\frac32\frac23x^{-1/3}\\&=\sqrt[3]x+\frac1{\sqrt[3]x}.',r'$x\ne0$; raíces cúbicas reales.')
e('4.1.22','t',r'\frac{27t^3-1}{\sqrt[3]t}',r'El denominador es $\sqrt[3]t$. Se obtiene $27t^{3-1/3}-t^{-1/3}=27t^{8/3}-t^{-1/3}$.',r'I&=27\frac{t^{11/3}}{11/3}-\frac{t^{2/3}}{2/3}+C\\&=27\left(\frac3{11}\right)t^{11/3}-\frac32t^{2/3}+C.',r'\frac{81}{11}t^{11/3}-\frac32t^{2/3}',r'F\prime(t)&=\frac{81}{11}\frac{11}3t^{8/3}-\frac32\frac23t^{-1/3}\\&=27t^{8/3}-t^{-1/3}=\frac{27t^3-1}{\sqrt[3]t}.',r'$t\ne0$.')
e('4.1.23','t',r'(3\sen t-2\cos t)',r'Se usan $\int\sen t\,dt=-\cos t$ y $\int\cos t\,dt=\sen t$.',r'I&=3\int\sen t\,dt-2\int\cos t\,dt\\&=3(-\cos t)-2\sen t+C.',r'-3\cos t-2\sen t',r'F\prime(t)&=-3(-\sen t)-2\cos t=3\sen t-2\cos t.')
e('4.1.24','x',r'(5\cos x-4\sen x)',r'Integrar $\sen x$ introduce un signo negativo que se combina con el coeficiente $-4$.',r'I&=5\int\cos x\,dx-4\int\sen x\,dx\\&=5\sen x-4(-\cos x)+C.',r'5\sen x+4\cos x',r'F\prime(x)&=5\cos x+4(-\sen x)=5\cos x-4\sen x.')
e('4.1.25','x',r'\frac{\sen x}{\cos^2x}',r'Para mostrar el factor de signo, se toma $u=\cos x$, $du=-\sen x\,dx$, de donde $\sen x\,dx=-du$.',r'I&=-\int u^{-2}\,du=-\frac{u^{-1}}{-1}+C=u^{-1}+C.',r'\frac1{\cos x}=\sec x',r'F\prime(x)&=-\cos^{-2}x(-\sen x)=\frac{\sen x}{\cos^2x}.',r'$\cos x\ne0$.')
e('4.1.26','x',r'\frac{\cos x}{\sen^2x}',r'Se elige $u=\sen x$ y $du=\cos x\,dx$; el denominador pasa a ser $u^2$.',r'I&=\int u^{-2}\,du=\frac{u^{-1}}{-1}+C=-u^{-1}+C.',r'-\frac1{\sen x}=-\csc x',r'F\prime(x)&=-[-\sen^{-2}x\cos x]=\frac{\cos x}{\sen^2x}.',r'$\sen x\ne0$.')
e('4.1.27','x',r'(4\csc x\cot x+2\sec^2x)',r'Se reconocen las derivadas $(\csc x)\prime=-\csc x\cot x$ y $(\tan x)\prime=\sec^2x$.',r'I&=4\int\csc x\cot x\,dx+2\int\sec^2x\,dx\\&=4(-\csc x)+2\tan x+C.',r'-4\csc x+2\tan x',r'F\prime(x)&=-4(-\csc x\cot x)+2\sec^2x\\&=4\csc x\cot x+2\sec^2x.',r'$\sen x\ne0$ y $\cos x\ne0$.')
e('4.1.28','t',r'(3\csc^2t-5\sec t\tan t)',r'Se usan las antiderivadas $-\cot t$ y $\sec t$, respectivamente.',r'I&=3\int\csc^2t\,dt-5\int\sec t\tan t\,dt\\&=3(-\cot t)-5\sec t+C.',r'-3\cot t-5\sec t',r'F\prime(t)&=-3(-\csc^2t)-5\sec t\tan t\\&=3\csc^2t-5\sec t\tan t.',r'$\sen t\ne0$ y $\cos t\ne0$.')
sec('Ejercicios 4.2: sustitución y aplicación')
e('4.2.1','y',r'\sqrt{1-4y}',r'Se elige $u=1-4y$ porque es el radicando. Entonces $du=-4\,dy$ y $dy=-du/4$.',r'I&=-\frac14\int u^{1/2}\,du=-\frac14\frac{u^{3/2}}{3/2}+C\\&=-\frac14\frac23u^{3/2}+C=-\frac16u^{3/2}+C.',r'-\frac16(1-4y)^{3/2}',r'F\prime(y)&=-\frac16\frac32(1-4y)^{1/2}(-4)=\sqrt{1-4y}.',r'$y\le1/4$; la derivación se realiza en el interior.')
e('4.2.2','x',r'\sqrt[3]{3x-4}',r'Se toma $u=3x-4$, $du=3\,dx$ y $dx=du/3$.',r'I&=\frac13\int u^{1/3}\,du=\frac13\frac{u^{4/3}}{4/3}+C\\&=\frac13\frac34u^{4/3}+C=\frac14u^{4/3}+C.',r'\frac14(3x-4)^{4/3}',r'F\prime(x)&=\frac14\frac43(3x-4)^{1/3}(3)=\sqrt[3]{3x-4}.',r'Todos los reales. En $x=4/3$ la derivada vale $0$ por continuidad del integrando y por el cociente incremental.')
e('4.2.3','x',r'x\sqrt[3]{x^2-9}',r'Se elige $u=x^2-9$. Su diferencial es $du=2x\,dx$, así que $x\,dx=du/2$.',r'I&=\frac12\int u^{1/3}\,du=\frac12\frac{u^{4/3}}{4/3}+C\\&=\frac12\frac34u^{4/3}+C=\frac38u^{4/3}+C.',r'\frac38(x^2-9)^{4/3}',r'F\prime(x)&=\frac38\frac43(x^2-9)^{1/3}(2x)\\&=x\sqrt[3]{x^2-9}.',r'Todos los reales, con raíz cúbica real. En $x=\pm3$ la derivada es $0$.')
e('4.2.4','x',r'x(2x^2+1)^6',r'La expresión elevada a la sexta potencia es $u=2x^2+1$. Se obtiene $du=4x\,dx$ y $x\,dx=du/4$.',r'I&=\frac14\int u^6\,du=\frac14\frac{u^7}{7}+C=\frac{u^7}{28}+C.',r'\frac{(2x^2+1)^7}{28}',r'F\prime(x)&=\frac1{28}(7)(2x^2+1)^6(4x)=x(2x^2+1)^6.')
e('4.2.5','x',r'x^2(x^3-1)^{10}',r'Se toma $u=x^3-1$, por lo que $du=3x^2\,dx$ y $x^2\,dx=du/3$.',r'I&=\frac13\int u^{10}\,du=\frac13\frac{u^{11}}{11}+C=\frac{u^{11}}{33}+C.',r'\frac{(x^3-1)^{11}}{33}',r'F\prime(x)&=\frac1{33}(11)(x^3-1)^{10}(3x^2)=x^2(x^3-1)^{10}.')
e('4.2.6','x',r'3x\sqrt{4-x^2}',r'Se elige $u=4-x^2$, $du=-2x\,dx$; por tanto $3x\,dx=-3\,du/2$.',r'I&=-\frac32\int u^{1/2}\,du=-\frac32\frac23u^{3/2}+C=-u^{3/2}+C.',r'-(4-x^2)^{3/2}',r'F\prime(x)&=-\frac32(4-x^2)^{1/2}(-2x)=3x\sqrt{4-x^2}.',r'$-2\le x\le2$; derivación en $(-2,2)$.')
e('4.2.7','y',r'\frac{y^3}{(1-2y^4)^5}',r'Se toma $u=1-2y^4$, $du=-8y^3\,dy$ y $y^3\,dy=-du/8$. El denominador se escribe $u^{-5}$.',r'I&=-\frac18\int u^{-5}\,du=-\frac18\frac{u^{-4}}{-4}+C=\frac1{32}u^{-4}+C.',r'\frac1{32(1-2y^4)^4}',r'F\prime(y)&=\frac1{32}(-4)(1-2y^4)^{-5}(-8y^3)\\&=\frac{y^3}{(1-2y^4)^5}.',r'$1-2y^4\ne0$.')
e('4.2.8','s',r'\frac{s}{\sqrt{3s^2+1}}',r'Se define $u=3s^2+1$, $du=6s\,ds$, de modo que $s\,ds=du/6$.',r'I&=\frac16\int u^{-1/2}\,du=\frac16\frac{u^{1/2}}{1/2}+C=\frac13u^{1/2}+C.',r'\frac13\sqrt{3s^2+1}',r'F\prime(s)&=\frac13\frac12(3s^2+1)^{-1/2}(6s)=\frac{s}{\sqrt{3s^2+1}}.',r'Todos los reales, pues $3s^2+1>0$.')
e('4.2.9','x',r'(x^2-4x+4)^{4/3}',r'Primero se reconoce el cuadrado perfecto $x^2-4x+4=(x-2)^2$. Con $u=x-2$ y $du=dx$, la raíz cúbica real permite escribir $(u^2)^{4/3}=u^{8/3}$.',r'I&=\int u^{8/3}\,du=\frac{u^{11/3}}{11/3}+C=\frac3{11}u^{11/3}+C.',r'\frac3{11}(x-2)^{11/3}',r'F\prime(x)&=\frac3{11}\frac{11}3(x-2)^{8/3}\\&=[(x-2)^2]^{4/3}=(x^2-4x+4)^{4/3}.',r'Todos los reales. En $x=2$, el cociente incremental da derivada $0$.')
e('4.2.10','x',r'x^4\sqrt{3x^5-5}',r'Se toma $u=3x^5-5$, $du=15x^4\,dx$ y $x^4\,dx=du/15$.',r'I&=\frac1{15}\int u^{1/2}\,du=\frac1{15}\frac23u^{3/2}+C=\frac2{45}u^{3/2}+C.',r'\frac2{45}(3x^5-5)^{3/2}',r'F\prime(x)&=\frac2{45}\frac32(3x^5-5)^{1/2}(15x^4)\\&=x^4\sqrt{3x^5-5}.',r'$x\ge(5/3)^{1/5}$; derivación en el interior.')
e('4.2.11','x',r'x\sqrt{x+2}',r'Se define $u=x+2$, $du=dx$. Es necesario sustituir también el factor $x=u-2$.',r'I&=\int(u-2)u^{1/2}\,du=\int(u^{3/2}-2u^{1/2})\,du\\&=\frac{u^{5/2}}{5/2}-2\frac{u^{3/2}}{3/2}+C.',r'\frac25(x+2)^{5/2}-\frac43(x+2)^{3/2}',r'F\prime(x)&=(x+2)^{3/2}-2(x+2)^{1/2}\\&=\sqrt{x+2}[(x+2)-2]=x\sqrt{x+2}.',r'$x\ge-2$; derivación para $x>-2$.')
e('4.2.12','t',r'\frac{t}{\sqrt{t+3}}',r'Con $u=t+3$, se tiene $dt=du$ y $t=u-3$. Se sustituye el numerador completo.',r'I&=\int(u-3)u^{-1/2}\,du=\int(u^{1/2}-3u^{-1/2})\,du\\&=\frac23u^{3/2}-6u^{1/2}+C.',r'\frac23(t+3)^{3/2}-6\sqrt{t+3}',r'F\prime(t)&=(t+3)^{1/2}-3(t+3)^{-1/2}\\&=\frac{(t+3)-3}{\sqrt{t+3}}=\frac t{\sqrt{t+3}}.',r'$t>-3$.')
e('4.2.13','r',r'\frac{2r}{(1-r)^7}',r'Se elige $u=1-r$, $dr=-du$ y $r=1-u$. El signo del diferencial afecta a todo el numerador.',r'I&=-2\int(1-u)u^{-7}\,du\\&=-2\int(u^{-7}-u^{-6})\,du\\&=-2\left(\frac{u^{-6}}{-6}-\frac{u^{-5}}{-5}\right)+C.',r'\frac1{3(1-r)^6}-\frac2{5(1-r)^5}',r'F\prime(r)&=2(1-r)^{-7}-2(1-r)^{-6}\\&=\frac{2-2(1-r)}{(1-r)^7}=\frac{2r}{(1-r)^7}.',r'$r\ne1$.')
e('4.2.14','x',r'x^3(2-x^2)^{12}',r'Se toma $u=2-x^2$, $du=-2x\,dx$. Se descompone $x^3dx=x^2(x\,dx)$ y se usa $x^2=2-u$.',r'I&=-\frac12\int(2-u)u^{12}\,du\\&=\int\left(-u^{12}+\frac12u^{13}\right)\,du\\&=-\frac{u^{13}}{13}+\frac{u^{14}}{28}+C.',r'-\frac{(2-x^2)^{13}}{13}+\frac{(2-x^2)^{14}}{28}',r'F\prime(x)&=2x(2-x^2)^{12}-x(2-x^2)^{13}\\&=x(2-x^2)^{12}[2-(2-x^2)]\\&=x^3(2-x^2)^{12}.')
parts.append(r'\noindent\textit{La captura continúa con los ejercicios 36--45; se respeta ese salto de numeración.}'+'\n')
e('4.2.36','x',r'x(x^2+1)\sqrt{4-2x^2-x^4}',r'Se desarrolla $(x^2+1)^2=x^4+2x^2+1$, por lo que el radicando es $5-(x^2+1)^2$. Primero, $u=x^2+1$ y $x\,dx=du/2$. Después, $v=5-u^2$ y $u\,du=-dv/2$.',r'I&=\frac12\int u\sqrt{5-u^2}\,du\\&=\frac12\left(-\frac12\right)\int v^{1/2}\,dv\\&=-\frac14\frac23v^{3/2}+C=-\frac16[5-u^2]^{3/2}+C.',r'-\frac16(4-2x^2-x^4)^{3/2}',r'F\prime(x)&=-\frac16\frac32(4-2x^2-x^4)^{1/2}(-4x-4x^3)\\&=x(x^2+1)\sqrt{4-2x^2-x^4}.',r'$|x|\le\sqrt{\sqrt5-1}$; se deriva en el interior. También puede hacerse en un solo cambio con $v=4-2x^2-x^4$ y $dv=-4x(1+x^2)dx$.')
e('4.2.37','y',r'\frac{y+3}{(3-y)^{2/3}}',r'Con $u=3-y$, $dy=-du$, $y=3-u$ y $y+3=6-u$. Se sustituye también el numerador.',r'I&=-\int(6-u)u^{-2/3}\,du\\&=\int(-6u^{-2/3}+u^{1/3})\,du\\&=-6\frac{u^{1/3}}{1/3}+\frac{u^{4/3}}{4/3}+C.',r'-18(3-y)^{1/3}+\frac34(3-y)^{4/3}',r'F\prime(y)&=6(3-y)^{-2/3}-(3-y)^{1/3}\\&=\frac{6-(3-y)}{(3-y)^{2/3}}=\frac{y+3}{(3-y)^{2/3}}.',r'$y\ne3$; las raíces cúbicas se toman reales.')
e('4.2.38','s',r'\sqrt{3+s}\,(s+1)^2',r'Se toma $u=s+3$, $ds=du$ y $s+1=u-2$. Se expande $(u-2)^2=u^2-4u+4$.',r'I&=\int u^{1/2}(u^2-4u+4)\,du\\&=\int(u^{5/2}-4u^{3/2}+4u^{1/2})\,du\\&=\frac27u^{7/2}-\frac85u^{5/2}+\frac83u^{3/2}+C.',r'\frac27(s+3)^{7/2}-\frac85(s+3)^{5/2}+\frac83(s+3)^{3/2}',r'F\prime(s)&=(s+3)^{5/2}-4(s+3)^{3/2}+4(s+3)^{1/2}\\&=\sqrt{s+3}[(s+3)^2-4(s+3)+4]\\&=\sqrt{s+3}(s+1)^2.',r'$s\ge-3$; derivación en $s>-3$.')
e('4.2.39','r',r'\frac{(r^{1/3}+2)^4}{\sqrt[3]{r^2}}',r'Se define $u=r^{1/3}+2$, $du=\tfrac13r^{-2/3}dr$. Entonces $dr/\sqrt[3]{r^2}=3\,du$.',r'I&=3\int u^4\,du=3\frac{u^5}{5}+C.',r'\frac35(r^{1/3}+2)^5',r'F\prime(r)&=\frac35(5)(r^{1/3}+2)^4\left(\frac13r^{-2/3}\right)\\&=\frac{(r^{1/3}+2)^4}{\sqrt[3]{r^2}}.',r'$r\ne0$.')
e('4.2.40','t',r'\left(t+\frac1t\right)^{3/2}\frac{t^2-1}{t^2}',r'La derivada de $u=t+1/t$ es $1-1/t^2=(t^2-1)/t^2$. Todo el segundo factor queda incluido en $du$.',r'du&=\frac{t^2-1}{t^2}\,dt,\\I&=\int u^{3/2}\,du=\frac{u^{5/2}}{5/2}+C=\frac25u^{5/2}+C.',r'\frac25\left(t+\frac1t\right)^{5/2}',r'F\prime(t)&=\frac25\frac52\left(t+\frac1t\right)^{3/2}\left(1-\frac1{t^2}\right)\\&=\left(t+\frac1t\right)^{3/2}\frac{t^2-1}{t^2}.',r'$t>0$ para que la potencia de denominador par sea real y $t\ne0$.')
e('4.2.41','x',r'\frac{x^3}{(x^2+4)^{3/2}}',r'Se usa $u=x^2+4$, $x\,dx=du/2$ y $x^2=u-4$. Se separa $x^3dx=x^2(x\,dx)$.',r'I&=\frac12\int(u-4)u^{-3/2}\,du\\&=\frac12\int(u^{-1/2}-4u^{-3/2})\,du\\&=\frac12\left(2u^{1/2}+8u^{-1/2}\right)+C.',r'\sqrt{x^2+4}+\frac4{\sqrt{x^2+4}}',r'F\prime(x)&=\frac{x}{\sqrt{x^2+4}}-\frac{4x}{(x^2+4)^{3/2}}\\&=\frac{x(x^2+4)-4x}{(x^2+4)^{3/2}}=\frac{x^3}{(x^2+4)^{3/2}}.',r'Todos los reales, pues $x^2+4>0$.')
e('4.2.42','x',r'\frac{x^3}{\sqrt{1-2x^2}}',r'El numerador $x^3$ exige conservar $x^2$ al sustituir. Sea $u=1-2x^2$, $x\,dx=-du/4$ y $x^2=(1-u)/2$.',r'I&=-\frac18\int(1-u)u^{-1/2}\,du\\&=-\frac18\int(u^{-1/2}-u^{1/2})\,du\\&=-\frac14u^{1/2}+\frac1{12}u^{3/2}+C.',r'-\frac14\sqrt{1-2x^2}+\frac1{12}(1-2x^2)^{3/2}',r'F\prime(x)&=\frac{x}{2\sqrt{1-2x^2}}-\frac{x}{2}\sqrt{1-2x^2}\\&=\frac{x[1-(1-2x^2)]}{2\sqrt{1-2x^2}}=\frac{x^3}{\sqrt{1-2x^2}}.',r'$|x|<1/\sqrt2$.')
e('4.2.43','x',r'\sen x\,\sen(\cos x)',r'Se toma la función interna $u=\cos x$, $du=-\sen x\,dx$, por lo que $\sen x\,dx=-du$.',r'I&=-\int\sen u\,du=-(-\cos u)+C=\cos u+C.',r'\cos(\cos x)',r'F\prime(x)&=-\sen(\cos x)(-\sen x)=\sen x\,\sen(\cos x).')
e('4.2.44','x',r'\sec x\tan x\cos(\sec x)',r'Se toma $u=\sec x$ y $du=\sec x\tan x\,dx$. El producto exterior es exactamente la derivada de la función interna.',r'I&=\int\cos u\,du=\sen u+C.',r'\sen(\sec x)',r'F\prime(x)&=\cos(\sec x)\,\sec x\tan x.',r'$\cos x\ne0$.')
count+=1
parts.append(r'''\begin{examplebox}{Ejercicio 4.2.45: función de costo total}
\textbf{Enunciado.} El costo marginal es $C'(x)=3(5x+4)^{-1/2}$ y el costo general es de \$10. Se interpreta este último como costo fijo: $C(0)=10$.

\textbf{1. Cambio de variable.} Para recuperar el costo se integra $C'(x)$. Se usa una constante $K$ para no confundirla con el nombre de la función:
\[
 u=5x+4,\qquad du=5\,dx,\qquad dx=\frac{du}{5}.
\]
\textbf{2. Integración y sustitución inversa.}
\begin{align*}
 C(x)&=\frac35\int u^{-1/2}\,du
 =\frac35\frac{u^{1/2}}{1/2}+K\\
 &=\frac65\sqrt{5x+4}+K.
\end{align*}
\textbf{3. Condición inicial.} El dato de costo fijo determina la constante:
\[
 10=C(0)=\frac65\sqrt4+K=\frac{12}5+K,
 \qquad K=10-\frac{12}5=\frac{38}5.
\]
\textbf{Resultado:}
\[
 \boxed{C(x)=\frac65\sqrt{5x+4}+\frac{38}5},\qquad x\ge0.
\]
\textbf{4. Verificación e interpretación.}
\[
 C'(x)=\frac65\frac12(5x+4)^{-1/2}(5)
 =3(5x+4)^{-1/2},\qquad C(0)=10.
\]
Para una cantidad producida $x\ge0$, el costo total parte de \$10 y aumenta porque su derivada es positiva. La fórmula satisface tanto la tasa marginal como el costo fijo.
\end{examplebox}
''')
sec('Lista A: funciones algebraicas, logarítmicas y trigonométricas')
parts.append(r'La numeración A.1--A.24 corresponde a la tercera imagen; A.25--A.36, a la cuarta.'+'\n')
e('A.1','x',r'\frac5x',r'El exponente de $x$ es $-1$, por lo que se usa el logaritmo y no la regla de la potencia.',r'I&=5\int\frac{dx}{x}=5\ln|x|+C.',r'5\ln|x|',r'F\prime(x)&=5\frac1x=\frac5x.',r'$x\ne0$.')
e('A.2','x',r'\frac{10}x',r'Se extrae la constante $10$ y se integra $1/x$.',r'I&=10\int\frac{dx}{x}=10\ln|x|+C.',r'10\ln|x|',r'F\prime(x)&=10\frac1x=\frac{10}x.',r'$x\ne0$.')
e('A.3','x',r'\frac1{x+1}',r'Se elige $u=x+1$, $du=dx$. La derivada del denominador coincide con el numerador.',r'I&=\int\frac{du}{u}=\ln|u|+C.',r'\ln|x+1|',r'F\prime(x)&=\frac1{x+1}\frac{d}{dx}(x+1)=\frac1{x+1}.',r'$x\ne-1$.')
e('A.4','x',r'\frac1{x-5}',r'Se toma $u=x-5$ y $du=dx$.',r'I&=\int\frac{du}{u}=\ln|u|+C.',r'\ln|x-5|',r'F\prime(x)&=\frac1{x-5}(1)=\frac1{x-5}.',r'$x\ne5$.')
e('A.5','x',r'\frac1{3-2x}',r'Sea $u=3-2x$, $du=-2\,dx$, de donde $dx=-du/2$. Este factor negativo debe conservarse.',r'I&=-\frac12\int\frac{du}{u}=-\frac12\ln|u|+C.',r'-\frac12\ln|3-2x|',r'F\prime(x)&=-\frac12\frac{-2}{3-2x}=\frac1{3-2x}.',r'$x\ne3/2$.')
e('A.6','x',r'\frac1{3x+2}',r'Con $u=3x+2$, $du=3\,dx$ y $dx=du/3$.',r'I&=\frac13\int\frac{du}{u}=\frac13\ln|u|+C.',r'\frac13\ln|3x+2|',r'F\prime(x)&=\frac13\frac3{3x+2}=\frac1{3x+2}.',r'$x\ne-2/3$.')
e('A.7','x',r'\frac{x}{x^2+1}',r'Se define $u=x^2+1$, $du=2x\,dx$ y $x\,dx=du/2$.',r'I&=\frac12\int\frac{du}{u}=\frac12\ln|u|+C.',r'\frac12\ln(x^2+1)',r'F\prime(x)&=\frac12\frac{2x}{x^2+1}=\frac{x}{x^2+1}.',r'Todos los reales; se omite el valor absoluto porque $x^2+1>0$.')
e('A.8','x',r'\frac{x^2}{3-x^3}',r'Se toma $u=3-x^3$, $du=-3x^2\,dx$ y $x^2\,dx=-du/3$.',r'I&=-\frac13\int\frac{du}{u}=-\frac13\ln|u|+C.',r'-\frac13\ln|3-x^3|',r'F\prime(x)&=-\frac13\frac{-3x^2}{3-x^3}=\frac{x^2}{3-x^3}.',r'$x\ne\sqrt[3]3$.')
e('A.9','x',r'\frac{x^2-4}{x}',r'Se divide cada término entre $x$: $(x^2-4)/x=x-4/x$.',r'I&=\int x\,dx-4\int\frac{dx}{x}\\&=\frac{x^2}{2}-4\ln|x|+C.',r'\frac{x^2}{2}-4\ln|x|',r'F\prime(x)&=x-\frac4x=\frac{x^2-4}{x}.',r'$x\ne0$.')
e('A.10','x',r'\frac{x}{\sqrt{9-x^2}}',r'Se toma $u=9-x^2$, $du=-2x\,dx$ y $x\,dx=-du/2$.',r'I&=-\frac12\int u^{-1/2}\,du=-\frac12\frac{u^{1/2}}{1/2}+C=-\sqrt u+C.',r'-\sqrt{9-x^2}',r'F\prime(x)&=-\frac12(9-x^2)^{-1/2}(-2x)=\frac{x}{\sqrt{9-x^2}}.',r'$-3<x<3$.')
e('A.11','x',r'\frac{x^2+2x+3}{x^3+3x^2+9x}',r'La derivada del denominador es tres veces el numerador. Se elige $u=x^3+3x^2+9x$, $du=3(x^2+2x+3)dx$.',r'(x^2+2x+3)\,dx&=\frac{du}{3},\\I&=\frac13\int\frac{du}{u}=\frac13\ln|u|+C.',r'\frac13\ln|x^3+3x^2+9x|',r'F\prime(x)&=\frac13\frac{3x^2+6x+9}{x^3+3x^2+9x}\\&=\frac{x^2+2x+3}{x^3+3x^2+9x}.',r'$x\ne0$, pues $x^2+3x+9=(x+3/2)^2+27/4>0$.')
e('A.12','x',r'\frac{x(x+2)}{x^3+3x^2-4}',r'Se toma $u=x^3+3x^2-4$. Entonces $du=(3x^2+6x)dx=3x(x+2)dx$.',r'x(x+2)\,dx&=\frac{du}{3},\\I&=\frac13\int\frac{du}{u}=\frac13\ln|u|+C.',r'\frac13\ln|x^3+3x^2-4|',r'F\prime(x)&=\frac13\frac{3x(x+2)}{x^3+3x^2-4}=\frac{x(x+2)}{x^3+3x^2-4}.',r'$x\ne1,-2$, porque $x^3+3x^2-4=(x-1)(x+2)^2$.')
e('A.13','x',r'\frac{x^2-3x+2}{x+1}',r'Se divide el polinomio. Primero $x^2/x=x$; al restar $x(x+1)$ queda $-4x+2$. Después $-4x/x=-4$; al restar $-4(x+1)$ queda $6$.',r'x^2-3x+2&=(x+1)(x-4)+6,\\I&=\int\left(x-4+\frac6{x+1}\right)dx\\&=\frac{x^2}{2}-4x+6\ln|x+1|+C.',r'\frac{x^2}{2}-4x+6\ln|x+1|',r'F\prime(x)&=x-4+\frac6{x+1}\\&=\frac{(x-4)(x+1)+6}{x+1}=\frac{x^2-3x+2}{x+1}.',r'$x\ne-1$.')
e('A.14','x',r'\frac{2x^2+7x-3}{x-2}',r'El primer término del cociente es $2x$ y el residuo parcial es $11x-3$. El segundo es $11$ y el residuo final es $19$.',r'2x^2+7x-3&=(x-2)(2x+11)+19,\\I&=\int\left(2x+11+\frac{19}{x-2}\right)dx\\&=x^2+11x+19\ln|x-2|+C.',r'x^2+11x+19\ln|x-2|',r'F\prime(x)&=2x+11+\frac{19}{x-2}\\&=\frac{(2x+11)(x-2)+19}{x-2}=\frac{2x^2+7x-3}{x-2}.',r'$x\ne2$.')
e('A.15','x',r'\frac{x^3-3x^2+5}{x-3}',r'Se divide $x^3$ entre $x$ y se obtiene $x^2$. Al restar $x^2(x-3)=x^3-3x^2$, sólo queda el residuo $5$.',r'x^3-3x^2+5&=(x-3)x^2+5,\\I&=\int\left(x^2+\frac5{x-3}\right)dx=\frac{x^3}{3}+5\ln|x-3|+C.',r'\frac{x^3}{3}+5\ln|x-3|',r'F\prime(x)&=x^2+\frac5{x-3}=\frac{x^2(x-3)+5}{x-3}\\&=\frac{x^3-3x^2+5}{x-3}.',r'$x\ne3$.')
e('A.16','x',r'\frac{x^3-6x-20}{x+5}',r'La división sucesiva produce $x^2$, $-5x$ y $19$. Los residuos parciales son $-5x^2-6x-20$, $19x-20$ y, finalmente, $-115$.',r'x^3-6x-20&=(x+5)(x^2-5x+19)-115,\\I&=\int\left(x^2-5x+19-\frac{115}{x+5}\right)dx\\&=\frac{x^3}{3}-\frac52x^2+19x-115\ln|x+5|+C.',r'\frac{x^3}{3}-\frac52x^2+19x-115\ln|x+5|',r'F\prime(x)&=x^2-5x+19-\frac{115}{x+5}\\&=\frac{(x^2-5x+19)(x+5)-115}{x+5}\\&=\frac{x^3-6x-20}{x+5}.',r'$x\ne-5$.')
e('A.17','x',r'\frac{x^4+x-4}{x^2+2}',r'La división da cociente $x^2-2$ y residuo $x$. Para la fracción restante, $u=x^2+2$, $du=2x\,dx$.',r'x^4+x-4&=(x^2+2)(x^2-2)+x,\\I&=\int(x^2-2)dx+\int\frac{x}{x^2+2}dx\\&=\frac{x^3}{3}-2x+\frac12\int\frac{du}{u}\\&=\frac{x^3}{3}-2x+\frac12\ln|u|+C.',r'\frac{x^3}{3}-2x+\frac12\ln(x^2+2)',r'F\prime(x)&=x^2-2+\frac{x}{x^2+2}\\&=\frac{(x^2-2)(x^2+2)+x}{x^2+2}=\frac{x^4+x-4}{x^2+2}.',r'Todos los reales, pues $x^2+2>0$.')
e('A.18','x',r'\frac{x^3-3x^2+4x-9}{x^2+3}',r'El cociente es $x-3$ y el residuo es $x$. En la fracción residual se toma $u=x^2+3$, $du=2x\,dx$.',r'x^3-3x^2+4x-9&=(x^2+3)(x-3)+x,\\I&=\int(x-3)dx+\frac12\int\frac{du}{u}\\&=\frac{x^2}{2}-3x+\frac12\ln|u|+C.',r'\frac{x^2}{2}-3x+\frac12\ln(x^2+3)',r'F\prime(x)&=x-3+\frac{x}{x^2+3}\\&=\frac{(x-3)(x^2+3)+x}{x^2+3}=\frac{x^3-3x^2+4x-9}{x^2+3}.',r'Todos los reales, pues $x^2+3>0$.')
e('A.19','x',r'\frac{(\ln x)^2}{x}',r'Se elige $u=\ln x$. El diferencial $du=dx/x$ ya está presente; queda una potencia cuadrática de $u$.',r'I&=\int u^2\,du=\frac{u^3}{3}+C.',r'\frac{(\ln x)^3}{3}',r'F\prime(x)&=\frac13(3)(\ln x)^2\frac1x=\frac{(\ln x)^2}{x}.',r'$x>0$.')
e('A.20','x',r'\frac1{x\ln(x^3)}',r'Se toma $u=\ln(x^3)$; por la regla de la cadena, $du=(3x^2/x^3)dx=3dx/x$, así que $dx/x=du/3$.',r'I&=\frac13\int\frac{du}{u}=\frac13\ln|u|+C.',r'\frac13\ln|\ln(x^3)|',r'F\prime(x)&=\frac13\frac1{\ln(x^3)}\frac3x=\frac1{x\ln(x^3)}.',r'$x>0$ y $x\ne1$. La expresión $\ln(x^3)$ no se define en los reales si $x\le0$.')
e('A.21','x',r'\frac1{\sqrt{x+1}}',r'La raíz abarca $x+1$. Se toma $u=x+1$, $du=dx$, y se escribe $u^{-1/2}$.',r'I&=\int u^{-1/2}\,du=\frac{u^{1/2}}{1/2}+C=2\sqrt u+C.',r'2\sqrt{x+1}',r'F\prime(x)&=2\frac12(x+1)^{-1/2}=\frac1{\sqrt{x+1}}.',r'$x>-1$.')
e('A.22','x',r'\frac1{x^{2/3}(1+x^{1/3})}',r'Se toma $u=1+x^{1/3}$, $du=\tfrac13x^{-2/3}dx$ y $dx/x^{2/3}=3\,du$.',r'I&=3\int\frac{du}{u}=3\ln|u|+C.',r'3\ln|1+x^{1/3}|',r'F\prime(x)&=\frac3{1+x^{1/3}}\frac13x^{-2/3}\\&=\frac1{x^{2/3}(1+x^{1/3})}.',r'$x\ne0,-1$; se usa la raíz cúbica real.')
e('A.23','x',r'\frac{2x}{(x-1)^2}',r'Sea $u=x-1$, $dx=du$ y $x=u+1$. Se expande el numerador después del cambio.',r'I&=2\int\frac{u+1}{u^2}\,du=2\int(u^{-1}+u^{-2})\,du\\&=2\ln|u|-2u^{-1}+C.',r'2\ln|x-1|-\frac2{x-1}',r'F\prime(x)&=\frac2{x-1}+\frac2{(x-1)^2}\\&=\frac{2(x-1)+2}{(x-1)^2}=\frac{2x}{(x-1)^2}.',r'$x\ne1$.')
e('A.24','x',r'\frac{x(x-2)}{(x-1)^3}',r'Con $u=x-1$, se tiene $x=u+1$, $x-2=u-1$ y $dx=du$. El producto del numerador es $(u+1)(u-1)=u^2-1$.',r'I&=\int\frac{u^2-1}{u^3}\,du=\int(u^{-1}-u^{-3})\,du\\&=\ln|u|-\frac{u^{-2}}{-2}+C=\ln|u|+\frac1{2u^2}+C.',r'\ln|x-1|+\frac1{2(x-1)^2}',r'F\prime(x)&=\frac1{x-1}-\frac1{(x-1)^3}\\&=\frac{(x-1)^2-1}{(x-1)^3}=\frac{x(x-2)}{(x-1)^3}.',r'$x\ne1$.')
e('A.25','x',r'\frac1{1+\sqrt{2x}}',r'Se sigue la sugerencia de tomar el denominador: $u=1+\sqrt{2x}$. Entonces $\sqrt{2x}=u-1$, $x=(u-1)^2/2$ y $dx=(u-1)du$.',r'I&=\int\frac{u-1}{u}\,du=\int(1-u^{-1})\,du\\&=u-\ln|u|+C\\&=1+\sqrt{2x}-\ln(1+\sqrt{2x})+C.',r'\sqrt{2x}-\ln(1+\sqrt{2x})',r'F\prime(x)&=\frac1{\sqrt{2x}}-\frac1{(1+\sqrt{2x})\sqrt{2x}}\\&=\frac{(1+\sqrt{2x})-1}{\sqrt{2x}(1+\sqrt{2x})}\\&=\frac1{1+\sqrt{2x}}\quad(x>0).',r'$x\ge0$. El término constante $1$ se absorbió en $C$. En $x=0$ la derivada lateral es $1$.')
e('A.26','x',r'\frac1{1+\sqrt{3x}}',r'Sea $u=1+\sqrt{3x}$. Se despeja $x=(u-1)^2/3$ y se deriva: $dx=\tfrac23(u-1)du$.',r'I&=\frac23\int\frac{u-1}{u}\,du=\frac23\int(1-u^{-1})\,du\\&=\frac23[u-\ln|u|]+C.',r'\frac23\sqrt{3x}-\frac23\ln(1+\sqrt{3x})',r'F\prime(x)&=\frac1{\sqrt{3x}}-\frac1{(1+\sqrt{3x})\sqrt{3x}}\\&=\frac1{1+\sqrt{3x}}\quad(x>0).',r'$x\ge0$. El término $2/3$ se absorbió en $C$; en $x=0$ la derivada lateral es $1$.')
e('A.27','x',r'\frac{\sqrt x}{\sqrt x-3}',r'Se elige $u=\sqrt x-3$. Entonces $\sqrt x=u+3$, $x=(u+3)^2$ y $dx=2(u+3)du$. Se sustituyen numerador, denominador y diferencial.',r'I&=2\int\frac{(u+3)^2}{u}\,du\\&=2\int\frac{u^2+6u+9}{u}\,du\\&=2\int(u+6+9u^{-1})\,du\\&=u^2+12u+18\ln|u|+C.',r'x+6\sqrt x+18\ln|\sqrt x-3|',r'F\prime(x)&=1+\frac3{\sqrt x}+\frac9{\sqrt x(\sqrt x-3)}\\&=\frac{\sqrt x(\sqrt x-3)+3(\sqrt x-3)+9}{\sqrt x(\sqrt x-3)}\\&=\frac{x}{\sqrt x(\sqrt x-3)}=\frac{\sqrt x}{\sqrt x-3}\quad(x>0).',r'$x\ge0$, $x\ne9$. Al regresar a $x$, $u^2+12u=x+6\sqrt x-27$, y $-27$ se absorbe en $C$. En $x=0$ la derivada lateral es $0$.')
e('A.28','x',r'\frac{\sqrt[3]x}{\sqrt[3]x-1}',r'Se toma $u=\sqrt[3]x-1$. Así, $\sqrt[3]x=u+1$, $x=(u+1)^3$ y $dx=3(u+1)^2du$.',r'I&=3\int\frac{(u+1)^3}{u}\,du\\&=3\int(u^2+3u+3+u^{-1})\,du\\&=u^3+\frac92u^2+9u+3\ln|u|+C.',r'x+\frac32x^{2/3}+3x^{1/3}+3\ln|x^{1/3}-1|',r'v&=\sqrt[3]x,\qquad \frac{dv}{dx}=\frac1{3v^2}\quad(x\ne0),\\F\prime(x)&=\left(3v^2+3v+3+\frac3{v-1}\right)\frac1{3v^2}\\&=\frac{(v^2+v+1)(v-1)+1}{v^2(v-1)}\\&=\frac{v^3}{v^2(v-1)}=\frac{\sqrt[3]x}{\sqrt[3]x-1}.',r'$x\ne1$. La constante $-11/2$ que aparece al expandir se absorbe en $C$. En $x=0$ el resultado es diferenciable y su derivada vale $0$; esto se comprueba con el cociente incremental, pues $F(x)-F(0)$ es de orden $x^{4/3}$.')
e('A.29',r'\theta',r'\frac{\cos\theta}{\sen\theta}',r'Se toma $u=\sen\theta$, $du=\cos\theta\,d\theta$.',r'I&=\int\frac{du}{u}=\ln|u|+C.',r'\ln|\sen\theta|',r'F\prime(\theta)&=\frac{\cos\theta}{\sen\theta}.',r'$\sen\theta\ne0$.')
e('A.30',r'\theta',r'\tan(5\theta)',r'Se escribe $\tan(5\theta)=\sen(5\theta)/\cos(5\theta)$. Se elige $u=\cos(5\theta)$, $du=-5\sen(5\theta)d\theta$.',r'I&=-\frac15\int\frac{du}{u}=-\frac15\ln|u|+C.',r'-\frac15\ln|\cos(5\theta)|',r'F\prime(\theta)&=-\frac15\frac{-5\sen(5\theta)}{\cos(5\theta)}=\tan(5\theta).',r'$\cos(5\theta)\ne0$.')
e('A.31','x',r'\csc(2x)',r'Primero $u=2x$, $dx=du/2$. Para integrar $\csc u$, se toma $w=\csc u-\cot u$; su derivada es $w\prime=-\csc u\cot u+\csc^2u=\csc u\,w$.',r'I&=\frac12\int\csc u\,du\\&=\frac12\int\frac{dw}{w}=\frac12\ln|w|+C.',r'\frac12\ln|\csc(2x)-\cot(2x)|',r'F\prime(x)&=\frac12\frac{-2\csc(2x)\cot(2x)+2\csc^2(2x)}{\csc(2x)-\cot(2x)}\\&=\frac{\csc(2x)[\csc(2x)-\cot(2x)]}{\csc(2x)-\cot(2x)}\\&=\csc(2x).',r'$\sen(2x)\ne0$. El argumento del logaritmo no es cero en ese dominio. También puede escribirse $\tfrac12\ln|\tan x|+C$.')
e('A.32','x',r'\sec\left(\frac x2\right)',r'Se toma $u=x/2$, $dx=2du$. Para integrar $\sec u$, sea $w=\sec u+\tan u$; entonces $dw=(\sec u\tan u+\sec^2u)du=\sec u\,w\,du$.',r'I&=2\int\sec u\,du=2\int\frac{dw}{w}=2\ln|w|+C.',r'2\ln\left|\sec\left(\frac x2\right)+\tan\left(\frac x2\right)\right|',r'q&=\frac x2,\\F\prime(x)&=2\frac{\tfrac12\sec q\tan q+\tfrac12\sec^2q}{\sec q+\tan q}\\&=\frac{\sec q(\tan q+\sec q)}{\sec q+\tan q}=\sec\left(\frac x2\right).',r'$\cos(x/2)\ne0$.')
e('A.33','t',r'\frac{\cos t}{1+\sen t}',r'Se toma $u=1+\sen t$, $du=\cos t\,dt$. El factor diferencial ya está en el numerador.',r'I&=\int\frac{du}{u}=\ln|u|+C.',r'\ln|1+\sen t|',r'F\prime(t)&=\frac{\cos t}{1+\sen t}.',r'$1+\sen t\ne0$.')
e('A.34','t',r'\frac{\csc^2t}{\cot t}',r'Se elige $u=\cot t$, $du=-\csc^2t\,dt$, así que $\csc^2t\,dt=-du$.',r'I&=-\int\frac{du}{u}=-\ln|u|+C.',r'-\ln|\cot t|',r'F\prime(t)&=-\frac{-\csc^2t}{\cot t}=\frac{\csc^2t}{\cot t}.',r'$\sen t\ne0$ y $\cos t\ne0$, para que $\csc t$ esté definida y $\cot t\ne0$.')
e('A.35','x',r'\frac{\sec x\tan x}{\sec x-1}',r'Sea $u=\sec x-1$; entonces $du=\sec x\tan x\,dx$.',r'I&=\int\frac{du}{u}=\ln|u|+C.',r'\ln|\sec x-1|',r'F\prime(x)&=\frac{\sec x\tan x}{\sec x-1}.',r'$\cos x\ne0$ y $\sec x\ne1$.')
e('A.36','t',r'(\sec t+\tan t)',r'Por linealidad se separan ambas funciones. La secante se integra como en A.32: $\ln|\sec t+\tan t|$. Para la tangente se toma $u=\cos t$ y $du=-\sen t\,dt$.',r'I&=\int\sec t\,dt+\int\frac{\sen t}{\cos t}\,dt\\&=\ln|\sec t+\tan t|-\int\frac{du}{u}\\&=\ln|\sec t+\tan t|-\ln|\cos t|+C.',r'\ln|\sec t+\tan t|-\ln|\cos t|',r'F\prime(t)&=\frac{\sec t\tan t+\sec^2t}{\sec t+\tan t}-\frac{-\sen t}{\cos t}\\&=\sec t+\tan t.',r'$\cos t\ne0$.')
parts.append(r'''
\section{Conclusiones}
La elección del método comienza con la forma del integrando. Los productos y cocientes de potencias se simplifican antes de integrar. En una sustitución, el diferencial determina el coeficiente exterior, mientras que los factores restantes deben expresarse en la nueva variable. En las fracciones impropias, la división polinómica separa una parte elemental y una fracción que suele conducir a un logaritmo.

Las comprobaciones muestran por qué no pueden omitirse los signos de un diferencial negativo ni los coeficientes de una función compuesta. En el problema de costo total, la integración produce una familia de funciones y el costo fijo selecciona una sola. Los dominios forman parte de la respuesta: una simplificación algebraica no autoriza a incluir puntos donde el integrando original no está definido.

\clearpage
\appendix
\section{Imágenes originales de la Evidencia 1}
Las imágenes siguientes proceden de \texttt{Evidencia-1-20-puntos.docx}. Se conserva la fuente completa para cotejar radicales, exponentes, numeración y los límites de lo visible.
\foreach \n in {1,...,4}{
  \begin{figure}[p]
    \centering
    \includegraphics[width=0.95\textwidth,height=0.80\textheight,keepaspectratio]{UANL/ingeniero-agronomo/calculo-integral/assets-calculo-integral/actividad-1-fuentes/image\n.png}
    \caption{Imagen original \n\ de la Evidencia 1 (Actividad 2).}
  \end{figure}
  \clearpage
}
\bibliography{UANL/ingeniero-agronomo/calculo-integral/calculo-integral}
''')
text='\n'.join(parts)
# Una igualdad entre dos formas de F no debe separar la constante de una de ellas.
text=text.replace(r'\frac1{\cos x}=\sec x+C.',r'\sec x+C.')
text=text.replace(r'-\frac1{\sen x}=-\csc x+C.',r'-\csc x+C.')
assert count==88,count
out.write_text(text,encoding='utf-8')
print(f'{count} ejercicios; {len(text.splitlines())} líneas; {out}')
