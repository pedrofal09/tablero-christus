import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sqlite3
import time
import os
from datetime import datetime

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

# Rutas de Archivos
DB_PATH = r"C:\Users\pedro\OneDrive\GENERAL ANTIGUA\Escritorio\mi_proyecto_inventario\Christus_DB_Master.db"
LOCAL_LOGO_PATH = "logo_christus_custom.png" # Nombre del archivo local para el logo personalizado
DEFAULT_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Christus_Health_Logo.svg/1200px-Christus_Health_Logo.svg.png"

MESES = ['NOV-25', 'DIC-25', 'ENE-26', 'FEB-26', 'MAR-26', 'ABR-26', 'MAY-26', 
         'JUN-26', 'JUL-26', 'AGO-26', 'SEP-26', 'OCT-26', 'NOV-26', 'DIC-26']

MAPA_TABLAS_OPERATIVAS = {
    'ADMISIONES': 'ope_admisiones',
    'FACTURACION': 'ope_facturacion',
    'AUTORIZACIONES': 'ope_autorizaciones',
    'RADICACION': 'ope_radicacion',
    'CUENTAS MEDICAS': 'ope_cuentas_medicas',
    'CARTERA': 'ope_cartera',
    'PROVISION': 'ope_provision'
}

# --- ESTILOS CSS ---
st.markdown(f"""
    <style>
    .main {{ background-color: #f4f6f9; }}
    .stApp {{ background-color: #f4f6f9; }}
    div.block-container {{ padding-top: 2rem; }}
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
# GESTIÓN DE ARCHIVOS Y BASE DE DATOS
# ==============================================================================

def get_connection():
    if not os.path.exists(DB_PATH):
        st.error(f"⚠️ No se encuentra la base de datos en: {DB_PATH}. Por favor ejecuta primero el script de carga.")
        st.stop()
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def obtener_logo_actual():
    """Retorna la ruta del logo local si existe, sino el default."""
    if os.path.exists(LOCAL_LOGO_PATH):
        return LOCAL_LOGO_PATH
    return DEFAULT_LOGO_URL

def autenticar(user, pwd):
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM usuarios WHERE usuario = ? AND contrasena = ?", conn, params=(user, pwd))
    except Exception as e:
        st.error(f"Error consultando usuarios: {e}")
        df = pd.DataFrame()
    conn.close()
    
    if not df.empty:
        return df.iloc[0].rename({'usuario': 'USUARIO', 'rol': 'ROL', 'area_acceso': 'AREA_ACCESO'})
    return None

def obtener_catalogo_indicadores():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM catalogo_indicadores", conn)
    except:
        df = pd.DataFrame(columns=['area', 'responsable', 'indicador'])
    conn.close()
    
    df.columns = [c.upper() for c in df.columns]
    if 'ÁREA' not in df.columns and 'AREA' in df.columns: df.rename(columns={'AREA': 'ÁREA'}, inplace=True)
    if 'INDICADOR' not in df.columns: df['INDICADOR'] = "Sin Nombre"
    
    return df

def obtener_datos_operativos(nombre_tabla):
    conn = get_connection()
    try:
        df = pd.read_sql(f"SELECT * FROM {nombre_tabla}", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

# ==============================================================================
# INTERFAZ DE USUARIO
# ==============================================================================

if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# Variable dinámica del logo
logo_actual = obtener_logo_actual()

# --- PANTALLA DE LOGIN ---
if st.session_state.user_info is None:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Muestra el logo (custom o default)
        try:
            st.image(logo_actual, width=250)
        except:
            st.warning("No se pudo cargar la imagen del logo.")
            
        st.markdown(f"<h3 style='text-align: center; color: {COLOR_SECONDARY};'>Visualizador Operativo</h3>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.info("Ingrese sus credenciales registradas en el Gestor.")
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            
            if st.form_submit_button("INGRESAR", use_container_width=True):
                auth = autenticar(u, p)
                if auth is not None:
                    st.session_state.user_info = auth
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas o usuario no existe.")
        
        st.caption(f"Conectado a: {DB_PATH}")
    st.stop()

# --- APP PRINCIPAL (SOLO VISUALIZACIÓN) ---
user_data = st.session_state.user_info
rol = user_data.get('ROL', 'Usuario')
area_perm = user_data.get('AREA_ACCESO', 'Todas')
user_name = user_data.get('USUARIO', 'Usuario')

# Barra Lateral
with st.sidebar:
    # Logo en Sidebar
    try:
        st.image(logo_actual, use_column_width=True)
    except:
        st.write("🏥 Christus Health")

    st.markdown(f"""
        <div style="background-color: white; padding: 10px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #eee;">
            <div style="font-weight: bold; color: {COLOR_PRIMARY}">👤 {user_name}</div>
            <div style="font-size: 12px; color: #666;">Rol: {rol}</div>
            <div style="font-size: 12px; color: #666;">Área: {area_perm}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Menú
    op = st.radio("Navegación:", ["📊 Indicadores (KPIs)", "📈 Tablero Operativo"])
    
    st.markdown("---")
    
    # --- SECCIÓN DE PERSONALIZACIÓN VISUAL ---
    with st.expander("🎨 Personalizar Identidad"):
        st.write("Sube el logo institucional:")
        uploaded_logo = st.file_uploader("Imagen (PNG/JPG)", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
        
        if uploaded_logo is not None:
            try:
                with open(LOCAL_LOGO_PATH, "wb") as f:
                    f.write(uploaded_logo.getbuffer())
                st.success("¡Logo actualizado!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error guardando imagen: {e}")
        
        if os.path.exists(LOCAL_LOGO_PATH):
            if st.button("Restaurar Logo Original", use_container_width=True):
                try:
                    os.remove(LOCAL_LOGO_PATH)
                    st.rerun()
                except:
                    st.error("No se pudo eliminar el archivo local.")

    st.markdown("---")
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.user_info = None
        st.rerun()

st.title(op.replace('📊 ', '').replace('📈 ', ''))

# 1. VISUALIZADOR DE INDICADORES
if "Indicadores" in op:
    df_ind = obtener_catalogo_indicadores()
    
    if area_perm != 'Todas' and area_perm != 'TODAS' and not df_ind.empty:
        col_area = 'ÁREA' if 'ÁREA' in df_ind.columns else 'AREA'
        if col_area in df_ind.columns:
            df_ind = df_ind[df_ind[col_area] == area_perm]
            
    if df_ind.empty:
        st.info("No hay indicadores cargados en la base de datos o no tienes asignados.")
    else:
        st.markdown("### Catálogo de Indicadores Asignados")
        st.dataframe(df_ind, use_container_width=True)
        st.caption(f"Total Indicadores Visibles: {len(df_ind)}")

# 2. VISUALIZADOR TABLERO OPERATIVO
elif "Tablero Operativo" in op:
    st.info(f"Vista de solo lectura de las bases operativas.")
    
    nombres_tablas = list(MAPA_TABLAS_OPERATIVAS.keys())
    tabs = st.tabs(nombres_tablas)
    
    for i, nombre_ui in enumerate(nombres_tablas):
        with tabs[i]:
            tabla_bd = MAPA_TABLAS_OPERATIVAS[nombre_ui]
            df = obtener_datos_operativos(tabla_bd)
            
            if not df.empty:
                if 'periodo_anio' in df.columns:
                    anios = df['periodo_anio'].unique()
                    st.caption(f"📅 Años disponibles: {list(anios)}")
                
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    f"⬇️ Descargar {nombre_ui}",
                    csv,
                    f"{tabla_bd}.csv",
                    "text/csv",
                    key=f"dl_{i}"
                )
            else:
                st.warning(f"La tabla de **{nombre_ui}** está vacía en la base de datos.")

# Pie de página
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #95a5a6; font-size: 0.8rem;'>"
    "Visualizador Christus Health © 2026"
    "</div>", 
    unsafe_allow_html=True
)
