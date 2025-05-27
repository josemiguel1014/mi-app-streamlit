import pandas as pd

def cargar_datos(file):
    try:
        df = pd.read_csv(file)
        if "Dia DiaID" not in df.columns or "Plu DESC" not in df.columns:
            return None
        df["fecha"] = pd.to_datetime(df["Dia DiaID"], errors="coerce")
        df = df.dropna(subset=["fecha"])
        return df
    except Exception as e:
        print(f"Error al cargar datos: {e}")
        return None
