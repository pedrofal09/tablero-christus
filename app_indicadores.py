import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Tablero Ciclo de Ingresos Integrado", layout="wide", page_icon="🏥")

# --- ARCHIVOS DE CONFIGURACIÓN ---
ARCHIVO_USUARIOS = 'usuarios.csv'
ARCHIVO_DATOS_INDICADORES = 'datos_indicadores_historico.csv'

# Nombres de archivos operativos (MASTER) que deben estar en la carpeta/repo
FILES_MASTER = {
    'ADMISIONES': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - ADMISIONES.csv',
    'AUTORIZACIONES': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - AUTORIZACIONES.csv',
    'FACTURACION': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - FACTURACION.csv',
    'RADICACION': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - RADICACION.csv',
    'GLOSAS': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - GLOSAS Y DEVOLUCIONES.csv',
    'CARTERA': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - CARTERA.csv'
}

# --- DATOS MAESTROS (Indicadores Oficiales) ---
DATOS_MAESTROS_IND = [
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

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .kpi-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        text-align: center;
        border-top: 3px solid #0F1C3F;
        margin-bottom: 10px;
    }
    .kpi-title { font-size: 13px; color: #6c757d; font-weight: 600; text-transform: uppercase; }
    .kpi-value { font-size: 22px; color: #0F1C3F; font-weight: bold; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNCIONES DE GESTIÓN DE USUARIOS Y DATOS
# ==============================================================================

def cargar_usuarios():
    if not os.path.exists(ARCHIVO_USUARIOS):
        df_users = pd.DataFrame([
            ['admin', 'admin123', 'ADMIN', 'TODAS'],
            ['ceo', 'ceo123', 'CEO', 'TODAS']
        ], columns=['USUARIO', 'PASSWORD', 'ROL', 'AREA_ACCESO'])
        df_users.to_csv(ARCHIVO_USUARIOS, index=False)
        return df_users
    return pd.read_csv(ARCHIVO_USUARIOS, dtype=str)

def guardar_usuarios(df_users):
    df_users.to_csv(ARCHIVO_USUARIOS, index=False)

def autenticar(usuario, password):
    df_users = cargar_usuarios()
    user_row = df_users[df_users['USUARIO'] == usuario]
    if not user_row.empty:
        if str(user_row.iloc[0]['PASSWORD']) == str(password):
            return user_row.iloc[0]
    return None

# --- Funciones para Indicadores ---
def inicializar_datos_ind():
    df = pd.DataFrame(DATOS_MAESTROS_IND, columns=['ÁREA', 'RESPONSABLE', 'INDICADOR', 'META_VALOR', 'LOGICA', 'META_TEXTO'])
    for mes in MESES:
        df[mes] = None
    return df

def cargar_datos_ind():
    if os.path.exists(ARCHIVO_DATOS_INDICADORES):
        try:
            return pd.read_csv(ARCHIVO_DATOS_INDICADORES)
        except:
            return inicializar_datos_ind()
    return inicializar_datos_ind()

def guardar_datos_ind(df):
    df.to_csv(ARCHIVO_DATOS_INDICADORES, index=False)

# --- Funciones para Tablero Operativo (MASTER) ---
@st.cache_data
def cargar_datos_master():
    data = {}
    missing = []
    
    for key, filename in FILES_MASTER.items():
        if os.path.exists(filename):
            try:
                # Intentar leer CSV con diferentes configuraciones
                try:
                    df = pd.read_csv(filename, sep=',')
                    if len(df.columns) < 2: df = pd.read_csv(filename, sep=';')
                except:
                    df = pd.read_csv(filename, sep=';', encoding='latin1')
                
                # Limpieza
                df.columns = df.columns.str.strip().str.upper()
                
                # Limpieza numérica
                for col in df.columns:
                    if df[col].dtype == object:
                        if df[col].astype(str).str.contains(r'\$').any():
                            df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[$,]', '', regex=True), errors='coerce').fillna(0)
                
                # Asegurar AÑO y MES
                if 'AÑO' in df.columns: df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce').fillna(0).astype(int)
                if 'MES' in df.columns: df['MES'] = pd.to_numeric(df['MES'], errors='coerce').fillna(0).astype(int)
                
                data[key] = df
            except Exception as e:
                # st.error(f"Error leyendo {filename}: {e}") # Ocultar error en prod
                data[key] = pd.DataFrame(columns=['AÑO', 'MES'])
        else:
            missing.append(filename)
            data[key] = pd.DataFrame(columns=['AÑO', 'MES'])
    return data, missing

# ==============================================================================
# LÓGICA DE LA APLICACIÓN
# ==============================================================================

# --- ESTADO DE SESIÓN ---
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- LOGIN ---
if st.session_state.user_info is None:
    st.title("🔐 Acceso al Sistema Integrado")
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.form("login"):
            user_in = st.text_input("Usuario")
            pass_in = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar"):
                usuario_auth = autenticar(user_in, pass_in)
                if usuario_auth is not None:
                    st.session_state.user_info = usuario_auth
                    st.success("Bienvenido")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
    st.stop()

# --- APP PRINCIPAL ---
user = st.session_state.user_info
rol = user['ROL']
area_permiso = user['AREA_ACCESO']

# Sidebar Header
with st.sidebar:
    try:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Christus_Health_Logo.svg/1200px-Christus_Health_Logo.svg.png", width=150)
    except:
        st.write("🏥 **CHRISTUS HEALTH**")
        
    st.subheader(f"👤 {user['USUARIO']}")
    st.caption(f"Rol: {rol}")
    
    if st.button("Cerrar Sesión"):
        st.session_state.user_info = None
        st.rerun()
    st.markdown("---")

# Cargar Datos Indicadores
if 'df_ind' not in st.session_state:
    st.session_state.df_ind = cargar_datos_ind()
df_ind = st.session_state.df_ind

# Cargar Datos Operativos (Master)
dfs_master, faltantes_master = cargar_datos_master()

# --- MENÚ DE NAVEGACIÓN ---
menu = ["📊 Dashboard Indicadores (Oficial)", "📈 Tablero Operativo (Data Master)"]

if rol in ['ADMIN', 'LIDER']:
    menu.append("📝 Reportar Indicador")

if rol == 'ADMIN':
    menu.append("⚙️ Admin Usuarios")

opcion = st.sidebar.radio("Navegación:", menu)

# ==========================================
# MODULO 1: GESTIÓN DE USUARIOS (ADMIN)
# ==========================================
if opcion == "⚙️ Admin Usuarios":
    st.title("Gestión de Usuarios")
    df_users = cargar_usuarios()
    st.dataframe(df_users, hide_index=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Crear Usuario")
        with st.form("new_u"):
            nu = st.text_input("Usuario")
            np = st.text_input("Pass")
            nr = st.selectbox("Rol", ["LIDER", "CEO", "ADMIN"])
            areas = ['TODAS'] + list(df_ind['ÁREA'].unique())
            na = st.selectbox("Área", areas)
            if st.form_submit_button("Crear"):
                if nu and np:
                    new_row = pd.DataFrame([[nu, np, nr, na]], columns=df_users.columns)
                    df_users = pd.concat([df_users, new_row], ignore_index=True)
                    guardar_usuarios(df_users)
                    st.success("Creado")
                    st.rerun()
    
    with c2:
        st.subheader("Eliminar Usuario")
        u_del = st.selectbox("Usuario a eliminar", df_users['USUARIO'].unique())
        if st.button("Eliminar"):
            if u_del != 'admin':
                df_users = df_users[df_users['USUARIO'] != u_del]
                guardar_usuarios(df_users)
                st.success("Eliminado")
                st.rerun()
            else:
                st.error("No se puede eliminar admin")

# ==========================================
# MODULO 2: REPORTE INDICADORES
# ==========================================
elif opcion == "📝 Reportar Indicador":
    st.header("Reporte Mensual de Indicadores")
    
    # Filtro áreas
    areas_posibles = df_ind['ÁREA'].unique()
    if area_permiso != 'TODAS':
        areas_posibles = [a for a in areas_posibles if a == area_permiso]
    
    if len(areas_posibles) == 0:
        st.error("No tienes área asignada.")
        st.stop()
        
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
            st.success("Guardado.")

# ==========================================
# MODULO 3: DASHBOARD INDICADORES (OFICIAL)
# ==========================================
elif opcion == "📊 Dashboard Indicadores (Oficial)":
    st.header("Tablero de Mando - Indicadores Estratégicos")
    
    if area_permiso == 'TODAS':
        df_view = df_ind
    else:
        df_view = df_ind[df_ind['ÁREA'] == area_permiso]
        
    kpi_sel = st.selectbox("Seleccione Indicador:", df_view['INDICADOR'].unique())
    
    row = df_ind[df_ind['INDICADOR'] == kpi_sel].iloc[0]
    meta = row['META_VALOR']
    logica = row['LOGICA']
    
    # Gráficos
    y_data = [row[m] if pd.notna(row[m]) else None for m in MESES]
    
    # Tarjetas
    last_val = None
    for m in reversed(MESES):
        if pd.notna(row[m]):
            last_val = row[m]
            break
            
    c1, c2 = st.columns(2)
    c1.metric("Meta", row['META_TEXTO'])
    if last_val is not None:
        delta_color = "normal" if logica == 'MAX' else "inverse"
        c2.metric("Último Resultado", f"{last_val:.1%}", f"{last_val-meta:.1%}", delta_color=delta_color)
    else:
        c2.metric("Último Resultado", "Sin Datos")
        
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=MESES, y=[meta]*len(MESES), mode='lines', name='Meta', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=MESES, y=y_data, mode='lines+markers+text', name='Real', line=dict(color='#0F1C3F'), text=[f"{v:.1%}" if v else "" for v in y_data], textposition="top center"))
    fig.update_layout(template="plotly_white", yaxis_tickformat='.0%')
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# MODULO 4: TABLERO OPERATIVO (MASTER)
# ==========================================
elif opcion == "📈 Tablero Operativo (Data Master)":
    st.header("Tablero Operativo - Consolidado")
    
    if faltantes_master:
        st.warning("Faltan algunos archivos operativos en el repositorio (Mostrando datos parciales)")
    
    # Filtros de Tiempo
    anios = [2025, 2026]
    meses_dict = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}
    
    c1, c2 = st.columns(2)
    anio_sel = c1.selectbox("Año Op.", anios)
    mes_sel = c2.selectbox("Mes Op.", list(meses_dict.keys()), format_func=lambda x: meses_dict[x], index=10 if anio_sel==2025 else 0)
    
    # Filtrado y KPI (Lógica de app_master.py)
    def get_kpi(df, col_keywords):
        if df.empty: return 0
        if 'AÑO' in df.columns and 'MES' in df.columns:
            mask = (df['AÑO'] == anio_sel) & (df['MES'] == mes_sel)
            df_filtered = df[mask]
            if df_filtered.empty: return 0
            target_col = next((c for c in df.columns if any(k in c for k in col_keywords)), None)
            if target_col:
                if df_filtered[target_col].dtype == object:
                     return pd.to_numeric(df_filtered[target_col].astype(str).str.replace(r'[$,]', '', regex=True), errors='coerce').sum()
                return df_filtered[target_col].sum()
        return 0

    facturado = get_kpi(dfs_master['FACTURACION'], ['FACTURADO', 'VALOR FACTURADO'])
    radicado = get_kpi(dfs_master['RADICACION'], ['RADICADO', 'VALOR RADICADO'])
    brecha = facturado - radicado
    recaudo = get_kpi(dfs_master['CARTERA'], ['RECAUDO REAL', 'REAL'])
    meta_rec = get_kpi(dfs_master['CARTERA'], ['META'])
    cump = (recaudo / meta_rec) if meta_rec > 0 else 0
    
    # Visualización KPIs
    k1, k2, k3, k4 = st.columns(4)
    
    def kpi_card_html(title, val, is_pct=False, color="#0F1C3F"):
        fmt = f"{val:.1%}" if is_pct else f"${val:,.0f}"
        return f"""<div class="kpi-card"><div class="kpi-title">{title}</div><div class="kpi-value" style="color:{color}">{fmt}</div></div>"""
    
    with k1: st.markdown(kpi_card_html("Facturado", facturado), unsafe_allow_html=True)
    with k2: st.markdown(kpi_card_html("Radicado", radicado), unsafe_allow_html=True)
    with k3: st.markdown(kpi_card_html("Recaudo Real", recaudo), unsafe_allow_html=True)
    with k4: st.markdown(kpi_card_html("% Cumplimiento", cump, True, "green" if cump >= 0.9 else "orange"), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Detalle Facturación
    st.subheader("Detalle Facturación del Mes")
    df_fac = dfs_master['FACTURACION']
    if not df_fac.empty and 'AÑO' in df_fac.columns:
        mask = (df_fac['AÑO'] == anio_sel) & (df_fac['MES'] == mes_sel)
        st.dataframe(df_fac[mask], use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos de facturación para este periodo.")
