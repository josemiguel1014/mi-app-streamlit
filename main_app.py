import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from datetime import datetime

st.set_page_config(layout="wide")

@st.cache_data
def cargar_datos_csv_drive(file_id):
    url = f"https://drive.google.com/uc?id={file_id}"
    df = pd.read_csv(url)
    df["Dia DiaID"] = pd.to_datetime(df["Dia DiaID"], errors='coerce')
    return df.dropna(subset=["Dia DiaID"])

@st.cache_data
def cargar_datos_desde_archivo(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        df["Dia DiaID"] = pd.to_datetime(df["Dia DiaID"], errors='coerce')
        return df.dropna(subset=["Dia DiaID"])
    return None

def generar_excel(df_r1, df_r2, comparacion):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_r1.to_excel(writer, index=False, sheet_name='Fecha Actual')
        df_r2.to_excel(writer, index=False, sheet_name='Fecha Anterior')
        comparacion.to_excel(writer, index=False, sheet_name='Comparación')
    output.seek(0)
    return output

def mostrar_comparacion(comparacion_df):
    st.subheader("📊 Resumen Comparativo")
    st.dataframe(comparacion_df)

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=comparacion_df["Producto"],
        y=comparacion_df["Total Fecha Actual"].apply(lambda x: float(x.replace('$', '').replace(',', ''))),
        name="Fecha Actual", marker_color='blue'
    ))
    fig_bar.add_trace(go.Bar(
        x=comparacion_df["Producto"],
        y=comparacion_df["Total Fecha Anterior"].apply(lambda x: float(x.replace('$', '').replace(',', ''))),
        name="Fecha Anterior", marker_color='orange'
    ))
    fig_bar.update_layout(
        barmode='group',
        title="📊 Comparación de Ventas por Producto",
        xaxis_title="Producto",
        yaxis_title="Ventas"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

def mostrar_poligonos(df_r1, df_r2, productos):
    st.subheader("📈 Polígonos de Frecuencia por Producto")
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

def mostrar_ventas_mensuales(df):
    st.subheader("📈 6. Análisis Mensual por Categoría y Marca")

    # Verifica tipo de fecha
    if not pd.api.types.is_datetime64_any_dtype(df["Dia DiaID"]):
        try:
            df["Dia DiaID"] = pd.to_datetime(df["Dia DiaID"])
        except Exception as e:
            st.error(f"Error al convertir 'Dia DiaID': {e}")
            return

    # Extrae columnas de tiempo
    df["Mes"] = df["Dia DiaID"].dt.strftime('%B')
    df["Mes_Num"] = df["Dia DiaID"].dt.month
    df["Año"] = df["Dia DiaID"].dt.year
    df["Mes_Año"] = df["Dia DiaID"].dt.strftime('%Y, %B')

    # Filtro hasta mayo 2025
    df = df[(df["Año"] == 2025) & (df["Mes_Num"] <= 5)]

    if df.empty:
        st.warning("⚠️ No hay datos disponibles hasta mayo 2025.")
        return

    # CATEGORÍA
    categorias = sorted(df["Sublinea DESC"].dropna().unique())
    categoria_seleccionada = st.selectbox("Selecciona una categoría (Sublinea DESC):", categorias, index=None, placeholder="Elegir...")

    marcas_disponibles = sorted(df[df["Sublinea DESC"] == categoria_seleccionada]["Marca DESC"].dropna().unique()) if categoria_seleccionada else []

    with st.form("form_marcas"):
        marcas_seleccionadas = st.multiselect("Selecciona marcas:", marcas_disponibles)
        submitted = st.form_submit_button("🔍 Mostrar análisis")

    if submitted:
        if not categoria_seleccionada:
            st.warning("⚠️ Por favor selecciona una categoría.")
            return
        if not marcas_seleccionadas:
            st.warning("⚠️ Por favor selecciona al menos una marca.")
            return

        df_categoria = df[df["Sublinea DESC"] == categoria_seleccionada]

        for marca in marcas_seleccionadas:
            df_marca = df_categoria[df_categoria["Marca DESC"] == marca]

            # Agrupar y calcular YoY
            ventas = df_marca.groupby(["Mes_Año", "Mes_Num"])["$ Ventas sin impuestos Totales"].sum().reset_index()
            ventas = ventas.sort_values("Mes_Num")
            ventas["YoY"] = ventas["$ Ventas sin impuestos Totales"].pct_change() * 100

            # Limitar valores extremos de YoY
            max_yoy = ventas["YoY"].abs().max()
            y2_max = min(max(max_yoy * 1.2, 100), 300)

            st.markdown(f"### 📊 Marca: {marca}")

            fig = go.Figure()

            # BARRAS - Ventas (ajustado para evitar superposición)
            fig.add_trace(go.Bar(
                x=ventas["Mes_Año"],
                y=ventas["$ Ventas sin impuestos Totales"] / 1e6,
                name="Ventas (Millones)",
                marker_color='rgba(31, 119, 180, 0.8)',
                yaxis='y1',
                text=[f"${v/1e6:.1f}M" for v in ventas["$ Ventas sin impuestos Totales"]],
                textposition='inside',  # CAMBIO: de 'outside' a 'inside'
                insidetextanchor='start',  # texto pegado al inicio (base de la barra)
                textfont=dict(size=11, color="white")  # texto más pequeño y visible
            ))

            # LÍNEA - % Var YoY (ajuste para evitar colisión)
            fig.add_trace(go.Scatter(
                x=ventas["Mes_Año"],
                y=ventas["YoY"],
                name="% Var YoY",
                mode='lines+markers+text',
                yaxis='y2',
                line=dict(color='rgba(50, 171, 96, 0.9)', width=3),
                marker=dict(size=10, color='rgba(50, 171, 96, 1)'),
                text=[f"{v:.1f}%" if pd.notna(v) else "" for v in ventas["YoY"]],
                textposition='top center',
                textfont=dict(size=11, color="darkgreen"),
                texttemplate="%{text}",  # asegura formato de texto
                textfont_size=11
            ))


            # Layout
            fig.update_layout(
                title=dict(
                    text=f"Tendencia de Ventas y %Var YoY - {marca.upper()} ({categoria_seleccionada.upper()})",
                    x=0.5,
                    font=dict(size=18)
                ),
                xaxis=dict(title="Mes y Año", tickangle=-30),
                yaxis=dict(
                    title="Ventas (Millones $)",
                    side='left',
                    showgrid=False,
                    tickformat=",.1f"
                ),
                yaxis2=dict(
                    title="% Var YoY",
                    overlaying='y',
                    side='right',
                    range=[-y2_max, y2_max],
                    showgrid=False,
                    tickformat=".1f"
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.05,
                    xanchor="center",
                    x=0.5
                ),
                bargap=0.25,
                height=600,
                plot_bgcolor='white'
            )

            st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("📊 Comparador de Ventas por Producto - Clientes Digitales")

    modo_carga = st.radio("Selecciona el origen de datos:", ["Desde Google Drive", "Subir archivo local"])

    df = None
    if modo_carga == "Desde Google Drive":
        FILE_ID = "1FxpQF4Qb6stQUiQ2EVSnsX2TZ8fpgk8_"
        with st.spinner("Cargando datos desde Google Drive..."):
            df = cargar_datos_csv_drive(FILE_ID)
    else:
        archivo_subido = st.file_uploader("📁 Sube tu archivo CSV", type=["csv"])
        if archivo_subido:
            df = cargar_datos_desde_archivo(archivo_subido)

    if df is not None:
        df["Producto Marca"] = (df["Plu DESC"].astype(str) + " - " + df["Marca DESC"].astype(str)).str.upper()
        productos = df["Producto Marca"].dropna().unique().tolist()

        if 'seleccionados' not in st.session_state:
            st.session_state.seleccionados = []
        if 'rango_seleccionado' not in st.session_state:
            st.session_state.rango_seleccionado = False
        if 'mostrar_rangos' not in st.session_state:
            st.session_state.mostrar_rangos = False

        seleccionados = st.multiselect(
            "📌 Selecciona los productos a comparar",
            productos,
            default=st.session_state.seleccionados,
            key="multiselect_productos"
        )

        if st.button("✅ Continuar productos"):
            st.session_state.seleccionados = seleccionados
            st.session_state.mostrar_rangos = True

        if st.session_state.mostrar_rangos and st.session_state.seleccionados:
            df_filtrado = df[df["Producto Marca"].isin(st.session_state.seleccionados)]
            min_fecha = df_filtrado["Dia DiaID"].min().date()
            max_fecha = df_filtrado["Dia DiaID"].max().date()

            st.subheader("📆 Selecciona los rangos de fecha")
            col1, col2 = st.columns(2)
            with col1:
                rango1 = st.date_input("📅 Fecha Actual", [min_fecha, max_fecha], min_value=min_fecha, max_value=max_fecha, key='r1')
            with col2:
                rango2 = st.date_input("📅 Fecha Anterior", [min_fecha, max_fecha], min_value=min_fecha, max_value=max_fecha, key='r2')

            if st.button("✅ Continuar fechas"):
                r1_start, r1_end = pd.to_datetime(rango1[0]), pd.to_datetime(rango1[1])
                r2_start, r2_end = pd.to_datetime(rango2[0]), pd.to_datetime(rango2[1])

                if r1_end <= r2_end:
                    st.error("⚠️ El rango de 'Fecha Actual' debe ser posterior al de 'Fecha Anterior'.")
                else:
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
                    diferencia = v1 - v2
                    variacion = ((v1 / v2 - 1) * 100) if v2 != 0 else 0
                    comparacion.append({
                        "Producto": producto,
                        "Total Fecha Actual": f"${v1:,.2f}",
                        "Total Fecha Anterior": f"${v2:,.2f}",
                        "Diferencia": f"${diferencia:,.2f}",
                        "% Variación": f"{variacion:,.2f}%"
                    })

                comparacion_df = pd.DataFrame(comparacion)

                mostrar_comparacion(comparacion_df)
                mostrar_poligonos(df_r1, df_r2, st.session_state.seleccionados)
                mostrar_ventas_mensuales(df)

                excel_data = generar_excel(df_r1, df_r2, comparacion_df)
                st.download_button("📥 Exportar datos a Excel", data=excel_data, file_name="comparacion_ventas.xlsx")

if __name__ == "__main__":
    main()
