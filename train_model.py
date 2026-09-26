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
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_absolute_error

from core.compatibility import filtrar_df, SIN_ASSIST

PIEZAS = ["Blade", "Assist", "Ratchet", "Bit"]

CSV_PATH   = "beyblade_stats.csv"
MODEL_PATH = "model.pkl"
# Versión del formato del payload. core/model_loader.py reentrena en memoria si
# model.pkl es de un formato anterior (p.ej. sin Assist).
FORMATO_PAYLOAD = 2

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


# ── Features sin fuga (leave-one-out) ─────────────────────────────────────────
PAIRS = {"BR": ("Blade", "Ratchet"), "BB": ("Blade", "Bit"), "RB": ("Ratchet", "Bit")}


def features_desde_stats(stats_df, target_df, ws_mean, loo=False):
    """
    Calcula Blade/Assist/Ratchet/Bit_score y BR/BB/RB_score para `target_df` usando las
    Wins/Partidas agregadas de `stats_df`.

    loo=True (target_df ES stats_df): se resta la propia fila antes de calcular
    el Wilson. Así, en entrenamiento, las features de un combo nunca contienen
    su propio resultado (el target) y el modelo ve lo mismo que verá al
    predecir un combo no jugado.
    """
    out = pd.DataFrame(index=target_df.index)
    grupos = [(c + "_score", [c], 1) for c in PIEZAS]
    grupos += [(k + "_score", list(v), MIN_PARTIDAS_PAR) for k, v in PAIRS.items()]

    for col, keys, min_n in grupos:
        agg = stats_df.groupby(keys)[["Wins", "Partidas"]].sum()
        t = target_df[keys].merge(agg, left_on=keys, right_index=True, how="left")
        w = t["Wins"].fillna(0).to_numpy(dtype=float)
        n = t["Partidas"].fillna(0).to_numpy(dtype=float)
        if loo:
            w = w - target_df["Wins"].to_numpy(dtype=float)
            n = n - target_df["Partidas"].to_numpy(dtype=float)
        out[col] = [wilson(wi, ni) if ni >= min_n else ws_mean for wi, ni in zip(w, n)]
    # "Sin Assist" (UX/BX) no es una pieza: score neutro. Con leave-one-out, un
    # grupo tan grande daría un valor casi constante que codifica el propio
    # resultado (más victorias -> score LOO algo menor) y el modelo aprendería
    # ese artefacto (R² CV 0,45 -> 0,34).
    out.loc[target_df["Assist"] == SIN_ASSIST, "Assist_score"] = ws_mean
    return out


def _crear_modelo():
    return GradientBoostingRegressor(
        n_estimators=400,
        learning_rate=0.04,
        max_depth=4,
        subsample=0.8,
        min_samples_leaf=3,
        random_state=42,
    )


def evaluar_cv(df, feature_cols, n_splits=5):
    """
    Validación cruzada que simula el uso real (predecir combos NO vistos):
    en cada fold, las features del test se calculan solo con el train.
    Devuelve métricas del modelo y de un baseline trivial (solo log(Partidas)).
    """
    y = df["Wilson Score"].to_numpy()
    pred = np.zeros(len(df))
    pred_base = np.zeros(len(df))
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=0)

    for tr, te in kf.split(df):
        a, b = df.iloc[tr], df.iloc[te]
        wm = float(a["Wilson Score"].mean())
        Xa = pd.concat([a, features_desde_stats(a, a, wm, loo=True)], axis=1)
        Xb = pd.concat([b, features_desde_stats(a, b, wm)], axis=1)
        pred[te] = _crear_modelo().fit(Xa[feature_cols].values, y[tr]).predict(Xb[feature_cols].values)

        # Baseline: regresión lineal sobre log(Partidas)
        coef = np.polyfit(a["Partidas_log"], y[tr], 1)
        pred_base[te] = np.polyval(coef, b["Partidas_log"])

    def _m(p):
        return {
            "r2": round(float(r2_score(y, p)), 4),
            "mae": round(float(mean_absolute_error(y, p)), 4),
            "spearman": round(float(spearmanr(y, p)[0]), 4),
        }

    return {"modelo": _m(pred), "baseline_log_partidas": _m(pred_base), "n_splits": n_splits}


# ── Entrenamiento ─────────────────────────────────────────────────────────────
def construir_payload(df, evaluar=True, verbose=True):
    """
    Entrena el modelo y devuelve el payload completo (el mismo que se guarda
    en model.pkl). Lo usa también core/model_loader.py como fallback en
    memoria cuando no existe model.pkl, para que solo haya UNA forma de
    entrenar el modelo.
    evaluar=False omite la validación cruzada (más rápido).
    """
    log = print if verbose else (lambda *a, **k: None)
    # Solo combos legales, con la columna Assist (vacía en UX/BX)
    df = filtrar_df(df).reset_index(drop=True)

    if df.empty or "Wilson Score" not in df.columns:
        raise ValueError("CSV vacío o sin columna Wilson Score")

    log(f"Filas cargadas: {len(df)}")

    # ── Label encoders ────────────────────────────────────────────────────────
    encoders = {}
    for col in PIEZAS:
        le = LabelEncoder()
        df[col + "_enc"] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    # ── Features por pieza individual ─────────────────────────────────────────
    df["Partidas_log"] = np.log1p(df["Partidas"])

    blade_dict   = calcular_score_pieza(df, "Blade")
    # Assist: solo CX. Sin Assist (UX/BX) usa ws_mean (ver features_desde_stats)
    assist_dict  = calcular_score_pieza(df[df["Assist"] != SIN_ASSIST], "Assist")
    ratchet_dict = calcular_score_pieza(df, "Ratchet")
    bit_dict     = calcular_score_pieza(df, "Bit")

    ws_mean = float(df["Wilson Score"].mean())

    # Diccionarios con TODOS los datos: se usan en inferencia (combos no
    # jugados, cuyo resultado no está en ninguno de estos agregados).
    par_br = calcular_score_par(df, "Blade", "Ratchet")
    par_bb = calcular_score_par(df, "Blade", "Bit")
    par_rb = calcular_score_par(df, "Ratchet", "Bit")
    # Blade CX + Assist (el antiguo "Blade completo"): solo como evidencia del ancla
    par_ba = calcular_score_par(df[df["Assist"] != SIN_ASSIST], "Blade", "Assist")

    # Features de ENTRENAMIENTO sin fuga: leave-one-out (cada combo excluye
    # su propio resultado de los scores de pieza y de par).
    df = pd.concat([df, features_desde_stats(df, df, ws_mean, loo=True)], axis=1)

    # ── Feature set completo ──────────────────────────────────────────────────
    feature_cols = [
        "Blade_enc", "Assist_enc", "Ratchet_enc", "Bit_enc",
        "Partidas_log",
        "Blade_score", "Assist_score", "Ratchet_score", "Bit_score",
        "BR_score", "BB_score", "RB_score",          # ← NUEVO
    ]

    # ── Validación (simula predecir combos no vistos) ─────────────────────────
    cv_metrics = None
    if evaluar:
        cv_metrics = evaluar_cv(
            df.drop(columns=[c for c in feature_cols if c.endswith("_score")]),
            feature_cols,
        )
        log(f"CV modelo:   {cv_metrics['modelo']}")
        log(f"CV baseline: {cv_metrics['baseline_log_partidas']}  (solo log(Partidas))")

    X = df[feature_cols].values.astype(float)
    y = df["Wilson Score"].values

    model = _crear_modelo()
    model.fit(X, y)
    log("Modelo entrenado.")

    # ── NUEVO: dict combo real → (wilson, partidas) para ancla ───────────────
    combo_dict = {}
    for _, row in df.iterrows():
        combo_dict[(row["Blade"], row["Assist"], row["Ratchet"], row["Bit"])] = (
            float(row["Wilson Score"]),
            int(row["Partidas"]),
        )

    # ── Pesos Spearman por pieza ──────────────────────────────────────────────
    corr_blade,   _ = spearmanr(df["Blade_score"],   df["Wilson Score"])
    corr_ratchet, _ = spearmanr(df["Ratchet_score"], df["Wilson Score"])
    corr_bit,     _ = spearmanr(df["Bit_score"],     df["Wilson Score"])
    total = abs(corr_blade) + abs(corr_ratchet) + abs(corr_bit)
    piece_weights = {
        "Blade":   round(float(abs(corr_blade)   / total), 4),
        "Ratchet": round(float(abs(corr_ratchet) / total), 4),
        "Bit":     round(float(abs(corr_bit)     / total), 4),
    }
    log(f"Pesos estimados por pieza: {piece_weights}")

    # ── Partidas por pieza (para filtro de confianza) ─────────────────────────
    partidas_blade   = df.groupby("Blade")["Partidas"].sum().to_dict()
    partidas_assist  = df.groupby("Assist")["Partidas"].sum().to_dict()
    partidas_ratchet = df.groupby("Ratchet")["Partidas"].sum().to_dict()
    partidas_bit     = df.groupby("Bit")["Partidas"].sum().to_dict()

    # ── Guardar payload ───────────────────────────────────────────────────────
    payload = {
        "model":           model,
        "encoders":        encoders,
        "feature_cols":    feature_cols,
        "blade_dict":      blade_dict,
        "assist_dict":     assist_dict,
        "ratchet_dict":    ratchet_dict,
        "bit_dict":        bit_dict,
        "ws_mean":         ws_mean,
        "piece_weights":   piece_weights,
        # NUEVO
        "par_br":          par_br,
        "par_bb":          par_bb,
        "par_rb":          par_rb,
        "par_ba":          par_ba,
        "combo_dict":      combo_dict,
        "partidas_blade":   partidas_blade,
        "partidas_assist":  partidas_assist,
        "partidas_ratchet": partidas_ratchet,
        "partidas_bit":     partidas_bit,
        "min_partidas_confiable": MIN_PARTIDAS_CONFIABLE,
        "min_partidas_par":       MIN_PARTIDAS_PAR,
        "cv_metrics":             cv_metrics,
        "formato":                FORMATO_PAYLOAD,
    }

    return payload


def entrenar_y_guardar():
    df = pd.read_csv(CSV_PATH)
    payload = construir_payload(df, evaluar=True)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(payload, f)

    print(f"✅ model.pkl guardado con {len(df)} filas y {len(payload['feature_cols'])} features")


if __name__ == "__main__":
    entrenar_y_guardar()