import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from datetime import datetime

st.set_page_config(layout="wide")

@st.cache_data
def cargar_datos(file):
    df = pd.read_excel(file)
    df["Dia DiaID"] = pd.to_datetime(df["Dia DiaID"], errors='coerce')
    return df.dropna(subset=["Dia DiaID"])

def generar_excel(df_r1, df_r2, comparacion):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_r1.to_excel(writer, index=False, sheet_name='Rango 1')
        df_r2.to_excel(writer, index=False, sheet_name='Rango 2')
        comparacion.to_excel(writer, index=False, sheet_name='Comparación')
    output.seek(0)
    return output

def mostrar_comparacion(comparacion_df):
    st.subheader("📊 Resumen Comparativo")
    st.dataframe(comparacion_df)

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=comparacion_df["Producto"],
        y=comparacion_df["Total Rango 1"].apply(lambda x: float(x.replace('$', '').replace(',', ''))),
        name="Rango 1", marker_color='blue'
    ))
    fig_bar.add_trace(go.Bar(
        x=comparacion_df["Producto"],
        y=comparacion_df["Total Rango 2"].apply(lambda x: float(x.replace('$', '').replace(',', ''))),
        name="Rango 2", marker_color='orange'
    ))
    fig_bar.update_layout(
        barmode='group',
        title="📊 Comparación de Ventas por Producto",
        xaxis_title="Producto",
        yaxis_title="Ventas"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

def mostrar_poligonos(df_r1, df_r2, productos):
    st.subheader("📈 4. Polígonos de Frecuencia por Producto")
    df_completo = pd.concat([df_r1, df_r2])

    for producto in productos:
        df_producto = df_completo[df_completo["Producto Marca"] == producto].copy()
        df_producto["Año"] = df_producto["Dia DiaID"].dt.year
        df_producto["Día-Mes"] = df_producto["Dia DiaID"].dt.strftime('%d-%b')

        fig = go.Figure()
        for anio in sorted(df_producto["Año"].unique()):
            df_anio = df_producto[df_producto["Año"] == anio]
            df_grouped = df_anio.groupby("Día-Mes")["$ Ventas sin impuestos Totales"].sum().reset_index()
            df_grouped = df_grouped.sort_values("Día-Mes")
            fig.add_trace(go.Scatter(
                x=df_grouped["Día-Mes"],
                y=df_grouped["$ Ventas sin impuestos Totales"],
                mode='lines+markers',
                name=str(anio)
            ))

        fig.update_layout(
            title=f"{producto} - Comparación de Ventas por Día y Año",
            xaxis_title="Día - Mes",
            yaxis_title="Ventas sin impuestos",
            height=450
        )
        st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("📊 Comparador de Ventas por Producto - Clientes Digitales")
    uploaded_file = st.file_uploader("📥 1. Cargar archivo de ventas", type=["xlsx"])

    if uploaded_file:
        df = cargar_datos(uploaded_file)

        # Crear nueva columna con producto + marca en mayúsculas
        df["Producto Marca"] = (df["Plu DESC"].astype(str) + " - " + df["Marca DESC"].astype(str)).str.upper()

        productos = df["Producto Marca"].dropna().unique().tolist()

        if 'seleccionados' not in st.session_state:
            st.session_state.seleccionados = []
        if 'rango_seleccionado' not in st.session_state:
            st.session_state.rango_seleccionado = False
        if 'mostrar_rangos' not in st.session_state:
            st.session_state.mostrar_rangos = False

        seleccionados = st.multiselect("📌 2. Selecciona los productos a comparar", productos, default=st.session_state.seleccionados)

        if st.button("✅ Continuar productos"):
            st.session_state.seleccionados = seleccionados
            st.session_state.mostrar_rangos = True

        if st.session_state.mostrar_rangos and st.session_state.seleccionados:
            df_filtrado = df[df["Producto Marca"].isin(st.session_state.seleccionados)]
            min_fecha = df_filtrado["Dia DiaID"].min().date()
            max_fecha = df_filtrado["Dia DiaID"].max().date()

            st.subheader("📆 3. Selecciona los rangos de fecha a comparar")
            col1, col2 = st.columns(2)
            with col1:
                rango1 = st.date_input("Rango 1", [min_fecha, max_fecha], min_value=min_fecha, max_value=max_fecha, key='r1')
            with col2:
                rango2 = st.date_input("Rango 2", [min_fecha, max_fecha], min_value=min_fecha, max_value=max_fecha, key='r2')

            if st.button("✅ Continuar fechas"):
                st.session_state.rango_seleccionado = True

            if st.session_state.rango_seleccionado and len(rango1) == 2 and len(rango2) == 2:
                r1_start, r1_end = pd.to_datetime(rango1[0]), pd.to_datetime(rango1[1])
                r2_start, r2_end = pd.to_datetime(rango2[0]), pd.to_datetime(rango2[1])

                df_r1 = df_filtrado[(df_filtrado["Dia DiaID"] >= r1_start) & (df_filtrado["Dia DiaID"] <= r1_end)]
                df_r2 = df_filtrado[(df_filtrado["Dia DiaID"] >= r2_start) & (df_filtrado["Dia DiaID"] <= r2_end)]

                comparacion = []
                for producto in st.session_state.seleccionados:
                    v1 = df_r1[df_r1["Producto Marca"] == producto]["$ Ventas sin impuestos Totales"].sum()
                    v2 = df_r2[df_r2["Producto Marca"] == producto]["$ Ventas sin impuestos Totales"].sum()
                    diferencia = v2 - v1
                    variacion = ((v2 - v1) / v1 * 100) if v1 != 0 else 0
                    comparacion.append({
                        "Producto": producto,
                        "Total Rango 1": f"${v1:,.2f}",
                        "Total Rango 2": f"${v2:,.2f}",
                        "Diferencia": f"${diferencia:,.2f}",
                        "% Variación": f"{variacion:,.2f}%"
                    })

                comparacion_df = pd.DataFrame(comparacion)

                mostrar_comparacion(comparacion_df)
                mostrar_poligonos(df_r1, df_r2, st.session_state.seleccionados)

                excel_data = generar_excel(df_r1, df_r2, comparacion_df)
                st.download_button("📥 7. Exportar datos a Excel", data=excel_data, file_name="comparacion_ventas.xlsx")

if __name__ == "__main__":
    main()
