"""
core/deck_match.py
------------------
Cálculo EXACTO (sin Monte Carlo) de un deck match 3on3 de Beyblade X.

Formato (confirmado):
  - Cada jugador tiene 3 beys y elige un orden a la vez y a ciegas (ve las
    piezas del rival, no su orden).
  - Combate k: bey k de A contra bey k de B. Tras cada combate AMBOS pasan al
    siguiente, gane quien gane.
  - Gana quien llega antes a 4 puntos (puede acabar a mitad de ronda).
  - Si tras los 3 combates nadie tiene 4, ambos eligen un orden NUEVO
    conociendo el marcador, y se repite.
  - No hay empates. Spin = 1 punto, Burst/Over = 2, Xtreme = 3.

Modelo:
  - Estado = marcador (sa, sb) al inicio de una ronda, con sa, sb < 4.
  - Cada ronda es un juego de suma cero 6x6 (órdenes de A x órdenes de B),
    cuyo pago es P(A gana la partida). Se resuelve por programación lineal
    (estrategias mixtas) y por inducción hacia atrás sobre el marcador:
    cada ronda sin ganador suma al menos 3 puntos, así que el marcador
    siempre avanza.
  - P(A_i gana a B_j) viene de `prob_fn(a, b)` (intercambiable; ver punto 8).
  - Puntos cuando A_i gana a B_j: la media entre los puntos por victoria de
    A_i y los puntos que cede B_j, repartida entre los dos enteros más
    cercanos (1,27 -> 73 % de 1 punto y 27 % de 2). Es una suposición: solo
    tenemos medias, no el desglose de finishes.
"""

from itertools import permutations

import numpy as np
from scipy.optimize import linprog

OBJETIVO = 4
ORDENES = list(permutations(range(3)))   # 6 órdenes posibles


# ── Puntos por combate ────────────────────────────────────────────────────────

def distribucion_puntos(media):
    """Reparte una media de puntos en {1,2,3} entre los dos enteros más cercanos."""
    m = float(np.clip(media if media == media else 1.0, 1.0, 3.0))  # NaN -> 1
    lo = int(np.floor(m))
    if lo >= 3:
        return {3: 1.0}
    frac = m - lo
    d = {lo: 1.0 - frac}
    if frac > 0:
        d[lo + 1] = frac
    return d


def _pts_media(ganador, perdedor):
    vals = [v for v in (ganador.get("pts_ganados"), perdedor.get("pts_cedidos"))
            if v is not None and v == v and v > 0]
    return float(np.mean(vals)) if vals else 1.0


# ── Juego de suma cero ────────────────────────────────────────────────────────

def resolver_matriz(M):
    """
    Resuelve max_x min_y x^T M y (A maximiza). Devuelve (valor, x, y).
    """
    M = np.asarray(M, dtype=float)
    n, m = M.shape
    # Estrategia de A: max v  s.a.  M^T x >= v,  sum x = 1,  x >= 0
    c = np.zeros(n + 1); c[-1] = -1.0
    A_ub = np.hstack([-M.T, np.ones((m, 1))])
    A_eq = np.hstack([np.ones((1, n)), np.zeros((1, 1))])
    res = linprog(c, A_ub=A_ub, b_ub=np.zeros(m), A_eq=A_eq, b_eq=[1.0],
                  bounds=[(0, None)] * n + [(None, None)], method="highs")
    x, v = res.x[:n], res.x[-1]
    # Estrategia de B: min w  s.a.  M y <= w,  sum y = 1,  y >= 0
    c2 = np.zeros(m + 1); c2[-1] = 1.0
    A_ub2 = np.hstack([M, -np.ones((n, 1))])
    A_eq2 = np.hstack([np.ones((1, m)), np.zeros((1, 1))])
    res2 = linprog(c2, A_ub=A_ub2, b_ub=np.zeros(n), A_eq=A_eq2, b_eq=[1.0],
                   bounds=[(0, None)] * m + [(None, None)], method="highs")
    y = res2.x[:m]
    x = np.clip(x, 0, None); x /= x.sum()
    y = np.clip(y, 0, None); y /= y.sum()
    return float(v), x, y


# ── Motor ─────────────────────────────────────────────────────────────────────

class DeckMatch:
    """
    deck_a, deck_b: listas de 3 dicts con al menos
        ws / pts_ganados / pts_cedidos (lo que use prob_fn y los puntos).
    prob_fn(a, b) -> P(a gana un combate a b).
    """

    def __init__(self, deck_a, deck_b, prob_fn):
        self.deck_a, self.deck_b = deck_a, deck_b
        self.p = np.array([[prob_fn(a, b) for b in deck_b] for a in deck_a])
        self.pts_a = [[distribucion_puntos(_pts_media(a, b)) for b in deck_b] for a in deck_a]
        self.pts_b = [[distribucion_puntos(_pts_media(b, a)) for b in deck_b] for a in deck_a]
        self._opt = {}
        self._azar = {}

    # Resultado de una ronda con órdenes fijos, partiendo de (sa, sb)
    def _ronda(self, oa, ob, sa, sb):
        """({'A': p, 'B': p}, {(sa', sb'): p}) — ganadores y marcadores sin ganador."""
        estados = {(sa, sb): 1.0}
        final = {"A": 0.0, "B": 0.0}
        for k in range(3):
            i, j = oa[k], ob[k]
            nuevos = {}
            for (x, y), pr in estados.items():
                for pts, q in self.pts_a[i][j].items():
                    w = pr * self.p[i, j] * q
                    if x + pts >= OBJETIVO:
                        final["A"] += w
                    else:
                        nuevos[(x + pts, y)] = nuevos.get((x + pts, y), 0.0) + w
                for pts, q in self.pts_b[i][j].items():
                    w = pr * (1 - self.p[i, j]) * q
                    if y + pts >= OBJETIVO:
                        final["B"] += w
                    else:
                        nuevos[(x, y + pts)] = nuevos.get((x, y + pts), 0.0) + w
            estados = nuevos
        return final, estados

    def matriz(self, sa, sb, modo="optimo"):
        """Matriz 6x6 de P(A gana la partida) desde (sa, sb) según el orden de ronda."""
        V = self.valor_optimo if modo == "optimo" else self.valor_azar
        M = np.zeros((6, 6))
        for a, oa in enumerate(ORDENES):
            for b, ob in enumerate(ORDENES):
                final, resto = self._ronda(oa, ob, sa, sb)
                M[a, b] = final["A"] + sum(pr * V(x, y) for (x, y), pr in resto.items())
        return M

    def valor_optimo(self, sa=0, sb=0):
        """P(A gana) si ambos juegan de forma óptima en todas las rondas."""
        if (sa, sb) not in self._opt:
            v, x, y = resolver_matriz(self.matriz(sa, sb, "optimo"))
            self._opt[(sa, sb)] = (v, x, y)
        return self._opt[(sa, sb)][0]

    def estrategias(self, sa=0, sb=0):
        """(valor, estrategia mixta de A, estrategia mixta de B) en (sa, sb)."""
        self.valor_optimo(sa, sb)
        return self._opt[(sa, sb)]

    def valor_azar(self, sa=0, sb=0):
        """P(A gana) si ambos eligen el orden al azar en todas las rondas."""
        if (sa, sb) not in self._azar:
            self._azar[(sa, sb)] = float(self.matriz(sa, sb, "azar").mean())
        return self._azar[(sa, sb)]

    def mejor_respuesta(self, orden_b, sa=0, sb=0):
        """
        Si A conoce el orden de B en esta ronda (y después se juega óptimo):
        lista [(orden_a, P(A gana))] ordenada de mejor a peor.
        """
        M = self.matriz(sa, sb, "optimo")
        b = ORDENES.index(tuple(orden_b))
        return sorted(((ORDENES[a], float(M[a, b])) for a in range(6)),
                      key=lambda t: t[1], reverse=True)

    def marcadores_posibles(self):
        """Marcadores (sa, sb) al inicio de una ronda que pueden darse tras la 1ª."""
        vistos, pend = set(), [(0, 0)]
        while pend:
            s = pend.pop()
            for oa in ORDENES:
                for ob in ORDENES:
                    _, resto = self._ronda(oa, ob, *s)
                    for e in resto:
                        if e not in vistos:
                            vistos.add(e); pend.append(e)
        return sorted(vistos)
