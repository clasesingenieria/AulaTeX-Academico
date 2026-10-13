 <!-- ======================= Descripción de la actividad ================
Cada programa deberá ser entregado en la actividad programada en Teams como "Actividad fundamental 1"
Se deberán entregar 7 programas (.psc) Generados por PSEINT
Además de esto, deberán entregar un PDF con todos los diagramas, pseudocodigos y ejecuciones de sus programas especificando cual programa es cada uno.

Ejemplo:
Programa 1:
*Foto de pseudocódigo (Screenshot)
*Foto de diagrama (Screenshot)
*Foto de la ejecución del programa (Screenshot)
Programa 2:
*Foto de pseudocodigo (Screenshot)
*Foto de diagrama (Screenshot)
*Foto de la ejecución del programa (Screenshot)
Así con los 7 programas
RESUMEN: se entregarán:
7 archivos .psc (no comprimidos, si se entregan comprimidos se bajarán puntos)
1 PDF (no .Docx ni .Pptx)
||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Programa 1: Suma de dos números y mostrar el resultado
Programa 2: Suma, Resta, Multiplicación y división de dos números (mostrar los 4 resultados)
Programa 3: Programa el cual calcule la energía potencial de un cuerpo en caída libre. (Epot = mgh)

Programa 4: Programa Que calcule e imprima el volumen de una esfera vol $=4 / 3 \Pi r^3$
Programa 5: La compañía de la luz desea generar el recibo de un cliente a partir de los siguientes datos:
Nombre del cliente
Consumo en kilowatts
Tarifa del kilowatt.
El recibo solo deberá contener el nombre y pago del cliente.
Programa 6: Una persona compró un terreno en un país. La extensión del terreno está especificada en acres. Introducir como dato la extensión del terreno en acres, calcular e imprimir la extensión del mismo en hectáreas.
- Un acre $=4047 \mathrm{~m} 2$.
- Una hectárea $=10000 \mathrm{~m} 2$.

Programa 7: Introducir como datos los valores de la longitud y el peso de un objeto expresado en pies y libras, imprimir los datos de este objeto pero expresado en metros y kilogramos.
- Un pie $=0.3048$ Mts.
- Una libra $=0.45359 \mathrm{Kgs}$.

 ======================= Ejemplos de pseudocódigo con Pseint =======================
// este es el ejemplo más simple de esta ayuda, 
// toma dos numeros, los suma y muestra el resultado


Algoritmo Suma


// para cargar un dato, se le muestra un mensaje al usuario
// con la instrucción Escribir, y luego se lee el dato en 
// una variable (A para el primero, B para el segundo) con 
// la instrucción Leer

Escribir "Ingrese el primer numero:"
Leer A

Escribir "Ingrese el segundo numero:"
Leer B


// ahora se calcula la suma y se guarda el resultado en la
// variable C mediante la asignación (<-)

C <- A+B


// finalmente, se muestra el resultado, precedido de un 
// mensaje para avisar al usuario, todo en una sola
// instrucción Escribir

Escribir "El resultado es: ",C

FinAlgoritmo

// Este ejemplo muestra el uso de expresiones, operadores y funciones matematicas

Algoritmo Matematicas


EligeSalir<-Falso
Escribir 'Ingresar un número:'
Leer N
Repetir
Escribir ' '
Escribir 'Presione una tecla para continuar'
Esperar Tecla
Limpiar Pantalla
Escribir 'Elija una opción:'
Escribir '  1 - Seno, coseno, arcotangente'
Escribir '  2 - Lograritmo natural, función exponencial'
Escribir '  3 - Truncar, redondear'
Escribir '  4 - Raíz cuadrada'
Escribir '  5 - Valor absoluto'
Escribir '  6 - Separar parte entera y decimal'
Escribir '  7 - Hallar factorial'
Escribir '  8 - Averiguar si es primo'
Escribir '  9 - Ingresar otro número'
Escribir '  0 - Salir'
Escribir ' '
Leer eleccion
Segun eleccion Hacer
1: 
Escribir 'Seno:',Sen(N)
Escribir 'Coseno:',Cos(N)
Escribir 'Arcotangente:',Atan(N)
2: 
Si N<=0
Entonces Escribir 'El numero debe ser mayor a cero!'
SiNo
Escribir 'Logaritmo natural: ',ln(N)
Escribir 'Función exponencial: ',exp(N)
FinSi
3: 
Escribir 'Truncar: ',trunc(N)
Escribir 'Redondear: ',redon(N)
4: Escribir 'Raiz Cuad.: ',rc(N)
5: Escribir 'Valor Abs.: ',abs(N)
6: 
Escribir 'Parte Entera: ',Trunc(n)
Escribir 'Parte Decimal: ',n-Trunc(n)
7: 
Si N<>Trunc(N)
Entonces
Escribir 'El numero debe ser entero!'
SiNo
Si abs(N)>50
Entonces Escribir 'Resultado muy grande!'
SiNo
r<-1; f<-1
Mientras f<=abs(N) Hacer
Si N<0 
Entonces r<-(-f)*r
SiNo
r<-f*r
FinSi
f<-f+1
FinMientras
Escribir 'Factorial:',r
FinSi
FinSi
8: 
Si N<>Trunc(N) Entonces
Escribir 'El numero debe ser entero!'
SiNo
Si N<0  entonces 
Nu<-N*(-1)
SiNo
Nu<-N
FinSi
Si N mod 2 = 0 Entonces 
Escribir 'Numero Primo:',Nu=2
Si Nu<>2 Entonces
Escribir N,'=2x',N/2
FinSi
SiNo
EsPrimo<-Nu<>1 
Nu<-RC(Nu)
Divisor<-3
Mientras Divisor<=Raiz(Nu) & EsPrimo Hacer
Si N mod Divisor = 0 Entonces 
EsPrimo<-Falso
Sino
Divisor<-Divisor+2
FinSi
FinMientras
Escribir 'Numero primo:',EsPrimo
Si N>1 & ~ EsPrimo Entonces 
Escribir N,'=',Divisor,'x',N/Divisor
FinSi
FinSi
FinSi
9:
Escribir 'Ingrese un número:'
Leer N
0: EligeSalir<-Verdadero
De Otro Modo:
Escribir 'eleccionción  no válida!'
FinSegun
Hasta que EligeSalir
FinAlgoritmo


 ======== Ejemplo de insertar bloque de código pseudocódigo en el documento =======================
\begin{sourcecode}{pseudocodecolor}{Algoritmo con fondo de color.}
	input: int N, int D
	output: int
	begin
	res $\gets$ 0
	while N $\geq$ D 
	N $\gets$ N - D
	res $\gets$ res + 1      
	end
	return res
	end    
\end{sourcecode} -->

# Suma de dos números

El programa solicita al usuario ingresar dos números, realiza la suma de ambos y muestra el resultado en pantalla. El pseudocódigo, diagrama de flujo y ejecución se presentan a continuación.

## Pseudocódigo

<!-- Blóque de pseudocódigo -->

```pseudocode
Algoritmo SumaDosNumeros
    Escribir "Ingrese el primer número:"
    // Escribe el primer número en pantalla y lo lee desde el teclado
    Leer numero1
    Escribir "Ingrese el segundo número:"
    // Escribe el segundo número en pantalla y lo lee desde el teclado
    Leer numero2
    // Realiza la suma de los dos números y almacena el resultado en la variable suma
    suma <- numero1 + numero2
    // Escribe el resultado de la suma en pantalla
    Escribir "El resultado de la suma es: ", suma
FinAlgoritmo
```

## Diagrama de flujo

![Diagrama de flujo para la suma de dos números](https://cdn.mathpix.com/snip/images/wVTA6MDTxNuGsL_CoY_f9eVqoQwKmprMQ0_UBUYD8Mc.original.fullsize.png)

## Ejecución

![Ejecución del programa para la suma de dos números](https://cdn.mathpix.com/snip/images/QRmCLQYLN09bKG1r-KeCjKUBVgviZE3uglSzaakOGUE.original.fullsize.png)

# Suma, Resta, Multiplicación y División de dos números

El programa solicita al usuario ingresar dos números, realiza las operaciones de suma, resta, multiplicación y división, y muestra los resultados en pantalla. El pseudocódigo, diagrama de flujo y ejecución se presentan a continuación.

## Pseudocódigo

```pseudocode
Algoritmo OperacionesBasicas
    Escribir "Ingrese el primer número:"
    // Lee el primer valor ingresado por el usuario
    Leer numero1
    Escribir "Ingrese el segundo número:"
    // Lee el segundo valor ingresado por el usuario
    Leer numero2
    // Calcula la suma de ambos números
    suma <- numero1 + numero2
    // Calcula la resta del primer número menos el segundo
    resta <- numero1 - numero2
    // Calcula la multiplicación de ambos números
    multiplicacion <- numero1 * numero2
    // Valida que el divisor sea diferente de cero antes de dividir
    Si numero2 <> 0 Entonces
        // Realiza la división cuando es válida
        division <- numero1 / numero2
    Sino
        // Muestra un mensaje de error si el divisor es cero
        Escribir "No se puede dividir por cero"
    FinSi
    // Muestra todos los resultados calculados
    Escribir "Suma: ", suma
    Escribir "Resta: ", resta
    Escribir "Multiplicación: ", multiplicacion
    Escribir "División: ", division
FinAlgoritmo
```

## Diagrama de flujo

![Diagrama de flujo para operaciones básicas](https://cdn.mathpix.com/snip/images/VlDw_pMjVS0DTo9f96Sqe7TrbfeD021Rf_F-i0c3AG8.original.fullsize.png)

## Ejecución

![Ejecución del programa para operaciones básicas](https://cdn.mathpix.com/snip/images/g4BahtJicLW6VnQD7Phe7xrrqIutu_A_lt0i_BFeH5c.original.fullsize.png)

# Energía potencial de un cuerpo en caída libre

El programa solicita al usuario ingresar la masa, la altura y la gravedad, calcula la energía potencial utilizando la fórmula $Epot = mgh$ y muestra el resultado en pantalla. El pseudocódigo, diagrama de flujo y ejecución se presentan a continuación.

## Pseudocódigo

```pseudocode
Algoritmo calculoEnergiaPotencial
    Escribir "Ingrese la masa del objeto (en kg):"
    // Lee la masa del objeto ingresada por el usuario
    Leer masa
    Escribir "Ingrese la altura desde la que cae el objeto (en metros):"
    // Lee la altura desde la que cae el objeto ingresada por el usuario
    Leer altura
    Escribir "Ingrese la gravedad (en m/s^2):"
    // Lee el valor de la gravedad ingresado por el usuario
    Leer gravedad
    // Calcula la energía potencial utilizando la fórmula Epot = mgh
    energiaPotencial <- masa * gravedad * altura
    // Muestra el resultado de la energía potencial calculada
    Escribir "La energía potencial del objeto es: ", energiaPotencial, " Joules"
FinAlgoritmo
```

## Diagrama de flujo

![Diagrama de flujo para energía potencial](https://cdn.mathpix.com/snip/images/6_rVw212epf2vyUVNSIDrqbcmMXGcnvgFx9RHssXgCg.original.fullsize.png)

## Ejecución

![Ejecución del programa para energía potencial](https://cdn.mathpix.com/snip/images/ZEAn9IWjIodIKlQt6pWWjhDDPMShedOIDWDW5c1VS5A.original.fullsize.png)

# Volumen de una esfera

El programa solicita al usuario ingresar el radio de una esfera, calcula el volumen utilizando la fórmula $vol = \frac{4}{3} \pi r^3$ y muestra el resultado en pantalla. El pseudocódigo, diagrama de flujo y ejecución se presentan a continuación.

## Pseudocódigo

```pseudocode
Algoritmo calculoVolumenEsfera
    Escribir "Ingrese el radio de la esfera (en metros):"
    // Lee el radio de la esfera ingresado por el usuario
    Leer radio
    // Calcula el volumen de la esfera utilizando la fórmula vol = (4/3) * π * r^3
    volumen <- (4/3) * 3.14159 * (radio^3)
    // Muestra el resultado del volumen calculado
    Escribir "El volumen de la esfera es: ", volumen, " metros cúbicos"
FinAlgoritmo
```

## Diagrama de flujo

![Diagrama de flujo para volumen de una esfera](https://cdn.mathpix.com/snip/images/0IH7toh9jWq0SrzXVHQ4bdC4FBfhl3t72cQ7H-4tj_U.original.fullsize.png)

## Ejecución

![Ejecución del programa para volumen de una esfera](https://cdn.mathpix.com/snip/images/-57AH2iXf95ibZNPnJ48dlz0lr8et5lp83lDMfH6MaU.original.fullsize.png)

# Recibo de la compañía de la luz

El programa solicita al usuario ingresar el nombre del cliente, el consumo en kilowatts y la tarifa del kilowatt, calcula el pago total y muestra el recibo con el nombre del cliente y el pago. El pseudocódigo, diagrama de flujo y ejecución se presentan a continuación.

## Pseudocódigo

```pseudocode
Algoritmo generarReciboLuz
    Escribir "Ingrese el nombre del cliente:"
    // Lee el nombre del cliente ingresado por el usuario
    Leer nombreCliente
    Escribir "Ingrese el consumo en kilowatts:"
    // Lee el consumo en kilowatts ingresado por el usuario
    Leer consumoKilowatts
    Escribir "Ingrese la tarifa del kilowatt:"
    // Lee la tarifa del kilowatt ingresada por el usuario
    Leer tarifaKilowatt
    // Calcula el pago total multiplicando el consumo por la tarifa
    pagoTotal <- consumoKilowatts * tarifaKilowatt
    // Muestra el recibo con el nombre del cliente y el pago total
    Escribir "Recibo de la compañía de la luz"
    Escribir "Cliente: ", nombreCliente
    Escribir "Pago total: $", pagoTotal
FinAlgoritmo
```

## Diagrama de flujo

![Diagrama de flujo para recibo de la luz](https://cdn.mathpix.com/snip/images/VPCyOpBiWVDx3o0B4pRpBT5xGlO0iJVtVdFnh1Iecbk.original.fullsize.png)

## Ejecución

![Ejecución del programa para recibo de la luz](https://cdn.mathpix.com/snip/images/0X7n2SguGBr7fJO7MA9w6AawY7YvsEjsei3EmUrH7-0.original.fullsize.png)

# Extensión de un terreno en hectáreas

El programa solicita al usuario ingresar la extensión del terreno en acres, realiza la conversión a hectáreas utilizando la equivalencia dada, y muestra el resultado en pantalla. El pseudocódigo, diagrama de flujo y ejecución se presentan a continuación.

## Pseudocódigo

```pseudocode
Algoritmo conversionAcresHectareas
    Escribir "Ingrese la extensión del terreno en acres:"
    // Lee la extensión del terreno en acres ingresada por el usuario
    Leer extensionAcres
    // Convierte la extensión de acres a hectáreas utilizando la equivalencia 1 acre = 0.4047 hectáreas
    extensionHectareas <- extensionAcres * 0.4047
    // Muestra el resultado de la conversión en pantalla
    Escribir "La extensión del terreno en hectáreas es: ", extensionHectareas, " ha"
FinAlgoritmo
```

## Diagrama de flujo

![Diagrama de flujo para conversión de acres a hectáreas](https://cdn.mathpix.com/snip/images/TlppQIz-eW4O78lhtq5lW5ghqqjOnd57OmoTqxjdPgU.original.fullsize.png)

## Ejecución

![Ejecución del programa para conversión de acres a hectáreas](https://cdn.mathpix.com/snip/images/6ixxdOeiDU_dlse8QuXMQ8Es0o8gXuFspW5Ug76Kx04.original.fullsize.png)

# Conversión de pies y libras a metros y kilogramos

El programa solicita al usuario ingresar la longitud en pies y el peso en libras, realiza la conversión a metros y kilogramos utilizando las equivalencias dadas, y muestra los resultados en pantalla. El pseudocódigo, diagrama de flujo y ejecución se presentan a continuación.

## Pseudocódigo

```pseudocode
Algoritmo conversionPiesLibras
    Escribir "Ingrese la longitud en pies:"
    // Lee la longitud en pies ingresada por el usuario
    Leer longitudPies
    Escribir "Ingrese el peso en libras:"
    // Lee el peso en libras ingresado por el usuario
    Leer pesoLibras
    // Convierte la longitud de pies a metros utilizando la equivalencia 1 pie = 0.3048 metros
    longitudMetros <- longitudPies * 0.3048
    // Convierte el peso de libras a kilogramos utilizando la equivalencia 1 libra = 0.45359 kilogramos
    pesoKilogramos <- pesoLibras * 0.45359
    // Muestra los resultados de la conversión en pantalla
    Escribir "La longitud en metros es: ", longitudMetros, " m"
    Escribir "El peso en kilogramos es: ", pesoKilogramos, " kg"
FinAlgoritmo
```

## Diagrama de flujo

![Diagrama de flujo para conversión de pies y libras](https://cdn.mathpix.com/snip/images/WQhtTmkyyyRaY4ecjoMBHaPLd7plI45D--nv3TSS3Tg.original.fullsize.png)

## Ejecución

![Ejecución del programa para conversión de pies y libras](https://cdn.mathpix.com/snip/images/6TEUI5N0AJjGVBWvXW2EhrcY4HKP0jGRqrtdIqXDXa4.original.fullsize.png)