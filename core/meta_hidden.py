import pandas as pd
import itertools

def generar_combos(df):

    blades = df["Blade"].unique()
    ratchets = df["Ratchet"].unique()
    bits = df["Bit"].unique()

    combos = list(itertools.product(blades, ratchets, bits))

    df_all = pd.DataFrame(combos, columns=["Blade", "Ratchet", "Bit"])

    df_existentes = df[["Blade", "Ratchet", "Bit"]]

    df_nuevos = df_all.merge(
        df_existentes,
        on=["Blade", "Ratchet", "Bit"],
        how="left",
        indicator=True
    )

    df_nuevos = df_nuevos[df_nuevos["_merge"] == "left_only"]

    return df_nuevos.drop(columns="_merge")