import pandas as pd
from sklearn.ensemble import RandomForestRegressor

def entrenar_modelo(df):

    X = pd.get_dummies(df[["Blade", "Ratchet", "Bit"]])
    y = df["Win %"]

    model = RandomForestRegressor(random_state=42)
    model.fit(X, y)

    return model, X.columns


def predecir(model, columns, blade, ratchet, bit):

    input_df = pd.DataFrame([{
        "Blade": blade,
        "Ratchet": ratchet,
        "Bit": bit
    }])

    input_encoded = pd.get_dummies(input_df)
    input_encoded = input_encoded.reindex(columns=columns, fill_value=0)

    pred = model.predict(input_encoded)[0]

    return round(pred, 2)