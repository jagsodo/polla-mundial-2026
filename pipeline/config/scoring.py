"""Reglas de puntaje de la polla. Configurable por si cambian los valores.

Puntos ACUMULABLES por partido:
  - Acertar el resultado 1X2 (ganador o empate): +5
  - Acertar el marcador exacto:                  +2
  - Acertar la diferencia de goles:              +1
Marcador exacto => 5+2+1 = 8.
Segunda ronda (eliminatorias): puntaje DOBLE.
Solo aplican los 90 minutos reglamentarios (+ reposición).
"""

VALORES = {
    "resultado": 5,   # acertar 1X2
    "marcador": 2,    # acertar goles exactos de cada equipo
    "diferencia": 1,  # acertar la diferencia de goles
}

MULTIPLICADOR_RONDA = {
    "grupos": 1,
    "eliminatorias": 2,
}


def _signo(h: int, a: int) -> int:
    return (h > a) - (h < a)


def puntos(pred: tuple, real: tuple, ronda: str = "grupos") -> int:
    """Puntos obtenidos por un pronóstico `pred=(gh, ga)` frente al resultado
    real `real=(gh, ga)` de los 90 minutos, según las reglas de la polla."""
    ph, pa = pred
    rh, ra = real
    pts = 0
    if _signo(ph, pa) == _signo(rh, ra):
        pts += VALORES["resultado"]
    if ph == rh and pa == ra:
        pts += VALORES["marcador"]
    if (ph - pa) == (rh - ra):
        pts += VALORES["diferencia"]
    return pts * MULTIPLICADOR_RONDA[ronda]


def puntos_esperados(pred: tuple, matriz, ronda: str = "grupos") -> float:
    """E[puntos(pred)] = sum_real P(real) * puntos(pred, real).

    `matriz[h][a]` = probabilidad de que el marcador real sea h-a.
    """
    e = 0.0
    n_h = len(matriz)
    n_a = len(matriz[0])
    for rh in range(n_h):
        for ra in range(n_a):
            p = matriz[rh][ra]
            if p > 0:
                e += p * puntos(pred, (rh, ra), ronda)
    return e


def mejor_pronostico(matriz, ronda: str = "grupos", max_goles: int = 7):
    """Devuelve (pred, esperanza) que maximiza los puntos esperados,
    recorriendo todos los marcadores candidatos 0..max_goles."""
    mejor, mejor_e = (1, 0), -1.0
    for ph in range(max_goles + 1):
        for pa in range(max_goles + 1):
            e = puntos_esperados((ph, pa), matriz, ronda)
            if e > mejor_e:
                mejor, mejor_e = (ph, pa), e
    return mejor, mejor_e
