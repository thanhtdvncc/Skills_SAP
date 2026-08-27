# Cómo modelar una placa base en SAP2000 — procedimiento

> **Qué es esto.** El registro paso a paso de una placa base modelada a mano, con la
> comprobación de cada paso. Se escribe *mientras* se modela, no después.
>
> **Para qué.** Es el **contrato** del generador: lo que `backend_placabase.py` tiene que
> recibir, lo que tiene que construir y —sobre todo— **lo que tiene que comprobar antes de
> decir que salió bien**. Hoy ese backend devuelve `success: True` de forma incondicional.
>
> **La regla que gobierna el procedimiento:** un paso, una auditoría. Si un paso no cierra,
> se para ahí. Nunca `except: pass`.
>
> **El generador que implementa este contrato es `build_placabase_COL_PLT_R.py`**, acá al
> lado. Reconstruye el modelo entero en **21,6 s** con **167 auditorías** y se corre así:
>
> ```powershell
> $env:PYTHONPATH = "C:\Proyectos_Python\Struct_Harness\_codigo"
> python -m harness.correr_generador `
>     C:\Proyectos_Python\Skills_SAP\scripts\placabase\build_placabase_COL_PLT_R.py
> ```

---

## El caso que se está modelando

Base de columna de pórtico del taller de neumáticos de El Pachón, `COL_PLT_R`.
Prediseño en `Struct_Harness/proyectos/2026-bechtel-pachon-taller-neumaticos/40_registro/memos/2026-08-27-predim-placa-y-pedestal.md`.

| | |
|---|---|
| Columna | doble T soldada **1.500 × 16 × 520 × 32** |
| Placa | **2.800 × 1.120 × 50 mm** |
| Cartelas | en `x` = **0, ±280, ±560** — vanos de **280 mm** · `t` = 25 mm |
| Silla | **`HA` = 500 mm** · chapa superior **`e1` = 50 mm**, continua del ala al borde |
| Continuidad | atiesador **32 mm** a `z` = 500, de ala a ala, partido por el alma |
| Pernos | **4 M64 F1554 G36 por fila, UNA fila por lado** en `x` = ±140, ±420 · `y` = **±1.250** |
| Demanda | `M_u` = **7.271,5** kN·m · `P_u` = **+326,5** kN — nudo 26 de `v24_POLVO_2026-08-26` |
| Uso del perno | **0,826** · `T` de fila = 2.653,0 kN |
| Planta acotada | `placa_base_v24_planta.svg` — ⚠️ **superado**, dibuja `L` = 3.200 y las cartelas sobre las líneas de perno |

> **El largo pasó de 3.200 a 2.800 mm el 2026-08-27**, decidido por el ingeniero sobre la
> hoja `predim_placa_pedestal.py`. Sube el uso del perno de 0,706 a 0,826 y ahorra 400 mm
> de pedestal en la dirección del momento. Arrastra la fila de pernos de ±1.450 a ±1.250 y
> el borde de ±1.600 a ±1.400.
>
> **La demanda también cambió, y no por la placa:** la pareja `M`–`N` ya no se cruza entre
> dos combinaciones. Está **medida** en el nudo 26, que gobierna sobre el 21 porque trae un
> tercio del axial con casi el mismo momento. Con gran excentricidad el axial es el que
> decide.

### Para qué sirve el modelo — y qué decide

**Es el contraste del cálculo a mano, no su reemplazo.** El lápiz dio `t_p` = 50 mm suponiendo
el panel entre atiesadores **empotrado** en los dos bordes (`M = f_p·b²/12`). El FE dice si esa
condición de borde era razonable o si el momento real es mayor.

Es lo mismo que `placabase_fe/verificar_placabase_fe.py` hace con el caso de la rev. 4, donde
encuentra que el β = 0,080 adoptado **subestima** el momento y la chapa de 35 mm queda al 0,99
en vez de con margen.

**Consecuencias sobre el modelo, que no son opcionales:**

1. Los **atiesadores hay que modelarlos fielmente** — son la condición de borde que se está
   verificando. Si no están, el modelo no responde la pregunta.
2. Hacen falta **resortes bajo la placa**. Apoyarla rígida da un momento equivocado.
3. El **contorno de placa** tiene que existir como geometría. No alcanza con anillos alrededor
   de los pernos.

Los tres puntos son justamente lo que el backend actual **no** construye.

---

## Sistema de unidades y ejes

| | |
|---|---|
| **Unidades** | **kN-m-C** (código 6). Todo en metros: la placa es 3,2 × 1,1 × 0,05 |
| **X** | ancho de placa, 1,100 m — es `B_col` del backend |
| **Y** | largo de placa, 3,200 m — es `H_col` del backend, la dirección del canto de columna |
| **Z** | vertical, **cara superior de la placa en Z = 0** |
| Archivo | `Struct_Harness/_run/placabase_COL_PLT_R_2026-08-27.sdb` |

> **Por qué kN-m-C y no N-mm.** Es el sistema del proyecto (`_codigo/sap/lectura.py` asierta
> el código 6). Mezclar sistemas entre el modelo de conjunto y el de detalle es la clase 1:
> no lanza excepción, devuelve otro número.

> **Por qué `_run/`.** Es scratch gitignorado, y está bien que lo sea: cuando el procedimiento
> esté probado, **el modelo se regenera desde el script**. La fuente de verdad es el generador,
> no el `.sdb` (invariante 4 de Struct_Harness).

---

## Paso 0 · Unidades, modelo vacío y archivo con nombre

**Qué se hace**

1. Comprobar que el modelo está **realmente vacío** antes de escribir nada.
2. Fijar unidades en kN-m-C.
3. Grabar con nombre.
4. Comprobar que las unidades **sobreviven al `Save`**.

**Por qué así**

- Empezar sobre un modelo que uno *cree* vacío y no lo está deja objetos huérfanos que después
  aparecen en las auditorías de conteo y no se explican.
- El `Save` puede cambiar el estado del modelo. En Struct_Harness la regla es dura:
  **`File.Save` desbloquea el modelo y descarta los resultados, y las tablas devuelven CEROS,
  no vacío.** Acá el modelo está vacío y no hay resultados que perder, pero **desde el paso 7
  en adelante esa regla manda**: no grabar después de analizar sin re-comprobar
  `GetModelIsLocked()`.

**Auditoría — medido el 2026-08-27**

| Comprobación | Resultado |
|---|---|
| Puntos · frames · áreas previos | **0 · 0 · 0** ✅ |
| Unidades antes | 12 (Ton-m-C, el default de SAP) |
| Unidades después | **6** ✅ |
| `File.Save` código de retorno | **0** ✅ |
| `GetModelFilename` | `…\_run\placabase_COL_PLT_R_2026-08-27.sdb` ✅ |
| Unidades tras el `Save` | **6** — no las tocó ✅ |
| `GetModelIsLocked` | `False` (correcto: no hay análisis) |

**Lo que el contrato hereda de este paso**

```
precondicion:  PointObj.Count() == FrameObj.Count() == AreaObj.Count() == 0
postcondicion: GetPresentUnits() == 6  y  GetModelFilename() termina en el nombre pedido
```

Ninguna de las dos existe hoy en `backend_placabase.py`: arranca escribiendo sobre lo que haya
y nunca declara unidades.

---

## Paso 1 · Materiales y propiedades de shell

| Material | `F_y` | `F_u` | Para |
|---|---:|---:|---|
| `A36` | 250 MPa `⁉️` | 400 `⁉️` | placa, cartelas, silla |
| `ACERO_COL` | **344,74 MPa** | 448,16 `⁉️` | alas y alma del stub |
| `F1554_G36` | 250 `⁉️` | 400 `⁉️` | pernos |

`E` = 200 GPa · `ν` = 0,30 · `γ` = 77,178 kN/m³ en los tres.

| Shell | `t` | Material |
|---|---:|---|
| `PLACA` | 50 mm | A36 |
| `ALA` | 32 | ACERO_COL |
| `ALMA` | 16 | ACERO_COL |
| `ATIESADOR` | **25** | A36 |
| `SILLA` | **25** | A36 |

Más `BOLT_M64`, sección circular ø64 sobre `F1554_G36`.

**Dos decisiones, con su razón**

1. **`ShellType` = 2, Shell-THICK, en los cinco.** No es cosmético: la placa de 50 mm salva
   280 mm entre cartelas, o sea **luz/espesor = 5,6**. Con *thin shell* se pierde la
   deformación por corte y el momento sale equivocado justo en el número que el modelo viene
   a verificar.
2. **`eFy` = `Fy` y `eFu` = `Fu`.** Sin sobrerresistencia: el modelo es elástico, no de
   capacidad. La capacidad ya está adentro de la demanda de 7.796,3 kN·m.

**Auditoría** — cada propiedad **releída** con `GetOSteel_1`, `GetMPIsotropic`, `GetShell_1` y
`GetCircle`, y comparada contra lo pedido. Las 9 comparaciones cierran.

> **Lo que destapó el conteo:** `PropMaterial.Count()` devuelve **6** habiendo definido 3. El
> modelo en blanco de SAP trae tres por defecto. No molesta, pero **un contrato que asertara
> «3 materiales» fallaría sin razón**: los conteos absolutos sobre propiedades no sirven, hay
> que comprobar por nombre.

---

## Paso 2 · Contorno de placa — lo que el backend actual no construye

Los 2.800 × 1.120 se construyen como **grilla explícita de 648 áreas**, no como un área grande
dividida después.

**Por qué así.** Los nudos tienen que caer exactamente donde después apoyan el perno y la
cartela. Construir un área y confiar en que `EditArea.Divide` ponga el nudo donde hace falta es
lo que obliga a los índices mágicos del `A_outer_link` (`[N][10]`, `[2*N-1][14]`…). Con la
grilla, la posición del nudo es un dato de entrada, no un resultado.

**Líneas de control declaradas de antemano**

| Eje | Estaciones | Qué apoya ahí |
|---|---|---|
| `X` | ±560 · ±420 · ±280 · ±260 · ±140 · 0 | borde y **cartela** · perno · **cartela** · ala · perno · alma y **cartela** |
| `Y` | ±1400 · ±1250 · ±734 · 0 | borde · fila de pernos · plano medio de ala · centro |

Elementos de 20 a 82 mm. Los de 20 salen del par `±260`/`±280`: **el ala termina en 260 y
la cartela arranca en 280**, y las dos líneas tienen que existir. Es el precio de que el
perno quede centrado en su vano.

> **Z = 0 es el PLANO MEDIO de la placa**, no la cara superior. La columna arranca en Z = 0, o
> sea se desprecia el solape de 25 mm entre el plano medio de la placa y la base de la columna.
> Es la idealización de láminas habitual y **va declarada**.

**Auditoría — las cinco**

| Comprobación | Resultado |
|---|---|
| Áreas | 648 = 18 × 36 ✅ |
| **Nudos** | **703 = 19 × 37 exacto** ✅ |
| Caja envolvente | X ±0,560 · Y ±1,400 · Z = 0 en los 703 ✅ |
| Nudo en cada línea de control | ninguna sin nudo, en los dos signos ✅ |
| Nudo exacto en los 8 pernos | los 8 con nombre ✅ |
| Propiedad `PLACA` en las 648 | 0 equivocadas ✅ |

> **El chequeo de fusión de nudos es el que más paga.** 703 contra los **2.592** que saldrían
> si cada área trajera sus cuatro puntos sin fusionar. Es una línea de código, y es la
> diferencia entre una placa continua y **648 placas sueltas que se ven idénticas en pantalla**.

> **Cómo el generador lo hace imposible en vez de comprobarlo después.** Los nudos se crean
> **una vez y se reutilizan por coordenada**, con un diccionario `(x,y,z) → nombre`. Así la
> fusión deja de ser algo que uno espera que SAP haga bien y pasa a ser una propiedad del
> constructor. La auditoría sigue existiendo igual: comprueba el resultado, no la intención.

---

## Paso 3 · Stub de columna

Alas en su **plano medio**, `y` = ±734 (= `d`/2 − `t_f`/2), abarcando `x` ∈ [−260, 260].
Alma en `x` = 0, abarcando `y` ∈ [−734, 734]. Altura de stub **1,50 m** en 15 divisiones de
100 mm.

240 áreas de ala + 270 de alma.

> **La altura de stub se elige, no se cablea.** El backend actual usa `z_col = 2.0*H` sin
> justificarlo. Acá 1,50 m ≈ 1× el canto, que por Saint-Venant alcanza para que la
> introducción de la carga no contamine la placa. **Se verifica alargándolo y viendo si la
> tensión en la placa se mueve.**

**Las estaciones NO se recalculan: se LEEN de la placa ya construida.** Así la columna se
conecta a los nudos que existen, no a los que uno cree que existen.

**Auditoría**

| Comprobación | Resultado |
|---|---|
| Áreas | 240 de ala + 270 de alma = **510** ✅ |
| Nudos totales | **1.228** (conjunto armado, no cableado) ✅ |
| **Nudos en Z = 0** | **703 — ni uno nuevo** ✅ |
| Propiedad en las 510 nuevas | 0 equivocadas ✅ |

Las 510 **no dependen del largo de placa**: la columna es la misma con `L` = 2.800 que con
3.200. Es la comprobación barata de que el cambio de hoy entró donde tenía que entrar.

> **«Nudos en Z = 0 sin cambios» es la que atrapa el error clásico**: una columna que se ve
> apoyada y está flotando sobre nudos duplicados a 10⁻⁹ m de los de la placa.

---

## Paso 4 · Cartelas y chapa transversal — y el defecto que la auditoría no vio

**Configuración adoptada**

| Chapa | Posición | Alcance | Altura | Áreas |
|---|---|---|---|---|
| **Cartela longitudinal** ×10 | `x` = **0, ±280, ±560**, plano Y-Z | `y` de ±734 a **±1400** | **500 mm** | **450** |
| **Chapa transversal** ×4 | `y` = ±734, plano X-Z | `x` de ±260 a **±560** | **500 mm** | **100** |

> **La transversal sube hasta la cota de la silla, no hasta la de la cartela.** Es donde la
> chapa de silla entrega la carga de los pernos de `x` = ±420 —los dos que quedan fuera del
> ancho del ala—, así que cortarla antes deja sin cerrar justo el tramo que importa.

> **Por qué existe la chapa transversal.** Las cartelas de `x` = ±280 y ±560 caen **fuera del
> ala**, que sólo llega a ±260: su extremo interior no tendría dónde apoyar. La chapa
> transversal prolonga el ala hasta el borde de placa y les da apoyo. **No es un
> refinamiento: sin ella media configuración está colgada.**
>
> Las cinco líneas de cartela tienen cada una su razón: `x` = 0 es la **prolongación del
> alma**, `x` = ±560 son las **paredes exteriores de la silla**, y las de ±280 parten los
> vanos. Sólo la de `x` = 0 apoya directamente en el ala; las otras cuatro, en la
> transversal — y la auditoría comprueba las dos cosas por separado.

### 🔴 El defecto — clase 1, y mi propia auditoría lo dejó pasar

Primera construcción: cartelas con 4 divisiones en altura → nudos en **z = 0 · 0,075 · 0,150 ·
0,225 · 0,300**. El stub de columna tiene los suyos en **z = 0 · 0,100 · 0,200 · 0,300**.

**Sólo coinciden en Z = 0.** La cartela tocaba el ala **únicamente en la base**, y todo lo de
arriba era un borde libre deslizando junto al ala. Se ve perfecta en pantalla. No lanza
ninguna excepción. Transferiría una fracción de la carga.

**Y la auditoría lo dio por bueno.** El chequeo era:

```
para cada z de la cartela: ¿existe nudo en (±140, ±734, z)?   ->  SÍ
```

Existía **porque lo había creado la propia cartela**. El chequeo se verificaba contra sí mismo.

### La corrección, y el chequeo que sí sirve

1. **Las estaciones Z de la cartela se leen de la columna**, no se eligen:
   `ZS = [z de la columna que sea ≤ altura de cartela]` → 0 · 0,100 · 0,200 · 0,300.
2. **El chequeo pasa a ser de propiedad compartida, no de existencia**: en cada línea de
   unión, el nudo tiene que estar tocado por **las dos chapas**.

```
para cada nudo de linea de union:
    props := {propiedad de cada area que toca ese nudo}
    assert {"ALA", "ATIESADOR"} <= props
```

Un intento intermedio —«que no aparezcan nudos nuevos»— **también era falso**: la chapa
transversal crea 312 nudos legítimos en sus bordes libres, donde antes no había nada. El
chequeo correcto es local a la línea de unión, no global al modelo.

**Auditoría final — verificada sobre la configuración vigente**

El chequeo se hace **por familia de área**, no por propiedad: cartela y chapa transversal
comparten la propiedad `ATIESADOR`, así que preguntar por la propiedad no distingue una de
otra y el chequeo pasaría con una sola de las dos presente.

| Línea de unión | Familias que tocan el nudo | En `z` = |
|---|---|---|
| `(0, 734, z)` | **ALA + CART** ✅ | 0 · 100 · 200 · 300 · 400 · 500 |
| `(±280, 734, z)` | **CART + TRAN** ✅ | 0 · 100 · 200 · 300 · 400 · 500 |
| `(±560, 734, z)` | **CART + TRAN** ✅ | 0 · 100 · 200 · 300 · 400 · 500 |
| `(0, 734, 0)` | ALA + CART + **PL** ✅ | la base |
| `(280, 734, 0)` | CART + TRAN + **PL** ✅ | la base |

**Estado tras el paso 4:** 1.708 áreas · 1.778 nudos · unidades 6.

### La regla que este paso deja para el contrato

> **Dos chapas que se cruzan no están unidas porque sus coordenadas coincidan: lo están
> cuando comparten nudo.** Y comprobar que «existe un nudo ahí» no lo demuestra —
> hay que comprobar **quién más lo toca**.

Es la comprobación más barata del modelo y la que más falla silenciosa evita. No existe en
ninguna forma en `backend_placabase.py`.

---

## Paso 5 · Silla y pernos — y el defecto más grave de todos

### 5a · Chapa superior de silla

Chapa a **`z` = 500 mm**, plano X-Y, de `y` = **734 a 1.400** (**666 mm**, el voladizo
completo), ancho `x` ∈ [−560, 560], espesor **50 mm**. Una sola chapa por fila, cubriendo los
cuatro pernos — configuración de *bota*, más simple y más rígida que cuatro sillas sueltas.
**324 áreas.**

Apoya en las **cinco** cartelas de cada fila, verificado nudo por nudo:
`{CART, SIL} ⊆ familias` en las **100** uniones.

### 🔴 La silla arrancaba a mitad del voladizo — corregido el 2026-08-27

Iba de `y` = 1.102,6 a 1.400. **Lo encontró el ingeniero mirando el render.**

**La silla es una viga en voladizo de 516 mm** entre la cara del ala (`y` = 734) y el perno
(`y` = 1.250): del lado traccionado el perno tira hacia abajo de la chapa superior y el ala
tira hacia arriba. Las cartelas son su alma; la chapa superior, **su ala**.

Con ese marco el defecto se ve solo: la chapa estaba sobre el **extremo libre**, donde el
momento del voladizo es **cero**, y **no existía en el empotramiento**, donde es máximo. 369
mm de voladizo sin ala superior, justo donde se la necesita. Es el peor lugar posible.

### 5a-bis · El atiesador de continuidad — la chapa que faltaba

La silla entrega su carga al ala a `z` = `HA`. Entre las dos alas **no había nada que la
recibiera**, así que el ala de 32 mm tenía que flexar fuera de su plano para equilibrarla.

El atiesador de continuidad es la **continuación literal de la chapa de silla a través de la
columna**: mismo plano X-Y, misma cota `z`, de ala a ala. Cierra el par de fuerzas *dentro*
de la columna. 144 áreas, `t` = 32 mm.

> **Y va partido por el alma sin partirlo a mano.** La malla ya tiene la estación `x` = 0, así
> que las dos mitades comparten los nudos del alma. La auditoría lo comprueba en las 19
> estaciones: sin eso sería una chapa apoyada en el aire dentro de la columna.

### El nudo de cinco familias

La comprobación que prueba de una vez que todo concurre donde debe:

```
en (0, 734, HA):  {ALA, ALM, SIL, CONT, CART} ⊆ familias
```

Ala, alma, chapa de silla, atiesador de continuidad y cartela, en el mismo punto. **Si
faltara cualquiera de las cinco, el modelo se vería idéntico en pantalla.**

Y las dos que cubren el ancho, que son las que separan lo que apoya de lo que cuelga:

| Dónde | Qué tiene que haber | Por qué |
|---|---|---|
| `(x, ±734, HA)` para `x` ∈ [−260, 260] | `{ALA, SIL, CONT}` | la silla entra al ala en **todo** el ancho del ala, no en un punto |
| `(±280, ±420, ±560; ±734, HA)` | `{TRAN, SIL}` | fuera del ala la recibe la **transversal** — por eso tuvo que subir hasta esta cota |

### 5b · Los pernos

| | |
|---|---|
| Recorrido | de la **silla** (`z` = **+0,500**) al **punto de anclaje** (`z` = −0,900) |
| Largo | **1,400 m** · `A` bruta 3.217 mm² · rigidez axial **459.571 kN/m** |
| Sección | `BOLT_M64` sobre `F1554_G36` |
| Extremo inferior | empotramiento de traslación (`TTTFFF`) |
| Límites T/C | **compresión = 0** en los ocho: el perno sólo trabaja a tracción |

> `L_ANC` = 0,900 m es **`⁉️`**: el `h_ef` real sale del Cap. 17 del ACI, que no está leído.
> Afecta la rigidez axial del perno y por lo tanto el reparto — hay que cerrarlo.

> **El extremo inferior empotrado en las 3 traslaciones es lo que hoy sostiene lateralmente el
> modelo**, porque los resortes del paso 6 son sólo verticales. Va declarado: **cuando se
> aplique el corte, iría entero a los pernos**, y eso contradice el diseño con llave de corte
> del DSC §7.10. Antes de aplicar `V` hay que modelar la llave.

### 🔴 El defecto — el perno soldado a todo lo que toca

Los pernos se crearon bien. Pero al armar el modelo de análisis:

```
line_elements = 32     (8 objetos frame -> 32 elementos)
```

**Cada perno se había partido en cuatro.** SAP mallea automáticamente los frames en los nudos
intermedios que encuentra en su camino, y el perno pasa por:

| `z` | Qué hay ahí |
|---:|---|
| 0,200 | nudo de **cartela** |
| 0,100 | nudo de **cartela** |
| 0,000 | nudo de **placa** |

O sea el perno quedaba **soldado a la cartela en toda su altura y a la placa**. Eso **anula la
silla por completo**: la tracción del perno iría directo a la placa en vez de subir a la silla,
que es exactamente lo contrario de lo que una silla existe para hacer.

**No lanza ninguna excepción. Se ve idéntico en pantalla. El modelo corre y da un número.**

### La corrección

```
FrameObj.SetAutoMesh(nombre, False, False, False, 0, 0.0, 0)
```

Con el mallado automático desactivado el perno queda de punta a punta y sólo toca sus dos
extremos: la silla arriba y el anclaje abajo. Verificado: **32 → 8 elementos**, todos de
**1,200 m**.

### La regla que este paso deja para el contrato

> **Un frame que atraviesa una malla se suelda a ella salvo que se le prohíba explícitamente.**
> Y el conteo de objetos no lo delata: `FrameObj.Count()` decía 8 en los dos casos. **Hay que
> contar ELEMENTOS, no objetos** — y para eso hay que llamar a `CreateAnalysisModel()` antes.

```
assert Analyze.CreateAnalysisModel() == 0
assert LineElm.Count() == n_pernos          # no FrameObj.Count()
assert {largo de cada elemento} == {largo nominal del perno}
```

`backend_placabase.py` crea los pernos con `AddByPoint` y **nunca llama a `SetAutoMesh` ni
comprueba `LineElm.Count()`**. Con la geometría de anillos que usa —donde el perno arranca en
el centro del anillo, sobre la placa— el efecto es distinto, pero la ausencia del chequeo es
la misma.

### 🔴 Y el chequeo que lo atrapa **caduca al grabar** — hallazgo del 2026-08-27

`File.Save` **descarta el modelo de análisis**, así que `LineElm.Count()` pasa de 8 a **0**.
Medido en la corrida del generador:

| | Antes del `Save` final | Después |
|---|---:|---:|
| `LineElm.Count()` | **8** | **0** |
| `FrameObj.Count()` | 8 | 8 |

O sea **la comprobación del automesh sólo vale antes del `Save`**. Corrida después devuelve
0, no 8 ni 32: falla *por la razón equivocada* y manda a buscar un defecto de conectividad
que no existe. Es la misma familia que la regla dura de `CLAUDE.md` —«`File.Save` desbloquea
el modelo y descarta los resultados, y las tablas devuelven **ceros**, no vacío»— pero
aplicada al modelo de análisis en vez de a los resultados, y aparece **antes** de que haya
ningún análisis corrido.

> **La regla:** todo contraste que se apoye en `CreateAnalysisModel()` se mide **antes** de
> grabar, y el generador declara el después en vez de dejarlo como un número suelto que el
> próximo lector va a interpretar como un defecto.

### Y un error de mi parte que conviene registrar

El primer intento falló con `('fallo restriccion', 1, [(True,…), 0])`. `SetRestraint` **no
devuelve un entero**: devuelve la tupla de salidas con el código al final. Comparar el retorno
contra `0` directamente da falso para una llamada que **funcionó**.

> **Todo retorno COM se normaliza antes de compararlo.** `_check_ret` del backend ya lo hace
> bien; lo que faltaba era usarlo en todas partes.

**Estado tras el paso 5:** 2.176 áreas · 8 frames · 2.174 nudos · 8 elementos de línea.

> ⚠️ **Subir `HA` alarga el perno y le baja la rigidez.** De 1,20 a 1,40 m, o sea `k` = `EA/L`
> cae un **14 %** (536.167 → 459.571 kN/m). Eso cambia el reparto entre pernos, y se suma a
> que `L_ANC` sigue siendo `⁉️`. **Toda decisión sobre la altura de silla toca el anclaje**,
> aunque parezca que sólo toca la chapa.

---

## 🔴 Corrección de geometría — el perno estaba sobre la cartela

**Lo encontró el ingeniero mirando el render, no la auditoría.** Vale la pena decirlo así:
ocho comprobaciones automáticas dieron verde sobre una configuración que **no se puede
construir**.

### El defecto

Las cartelas se habían puesto **en las líneas de perno**, `x` = ±140 y ±420 — con la idea de
que «cada perno entregue su tracción a una cartela». Dos consecuencias:

1. **Físicamente imposible**: el perno atravesaría la chapa de la cartela.
2. **Estructuralmente anula la silla**: si el perno está sobre la cartela, su tracción baja
   directo por ella y **la chapa de silla no flexa**. La silla deja de hacer lo único que hace.

Es el mismo error que el automesh del paso 5 —el perno conectado a lo que no debe— pero por
**geometría** en vez de por conectividad. Ninguna auditoría de conectividad lo ve, porque la
conectividad era correcta: el problema es que la configuración estaba mal.

### La corrección

**El perno va CENTRADO ENTRE cartelas**, para que la silla trabaje como lo que es: una chapa
que salva entre dos apoyos con la carga en el medio.

| | Antes | **Ahora** |
|---|---|---|
| Ancho de placa `B` | 1.100 mm | **1.120 mm** |
| Cartelas en `x` | ±140, ±420 | **0, ±280, ±560** |
| Pernos en `x` | ±140, ±420 | ±140, ±420 — **centrados en vanos de 280** |

Con `B` = 1.120 los cuatro vanos salen **exactamente 280 mm** y cada perno queda al centro del
suyo, con excentricidad medida **0,0 mm**. De paso, las cartelas nuevas tienen sentido propio:

- `x` = 0 es la **prolongación del alma** más allá del ala.
- `x` = ±560 son las **paredes exteriores de la silla**, que antes no existían.

Mínimos, **con los valores ya leídos** (ACI Tabla 17.9.2(a), impresa 294, rasterizada el
2026-08-27): separación **280 ≥ 4·`d_a` = 256** ✅ · borde al hormigón **290 ≥ 75** ✅.

> ⚠️ **Corrección del propio párrafo anterior.** Cuando esto se escribió decía «borde
> 140 ≥ 2·`d` = 128». **Las dos cifras eran equivocadas y ninguna daba síntoma:**
>
> - el **2·`d` no existe en el ACI** — para anclaje colado y no torqueado el mínimo es el
>   *recubrimiento* de 20.5.1.3, y no es un múltiplo del diámetro;
> - y el **140 se medía contra el borde de placa**, cuando `c_a,min` está definido como
>   «minimum distance from center of an anchor shaft to the edge of **concrete**» (notación,
>   impresa 18). Contra el borde del **pedestal** hay 290 mm.
>
> Un límite inventado más estricto que el tabulado **nunca falla una verificación**: es la
> clase 4 en su forma exacta, y por eso sobrevivió a ocho auditorías en verde.

### Las dos comprobaciones nuevas que esto agrega al contrato

```
# 1. Ningun perno puede caer sobre una linea de cartela
assert not [b for b in pernos_x if any(abs(b-c) < 1mm for c in cartelas_x)]

# 2. Cada perno CENTRADO en su vano, con cartela a los dos lados
para cada perno:
    izq := max(cartela < perno)      # tiene que existir
    der := min(cartela > perno)      # tiene que existir
    assert |perno - (izq+der)/2| ~ 0
```

La segunda es la que importa: no alcanza con que el perno no choque, tiene que estar **al
centro**. Un perno pegado a una cartela transfiere casi todo por ella y la silla vuelve a no
trabajar, sin que nada lo denuncie.

### La lección, que es más general que este modelo

> **La auditoría automática comprueba que el modelo sea el que se pidió. No comprueba que lo
> que se pidió tenga sentido.** Las ocho comprobaciones estaban bien escritas y todas pasaban;
> lo que fallaba era la configuración, y eso lo ve un ojo sobre el render.
>
> **El paso de mirar el modelo en la GUI no es opcional y no lo reemplaza ningún assert.**

---

## 🔴 El generador no existía — hallazgo del 2026-08-27, segunda sesión

La sección anterior terminaba diciendo que el modelo *«se reconstruyó entero desde cero en
16 s con un solo script»*, y lo daba como **la prueba de que la fuente de verdad es el
generador y no el `.sdb`**.

**Ese script no estaba en disco.** Búsqueda en todo `C:\Proyectos_Python`: ni un `.py` que
construyera la placa. Los pasos 0-5 se habían corrido por el puente MCP, en memoria, y lo
único que quedó fue el `.sdb` en `_run/` — que está **gitignorado**.

O sea el modelo de 1.764 áreas **no era regenerable por nadie**, mientras el documento
afirmaba que sí. Es exactamente lo que prohíbe `_regla_propia_3` del `PERFIL.json` del
proyecto (A-35) —*todo cambio que deba persistir va dentro de un script*— y el invariante 4
de `CLAUDE.md`.

> **Por qué no dio síntoma.** Mientras la sesión seguía viva, el modelo estaba abierto y todo
> funcionaba. La afirmación «es regenerable» sólo se puede falsar *intentando regenerarlo*, y
> nadie lo intentó hasta que hizo falta cambiar el largo de placa. **Una capacidad que nunca
> se ejercita se atrofia sin avisar**, y el documento que la afirma la vuelve invisible.

**Corregido:** `build_placabase_COL_PLT_R.py`, acá al lado, implementa los pasos 0 a 5
completos con las auditorías de este contrato.

---

# LO QUE SE LLEVA A LA PRÓXIMA PLACA BASE

Todo lo de arriba es el registro de **una** placa. Esto es lo que sobrevive al caso: las
reglas que valen para cualquier configuración, cada una con el defecto real que la originó.

## A · Concepción — qué chapas van y por qué

### A-1 · La silla es una viga en voladizo. Dibujá esa viga antes de dibujar chapas

Entre la **cara del ala** y el **eje del perno**. Del lado traccionado el perno tira hacia
abajo de la chapa superior y el ala tira hacia arriba.

| Pieza de la silla | Qué es en la viga |
|---|---|
| Cartelas verticales | **el alma** |
| Chapa superior | **el ala** |
| Cara del ala de la columna | **el empotramiento** |
| Eje del perno | **el extremo libre** |

> **La regla:** la chapa superior tiene que existir **en el empotramiento**, que es donde el
> momento es máximo. Ponerla sólo bajo el perno es ponerla donde el momento es cero.
>
> *Cómo se manifestó:* la silla iba de `y` = 1.102,6 a 1.400 con el ala en 734 — 369 mm de
> voladizo sin ala superior. Ocho auditorías en verde, y el defecto se ve en un render.

### A-2 · Toda chapa que llega a un ala necesita continuidad del otro lado

Si una chapa entrega carga perpendicular a un ala y no hay nada que la reciba **del otro
lado**, el ala flexa fuera de su plano. Es un *continuity plate* clásico, y en una placa base
con silla toma una forma muy concreta: **la chapa de silla tiene que atravesar la columna**,
mismo plano, misma cota, de ala a ala.

> **Preguntá siempre:** ¿qué hay del otro lado del ala, a la cota donde entrego la carga?
> Si la respuesta es «nada», falta una chapa.

### A-3 · Cada cartela tiene que tener un elemento de la columna que la reciba

Tres calidades de apoyo, en orden:

| La cartela cae… | Camino a la columna | Calidad |
|---|---|---|
| alineada con el **alma** | continúa en el alma sin transición | ✅ directo |
| dentro del **ancho del ala** | forma T con el ala | ✅ bueno |
| **fuera del ala** | necesita una chapa de transferencia que la lleve al canto del ala | ⚠️ indirecto |

Y si es indirecto: **esa chapa de transferencia tiene que llegar hasta la cota donde se
entrega la carga**, no hasta la altura de la cartela.

> *Cómo se manifestó:* la chapa transversal moría en `z` = 300 cuando la silla entregaba en
> `z` = 500. Los dos pernos exteriores quedaban colgando del tramo que faltaba.

### A-4 · El ancho del ala dice cuántos pernos pueden tener camino directo

Comprobación de treinta segundos, **antes de dibujar nada**:

```
n_directos = piso(b_f / s_min) + 1        con s_min de la Tabla 17.9.2(a) del ACI
```

Acá: `b_f` = 520 y `s_min` = 4·`d_a` = 256 → **2 pernos**. Con 4 por fila, **dos siempre van
a quedar afuera**. Ninguna silla arregla eso: se resuelve con chapa de transferencia y se
declara, o se cambia la configuración de pernos.

> Es el número que explica por qué una placa «se ve rara» antes de modelarla.

### A-5 · El perno va centrado entre cartelas, nunca sobre una

Sobre la cartela el perno es imposible de construir *y* anula la silla: la tracción baja
directo por la chapa y la silla no flexa. Pegado a una cartela, casi lo mismo, y **nada lo
denuncia**. Dos comprobaciones, no una:

```
1. ningún perno sobre una línea de cartela
2. cada perno con cartela a los dos lados Y equidistante de ambas
```

### A-6 · El espesor de la chapa de silla sale de la flexión entre cartelas

No del espesor de la placa base ni del de las cartelas:

```
M ≈ (T_perno · s / 4) / ancho_colaborante        t ≈ √(4M / (φ_b · F_y))
```

Acá dio 52 mm con `T` = 663 kN y `s` = 280 → **50 mm**. La chapa estaba en 25.

> **Contrastalo siempre contra una tabla de taller.** Dos caminos independientes que dan lo
> mismo valen mucho más que uno solo; y si discrepan, hay algo que entender antes de seguir.

### A-7 · La altura de silla no es sólo de la silla

Toca el anclaje: alarga el perno y le baja la rigidez axial `EA/L`, lo que **cambia el
reparto entre pernos**. Subir `HA` de 300 a 500 costó un 14 % de rigidez.

---

## B · Oficio de modelado — cómo construirlo y cómo auditarlo

### B-1 · Las estaciones se leen, no se eligen

- Las `Z` de la cartela, **de la columna**.
- Las `Y` de la silla, **de la placa**.
- Las de la columna, **de la placa ya construida**.

> *Cómo se manifestó:* cartela con 4 divisiones propias → nudos en 0/75/150/225/300 contra
> 0/100/200/300 de la columna. **Coincidían sólo en `z` = 0.** La cartela tocaba el ala
> únicamente en la base y todo lo de arriba era un borde libre deslizando. Se ve perfecta.

Y al revés: **un límite «redondo» es una señal de alarma**. Si la silla arranca en 1.100
porque es un número lindo, o mete una línea que no apoya nada, o deja un borde libre entre
nudos.

### B-2 · Los nudos se crean una vez y se reutilizan por coordenada

Un diccionario `(x,y,z) → nombre`. Así la fusión deja de ser algo que uno **espera** que SAP
haga y pasa a ser una propiedad del constructor. La auditoría se hace igual: comprueba el
resultado, no la intención.

> El chequeo que más paga: 703 nudos contra los **2.592** que saldrían sin fusionar. Es la
> diferencia entre una placa continua y 648 placas sueltas **que se ven idénticas**.

### B-3 · Comprobá quién más toca el nudo, no que el nudo exista

El chequeo «¿existe nudo en (x,y,z)?» **se verifica contra sí mismo**: el nudo lo creó la
propia chapa que estás auditando. Siempre da verde.

```
props := {familia de cada área que toca ese nudo}
assert {"ALA", "CART"} ⊆ props
```

**Dos chapas que se cruzan no están unidas porque sus coordenadas coincidan: lo están cuando
comparten nudo.** Es la comprobación más barata del modelo y la que más falla silenciosa
evita.

### B-4 · Chequeá por familia de área, no por propiedad

Cartela y chapa transversal comparten la propiedad `ATIESADOR`. Preguntar por la propiedad
**no distingue una de otra**, y el chequeo pasa con una sola de las dos presente. La familia
sale del nombre del área, que lo ponés vos.

### B-5 · Buscá el nudo donde concurre todo y auditalo

En esta placa: `(0, 734, HA)` con `{ALA, ALM, SIL, CONT, CART}`. Una sola línea prueba que
las cinco chapas llegan donde tienen que llegar. **Si faltara cualquiera, el modelo se vería
idéntico en pantalla.**

Y auditá **el ancho completo**, no un punto: la silla tiene que entrar al ala en las 9
estaciones del ancho del ala, no en el centro.

### B-6 · Un frame que atraviesa una malla se suelda a ella

Salvo que se lo prohíbas: `FrameObj.SetAutoMesh(nombre, False, False, False, 0, 0.0, 0)`.

> *Cómo se manifestó:* cada perno partido en 4 por los nudos de cartela y placa que
> atraviesa. Quedaba **soldado a la cartela en toda su altura y a la placa**, lo que anula la
> silla por completo. El modelo corre y da un número.

Y **`FrameObj.Count()` no lo delata**: dice 8 en los dos casos. Hay que contar **elementos**:

```
assert Analyze.CreateAnalysisModel() == 0
assert LineElm.Count() == n_pernos           # no FrameObj.Count()
assert {largo de cada elemento} == {largo nominal}
```

### B-7 · Todo contraste que dependa del modelo de análisis se mide antes del `Save`

`File.Save` **descarta el modelo de análisis**: `LineElm.Count()` pasa de 8 a **0**. La
comprobación de B-6 corrida después falla **por la razón equivocada** y manda a buscar un
defecto que no existe. Es pariente de la regla dura de `CLAUDE.md` sobre los resultados, pero
aparece antes de que haya ningún análisis.

### B-8 · Todo retorno COM se normaliza, y los índices se verifican

```python
def ok(r):
    return (r if isinstance(r, (int, float)) else r[-1]) == 0
```

`SetRestraint` no devuelve un entero: devuelve la tupla de salidas **con el código al final**.
Comparar contra `0` da falso para una llamada que funcionó.

Y al leer: `GetCircle` devuelve `(FileName, MatProp, T3, …, ret)` — el diámetro es `[2]`.
Acá reventó con `TypeError` porque `[1]` es un string; **si hubiera caído sobre otro float
habría devuelto un número equivocado sin ningún síntoma.**

### B-9 · Los conteos absolutos de propiedades no sirven

`PropMaterial.Count()` devuelve 6 habiendo definido 3: el modelo en blanco de SAP trae tres
por defecto. Un contrato que asertara «3 materiales» **falla sin razón**. Comprobá por nombre.

En cambio los conteos de **objetos que creaste vos** sí sirven, y mucho — siempre que salgan
de la especificación y no estén cableados:

```python
auditar("áreas de placa", n, (len(EST_X) - 1) * (len(EST_Y) - 1))
```

Así, cambiar el largo de placa reajusta el esperado solo, y las 510 áreas de columna que **no
deben moverse** son la comprobación barata de que el cambio entró donde tenía que entrar.

### B-10 · Shell-thick, siempre que la luz sobre el espesor sea chica

Acá la placa de 50 mm salva 280 mm entre cartelas: **luz/espesor = 5,6**. Con *thin shell* se
pierde la deformación por corte y el momento sale equivocado **justo en el número que el
modelo viene a verificar**.

### B-11 · Un paso, una auditoría — y la auditoría levanta, no avisa

Si un paso no cierra se para ahí. Nunca `except: pass`, nunca un aviso que el próximo lector
va a pasar por alto. El generador acumula 282 comprobaciones y **cualquiera de ellas corta la
corrida**.

### B-12 · Y la que ninguna de las anteriores reemplaza

> **La auditoría automática comprueba que el modelo sea el que se pidió. No comprueba que lo
> que se pidió tenga sentido.**

Los tres defectos más graves de esta placa —el perno sobre la cartela, la silla que no llegaba
al ala, el atiesador de continuidad que faltaba— **los encontró el ingeniero mirando el
render**, con todas las auditorías en verde. Las auditorías estaban bien escritas; lo que
fallaba era la configuración.

**Mirar el modelo en la GUI no es opcional y no lo reemplaza ningún assert.**

---

## C · El orden en que conviene atacar una placa nueva

1. **Dibujá la viga en voladizo** de la silla (A-1) y contá los pernos directos (A-4).
   Los dos son de lápiz y deciden la configuración entera.
2. Leé **separación mínima y distancia de borde** rasterizadas antes de fijar el ancho. Con
   una sola fila de pernos, deciden el diámetro.
3. Declará **las líneas de control** de los dos ejes antes de construir nada.
4. Construí de adentro hacia afuera —placa, columna, cartelas, silla— **leyendo las
   estaciones** del paso anterior (B-1).
5. Auditá cada paso con **quién comparte el nudo** (B-3, B-4, B-5).
6. **Abrí la GUI y mirá** (B-12).
7. Recién ahí, resortes, cargas y análisis.

---

## ESTADO — 2026-08-27, segunda sesión

### Lo que está hecho

| Paso | Estado |
|---|---|
| 0 · unidades, modelo vacío, archivo | ✅ |
| 1 · materiales y propiedades | ✅ |
| 2 · contorno de placa | ✅ |
| 3 · stub de columna | ✅ |
| 4 · cartelas y chapa transversal | ✅ · un defecto encontrado y corregido |
| 5 · silla y pernos | ✅ · dos defectos encontrados y corregidos |
| — · **el generador, en disco** | ✅ · **`build_placabase_COL_PLT_R.py`** |
| — · largo de placa 3.200 → **2.800** | ✅ · regenerado entero |
| — · **los cinco cambios de silla** | ✅ · regenerado entero |
| **6 · resortes de hormigón** | **pendiente** |
| **7 · cargas** | **pendiente** |
| **8 · auditoría final y análisis** | **pendiente** |

### Los cinco cambios de silla — 2026-08-27

Salieron de mirar el render contra el modelo. Los cinco de una:

| # | Cambio | Por qué |
|:-:|---|---|
| 1 | Chapa de silla **continua de `y` = 734 a 1.400** | ala superior en el empotramiento del voladizo (**A-1**) |
| 2 | **Atiesador de continuidad** a `z` = `HA`, de ala a ala | cierra el par dentro de la columna en vez de flexar el ala (**A-2**) |
| 3 | Chapa transversal **hasta `z` = `HA`**, no 300 | es lo que sostiene a los pernos fuera del ala (**A-3**) |
| 4 | `e1` de silla **25 → 50 mm** | cálculo y tabla de taller dan lo mismo (**A-6**) |
| 5 | `HA` **300 → 500 mm** | más brazo y más longitud de soldadura (**A-7**) |

**Modelo:** `Struct_Harness/_run/placabase_COL_PLT_R_2026-08-27.sdb`

| | |
|---|---|
| Áreas | **2.176** — placa 648 · columna 510 · cartelas 450 · transversal 100 · silla 324 · **continuidad 144** |
| Nudos | **2.174** · **703** en Z = 0 (= 19 × 37) |
| Frames | 8 · **8 elementos de línea** de 1,400 m (medidos antes del `Save`) |
| Auditoría | **282 comprobaciones, 0 fallan** |
| Corrida | **25,8 s** de punta a punta |

**Ahora sí el `.sdb` no es la fuente de verdad**, y la frase se puede sostener: cambiar el
largo de placa costó una corrida.

### Las tres lecturas que bloqueaban — ✅ **las tres cerradas**

Todas rasterizadas el 2026-08-27 y anotadas en el `leidas.json` de su norma.

| # | Qué se leyó | Qué dijo |
|:-:|---|---|
| 1 | **ACI 318-25 Tabla 17.9.2(a)** · impresa 294 | Anclaje colado **no torqueado**: separación **4·`d_a` = 256 mm** ✅ (hay 280). Borde: **el recubrimiento de 20.5.1.3**, no un múltiplo de `d` — **75 mm** ✅ (hay 290). **Torqueado sería 6·`d_a` = 384 en las dos y se cae todo** |
| 2 | **AISC DG1 Ec. (4-1) y (4-2)** · impresas 20-21 | `f_p(max)` = 0,85·`f'c`·√(A₂/A₁) ≤ 1,7·`f'c`, y `f_pu` = `φ_c`·`f_p` con **`φ_c` = 0,65**. Da **18,35 MPa**, un 27 % *menos* que los 25 supuestos |
| 3 | **DSC §8.7** · impresa 30 | **La resuelve el criterio del cliente:** tabula «`f'c` (ACI 318) = 30 MPa» y la equivalencia «ACI 30 ↔ CIRSOC H-30». **No hay conversión cúbica/cilíndrica que hacer** |

> **Lo que el `f_p` leído enseñó.** Baja un 27 % y la tracción sube apenas 0,9 % (2.630,4 →
> 2.653,0 kN). Confirma que **`T` sale del brazo de palanca, no de la resistencia del
> hormigón**: el `f_p` decide el *espesor*, no el perno. La lectura que parecía crítica no lo
> era, y la que parecía menor —la separación— era la que podía tirar abajo el diseño.

### La decisión, cerrada

**Largo de placa: 2,80 m**, tomado por el ingeniero el 2026-08-27.

| Largo | `T` de fila | Uso 4 M64 | Pedestal |
|---:|---:|---:|---|
| **2,80 m** | **2.653,0 kN** | **0,826** | 3.100 × 1.420 |
| 3,20 m | 2.267,1 kN | 0,706 | 3.500 × 1.420 |

Respaldo: `20_calculo/scripts/predim_placa_pedestal.py` → memo
`40_registro/memos/2026-08-27-placa-pedestal-valores-leidos.md`. Cierra con **7 chequeos en
verde, 12 valores leídos rasterizados, 2 supuestos y 3 inferidos**.

### 🔴 El supuesto del que cuelga toda la geometría

**Los pernos de anclaje NO se torquean.** Es lo único que habilita el 4·`d_a`.

El DSC **no lo resuelve**: su párrafo «los pernos se tensarán completamente hasta los valores
recomendados» (impresa 29, rasterizada) está en el **§8.2, que habla de pernos estructurales
ASTM F3125 A325 de conexión**. El §8.5, que sí es el de anclaje, remite a la guía Bechtel
3DG-C13-00012 — **que no está en la biblioteca** y ya figura como hueco `pernos_de_anclaje`
del `PERFIL.json`.

> **Tiene que bajar al plano con esas palabras.** Si el montaje los pretensa, rige 6·`d_a` y
> hay que ir a placa de 1.536 y pedestal de 1.920 mm de ancho.

Y el margen de separación es de **9,4 %** (280 contra 256). No es cómodo, y **la tolerancia
de montaje del anclaje no está verificada contra ese número.**

### Lo que quedó declarado y no se puede olvidar

- **El corte de capacidad no está medido.** Hoy el modelo se sostiene lateralmente con los 8
  pernos empotrados, lo que **contradice el diseño con llave de corte** del DSC §7.10.
  Antes de aplicar `V` hay que modelar la llave.
- **`L_ANC` = 0,900 m es `⁉️`** — el `h_ef` sale del Cap. 17 y **también fija la altura del
  pedestal**, que sigue sin cerrarse.
- **El espesor de 50 mm cuelga de que la silla y las cartelas se diseñen**, en las dos
  direcciones. Están *supuestas provistas*, no calculadas.
- **`demanda_capacidad_63.py` mide sólo la transversal.** El tope del §6.3 en la longitudinal
  (fila 22, PSEAC, `R` = 5) no existe: ahí la capacidad la fija el mecanismo de riostras.
- **La zapata sigue bloqueada por geotecnia**: `MWH-GEOTEC-RevB` tiene tres páginas leídas y las
  tres son de calibración de offset.
- **`placa_base_v24_planta.svg` está superado dos veces**: dibuja `L` = 3.200 y las cartelas
  sobre las líneas de perno.

---

<!-- Pasos 6 a 8 pendientes: resortes de hormigón · cargas · auditoría final y análisis. -->



