import pandas as pd

def cargar_datos(file):
    try:
        df = pd.read_excel(file)
        if "Dia DiaID" not in df.columns or "Plu DESC" not in df.columns:
            return None
        df["fecha"] = pd.to_datetime(df["Dia DiaID"], errors="coerce")
        df = df.dropna(subset=["fecha"])
        return df
    except Exception as e:
        print(f"Error al cargar datos: {e}")
        return None

def filtrar_por_fechas(df, productos, fecha_inicio, fecha_fin):
    df_filtrado = df[
        (df["Plu DESC"].isin(productos)) &
        (df["fecha"] >= pd.to_datetime(fecha_inicio)) &
        (df["fecha"] <= pd.to_datetime(fecha_fin))
    ]
    return df_filtrado

def comparar_ventas(df_r1, df_r2):
    resumen_r1 = df_r1.groupby("Plu DESC")["$ Ventas sin impuestos Totales"].sum().reset_index()
    resumen_r1.columns = ["Producto", "Total Rango 1"]

    resumen_r2 = df_r2.groupby("Plu DESC")["$ Ventas sin impuestos Totales"].sum().reset_index()
    resumen_r2.columns = ["Producto", "Total Rango 2"]

    comparacion = pd.merge(resumen_r1, resumen_r2, on="Producto", how="outer").fillna(0)
    comparacion["Diferencia"] = comparacion["Total Rango 2"] - comparacion["Total Rango 1"]
    return comparacion

