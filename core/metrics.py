def wilson(w, n, z=1.96):
    if n == 0:
        return 0
    p = w / n
    return (p + z**2/(2*n) - z*((p*(1-p)+z**2/(4*n))/n)**0.5) / (1 + z**2/n)


def calcular_agregados(df):
    df_blade = df.groupby("Blade")[["Wins", "Losses", "Partidas"]].sum().reset_index()
    df_ratchet = df.groupby("Ratchet")[["Wins", "Losses", "Partidas"]].sum().reset_index()
    df_bit = df.groupby("Bit")[["Wins", "Losses", "Partidas"]].sum().reset_index()

    for df_ in [df_blade, df_ratchet, df_bit]:
        df_["Wilson Score"] = df_.apply(
            lambda row: wilson(row["Wins"], row["Partidas"]), axis=1
        )

    return df_blade, df_ratchet, df_bit