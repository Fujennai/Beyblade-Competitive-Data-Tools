import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import math
import logging
from datetime import datetime
import os

# ----------------------------
# Configuración
# ----------------------------

logging.basicConfig(level=logging.INFO)

URL = "https://sbbl.es/stats"

params = {
    "sort": "percentage_victories",
    "order": "desc",
    "blade": "",
    "ratchet": "",
    "bit": "",
    "min_partidas": 0,
    "fecha_inicio": "",
    "fecha_fin": ""
}

# Ratchets "especiales" con nombre en lugar de formato N-N. Son válidos.
ratchets_especiales = ["Turbo", "Operate"]

# Palabras que aparecen en la web como si fueran un Ratchet pero en realidad
# son Assist Blades (parte del Blade). Los combos que las muestren como
# Ratchet se descartan, ya que el verdadero Ratchet (formato N-N) no se
# pudo parsear o no existe.
ASSIST_BLADES = {"Zillion"}

# Un Ratchet numérico válido tiene formato "N-N" (p.ej. "1-60", "3-80").
RATCHET_REGEX = re.compile(r"^\d+-\d+$")


def es_ratchet_valido(ratchet):
    """True si el Ratchet es N-N o un especial reconocido (Turbo/Operate)."""
    if ratchet is None:
        return False
    s = str(ratchet).strip()
    if s in ASSIST_BLADES:
        return False
    return bool(RATCHET_REGEX.match(s)) or s in ratchets_especiales


# ----------------------------
# Funciones auxiliares
# ----------------------------

def separar_componentes(texto):
    """
    Devuelve (blade, ratchet, bit). Considera como Ratchet los tokens que
    cumplen `\\d+-\\d+` o que son uno de los ratchets especiales (Turbo,
    Operate). Las Assist Blades (Zillion) NO se reconocen como Ratchet:
    se quedan como parte del nombre del Blade y la búsqueda continúa hasta
    encontrar un Ratchet real más adelante.
    """
    partes = texto.split()

    for i, p in enumerate(partes):
        if p in ASSIST_BLADES:
            continue  # ignorar Assist Blades, son parte del nombre del Blade
        if RATCHET_REGEX.match(p) or p in ratchets_especiales:
            blade = " ".join(partes[:i])
            ratchet = p

            if "X" in partes:
                x_idx = partes.index("X")
                bit = " ".join(partes[x_idx + 1:]) if len(partes) > x_idx + 1 else None
            else:
                bit = " ".join(partes[i + 1:]) if len(partes) > i + 1 else None

            return blade, ratchet, bit

    return texto, None, None


def es_combo_valido(blade, ratchet, bit):
    if not blade or not ratchet:
        return False

    texto = f"{blade} {ratchet} {bit}".lower()

    if "selecciona" in texto:
        return False

    if ratchet.strip() == "_" or (bit and bit.strip() == "_"):
        return False

    return True

# 1.96 es el valor estándar de la distribución normal
def wilson_score(wins, total, z=1.96):
    if total == 0:
        return None

    p = wins / total
    denominator = 1 + z**2 / total
    centre = p + z**2 / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)

    return (centre - margin) / denominator


def generar_datasets_agregados(df):

    df_blade = df.groupby("Blade")[["Wins", "Losses", "Partidas"]].sum().reset_index()
    df_ratchet = df.groupby("Ratchet")[["Wins", "Losses", "Partidas"]].sum().reset_index()
    df_bit = df.groupby("Bit")[["Wins", "Losses", "Partidas"]].sum().reset_index()

    for df_ in [df_blade, df_ratchet, df_bit]:
        df_["Wilson Score"] = df_.apply(
            lambda row: wilson_score(row["Wins"], row["Partidas"])
            if row["Partidas"] > 0 else None,
            axis=1
        )

    return df_blade, df_ratchet, df_bit


# ----------------------------
# Scraper principal
# ----------------------------

def scrape():
    logging.info("Iniciando scraping...")

    response = requests.get(URL, params=params)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")

    if not table:
        raise Exception("No se encontró la tabla")

    rows = table.find_all("tr")

    data = []
    i = 1

    while i < len(rows):
        cols = rows[i].find_all("td")

        if not cols:
            i += 1
            continue

        try:
            combo_text = cols[0].get_text(" ", strip=True)
            winrate_text = cols[1].get_text(strip=True)
            partidas_text = cols[2].get_text(strip=True)

            # Separar bit si viene con "•"
            if "•" in combo_text:
                parte_principal, bit = combo_text.split("•", 1)
                bit = bit.strip()
            else:
                parte_principal = combo_text
                bit = None

            blade, ratchet, bit_text = separar_componentes(parte_principal)

            if ratchet is None:
                i += 2
                continue

            # Defensivo: descartar Assist Blades (Zillion) si por algún motivo
            # llegan hasta aquí como Ratchet.
            if ratchet in ASSIST_BLADES:
                logging.info(f"Descartado por Assist Blade como Ratchet: {blade} / {ratchet} / {bit}")
                i += 2
                continue

            if bit is None:
                bit = bit_text

            # Ratchets especiales (Turbo, Operate): si no hay bit detectado,
            # mantenemos la lógica original de mover el ratchet al bit.
            if ratchet in ratchets_especiales:
                if not bit:
                    bit = ratchet
                else:
                    i += 2
                    continue

            if not es_combo_valido(blade, ratchet, bit):
                i += 2
                continue

            # Métricas
            win_match = re.search(r"([\d\.]+)%", winrate_text)
            wl_match = re.search(r"(\d+)W\s*-\s*(\d+)L", winrate_text)

            wins = int(wl_match.group(1)) if wl_match else None
            losses = int(wl_match.group(2)) if wl_match else None
            win_percent = float(win_match.group(1)) if win_match else None

            partidas = int(partidas_text)

            # Detalle
            detalle_text = rows[i + 1].get_text(" ", strip=True) if i + 1 < len(rows) else ""
            nums = re.findall(r"\d+\.\d+", detalle_text)

            pts_ganados = float(nums[0]) if len(nums) > 0 else None
            pts_cedidos = float(nums[1]) if len(nums) > 1 else None

            data.append({
                "Blade": blade,
                "Ratchet": ratchet,
                "Bit": bit,
                "Win %": win_percent,
                "Wins": wins,
                "Losses": losses,
                "Partidas": partidas,
                "Pts Ganados/Combate": pts_ganados,
                "Pts Cedidos/Combate": pts_cedidos
            })

        except Exception as e:
            logging.warning(f"Error en fila {i}: {e}")

        i += 2

    df = pd.DataFrame(data)

    if df.empty:
        raise Exception("El dataframe está vacío")

    # ----------------------------
    # ELIMINAR DUPLICADOS
    # ----------------------------

    before = len(df)

    df = df.groupby(["Blade", "Ratchet", "Bit"], as_index=False).agg({
        "Win %": "mean",
        "Wins": "sum",
        "Losses": "sum",
        "Partidas": "sum",
        "Pts Ganados/Combate": "mean",
        "Pts Cedidos/Combate": "mean"
    })

    after = len(df)
    logging.info(f"Duplicados eliminados: {before - after}")

    # ----------------------------
    # Wilson Score
    # ----------------------------

    df["Wilson Score"] = df.apply(
        lambda row: wilson_score(row["Wins"], row["Partidas"])
        if pd.notna(row["Wins"]) and row["Partidas"] > 0 else None,
        axis=1
    )

    # ----------------------------
    # Calcular métricas por victoria/derrota
    # ----------------------------

    df["Pts Ganados/Partida Ganada"] = df.apply(
        lambda row: (row["Pts Ganados/Combate"] * row["Partidas"] / row["Wins"])
        if pd.notna(row["Wins"]) and row["Wins"] > 0 else None,
        axis=1
    )

    df["Pts Cedidos/Partida Perdida"] = df.apply(
        lambda row: (row["Pts Cedidos/Combate"] * row["Partidas"] / row["Losses"])
        if pd.notna(row["Losses"]) and row["Losses"] > 0 else None,
        axis=1
    )

    # Limpieza
    df.dropna(inplace=True)
    df = df[df['Partidas'] > 0]
    df = df[df['Win %'] <= 100]

    # Validación: métricas por partida ganada/perdida deben estar entre 1.0 y 3.0
    df = df[(df['Pts Ganados/Partida Ganada'] >= 1.0) & (df['Pts Ganados/Partida Ganada'] <= 3.0)]
    df = df[(df['Pts Cedidos/Partida Perdida'] >= 1.0) & (df['Pts Cedidos/Partida Perdida'] <= 3.0)]

    # ----------------------------
    # Compatibilidad de piezas
    # ----------------------------

    BLADE_RATCHET_COMPAT = {
        "Clock Mirage": lambda r: r.endswith("5"),
    }

    def es_compatible(row):
        blade = row["Blade"]
        if blade in BLADE_RATCHET_COMPAT:
            return BLADE_RATCHET_COMPAT[blade](row["Ratchet"])
        return True

    antes = len(df)
    df = df[df.apply(es_compatible, axis=1)]
    logging.info(f"Combos incompatibles eliminados: {antes - len(df)}")

    logging.info(f"Filas finales: {len(df)}")


    # ----------------------------
    # Arquetipos
    # ----------------------------

    def categorizar(valor, partidas, winrate):
        if partidas < 10:
            return -1
        if winrate >= 95 and partidas < 25:
            return -1
        # Ahora valor está entre 1.0 y 3.0 (puntos por partida ganada/perdida)
        if valor < 1.5:   return 1  # Spin finish (1.0-1.5)
        elif valor < 2.5: return 2  # Burst / Over (1.5-2.5)
        else:             return 3  # Xtreme finish (2.5-3.0)

    map_victoria = {
        -1: "⚪ Datos insuficientes",
         1: "🔵 Spin finish",
         2: "🟠 Burst / Over",
         3: "🟢 Xtreme finish"
    }
    map_derrota = {
        -1: "⚪ Datos insuficientes",
         1: "🔵 Pierde por spin",
         2: "🟠 Pierde por burst/over",
         3: "🟢 Pierde por xtreme"
    }

    df["tipo_victoria"] = df.apply(
        lambda r: categorizar(r["Pts Ganados/Partida Ganada"], r["Partidas"], r["Win %"]), axis=1
    )
    df["tipo_derrota"] = df.apply(
        lambda r: categorizar(r["Pts Cedidos/Partida Perdida"], r["Partidas"], r["Win %"]), axis=1
    )
    df["Arquetipo victoria"] = df["tipo_victoria"].map(map_victoria)
    df["Arquetipo derrota"]  = df["tipo_derrota"].map(map_derrota)
    df = df.drop(columns=["tipo_victoria", "tipo_derrota"])

    # ----------------------------
    # Exportar
    # ----------------------------

    os.makedirs("history", exist_ok=True)

    fecha = datetime.now().strftime("%Y-%m-%d")

    df.to_csv(f"history/beyblade_stats_{fecha}.csv", index=False)
    df.to_csv("beyblade_stats.csv", index=False)

    df_blade, df_ratchet, df_bit = generar_datasets_agregados(df)

    df_blade.to_csv("blade_stats.csv", index=False)
    df_ratchet.to_csv("ratchet_stats.csv", index=False)
    df_bit.to_csv("bit_stats.csv", index=False)

    logging.info("Todos los CSV generados correctamente")


def main():
    scrape()


if __name__ == "__main__":
    main()