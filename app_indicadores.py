import streamlit as st
import pandas as pd
import sqlite3
import time
import os
import unicodedata

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

# RUTA DE LA BASE DE DATOS (Intenta ambas rutas)
DB_PATH_ABSOLUTE = r"C:\Users\pedro\OneDrive\GENERAL ANTIGUA\Escritorio\mi_proyecto_inventario\Christus_DB_Master.db"
DB_NAME_LOCAL = "Christus_DB_Master.db"

# Archivos de personalización visual
LOCAL_LOGO_PATH = "logo_christus_custom.png"     
LOCAL_BANNER_PATH = "banner_christus_custom.png" 
DEFAULT_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Christus_Health_Logo.svg/1200px-Christus_Health_Logo.svg.png"

# MAPEO FLEXIBLE (Para búsqueda inteligente)
MAPA_TABLAS_OPERATIVAS = {
    'FACTURACION': ['ope_facturacion', 'facturacion', 'tbl_facturacion'],
    'RADICACION': ['ope_radicacion', 'radicacion', 'tbl_radicacion'],
    'ADMISIONES': ['ope_admisiones', 'admisiones', 'tbl_admisiones'],
    'AUTORIZACIONES': ['ope_autorizaciones', 'autorizaciones', 'tbl_autorizaciones'],
    'CUENTAS MEDICAS': ['ope_cuentas_medicas', 'cuentas_medicas', 'glosas'],
    'CARTERA': ['ope_cartera', 'cartera', 'tbl_cartera'],
    'PROVISION': ['ope_provision', 'provision', 'tbl_provision']
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
    .stAlert {{ margin-top: 1rem; }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNCIONES DE UTILIDAD Y BASE DE DATOS
# ==============================================================================

def normalize_text(text):
    """Elimina tildes y convierte a mayúsculas para comparaciones."""
    if not isinstance(text, str): return str(text)
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.upper().strip()

def get_connection():
    """Conexión robusta con reporte de ruta."""
    # 1. Intentar ruta absoluta
    if os.path.exists(DB_PATH_ABSOLUTE):
        return sqlite3.connect(DB_PATH_ABSOLUTE, check_same_thread=False), DB_PATH_ABSOLUTE
    
    # 2. Intentar ruta local
    if os.path.exists(DB_NAME_LOCAL):
        return sqlite3.connect(DB_NAME_LOCAL, check_same_thread=False), os.path.abspath(DB_NAME_LOCAL)
    
    return None, None

def obtener_imagen_local(path, default=None):
    if os.path.exists(path): return path
    return default

def autenticar(user, pwd):
    conn, path = get_connection()
    if not conn: return None, "No se encontró la Base de Datos"
    
    df = pd.DataFrame()
    try:
        # Intentar leer usuario
        query = "SELECT * FROM usuarios"
        all_users = pd.read_sql(query, conn)
        
        # Filtrado manual en Python para evitar problemas de SQL con columnas 'contraseña' vs 'password'
        # Detectar columna de contraseña
        col_pwd = None
        for c in all_users.columns:
            if normalize_text(c) in ['CONTRASENA', 'PASSWORD', 'CLAVE', 'CONTRASEÑA']:
                col_pwd = c
                break
        
        if col_pwd:
            # Filtrar
            user_match = all_users[
                (all_users['usuario'].astype(str) == user) & 
                (all_users[col_pwd].astype(str) == pwd)
            ]
            if not user_match.empty:
                row = user_match.iloc[0]
                conn.close()
                return {
                    'USUARIO': row['usuario'],
                    'ROL': row.get('rol', 'Usuario'),
                    'AREA_ACCESO': row.get('area_acceso', 'Todas')
                }, None
    except Exception as e:
        conn.close()
        return None, str(e)
        
    conn.close()
    return None, "Usuario o contraseña incorrectos"

def obtener_tablas_disponibles():
    """Lista todas las tablas reales en la BD."""
    conn, _ = get_connection()
    if not conn: return []
    try:
        tablas = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)['name'].tolist()
    except:
        tablas = []
    conn.close()
    return tablas

def buscar_tabla_mejor_coincidencia(nombre_objetivo, lista_candidatos):
    """Busca la tabla en la BD."""
    tablas_bd = obtener_tablas_disponibles()
    tablas_bd_norm = {normalize_text(t): t for t in tablas_bd}
    
    # 1. Búsqueda por lista de candidatos configurada
    for cand in lista_candidatos:
        cand_norm = normalize_text(cand)
        if cand_norm in tablas_bd_norm:
            return tablas_bd_norm[cand_norm]
    
    # 2. Búsqueda parcial (contiene palabra clave)
    clave = normalize_text(nombre_objetivo)
    for t_norm, t_real in tablas_bd_norm.items():
        if clave in t_norm:
            return t_real
            
    return None

def obtener_datos(nombre_categoria, candidatos):
    conn, _ = get_connection()
    if not conn: return pd.DataFrame(), "Sin conexión"
    
    tabla_real = buscar_tabla_mejor_coincidencia(nombre_categoria, candidatos)
    
    if tabla_real:
        try:
            df = pd.read_sql(f"SELECT * FROM {tabla_real}", conn)
            conn.close()
            return df, tabla_real
        except Exception as e:
            conn.close()
            return pd.DataFrame(), str(e)
            
    conn.close()
    return pd.DataFrame(), None

# ==============================================================================
# INTERFAZ DE USUARIO
# ==============================================================================

if 'user_info' not in st.session_state:
    st.session_state.user_info = None

logo_actual = obtener_imagen_local(LOCAL_LOGO_PATH, DEFAULT_LOGO_URL)
banner_actual = obtener_imagen_local(LOCAL_BANNER_PATH, None)

# --- LOGIN ---
if st.session_state.user_info is None:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        try: st.image(logo_actual, width=250)
        except: pass
        st.markdown(f"<h3 style='text-align: center; color: {COLOR_SECONDARY};'>Visualizador Operativo</h3>", unsafe_allow_html=True)
        
        # Diagnóstico de Conexión en Login
        conn_test, path_used = get_connection()
        if conn_test:
            st.success(f"✅ Base de datos conectada")
            st.caption(f"Ruta: {path_used}")
            conn_test.close()
            
            # Verificar si hay usuarios
            if len(obtener_tablas_disponibles()) == 0:
                 st.error("⚠️ La base de datos está vacía (0 tablas). Ejecuta el Gestor de Bases primero.")
        else:
            st.error("❌ No se encontró el archivo 'Christus_DB_Master.db'.")
            st.info(f"Ruta esperada: {DB_PATH_ABSOLUTE}")
        
        with st.form("login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("INGRESAR", use_container_width=True):
                user_data, err = autenticar(u, p)
                if user_data:
                    st.session_state.user_info = user_data
                    st.rerun()
                else:
                    st.error(err)
    st.stop()

# --- DENTRO DE LA APP ---
user = st.session_state.user_info
usuario_rol = user['ROL']
usuario_area_norm = normalize_text(user['AREA_ACCESO'])

# --- SIDEBAR ---
with st.sidebar:
    try: st.image(logo_actual, use_column_width=True)
    except: st.header("Christus")
    
    st.info(f"👤 {user['USUARIO']}\n\nRol: {usuario_rol}\nÁrea: {user['AREA_ACCESO']}")
    
    nav = st.radio("Ir a:", ["📊 Indicadores", "📈 Tablero Operativo"])
    
    st.markdown("---")
    with st.expander("🛠️ Personalizar / Diagnóstico"):
        st.write("**Tablas en BD:**")
        st.code(obtener_tablas_disponibles())
        
        uploaded_logo = st.file_uploader("Logo", type=['png','jpg'], key="l")
        if uploaded_logo: 
            with open(LOCAL_LOGO_PATH, "wb") as f: f.write(uploaded_logo.getbuffer())
            st.rerun()
            
    if st.button("Salir"):
        st.session_state.user_info = None
        st.rerun()

# --- HEADER ---
if banner_actual:
    try: st.image(banner_actual, use_container_width=True)
    except: pass

st.title(nav)

# --- MÓDULO INDICADORES ---
if nav == "📊 Indicadores":
    # Buscar tabla de indicadores (varios nombres posibles)
    df, nombre_tabla = obtener_datos("INDICADORES", ['catalogo_indicadores', 'indicadores', 'base_indicadores'])
    
    if df.empty:
        st.warning("⚠️ No se encontró la tabla de indicadores.")
        st.markdown("Asegúrate de haber cargado el archivo 'BASE INDICADORES' en el Gestor.")
    else:
        # Normalizar columnas para evitar errores de mayúsculas/tildes
        df.columns = [normalize_text(c) for c in df.columns]
        
        # Buscar columna de AREA
        col_area = next((c for c in df.columns if 'AREA' in c), None)
        
        if not col_area:
            st.error("La tabla de indicadores existe pero no tiene columna 'AREA'.")
            st.write("Columnas encontradas:", df.columns.tolist())
        else:
            # LOGICA DE FILTRADO
            # Si es Admin, CEO o tiene acceso "TODAS", ve todo.
            if usuario_area_norm in ['TODAS', 'TODOS', 'ALL'] or normalize_text(usuario_rol) in ['ADMIN', 'CEO', 'ADMIN DELEGADO']:
                df_view = df
                st.success(f"Mostrando todos los registros ({len(df)}) - Modo Admin/Todas")
            else:
                # Filtrar normalizando texto
                df['TEMP_AREA_NORM'] = df[col_area].apply(normalize_text)
                df_view = df[df['TEMP_AREA_NORM'] == usuario_area_norm].drop(columns=['TEMP_AREA_NORM'])
            
            if df_view.empty:
                st.info(f"No hay indicadores asignados al área: {user['AREA_ACCESO']}")
            else:
                st.dataframe(df_view, use_container_width=True)

# --- MÓDULO TABLERO OPERATIVO ---
elif nav == "📈 Tablero Operativo":
    tabs = st.tabs(list(MAPA_TABLAS_OPERATIVAS.keys()))
    
    for i, (nombre_ui, candidatos) in enumerate(MAPA_TABLAS_OPERATIVAS.items()):
        with tabs[i]:
            df, nombre_real = obtener_datos(nombre_ui, candidatos)
            
            if not df.empty:
                st.success(f"✅ Datos cargados desde tabla: **{nombre_real}**")
                
                # Normalizar nombres de columnas para filtros
                df_display = df.copy()
                cols_norm = {c: normalize_text(c) for c in df.columns}
                
                # Intentar filtros de fecha si existen columnas parecidas a 'ANIO' o 'MES'
                col_anio = next((c for c, cn in cols_norm.items() if 'ANIO' in cn or 'YEAR' in cn), None)
                col_mes = next((c for c, cn in cols_norm.items() if 'MES' in cn or 'MONTH' in cn), None)
                
                c1, c2 = st.columns(2)
                if col_anio:
                    anios = sorted(df_display[col_anio].astype(str).unique())
                    sel_a = c1.multiselect(f"Filtrar Año", anios, key=f"fa{i}")
                    if sel_a: df_display = df_display[df_display[col_anio].astype(str).isin(sel_a)]
                    
                if col_mes:
                    meses = df_display[col_mes].astype(str).unique()
                    sel_m = c2.multiselect(f"Filtrar Mes", meses, key=f"fm{i}")
                    if sel_m: df_display = df_display[df_display[col_mes].astype(str).isin(sel_m)]
                
                st.dataframe(df_display, use_container_width=True)
                st.caption(f"Total registros: {len(df_display)}")
                
            else:
                st.warning(f"No se encontraron datos para **{nombre_ui}**.")
                st.markdown(f"**Diagnóstico:** El sistema buscó tablas llamadas: `{candidatos}` pero no existen en la BD.")
                if nombre_real: st.error(f"Error técnico: {nombre_real}")
