import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
from datetime import datetime

st.set_page_config(layout="wide")

def generar_excel(df_r1, df_r2, comparacion):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_r1.to_excel(writer, index=False, sheet_name='Rango 1')
        df_r2.to_excel(writer, index=False, sheet_name='Rango 2')
        comparacion.to_excel(writer, index=False, sheet_name='Comparación')
    output.seek(0)
    return output

def main():
    st.title("📊Comparador de Ventas por Producto - Clientes Digitales")

    uploaded_file = st.file_uploader("📥 1. Cargar archivo de ventas", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        df["Dia DiaID"] = pd.to_datetime(df["Dia DiaID"], errors='coerce')
        df = df.dropna(subset=["Dia DiaID"])

        productos = df["Plu DESC"].dropna().unique().tolist()

        if 'seleccionados' not in st.session_state:
            st.session_state.seleccionados = []
        if 'mostrar_rangos' not in st.session_state:
            st.session_state.mostrar_rangos = False

        seleccionados = st.multiselect("📌 2. Selecciona los productos a comparar", productos, default=st.session_state.seleccionados)

        if st.button("✅ Continuar"):
            st.session_state.seleccionados = seleccionados
            st.session_state.mostrar_rangos = True

        if st.session_state.mostrar_rangos and st.session_state.seleccionados:
            df_filtrado = df[df["Plu DESC"].isin(st.session_state.seleccionados)]
            min_fecha = df_filtrado["Dia DiaID"].min().date()
            max_fecha = df_filtrado["Dia DiaID"].max().date()

            st.subheader("📆 3. Selecciona los rangos de fecha a comparar")
            col1, col2 = st.columns(2)
            with col1:
                rango1 = st.date_input("Rango 1", [min_fecha, max_fecha], min_value=min_fecha, max_value=max_fecha, key='r1')
            with col2:
                rango2 = st.date_input("Rango 2", [min_fecha, max_fecha], min_value=min_fecha, max_value=max_fecha, key='r2')

            if len(rango1) == 2 and len(rango2) == 2:
                r1_start, r1_end = pd.to_datetime(rango1[0]), pd.to_datetime(rango1[1])
                r2_start, r2_end = pd.to_datetime(rango2[0]), pd.to_datetime(rango2[1])

                df_r1 = df_filtrado[(df_filtrado["Dia DiaID"] >= r1_start) & (df_filtrado["Dia DiaID"] <= r1_end)]
                df_r2 = df_filtrado[(df_filtrado["Dia DiaID"] >= r2_start) & (df_filtrado["Dia DiaID"] <= r2_end)]

                # Polígonos de frecuencia por producto
                for producto in st.session_state.seleccionados:
                    prod_r1 = df_r1[df_r1["Plu DESC"] == producto]
                    prod_r2 = df_r2[df_r2["Plu DESC"] == producto]

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=prod_r1["Dia DiaID"], y=prod_r1["$ Ventas sin impuestos Totales"],
                                             mode='lines+markers', name=f"{producto}, Rango 1", line=dict(color='blue')))
                    fig.add_trace(go.Scatter(x=prod_r2["Dia DiaID"], y=prod_r2["$ Ventas sin impuestos Totales"],
                                             mode='lines+markers', name=f"{producto}, Rango 2", line=dict(color='orange')))
                    fig.update_layout(title=f"📈 Polígono de Frecuencia - {producto}", xaxis_title="Fecha", yaxis_title="Ventas sin impuestos Totales", height=400)
                    st.plotly_chart(fig, use_container_width=True)

                    # Pie chart por producto
                    total_r1 = prod_r1["$ Ventas sin impuestos Totales"].sum()
                    total_r2 = prod_r2["$ Ventas sin impuestos Totales"].sum()
                    fig_pie = px.pie(names=["Rango 1", "Rango 2"], values=[total_r1, total_r2],
                                     title=f"🥧 Distribución de Ventas - {producto}", color_discrete_sequence=['blue', 'orange'])
                    st.plotly_chart(fig_pie, use_container_width=True)

                # Comparación total
                comparacion = []
                for producto in st.session_state.seleccionados:
                    v1 = df_r1[df_r1["Plu DESC"] == producto]["$ Ventas sin impuestos Totales"].sum()
                    v2 = df_r2[df_r2["Plu DESC"] == producto]["$ Ventas sin impuestos Totales"].sum()
                    comparacion.append({"Producto": producto, "Total Rango 1": v1, "Total Rango 2": v2, "Diferencia": v2 - v1})
                comparacion_df = pd.DataFrame(comparacion)

                st.subheader("📊 Resumen Comparativo")
                st.dataframe(comparacion_df)

                # Gráfico de barras comparativas
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(x=comparacion_df["Producto"], y=comparacion_df["Total Rango 1"], name="Rango 1", marker_color='blue'))
                fig_bar.add_trace(go.Bar(x=comparacion_df["Producto"], y=comparacion_df["Total Rango 2"], name="Rango 2", marker_color='orange'))
                fig_bar.update_layout(barmode='group', title="📊 Comparación de Ventas por Producto", xaxis_title="Producto", yaxis_title="Ventas")
                st.plotly_chart(fig_bar, use_container_width=True)

                # Exportar
                excel_data = generar_excel(df_r1, df_r2, comparacion_df)
                st.download_button("📥 7. Exportar datos a Excel", data=excel_data, file_name="comparacion_ventas.xlsx")

if __name__ == "__main__":
    main()
