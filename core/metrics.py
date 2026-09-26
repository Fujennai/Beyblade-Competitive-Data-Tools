def wilson(w, n, z=1.96):
    if n == 0:
        return 0
    p = w / n
    return (p + z**2/(2*n) - z*((p*(1-p)+z**2/(4*n))/n)**0.5) / (1 + z**2/n)


def calcular_agregados(df):
    """Agregados por pieza: Blade, Assist (solo CX), Ratchet y Bit."""
    cols = ["Wins", "Losses", "Partidas"]
    df_blade = df.groupby("Blade")[cols].sum().reset_index()
    df_assist = df[df["Assist"] != ""].groupby("Assist")[cols].sum().reset_index()
    df_ratchet = df.groupby("Ratchet")[cols].sum().reset_index()
    df_bit = df.groupby("Bit")[cols].sum().reset_index()

    for df_ in [df_blade, df_assist, df_ratchet, df_bit]:
        df_["Wilson Score"] = [wilson(w, n) for w, n in zip(df_["Wins"], df_["Partidas"])]

    return df_blade, df_assist, df_ratchet, df_bit
