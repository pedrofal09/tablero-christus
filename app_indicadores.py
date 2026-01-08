import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
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
COLOR_ACCENT = "#e67e22"

# RUTA DE LA BASE DE DATOS
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

# Mapeo de Tablas Operativas
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
        border-radius: 12px; 
        padding: 20px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); 
        text-align: center; 
        border-left: 5px solid {COLOR_PRIMARY};
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }}
    .kpi-card:hover {{ transform: translateY(-5px); }}
    .kpi-title {{ font-size: 14px; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
    .kpi-value {{ font-size: 32px; color: {COLOR_SECONDARY}; font-weight: 800; margin-top: 5px; }}
    .stAlert {{ margin-top: 1rem; }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. GESTIÓN DE CONEXIÓN Y AUTO-REPARACIÓN
# ==============================================================================

def get_connection():
    """Devuelve la conexión a la BD, creándola si no existe."""
    path = DB_NAME_LOCAL
    if os.path.exists(DB_PATH_ABSOLUTE):
        path = DB_PATH_ABSOLUTE
    
    conn = sqlite3.connect(path, check_same_thread=False)
    return conn, path

def init_db():
    """Crea las tablas necesarias si no existen."""
    conn, _ = get_connection()
    c = conn.cursor()

    try:
        c.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE NOT NULL, rol TEXT, area_acceso TEXT)")
        cols = [info[1] for info in c.execute("PRAGMA table_info(usuarios)")]
        if 'contrasena' not in cols:
            try: c.execute("ALTER TABLE usuarios ADD COLUMN contrasena TEXT DEFAULT '1234'")
            except: pass 
    except Exception as e:
        print(f"Error init usuarios: {e}")

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

init_db()

# ==============================================================================
# 2. FUNCIONES DE LECTURA E INTELIGENCIA
# ==============================================================================

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.upper().strip()

def buscar_columna_inteligente(df, palabras_clave):
    """Busca una columna que contenga alguna de las palabras clave."""
    cols_norm = {normalize_text(c): c for c in df.columns}
    for kw in palabras_clave:
        kw_norm = normalize_text(kw)
        for col_n, col_real in cols_norm.items():
            if kw_norm == col_n: # Prioridad coincidencia exacta
                return col_real
    # Si no hay exacta, buscar parcial
    for kw in palabras_clave:
        kw_norm = normalize_text(kw)
        for col_n, col_real in cols_norm.items():
            if kw_norm in col_n:
                return col_real
    return None

def autenticar(user, pwd):
    conn, _ = get_connection()
    try:
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
        if nombre_objetivo in tablas: return nombre_objetivo
        for t in tablas:
            if t.lower() == nombre_objetivo.lower(): return t
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
# 3. FUNCIONES DE ESCRITURA (GESTOR)
# ==============================================================================

def crear_usuario_bd(usuario, contrasena, rol, area):
    conn, _ = get_connection()
    try:
        cols = [info[1] for info in conn.execute("PRAGMA table_info(usuarios)")]
        col_pwd = 'contrasena' if 'contrasena' in cols else 'password'
        conn.execute(f"INSERT INTO usuarios (usuario, {col_pwd}, rol, area_acceso) VALUES (?, ?, ?, ?)", (usuario, contrasena, rol, area))
        conn.commit()
        return True, "Usuario creado exitosamente."
    except sqlite3.IntegrityError: return False, "El usuario ya existe."
    except Exception as e: return False, f"Error: {e}"
    finally: conn.close()

def cargar_dataframe_bd(df, nombre_tabla, modo='append', anio_sel=None, mes_sel=None):
    conn, _ = get_connection()
    try:
        # Asegurar columnas de periodo
        col_anio = buscar_columna_inteligente(df, ['ANIO', 'YEAR', 'PERIODO_ANIO'])
        col_mes = buscar_columna_inteligente(df, ['MES', 'MONTH', 'PERIODO_MES'])
        
        # Si no existen en el archivo o están vacías, usamos las seleccionadas
        if not col_anio and anio_sel:
            df['PERIODO_ANIO'] = anio_sel
        elif col_anio and anio_sel:
             # Opcional: Rellenar vacíos con la selección
             df[col_anio] = df[col_anio].fillna(anio_sel)

        if not col_mes and mes_sel:
            df['PERIODO_MES'] = mes_sel
        elif col_mes and mes_sel:
             df[col_mes] = df[col_mes].fillna(mes_sel)

        df['fecha_carga'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df.columns = df.columns.astype(str)
        
        df.to_sql(nombre_tabla, conn, if_exists=modo, index=False)
        return True, f"✅ Éxito: {len(df)} registros procesados."
    except Exception as e: return False, f"❌ Error SQL: {e}"
    finally: conn.close()

def obtener_imagen_local(path, default=None):
    if os.path.exists(path): return path
    return default

# ==============================================================================
# INTERFAZ PRINCIPAL
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
    
    # Menú Principal
    opciones_menu = ["🚀 Dashboard Gerencial", "📊 Indicadores", "📈 Tablero Operativo"]
    
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
# FUNCIONES COMUNES DE FILTRADO
# ==============================================================================
def filtrar_por_periodo(df, anio, mes):
    """Filtra un DataFrame genérico por Año y Mes usando búsqueda inteligente de columnas."""
    if df.empty: return df
    
    df_filtrado = df.copy()
    
    # 1. Filtro Año
    col_anio = buscar_columna_inteligente(df_filtrado, ['ANIO', 'YEAR', 'PERIODO_ANIO'])
    if col_anio and anio:
        df_filtrado = df_filtrado[df_filtrado[col_anio].astype(str) == str(anio)]
        
    # 2. Filtro Mes
    if mes and mes != "Todos":
        col_mes = buscar_columna_inteligente(df_filtrado, ['MES', 'MONTH', 'PERIODO_MES'])
        if col_mes:
            mes_norm = normalize_text(mes)
            # Normalizamos la columna para comparar
            df_filtrado['TEMP_MES_NORM'] = df_filtrado[col_mes].astype(str).apply(normalize_text)
            df_filtrado = df_filtrado[df_filtrado['TEMP_MES_NORM'] == mes_norm].drop(columns=['TEMP_MES_NORM'])
            
    return df_filtrado

# ==============================================================================
# MÓDULO 1: DASHBOARD GERENCIAL
# ==============================================================================
if nav == "🚀 Dashboard Gerencial":
    st.markdown("### Visión Estratégica Integral")
    
    # --- FILTROS GLOBALES ---
    st.markdown("##### 📅 Filtros de Periodo")
    col_f1, col_f2 = st.columns(2)
    anio_dash = col_f1.selectbox("Seleccionar Año:", LISTA_ANIOS, index=0)
    mes_dash = col_f2.selectbox("Seleccionar Mes:", ["Todos"] + LISTA_MESES, index=0)
    st.markdown("---")
    
    # 1. Obtener Datos Crudos
    df_fact, _ = obtener_datos('FACTURACION', 'ope_facturacion')
    df_rad, _ = obtener_datos('RADICACION', 'ope_radicacion')
    df_cart, _ = obtener_datos('CARTERA', 'ope_cartera')
    df_adm, _ = obtener_datos('ADMISIONES', 'ope_admisiones')
    df_ind, _ = obtener_datos('INDICADORES', 'catalogo_indicadores')

    # 2. Aplicar Filtros
    df_fact_f = filtrar_por_periodo(df_fact, anio_dash, mes_dash)
    df_rad_f = filtrar_por_periodo(df_rad, anio_dash, mes_dash)
    df_cart_f = filtrar_por_periodo(df_cart, anio_dash, mes_dash)
    df_adm_f = filtrar_por_periodo(df_adm, anio_dash, mes_dash)
    
    # Nota: Los indicadores a veces no tienen columna fecha si son solo catálogo. 
    # Si tienen histórico, se filtran igual.
    df_ind_f = filtrar_por_periodo(df_ind, anio_dash, mes_dash)

    # --- TARJETAS KPI ---
    col1, col2, col3, col4 = st.columns(4)
    
    # KPI 1: Facturación
    col_val_fact = buscar_columna_inteligente(df_fact_f, ['VALOR', 'FACTURADO', 'TOTAL'])
    total_fact = df_fact_f[col_val_fact].sum() if not df_fact_f.empty and col_val_fact else 0
    
    with col1:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Facturación</div><div class="kpi-value">${total_fact:,.0f}</div></div>""", unsafe_allow_html=True)

    # KPI 2: Radicación
    col_val_rad = buscar_columna_inteligente(df_rad_f, ['VALOR', 'RADICADO'])
    total_rad = df_rad_f[col_val_rad].sum() if not df_rad_f.empty and col_val_rad else 0
    
    with col2:
        st.markdown(f"""<div class="kpi-card" style="border-left-color: {COLOR_ACCENT}"><div class="kpi-title">Radicación</div><div class="kpi-value">${total_rad:,.0f}</div></div>""", unsafe_allow_html=True)

    # KPI 3: Recaudo
    col_val_recaudo = buscar_columna_inteligente(df_cart_f, ['RECAUDO', 'REAL'])
    total_recaudo = df_cart_f[col_val_recaudo].sum() if not df_cart_f.empty and col_val_recaudo else 0
    
    with col3:
        st.markdown(f"""<div class="kpi-card" style="border-left-color: #27ae60"><div class="kpi-title">Recaudo</div><div class="kpi-value">${total_recaudo:,.0f}</div></div>""", unsafe_allow_html=True)

    # KPI 4: Admisiones
    col_adm_cant = buscar_columna_inteligente(df_adm_f, ['CANTIDAD', 'ACTIVIDADES', 'PACIENTES'])
    total_adm = df_adm_f[col_adm_cant].sum() if not df_adm_f.empty and col_adm_cant else 0
    
    with col4:
        st.markdown(f"""<div class="kpi-card" style="border-left-color: #3498db"><div class="kpi-title">Admisiones</div><div class="kpi-value">{total_adm:,.0f}</div></div>""", unsafe_allow_html=True)

    # --- GRÁFICOS ESTRATÉGICOS ---
    c_chart1, c_chart2 = st.columns(2)

    with c_chart1:
        st.subheader("📊 Tendencia Financiera (Anual)")
        # Para tendencia usamos los datos SIN filtro de mes, pero CON filtro de año
        df_fact_y = filtrar_por_periodo(df_fact, anio_dash, "Todos")
        df_rad_y = filtrar_por_periodo(df_rad, anio_dash, "Todos")
        
        datos_grafico = []
        def agregar_serie(df_in, col_v, etiqueta):
            if df_in.empty or not col_v: return
            col_m = buscar_columna_inteligente(df_in, ['MES', 'MONTH'])
            if col_m:
                agrupado = df_in.groupby(col_m)[col_v].sum().reset_index()
                # Ordenar por mes lógico
                agrupado['Mes_Num'] = agrupado[col_m].apply(lambda x: LISTA_MESES.index(x) if x in LISTA_MESES else 99)
                agrupado = agrupado.sort_values('Mes_Num')
                for _, r in agrupado.iterrows():
                    datos_grafico.append({'Mes': r[col_m], 'Valor': r[col_v], 'Tipo': etiqueta})

        agregar_serie(df_fact_y, col_val_fact, 'Facturado')
        agregar_serie(df_rad_y, col_val_rad, 'Radicado')
        
        if datos_grafico:
            fig = px.line(pd.DataFrame(datos_grafico), x='Mes', y='Valor', color='Tipo', markers=True,
                          color_discrete_map={'Facturado': COLOR_PRIMARY, 'Radicado': COLOR_ACCENT})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay suficientes datos temporales para graficar tendencias.")

    with c_chart2:
        st.subheader("🏢 Top Aseguradoras (Periodo Actual)")
        # Usamos los datos filtrados por mes y año
        col_aseg = buscar_columna_inteligente(df_fact_f, ['ASEGURADORA', 'CLIENTE', 'EPS'])
        
        if not df_fact_f.empty and col_aseg and col_val_fact:
            df_top = df_fact_f.groupby(col_aseg)[col_val_fact].sum().reset_index().sort_values(col_val_fact, ascending=False).head(7)
            fig2 = px.bar(df_top, x=col_val_fact, y=col_aseg, orientation='h', text_auto='.2s', color=col_val_fact)
            fig2.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Faltan datos de Aseguradora/Valor para este periodo.")

    # --- SECCIÓN INDICADORES (KPIs) ---
    st.markdown("### 🚦 Estado de Indicadores")
    if not df_ind_f.empty:
        st.dataframe(df_ind_f, use_container_width=True)
    else:
        st.info("No hay indicadores registrados para este periodo.")


# ==============================================================================
# MÓDULO 2: INDICADORES (DETALLE)
# ==============================================================================
elif nav == "📊 Indicadores":
    df, _ = obtener_datos("INDICADORES", "catalogo_indicadores")
    
    if df.empty:
        st.warning("No hay indicadores. Ve a 'Gestión y Carga' para subir el archivo base.")
    else:
        df.columns = [normalize_text(c) for c in df.columns]
        col_area = next((c for c in df.columns if 'AREA' in c), None)
        
        if col_area:
            if normalize_text(area_usuario) not in ['TODAS', 'ALL'] and normalize_text(rol_usuario) not in ['ADMIN', 'CEO']:
                df = df[df[col_area].apply(normalize_text) == normalize_text(area_usuario)]
        
        st.dataframe(df, use_container_width=True)

# ==============================================================================
# MÓDULO 3: TABLERO OPERATIVO (DETALLE)
# ==============================================================================
elif nav == "📈 Tablero Operativo":
    tabs = st.tabs(list(MAPA_TABLAS_OPERATIVAS.keys()))
    
    for i, (nombre_ui, nombre_tabla) in enumerate(MAPA_TABLAS_OPERATIVAS.items()):
        with tabs[i]:
            df, real_name = obtener_datos(nombre_ui, nombre_tabla)
            
            if not df.empty:
                # Filtros Locales por Pestaña
                c1, c2 = st.columns(2)
                
                df_view = df.copy()
                col_anio = buscar_columna_inteligente(df_view, ['ANIO', 'YEAR', 'PERIODO_ANIO'])
                col_mes = buscar_columna_inteligente(df_view, ['MES', 'MONTH', 'PERIODO_MES'])
                
                sel_a, sel_m = None, None
                
                if col_anio:
                    anios = sorted(df_view[col_anio].astype(str).unique())
                    sel_a = c1.multiselect(f"Año", anios, key=f"fa_{i}")
                    if sel_a: df_view = df_view[df_view[col_anio].astype(str).isin(sel_a)]
                
                if col_mes:
                    meses = df_view[col_mes].astype(str).unique()
                    sel_m = c2.multiselect(f"Mes", meses, key=f"fm_{i}")
                    if sel_m: df_view = df_view[df_view[col_mes].astype(str).isin(sel_m)]
                
                st.dataframe(df_view, use_container_width=True)
                st.caption(f"Registros: {len(df_view)}")
            else:
                st.info(f"Sin datos en {nombre_ui}.")

# ==============================================================================
# MÓDULO 4: GESTIÓN Y CARGA
# ==============================================================================
elif nav == "📂 Gestión y Carga":
    st.markdown("### 🛠️ Centro de Control de Datos")
    
    tab_carga, tab_usr, tab_brand = st.tabs(["📤 Carga Masiva", "👤 Usuarios", "🎨 Marca"])
    
    # --- PESTAÑA 1: CARGA DE ARCHIVOS ---
    with tab_carga:
        st.subheader("Alimentar Bases de Datos")
        
        tipo_carga = st.selectbox("¿Qué desea cargar?", ["Indicadores (Catálogo)", "Datos Operativos"])
        
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
            
            # Selectores de Periodo para inyección
            c1, c2 = st.columns(2)
            anio = c1.selectbox("Año de los datos:", LISTA_ANIOS)
            mes = c2.selectbox("Mes de los datos:", LISTA_MESES)
            
            f = st.file_uploader(f"Archivo para {proceso}", type=['csv', 'xlsx'])
            modo = st.radio("Modo:", ["Agregar (Append)", "Reemplazar Todo (Replace)"])
            
            if f and st.button(f"Cargar a {proceso}"):
                try:
                    df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
                    
                    modo_sql = 'append' if 'Append' in modo else 'replace'
                    # Pasamos anio y mes para que la función los inyecte si faltan
                    ok, msg = cargar_dataframe_bd(df, tabla_destino, modo=modo_sql, anio_sel=anio, mes_sel=mes)
                    
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
