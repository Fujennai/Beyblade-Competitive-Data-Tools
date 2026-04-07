import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import math
import logging

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

ratchets_especiales = ["Turbo", "Operate", "Zillion"]


# ----------------------------
# Funciones auxiliares
# ----------------------------

def separar_componentes(texto):
    partes = texto.split()

    for i, p in enumerate(partes):
        if re.match(r"\d+-\d+", p) or p in ratchets_especiales:
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


def wilson_score(wins, total, z=1.96):
    if total == 0:
        return None

    p = wins / total
    denominator = 1 + z**2 / total
    centre = p + z**2 / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)

    return (centre - margin) / denominator


def generar_datasets_agregados(df):

    # Blade
    df_blade = (
        df[["Blade", "Wins", "Losses", "Partidas"]]
        .groupby("Blade")
        .sum()
        .reset_index()
    )

    df_blade["Wilson Score"] = df_blade.apply(
        lambda row: wilson_score(row["Wins"], row["Partidas"])
        if row["Partidas"] > 0 else None,
        axis=1
    )

    # Ratchet
    df_ratchet = (
        df[["Ratchet", "Wins", "Losses", "Partidas"]]
        .groupby("Ratchet")
        .sum()
        .reset_index()
    )

    df_ratchet["Wilson Score"] = df_ratchet.apply(
        lambda row: wilson_score(row["Wins"], row["Partidas"])
        if row["Partidas"] > 0 else None,
        axis=1
    )

    # Bit
    df_bit = (
        df[["Bit", "Wins", "Losses", "Partidas"]]
        .groupby("Bit")
        .sum()
        .reset_index()
    )

    df_bit["Wilson Score"] = df_bit.apply(
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
            eficiencia_text = cols[3].get_text(strip=True)

            # Formato con "•"
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

            if bit is None:
                bit = bit_text

            # Ratchets especiales
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
            eficiencia = int(re.search(r"\d+", eficiencia_text).group())

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
                "Eficiencia": eficiencia,
                "Pts Ganados/Combate": pts_ganados,
                "Pts Cedidos/Combate": pts_cedidos
            })

        except Exception as e:
            logging.warning(f"Error en fila {i}: {e}")

        i += 2

    df = pd.DataFrame(data)

    if df.empty:
        raise Exception("El dataframe está vacío")

    # Wilson Score global
    df["Wilson Score"] = df.apply(
        lambda row: wilson_score(row["Wins"], row["Partidas"])
        if pd.notna(row["Wins"]) and row["Partidas"] > 0 else None,
        axis=1
    )

    # Limpieza
    df.dropna(inplace=True)
    df = df[df['Partidas'] > 0]
    df = df[df['Win %'] <= 100]
    df = df[(df['Pts Ganados/Combate'] >= 0) & (df['Pts Ganados/Combate'] <= 3)]
    df = df[(df['Pts Cedidos/Combate'] >= 0) & (df['Pts Cedidos/Combate'] <= 3)]

    logging.info(f"Filas finales: {len(df)}")

    # ----------------------------
    # Exportar datasets
    # ----------------------------

    # Dataset principal
    df.to_csv("beyblade_stats.csv", index=False)

    # Agregados
    df_blade, df_ratchet, df_bit = generar_datasets_agregados(df)

    df_blade.to_csv("blade_stats.csv", index=False)
    df_ratchet.to_csv("ratchet_stats.csv", index=False)
    df_bit.to_csv("bit_stats.csv", index=False)

    logging.info("Todos los CSV generados correctamente")


def main():
    scrape()


if __name__ == "__main__":
    main()
