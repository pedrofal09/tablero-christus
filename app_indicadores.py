import streamlit as st
import pandas as pd
import sqlite3
import time
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Tablero Ciclo de Ingresos Christus", 
    layout="wide", 
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

# --- CONSTANTES Y CONFIGURACIÓN ---
COLOR_PRIMARY = "#663399"
COLOR_SECONDARY = "#2c3e50"

# RUTA DE LA BASE DE DATOS (Asegúrate de que esta ruta sea accesible)
DB_PATH = r"C:\Users\pedro\OneDrive\GENERAL ANTIGUA\Escritorio\mi_proyecto_inventario\Christus_DB_Master.db"

# Archivos de personalización visual (Se guardan en la misma carpeta del script)
LOCAL_LOGO_PATH = "logo_christus_custom.png"     
LOCAL_BANNER_PATH = "banner_christus_custom.png" 
DEFAULT_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Christus_Health_Logo.svg/1200px-Christus_Health_Logo.svg.png"

# ORDEN Y MAPEO DE TABLAS (SEGÚN TU REQUERIMIENTO)
MAPA_TABLAS_OPERATIVAS = {
    'FACTURACION': 'ope_facturacion',
    'RADICACION': 'ope_radicacion',
    'ADMISIONES': 'ope_admisiones',
    'AUTORIZACIONES': 'ope_autorizaciones',
    'CUENTAS MEDICAS': 'ope_cuentas_medicas',
    'CARTERA': 'ope_cartera',
    'PROVISION': 'ope_provision'
}

# --- ESTILOS CSS ---
st.markdown(f"""
    <style>
    .main {{ background-color: #f4f6f9; }}
    .stApp {{ background-color: #f4f6f9; }}
    div.block-container {{ padding-top: 1rem; }}
    .kpi-card {{ 
        background-color: #ffffff; 
        border-radius: 10px; 
        padding: 20px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
        text-align: center; 
        border-left: 5px solid {COLOR_PRIMARY};
        margin-bottom: 1rem;
    }}
    .kpi-title {{ font-size: 14px; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }}
    .kpi-value {{ font-size: 28px; color: {COLOR_SECONDARY}; font-weight: 900; margin: 0; }}
    h1, h2, h3 {{ color: {COLOR_PRIMARY}; }}
    .stButton>button {{ background-color: {COLOR_PRIMARY}; color: white; border-radius: 5px; }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# GESTIÓN DE BASE DE DATOS (SOLO LECTURA)
# ==============================================================================

def get_connection():
    # Intentar ruta absoluta
    if os.path.exists(DB_PATH):
        return sqlite3.connect(DB_PATH, check_same_thread=False)
    
    # Intentar ruta relativa (en la misma carpeta)
    if os.path.exists("Christus_DB_Master.db"):
        return sqlite3.connect("Christus_DB_Master.db", check_same_thread=False)
        
    st.error(f"⚠️ No se encuentra la base de datos en: {DB_PATH}")
    st.info("Ejecuta el 'Gestor_Bases_Christus.py' para crearla y cargar datos.")
    st.stop()

def obtener_imagen_local(path, default=None):
    if os.path.exists(path):
        return path
    return default

def autenticar(user, pwd):
    """Verifica usuario y contraseña en la BD."""
    conn = get_connection()
    df = pd.DataFrame()
    
    try:
        # Consulta principal usando la columna creada por el gestor
        query = "SELECT * FROM usuarios WHERE usuario = ? AND contrasena = ?"
        df = pd.read_sql(query, conn, params=(user, pwd))
    except Exception as e:
        # Fallback por si la columna se llama diferente en versiones viejas
        try:
            query = "SELECT * FROM usuarios WHERE usuario = ? AND password = ?"
            df = pd.read_sql(query, conn, params=(user, pwd))
        except:
            st.error(f"Error en autenticación: {e}")
    finally:
        conn.close()
    
    if not df.empty:
        row = df.iloc[0]
        return {
            'USUARIO': row['usuario'],
            'ROL': row.get('rol', 'Usuario'),
            'AREA_ACCESO': row.get('area_acceso', 'Todas')
        }
    return None

def obtener_catalogo_indicadores():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM catalogo_indicadores", conn)
        # Normalizar mayúsculas
        df.columns = [c.upper() for c in df.columns]
    except:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

def buscar_tabla_inteligente(conn, nombre_objetivo):
    """Busca tablas ignorando mayúsculas/minúsculas."""
    try:
        tablas_db = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)['name'].tolist()
        
        # 1. Exacta
        if nombre_objetivo in tablas_db: return nombre_objetivo
        
        # 2. Insensible a mayúsculas
        for t in tablas_db:
            if t.lower() == nombre_objetivo.lower(): return t
            
        # 3. Aproximada (contiene la palabra clave)
        clave = nombre_objetivo.replace('ope_', '')
        for t in tablas_db:
            if clave in t.lower(): return t
            
        return None
    except:
        return None

def obtener_datos_tabla(nombre_tabla_ideal):
    conn = get_connection()
    df = pd.DataFrame()
    nombre_real = nombre_tabla_ideal
    
    tabla_real = buscar_tabla_inteligente(conn, nombre_tabla_ideal)
    
    if tabla_real:
        nombre_real = tabla_real
        try:
            df = pd.read_sql(f"SELECT * FROM {nombre_real}", conn)
        except:
            pass
            
    conn.close()
    return df, nombre_real

# ==============================================================================
# INTERFAZ DE USUARIO
# ==============================================================================

if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# Cargar imágenes personalizadas
logo_actual = obtener_imagen_local(LOCAL_LOGO_PATH, DEFAULT_LOGO_URL)
banner_actual = obtener_imagen_local(LOCAL_BANNER_PATH, None)

# --- PANTALLA DE LOGIN ---
if st.session_state.user_info is None:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        try:
            if logo_actual: st.image(logo_actual, width=250)
        except: pass
            
        st.markdown(f"<h3 style='text-align: center; color: {COLOR_SECONDARY};'>Visualizador Operativo</h3>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            
            if st.form_submit_button("INGRESAR", use_container_width=True):
                user_data = autenticar(u, p)
                if user_data:
                    st.session_state.user_info = user_data
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas.")
        
        st.caption(f"Conexión BD: {DB_PATH}")
    st.stop()

# --- APP PRINCIPAL (DENTRO) ---
user = st.session_state.user_info
usuario_nombre = user['USUARIO']
usuario_rol = user['ROL']
usuario_area = user['AREA_ACCESO']

# --- BARRA LATERAL ---
with st.sidebar:
    try:
        if logo_actual: st.image(logo_actual, use_column_width=True)
    except: st.header("Christus Health")
    
    st.markdown(f"""
        <div style="padding:10px; background:white; border-radius:5px; margin-bottom:10px;">
            <b>👤 {usuario_nombre}</b><br>
            <small>{usuario_rol} | {usuario_area}</small>
        </div>
    """, unsafe_allow_html=True)
    
    modo = st.radio("Navegación:", ["📊 Indicadores (KPIs)", "📈 Tablero Operativo"])
    
    st.markdown("---")
    
    # Personalización Visual
    with st.expander("🎨 Personalizar Identidad"):
        uploaded_logo = st.file_uploader("Logo Sidebar", type=['png', 'jpg'], key="logo")
        if uploaded_logo:
            with open(LOCAL_LOGO_PATH, "wb") as f: f.write(uploaded_logo.getbuffer())
            st.success("Guardado"); time.sleep(1); st.rerun()
            
        uploaded_banner = st.file_uploader("Banner Superior", type=['png', 'jpg'], key="banner")
        if uploaded_banner:
            with open(LOCAL_BANNER_PATH, "wb") as f: f.write(uploaded_banner.getbuffer())
            st.success("Guardado"); time.sleep(1); st.rerun()
            
        if st.button("Restaurar Originales"):
            if os.path.exists(LOCAL_LOGO_PATH): os.remove(LOCAL_LOGO_PATH)
            if os.path.exists(LOCAL_BANNER_PATH): os.remove(LOCAL_BANNER_PATH)
            st.rerun()

    if st.button("Cerrar Sesión"):
        st.session_state.user_info = None
        st.rerun()

# --- CABECERA SUPERIOR ---
if banner_actual:
    try: st.image(banner_actual, use_container_width=True)
    except: pass

st.title(modo.split(" ")[1] + " " + modo.split(" ")[2])

# ------------------------------------------------------------------------------
# MÓDULO 1: INDICADORES
# ------------------------------------------------------------------------------
if "Indicadores" in modo:
    df = obtener_catalogo_indicadores()
    
    if df.empty:
        st.info("No hay indicadores cargados en la base de datos.")
    else:
        # Filtrado por área de usuario
        if usuario_area not in ['Todas', 'TODAS']:
            col_area = 'ÁREA' if 'ÁREA' in df.columns else 'AREA'
            if col_area in df.columns:
                df = df[df[col_area] == usuario_area]
        
        st.markdown(f"**Total Indicadores:** {len(df)}")
        st.dataframe(df, use_container_width=True)

# ------------------------------------------------------------------------------
# MÓDULO 2: TABLERO OPERATIVO (VISOR)
# ------------------------------------------------------------------------------
elif "Tablero Operativo" in modo:
    # Diagnóstico oculto
    with st.expander("🔍 Diagnóstico de Tablas (Técnico)", expanded=False):
        conn = get_connection()
        tbls = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
        st.write("Tablas encontradas:", tbls['name'].tolist())
        conn.close()

    # Pestañas en el orden solicitado
    pestanas = list(MAPA_TABLAS_OPERATIVAS.keys())
    tabs = st.tabs(pestanas)
    
    for i, nombre_pestana in enumerate(pestanas):
        with tabs[i]:
            tabla_ideal = MAPA_TABLAS_OPERATIVAS[nombre_pestana]
            df_tabla, nombre_real_db = obtener_datos_tabla(tabla_ideal)
            
            if not df_tabla.empty:
                # Filtros de año/mes si existen
                c1, c2 = st.columns(2)
                df_view = df_tabla.copy()
                
                if 'periodo_anio' in df_view.columns:
                    anios = sorted(df_view['periodo_anio'].astype(str).unique())
                    sel_anio = c1.multiselect(f"Año ({nombre_pestana})", anios, default=anios, key=f"y_{i}")
                    if sel_anio:
                        df_view = df_view[df_view['periodo_anio'].astype(str).isin(sel_anio)]
                        
                if 'periodo_mes' in df_view.columns:
                    meses = df_view['periodo_mes'].unique()
                    sel_mes = c2.multiselect(f"Mes ({nombre_pestana})", meses, default=meses, key=f"m_{i}")
                    if sel_mes:
                        df_view = df_view[df_view['periodo_mes'].isin(sel_mes)]
                
                st.dataframe(df_view, use_container_width=True)
                st.caption(f"Fuente: {nombre_real_db} | {len(df_view)} registros")
                
                # Descargar
                csv = df_view.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Descargar CSV", csv, f"{nombre_pestana}.csv", "text/csv", key=f"d_{i}")
                
            else:
                st.warning(f"No hay datos para **{nombre_pestana}**.")
                st.info(f"El sistema buscó la tabla '{tabla_ideal}' (o similares) pero no encontró registros.")
