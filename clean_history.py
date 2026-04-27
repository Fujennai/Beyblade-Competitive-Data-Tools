import pandas as pd
import os

FOLDER = "history"

def clean_file(path):
    df = pd.read_csv(path)

    if df.empty:
        return

    before = len(df)

    df = df.groupby(["Blade", "Ratchet", "Bit"], as_index=False).agg({
        "Win %": "mean",
        "Wins": "sum",
        "Losses": "sum",
        "Partidas": "sum",
        "Eficiencia": "mean",
        "Pts Ganados/Combate": "mean",
        "Pts Cedidos/Combate": "mean",
        "Wilson Score": "mean"
    })

    after = len(df)

    df.to_csv(path, index=False)

    print(f"{os.path.basename(path)} → {before - after} duplicados eliminados")


def main():
    files = sorted(os.listdir(FOLDER))

    for file in files:
        if file.endswith(".csv"):
            path = os.path.join(FOLDER, file)
            clean_file(path)


if __name__ == "__main__":
    main()
