# -*- coding: utf-8 -*-
"""Generador del modelo de placa base de COL_PLT_R — pasos 0 a 5.

    python -m harness.correr_generador ^
        C:\\Proyectos_Python\\Skills_SAP\\scripts\\placabase\\build_placabase_COL_PLT_R.py

QUE ES ESTO
-----------
La implementacion literal de `COMO_MODELAR.md`, que es su contrato: lo que hay
que construir y —sobre todo— **lo que hay que comprobar antes de decir que salio
bien**. Un paso, una auditoria. Si un paso no cierra, se para ahi. Nunca
`except: pass`.

POR QUE EXISTE ESTE ARCHIVO Y NO EXISTIA ANTES
----------------------------------------------
🔴 Los pasos 0-5 se corrieron el 2026-08-27 por el puente MCP, en memoria, y el
script NO QUEDO EN DISCO. El `.sdb` vive en `_run/`, que esta gitignorado. O sea
el modelo de 1.764 areas no era regenerable por nadie, y el propio
`COMO_MODELAR.md` afirmaba que si lo era.

Es exactamente lo que `_regla_propia_3` del PERFIL del proyecto prohibe (A-35):
**todo cambio que deba persistir va dentro de un script**. Y es el invariante 4
de Struct_Harness: la fuente de verdad es el generador, no el `.sdb`.

QUE CAMBIA RESPECTO DE LA CORRIDA DEL 2026-08-27
------------------------------------------------
**El largo de placa pasa de 3.200 a 2.800 mm**, decidido por el ingeniero sobre
la hoja de valores `predim_placa_pedestal.py`. Con la pareja M-N medida en el
nudo 26 de v24 eso da uso 0,826 en los pernos contra 0,706, y ahorra 400 mm de
pedestal en la direccion del momento. Arrastra:

    fila de pernos   y = +-1.450  ->  +-1.250
    borde de placa   y = +-1.600  ->  +-1.400
    areas            1.764        ->  1.632
    nudos en Z = 0   779          ->  703

El ancho, las cartelas y los pernos NO se mueven: son la configuracion corregida
del 2026-08-27, con el perno centrado en su vano de 280 mm.

LO QUE ESTE GENERADOR NO HACE
-----------------------------
No aplica cargas, no analiza y no disena: eso son los pasos 6 a 8. Y no toca
ningun modelo del proyecto — construye uno nuevo en `_run/`, que es scratch.
"""

import math
import os

# ═══════════════════════════════════════════════════════════ ESPECIFICACION

ARCHIVO = r"C:\Proyectos_Python\Struct_Harness\_run\placabase_COL_PLT_R_2026-08-27.sdb"

UNIDADES = 6                      # kN-m-C. `_codigo/sap/lectura.py` asierta este codigo

# --- placa. X = ancho, Y = largo (la direccion del canto de columna) ---------
B_PLACA = 1120.0                  # mm, ancho
L_PLACA = 2800.0                  # mm, largo  <- LO QUE CAMBIA HOY
T_PLACA = 50.0                    # mm

# --- columna COL_PLT_R: doble T soldada 1500 x 16, alas 520 x 32 -------------
D_COL, TW_COL = 1500.0, 16.0
BF_COL, TF_COL = 520.0, 32.0
Y_ALA = (D_COL - TF_COL) / 2.0    # 734,0 — plano MEDIO del ala
X_ALA = BF_COL / 2.0              # 260,0
H_STUB = 1500.0                   # ~1x el canto: por Saint-Venant alcanza para que
N_DIV_STUB = 15                   # la introduccion de la carga no contamine la placa

# --- cartelas y silla --------------------------------------------------------
# La silla es una VIGA EN VOLADIZO de 516 mm entre la cara del ala (y = 734) y el
# perno (y = 1.250). Las cartelas son su alma; la chapa superior, su ala. Todo lo
# que sigue se entiende desde ahi.
H_SILLA = 500.0                   # (5) era 300. Referencia de taller para o 2 1/2":
                                  #     HA = 500. Mas brazo en el voladizo y mas
                                  #     longitud de soldadura contra el ala
T_CARTELA = 25.0
CARTELAS_X = [-560.0, -280.0, 0.0, 280.0, 560.0]
T_SILLA = 50.0                    # (4) era 25. Dos caminos independientes dan lo
                                  #     mismo: el calculo de flexion entre cartelas
                                  #     pide ~52 mm, y la referencia de taller da
                                  #     e1 = 50 para este diametro. Con 25 el uso
                                  #     era ~4,4
T_CONTINUIDAD = TF_COL            # (2) 32 mm = el ala de la columna. Es prediseno:
                                  #     el espesor definitivo lo dice la tension que
                                  #     mida el propio FE

# --- pernos ------------------------------------------------------------------
D_PERNO = 64.0                    # M64
PERNOS_X = [-420.0, -140.0, 140.0, 420.0]
Y_PERNO = L_PLACA / 2.0 - 150.0   # 1.250,0 — 150 mm del borde de placa
Z_SILLA = H_SILLA                 # +500, el perno arranca en la chapa de silla
Z_ANCLAJE = -900.0                # ⁉️ el h_ef real sale del Cap. 17, no esta leido

# --- materiales --------------------------------------------------------------
E_ACERO = 200.0e6                 # kPa = 200 GPa
NU = 0.30
GAMMA = 77.178                    # kN/m3
FY_A36, FU_A36 = 250.0e3, 400.0e3           # kPa   ⁉️ ASTM A36 no esta en biblioteca
FY_COL, FU_COL = 344.74e3, 448.16e3         # kPa   A572 Gr.50, leido del modelo v24
FY_F1554, FU_F1554 = 250.0e3, 400.0e3       # kPa   ⁉️ ASTM F1554 no esta en biblioteca

SHELL_THICK = 2                   # NO es cosmetico: luz/espesor = 280/50 = 5,6

MM = 1000.0                       # el modelo esta en metros


# ═══════════════════════════════════════════════════════════════ UTILIDADES

def ok(r):
    """El codigo de retorno va al final cuando la funcion tiene ByRef. Ver A-14.

    `SetRestraint` no devuelve un entero: devuelve la tupla de salidas con el
    codigo al final. Comparar el retorno contra 0 directamente da falso para una
    llamada que FUNCIONO.
    """
    return (r if isinstance(r, (int, float)) else r[-1]) == 0


def espejar(semi):
    """[0, a, b] -> [-b, -a, 0, a, b]. Sin duplicar el cero."""
    return [-v for v in reversed(semi[1:])] + list(semi)


def tramo(a, b, n):
    """n subdivisiones de [a, b], sin repetir a."""
    return [a + (b - a) * (i + 1) / n for i in range(n)]


# --- las estaciones, declaradas ANTES de construir nada ----------------------
# X: borde 560 · cartelas 0/280/560 · pernos 140/420 · ala 260
SEMI_X = [0.0] + tramo(0, 140, 2) + tramo(140, 260, 2) + tramo(260, 280, 1) \
         + tramo(280, 420, 2) + tramo(420, 560, 2)
EST_X = espejar(SEMI_X)

# Y: borde L/2 · pernos Y_PERNO · plano medio de ala 734
SEMI_Y = [0.0] + tramo(0, Y_ALA, 9) + tramo(Y_ALA, Y_PERNO, 7) \
         + tramo(Y_PERNO, L_PLACA / 2, 2)
EST_Y = espejar(SEMI_Y)

EST_Z_STUB = [H_STUB * i / N_DIV_STUB for i in range(N_DIV_STUB + 1)]

LINEAS_CONTROL_X = [0.0, 140.0, 260.0, 280.0, 420.0, 560.0]
LINEAS_CONTROL_Y = [0.0, Y_ALA, Y_PERNO, L_PLACA / 2]


# ═══════════════════════════════════════════ el registro de lo que se audita

AUD = []


def auditar(paso, que, medido, esperado, sentido="=="):
    """Registra una comprobacion y LEVANTA si no cierra. Nunca avisa y sigue."""
    if sentido == "==":
        pasa = medido == esperado
    elif sentido == "<=":
        pasa = medido <= esperado
    else:
        pasa = medido >= esperado
    AUD.append({"paso": paso, "que": que, "medido": medido,
                "esperado": esperado, "sentido": sentido, "pasa": bool(pasa)})
    if not pasa:
        raise AssertionError(
            "PASO %s — %s: medido %r, esperado %s %r" % (paso, que, medido,
                                                         sentido, esperado))
    return True


result["parametros"] = {
    "L_placa_mm": L_PLACA, "B_placa_mm": B_PLACA, "t_placa_mm": T_PLACA,
    "y_perno_mm": Y_PERNO, "cartelas_x_mm": CARTELAS_X, "pernos_x_mm": PERNOS_X,
    "n_est_x": len(EST_X), "n_est_y": len(EST_Y),
    "_cambio": "L_placa 3.200 -> 2.800 mm, decidido 2026-08-27",
}


# ═════════════════════════════════════ PASO 0 · unidades, vacio y archivo

# La precondicion se comprueba ANTES de escribir nada: empezar sobre un modelo
# que uno CREE vacio y no lo esta deja objetos huerfanos que despues aparecen en
# las auditorias de conteo y no se explican.
assert ok(SapModel.InitializeNewModel(UNIDADES)), "InitializeNewModel"
assert ok(SapModel.File.NewBlank()), "NewBlank"

auditar(0, "puntos previos", SapModel.PointObj.Count(), 0)
auditar(0, "frames previos", SapModel.FrameObj.Count(), 0)
auditar(0, "areas previas", SapModel.AreaObj.Count(), 0)
auditar(0, "unidades antes de grabar", SapModel.GetPresentUnits(), UNIDADES)

assert ok(SapModel.File.Save(ARCHIVO)), "File.Save"

# El Save puede cambiar el estado del modelo. Aca no hay resultados que perder,
# pero desde el paso 7 en adelante la regla dura manda: no grabar despues de
# analizar sin re-comprobar GetModelIsLocked().
auditar(0, "unidades TRAS el Save", SapModel.GetPresentUnits(), UNIDADES)
auditar(0, "nombre de archivo",
        os.path.basename(SapModel.GetModelFilename(True)).lower(),
        os.path.basename(ARCHIVO).lower())
auditar(0, "modelo NO bloqueado (no hay analisis)",
        bool(SapModel.GetModelIsLocked()), False)

result["paso0"] = {"archivo": SapModel.GetModelFilename(True),
                   "unidades": SapModel.GetPresentUnits()}


# ══════════════════════════════ PASO 1 · materiales y propiedades de shell

MATERIALES = [
    ("A36",       FY_A36,   FU_A36),
    ("ACERO_COL", FY_COL,   FU_COL),
    ("F1554_G36", FY_F1554, FU_F1554),
]
for nom, fy, fu in MATERIALES:
    assert ok(SapModel.PropMaterial.SetMaterial(nom, 1)), nom          # 1 = STEEL
    assert ok(SapModel.PropMaterial.SetMPIsotropic(nom, E_ACERO, NU, 1.17e-5)), nom
    assert ok(SapModel.PropMaterial.SetWeightAndMass(nom, 1, GAMMA)), nom
    # eFy = Fy y eFu = Fu, SIN sobrerresistencia: el modelo es elastico, no de
    # capacidad. La capacidad ya esta adentro de la demanda de 7.271,5 kN.m.
    assert ok(SapModel.PropMaterial.SetOSteel_1(
        nom, fy, fu, fy, fu, 1, 2, 0.02, 0.1, 0.2, -0.1)), nom

SHELLS = [
    ("PLACA",     T_PLACA,       "A36"),
    ("ALA",       TF_COL,        "ACERO_COL"),
    ("ALMA",      TW_COL,        "ACERO_COL"),
    ("ATIESADOR", T_CARTELA,     "A36"),
    ("SILLA",     T_SILLA,       "A36"),
    ("CONTIN",    T_CONTINUIDAD, "ACERO_COL"),
]
for nom, t, mat in SHELLS:
    assert ok(SapModel.PropArea.SetShell_1(
        nom, SHELL_THICK, True, mat, 0.0, t / MM, t / MM)), nom

assert ok(SapModel.PropFrame.SetCircle("BOLT_M64", "F1554_G36", D_PERNO / MM)), "BOLT"

# Cada propiedad RELEIDA y comparada contra lo pedido. Un `Set` que devuelve 0 no
# prueba que la propiedad haya quedado con el valor que se pidio.
for nom, fy, fu in MATERIALES:
    r = SapModel.PropMaterial.GetOSteel_1(nom)
    auditar(1, "Fy de %s" % nom, round(r[0], 3), round(fy, 3))
    auditar(1, "Fu de %s" % nom, round(r[1], 3), round(fu, 3))
    e, u, _, _ = SapModel.PropMaterial.GetMPIsotropic(nom)[:4]
    auditar(1, "E de %s" % nom, round(e, 1), round(E_ACERO, 1))
    auditar(1, "nu de %s" % nom, round(u, 4), NU)

for nom, t, mat in SHELLS:
    r = SapModel.PropArea.GetShell_1(nom)
    auditar(1, "ShellType de %s" % nom, r[0], SHELL_THICK)
    auditar(1, "material de %s" % nom, r[2], mat)
    auditar(1, "espesor de %s" % nom, round(r[4] * MM, 3), round(t, 3))

# GetCircle devuelve (FileName, MatProp, T3, Color, Notes, GUID, ret): el
# diametro es [2], no [1]. Indexar un retorno COM a ojo es la clase 1 en su
# forma mas barata — aca revienta, pero un indice corrido que cae sobre otro
# float devuelve un numero equivocado sin ningun sintoma.
_circ = SapModel.PropFrame.GetCircle("BOLT_M64")
auditar(1, "material de BOLT_M64", _circ[1], "F1554_G36")
auditar(1, "diametro de BOLT_M64", round(_circ[2] * MM, 3), D_PERNO)

# NO se cuentan materiales: el modelo en blanco de SAP trae tres por defecto, y
# un contrato que asertara "3 materiales" fallaria sin razon. Se comprueba POR
# NOMBRE, que es lo unico que significa algo.
_lista_mat = list(SapModel.PropMaterial.GetNameList()[1])
for nom, _, _ in MATERIALES:
    auditar(1, "existe el material %s" % nom, nom in _lista_mat, True)

result["paso1"] = {"materiales": [m[0] for m in MATERIALES],
                   "shells": [s[0] for s in SHELLS],
                   "materiales_en_el_modelo": len(_lista_mat),
                   "_nota": "SAP trae 3 materiales por defecto: el conteo absoluto "
                            "no sirve, hay que comprobar por nombre"}


# ═══════════════════════════════════════════════ PASO 2 · contorno de placa

# Los nudos se crean UNA vez y se reutilizan por coordenada. Asi la fusion no es
# algo que uno espera que SAP haga: es una propiedad del constructor.
NUDOS = {}


def pt(x, y, z):
    """Nombre del nudo en (x, y, z) mm. Lo crea si no existe."""
    k = (round(x, 4), round(y, 4), round(z, 4))
    if k not in NUDOS:
        nm = "N%05d" % (len(NUDOS) + 1)
        r = SapModel.PointObj.AddCartesian(x / MM, y / MM, z / MM, "", nm)
        assert ok(r), "AddCartesian %r" % (k,)
        NUDOS[k] = nm
    return NUDOS[k]


def malla(prop, nombre_base, puntos_uv, mapa):
    """Grilla explicita de areas de 4 nudos. `mapa(u, v) -> (x, y, z)`.

    Se construye como grilla y no como area grande dividida despues porque los
    nudos tienen que caer EXACTAMENTE donde apoyan el perno y la cartela. Con la
    grilla la posicion del nudo es un dato de entrada, no un resultado — y no
    hacen falta los indices magicos que aparecen si uno confia en Divide.
    """
    us, vs = puntos_uv
    n = 0
    for i in range(len(us) - 1):
        for j in range(len(vs) - 1):
            esquinas = [mapa(us[i], vs[j]), mapa(us[i + 1], vs[j]),
                        mapa(us[i + 1], vs[j + 1]), mapa(us[i], vs[j + 1])]
            ptos = [pt(*e) for e in esquinas]
            nm = "%s_%03d_%03d" % (nombre_base, i, j)
            assert ok(SapModel.AreaObj.AddByPoint(4, ptos, "", prop, nm)), nm
            n += 1
    return n


n_placa = malla("PLACA", "PL", (EST_X, EST_Y), lambda x, y: (x, y, 0.0))

auditar(2, "areas de placa", n_placa, (len(EST_X) - 1) * (len(EST_Y) - 1))
auditar(2, "nudos en Z = 0", len(NUDOS), len(EST_X) * len(EST_Y))

# Caja envolvente: si un nudo se fue de la placa, el conteo puede seguir dando
# bien y la geometria estar mal.
xs = [k[0] for k in NUDOS]
ys = [k[1] for k in NUDOS]
zs = [k[2] for k in NUDOS]
auditar(2, "X minimo", round(min(xs), 3), -B_PLACA / 2)
auditar(2, "X maximo", round(max(xs), 3), B_PLACA / 2)
auditar(2, "Y minimo", round(min(ys), 3), -L_PLACA / 2)
auditar(2, "Y maximo", round(max(ys), 3), L_PLACA / 2)
auditar(2, "todos los nudos en Z = 0", max(abs(z) for z in zs), 0.0)

# Nudo en CADA linea de control, en los dos signos.
for lx in LINEAS_CONTROL_X:
    for s in ({1} if lx == 0 else {1, -1}):
        auditar(2, "hay estacion X en %+.1f" % (s * lx),
                any(abs(x - s * lx) < 1e-6 for x in EST_X), True)
for ly in LINEAS_CONTROL_Y:
    for s in ({1} if ly == 0 else {1, -1}):
        auditar(2, "hay estacion Y en %+.1f" % (s * ly),
                any(abs(y - s * ly) < 1e-6 for y in EST_Y), True)

# Nudo EXACTO bajo los ocho pernos.
for px in PERNOS_X:
    for py in (Y_PERNO, -Y_PERNO):
        auditar(2, "nudo de placa bajo el perno (%+.0f, %+.0f)" % (px, py),
                (round(px, 4), round(py, 4), 0.0) in NUDOS, True)

# La propiedad, releida area por area.
_mal = 0
for a in list(SapModel.AreaObj.GetNameList()[1]):
    if SapModel.AreaObj.GetProperty(a)[0] != "PLACA":
        _mal += 1
auditar(2, "areas con propiedad distinta de PLACA", _mal, 0)

result["paso2"] = {"areas": n_placa, "nudos_z0": len(NUDOS),
                   "grilla": "%d x %d" % (len(EST_X), len(EST_Y)),
                   "_sin_fusion_habrian_sido": n_placa * 4}


# ═══════════════════════════════════════════════ PASO 3 · stub de columna

# Las estaciones NO se recalculan: se LEEN de la placa ya construida. Asi la
# columna se conecta a los nudos que EXISTEN, no a los que uno cree que existen.
EST_X_ALA = [x for x in EST_X if -X_ALA - 1e-6 <= x <= X_ALA + 1e-6]
EST_Y_ALMA = [y for y in EST_Y if -Y_ALA - 1e-6 <= y <= Y_ALA + 1e-6]

n_col = 0
for y_ala in (Y_ALA, -Y_ALA):
    n_col += malla("ALA", "ALA_%s" % ("P" if y_ala > 0 else "N"),
                   (EST_X_ALA, EST_Z_STUB),
                   (lambda ya: lambda x, z: (x, ya, z))(y_ala))
n_col += malla("ALMA", "ALM", (EST_Y_ALMA, EST_Z_STUB),
               lambda y, z: (0.0, y, z))

auditar(3, "areas de columna", n_col,
        2 * (len(EST_X_ALA) - 1) * N_DIV_STUB + (len(EST_Y_ALMA) - 1) * N_DIV_STUB)

# La que atrapa el error clasico: una columna que se ve apoyada y esta flotando
# sobre nudos duplicados a 1e-9 m de los de la placa.
auditar(3, "nudos en Z = 0 SIN CAMBIOS",
        sum(1 for k in NUDOS if k[2] == 0.0), len(EST_X) * len(EST_Y))

_mal = 0
for a in list(SapModel.AreaObj.GetNameList()[1]):
    p = SapModel.AreaObj.GetProperty(a)[0]
    if a.startswith("ALA_") and p != "ALA":
        _mal += 1
    if a.startswith("ALM_") and p != "ALMA":
        _mal += 1
auditar(3, "areas de columna con propiedad equivocada", _mal, 0)

result["paso3"] = {"areas": n_col, "nudos_totales": len(NUDOS),
                   "nudos_z0": sum(1 for k in NUDOS if k[2] == 0.0),
                   "altura_stub_mm": H_STUB}


# ═══════════════════════════ PASO 4 · cartelas y chapa transversal

# 🔴 Las estaciones Z de la cartela se LEEN de la columna, no se eligen. Con 4
# divisiones propias la cartela quedaria con nudos en 0/75/150/225/300 y la
# columna los tiene en 0/100/200/300: SOLO COINCIDIRIAN EN Z = 0. La cartela
# tocaria el ala unicamente en la base y todo lo de arriba seria un borde libre
# deslizando junto al ala. Se ve perfecta en pantalla y no lanza excepcion.
EST_Z_CART = [z for z in EST_Z_STUB if z <= H_SILLA + 1e-6]
auditar(4, "estaciones Z de cartela leidas de la columna", len(EST_Z_CART), 6)

EST_Y_CART = [y for y in EST_Y if Y_ALA - 1e-6 <= y <= L_PLACA / 2 + 1e-6]
EST_X_TRAN = [x for x in EST_X if X_ALA - 1e-6 <= x <= B_PLACA / 2 + 1e-6]

n_cart = 0
for i, cx in enumerate(CARTELAS_X):
    for sig in (1, -1):
        ys = [sig * y for y in EST_Y_CART]
        n_cart += malla("ATIESADOR", "CART_%d%s" % (i, "P" if sig > 0 else "N"),
                        (ys, EST_Z_CART),
                        (lambda c: lambda y, z: (c, y, z))(cx))

# La chapa transversal NO es un refinamiento: las cartelas de x = +-280 y +-560
# caen FUERA del ala, que solo llega a +-260. Sin ella, media configuracion esta
# colgada — su extremo interior no tendria donde apoyar.
#
# (3) AHORA SUBE HASTA z = H_SILLA, no hasta 300. Antes moria a la altura vieja de
# cartela y dejaba sin cerrar justo el tramo superior, que es por donde la chapa de
# silla entrega la carga de los pernos de x = +-420 —los dos que quedan FUERA del
# ancho del ala y cuyo unico camino a la columna pasa por aca—.
n_tran = 0
for sx in (1, -1):
    for sy in (1, -1):
        xs_t = [sx * x for x in EST_X_TRAN]
        n_tran += malla("ATIESADOR", "TRAN_%s%s" % ("P" if sx > 0 else "N",
                                                    "P" if sy > 0 else "N"),
                        (xs_t, EST_Z_CART),
                        (lambda s: lambda x, z: (x, s * Y_ALA, z))(sy))

auditar(4, "areas de cartela", n_cart,
        len(CARTELAS_X) * 2 * (len(EST_Y_CART) - 1) * (len(EST_Z_CART) - 1))
auditar(4, "areas de chapa transversal", n_tran,
        4 * (len(EST_X_TRAN) - 1) * (len(EST_Z_CART) - 1))


def familias_por_nudo():
    """nudo -> {familia de cada area que lo toca}.

    Dos chapas que se cruzan NO estan unidas porque sus coordenadas coincidan:
    lo estan cuando COMPARTEN NUDO. Y comprobar que "existe un nudo ahi" no lo
    demuestra —lo crea la propia chapa que se esta auditando, y el chequeo se
    verifica contra si mismo—: hay que comprobar QUIEN MAS lo toca.
    """
    inv = {v: k for k, v in NUDOS.items()}
    m = {}
    for a in list(SapModel.AreaObj.GetNameList()[1]):
        fam = a.split("_")[0]
        for p in list(SapModel.AreaObj.GetPoints(a)[1]):
            c = inv.get(p)
            if c is not None:
                m.setdefault(c, set()).add(fam)
    return m


FAM = familias_por_nudo()


def fam_en(x, y, z):
    return FAM.get((round(x, 4), round(y, 4), round(z, 4)), set())


for z in EST_Z_CART:
    # cartela de x = 0: apoya en el ALA, que llega hasta x = +-260
    auditar(4, "union ALA+CART en (0, 734, %.0f)" % z,
            {"ALA", "CART"} <= fam_en(0.0, Y_ALA, z), True)
    # cartelas de x = +-280 y +-560: apoyan en la chapa TRANSVERSAL
    for cx in (280.0, 560.0, -280.0, -560.0):
        auditar(4, "union CART+TRAN en (%+.0f, 734, %.0f)" % (cx, z),
                {"CART", "TRAN"} <= fam_en(cx, Y_ALA, z), True)

# En Z = 0 las tres tienen que compartir el nudo con la PLACA.
auditar(4, "union ALA+CART+PLACA en (0, 734, 0)",
        {"ALA", "CART", "PL"} <= fam_en(0.0, Y_ALA, 0.0), True)
auditar(4, "union CART+TRAN+PLACA en (280, 734, 0)",
        {"CART", "TRAN", "PL"} <= fam_en(280.0, Y_ALA, 0.0), True)

result["paso4"] = {"areas_cartela": n_cart, "areas_transversal": n_tran,
                   "estaciones_z": EST_Z_CART, "nudos_totales": len(NUDOS)}


# ══════════════════════════════════════════════ PASO 5 · silla y pernos

# ---- 5a · chapa superior de silla ------------------------------------------
# Una sola chapa por fila, cubriendo los cuatro pernos: configuracion de BOTA,
# mas simple y mas rigida que cuatro sillas sueltas.
#
# (1) LA CHAPA ARRANCA EN EL ALA, no a mitad del voladizo. Antes iba de y = 1.102,6
# a 1.400: estaba sobre el EXTREMO LIBRE, donde el momento del voladizo es cero, y
# NO EXISTIA en el empotramiento (y = 734), donde es maximo. Es el peor lugar
# posible para el ala de una viga en voladizo — 369 mm sin ala superior justo donde
# se necesita. Ahora cubre los 666 mm completos.
EST_Y_SILLA = [y for y in EST_Y if Y_ALA - 1e-6 <= y <= L_PLACA / 2 + 1e-6]
auditar(5, "la silla cubre la fila de pernos",
        min(EST_Y_SILLA) < Y_PERNO < max(EST_Y_SILLA), True)
auditar(5, "la silla ARRANCA en la cara del ala", round(min(EST_Y_SILLA), 4), Y_ALA)

n_silla = 0
for sig in (1, -1):
    ys = [sig * y for y in EST_Y_SILLA]
    n_silla += malla("SILLA", "SIL_%s" % ("P" if sig > 0 else "N"),
                     (EST_X, ys), lambda x, y: (x, y, Z_SILLA))
auditar(5, "areas de silla", n_silla,
        2 * (len(EST_X) - 1) * (len(EST_Y_SILLA) - 1))

# ---- 5a-bis · atiesador de CONTINUIDAD ------------------------------------
# (2) La silla entrega su carga al ala a z = H_SILLA. Entre las dos alas no habia
# NADA que la recibiera, asi que el ala de 32 mm tenia que flexar fuera de su plano
# para equilibrarla. Este atiesador es la CONTINUACION LITERAL de la chapa de
# silla a traves de la columna: mismo plano X-Y, misma cota z, de ala a ala. Cierra
# el par de fuerzas DENTRO de la columna.
#
# Va PARTIDO POR EL ALMA sin que haya que partirlo a mano: la malla incluye la
# estacion x = 0, asi que las dos mitades comparten los nudos del alma.
n_cont = malla("CONTIN", "CONT", (EST_X_ALA, EST_Y_ALMA),
               lambda x, y: (x, y, Z_SILLA))
auditar(5, "areas de atiesador de continuidad", n_cont,
        (len(EST_X_ALA) - 1) * (len(EST_Y_ALMA) - 1))

FAM = familias_por_nudo()
_uniones = 0
for cx in CARTELAS_X:
    for sig in (1, -1):
        for y in EST_Y_SILLA:
            auditar(5, "silla apoya en cartela (%+.0f, %+.1f, %.0f)"
                    % (cx, sig * y, Z_SILLA),
                    {"CART", "SIL"} <= fam_en(cx, sig * y, Z_SILLA), True)
            _uniones += 1

# El nudo que prueba que los cinco elementos concurren donde tienen que concurrir.
# Si alguno faltara, el modelo se veria identico en pantalla.
auditar(5, "nudo de cinco familias en (0, 734, %.0f)" % Z_SILLA,
        {"ALA", "ALM", "SIL", "CONT", "CART"} <= fam_en(0.0, Y_ALA, Z_SILLA), True)

# La silla entra al ala en TODO el ancho del ala, no solo en un punto.
for x in EST_X_ALA:
    for sig in (1, -1):
        auditar(5, "silla + ala + continuidad en (%+.0f, %+.0f, %.0f)"
                % (x, sig * Y_ALA, Z_SILLA),
                {"ALA", "SIL", "CONT"} <= fam_en(x, sig * Y_ALA, Z_SILLA), True)

# Y fuera del ancho del ala la que recibe a la silla es la chapa TRANSVERSAL,
# que por eso tuvo que subir hasta esta cota.
for x in (280.0, 420.0, 560.0, -280.0, -420.0, -560.0):
    for sig in (1, -1):
        auditar(5, "silla + transversal en (%+.0f, %+.0f, %.0f)"
                % (x, sig * Y_ALA, Z_SILLA),
                {"TRAN", "SIL"} <= fam_en(x, sig * Y_ALA, Z_SILLA), True)

# El atiesador de continuidad tiene que compartir nudo con el ALMA en toda su
# longitud: si no, es una chapa apoyada en el aire dentro de la columna.
for y in EST_Y_ALMA:
    auditar(5, "continuidad + alma en (0, %+.1f, %.0f)" % (y, Z_SILLA),
            {"CONT", "ALM"} <= fam_en(0.0, y, Z_SILLA), True)

# ---- 5b · la geometria del perno, que la auditoria automatica NO ve ---------
# Lo encontro el ingeniero mirando el render: con las cartelas EN las lineas de
# perno, el perno atravesaria la chapa —imposible de construir— y su traccion
# bajaria directo por la cartela, con lo que la silla no flexaria y dejaria de
# hacer lo unico que hace. La conectividad era correcta; la configuracion no.
for px in PERNOS_X:
    auditar(5, "el perno %+.0f no cae sobre una cartela" % px,
            min(abs(px - c) for c in CARTELAS_X) > 1.0, True)
    izq = max(c for c in CARTELAS_X if c < px)
    der = min(c for c in CARTELAS_X if c > px)
    auditar(5, "el perno %+.0f esta CENTRADO en su vano" % px,
            round(abs(px - (izq + der) / 2.0), 6), 0.0)

# Los minimos del ACI, con el valor LEIDO el 2026-08-27 (Tabla 17.9.2(a),
# columna "Cast-in anchors / Not torqued", impresa 294).
_sep = min(PERNOS_X[i + 1] - PERNOS_X[i] for i in range(len(PERNOS_X) - 1))
auditar(5, "separacion entre pernos >= 4 d_a", _sep, 4 * D_PERNO, ">=")

# ---- 5c · los pernos --------------------------------------------------------
PERNOS = []
for px in PERNOS_X:
    for py in (Y_PERNO, -Y_PERNO):
        nm = "BOLT_%+05d_%+05d" % (px, py)
        p_sup = pt(px, py, Z_SILLA)
        p_inf = pt(px, py, Z_ANCLAJE)
        assert ok(SapModel.FrameObj.AddByPoint(p_sup, p_inf, "", "BOLT_M64", nm)), nm

        # 🔴 Un frame que atraviesa una malla SE SUELDA A ELLA salvo que se le
        # prohiba explicitamente. El perno pasa por los nudos de cartela en
        # z = 200 y 100 y por el de placa en z = 0: sin esto queda soldado a la
        # cartela en toda su altura y a la placa, lo que ANULA LA SILLA POR
        # COMPLETO —la traccion iria directo a la placa en vez de subir a la
        # silla, que es exactamente lo contrario de lo que una silla existe para
        # hacer—. No lanza excepcion y se ve identico en pantalla.
        assert ok(SapModel.FrameObj.SetAutoMesh(nm, False, False, False, 0, 0.0, 0)), nm

        # El perno solo trabaja a traccion.
        assert ok(SapModel.FrameObj.SetTCLimits(nm, True, 0.0, False, 0.0, 0)), nm

        # Empotramiento de traslacion en el extremo inferior. VA DECLARADO: es lo
        # que hoy sostiene lateralmente el modelo, porque los resortes del paso 6
        # son solo verticales. Cuando se aplique el corte iria entero a los
        # pernos, y eso contradice el diseno con llave de corte del DSC §7.10.
        assert ok(SapModel.PointObj.SetRestraint(
            p_inf, [True, True, True, False, False, False])), p_inf
        PERNOS.append(nm)

auditar(5, "objetos frame", SapModel.FrameObj.Count(), len(PERNOS_X) * 2)

# El conteo de OBJETOS no delata el automesh: FrameObj.Count() dice 8 en los dos
# casos. Hay que contar ELEMENTOS, y para eso hay que armar el modelo de
# analisis primero.
assert ok(SapModel.Analyze.CreateAnalysisModel()), "CreateAnalysisModel"
auditar(5, "ELEMENTOS de linea (8 = un elemento por perno; 32 = soldado)",
        SapModel.LineElm.Count(), len(PERNOS))

L_NOMINAL = (Z_SILLA - Z_ANCLAJE) / MM
_largos = []
for le in list(SapModel.LineElm.GetNameList()[1]):
    p1, p2 = SapModel.LineElm.GetPoints(le)[:2]
    c1 = SapModel.PointElm.GetCoordCartesian(p1, 0.0, 0.0, 0.0)[:3]
    c2 = SapModel.PointElm.GetCoordCartesian(p2, 0.0, 0.0, 0.0)[:3]
    _largos.append(round(math.dist(c1, c2), 6))
auditar(5, "todos los elementos con el largo nominal del perno",
        sorted(set(_largos)), [round(L_NOMINAL, 6)])

result["paso5"] = {"areas_silla": n_silla, "areas_continuidad": n_cont,
                   "uniones_silla_cartela": _uniones,
                   "silla_de_y": [min(EST_Y_SILLA), max(EST_Y_SILLA)],
                   "altura_silla_mm": H_SILLA,
                   "pernos": len(PERNOS), "elementos_de_linea": SapModel.LineElm.Count(),
                   "largo_perno_m": L_NOMINAL,
                   "separacion_mm": _sep, "minimo_4d_mm": 4 * D_PERNO,
                   "_L_ANC_es_inferido": "z = -900 mm: el h_ef real sale del Cap. 17 del "
                                         "ACI, que todavia no esta leido. Afecta la "
                                         "rigidez axial del perno y por lo tanto el reparto"}


# ═══════════════════════════════════════════════════════════ CIERRE Y ESTADO

_le_antes = SapModel.LineElm.Count()

assert ok(SapModel.File.Save(ARCHIVO)), "Save final"
auditar(9, "unidades tras el Save final", SapModel.GetPresentUnits(), UNIDADES)

# 🔴 EL CONTRASTE DEL AUTOMESH CADUCA AL GRABAR. `File.Save` descarta el modelo
# de analisis, asi que `LineElm.Count()` pasa de 8 a 0. La comprobacion que
# atrapa el perno soldado a la malla —la del paso 5— SOLO VALE ANTES DEL SAVE:
# corrida despues devuelve 0, o sea falla por la razon equivocada y manda a
# buscar un defecto que no existe. Se mide antes y se declara el despues.
_le_despues = SapModel.LineElm.Count()
auditar(9, "el Save descarta el modelo de analisis (LineElm 8 -> 0)",
        (_le_antes, _le_despues), (len(PERNOS), 0))

result["estado"] = {
    "areas": SapModel.AreaObj.Count(),
    "nudos": SapModel.PointObj.Count(),
    "frames": SapModel.FrameObj.Count(),
    "elementos_de_linea_ANTES_del_save": _le_antes,
    "elementos_de_linea_DESPUES_del_save": _le_despues,
    "nudos_z0": sum(1 for k in NUDOS if k[2] == 0.0),
    "unidades": SapModel.GetPresentUnits(),
    "archivo": SapModel.GetModelFilename(True),
    "_ojo": "LineElm vuelve a 0 al grabar: el modelo de analisis se descarta. El "
            "chequeo del automesh hay que hacerlo ANTES del Save, siempre.",
}
result["auditorias"] = AUD
result["auditorias_resumen"] = {
    "total": len(AUD), "pasan": sum(1 for a in AUD if a["pasa"]),
    "fallan": sum(1 for a in AUD if not a["pasa"]),
}
result["pendiente"] = ["6 · resortes de hormigon", "7 · cargas",
                       "8 · auditoria final y analisis"]
