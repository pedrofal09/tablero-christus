import streamlit as st
import pandas as pd
import sqlite3
import time
import os
import unicodedata
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

# RUTA DE LA BASE DE DATOS
# Intenta usar la ruta absoluta, si falla usa la local
DB_PATH_ABSOLUTE = r"C:\Users\pedro\OneDrive\GENERAL ANTIGUA\Escritorio\mi_proyecto_inventario\Christus_DB_Master.db"
DB_NAME_LOCAL = "Christus_DB_Master.db"

# Listas para gestión
LISTA_ANIOS = [2025, 2026, 2027]
LISTA_MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
ROLES_USUARIOS = ["Admin", "Ceo", "Admin Delegado", "Lider"]
AREAS_ACCESO = ["Todas", "Facturación", "Cuentas Medicas", "Admisiones", "Autorizaciones", "Cartera"]

# Mapeo de Tablas Operativas (Coincidencia exacta entre Visualizador y Gestor)
MAPA_TABLAS_OPERATIVAS = {
    'FACTURACION': 'ope_facturacion',
    'RADICACION': 'ope_radicacion',
    'ADMISIONES': 'ope_admisiones',
    'AUTORIZACIONES': 'ope_autorizaciones',
    'CUENTAS MEDICAS': 'ope_cuentas_medicas',
    'CARTERA': 'ope_cartera',
    'PROVISION': 'ope_provision'
}

# Archivos de personalización visual
LOCAL_LOGO_PATH = "logo_christus_custom.png"     
LOCAL_BANNER_PATH = "banner_christus_custom.png" 
DEFAULT_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Christus_Health_Logo.svg/1200px-Christus_Health_Logo.svg.png"

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
# 1. GESTIÓN DE CONEXIÓN Y AUTO-REPARACIÓN
# ==============================================================================

def get_connection():
    """Devuelve la conexión a la BD, creándola si no existe."""
    # Prioridad: Ruta absoluta -> Ruta local -> Crear local
    path = DB_NAME_LOCAL
    if os.path.exists(DB_PATH_ABSOLUTE):
        path = DB_PATH_ABSOLUTE
    
    conn = sqlite3.connect(path, check_same_thread=False)
    return conn, path

def init_db():
    """Crea las tablas necesarias si no existen."""
    conn, _ = get_connection()
    c = conn.cursor()

    # 1. Tabla Usuarios (Auto-reparación de columnas)
    try:
        c.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE NOT NULL, rol TEXT, area_acceso TEXT)")
        # Verificar columna contraseña
        cols = [info[1] for info in c.execute("PRAGMA table_info(usuarios)")]
        if 'contrasena' not in cols:
            try: c.execute("ALTER TABLE usuarios ADD COLUMN contrasena TEXT DEFAULT '1234'")
            except: pass # Si falla es porque ya existe con otro nombre o sqlite viejo
    except Exception as e:
        print(f"Error init usuarios: {e}")

    # 2. Tabla Indicadores
    c.execute("""
        CREATE TABLE IF NOT EXISTS catalogo_indicadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area TEXT,
            responsable TEXT,
            indicador TEXT,
            fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Ejecutar inicialización al cargar el script
init_db()

# ==============================================================================
# 2. FUNCIONES DE LECTURA (VISUALIZADOR)
# ==============================================================================

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.upper().strip()

def autenticar(user, pwd):
    conn, _ = get_connection()
    df = pd.DataFrame()
    try:
        # Intentar leer usuario
        query = "SELECT * FROM usuarios"
        all_users = pd.read_sql(query, conn)
        
        col_pwd = None
        for c in all_users.columns:
            if normalize_text(c) in ['CONTRASENA', 'PASSWORD', 'CLAVE', 'CONTRASEÑA']:
                col_pwd = c
                break
        
        if col_pwd:
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
    return None, "Credenciales incorrectas"

def buscar_tabla_inteligente(conn, nombre_objetivo):
    try:
        tablas = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)['name'].tolist()
        # 1. Exacta
        if nombre_objetivo in tablas: return nombre_objetivo
        # 2. Insensible a mayúsculas
        for t in tablas:
            if t.lower() == nombre_objetivo.lower(): return t
        # 3. Aproximada
        clave = nombre_objetivo.replace('ope_', '')
        for t in tablas:
            if clave in t.lower(): return t
        return None
    except: return None

def obtener_datos(nombre_ui, nombre_tabla_ideal):
    conn, _ = get_connection()
    tabla_real = buscar_tabla_inteligente(conn, nombre_tabla_ideal)
    df = pd.DataFrame()
    if tabla_real:
        try: df = pd.read_sql(f"SELECT * FROM {tabla_real}", conn)
        except: pass
    conn.close()
    return df, tabla_real

# ==============================================================================
# 3. FUNCIONES DE ESCRITURA (GESTOR/CARGA)
# ==============================================================================

def crear_usuario_bd(usuario, contrasena, rol, area):
    conn, _ = get_connection()
    try:
        # Verificar columnas para insert correcto
        cols = [info[1] for info in conn.execute("PRAGMA table_info(usuarios)")]
        col_pwd = 'contrasena' if 'contrasena' in cols else 'password'
        
        conn.execute(
            f"INSERT INTO usuarios (usuario, {col_pwd}, rol, area_acceso) VALUES (?, ?, ?, ?)",
            (usuario, contrasena, rol, area)
        )
        conn.commit()
        return True, "Usuario creado exitosamente."
    except sqlite3.IntegrityError:
        return False, "El usuario ya existe."
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        conn.close()

def cargar_dataframe_bd(df, nombre_tabla, modo='append'):
    conn, _ = get_connection()
    try:
        df.columns = df.columns.astype(str) # Asegurar nombres de columnas string
        df.to_sql(nombre_tabla, conn, if_exists=modo, index=False)
        return True, f"✅ Éxito: {len(df)} registros procesados."
    except Exception as e:
        return False, f"❌ Error SQL: {e}"
    finally:
        conn.close()

def obtener_imagen_local(path, default=None):
    if os.path.exists(path): return path
    return default

# ==============================================================================
# INTERFAZ DE USUARIO PRINCIPAL
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
        st.markdown(f"<h3 style='text-align: center; color: {COLOR_SECONDARY};'>Portal Integral Christus</h3>", unsafe_allow_html=True)
        
        # Diagnóstico
        conn_test, path_used = get_connection()
        if conn_test:
            conn_test.close()
            st.caption(f"Conectado a BD: {path_used}")
        else:
            st.error("Error crítico de conexión a BD")

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

# --- APLICACIÓN ---
user = st.session_state.user_info
rol_usuario = user['ROL']
area_usuario = user['AREA_ACCESO']

# --- SIDEBAR ---
with st.sidebar:
    try: st.image(logo_actual, use_column_width=True)
    except: st.header("Christus")
    
    st.info(f"👤 {user['USUARIO']}\n\nRol: {rol_usuario}")
    
    # Menú extendido con Gestor
    opciones_menu = ["📊 Indicadores", "📈 Tablero Operativo"]
    
    # Solo roles autorizados pueden ver el Gestor de Carga
    if normalize_text(rol_usuario) in ['ADMIN', 'CEO', 'ADMIN DELEGADO', 'LIDER', 'ADMINISTRADOR']:
        opciones_menu.append("📂 Gestión y Carga")
    
    nav = st.radio("Navegación:", opciones_menu)
    
    st.markdown("---")
    if st.button("Salir"):
        st.session_state.user_info = None
        st.rerun()

# --- HEADER ---
if banner_actual:
    try: st.image(banner_actual, use_container_width=True)
    except: pass

st.title(nav)

# ==============================================================================
# MÓDULO 1: INDICADORES (VISUALIZACIÓN)
# ==============================================================================
if nav == "📊 Indicadores":
    df, _ = obtener_datos("INDICADORES", "catalogo_indicadores")
    
    if df.empty:
        st.warning("No hay indicadores. Ve a 'Gestión y Carga' para subir el archivo base.")
    else:
        # Filtros de visualización
        df.columns = [normalize_text(c) for c in df.columns]
        col_area = next((c for c in df.columns if 'AREA' in c), None)
        
        if col_area:
            # Si no es Admin/Todas, filtra
            if normalize_text(area_usuario) not in ['TODAS', 'ALL'] and normalize_text(rol_usuario) not in ['ADMIN', 'CEO']:
                df = df[df[col_area].apply(normalize_text) == normalize_text(area_usuario)]
        
        st.dataframe(df, use_container_width=True)

# ==============================================================================
# MÓDULO 2: TABLERO OPERATIVO (VISUALIZACIÓN)
# ==============================================================================
elif nav == "📈 Tablero Operativo":
    tabs = st.tabs(list(MAPA_TABLAS_OPERATIVAS.keys()))
    
    for i, (nombre_ui, nombre_tabla) in enumerate(MAPA_TABLAS_OPERATIVAS.items()):
        with tabs[i]:
            df, real_name = obtener_datos(nombre_ui, nombre_tabla)
            
            if not df.empty:
                # Filtros de Fecha
                df_view = df.copy()
                cols_norm = {c: normalize_text(c) for c in df.columns}
                col_anio = next((c for c, cn in cols_norm.items() if 'ANIO' in cn or 'YEAR' in cn), None)
                
                if col_anio:
                    anios = sorted(df_view[col_anio].astype(str).unique())
                    sel_a = st.multiselect(f"Año", anios, key=f"fa_{i}")
                    if sel_a: df_view = df_view[df_view[col_anio].astype(str).isin(sel_a)]
                
                st.dataframe(df_view, use_container_width=True)
                st.caption(f"Registros: {len(df_view)}")
            else:
                st.info(f"Sin datos en {nombre_ui}. Usa 'Gestión y Carga' para alimentar esta base.")

# ==============================================================================
# MÓDULO 3: GESTIÓN Y CARGA (ADMINISTRACIÓN)
# ==============================================================================
elif nav == "📂 Gestión y Carga":
    st.markdown("### 🛠️ Centro de Control de Datos")
    
    tab_carga, tab_usr, tab_brand = st.tabs(["📤 Carga Masiva", "👤 Usuarios", "🎨 Marca"])
    
    # --- PESTAÑA 1: CARGA DE ARCHIVOS ---
    with tab_carga:
        st.subheader("Alimentar Bases de Datos")
        
        tipo_carga = st.selectbox("¿Qué desea cargar?", ["Indicadores (Catálogo)", "Datos Operativos (Facturación, Cartera...)"])
        
        if tipo_carga == "Indicadores (Catálogo)":
            st.info("Sube el archivo 'BASE INDICADORES.csv'")
            f = st.file_uploader("Archivo Indicadores", type=['csv', 'xlsx'])
            if f and st.button("Procesar Indicadores"):
                try:
                    df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
                    ok, msg = cargar_dataframe_bd(df, "catalogo_indicadores", modo="replace")
                    if ok: st.success(msg)
                    else: st.error(msg)
                except Exception as e: st.error(f"Error: {e}")
                
        else: # Datos Operativos
            proceso = st.selectbox("Seleccione el Proceso:", list(MAPA_TABLAS_OPERATIVAS.keys()))
            tabla_destino = MAPA_TABLAS_OPERATIVAS[proceso]
            
            c1, c2 = st.columns(2)
            anio = c1.selectbox("Año", LISTA_ANIOS)
            mes = c2.selectbox("Mes", LISTA_MESES)
            
            f = st.file_uploader(f"Archivo para {proceso}", type=['csv', 'xlsx'])
            modo = st.radio("Modo:", ["Agregar (Append)", "Reemplazar Todo (Replace)"])
            
            if f and st.button(f"Cargar a {proceso}"):
                try:
                    df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
                    # Estampado de tiempo
                    df['periodo_anio'] = anio
                    df['periodo_mes'] = mes
                    df['fecha_carga'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    modo_sql = 'append' if 'Append' in modo else 'replace'
                    ok, msg = cargar_dataframe_bd(df, tabla_destino, modo=modo_sql)
                    if ok: st.success(msg)
                    else: st.error(msg)
                except Exception as e: st.error(f"Error: {e}")

    # --- PESTAÑA 2: USUARIOS ---
    with tab_usr:
        st.subheader("Crear Nuevo Usuario")
        with st.form("new_user"):
            nu = st.text_input("Usuario")
            np = st.text_input("Contraseña", type="password")
            nr = st.selectbox("Rol", ROLES_USUARIOS)
            na = st.selectbox("Área", AREAS_ACCESO)
            if st.form_submit_button("Crear"):
                if nu and np:
                    ok, msg = crear_usuario_bd(nu, np, nr, na)
                    if ok: st.success(msg)
                    else: st.error(msg)
                else: st.warning("Datos incompletos")
        
        st.markdown("---")
        st.subheader("Usuarios Existentes")
        conn, _ = get_connection()
        try:
            st.dataframe(pd.read_sql("SELECT usuario, rol, area_acceso FROM usuarios", conn), use_container_width=True)
        except: pass
        conn.close()

    # --- PESTAÑA 3: MARCA ---
    with tab_brand:
        st.subheader("Personalización Visual")
        ul = st.file_uploader("Logo", type=['png','jpg'], key="ul")
        if ul:
            with open(LOCAL_LOGO_PATH, "wb") as f: f.write(ul.getbuffer())
            st.success("Logo actualizado")
            
        ub = st.file_uploader("Banner", type=['png','jpg'], key="ub")
        if ub:
            with open(LOCAL_BANNER_PATH, "wb") as f: f.write(ub.getbuffer())
            st.success("Banner actualizado")
