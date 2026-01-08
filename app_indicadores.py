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
LOCAL_LOGO_PATH = "logo_christus_custom.png"     
LOCAL_BANNER_PATH = "banner_christus_custom.png" 
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
# GESTIÓN DE ARCHIVOS Y BASE DE DATOS
# ==============================================================================

def get_connection():
    if not os.path.exists(DB_PATH):
        st.error(f"⚠️ No se encuentra la base de datos en: {DB_PATH}. Por favor ejecuta primero el script de carga.")
        st.stop()
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def obtener_imagen_local(path, default=None):
    if os.path.exists(path):
        return path
    return default

def autenticar(user, pwd):
    """
    Autentica al usuario de forma robusta, detectando nombres de columnas
    automáticamente para evitar errores de 'no such column'.
    """
    conn = get_connection()
    
    # 1. Inspeccionar columnas reales de la tabla 'usuarios'
    try:
        cursor = conn.execute("PRAGMA table_info(usuarios)")
        columnas_db = [row[1] for row in cursor.fetchall()]
    except Exception as e:
        conn.close()
        st.error(f"Error leyendo estructura de la tabla usuarios: {e}")
        return None

    # 2. Determinar nombre exacto de la columna contraseña
    col_pass = 'contrasena' # Default
    if 'contrasena' not in columnas_db:
        if 'password' in columnas_db: col_pass = 'password'
        elif 'contraseña' in columnas_db: col_pass = 'contraseña'
        elif 'clave' in columnas_db: col_pass = 'clave'
    
    # 3. Determinar nombre exacto de la columna usuario
    col_user = 'usuario'
    if 'usuario' not in columnas_db and 'username' in columnas_db: col_user = 'username'

    # 4. Ejecutar consulta con las columnas detectadas
    try:
        query = f"SELECT * FROM usuarios WHERE {col_user} = ? AND {col_pass} = ?"
        df = pd.read_sql(query, conn, params=(user, pwd))
    except Exception as e:
        st.error(f"Error consultando usuarios: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    
    if not df.empty:
        # Renombrar para estandarizar el uso en la app
        return df.iloc[0].rename({col_user: 'USUARIO', 'rol': 'ROL', 'area_acceso': 'AREA_ACCESO'})
    return None

def verificar_usuarios_existentes():
    conn = get_connection()
    try:
        count = pd.read_sql("SELECT count(*) as total FROM usuarios", conn).iloc[0]['total']
    except:
        count = 0
    conn.close()
    return count

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

# Variables visuales
logo_actual = obtener_imagen_local(LOCAL_LOGO_PATH, DEFAULT_LOGO_URL)
banner_actual = obtener_imagen_local(LOCAL_BANNER_PATH, None)

# --- PANTALLA DE LOGIN ---
if st.session_state.user_info is None:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        try:
            if logo_actual:
                st.image(logo_actual, width=250)
        except:
            st.warning("No se pudo cargar la imagen del logo.")
            
        st.markdown(f"<h3 style='text-align: center; color: {COLOR_SECONDARY};'>Visualizador Operativo</h3>", unsafe_allow_html=True)
        
        # Verificación preventiva
        total_usuarios = verificar_usuarios_existentes()
        if total_usuarios == 0:
            st.warning("⚠️ La base de datos de usuarios está vacía.")
            st.info("Por favor utiliza el 'Script Gestor' para crear al menos un usuario administrador.")
        
        with st.form("login_form"):
            st.info("Ingrese sus credenciales registradas.")
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
    try:
        if logo_actual:
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
    
    op = st.radio("Navegación:", ["📊 Indicadores (KPIs)", "📈 Tablero Operativo"])
    
    st.markdown("---")
    
    # --- SECCIÓN DE PERSONALIZACIÓN VISUAL ---
    with st.expander("🎨 Personalizar Identidad"):
        st.markdown("**1. Logo (Barra Lateral / Login)**")
        uploaded_logo = st.file_uploader("Subir Logo (PNG/JPG)", type=['png', 'jpg', 'jpeg'], key="up_logo")
        
        if uploaded_logo is not None:
            try:
                with open(LOCAL_LOGO_PATH, "wb") as f:
                    f.write(uploaded_logo.getbuffer())
                st.success("Logo actualizado!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        
        st.markdown("**2. Banner (Cabecera Principal)**")
        uploaded_banner = st.file_uploader("Subir Banner (PNG/JPG)", type=['png', 'jpg', 'jpeg'], key="up_banner")
        
        if uploaded_banner is not None:
            try:
                with open(LOCAL_BANNER_PATH, "wb") as f:
                    f.write(uploaded_banner.getbuffer())
                st.success("Banner actualizado!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        if st.button("Restaurar Originales", use_container_width=True):
            try:
                if os.path.exists(LOCAL_LOGO_PATH): os.remove(LOCAL_LOGO_PATH)
                if os.path.exists(LOCAL_BANNER_PATH): os.remove(LOCAL_BANNER_PATH)
                st.rerun()
            except:
                st.error("Error eliminando archivos locales.")

    st.markdown("---")
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.user_info = None
        st.rerun()

# --- CABECERA PRINCIPAL ---
if banner_actual:
    try:
        st.image(banner_actual, use_container_width=True)
    except:
        pass

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
