import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Tablero Ciclo de Ingresos", layout="wide", page_icon="📊")

# --- ARCHIVO DE DATOS ---
# Aquí se guardarán los resultados. Si no existe, se crea.
ARCHIVO_DATOS = 'datos_indicadores_historico.csv'

# --- DATOS MAESTROS (Tus 27 indicadores oficiales) ---
# Estructura: [Área, Responsable, Indicador, Meta_Valor, Lógica (MAX/MIN), Meta_Texto]
DATOS_MAESTROS = [
    # FACTURACIÓN
    ['FACTURACIÓN', 'Dir. Facturación', 'Facturación oportuna (≤72h egreso)', 0.95, 'MAX', '>95%'],
    ['FACTURACIÓN', 'Dir. Facturación', 'Radicación oportuna (≤22 días)', 0.98, 'MAX', '>98%'],
    ['FACTURACIÓN', 'Dir. Facturación', 'Cierre de cargos abiertos (≤30 días)', 0.90, 'MAX', '>90%'],
    ['FACTURACIÓN', 'Dir. Facturación', 'Depuración de vigencias anteriores', 0.02, 'MIN', '<2%'],
    
    # CUENTAS MÉDICAS
    ['CUENTAS MÉDICAS', 'Jefatura Cuentas Médicas', '% de glosas aceptadas en el mes', 0.02, 'MIN', '<2%'],
    ['CUENTAS MÉDICAS', 'Jefatura Cuentas Médicas', '% de glosas respondidas en ≤7 días hábiles', 0.50, 'MAX', '>50%'],
    ['CUENTAS MÉDICAS', 'Jefatura Cuentas Médicas', '% de devoluciones de facturas respondidas oportunamente', 0.30, 'MAX', '>30%'],
    ['CUENTAS MÉDICAS', 'Jefatura Cuentas Médicas', '% de cumplimiento del cronograma de conciliaciones con entidades', 1.00, 'MAX', '100%'],
    ['CUENTAS MÉDICAS', 'Jefatura Cuentas Médicas', '% efectividad en conciliación', 0.75, 'MAX', '>75%'],
    
    # ADMISIONES
    ['ADMISIONES', 'Coordinación Admisiones', '% de facturas anuladas por falta de autorización', 0.01, 'MIN', '≤ 1%'],
    ['ADMISIONES', 'Coordinación Admisiones', '% de facturas anuladas por error en datos de identificación', 0.005, 'MIN', '≤ 0.5%'],
    ['ADMISIONES', 'Coordinación Admisiones', '% de facturas anuladas por error en escogencia del tipo de usuario', 0.005, 'MIN', '≤ 0.5%'],
    ['ADMISIONES', 'Coordinación Admisiones', '% de facturas anuladas por error en selección de asegurador', 0.005, 'MIN', '≤ 0.5%'],
    ['ADMISIONES', 'Coordinación Admisiones', '% de quejas por actitud de servicio en admisión', 0.02, 'MIN', '≤ 2%'],
    
    # AUTORIZACIONES
    ['AUTORIZACIONES', 'Coord. Autorizaciones', '% de autorizaciones de urgencias y hospitalización generadas en ≤7 horas', 1.00, 'MAX', '100%'],
    ['AUTORIZACIONES', 'Coord. Autorizaciones', '% de autorizaciones de urgencias y hospitalización generadas en ≤9 horas', 0.60, 'MIN', '< 60%'],
    ['AUTORIZACIONES', 'Coord. Autorizaciones', '% de solicitudes de tecnologias no convenidas gestionadas integralmente', 0.70, 'MAX', '≥ 70%'],
    ['AUTORIZACIONES', 'Coord. Autorizaciones', '% de solicitudes de tecnologías no cubiertas de planes voluntarios gestionadas', 1.00, 'MAX', '100%'],
    ['AUTORIZACIONES', 'Coord. Autorizaciones', '% de glosa por falta de autorización o error aceptada ', 1.00, 'MAX', '100%'], 

    # CARTERA
    ['CARTERA', 'Jefatura de Cartera', '% De cumplimiento de la meta de días de rotación de cartera (DSO)', 1.00, 'MAX', '100%'],
    ['CARTERA', 'Jefatura de Cartera', '% de cartera vencida >60 días', 0.60, 'MIN', '< 60%'],
    ['CARTERA', 'Jefatura de Cartera', '% de recaudo sobre facturación del periodo', 0.70, 'MAX', '≥ 70%'],
    ['CARTERA', 'Jefe Cartera', 'Recuperación de Glosa', 0.85, 'MAX', '> 85%'],
    ['CARTERA', 'Jefatura de Cartera', '% de conciliaciones realizadas en el mes', 1.00, 'MAX', '100%'],
    ['CARTERA', 'Jefatura de Cartera', '% de reuniones efectivas con actores clave de clientes pagadores', 1.00, 'MAX', '100%'],
    ['CARTERA', 'Jefatura de Cartera', '% de cumplimiento del comité de cartera mensual', 1.00, 'MAX', '100%'],
    ['CARTERA', 'Jefatura de Cartera', '% de cartera >360 días', 0.36, 'MIN', '< 36%']
]

# Meses de Nov-25 a Dic-26
MESES = ['NOV-25', 'DIC-25', 'ENE-26', 'FEB-26', 'MAR-26', 'ABR-26', 'MAY-26', 
         'JUN-26', 'JUL-26', 'AGO-26', 'SEP-26', 'OCT-26', 'NOV-26', 'DIC-26']

# --- FUNCIONES DE CARGA Y GUARDADO ---
def inicializar_datos():
    """Crea la estructura base si no existe el archivo"""
    cols = ['ÁREA', 'RESPONSABLE', 'INDICADOR', 'META_VALOR', 'LOGICA', 'META_TEXTO'] + MESES
    df = pd.DataFrame(DATOS_MAESTROS, columns=['ÁREA', 'RESPONSABLE', 'INDICADOR', 'META_VALOR', 'LOGICA', 'META_TEXTO'])
    # Asegurar que las columnas de meses existan
    for mes in MESES:
        df[mes] = None 
    return df

def cargar_datos():
    """Carga los datos del CSV o crea uno nuevo"""
    if os.path.exists(ARCHIVO_DATOS):
        try:
            return pd.read_csv(ARCHIVO_DATOS)
        except:
            return inicializar_datos()
    return inicializar_datos()

def guardar_datos(df):
    """Guarda el DataFrame en CSV"""
    df.to_csv(ARCHIVO_DATOS, index=False)

# --- INICIO DE LA APP ---
st.title("🏥 Tablero de Control - Ciclo de Ingresos Christus")
st.markdown("---")

# Cargar estado de los datos
if 'df_datos' not in st.session_state:
    st.session_state.df_datos = cargar_datos()

df = st.session_state.df_datos

# --- BARRA LATERAL (MENÚ) ---
with st.sidebar:
    st.header("Navegación")
    opcion = st.radio("Ir a:", ["📊 Dashboard Gerencial", "📝 Ingreso de Resultados"])
    st.markdown("---")
    
    st.subheader("Gestión de Archivos")
    # Botón para descargar la base de datos actual
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Descargar Base de Datos (CSV)",
        csv,
        "indicadores_christus_backup.csv",
        "text/csv",
        key='download-csv'
    )
    
    # Opción para subir un archivo previo (Backup)
    uploaded_file = st.file_uploader("Subir respaldo (CSV)", type=['csv'])
    if uploaded_file is not None:
        try:
            df_uploaded = pd.read_csv(uploaded_file)
            st.session_state.df_datos = df_uploaded
            guardar_datos(df_uploaded)
            st.success("¡Datos cargados correctamente!")
            st.experimental_rerun()
        except:
            st.error("Error al cargar el archivo.")

# --- VISTA: INGRESO DE DATOS ---
if opcion == "📝 Ingreso de Resultados":
    st.header("Reporte Mensual de Indicadores")
    st.info("Seleccione el Área y el Mes para registrar los resultados obtenidos.")
    
    col1, col2 = st.columns(2)
    with col1:
        area_sel = st.selectbox("Seleccione Área:", df['ÁREA'].unique())
    with col2:
        mes_sel = st.selectbox("Seleccione Mes:", MESES)
    
    # Filtrar datos para esa área
    df_filtrado = df[df['ÁREA'] == area_sel].copy()
    
    st.markdown(f"### Indicadores de {area_sel} - {mes_sel}")
    
    with st.form("formulario_ingreso"):
        valores_ingresados = {}
        for idx, row in df_filtrado.iterrows():
            # Valor actual (si existe)
            val_actual = row[mes_sel] if pd.notna(row[mes_sel]) else 0.0
            val_actual_pct = val_actual * 100 # Mostrar como porcentaje (ej 95.0)
            
            st.markdown(f"**{row['INDICADOR']}**")
            st.caption(f"Responsable: {row['RESPONSABLE']} | Meta: {row['META_TEXTO']}")
            
            valores_ingresados[idx] = st.number_input(
                f"Resultado % para {row['INDICADOR']}", 
                value=float(val_actual_pct),
                step=0.1,
                format="%.2f",
                label_visibility="collapsed"
            )
            st.markdown("---")
            
        submitted = st.form_submit_button("💾 Guardar Resultados")
        
        if submitted:
            # Actualizar el DataFrame principal
            for idx, valor in valores_ingresados.items():
                df.at[idx, mes_sel] = valor / 100 # Guardar como decimal
            
            # Guardar en archivo y estado
            st.session_state.df_datos = df
            guardar_datos(df)
            st.success(f"✅ ¡Datos guardados exitosamente para {area_sel} en {mes_sel}!")

# --- VISTA: DASHBOARD GERENCIAL ---
elif opcion == "📊 Dashboard Gerencial":
    st.header("Tablero de Mando Integral")
    
    # Selector de Indicador
    lista_indicadores = df['INDICADOR'].unique()
    indicador_sel = st.selectbox("🔍 Seleccione Indicador a Analizar:", lista_indicadores)
    
    # Obtener datos del indicador seleccionado
    fila = df[df['INDICADOR'] == indicador_sel].iloc[0]
    
    meta_val = fila['META_VALOR']
    meta_txt = fila['META_TEXTO']
    logica = fila['LOGICA']
    area = fila['ÁREA']
    resp = fila['RESPONSABLE']
    
    # Preparar datos para gráfico
    datos_grafico = []
    meses_grafico = []
    
    ultimo_valor = None
    ultimo_mes = ""
    
    for mes in MESES:
        val = fila[mes]
        meses_grafico.append(mes)
        if pd.notna(val):
            datos_grafico.append(val)
            ultimo_valor = val
            ultimo_mes = mes
        else:
            datos_grafico.append(None) # Para que el gráfico muestre huecos o conecte según se desee
            
    # --- TARJETAS KPI ---
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Meta", meta_txt)
        
    with col2:
        if ultimo_valor is not None:
            # Calcular delta (diferencia) y color
            diff = ultimo_valor - meta_val
            
            # Lógica de color para st.metric
            # Si delta_color es "normal": positivo es verde, negativo es rojo
            # Si delta_color es "inverse": positivo es rojo, negativo es verde
            
            color_mode = "normal"
            if logica == 'MIN': # Menor es mejor
                color_mode = "inverse"
            
            st.metric(f"Último ({ultimo_mes})", f"{ultimo_valor*100:.2f}%", f"{diff*100:.2f}%", delta_color=color_mode)
        else:
            st.metric("Último Resultado", "Sin Datos")
            
    with col3:
        st.info(f"**Área:**\n{area}")
        
    with col4:
        st.info(f"**Responsable:**\n{resp}")

    # --- GRÁFICO DE TENDENCIA (PLOTLY) ---
    fig = go.Figure()
    
    # Línea de Meta
    fig.add_trace(go.Scatter(
        x=meses_grafico, 
        y=[meta_val]*len(meses_grafico),
        mode='lines',
        name='Meta',
        line=dict(color='red', width=2, dash='dash')
    ))
    
    # Línea de Real
    # Filtramos nulos para que la línea no se rompa o para mostrar puntos solo donde hay datos
    meses_con_datos = [m for m, v in zip(meses_grafico, datos_grafico) if v is not None]
    valores_con_datos = [v for v in datos_grafico if v is not None]
    
    fig.add_trace(go.Scatter(
        x=meses_con_datos, 
        y=valores_con_datos,
        mode='lines+markers+text',
        name='Resultado Real',
        line=dict(color='#002060', width=4),
        marker=dict(size=10),
        text=[f"{v*100:.1f}%" for v in valores_con_datos],
        textposition="top center"
    ))
    
    fig.update_layout(
        title=f"Tendencia: {indicador_sel}",
        yaxis_title="Porcentaje",
        yaxis_tickformat='.0%',
        template="plotly_white",
        height=500,
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # --- TABLA DE DATOS ---
    with st.expander("Ver Tabla de Datos Detallada"):
        # Transponer para mostrar meses como filas es a veces más legible, o dejarlo horizontal
        # Mostraremos solo la fila del indicador seleccionado
        st.dataframe(
            df[df['INDICADOR'] == indicador_sel][['INDICADOR'] + MESES].style.format({m: "{:.2%}" if pd.notna(df[df['INDICADOR'] == indicador_sel].iloc[0][m]) else "" for m in MESES})
        )