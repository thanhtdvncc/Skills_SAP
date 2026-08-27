# -*- coding: utf-8 -*-
"""
verificar_placabase_fe — autochequeo de la teoria de placa, sin SAP2000.

Cada asercion lleva al lado el calculo que la respalda, para poder rehacerlo
con lapiz si algo cambia. Sigue el patron de cirsoc/verificar_cirsoc.py.

    python verificar_placabase_fe.py

Codigos de salida: 0 todo bien · 1 algun chequeo fallo.
"""
import sys

import teoria_placa as tp

FALLOS = []


def chk(etiqueta, obtenido, esperado, tol=1e-3):
    if isinstance(esperado, float):
        ok = abs(obtenido - esperado) <= tol * max(1.0, abs(esperado))
    else:
        ok = obtenido == esperado
    marca = "OK  " if ok else "FALLA"
    print("  [%s] %-56s %r" % (marca, etiqueta, obtenido)
          + ("" if ok else "   esperado %r" % (esperado,)))
    if not ok:
        FALLOS.append(etiqueta)


print("\n1. Casos con solucion conocida — validan la serie de Navier")
# Placa cuadrada simplemente apoyada, nu = 0,3: el coeficiente clasico de la
# teoria de placas delgadas es 0,0479. Es el chequeo que ancla la escala.
chk("placa cuadrada, nu=0,3: beta = 0,0479", tp.beta_lado_corto(1.0, nu=0.3), 0.0479, 2e-3)
chk("placa cuadrada: beta_x == beta_y por simetria",
    round(tp.navier(1.0, 1.0, 1.0, nu=0.3)["beta_x"], 9),
    round(tp.navier(1.0, 1.0, 1.0, nu=0.3)["beta_y"], 9))

# Al alargarse indefinidamente la placa degenera en viga simplemente apoyada
# de luz igual al lado corto: M = q*a^2/8 = 0,125*q*a^2. Es el chequeo que
# ancla el otro extremo del rango.
chk("b/a -> infinito: beta -> 1/8 = 0,125", tp.beta_lado_corto(400.0, nu=0.3), 0.125, 2e-3)
chk("b/a -> infinito con nu=0: mismo limite", tp.beta_lado_corto(400.0, nu=0.0), 0.125, 2e-3)

# nu no puede cambiar el limite de viga, porque una franja aislada no tiene
# curvatura transversal que acoplar.
chk("relacion 2,0, nu=0,3", tp.beta_lado_corto(2.0, nu=0.3), 0.1017, 3e-3)

print("\n2. Monotonia y coherencia interna")
seq = [tp.beta_lado_corto(r) for r in (1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 3.0, 5.0)]
chk("beta_x crece con la relacion de lados", all(b < c for b, c in zip(seq, seq[1:])), True)
chk("beta_x siempre por debajo del limite de viga", max(seq) < 0.1251, True)
chk("beta con nu=0,3 mayor que con nu=0 (acople de curvaturas)",
    tp.beta_lado_corto(1.8, nu=0.3) > tp.beta_lado_corto(1.8, nu=0.0), True)
chk("la escala no cambia beta (adimensional)",
    round(tp.navier(0.192, 0.350, 19012.0)["beta_x"], 9),
    round(tp.navier(192.0, 350.0, 1.0)["beta_x"], 9))

print("\n3. Convergencia de la serie")
b_51 = tp.beta_lado_corto(1.82, n_terminos=51)
b_201 = tp.beta_lado_corto(1.82, n_terminos=201)
b_401 = tp.beta_lado_corto(1.82, n_terminos=401)
chk("51 vs 201 terminos difieren menos de 0,5 %", abs(b_51 / b_201 - 1) < 5e-3, True)
chk("201 vs 401 terminos difieren menos de 0,1 %", abs(b_401 / b_201 - 1) < 1e-3, True)

print("\n4. El caso de El Pachon — panel entre nervios de la placa base rev. 4")
# Panel de 350 (voladizo) x 192 (luz entre nervios), presion de aplastamiento
# f_p = 19 012 kPa. La memoria adopta beta = 0,080 sin leerlo de tabla.
A, B, Q = 0.192, 0.350, 19012.0
FY, PHI = 248200.0, 0.90
r = tp.navier(A, B, Q)
chk("relacion de lados del panel", round(r["relacion"], 3), 1.823, 1e-3)
beta_navier = r["beta_x"]
chk("beta por Navier, apoyo simple", round(beta_navier, 4), 0.0956, 5e-3)

M_adoptado = 0.080 * Q * A ** 2
M_navier = r["Mx"]
t_adoptado = tp.espesor_requerido(M_adoptado, FY, PHI)
t_navier = tp.espesor_requerido(M_navier, FY, PHI)
chk("t requerido con beta = 0,080 [mm]", round(t_adoptado * 1000, 1), 31.7, 5e-3)
chk("t requerido con beta de Navier [mm]", round(t_navier * 1000, 1), 34.7, 1e-2)
chk("el beta adoptado subestima el momento", beta_navier > 0.080, True)
chk("uso de la chapa de 35 mm con el beta de Navier",
    round(t_navier / 0.035, 3), 0.991, 2e-2)

print()
print("  LECTURA: con apoyo simple en los cuatro bordes —hipotesis conservadora—")
print("  la chapa de 35 mm queda al %.2f. No falla, pero el margen que sugeria" % (t_navier / 0.035))
print("  el beta = 0,080 no existe. El apoyo real da empotramiento parcial en el")
print("  ala y en los nervios, que baja el momento en el centro: el valor que")
print("  gobierna esta ENTRE el de placa empotrada y este. Lo mide el FE.")

print("\n" + "=" * 70)
if FALLOS:
    print("FALLARON %d chequeos:" % len(FALLOS))
    for f in FALLOS:
        print("  - %s" % f)
    sys.exit(1)
print("Todo verificado.")
