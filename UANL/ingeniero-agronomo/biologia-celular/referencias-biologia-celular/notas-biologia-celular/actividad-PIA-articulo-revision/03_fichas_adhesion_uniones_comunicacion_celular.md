# Ficha Conceptual 03: Adhesión Intercelular, Matriz Extracelular y Señalización Molecular

**Asignatura:** Biología Celular | **Actividad:** PIA (Artículo de Revisión)  
**Tema Central:** Mecanismos Moleculares de Adhesión, Uniones y Vías de Transducción de Señales  

---

## 1. Ontogenia, Linaje Celular y Mecánica de la Pared Extracelular

### 1.1 Señalización y Cascada Transcripcional del Linaje Estomático
En las plantas vasculares, la especificación de las células oclusivas ocurre en la protodermis foliar mediante divisiones asimétricas y un circuito riguroso de factores de transcripción de hélice-bucle-hélice básica (bHLH):

```
Célula Protodérmica
       |
       v  [SPCH (SPEECHLESS) + SCRM/ICE1]  <-- Regulado negativamente por YODA (MAPK)
Célula Madre Meristemoide (MMC)
       |  (División asimétrica)
       v
Meristemoide (M) + Célula Adyacente (SLGC)
       |
       v  [MUTE + SCRM]
Célula Madre de Guarda (GMC)
       |  (División simétrica única)
       v  [FAMA + FLP (FOUR LIPS)]
Par de Células Oclusivas Inmaduras
       |  (Depósito de calosa y remodelación de pared)
       v
Estoma Maduro Simplásticamente Aislado
```

- **Módulo receptor LRR-RLK / Péptidos EPF:** La densidad y el patrón espacial ("regla de una célula de distancia") están controlados por receptores tipo quinasa ricos en repeticiones de leucina (ERECTA, ERL1, ERL2 y el co-receptor TMM) activados por los ligandos peptídicos secretados EPF1 y EPF2. La unión ligando-receptor activa la cascada MAP cinasa (MAPKKK YODA $\rightarrow$ MKK4/5 $\rightarrow$ MPK3/6), la cual fosforila e inactiva a SPEECHLESS para evitar la formación de estomas contiguos.

### 1.2 Aislamiento Simplástico y Anclaje Polar a la Lámina Media
- **Oclusión de plasmodesmos:** Durante la transición final guiada por FAMA, los plasmodesmos primarios se sellan irreversiblemente mediante síntesis local de callosa ($\beta$-1,3-glucano) catalizada por calosa sintasas (GSL), seguida de degradación de la continuidad citoplasmática. Esto previene la fuga osmótica pasiva hacia el simplasto adyacente.
- **Pectinas polares y puntos de pivote mecánico:** En los dos polos donde las dos células oclusivas permanecen unidas, la lámina media es rica en homogalacturonanos des-metilesterificados unidos por puentes de calcio ($Ca^{2+}$-pectatos). Esta rigidez polar crea pivotes estables que convierten el alargamiento longitudinal turgente en un arqueamiento centrífugo que abre el ostiolo.

---

## 2. Vías Moleculares de Transducción de Señales en Células Oclusivas

### 2.1 Vía Canónica del Ácido Abscísico (ABA)
El cierre estomático en respuesta al déficit hídrico edáfico y ambiental es gobernado por el módulo tripartito soluble:

$$\text{Receptores PYR/PYL/RCAR} \quad \longleftrightarrow \quad \text{Fosfatasas PP2C (ABI1, ABI2, HAB1)} \quad \longleftrightarrow \quad \text{Proteína Cinasa SnRK2.6 (OST1)}$$

```
[Ausencia de Estrés / Sin ABA]
PP2C (Activa) -----(Inhibición por desfosforilación)-----> SnRK2.6/OST1 (Inactiva)
--> Canales aniónicos SLAC1 apagados; H+-ATPasa activa (Estoma Abierto)

[Presencia de Estrés Hídrico / ABA Elevado]
ABA + PYR/PYL/RCAR  ===> Complejo ternario [ABA-PYL-PP2C]
                            |
                            v  (Inhibición estérica del sitio catalítico de PP2C)
                     SnRK2.6/OST1 liberada
                            |
                            v  (Autofosforilación en Ser-175)
                     SnRK2.6/OST1 Hiperactiva
                            |
        +-------------------+-------------------+
        |                                       |
        v                                       v
Fosforilación y Activación de          Fosforilación e Inhibición de
Canales SLAC1 y ALMT12                 H+-ATPasa AHA1/2 y Canales KAT1
        |                                       |
        v                                       v
Eflujo masivo de Cl-, NO3-, Malato     Cese de bombeo de H+ e influjo de K+
        |                                       |
        +-------------------+-------------------+
                            |
                            v
Despolarización de membrana (-30 mV) ==> Apertura de canal de K+ saliente (GORK)
                            |
                            v
Pérdida de turgencia y Cierre Estomático Rápido
```

### 2.2 Transducción de Luz Azul por Fototropinas
- **Receptores PHOT1 y PHOT2:** Contienen dominios flavoproteicos LOV1 y LOV2 que unen flavín mononucleótido (FMN). La luz azul ($400 - 500\ \text{nm}$) induce aductos cisteinil-flavinilo que activan el dominio quinasa serina/treonina.
- **Señalización downstream:** Fosforilación de la fosfatasa de serina/treonina PP1 y BLUS1 (*Blue Light Signaling 1*), estimulando la fosforilación terminal de la $H^+$-ATPasa (Thr-947) y el anclaje de la proteína 14-3-3.

---

## 3. Complejos de Unión y Señalización en el Modelo Animal (Hepatocito)

### 3.1 Uniones Ocluyentes, de Adhesión y Comunicantes en el Tejido Hepático

```
[Luz del Canalículo Biliar]
==============================================  <-- Membrana Apical
  [Uniones Estrechas / Tight Junctions]       <-- Claudina-1, Claudina-3, Ocludina, ZO-1/ZO-2
----------------------------------------------      (Sellado paracelular a sales biliares)
  [Uniones Adherentes / Zonula Adherens]      <-- E-Cadherina acoplada a Actina vía Cateninas
----------------------------------------------
  [Desmosomas / Macula Adherens]              <-- Desmogleína-2, Desmocolina-2 y Desmoplaquina
----------------------------------------------      (Anclaje a citoesqueleto de Citoqueratinas)
  [Uniones Gap / Comunicantes]                <-- Conexones formados por Conexina-32 y Conexina-26
==============================================      (Paso directo de Ca2+, IP3, glucosa < 1.2 kDa)
[Espacio de Disse y Membrana Sinusoidal Basolateral]
  [Hemidesmosomas e Integrinas alpha1/beta1]  <-- Anclaje a Matriz Extracelular (Colágeno IV, Laminina)
```

### 3.2 Cascada de Señalización de Insulina vs. Glucagón en Homeostasis Glucémica
1. **Señalización por Insulina (Receptor Tirosina Cinasa - RTK):**
   - Unión de insulina a las subunidades $\alpha$ extracelulares $\rightarrow$ autofosforilación trans de las subunidades $\beta$ citosólicas en residuos de tirosina.
   - Reclutamiento y fosforilación de sustratos del receptor de insulina (IRS-1 e IRS-2).
   - Activación de Fosfatidilinositol 3-cinasa (PI3K) $\rightarrow$ conversión de $\text{PIP}_2$ en $\text{PIP}_3$.
   - Reclutamiento de PDK1 y activación por fosforilación de Akt / Proteína Cinasa B (PKB).
   - Akt fosforila e inhibe a la Glucógeno Sintasa Cinasa 3 ($\text{GSK3}\beta$), activando por desfosforilación a la glucógeno sintasa para almacenar glucógeno en el citosol.
2. **Señalización por Glucagón (Receptor Acoplado a Proteína G - GPCR):**
   - Unión de glucagón al receptor acoplado a proteína $G\alpha_s \rightarrow$ intercambio de GDP por GTP.
   - Activación de adenilato ciclasa transmembranal $\rightarrow$ producción de AMP cíclico (AMPc).
   - Activación de Proteína Cinasa A (PKA) $\rightarrow$ fosforilación de fosforilasa cinasa $\rightarrow$ activación de glucógeno fosforilasa, liberando glucosa-1-fosfato para sostener la glucemia en sangre.

