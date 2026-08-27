# -*- coding: utf-8 -*-
"""
teoria_placa — solucion analitica de placa delgada rectangular, sin SAP.

POR QUE EXISTE
--------------
El espesor de una placa base rigidizada se dimensiona tratando el panel entre
nervios como una placa apoyada en sus cuatro bordes:

    M = beta * q * a^2          (a = lado corto)

y el `beta` se toma de una tabla. Una memoria de calculo de El Pachon adopto
beta = 0,080 "por orden de magnitud, no leido de tabla", y de ese coeficiente
cuelga el espesor de la chapa. Este modulo calcula el beta EXACTO en vez de
transcribirlo, resolviendo la placa por la serie de Navier.

Que se gana contra una tabla: el valor sale para la relacion de lados y el
coeficiente de Poisson REALES del caso, no interpolado entre filas, y es
reproducible con lapiz. Y sirve de referencia para validar una malla de
elementos finitos, que es el uso principal: si el modelo no reproduce esta
solucion, no hay derecho a creerle cuando se lo lleve al panel real, cuyas
condiciones de borde no tienen solucion cerrada.

LO QUE ESTE MODULO NO ES
------------------------
La solucion de Navier vale para placa SIMPLEMENTE APOYADA en los cuatro bordes.
El panel real de una placa base no lo esta: el ala de la columna y los nervios
dan un empotramiento parcial que reduce el momento en el centro y lo lleva a
los bordes. Por eso el beta de Navier es una COTA SUPERIOR del caso real, y el
FE es el que tiene que medir el caso real.

CONVENIO
--------
  a = lado CORTO, b = lado largo, en las mismas unidades
  q = presion uniforme
  M sale en fuerza*longitud por unidad de ancho
  beta_x se refiere al momento que flexiona la placa en la direccion CORTA,
  que es el que gobierna el espesor.

Ejecutar:  python teoria_placa.py
"""
import math


def navier(a, b, q, nu=0.3, n_terminos=201):
    """Placa rectangular simplemente apoyada en 4 bordes, carga uniforme q.

    Serie de Navier. Devuelve un dict con los momentos en el centro y la
    flecha maxima, mas los beta adimensionales referidos al lado corto.

    a : lado corto · b : lado largo · nu : coeficiente de Poisson
    n_terminos : mayor impar considerado en cada direccion.

    La serie converge como 1/(m*n*(...)^2); con 201 el residuo esta muy por
    debajo de la cuarta cifra, que es lo que se necesita para dimensionar una
    chapa en multiplos de 5 mm.
    """
    if a > b:
        a, b = b, a
    Mx = My = w_coef = 0.0
    for m in range(1, n_terminos + 1, 2):
        for n in range(1, n_terminos + 1, 2):
            # sin(m*pi/2) = +-1 para m impar
            s = ((-1) ** ((m - 1) // 2)) * ((-1) ** ((n - 1) // 2))
            km = (m / a) ** 2
            kn = (n / b) ** 2
            den = m * n * (km + kn) ** 2
            Mx += s * (km + nu * kn) / den
            My += s * (kn + nu * km) / den
            w_coef += s / (m * n * (km + kn) ** 2)
    f = 16.0 * q / (math.pi ** 4)
    Mx *= f
    My *= f
    return {
        "a": a, "b": b, "relacion": b / a, "nu": nu,
        "Mx": Mx,                      # flexiona en la direccion CORTA
        "My": My,
        "beta_x": Mx / (q * a ** 2),
        "beta_y": My / (q * a ** 2),
        "w_coef_x_qa4_sobre_D": 16.0 * w_coef / (math.pi ** 6) / (a ** 4),
    }


def beta_lado_corto(relacion, nu=0.3, n_terminos=201):
    """beta tal que M_max = beta * q * a^2, con a el lado corto.

    Depende SOLO de la relacion de lados y de nu, no de la escala.
    """
    return navier(1.0, float(relacion), 1.0, nu=nu, n_terminos=n_terminos)["beta_x"]


def espesor_requerido(M_lineal, Fy, phi=0.90):
    """Espesor de chapa por flexion plastica, momento por unidad de ancho.

    Z de una franja de ancho unitario = t^2/4, de donde
        phi * Fy * t^2/4 >= M   ->   t = raiz(4M/(phi*Fy))
    Unidades coherentes: M en kN.m/m y Fy en kPa dan t en m.
    """
    return math.sqrt(4.0 * M_lineal / (phi * Fy))


if __name__ == "__main__":
    print("=" * 74)
    print("beta para placa simplemente apoyada en 4 bordes, carga uniforme")
    print("M_max = beta * q * a^2   con a = lado corto   ·   nu = 0,30")
    print("=" * 74)
    print("  %-12s %12s %12s %12s" % ("b/a", "beta_x", "beta_y", "beta_x(nu=0)"))
    print("  " + "-" * 60)
    for rel in (1.0, 1.2, 1.4, 1.6, 1.8, 1.82, 2.0, 2.5, 3.0, 5.0, 100.0):
        bx = beta_lado_corto(rel, nu=0.3)
        by = navier(1.0, rel, 1.0, nu=0.3)["beta_y"]
        b0 = beta_lado_corto(rel, nu=0.0)
        print("  %-12.2f %12.5f %12.5f %12.5f" % (rel, bx, by, b0))
    print()
    print("  Comprobacion de la implementacion: para b/a -> infinito la placa")
    print("  degenera en viga simplemente apoyada de luz a, con M = q*a^2/8 =")
    print("  0,125*q*a^2. El valor de la ultima fila debe tender a 0,125.")
