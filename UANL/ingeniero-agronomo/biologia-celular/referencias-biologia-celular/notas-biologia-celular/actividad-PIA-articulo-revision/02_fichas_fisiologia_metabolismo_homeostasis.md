# Ficha Conceptual 02: Fisiología Celular, Bioenergética y Homeostasis Osmótica

**Asignatura:** Biología Celular | **Actividad:** PIA (Artículo de Revisión)  
**Tema Central:** Mecanismos Fisiológicos y Procesos Metabólicos en Homeostasis Celular  

---

## 1. Biofísica del Potencial Hídrico y Turgencia Celular

La función fisiológica primordial de la célula oclusiva radica en modular la resistencia estomática ($r_s$) y el poro estomático mediante la variación reversible de su potencial hídrico ($\Psi_w$):

$$\Psi_w = \Psi_s + \Psi_p$$

- $\Psi_s$ (potencial osmótico o de solutos): Determinado por la concentración molar de osmolitos acumulados en el citosol y en la vacuola ($K^+$, $\text{Cl}^-$, $\text{NO}_3^-$, malato$^{2-}$ y sacarosa).
- $\Psi_p$ (potencial de presión o turgencia hidrostática): Fuerza mecánica que empuja contra la pared celular elástica. Al incrementarse de $0.5\ \text{MPa}$ a $3.0 - 5.0\ \text{MPa}$, deforma la pared delgada dorsal hacia el exterior y dilata el poro intercelular.

---

## 2. Fase de Apertura Estomática: Maquinaria de Transporte de Membrana

```
[Exterior celular / Apoplasto]
       |
       |  H+ (Bombeo activo primario por H+-ATPasa AHA1/2)  <-- Gasto de ATP
       v
[Membrana Plasmática Hyperpolarizada: Vm = -150 a -200 mV]
       ^
       |  K+ (Entrada electroforética pasiva por canales KAT1/KAT2)
       |  Cl- / NO3- (Co-transporte simporte 2H+/Anión)
       v
[Citosol (pH 7.2 - 7.5)]
       |
       +--> Síntesis citosólica de Malato2- vía PEP carboxilasa (PEPC)
       |
       v  Transporte activo secundario hacia el tonoplasto
[Vacuola Central (pH 5.0 - 5.5)]  --> Acumulación neta de 400 - 800 mM K+
```

### 2.1 Bombeo Primario de Protones
1. **Activación de la $H^+$-ATPasa:** La luz azul activa el fotoreceptor citosólico fototropina 1 y 2 (PHOT1/PHOT2), induciendo la fosforilación de un residuo de treonina en el extremo carboxilo terminal de la $H^+$-ATPasa de membrana (Thr-947 en *Arabidopsis*).
2. **Unión de proteína 14-3-3:** El residuo fosforilado recluta una proteína adaptadora 14-3-3, estabilizando el estado conformacional hiperactivo de la bomba.
3. **Hiperpolarización del potencial de membrana ($V_m$):** El bombeo masivo de $H^+$ hacia el apoplasto acidifica la pared celular ($\text{pH} \approx 4.5 - 5.0$) y desplaza el potencial de membrana a valores más negativos que el potencial de equilibrio de Nernst para el potasio ($E_K \approx -120\ \text{mV}$), alcanzando entre $-160\ \text{mV}$ y $-200\ \text{mV}$.

### 2.2 Flujo Masivo de Contraiones Osmolitos
- **Canales rectificadores entrantes de Potasio (KAT1 / KAT2 / AKT1):** La hiperpolarización abre la compuerta de activación de los canales de potasio dependientes de voltaje, induciendo un influjo neto de $K^+$ a favor de su gradiente electroquímico.
- **Influjo de Cloruro y Nitrato:** El gradiente de protones generado es aprovechado por transportadores de simporte anión/$H^+$ (CLCa y NRT1.5) para ingresar $\text{Cl}^-$ y $\text{NO}_3^-$ contra gradiente electroquímico.
- **Biosíntesis de Malato Citosólico:** El citosol neutraliza la carga positiva del $K^+$ sintetizando malato$^{2-}$:
  $$\text{Fosfoenolpiruvato (PEP)} + \text{HCO}_3^- \xrightarrow{\text{PEPC}} \text{Oxalacetato} + \text{P}_i$$
  $$\text{Oxalacetato} + \text{NADH} + \text{H}^+ \xrightarrow{\text{c-MDH}} \text{Malato}^{2-} + \text{NAD}^+$$
- **Secuestro Tonoplástico:** El transportador AtALMT9 introduce malato$^{2-}$ y $\text{Cl}^-$ al interior de la vacuola, mientras que antiportadores $NHX$ ($K^+/H^+$) y canales TPK concentran el potasio vacuolar hasta niveles de $400 - 800\ \text{mM}$.

### 2.3 Transición Diurna al Osmolito Sacarosa
- En las primeras horas de la mañana ($06:00 - 10:00\ \text{h}$), el influjo de $K^+$ y síntesis de malato dominan el balance osmótico.
- Hacia el mediodía y la tarde ($11:00 - 16:00\ \text{h}$), la concentración de potasio celular decae progresivamente y la turgencia se mantiene por acumulación osmótica de **sacarosa** sintetizada localmente y captada del apoplasto por transportadores SUC/SUT ($H^+$/sacarosa).

---

## 3. Fase de Cierre Estomático: Despolarización y Eflujo Iónico

1. **Apertura de canales de calcio ($Ca^{2+}$):** La señal de estrés hídrico mediada por Ácido Abscísico ($ABA$) activa canales de calcio dependientes de voltaje y canales permeables a calcio en membrana plasmática y tonoplasto, elevando $[Ca^{2+}]_{\text{cyt}}$ desde niveles basales ($50 - 100\ \text{nM}$) hasta micro molares ($1 - 2\ \mu\text{M}$).
2. **Despolarización y activación de canales aniónicos SLAC1 / ALMT12 (QUAC1):** Las proteínas cinasas dependientes de calcio (CDPK) y SnRK2 fosforilan y abren los canales aniónicos de salida lenta (SLAC1) y rápida (QUAC1/ALMT12). El eflujo de $\text{Cl}^-$ y malato despolariza la membrana plasmática hacia valores de $-40\ \text{mV}$ a $-30\ \text{mV}$.
3. **Eflujo masivo de $K^+$ por canales rectificadores salientes (GORK):** La despolarización sostenida abre el canal GORK (*Guard Cell Outward Rectifying $K^+$ channel*), expulsando potasio al apoplasto.
4. **Salida osmótica de agua:** El eflujo total de solutos eleva el $\Psi_s$ intracelular, provocando la salida termodinámica de agua a través de acuaporinas (PIP2), reduciendo la turgencia y sellando el poro estomático.

---

## 4. Comparativa con la Fisiología del Hepatocito Animal

| Proceso Fisiológico | Célula Oclusiva Vegetal | Hepatocito de Mamífero Doméstico |
|---|---|---|
| **Mecanismo impulsor primario** | $H^+$-ATPasa de membrana plasmática (bombeo electrogénico de $H^+$). | $\text{Na}^+/\text{K}^+$-ATPasa de membrana (antiporte electrogénico $3\text{Na}^+/2\text{K}^+$). |
| **Moneda de cotransporte secundario** | Fuerza protón-motriz ($\Delta\mu_{H^+}$). | Gradiente de sodio transmembranal ($\Delta\mu_{\text{Na}^+}$). |
| **Respuesta a hipoosmolaridad** | Incremento de turgencia hidrostática soportado por pared celular de celulosa. | Hinchamiento y activación de canales osmóticos reguladores (RVD: *Regulatory Volume Decrease*). |
| **Homeostasis energética** | Fotofosforilación plastídica + respiración mitocondrial aeróbica. | Fosforilación oxidativa mitocondrial + glucólisis y $\beta$-oxidación de ácidos grasos. |
| **Metabolismo de reserva** | Conversión diurna reversible de almidón $\leftrightarrow$ sacarosa/malato. | Biosíntesis y degradación de glucógeno mediante glucógeno sintasa y glucógeno fosforilasa. |
| **Destoxificación metabólica** | Conjugación vacuolar vía glutatión S-transferasas (GST) y secuestro en vacuola. | Fase I (citocromo P450 monooxigenasas) y Fase II (glucuronidación, sulfatación) en REL. |

