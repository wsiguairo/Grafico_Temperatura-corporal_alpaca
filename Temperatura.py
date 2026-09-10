# Temperatura.py - VERSIÓN STREAMLIT (con botones de navegación)
# =========================================================
# Adaptación del código de Colab para Streamlit.
# Mantiene INTACTO el diseño de la gráfica.
# Agrega logo SENAMHI + botones de navegación.
# Auto-refresh cada 60 segundos.
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import re
import warnings
import io
import requests
import base64
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

warnings.simplefilter(action='ignore', category=FutureWarning)

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="Gráfica Temperatura Corporal y Clima",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ESTILOS - LOGO SENAMHI + BOTONES + TÍTULO PEQUEÑO
# ============================================================
st.markdown("""
<style>
    .main .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0rem !important;
        max-width: 100% !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    
    header { display: none !important; }
    footer { display: none !important; }
    
    .logo-senamhi {
        position: fixed;
        top: 10px;
        left: 10px;
        z-index: 999999;
        width: 80px;
        height: auto;
        opacity: 0.9;
        transition: all 0.3s ease;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        background: rgba(255, 255, 255, 0.85);
        padding: 4px;
    }
    
    .logo-senamhi:hover {
        opacity: 1;
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    
    /* TÍTULO "SELECCIONAR GRÁFICA" - PEQUEÑO Y SIN NEGRITA */
    .titulo-seleccionar {
        font-size: 13px;
        font-weight: 400;
        color: #555;
        margin: 5px 0 8px 0;
        text-align: left;
    }
    
    /* ESTILO DE BOTONES DE STREAMLIT */
    div[data-testid="stHorizontalBlock"] .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 500;
        font-size: 13px;
        padding: 8px 12px;
        transition: all 0.2s ease;
        line-height: 1.3;
        
        /* BOTÓN TRANSPARENTE CON BORDE PLOMO */
        background-color: transparent !important;
        color: #555555 !important;
        border: 1px solid #D1D5DB !important;
    }

    /* REEMPLAZA EL ROJO POR PLOMO CLARO AL INTERACTUAR */
    div[data-testid="stHorizontalBlock"] .stButton > button:hover,
    div[data-testid="stHorizontalBlock"] .stButton > button:focus,
    div[data-testid="stHorizontalBlock"] .stButton > button:active {
        background-color: #E5E7EB !important; /* Plomo claro sutil */
        color: #111111 !important;
        border-color: #9CA3AF !important;
        box-shadow: none !important;
    }
    
    @media only screen and (max-width: 768px) {
        .logo-senamhi {
            width: 55px;
            top: 5px;
            left: 5px;
            padding: 3px;
            border-radius: 6px;
        }
        .titulo-seleccionar {
            font-size: 12px;
        }
        div[data-testid="stHorizontalBlock"] .stButton > button {
            font-size: 11px;
            padding: 6px 8px;
        }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# MOSTRAR LOGO SENAMHI
# ============================================================
def mostrar_logo_senamhi():
    ruta_logo = "fotosenamhi.png"
    
    if os.path.exists(ruta_logo):
        try:
            with open(ruta_logo, "rb") as f:
                imagen_base64 = base64.b64encode(f.read()).decode()
            
            st.markdown(f"""
            <img src="data:image/png;base64,{imagen_base64}" 
                 class="logo-senamhi" 
                 alt="Logo SENAMHI"
                 title="SENAMHI - Servicio Nacional de Meteorología e Hidrología">
            """, unsafe_allow_html=True)
        except:
            pass

# ============================================================
# URLS DE GOOGLE SHEETS
# ============================================================
URL_CORPORAL = 'https://docs.google.com/spreadsheets/d/1AktP7JsWWtndUpyug005IynsKGfhn-5O-qWowXwhqy4/edit?gid=2146945474#gid=2146945474'
URL_CLIMA = 'https://docs.google.com/spreadsheets/d/1sftR-fLiB00xaA3HWZJocO4NI1daQ_24vYoiI3mNEuk/edit?gid=4165835#gid=4165835'

SHEET_NAME_CLIMA = 'Crucero_alto'
DEPARTAMENTO = 'Puno'

# ============================================================
# FUNCIÓN PARA LEER GOOGLE SHEETS
# ============================================================
@st.cache_data(ttl=60)
def read_google_sheet(url, sheet_name=None):
    file_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if not file_id_match:
        raise ValueError("No se pudo extraer el file_id de la URL")
    file_id = file_id_match.group(1)

    gid_match = re.search(r'gid=([0-9]+)', url)
    if not gid_match:
        raise ValueError("No se pudo extraer el gid de la URL")
    gid = gid_match.group(1)

    export_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv&gid={gid}"

    try:
        response = requests.get(export_url, timeout=30)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error al descargar la hoja: {e}")
        raise
    except Exception as e:
        st.error(f"❌ Error al procesar la hoja: {e}")
        raise

# ============================================================
# FUNCIÓN PARA CONVERTIR FECHAS
# ============================================================
def convertir_fecha_formato_especial(fecha_str):
    if pd.isna(fecha_str):
        return pd.NaT

    try:
        meses_map = {
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'sep': 9, 'set': 9, 'oct': 10, 'nov': 11, 'dic': 12
        }

        partes = str(fecha_str).lower().split('-')
        if len(partes) == 3:
            dia = int(partes[0])
            mes_str = partes[1][:3]
            año = int(partes[2])

            if año < 100:
                año = 2000 + año

            mes = meses_map.get(mes_str, 1)

            return pd.Timestamp(year=año, month=mes, day=dia)
    except:
        pass

    return pd.NaT

# ============================================================
# LEGEND LABELS
# ============================================================
legend_labels = {
    "temp_min": "Temperatura mínima", "vel_viento": "Velocidad Viento", "precipitacion": "Precipitación",
    "temp_cria_hembra": "Temperatura corporal (Cría hembra)", "temp_cria_macho": "Temperatura corporal (Cría macho)",
    "temp_cria": "Temperatura corporal (Crías)", "temp_adulto_hembra": "Temperatura corporal (Adulto hembra)",
    "temp_adulto_macho": "Temperatura corporal (Adulto macho)", "temp_adulto": "Temperatura corporal (Adultos)",
    "enfermos": "Alpacas Enfermas", "muertos": "Alpacas Muertas", "abortos": "Abortos Ocurridos",
    "Rango corporal normal": "Rango temperatura corporal normal"
}

# ============================================================
# FUNCIÓN PRINCIPAL DE LA GRÁFICA (INTACTA)
# ============================================================
def create_interactive_plot(df, cols, title, filename, primary_cols_list, secondary_cols_list,
                            zona_nombre="", departamento=""):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    color_map = {
        "temp_min": "blue", "vel_viento": "orange", "precipitacion": "purple",
        "temp_cria_hembra": "darkorange", "temp_cria_macho": "green",
        "temp_cria": "darkorange", "temp_adulto_hembra": "darkorange",
        "temp_adulto_macho": "green", "temp_adulto": "darkgreen"
    }

    for p in primary_cols_list:
        col_name = cols.get(p)
        if col_name and col_name in df.columns:
            datos_validos = df[['fecha', col_name]].dropna()
            if not datos_validos.empty:
                fig.add_trace(
                    go.Scatter(
                        x=datos_validos['fecha'],
                        y=datos_validos[col_name],
                        name=legend_labels.get(p, col_name),
                        line=dict(color=color_map.get(p), width=3),
                        mode='lines',
                        legendgroup='primary',
                        showlegend=True,
                        hovertemplate=legend_labels.get(p, col_name) + ': %{y:.2f}°C<extra></extra>'
                    ),
                    secondary_y=False
                )

    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="gray",
        line_width=1.5,
        opacity=0.7,
        secondary_y=False,
        showlegend=False
    )

    for s in secondary_cols_list:
        col_name = cols.get(s)
        if col_name and col_name in df.columns:
            datos_validos = df[['fecha', col_name]].dropna()
            if not datos_validos.empty:
                fig.add_trace(
                    go.Scatter(
                        x=datos_validos['fecha'],
                        y=datos_validos[col_name],
                        name=legend_labels.get(s, col_name),
                        line=dict(color=color_map.get(s), width=3),
                        mode='lines',
                        legendgroup='secondary',
                        showlegend=True,
                        hovertemplate=legend_labels.get(s, col_name) + ': %{y:.2f}°C<extra></extra>'
                    ),
                    secondary_y=True
                )

    fig.add_hrect(
        y0=37.0, y1=38.9,
        fillcolor="green",
        opacity=0.2,
        line_width=0,
        secondary_y=True,
        name=legend_labels.get("Rango corporal normal"),
        showlegend=True
    )

    if 'fecha' in df.columns and not df['fecha'].empty:
        columnas_para_verificar = []
        for col_list in [primary_cols_list, secondary_cols_list]:
            for col_key in col_list:
                col_name = cols.get(col_key)
                if col_name and col_name in df.columns:
                    columnas_para_verificar.append(col_name)

        if columnas_para_verificar:
            mask = df[columnas_para_verificar].notna().any(axis=1)
            df_con_datos = df[mask]

            if not df_con_datos.empty:
                meses_con_datos = set()
                for fecha in df_con_datos['fecha'].dropna():
                    if pd.notna(fecha):
                        clave_mes = f"{fecha.year}-{fecha.month:02d}"
                        meses_con_datos.add(clave_mes)

                for clave_mes in sorted(meses_con_datos):
                    year, month = map(int, clave_mes.split('-'))
                    for day in [1, 10, 20]:
                        try:
                            fecha_linea = pd.Timestamp(year=year, month=month, day=day)
                            datos_fecha = df_con_datos[df_con_datos['fecha'] == fecha_linea]
                            if not datos_fecha.empty:
                                if datos_fecha[columnas_para_verificar].notna().any(axis=1).any():
                                    fig.add_vline(
                                        x=fecha_linea,
                                        line_dash="dash",
                                        line_color="gray",
                                        line_width=1,
                                        opacity=0.7,
                                        showlegend=False
                                    )
                        except:
                            pass

    if not df['fecha'].empty:
        fecha_mas_reciente = df['fecha'].max().normalize()
        fecha_actual = pd.Timestamp.now().normalize()
        tiene_datos_futuros = fecha_mas_reciente > fecha_actual

        if tiene_datos_futuros:
            fecha_inicio_zoom = fecha_mas_reciente - pd.DateOffset(months=4)
        else:
            fecha_inicio_zoom = fecha_actual - pd.DateOffset(months=4)

        fecha_min_datos = df['fecha'].min().normalize()
        if fecha_inicio_zoom < fecha_min_datos:
            fecha_inicio_zoom = fecha_min_datos

        fecha_fin_zoom = fecha_mas_reciente + pd.DateOffset(months=1)

        if df[(df['fecha'] >= fecha_inicio_zoom) & (df['fecha'] <= fecha_fin_zoom)].empty:
            fecha_inicio_zoom = df['fecha'].min()
            fecha_fin_zoom = df['fecha'].max()

    fecha_max_ticks = df['fecha'].max() + pd.DateOffset(months=1)
    fecha_min_ticks = df['fecha'].min()

    date_range = pd.date_range(start=fecha_min_ticks, end=fecha_max_ticks, freq='MS')
    tickvals = list(date_range)

    months_es = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    ticktext = [f"{months_es[d.month - 1]} {d.year}" for d in date_range]

    temp_min_col_name = cols.get("temp_min")
    if temp_min_col_name and temp_min_col_name in df.columns:
        datos_temp = df[temp_min_col_name].dropna()
        if not datos_temp.empty:
            min_val = datos_temp.min()
            max_val = datos_temp.max()
            padding = (max_val - min_val) * 0.1 if max_val > min_val else 1
            fig.update_yaxes(
                title_text="Temperatura mínima (°C)",
                title_font=dict(size=20, color="black", family='DejaVu Sans'),
                tickfont=dict(size=14, color="black"),
                range=[min_val - padding, max_val + padding],
                secondary_y=False,
                showline=True,
                linewidth=1,
                linecolor='black',
                zeroline=False
            )
        else:
            fig.update_yaxes(
                title_text="Temperatura mínima (°C)",
                title_font=dict(size=20, color="black", family='DejaVu Sans'),
                tickfont=dict(size=14, color="black"),
                range=[-15, 5],
                secondary_y=False,
                showline=True,
                linewidth=1,
                linecolor='black',
                zeroline=False
            )
    else:
        fig.update_yaxes(
            title_text="Temperatura mínima (°C)",
            title_font=dict(size=20, color="black", family='DejaVu Sans'),
            tickfont=dict(size=14, color="black"),
            range=[-15, 5],
            secondary_y=False,
            showline=True,
            linewidth=1,
            linecolor='black',
            zeroline=False
        )

    fig.update_yaxes(
        title_text="Temperatura corporal (°C)",
        title_font=dict(size=20, color="black", family='DejaVu Sans'),
        tickfont=dict(size=14, color="black"),
        range=[34.0, 40.0],
        tickvals=[34.0, 34.5, 35.0, 35.5, 36.0, 36.5, 37.0, 37.5, 38.0, 38.5, 39.0, 39.5, 40.0],
        secondary_y=True,
        showline=True,
        linewidth=1,
        linecolor='black',
        zeroline=False,
        side='right'
    )

    fig.update_xaxes(
        tickvals=tickvals,
        ticktext=ticktext,
        tickangle=0,
        tickfont=dict(size=12, color="black"),
        showline=True,
        linewidth=1,
        linecolor='black',
        range=[fecha_inicio_zoom, fecha_fin_zoom] if 'fecha_inicio_zoom' in locals() else None,
        rangeslider=dict(visible=False),
        fixedrange=False,
        title_text="Fecha",
        title_font=dict(size=14, color="black")
    )

    sufijo_titulo = ""
    if zona_nombre:
        if departamento:
            sufijo_titulo = f"  —  {zona_nombre} ({departamento})"
        else:
            sufijo_titulo = f"  —  {zona_nombre}"

    titulo_final = f"{title}{sufijo_titulo}"

    fig.update_layout(
        title=dict(
            text=titulo_final,
            font=dict(size=22, family='DejaVu Sans', color="black"),
            x=0.5,
            xanchor='center'
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            xanchor="center",
            x=0.5,
            font=dict(size=14, family='DejaVu Sans', color="black"),
            bgcolor="white",
            bordercolor="black",
            borderwidth=1,
            traceorder="normal",
            itemsizing="constant",
            itemclick="toggle",
            itemdoubleclick="toggleothers",
            groupclick="toggleitem",
            valign='middle',
            itemwidth=30,
            tracegroupgap=15
        ),
        hovermode='x unified',
        template='plotly_white',
        autosize=True,
        width=None,
        height=750,
        margin=dict(l=50, r=50, t=60, b=150),
        plot_bgcolor='white',
        dragmode='pan',
        hoverlabel=dict(
            bgcolor="rgba(255, 255, 255, 0.8)",
            font=dict(size=14, family='DejaVu Sans', color="black"),
            bordercolor="rgba(0, 0, 0, 0.3)",
            namelength=-1
        ),
        yaxis2=dict(
            side='right',
            overlaying='y',
            title_text="Temperatura corporal (°C)",
            title_font=dict(size=18, color="black", family='DejaVu Sans'),
            tickfont=dict(size=12, color="black"),
            range=[34.0, 40.0],
            showline=True,
            linewidth=1,
            linecolor='black'
        )
    )

    return fig

# ============================================================
# CARGA Y PROCESAMIENTO DE DATOS
# ============================================================
@st.cache_data(ttl=60)
def cargar_y_procesar_datos():
    df_clima = read_google_sheet(URL_CLIMA, sheet_name=SHEET_NAME_CLIMA)
    df_temp_corporal = read_google_sheet(URL_CORPORAL, sheet_name='grafX_corporal')

    rename_clima = {}
    patrones_usados = set()
    for col in df_clima.columns:
        col_lower = col.lower()
        if ('temperatura minima' in col_lower or 'temperatura mínima' in col_lower) and 'temperatura_minima' not in patrones_usados:
            rename_clima[col] = 'temperatura_minima'
            patrones_usados.add('temperatura_minima')
        elif 'velocidad de viento' in col_lower and 'velocidad_viento' not in patrones_usados:
            rename_clima[col] = 'velocidad_viento'
            patrones_usados.add('velocidad_viento')
        elif ('precipitacion' in col_lower or 'precipitación' in col_lower) and 'precipitacion' not in patrones_usados:
            rename_clima[col] = 'precipitacion'
            patrones_usados.add('precipitacion')

    if rename_clima:
        df_clima = df_clima.rename(columns=rename_clima)

    rename_corporal = {}
    patrones_usados = set()
    for col in df_temp_corporal.columns:
        col_lower = col.lower()
        if ('t_crias_hembra' in col_lower or 'temp_crias_hembra' in col_lower) and 'temp_cria_hembra' not in patrones_usados:
            rename_corporal[col] = 'temp_cria_hembra'
            patrones_usados.add('temp_cria_hembra')
        elif ('t_crias_macho' in col_lower or 'temp_crias_macho' in col_lower) and 'temp_cria_macho' not in patrones_usados:
            rename_corporal[col] = 'temp_cria_macho'
            patrones_usados.add('temp_cria_macho')
        elif ('t_adulto_hembra' in col_lower or 'temp_adulto_hembra' in col_lower) and 'temp_adulto_hembra' not in patrones_usados:
            rename_corporal[col] = 'temp_adulto_hembra'
            patrones_usados.add('temp_adulto_hembra')
        elif ('t_adulto_macho' in col_lower or 'temp_adulto_macho' in col_lower) and 'temp_adulto_macho' not in patrones_usados:
            rename_corporal[col] = 'temp_adulto_macho'
            patrones_usados.add('temp_adulto_macho')

    if rename_corporal:
        df_temp_corporal = df_temp_corporal.rename(columns=rename_corporal)

    df_clima = df_clima.loc[:, ~df_clima.columns.duplicated()]
    df_temp_corporal = df_temp_corporal.loc[:, ~df_temp_corporal.columns.duplicated()]

    if 'fecha' in df_clima.columns:
        df_clima['fecha'] = df_clima['fecha'].apply(convertir_fecha_formato_especial)

    if 'fecha' in df_temp_corporal.columns:
        df_temp_corporal['fecha'] = df_temp_corporal['fecha'].apply(convertir_fecha_formato_especial)

    for col in ['temperatura_minima', 'velocidad_viento', 'precipitacion']:
        if col in df_clima.columns:
            serie = df_clima[col]
            if isinstance(serie, pd.DataFrame):
                serie = serie.iloc[:, 0]
            df_clima[col] = pd.to_numeric(serie, errors='coerce')

    for col in ['temp_cria_hembra', 'temp_cria_macho', 'temp_adulto_hembra', 'temp_adulto_macho']:
        if col in df_temp_corporal.columns:
            serie = df_temp_corporal[col]
            if isinstance(serie, pd.DataFrame):
                serie = serie.iloc[:, 0]
            df_temp_corporal[col] = pd.to_numeric(serie, errors='coerce')

    if 'temp_cria_hembra' in df_temp_corporal.columns and 'temp_cria_macho' in df_temp_corporal.columns:
        df_temp_corporal['temp_cria'] = df_temp_corporal[['temp_cria_hembra', 'temp_cria_macho']].mean(axis=1)

    if 'temp_adulto_hembra' in df_temp_corporal.columns and 'temp_adulto_macho' in df_temp_corporal.columns:
        df_temp_corporal['temp_adulto'] = df_temp_corporal[['temp_adulto_hembra', 'temp_adulto_macho']].mean(axis=1)

    combined_df = pd.merge(df_clima, df_temp_corporal, on='fecha', how='outer')
    combined_df.sort_values(by='fecha', inplace=True)
    combined_df.drop_duplicates(subset=['fecha'], inplace=True)
    combined_df = combined_df[combined_df['fecha'].notna()]

    def detect_cols(df):
        cols = {}
        cols["temp_min"] = next((c for c in df.columns if 'temperatura_minima' in c), None)
        cols["vel_viento"] = next((c for c in df.columns if 'velocidad_viento' in c), None)
        cols["precipitacion"] = next((c for c in df.columns if 'precipitacion' in c), None)
        cols["temp_cria_hembra"] = next((c for c in df.columns if 'temp_cria_hembra' in c), None)
        cols["temp_cria_macho"] = next((c for c in df.columns if 'temp_cria_macho' in c), None)
        cols["temp_adulto_hembra"] = next((c for c in df.columns if 'temp_adulto_hembra' in c), None)
        cols["temp_adulto_macho"] = next((c for c in df.columns if 'temp_adulto_macho' in c), None)
        cols["temp_cria"] = next((c for c in df.columns if 'temp_cria' in c and 'hembra' not in c and 'macho' not in c), None)
        cols["temp_adulto"] = next((c for c in df.columns if 'temp_adulto' in c and 'hembra' not in c and 'macho' not in c), None)
        return cols

    cols = detect_cols(combined_df)

    return combined_df, cols

# ============================================================
# MAIN
# ============================================================
def main():
    mostrar_logo_senamhi()

    st.markdown("""
    <div style="text-align: center; padding: 0.5rem 0;">
        <h2 style="font-size: clamp(1.2rem, 4vw, 2rem);">🌡️ Temperatura Corporal y Clima - Alpacas</h2>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # BOTONES DE NAVEGACIÓN
    # ============================================================
    if 'grafica_seleccionada' not in st.session_state:
        st.session_state.grafica_seleccionada = 1

    # Título pequeño y sin negrita
    st.markdown('<div class="titulo-seleccionar">Seleccionar gráfica:</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button(
            "📊 Gráfica 1 · Crías m y h",
            use_container_width=True,
            type="primary" if st.session_state.grafica_seleccionada == 1 else "secondary",
            key="btn_g1"
        ):
            st.session_state.grafica_seleccionada = 1
            st.rerun()

    with col2:
        if st.button(
            "📈 Gráfica 2 · Adultos m y h",
            use_container_width=True,
            type="primary" if st.session_state.grafica_seleccionada == 2 else "secondary",
            key="btn_g2"
        ):
            st.session_state.grafica_seleccionada = 2
            st.rerun()

    with col3:
        if st.button(
            "📉 Gráfica 3 · Crías y adultos",
            use_container_width=True,
            type="primary" if st.session_state.grafica_seleccionada == 3 else "secondary",
            key="btn_g3"
        ):
            st.session_state.grafica_seleccionada = 3
            st.rerun()

    st.markdown("---")

    # ============================================================
    # AUTO-REFRESH CADA 60 SEGUNDOS
    # ============================================================
    st_autorefresh(interval=60 * 1000, key="auto_refresh_temp")

    # ============================================================
    # CARGAR DATOS
    # ============================================================
    with st.spinner('🔄 Cargando datos desde Google Sheets...'):
        combined_df, cols = cargar_y_procesar_datos()

    if combined_df is None or combined_df.empty:
        st.error("❌ No hay datos para generar gráficos. Verifica las hojas de Google Sheets.")
        return

    zona_nombre = SHEET_NAME_CLIMA.replace('_', ' ').title()

    # ============================================================
    # GENERAR GRÁFICA SEGÚN SELECCIÓN
    # ============================================================
    with st.spinner('📊 Generando gráfica interactiva...'):
        if st.session_state.grafica_seleccionada == 1:
            fig = create_interactive_plot(
                df=combined_df,
                cols=cols,
                title="Gráfica 1. Influencia de las temperaturas mínimas en alpacas crías machos y hembras",
                filename="grafica1.png",
                primary_cols_list=["temp_min"],
                secondary_cols_list=["temp_cria_hembra", "temp_cria_macho"],
                zona_nombre=zona_nombre,
                departamento=DEPARTAMENTO
            )
        elif st.session_state.grafica_seleccionada == 2:
            fig = create_interactive_plot(
                df=combined_df,
                cols=cols,
                title="Gráfica 2. Influencia de las temperaturas mínimas en alpacas adultos machos y hembras",
                filename="grafica2.png",
                primary_cols_list=["temp_min"],
                secondary_cols_list=["temp_adulto_hembra", "temp_adulto_macho"],
                zona_nombre=zona_nombre,
                departamento=DEPARTAMENTO
            )
        else:
            fig = create_interactive_plot(
                df=combined_df,
                cols=cols,
                title="Gráfica 3. Influencia de las temperaturas mínimas en alpacas crías y adultos",
                filename="grafica3.png",
                primary_cols_list=["temp_min"],
                secondary_cols_list=["temp_cria", "temp_adulto"],
                zona_nombre=zona_nombre,
                departamento=DEPARTAMENTO
            )

    # ============================================================
    # VISUALIZAR GRÁFICA
    # ============================================================
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, config={
            'displayModeBar': True,
            'displaylogo': False,
            'scrollZoom': True,
            'responsive': True
        })

if __name__ == "__main__":
    main()
