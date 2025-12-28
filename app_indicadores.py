import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import time
from datetime import datetime
from PIL import Image

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Tablero Ciclo de Ingresos Christus",
    layout="wide",
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

# --- ARCHIVOS DE CONFIGURACIÓN ---
ARCHIVO_USUARIOS = 'usuarios.csv'
ARCHIVO_DATOS_INDICADORES = 'datos_indicadores_historico.csv'
ARCHIVO_MAESTRO_INDICADORES = 'maestro_indicadores.csv'
ARCHIVO_LOG = 'auditoria_log.csv'

# Archivos de Imagen Configurables
LOGO_FILENAME = 'logo_config.png'
LOGIN_IMAGE_FILENAME = 'login_image.png'

# URL del Logo (Respaldo online)
LOGO_DEFAULT_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Christus_Health_Logo.svg/1200px-Christus_Health_Logo.svg.png"

# Nombres de archivos operativos (MASTER)
FILES_MASTER = {
    'ADMISIONES': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - ADMISIONES.csv',
    'AUTORIZACIONES': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - AUTORIZACIONES.csv',
    'FACTURACION': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - FACTURACION.csv',
    'RADICACION': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - RADICACION.csv',
    'GLOSAS': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - GLOSAS Y DEVOLUCIONES.csv',
    'CARTERA': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - CARTERA.csv',
    'PROVISION': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - PROVISION.csv'
}

# --- ESTRUCTURA EXACTA DE COLUMNAS (Para el Editor) ---
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

# --- DATOS MAESTROS INICIALES ---
DATOS_MAESTROS_IND_INICIAL = [
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

# Meses
MESES = ['NOV-25', 'DIC-25', 'ENE-26', 'FEB-26', 'MAR-26', 'ABR-26', 'MAY-26',
         'JUN-26', 'JUL-26', 'AGO-26', 'SEP-26', 'OCT-26', 'NOV-26', 'DIC-26']

# --- ESTILOS CSS ---
st.markdown("""
<style>
.kpi-card {
  background-color: #ffffff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  text-align: center;
  border-left: 5px solid #663399; /* Morado Christus */
  transition: transform 0.2s;
}
.kpi-card:hover {
  transform: translateY(-5px);
}
.kpi-title {
  font-size: 14px;
  color: #6c757d;
  text-transform: uppercase;
  font-weight: 700;
  margin-bottom: 8px;
}
.kpi-value {
  font-size: 28px;
  color: #2c3e50;
  font-weight: 900;
}
/* Encabezado */
.header-container {
  display: flex;
  align-items: center;
  padding-bottom: 20px;
  border-bottom: 2px solid #663399;
  margin-bottom: 20px;
}
.header-logo {
  height: 60px;
  margin-right: 20px;
}
.header-title {
  font-size: 32px;
  color: #663399;
  font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNCIONES DE GESTIÓN DE USUARIOS, AUDITORÍA Y DATOS
# ==============================================================================

def registrar_log(usuario, accion, detalle):
    """Registra eventos importantes en el archivo de auditoría."""
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nuevo_registro = pd.DataFrame([[fecha, usuario, accion, detalle]], columns=['FECHA', 'USUARIO', 'ACCION', 'DETALLE'])
    if not os.path.exists(ARCHIVO_LOG):
        nuevo_registro.to_csv(ARCHIVO_LOG, index=False)
    else:
        nuevo_registro.to_csv(ARCHIVO_LOG, mode='a', header=False, index=False)

def cargar_logs():
    """Carga el historial de logs."""
    if os.path.exists(ARCHIVO_LOG):
        return pd.read_csv(ARCHIVO_LOG)
    return pd.DataFrame(columns=['FECHA', 'USUARIO', 'ACCION', 'DETALLE'])

def crear_usuarios_default():
    """Crea un DataFrame de usuarios por defecto."""
    return pd.DataFrame([
        ['Administrador', 'Noviembre 2021', 'ADMIN', 'TODAS'],
        ['ceo', 'ceo123', 'CEO', 'TODAS']
    ], columns=['USUARIO', 'PASSWORD', 'ROL', 'AREA_ACCESO'])

def cargar_usuarios():
    """
    Carga los usuarios de forma robusta. Si el archivo no existe o está corrupto,
    lo regenera. Además fuerza la migración:
      - Elimina el usuario antiguo 'admin' si existe.
      - Asegura que exista 'Administrador' con password por defecto.
      - Asegura que exista 'ceo' con password por defecto.
    Registra en auditoría cada cambio de migración.
    Devuelve un DataFrame con las columnas: ['USUARIO','PASSWORD','ROL','AREA_ACCESO'].
    """
    # Determinar actor para logs (usuario actual o SYSTEM)
    actor = 'SYSTEM'
    try:
        if 'user_info' in st.session_state and st.session_state.user_info is not None:
            actor = st.session_state.user_info.get('USUARIO', 'SYSTEM')
    except Exception:
        actor = 'SYSTEM'

    expected_cols = ['USUARIO', 'PASSWORD', 'ROL', 'AREA_ACCESO']

    # Si no existe el archivo, crear defaults y devolverlos (y registrar)
    if not os.path.exists(ARCHIVO_USUARIOS):
        df_users = crear_usuarios_default()
        df_users.to_csv(ARCHIVO_USUARIOS, index=False)
        registrar_log(actor, 'Migración Usuarios', 'Archivo usuarios no existía. Se crearon usuarios por defecto.')
        return df_users

    # Si existe, intentar leerlo de forma segura
    try:
        df_users = pd.read_csv(ARCHIVO_USUARIOS, dtype=str)
        # Validar esquema
        if df_users.empty or not all(col in df_users.columns for col in expected_cols):
            st.warning("Archivo de usuarios inválido o incompleto. Restaurando defaults de seguridad.")
            registrar_log(actor, 'Migración Usuarios', 'Archivo usuarios inválido. Restauración a defaults.')
            df_users = crear_usuarios_default()
            df_users.to_csv(ARCHIVO_USUARIOS, index=False)
            return df_users

        # Normalizar y limpiar
        df_users = df_users.astype(str)
        df_users['USUARIO'] = df_users['USUARIO'].str.strip()
        df_users['PASSWORD'] = df_users['PASSWORD'].str.strip()
        df_users['ROL'] = df_users['ROL'].str.strip()
        df_users['AREA_ACCESO'] = df_users['AREA_ACCESO'].str.strip()

        cambios = False

        # 1) Eliminar 'admin' antiguo si existe (coincidencia exacta)
        if 'admin' in df_users['USUARIO'].values:
            df_users = df_users[df_users['USUARIO'] != 'admin']
            cambios = True
            registrar_log(actor, 'Migración Usuarios', "Eliminado usuario antiguo 'admin' del archivo usuarios.")

        # 2) Asegurar que exista 'Administrador'
        if 'Administrador' not in df_users['USUARIO'].values:
            nuevo_admin = pd.DataFrame([['Administrador', 'Noviembre 2021', 'ADMIN', 'TODAS']],
                                      columns=expected_cols)
            df_users = pd.concat([df_users, nuevo_admin], ignore_index=True)
            cambios = True
            registrar_log(actor, 'Migración Usuarios', "Creado usuario 'Administrador' en archivo usuarios.")

        # 3) Asegurar que exista 'ceo'
        if 'ceo' not in df_users['USUARIO'].values:
            nuevo_ceo = pd.DataFrame([['ceo', 'ceo123', 'CEO', 'TODAS']],
                                    columns=expected_cols)
            df_users = pd.concat([df_users, nuevo_ceo], ignore_index=True)
            cambios = True
            registrar_log(actor, 'Migración Usuarios', "Creado usuario 'ceo' en archivo usuarios.")

        # Si hubo cambios, sobrescribir el archivo existente de forma atómica
        if cambios:
            tmp_file = ARCHIVO_USUARIOS + ".tmp"
            df_users.to_csv(tmp_file, index=False)
            try:
                os.replace(tmp_file, ARCHIVO_USUARIOS)
            except Exception:
                # Fallback simple
                df_users.to_csv(ARCHIVO_USUARIOS, index=False)
            registrar_log(actor, 'Migración Usuarios', 'Cambios de migración guardados en archivo usuarios.')

        return df_users

    except Exception as e:
        # En caso de error al leer, restaurar defaults y avisar
        st.error(f"Error crítico cargando usuarios: {e}. Restaurando acceso por defecto.")
        registrar_log(actor, 'Migración Usuarios', f'Error leyendo archivo usuarios: {e}. Restauración a defaults.')
        df_users = crear_usuarios_default()
        df_users.to_csv(ARCHIVO_USUARIOS, index=False)
        return df_users

def guardar_usuarios(df_users):
    """Guarda los usuarios asegurando formato string."""
    df_users = df_users.astype(str)
    df_users.to_csv(ARCHIVO_USUARIOS, index=False)

def autenticar(usuario, password):
    df_users = cargar_usuarios()
    user_row = df_users[df_users['USUARIO'] == usuario]
    if not user_row.empty:
        password_registrado = str(user_row.iloc[0]['PASSWORD']).strip()
        password_input = str(password).strip()
        if password_registrado == password_input:
            return user_row.iloc[0]
    return None

def cargar_maestro_indicadores():
    if os.path.exists(ARCHIVO_MAESTRO_INDICADORES):
        try:
            return pd.read_csv(ARCHIVO_MAESTRO_INDICADORES)
        except:
            pass
    df = pd.DataFrame(DATOS_MAESTROS_IND_INICIAL, columns=['ÁREA', 'RESPONSABLE', 'INDICADOR', 'META_VALOR', 'LOGICA', 'META_TEXTO'])
    df.to_csv(ARCHIVO_MAESTRO_INDICADORES, index=False)
    return df

def guardar_maestro_indicadores(df):
    df.to_csv(ARCHIVO_MAESTRO_INDICADORES, index=False)

def inicializar_datos_ind(df_maestro):
    df = df_maestro.copy()
    for mes in MESES:
        df[mes] = None
    return df

def cargar_datos_ind():
    df_maestro = cargar_maestro_indicadores()
    if os.path.exists(ARCHIVO_DATOS_INDICADORES):
        try:
            df_datos = pd.read_csv(ARCHIVO_DATOS_INDICADORES)
            cols_datos = ['INDICADOR'] + [m for m in MESES if m in df_datos.columns]
            df_merged = pd.merge(df_maestro, df_datos[cols_datos], on='INDICADOR', how='left')
            return df_merged
        except:
            return inicializar_datos_ind(df_maestro)
    return inicializar_datos_ind(df_maestro)

def guardar_datos_ind(df):
    df.to_csv(ARCHIVO_DATOS_INDICADORES, index=False)

def cargar_datos_master_disco():
    data = {}
    missing = []
    for key, filename in FILES_MASTER.items():
        cols_esperadas = ESTRUCTURA_COLUMNAS.get(key, ['AÑO', 'MES'])
        if os.path.exists(filename):
            try:
                try:
                    df = pd.read_csv(filename, sep=',')
                    if len(df.columns) < 2:
                        df = pd.read_csv(filename, sep=';')
                except:
                    df = pd.read_csv(filename, sep=';', encoding='latin1')
                df.columns = df.columns.str.strip()
                if key == 'ADMISIONES':
                    df.columns = [c.replace('MES.1', 'MES_LETRAS') if 'MES.' in c else c for c in df.columns]
                for col in cols_esperadas:
                    if col not in df.columns:
                        df[col] = None
                df = df[cols_esperadas]
                for col in df.columns:
                    if df[col].dtype == object:
                        if df[col].astype(str).str.contains(r'\$').any():
                            df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[$,]', '', regex=True), errors='coerce').fillna(0)
                if 'AÑO' in df.columns:
                    df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce').fillna(0).astype(int)
                if 'MES' in df.columns:
                    df['MES'] = pd.to_numeric(df['MES'], errors='coerce').fillna(0).astype(int)
                data[key] = df
            except:
                data[key] = pd.DataFrame(columns=cols_esperadas)
        else:
            missing.append(filename)
            data[key] = pd.DataFrame(columns=cols_esperadas)
    return data, missing

def guardar_datos_master_disco(dfs):
    for key, df in dfs.items():
        filename = FILES_MASTER[key]
        df.to_csv(filename, index=False)

def save_uploaded_image(uploaded_file, filename):
    try:
        with open(filename, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    except:
        return False

# Carga inicial de datos master
if 'dfs_master' not in st.session_state:
    st.session_state.dfs_master, st.session_state.faltantes_master = cargar_datos_master_disco()

# ==============================================================================
# LÓGICA DE LA APLICACIÓN
# ==============================================================================

if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- LOGIN ---
if st.session_state.user_info is None:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if os.path.exists(LOGIN_IMAGE_FILENAME):
            st.image(LOGIN_IMAGE_FILENAME, use_column_width=True)
        else:
            st.markdown("<h1 style='text-align: center; color: #663399;'>🏥 Christus Health</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Acceso al Sistema Integrado</h3>", unsafe_allow_html=True)
        st.markdown("---")
    with st.form("login"):
        user_in = st.text_input("Usuario")
        pass_in = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            usuario_auth = autenticar(user_in, pass_in)
            if usuario_auth is not None:
                st.session_state.user_info = usuario_auth
                # Podríamos registrar logins, pero para no saturar solo registramos cambios
                # registrar_log(user_in, 'Login', 'Ingreso exitoso')
                st.success("Bienvenido")
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()

# --- APP PRINCIPAL ---
user = st.session_state.user_info
rol = user['ROL']
area_permiso = user['AREA_ACCESO']
current_user_name = user['USUARIO']

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_FILENAME):
        st.image(LOGO_FILENAME, width=200)
    else:
        st.image(LOGO_DEFAULT_URL, width=180)
    st.subheader(f"👤 {current_user_name}")
    st.caption(f"Rol: **{rol}**")
    if st.button("Cerrar Sesión"):
        st.session_state.user_info = None
        st.rerun()
    st.markdown("---")

if 'df_ind' not in st.session_state:
    st.session_state.df_ind = cargar_datos_ind()
df_ind = st.session_state.df_ind

if 'dfs_master' not in st.session_state:
    st.session_state.dfs_master, st.session_state.faltantes_master = cargar_datos_master_disco()

menu = ["📊 Dashboard Indicadores (Oficial)", "📈 Tablero Operativo (Data Master)"]
if rol in ['ADMIN', 'LIDER']:
    menu.append("📝 Reportar Indicador")
if rol == 'ADMIN':
    menu.append("⚙️ Administración")
opcion = st.sidebar.radio("Navegación:", menu)

# --- CABECERA COMÚN ---
logo_src = LOGO_FILENAME if os.path.exists(LOGO_FILENAME) else LOGO_DEFAULT_URL
h1, h2 = st.columns([1, 6])
with h1:
    st.image(logo_src, width=80)
with h2:
    st.markdown(f"<h1 style='color: #663399; margin-top: -10px;'>{opcion.replace('📊 ', '').replace('📈 ', '').replace('📝 ', '').replace('⚙️ ', '')}</h1>", unsafe_allow_html=True)

# ==========================================
# MODULO 1: ADMINISTRACIÓN
# ==========================================
if opcion == "⚙️ Administración":
    tab_users, tab_kpis, tab_config, tab_audit = st.tabs(["👥 Gestión de Usuarios", "📊 Gestión de Indicadores", "🖼️ Configuración Visual", "📜 Auditoría de Cambios"])

    with tab_users:
        df_users = cargar_usuarios()
        st.subheader("Directorio de Usuarios")
        st.dataframe(df_users, hide_index=True, use_container_width=True)
        st.markdown("---")
        gc1, gc2, gc3 = st.columns(3)

        # 1. CREAR USUARIO
        with gc1:
            st.markdown("##### ➕ Crear Nuevo")
            with st.form("new_u"):
                nu = st.text_input("Usuario")
                np = st.text_input("Password", type="password")
                nr = st.selectbox("Rol", ["LIDER", "CEO", "ADMIN"])
                na = st.selectbox("Área", ['TODAS'] + list(df_ind['ÁREA'].unique()))
                if st.form_submit_button("Crear"):
                    if nu and np:
                        if nu in df_users['USUARIO'].values:
                            st.error("El usuario ya existe.")
                        else:
                            new_row = pd.DataFrame([[nu, np, nr, na]], columns=df_users.columns)
                            df_users = pd.concat([df_users, new_row], ignore_index=True)
                            guardar_usuarios(df_users)
                            registrar_log(current_user_name, 'Crear Usuario', f'Creó al usuario: {nu}')
                            st.success("Usuario creado.")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.warning("Complete usuario y contraseña.")

        # 2. MODIFICAR CONTRASEÑA
        with gc2:
            st.markdown("##### 🔑 Cambiar Contraseña")
            user_to_mod = st.selectbox("Seleccionar Usuario", df_users['USUARIO'].unique(), key="sel_mod_pass")
            new_pass_admin = st.text_input("Nueva Contraseña", type="password", key="new_pass_admin")
            if st.button("Actualizar Contraseña"):
                if new_pass_admin:
                    df_users.loc[df_users['USUARIO'] == user_to_mod, 'PASSWORD'] = str(new_pass_admin)
                    guardar_usuarios(df_users)
                    registrar_log(current_user_name, 'Cambio Contraseña', f'Actualizó pass de: {user_to_mod}')
                    st.success(f"Contraseña actualizada para: {user_to_mod}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Debe ingresar una nueva contraseña.")

        # 3. ELIMINAR USUARIO
        with gc3:
            st.markdown("##### 🗑️ Eliminar")
            u_del = st.selectbox("Eliminar Usuario", df_users['USUARIO'].unique(), key="sel_del_user")
            if st.button("Eliminar Definitivamente"):
                if u_del == 'Administrador':
                    st.error("No se puede eliminar al usuario Administrador principal.")
                elif u_del == current_user_name:
                    st.error("No puedes eliminar tu propio usuario mientras estás logueado.")
                else:
                    df_users = df_users[df_users['USUARIO'] != u_del]
                    guardar_usuarios(df_users)
                    registrar_log(current_user_name, 'Eliminar Usuario', f'Eliminó al usuario: {u_del}')
                    st.success("Usuario eliminado.")
                    time.sleep(1)
                    st.rerun()

    with tab_kpis:
        st.subheader("Gestión Maestra de Indicadores")
        df_maestro = cargar_maestro_indicadores()
        edited_maestro = st.data_editor(
            df_maestro, num_rows="dynamic", use_container_width=True, key="editor_maestro_kpi",
            column_config={"LOGICA": st.column_config.SelectboxColumn("Lógica", options=["MAX", "MIN"], required=True),
                           "META_VALOR": st.column_config.NumberColumn("Meta (Decimal)", format="%.2f"),
                           "ÁREA": st.column_config.SelectboxColumn("Área", options=list(df_maestro['ÁREA'].unique()))}
        )
        if st.button("💾 Guardar Cambios en Indicadores"):
            guardar_maestro_indicadores(edited_maestro)
            st.session_state.df_ind = cargar_datos_ind()
            registrar_log(current_user_name, 'Configuración Indicadores', 'Actualizó maestro de KPIs')
            st.success("Actualizado.")
            time.sleep(1)
            st.rerun()

    with tab_config:
        st.subheader("Personalización de Marca")
        st.info("Sube las imágenes corporativas aquí (Formatos: PNG, JPG).")
        c_logo, c_login = st.columns(2)
        with c_logo:
            st.markdown("### Logo Principal (Barra Lateral)")
            logo_file = st.file_uploader("Subir Logo", type=['png', 'jpg', 'jpeg'], key="up_logo")
            if logo_file:
                if save_uploaded_image(logo_file, LOGO_FILENAME):
                    registrar_log(current_user_name, 'Branding', 'Actualizó Logo Principal')
                    st.success("Logo actualizado.")
                    st.image(LOGO_FILENAME, width=150)
                    time.sleep(1); st.rerun()
            elif os.path.exists(LOGO_FILENAME):
                st.image(LOGO_FILENAME, width=150)
            if st.button("Restaurar Logo Default"):
                os.remove(LOGO_FILENAME)
                registrar_log(current_user_name, 'Branding', 'Restauró Logo Default')
                st.rerun()

        with c_login:
            st.markdown("### Imagen Pantalla Login")
            login_file = st.file_uploader("Subir Imagen Login", type=['png', 'jpg', 'jpeg'], key="up_login")
            if login_file:
                if save_uploaded_image(login_file, LOGIN_IMAGE_FILENAME):
                    registrar_log(current_user_name, 'Branding', 'Actualizó Imagen Login')
                    st.success("Imagen de login actualizada.")
                    st.image(LOGIN_IMAGE_FILENAME, width=200)
                    time.sleep(1); st.rerun()
            elif os.path.exists(LOGIN_IMAGE_FILENAME):
                st.image(LOGIN_IMAGE_FILENAME, width=200)
            if st.button("Quitar Imagen Login"):
                os.remove(LOGIN_IMAGE_FILENAME)
                registrar_log(current_user_name, 'Branding', 'Eliminó Imagen Login')
                st.rerun()

    with tab_audit:
        st.subheader("Registro de Auditoría y Cambios")
        st.markdown("Historial de acciones realizadas por los usuarios en el sistema.")
        df_log = cargar_logs()
        if not df_log.empty:
            # Ordenar por fecha descendente (asumiendo formato ordenable, o invertimos)
            df_log = df_log.iloc[::-1]
            st.dataframe(df_log, use_container_width=True, hide_index=True)
        else:
            st.info("No hay registros de auditoría aún.")

# ==========================================
# MODULO 2: REPORTE INDICADORES
# ==========================================
elif opcion == "📝 Reportar Indicador":
    areas_posibles = df_ind['ÁREA'].unique()
    if area_permiso != 'TODAS':
        areas_posibles = [a for a in areas_posibles if a == area_permiso]
    c1, c2 = st.columns(2)
    area_sel = c1.selectbox("Área:", areas_posibles)
    mes_sel = c2.selectbox("Mes:", MESES)
    df_f = df_ind[df_ind['ÁREA'] == area_sel]
    with st.form("reporte"):
        inputs = {}
        for idx, row in df_f.iterrows():
            val = row[mes_sel] if pd.notna(row[mes_sel]) else 0.0
            st.markdown(f"**{row['INDICADOR']}** (Meta: {row['META_TEXTO']})")
            inputs[idx] = st.number_input("Resultado %", value=float(val)*100, step=0.1, key=idx)
            st.markdown("---")
        if st.form_submit_button("Guardar"):
            for i, v in inputs.items():
                df_ind.at[i, mes_sel] = v / 100
            st.session_state.df_ind = df_ind
            guardar_datos_ind(df_ind)
            registrar_log(current_user_name, 'Reporte Mensual', f'Cargó datos {area_sel} - {mes_sel}')
            st.success("Guardado.")

# ==========================================
# MODULO 3: DASHBOARD INDICADORES (OFICIAL)
# ==========================================
elif opcion == "📊 Dashboard Indicadores (Oficial)":
    df_view = df_ind if area_permiso == 'TODAS' else df_ind[df_ind['ÁREA'] == area_permiso]
    if df_view.empty:
        st.warning("No hay indicadores disponibles.")
    else:
        kpi_sel = st.selectbox("Indicador:", df_view['INDICADOR'].unique())
        row = df_ind[df_ind['INDICADOR'] == kpi_sel].iloc[0]
        meta = row['META_VALOR']; logica = row['LOGICA']
        y_data = [row[m] if pd.notna(row[m]) else None for m in MESES]
        last_val = None
        for m in reversed(MESES):
            if pd.notna(row[m]):
                last_val = row[m]
                break
        c1, c2 = st.columns(2)
        c1.metric("Meta", row['META_TEXTO'])
        if last_val is not None:
            color = "normal" if logica == 'MAX' else "inverse"
            c2.metric("Último", f"{last_val:.1%}", f"{last_val-meta:.1%}", delta_color=color)
        else:
            c2.metric("Último", "Sin Datos")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=MESES, y=[meta]*len(MESES), mode='lines', name='Meta', line=dict(color='red', dash='dash')))
        fig.add_trace(go.Scatter(x=MESES, y=y_data, mode='lines+markers+text', name='Real', line=dict(color='#0F1C3F'), text=[f"{v:.1%}" if v else "" for v in y_data], textposition="top center"))
        fig.update_layout(template="plotly_white", yaxis_tickformat='.0%')
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# MODULO 4: TABLERO OPERATIVO (MASTER)
# ==========================================
elif opcion == "📈 Tablero Operativo (Data Master)":
    tab_vis, tab_edit = st.tabs(["📊 Visualización KPIs", "📝 Editor de Datos (Operativo)"])

    with tab_vis:
        anios = [2025, 2026]
        meses_dict = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}
        c1, c2 = st.columns(2)
        anio_sel = c1.selectbox("Año Op.", anios)
        mes_sel = c2.selectbox("Mes Op.", list(meses_dict.keys()), format_func=lambda x: meses_dict[x], index=10 if anio_sel==2025 else 0)

        def get_kpi(df, col_keywords):
            if df.empty:
                return 0
            if 'AÑO' in df.columns and 'MES' in df.columns:
                mask = (df['AÑO'] == anio_sel) & (df['MES'] == mes_sel)
                df_filtered = df[mask]
                if df_filtered.empty:
                    return 0
                target_col = next((c for c in df.columns if any(k in c for k in col_keywords)), None)
                if target_col:
                    if df_filtered[target_col].dtype == object:
                        return pd.to_numeric(df_filtered[target_col].astype(str).str.replace(r'[$,]', '', regex=True), errors='coerce').sum()
                    return df_filtered[target_col].sum()
            return 0

        dfs_m = st.session_state.dfs_master
        facturado = get_kpi(dfs_m['FACTURACION'], ['Valor Facturado', 'FACTURADO'])
        radicado = get_kpi(dfs_m['RADICACION'], ['Valor Radicado', 'RADICADO'])
        brecha = facturado - radicado
        recaudo = get_kpi(dfs_m['CARTERA'], ['Recaudo Real', 'REAL'])
        meta_rec = get_kpi(dfs_m['CARTERA'], ['Meta Recaudo', 'META'])
        cump = (recaudo / meta_rec) if meta_rec > 0 else 0
        glosa_inicial = get_kpi(dfs_m['GLOSAS'], ['Valor Glosa Inicial', 'INICIAL'])
        devoluciones = get_kpi(dfs_m['GLOSAS'], ['Valor Devoluciones', 'DEVOLUCIONES'])
        levantado = get_kpi(dfs_m['GLOSAS'], ['Valor Rechazado', 'Rechazado'])
        aceptado = get_kpi(dfs_m['GLOSAS'], ['Valor Aceptado', 'Aceptado'])
        prov_acostados = get_kpi(dfs_m['PROVISION'], ['Prov. Acostados', 'Acostados'])
        prov_ambulatorios = get_kpi(dfs_m['PROVISION'], ['Prov. Ambulatorios', 'Ambulatorios'])
        prov_egresados = get_kpi(dfs_m['PROVISION'], ['Prov. Egresados', 'Egresados'])
        sin_radicar = get_kpi(dfs_m['PROVISION'], ['Facturado Sin Radicar', 'Sin Radicar'])
        glosas_pend = get_kpi(dfs_m['PROVISION'], ['Valor Glosas Pendientes', 'Glosas Pendientes'])

        def kpi_card_html(title, val, is_pct=False, color="#0F1C3F"):
            fmt = f"{val:.1%}" if is_pct else f"${val:,.0f}"
            return f"""<div class="kpi-card"><div class="kpi-title">{title}</div><div class="kpi-value" style="color:{color}">{fmt}</div></div>"""

        st.subheader("1. Desempeño Financiero")
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(kpi_card_html("Facturado", facturado), unsafe_allow_html=True)
        with k2:
            st.markdown(kpi_card_html("Radicado", radicado), unsafe_allow_html=True)
        with k3:
            st.markdown(kpi_card_html("Recaudo Real", recaudo), unsafe_allow_html=True)
        with k4:
            st.markdown(kpi_card_html("% Cumplimiento", cump, True, "green" if cump >= 0.9 else "orange"), unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("2. Gestión de Glosas Cerradas")
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            st.markdown(kpi_card_html("Devoluciones", devoluciones), unsafe_allow_html=True)
        with g2:
            st.markdown(kpi_card_html("Glosa Inicial", glosa_inicial), unsafe_allow_html=True)
        with g3:
            st.markdown(kpi_card_html("Levantado (Recuperado)", levantado, False, "green"), unsafe_allow_html=True)
        with g4:
            st.markdown(kpi_card_html("Aceptado (Pérdida)", aceptado, False, "red"), unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("3. Análisis de Provisión y Pendientes")
        p1, p2, p3, p4, p5 = st.columns(5)
        with p1:
            st.markdown(kpi_card_html("Prov. Acostados", prov_acostados), unsafe_allow_html=True)
        with p2:
            st.markdown(kpi_card_html("Prov. Ambulatorios", prov_ambulatorios), unsafe_allow_html=True)
        with p3:
            st.markdown(kpi_card_html("Prov. Egresados", prov_egresados), unsafe_allow_html=True)
        with p4:
            st.markdown(kpi_card_html("Sin Radicar (Inc. Dev)", sin_radicar, False, "orange"), unsafe_allow_html=True)
        with p5:
            st.markdown(kpi_card_html("Glosas Pendientes", glosas_pend, False, "orange"), unsafe_allow_html=True)

    with tab_edit:
        st.header("📝 Gestión de Datos Operativos (Por Periodo)")
        st.info("Seleccione el periodo específico. Puede cargar archivo o pegar datos.")
        col_db, col_anio, col_mes = st.columns([2, 1, 1])
        with col_db:
            dataset_name = st.selectbox("Base de Datos:", list(FILES_MASTER.keys()))
        with col_anio:
            edit_anio = st.selectbox("Año Edición:", [2025, 2026])
        with col_mes:
            edit_mes = st.selectbox("Mes Edición:", list(range(1, 13)), index=10)

        df_full = st.session_state.dfs_master[dataset_name]

        # FIX AÑO MES
        if 'AÑO' not in df_full.columns:
            df_full['AÑO'] = 0
        if 'MES' not in df_full.columns:
            df_full['MES'] = 0
        df_full['AÑO'] = pd.to_numeric(df_full['AÑO'], errors='coerce').fillna(0).astype(int)
        df_full['MES'] = pd.to_numeric(df_full['MES'], errors='coerce').fillna(0).astype(int)

        mask_edit = (df_full['AÑO'] == edit_anio) & (df_full['MES'] == edit_mes)
        df_periodo = df_full[mask_edit].copy()
        if df_periodo.empty:
            df_periodo = pd.DataFrame(columns=ESTRUCTURA_COLUMNAS[dataset_name])

        st.markdown(f"### Editando: {dataset_name} - {edit_mes}/{edit_anio}")
        uploaded_file = st.file_uploader(f"Cargar CSV/Excel para {dataset_name}", type=['csv', 'xlsx'])
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_upload = pd.read_csv(uploaded_file)
                else:
                    df_upload = pd.read_excel(uploaded_file)
                df_upload.columns = df_upload.columns.str.strip()
                cols_req = ESTRUCTURA_COLUMNAS[dataset_name]
                for c in cols_req:
                    if c not in df_upload.columns:
                        df_upload[c] = None
                df_upload = df_upload[cols_req]
                df_upload['AÑO'] = edit_anio; df_upload['MES'] = edit_mes
                df_periodo = df_upload
                st.success("Archivo cargado en vista previa.")
            except Exception as e:
                st.error(f"Error: {e}")

        edited_periodo = st.data_editor(df_periodo, num_rows="dynamic", use_container_width=True, key=f"editor_{dataset_name}_{edit_anio}_{edit_mes}")
        if st.button(f"💾 Guardar Periodo {edit_mes}/{edit_anio}"):
            mask_old = (df_full['AÑO'] == edit_anio) & (df_full['MES'] == edit_mes)
            df_clean = df_full[~mask_old]
            if not edited_periodo.empty:
                if 'AÑO' in edited_periodo.columns:
                    edited_periodo['AÑO'] = edited_periodo['AÑO'].fillna(edit_anio).astype(int)
                else:
                    edited_periodo['AÑO'] = edit_anio
                if 'MES' in edited_periodo.columns:
                    edited_periodo['MES'] = edited_periodo['MES'].fillna(edit_mes).astype(int)
                else:
                    edited_periodo['MES'] = edit_mes
                edited_periodo.loc[edited_periodo['AÑO'] == 0, 'AÑO'] = edit_anio
                # Nota: el archivo original estaba truncado en la versión adjunta; aquí termina la integración.
