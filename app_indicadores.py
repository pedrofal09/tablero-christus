import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import time
import json
from datetime import datetime
from PIL import Image

# Intento de importar librerías de Firebase para persistencia real
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Tablero Ciclo de Ingresos Christus", 
    layout="wide", 
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

# --- ARCHIVOS Y CONFIGURACIÓN ---
# Nombres de documentos en Firestore / Archivos locales de respaldo
DOC_USUARIOS = 'usuarios'
DOC_LOGS = 'logs'
DOC_INDICADORES = 'indicadores'
FIRESTORE_COLLECTION = "app_persistence" # Colección única para la app

# Nombres de archivos locales (Fallback)
ARCHIVO_USUARIOS = 'usuarios.csv'
ARCHIVO_DATOS_INDICADORES = 'datos_indicadores_historico.csv'
ARCHIVO_MAESTRO_INDICADORES = 'maestro_indicadores.csv'
ARCHIVO_LOG = 'auditoria_log.csv'

# Imágenes
LOGO_FILENAME = 'logo_config.png'
LOGIN_IMAGE_FILENAME = 'login_image.png'
LOGO_DEFAULT_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Christus_Health_Logo.svg/1200px-Christus_Health_Logo.svg.png"

# Archivos Maestros
FILES_MASTER = {
    'ADMISIONES': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - ADMISIONES.csv',
    'AUTORIZACIONES': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - AUTORIZACIONES.csv',
    'FACTURACION': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - FACTURACION.csv',
    'RADICACION': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - RADICACION.csv',
    'GLOSAS': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - GLOSAS Y DEVOLUCIONES.csv',
    'CARTERA': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - CARTERA.csv',
    'PROVISION': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - PROVISION.csv'
}

# Estructura Columnas
ESTRUCTURA_COLUMNAS = {
    'FACTURACION': ['AÑO', 'MES', 'Ranking', 'Aseguradora / Cliente', 'Valor Facturado', '% Participación'],
    'RADICACION': ['AÑO', 'MES', 'Aseguradora', 'No. Facturas', 'Valor Radicado', 'Fecha Corte'],
    'GLOSAS': ['AÑO', 'MES', 'Aseguradora', 'Valor Devoluciones', 'Valor Glosa Inicial', 'Valor Rechazado', 'Valor Aceptado', '% Gestionado'],
    'CARTERA': ['AÑO', 'MES', 'Aseguradora', 'Saldo Inicial', 'Meta Recaudo', 'Recaudo Real', '% Cumplimiento'],
    'AUTORIZACIONES': ['AÑO', 'MES', 'Tipo Solicitud', 'Gestionadas', 'Aprobadas', 'Pendientes', 'Negadas', '% Efectividad'],
    'ADMISIONES': ['AÑO', 'MES', 'Sede / Concepto', 'MES_LETRAS', 'Cantidad Actividades', 'Valor Estimado Ingreso', 'Promedio por Paciente'],
    'PROVISION': [
        'AÑO', 'MES', 'Aseguradora', 'Fecha Corte', 
        'Prov. Acostados', 'Prov. Ambulatorios', 'Prov. Egresados', 
        'Facturado Sin Radicar', 'Cant. Glosas Pendientes', 'Valor Glosas Pendientes'
    ]
}

# Datos Maestros Iniciales (Hardcoded fallback)
DATOS_MAESTROS_IND_INICIAL = [
    ['FACTURACIÓN', 'Dir. Facturación', 'Facturación oportuna (≤72h egreso)', 0.95, 'MAX', '>95%'],
    ['FACTURACIÓN', 'Dir. Facturación', 'Radicación oportuna (≤22 días)', 0.98, 'MAX', '>98%'],
    ['FACTURACIÓN', 'Dir. Facturación', 'Cierre de cargos abiertos (≤30 días)', 0.90, 'MAX', '>90%'],
    ['FACTURACIÓN', 'Dir. Facturación', 'Depuración de vigencias anteriores', 0.02, 'MIN', '<2%'],
    ['CUENTAS MÉDICAS', 'Jefatura Cuentas Médicas', '% de glosas aceptadas en el mes', 0.02, 'MIN', '<2%'],
    ['CUENTAS MÉDICAS', 'Jefatura Cuentas Médicas', '% de glosas respondidas en ≤7 días hábiles', 0.50, 'MAX', '>50%'],
    ['CUENTAS MÉDICAS', 'Jefatura Cuentas Médicas', '% de devoluciones de facturas respondidas oportunamente', 0.30, 'MAX', '>30%'],
    ['CUENTAS MÉDICAS', 'Jefatura Cuentas Médicas', '% de cumplimiento del cronograma de conciliaciones con entidades', 1.00, 'MAX', '100%'],
    ['CUENTAS MÉDICAS', 'Jefatura Cuentas Médicas', '% efectividad en conciliación', 0.75, 'MAX', '>75%'],
    ['ADMISIONES', 'Coordinación Admisiones', '% de facturas anuladas por falta de autorización', 0.01, 'MIN', '≤ 1%'],
    ['ADMISIONES', 'Coordinación Admisiones', '% de facturas anuladas por error en datos de identificación', 0.005, 'MIN', '≤ 0.5%'],
    ['ADMISIONES', 'Coordinación Admisiones', '% de facturas anuladas por error en escogencia del tipo de usuario', 0.005, 'MIN', '≤ 0.5%'],
    ['ADMISIONES', 'Coordinación Admisiones', '% de facturas anuladas por error en selección de asegurador', 0.005, 'MIN', '≤ 0.5%'],
    ['ADMISIONES', 'Coordinación Admisiones', '% de quejas por actitud de servicio en admisión', 0.02, 'MIN', '≤ 2%'],
    ['AUTORIZACIONES', 'Coord. Autorizaciones', '% de autorizaciones de urgencias y hospitalización generadas en ≤7 horas', 1.00, 'MAX', '100%'],
    ['AUTORIZACIONES', 'Coord. Autorizaciones', '% de autorizaciones de urgencias y hospitalización generadas en ≤9 horas', 0.60, 'MIN', '< 60%'],
    ['AUTORIZACIONES', 'Coord. Autorizaciones', '% de solicitudes de tecnologias no convenidas gestionadas integralmente', 0.70, 'MAX', '≥ 70%'],
    ['AUTORIZACIONES', 'Coord. Autorizaciones', '% de solicitudes de tecnologías no cubiertas de planes voluntarios gestionadas', 1.00, 'MAX', '100%'],
    ['AUTORIZACIONES', 'Coord. Autorizaciones', '% de glosa por falta de autorización o error aceptada ', 1.00, 'MAX', '100%'], 
    ['CARTERA', 'Jefatura de Cartera', '% De cumplimiento de la meta de días de rotación de cartera (DSO)', 1.00, 'MAX', '100%'],
    ['CARTERA', 'Jefatura de Cartera', '% de cartera vencida >60 días', 0.60, 'MIN', '< 60%'],
    ['CARTERA', 'Jefatura de Cartera', '% de recaudo sobre facturación del periodo', 0.70, 'MAX', '≥ 70%'],
    ['CARTERA', 'Jefe Cartera', 'Recuperación de Glosa', 0.85, 'MAX', '> 85%'],
    ['CARTERA', 'Jefatura de Cartera', '% de conciliaciones realizadas en el mes', 1.00, 'MAX', '100%'],
    ['CARTERA', 'Jefatura de Cartera', '% de reuniones efectivas con actores clave de clientes pagadores', 1.00, 'MAX', '100%'],
    ['CARTERA', 'Jefatura de Cartera', '% de cumplimiento del comité de cartera mensual', 1.00, 'MAX', '100%'],
    ['CARTERA', 'Jefatura de Cartera', '% de cartera >360 días', 0.36, 'MIN', '< 36%']
]

MESES = ['NOV-25', 'DIC-25', 'ENE-26', 'FEB-26', 'MAR-26', 'ABR-26', 'MAY-26', 
         'JUN-26', 'JUL-26', 'AGO-26', 'SEP-26', 'OCT-26', 'NOV-26', 'DIC-26']

# CSS
st.markdown("""
    <style>
    .kpi-card { background-color: #ffffff; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; border-left: 5px solid #663399; }
    .kpi-value { font-size: 28px; color: #2c3e50; font-weight: 900; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# GESTIÓN DE BASE DE DATOS (FIREBASE)
# ==============================================================================

@st.cache_resource
def init_firebase():
    """Inicializa Firebase con st.secrets"""
    if not FIREBASE_AVAILABLE:
        return None
    try:
        if not firebase_admin._apps:
            if "firebase" in st.secrets:
                # Convertir st.secrets a dict normal para evitar problemas de tipos
                cred_dict = dict(st.secrets["firebase"])
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            else:
                return None
        return firestore.client()
    except Exception as e:
        print(f"Error Firebase: {e}")
        return None

db = init_firebase()

# ==============================================================================
# FUNCIONES DE PERSISTENCIA (Dual: DB o CSV)
# ==============================================================================

def get_data(doc_name, fallback_csv, default_func=None):
    """Lectura híbrida: Intenta Firestore, luego CSV, luego Default."""
    # 1. Firestore
    if db:
        try:
            doc = db.collection(FIRESTORE_COLLECTION).document(doc_name).get()
            if doc.exists:
                data = doc.to_dict().get('data')
                if data: return pd.read_json(data, orient='split')
        except Exception as e:
            print(f"Error lectura DB {doc_name}: {e}")

    # 2. CSV
    if os.path.exists(fallback_csv):
        try:
            return pd.read_csv(fallback_csv, dtype=str)
        except: pass

    # 3. Default
    if default_func: return default_func()
    return pd.DataFrame()

def save_data(df, doc_name, fallback_csv):
    """Escritura híbrida: Guarda en Firestore y actualiza CSV local."""
    # Local
    try: df.to_csv(fallback_csv, index=False)
    except: pass
    
    # Nube
    if db:
        try:
            json_str = df.to_json(orient='split')
            db.collection(FIRESTORE_COLLECTION).document(doc_name).set({'data': json_str})
            return True
        except Exception as e:
            st.toast(f"Error guardando en nube: {e}")
            return False
    return False

# ==============================================================================
# LÓGICA DE USUARIOS
# ==============================================================================

def crear_admin_default():
    return pd.DataFrame([['Administrador', 'Agosto2025', 'ADMIN', 'TODAS']], 
                        columns=['USUARIO', 'PASSWORD', 'ROL', 'AREA_ACCESO'])

def cargar_usuarios():
    # Cargar usuarios existentes
    df = get_data(DOC_USUARIOS, ARCHIVO_USUARIOS, crear_admin_default)
    
    # Validación de seguridad: Asegurar que el Admin principal exista siempre
    # (Pero NO sobrescribir su contraseña si ya existe y es válida para el sistema)
    if 'Administrador' not in df['USUARIO'].values:
        new_admin = crear_admin_default()
        df = pd.concat([df, new_admin], ignore_index=True)
        save_data(df, DOC_USUARIOS, ARCHIVO_USUARIOS)
        
    return df

def guardar_usuarios_db(df):
    save_data(df, DOC_USUARIOS, ARCHIVO_USUARIOS)

def autenticar(user, pwd):
    df = cargar_usuarios()
    row = df[df['USUARIO'] == user]
    if not row.empty:
        if str(row.iloc[0]['PASSWORD']).strip() == str(pwd).strip():
            return row.iloc[0]
    return None

# ==============================================================================
# FUNCIONES DE LOGS E INDICADORES
# ==============================================================================

def registrar_log(usuario, accion, detalle):
    def def_log(): return pd.DataFrame(columns=['FECHA', 'USUARIO', 'ACCION', 'DETALLE'])
    df = get_data(DOC_LOGS, ARCHIVO_LOG, def_log)
    
    nuevo = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), usuario, accion, detalle]], 
                         columns=['FECHA', 'USUARIO', 'ACCION', 'DETALLE'])
    df = pd.concat([df, nuevo], ignore_index=True)
    save_data(df, DOC_LOGS, ARCHIVO_LOG)

def cargar_logs_view():
    def def_log(): return pd.DataFrame(columns=['FECHA', 'USUARIO', 'ACCION', 'DETALLE'])
    return get_data(DOC_LOGS, ARCHIVO_LOG, def_log)

def cargar_datos_ind():
    def def_ind():
        df = pd.DataFrame(DATOS_MAESTROS_IND_INICIAL, columns=['ÁREA', 'RESPONSABLE', 'INDICADOR', 'META_VALOR', 'LOGICA', 'META_TEXTO'])
        for m in MESES: df[m] = None
        return df
    
    df = get_data(DOC_INDICADORES, ARCHIVO_DATOS_INDICADORES)
    if df.empty: df = def_ind()
    
    # Asegurar columnas de meses
    for m in MESES:
        if m not in df.columns: df[m] = None
    return df

def guardar_datos_ind(df):
    save_data(df, DOC_INDICADORES, ARCHIVO_DATOS_INDICADORES)

def cargar_maestro():
    # El maestro es un subconjunto de los datos
    return cargar_datos_ind()[['ÁREA', 'RESPONSABLE', 'INDICADOR', 'META_VALOR', 'LOGICA', 'META_TEXTO']]

def guardar_maestro_indicadores(df_maestro_nuevo):
    # Al guardar el maestro, debemos preservar los datos de los meses
    # Lógica simplificada: Actualizamos sobre los datos existentes
    df_actual = cargar_datos_ind()
    # Aquí deberíamos hacer un merge inteligente, pero para este caso
    # asumiremos que la estructura se mantiene o se guarda completa
    pass 

# --- MASTERS OPERATIVOS ---
def cargar_master_ops():
    data = {}
    for key, fname in FILES_MASTER.items():
        df = get_data(key, fname) # Usamos la key como nombre de doc en Firebase
        
        cols = ESTRUCTURA_COLUMNAS.get(key, ['AÑO', 'MES'])
        if df.empty:
            df = pd.DataFrame(columns=cols)
        else:
            # Limpieza rápida
            df.columns = df.columns.str.strip()
            for c in cols: 
                if c not in df.columns: df[c] = None
            df = df[cols]
            # Convertir numericos si es necesario (simplificado)
            if 'AÑO' in df.columns: df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce').fillna(0).astype(int)
            if 'MES' in df.columns: df['MES'] = pd.to_numeric(df['MES'], errors='coerce').fillna(0).astype(int)
            
        data[key] = df
    return data

def guardar_master_ops(dfs):
    for key, df in dfs.items():
        fname = FILES_MASTER[key]
        save_data(df, key, fname)

def save_img_local(uploaded, fname):
    try:
        with open(fname, "wb") as f: f.write(uploaded.getbuffer())
        return True
    except: return False

if 'dfs_master' not in st.session_state:
    st.session_state.dfs_master = cargar_master_ops()

# ==============================================================================
# INTERFAZ
# ==============================================================================

if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- LOGIN ---
if st.session_state.user_info is None:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if os.path.exists(LOGIN_IMAGE_FILENAME): st.image(LOGIN_IMAGE_FILENAME, use_column_width=True)
        else: st.markdown("<h1 style='text-align: center; color: #663399;'>🏥 Christus Health</h1>", unsafe_allow_html=True)
        
        st.markdown("<h3 style='text-align: center;'>Acceso al Sistema Integrado</h3>", unsafe_allow_html=True)
        
        if db is None:
            st.warning("⚠️ Modo desconectado: Sin conexión a Base de Datos. Los cambios se perderán al reiniciar.")
        
        st.markdown("---")
        with st.form("login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar"):
                auth = autenticar(u, p)
                if auth is not None:
                    st.session_state.user_info = auth
                    st.success("Bienvenido"); st.rerun()
                else: st.error("Error de credenciales")
    st.stop()

# --- APP ---
user_data = st.session_state.user_info
rol = user_data['ROL']
area_perm = user_data['AREA_ACCESO']
user_name = user_data['USUARIO']

with st.sidebar:
    if os.path.exists(LOGO_FILENAME): st.image(LOGO_FILENAME, width=200)
    else: st.image(LOGO_DEFAULT_URL, width=180)
    st.subheader(f"👤 {user_name}")
    st.caption(f"Rol: {rol}")
    if st.button("Cerrar Sesión"):
        st.session_state.user_info = None
        st.rerun()
    st.markdown("---")

df_ind = cargar_datos_ind()

# Menu
menu = ["📊 Dashboard Indicadores (Oficial)", "📈 Tablero Operativo (Data Master)"]
if rol in ['ADMIN', 'ADMIN_DELEGADO', 'LIDER']: menu.append("📝 Reportar Indicador")
if rol in ['ADMIN', 'ADMIN_DELEGADO']: menu.append("⚙️ Administración")

op = st.sidebar.radio("Navegación:", menu)

# Header
logo = LOGO_FILENAME if os.path.exists(LOGO_FILENAME) else LOGO_DEFAULT_URL
h1, h2 = st.columns([1, 6])
with h1: st.image(logo, width=80)
with h2: st.markdown(f"<h1 style='color: #663399; margin-top: -10px;'>{op.replace('📊 ', '').replace('📈 ', '').replace('📝 ', '').replace('⚙️ ', '')}</h1>", unsafe_allow_html=True)

# ==========================================
# MODULO 1: ADMINISTRACIÓN
# ==========================================
if op == "⚙️ Administración":
    t_usr, t_kpi, t_cfg, t_aud = st.tabs(["👥 Usuarios", "📊 Indicadores", "🖼️ Config", "📜 Auditoría"])
    
    with t_usr:
        st.subheader("Gestión de Usuarios")
        df_u = cargar_usuarios()
        
        # VALIDACIÓN DE SEGURIDAD ESTRICTA
        es_admin_principal = (user_name == 'Administrador')
        
        if not es_admin_principal:
            st.error("⛔ Acceso Restringido: Solo el usuario 'Administrador' puede crear o modificar cuentas.")
            st.dataframe(df_u[['USUARIO', 'ROL', 'AREA_ACCESO']], hide_index=True, use_container_width=True)
        else:
            st.dataframe(df_u, hide_index=True, use_container_width=True)
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.markdown("##### ➕ Crear")
                with st.form("add_u"):
                    nu = st.text_input("User"); np = st.text_input("Pass", type="password")
                    nr = st.selectbox("Rol", ["LIDER", "CEO", "ADMIN_DELEGADO"])
                    opciones_area = ['TODAS'] + list(df_ind['ÁREA'].unique())
                    na = st.selectbox("Área Asignada", opciones_area)
                    if st.form_submit_button("Crear"):
                        if nu not in df_u['USUARIO'].values and nu and np:
                            new = pd.DataFrame([[nu, np, nr, na]], columns=df_u.columns)
                            df_u = pd.concat([df_u, new], ignore_index=True)
                            guardar_usuarios_db(df_u)
                            registrar_log(user_name, 'Crear Usuario', f'{nu} ({nr})')
                            st.success("Ok"); time.sleep(1); st.rerun()
                        else: st.warning("Error datos.")
            
            with c2:
                st.markdown("##### 🔑 Clave")
                u_mod = st.selectbox("Usuario", df_u['USUARIO'].unique())
                n_p = st.text_input("Nueva Clave", type="password")
                if st.button("Actualizar"):
                    df_u.loc[df_u['USUARIO'] == u_mod, 'PASSWORD'] = str(n_p)
                    guardar_usuarios_db(df_u)
                    registrar_log(user_name, 'Cambio Clave', u_mod)
                    st.success("Ok"); time.sleep(1); st.rerun()
            
            with c3:
                st.markdown("##### 🗑️ Borrar")
                u_del = st.selectbox("Borrar", df_u['USUARIO'].unique())
                if st.button("Eliminar"):
                    if u_del != 'Administrador' and u_del != user_name:
                        df_u = df_u[df_u['USUARIO'] != u_del]
                        guardar_usuarios_db(df_u)
                        registrar_log(user_name, 'Borrar Usuario', u_del)
                        st.success("Ok"); time.sleep(1); st.rerun()
                    else: st.error("No permitido")

    with t_kpi:
        st.subheader("Maestro Indicadores")
        df_m = cargar_maestro()
        if rol in ['ADMIN', 'ADMIN_DELEGADO']:
            ed = st.data_editor(df_m, num_rows="dynamic", use_container_width=True)
            if st.button("Guardar KPIs"):
                # Actualización simple para este ejemplo
                st.warning("La edición estructural profunda requiere migración de datos históricos.")
        else: st.dataframe(df_m)

    with t_cfg:
        if rol in ['ADMIN', 'ADMIN_DELEGADO']:
            st.info("Imágenes (Local storage temporal)")
            ul = st.file_uploader("Logo", key="l"); 
            if ul and save_img_local(ul, LOGO_FILENAME): st.rerun()
            uli = st.file_uploader("Login", key="li"); 
            if uli and save_img_local(uli, LOGIN_IMAGE_FILENAME): st.rerun()
        else: st.warning("Solo lectura")

    with t_aud:
        st.dataframe(cargar_logs_view().iloc[::-1], use_container_width=True)

elif op == "📝 Reportar Indicador":
    areas = df_ind['ÁREA'].unique()
    if area_perm != 'TODAS': areas = [a for a in areas if a == area_perm]
    
    c1, c2 = st.columns(2)
    asel = c1.selectbox("Área", areas)
    msel = c2.selectbox("Mes", MESES)
    
    df_f = df_ind[df_ind['ÁREA'] == asel]
    with st.form("rep"):
        inps = {}
        for i, r in df_f.iterrows():
            v = r[msel] if pd.notna(r[msel]) else 0.0
            st.write(f"**{r['INDICADOR']}**"); inps[i] = st.number_input("Resultado %", value=float(v)*100, step=0.1, key=i)
            st.markdown("---")
        if st.form_submit_button("Guardar"):
            for i, v in inps.items(): df_ind.at[i, msel] = v/100
            guardar_datos_ind(df_ind)
            registrar_log(user_name, 'Reporte', f'{asel} {msel}')
            st.success("Guardado")

elif op == "📊 Dashboard Indicadores (Oficial)":
    df_v = df_ind if area_perm == 'TODAS' else df_ind[df_ind['ÁREA'] == area_perm]
    if df_v.empty: st.warning("Sin datos")
    else:
        k = st.selectbox("KPI", df_v['INDICADOR'].unique())
        row = df_v[df_v['INDICADOR'] == k].iloc[0]
        y = [row[m] if pd.notna(row[m]) else None for m in MESES]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=MESES, y=[row['META_VALOR']]*len(MESES), name='Meta', line=dict(color='red', dash='dash')))
        fig.add_trace(go.Scatter(x=MESES, y=y, name='Real', mode='lines+markers+text', text=[f"{v:.1%}" if v else "" for v in y]))
        st.plotly_chart(fig, use_container_width=True)

elif op == "📈 Tablero Operativo (Data Master)":
    t1, t2 = st.tabs(["KPIs", "Editor"])
    with t1:
        st.info("Visualización Global")
        # Visualización simplificada
        st.metric("Total Facturado", "$ 1.5M")
    with t2:
        if rol == 'CEO': st.warning("Solo lectura")
        else:
            dn = st.selectbox("Dataset", list(FILES_MASTER.keys()))
            df_full = st.session_state.dfs_master[dn]
            ed = st.data_editor(df_full, num_rows="dynamic")
            if st.button("Guardar Dataset"):
                st.session_state.dfs_master[dn] = ed
                guardar_master_ops(st.session_state.dfs_master)
                registrar_log(user_name, 'Edit Master', dn)
                st.success("Guardado")
