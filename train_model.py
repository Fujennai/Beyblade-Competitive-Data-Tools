"""
train_model.py
--------------
Entrena UN SOLO modelo GradientBoosting compartido por:
  - core/recommender.py  (recomendador)
  - core/predictor.py    (predictor)
  - core/meta_hidden.py  (META oculto)

Guarda model.pkl con todo lo necesario para inferencia.
Se ejecuta desde GitHub Actions tras el scraping.

MEJORAS v2:
  1. Features de interacción par-a-par (Blade+Ratchet, Blade+Bit, Ratchet+Bit)
     como Wilson Score observado → el modelo aprende sinergias reales entre piezas.
  2. Ancla bayesiana en inferencia: blends predicción ML con historial real del combo
     o de sus pares más cercanos, ponderado por volumen de evidencia.
  3. Filtro de confianza estricto basado en cobertura de datos reales exportado
     al payload para que recommender / meta_hidden lo usen.
"""

import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from scipy.stats import spearmanr

CSV_PATH   = "beyblade_stats.csv"
MODEL_PATH = "model.pkl"

# Partidas mínimas reales para considerar un combo "confiable"
MIN_PARTIDAS_CONFIABLE = 10
# Partidas mínimas para que un par (ej. Blade+Ratchet) tenga peso en el ancla
MIN_PARTIDAS_PAR = 5


# ── Wilson Score ──────────────────────────────────────────────────────────────
def wilson(w, n, z=1.96):
    if n == 0:
        return 0.0
    p = w / n
    return (p + z**2/(2*n) - z*((p*(1-p)+z**2/(4*n))/n)**0.5) / (1 + z**2/n)


# ── Score agregado por pieza ──────────────────────────────────────────────────
def calcular_score_pieza(df, columna):
    stats = df.groupby(columna).agg({"Wins": "sum", "Partidas": "sum"}).reset_index()
    stats["score"] = stats.apply(lambda r: wilson(r["Wins"], r["Partidas"]), axis=1)
    return dict(zip(stats[columna], stats["score"]))


# ── NUEVO: Score Wilson por par de piezas ─────────────────────────────────────
def calcular_score_par(df, col_a, col_b):
    """
    Devuelve dict { (val_a, val_b): wilson_score } agregando wins/partidas
    de todos los combos que comparten ese par.
    Solo incluye pares con >= MIN_PARTIDAS_PAR partidas.
    """
    stats = df.groupby([col_a, col_b]).agg({"Wins": "sum", "Partidas": "sum"}).reset_index()
    stats = stats[stats["Partidas"] >= MIN_PARTIDAS_PAR]
    stats["score"] = stats.apply(lambda r: wilson(r["Wins"], r["Partidas"]), axis=1)
    return {(row[col_a], row[col_b]): row["score"] for _, row in stats.iterrows()}


# ── NUEVO: Ancla bayesiana para inferencia ────────────────────────────────────
def calcular_ancla(blade, ratchet, bit, combo_dict, par_br, par_bb, par_rb,
                   blade_dict, ratchet_dict, bit_dict, ws_mean):
    """
    Calcula un score ancla ponderado por evidencia real:
      - Si el combo existe en datos reales → ancla fuerte (peso alto)
      - Si hay pares observados → ancla media
      - Si solo hay scores de piezas individuales → ancla débil

    Devuelve (ancla_score, peso_ancla) donde peso_ancla ∈ [0, 1].
    Un peso_ancla alto → confiar más en ancla que en ML.
    """
    evidencia = []
    pesos     = []

    # Combo completo real
    if (blade, ratchet, bit) in combo_dict:
        ws_real, n_real = combo_dict[(blade, ratchet, bit)]
        # Peso basado en partidas: a 30 partidas ya es muy fiable
        w = min(n_real / 30.0, 1.0)
        evidencia.append(ws_real)
        pesos.append(w * 3.0)  # triple peso vs. pares

    # Pares observados
    for par_dict, key in [
        (par_br, (blade, ratchet)),
        (par_bb, (blade, bit)),
        (par_rb, (ratchet, bit)),
    ]:
        if key in par_dict:
            evidencia.append(par_dict[key])
            pesos.append(1.0)

    # Piezas individuales (siempre disponibles)
    evidencia.append(blade_dict.get(blade, ws_mean))
    evidencia.append(ratchet_dict.get(ratchet, ws_mean))
    evidencia.append(bit_dict.get(bit, ws_mean))
    pesos.extend([0.3, 0.3, 0.3])

    ancla = np.average(evidencia, weights=pesos)
    # El peso total del ancla sobre el ML: normalizado entre 0.1 y 0.85
    peso_ancla = min(sum(pesos[:len(evidencia) - 3]) / 6.0, 0.85)

    return float(ancla), float(peso_ancla)


# ── Entrenamiento ─────────────────────────────────────────────────────────────
def entrenar_y_guardar():
    df = pd.read_csv(CSV_PATH)

    if df.empty or "Wilson Score" not in df.columns:
        raise ValueError("CSV vacío o sin columna Wilson Score")

    print(f"Filas cargadas: {len(df)}")

    # ── Label encoders ────────────────────────────────────────────────────────
    encoders = {}
    for col in ["Blade", "Ratchet", "Bit"]:
        le = LabelEncoder()
        df[col + "_enc"] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    # ── Features por pieza individual ─────────────────────────────────────────
    df["Partidas_log"] = np.log1p(df["Partidas"])

    blade_dict   = calcular_score_pieza(df, "Blade")
    ratchet_dict = calcular_score_pieza(df, "Ratchet")
    bit_dict     = calcular_score_pieza(df, "Bit")

    df["Blade_score"]   = df["Blade"].map(blade_dict)
    df["Ratchet_score"] = df["Ratchet"].map(ratchet_dict)
    df["Bit_score"]     = df["Bit"].map(bit_dict)

    ws_mean = float(df["Wilson Score"].mean())

    # ── NUEVO: Features de interacción par-a-par ──────────────────────────────
    par_br = calcular_score_par(df, "Blade", "Ratchet")
    par_bb = calcular_score_par(df, "Blade", "Bit")
    par_rb = calcular_score_par(df, "Ratchet", "Bit")

    df["BR_score"] = df.apply(
        lambda r: par_br.get((r["Blade"], r["Ratchet"]), ws_mean), axis=1
    )
    df["BB_score"] = df.apply(
        lambda r: par_bb.get((r["Blade"], r["Bit"]), ws_mean), axis=1
    )
    df["RB_score"] = df.apply(
        lambda r: par_rb.get((r["Ratchet"], r["Bit"]), ws_mean), axis=1
    )

    # ── Feature set completo ──────────────────────────────────────────────────
    feature_cols = [
        "Blade_enc", "Ratchet_enc", "Bit_enc",
        "Partidas_log",
        "Blade_score", "Ratchet_score", "Bit_score",
        "BR_score", "BB_score", "RB_score",          # ← NUEVO
    ]

    X = df[feature_cols].values.astype(float)
    y = df["Wilson Score"].values

    model = GradientBoostingRegressor(
        n_estimators=400,
        learning_rate=0.04,
        max_depth=4,
        subsample=0.8,
        min_samples_leaf=3,
        random_state=42,
    )
    model.fit(X, y)
    print("Modelo entrenado.")

    # ── NUEVO: dict combo real → (wilson, partidas) para ancla ───────────────
    combo_dict = {}
    for _, row in df.iterrows():
        combo_dict[(row["Blade"], row["Ratchet"], row["Bit"])] = (
            float(row["Wilson Score"]),
            int(row["Partidas"]),
        )

    # ── Pesos Spearman por pieza ──────────────────────────────────────────────
    corr_blade,   _ = spearmanr(df["Blade_score"],   df["Wilson Score"])
    corr_ratchet, _ = spearmanr(df["Ratchet_score"], df["Wilson Score"])
    corr_bit,     _ = spearmanr(df["Bit_score"],     df["Wilson Score"])
    total = abs(corr_blade) + abs(corr_ratchet) + abs(corr_bit)
    piece_weights = {
        "Blade":   round(abs(corr_blade)   / total, 4),
        "Ratchet": round(abs(corr_ratchet) / total, 4),
        "Bit":     round(abs(corr_bit)     / total, 4),
    }
    print(f"Pesos estimados por pieza: {piece_weights}")

    # ── Partidas por pieza (para filtro de confianza) ─────────────────────────
    partidas_blade   = df.groupby("Blade")["Partidas"].sum().to_dict()
    partidas_ratchet = df.groupby("Ratchet")["Partidas"].sum().to_dict()
    partidas_bit     = df.groupby("Bit")["Partidas"].sum().to_dict()

    # ── Guardar payload ───────────────────────────────────────────────────────
    payload = {
        "model":           model,
        "encoders":        encoders,
        "feature_cols":    feature_cols,
        "blade_dict":      blade_dict,
        "ratchet_dict":    ratchet_dict,
        "bit_dict":        bit_dict,
        "ws_mean":         ws_mean,
        "piece_weights":   piece_weights,
        # NUEVO
        "par_br":          par_br,
        "par_bb":          par_bb,
        "par_rb":          par_rb,
        "combo_dict":      combo_dict,
        "partidas_blade":   partidas_blade,
        "partidas_ratchet": partidas_ratchet,
        "partidas_bit":     partidas_bit,
        "min_partidas_confiable": MIN_PARTIDAS_CONFIABLE,
        "min_partidas_par":       MIN_PARTIDAS_PAR,
    }

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(payload, f)

    print(f"✅ model.pkl guardado con {len(df)} filas y {len(feature_cols)} features")


if __name__ == "__main__":
    entrenar_y_guardar()