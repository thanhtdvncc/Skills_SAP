# -*- coding: utf-8 -*-
"""
teoria_winkler — placa RIGIDA sobre lecho elastico, con y sin despegue.

POR QUE EXISTE
--------------
Es la referencia contra la que se validan las capas 1 y 2 del modelo de placa
base: si el modelo de elementos finitos no reproduce estas dos soluciones
cerradas cuando se le da una placa artificialmente rigida, no hay derecho a
creerle nada cuando se le baje al espesor real y se le agreguen pernos.

Las dos soluciones son clasicas y no dependen del modulo de balasto en la
distribucion de presiones — solo en el asentamiento. Eso las hace buenas
pruebas: si el modelo acierta la presion pero falla el asentamiento, el error
esta en k_s; si falla la presion, el error esta en la geometria o en el sentido
del resorte.

CONVENIO
--------
  L = largo de la placa en la direccion del momento
  B = ancho
  P = axial, compresion POSITIVA
  M = momento, valor absoluto
  e = M/P excentricidad
  Presiones positivas en compresion.

QUE BORDE SE COMPRIME — verificado contra SAP2000 el 2026-08-19
---------------------------------------------------------------
Un momento **Mx positivo** (vector segun la regla de la mano derecha sobre el
eje X global) rota de +Y hacia +Z: **levanta el borde +Y y comprime el borde
-Y**. Este modulo devuelve magnitudes, no dice en que borde caen; al comparar
contra un modelo hay que asignarlas mirando el signo del momento aplicado.

No es un detalle menor. En la primera corrida de la capa 1 los valores del
modelo y de la teoria coincidian dentro del 0,5 % pero aparecian intercambiados
de borde, lo que a primera vista se lee como un error del modelo y no lo era.

EL LIMITE DEL NUCLEO CENTRAL
----------------------------
  e <= L/6  ->  toda la placa comprimida, distribucion trapecial (o triangular
                justo en e = L/6). Vale la formula de flexion compuesta.
  e >  L/6  ->  la placa DESPEGA. Solo una franja de longitud a = 3*(L/2 - e)
                queda en contacto, con distribucion triangular.

La segunda es la que importa para una placa base con gran excentricidad, y es
la que el bloque RECTANGULAR de la AISC Design Guide 1 sustituye por una
idealizacion. No son la misma cosa y no tienen por que dar lo mismo: esta
supone material elastico sin tope de tension, y la DG1 supone plastificacion
completa a la presion admisible.

Ejecutar:  python teoria_winkler.py
"""


def sin_despegue(P, M, L, B):
    """Flexion compuesta, valida mientras e <= L/6.

    Devuelve presiones en los dos bordes y en el centro.
    """
    A = L * B
    W = B * L ** 2 / 6.0          # modulo resistente de la huella
    p_med = P / A
    dp = M / W
    return {
        "p_max": p_med + dp,
        "p_min": p_med - dp,
        "p_medio": p_med,
        "e": (M / P) if P else float("inf"),
        "e_limite": L / 6.0,
        "despega": (M / P if P else 1e9) > L / 6.0,
        "longitud_contacto": L,
    }


def con_despegue(P, M, L, B):
    """Placa rigida que despega: contacto triangular sobre a = 3*(L/2 - e).

    El equilibrio de una cuna triangular de longitud a y ancho B con
    resultante P exige p_max = 2P/(B*a), y que la resultante caiga a a/3 del
    borde, o sea a L/2 - e del centro. De ahi a = 3*(L/2 - e).
    """
    e = M / P
    a = 3.0 * (L / 2.0 - e)
    if a <= 0:
        raise ValueError("excentricidad fuera de la placa: no hay equilibrio "
                         "sin anclaje (e = %.4f, L/2 = %.4f)" % (e, L / 2.0))
    p_max = 2.0 * P / (B * a)
    return {
        "p_max": p_max,
        "p_min": 0.0,
        "e": e,
        "e_limite": L / 6.0,
        "despega": True,
        "longitud_contacto": a,
        "fraccion_en_contacto": a / L,
        "brazo_resultante": L / 2.0 - a / 3.0,
    }


def resolver(P, M, L, B):
    """Elige la rama que corresponde y devuelve el resultado."""
    if P <= 0:
        raise ValueError("con axial nula o de traccion no hay contacto: el "
                         "equilibrio lo tienen que dar los pernos")
    e = M / P
    return con_despegue(P, M, L, B) if e > L / 6.0 else sin_despegue(P, M, L, B)


def asentamiento_medio(P, L, B, ks):
    """Descenso de una placa rigida con carga centrada: d = p/ks."""
    return P / (L * B) / ks


def rigidez_rotacional(L, B, ks):
    """Rigidez rotacional de una placa rigida sobre lecho elastico, SIN
    despegue: K = M/theta = ks * I_huella, con I = B*L^3/12.

    Es la cota superior de la rigidez de base: cualquier despegue, y la
    flexibilidad de la placa y de los pernos, solo pueden bajarla.
    """
    return ks * B * L ** 3 / 12.0


if __name__ == "__main__":
    # Placa base de El Pachon, rev. 4
    L, B = 1.700, 0.950
    KS = 56664.0          # kN/m3, el que corresponde a B = 4,00 m

    print("=" * 74)
    print("Placa rigida sobre lecho elastico — placa base rev. 4")
    print("L = %.3f m · B = %.3f m · nucleo central e <= L/6 = %.4f m"
          % (L, B, L / 6.0))
    print("=" * 74)
    print("  %-34s %10s %10s %10s %9s" %
          ("Caso", "e [m]", "p_max[kPa]", "contacto", "despega"))
    print("  " + "-" * 78)
    casos = [
        ("Axial pura, P = 2000 kN", 2000.0, 0.0),
        ("e = L/12, dentro del nucleo", 2000.0, 2000.0 * L / 12.0),
        ("e = L/6, justo en el limite", 2000.0, 2000.0 * L / 6.0),
        ("e = L/4, despega", 2000.0, 2000.0 * L / 4.0),
        ("Aplastamiento real, nudo 12", 1269.4, 4859.1),
    ]
    for nom, P, M in casos:
        try:
            r = resolver(P, M, L, B)
            print("  %-34s %10.4f %10.1f %10.3f %9s"
                  % (nom, r["e"], r["p_max"], r["longitud_contacto"],
                     "si" if r["despega"] else "no"))
        except ValueError as exc:
            print("  %-34s %s" % (nom, exc))
    print()
    print("  Rigidez rotacional sin despegue, ks = %.0f kN/m3:" % KS)
    print("    K = ks*B*L^3/12 = %.0f kN.m/rad" % rigidez_rotacional(L, B, KS))
    print()
    print("  El ultimo caso es el que gobierna el aplastamiento de la memoria.")
    print("  Su excentricidad, %.3f m, es MAYOR que L/2 = %.3f: sin pernos no"
          % (4859.1 / 1269.4, L / 2.0))
    print("  hay equilibrio posible. Es la prueba de que el anclaje no es un")
    print("  refuerzo sino el mecanismo, y de que la capa 2 del modelo no puede")
    print("  verificarse con el caso real: hay que bajar la excentricidad.")
