import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import time
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
LOGO_DEFAULT_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Christus_Health_Logo.svg/1200px-Christus_Health_Logo.svg.png"

MESES = ['NOV-25', 'DIC-25', 'ENE-26', 'FEB-26', 'MAR-26', 'ABR-26', 'MAY-26', 
         'JUN-26', 'JUL-26', 'AGO-26', 'SEP-26', 'OCT-26', 'NOV-26', 'DIC-26']

# Definición de estructuras de datos (Archivos Maestros Virtuales)
ESTRUCTURA_COLUMNAS = {
    'FACTURACION': ['AÑO', 'MES', 'Ranking', 'Aseguradora / Cliente', 'Valor Facturado', '% Participación'],
    'RADICACION': ['AÑO', 'MES', 'Aseguradora', 'No. Facturas', 'Valor Radicado', 'Fecha Corte'],
    'GLOSAS': ['AÑO', 'MES', 'Aseguradora', 'Valor Devoluciones', 'Valor Glosa Inicial', 'Valor Rechazado', 'Valor Aceptado', '% Gestionado'],
    'CARTERA': ['AÑO', 'MES', 'Aseguradora', 'Saldo Inicial', 'Meta Recaudo', 'Recaudo Real', '% Cumplimiento'],
    'AUTORIZACIONES': ['AÑO', 'MES', 'Tipo Solicitud', 'Gestionadas', 'Aprobadas', 'Pendientes', 'Negadas', '% Efectividad'],
    'ADMISIONES': ['AÑO', 'MES', 'Sede / Concepto', 'MES_LETRAS', 'Cantidad Actividades', 'Valor Estimado Ingreso', 'Promedio por Paciente'],
    'PROVISION': ['AÑO', 'MES', 'Aseguradora', 'Fecha Corte', 'Prov. Acostados', 'Prov. Ambulatorios', 'Prov. Egresados', 'Facturado Sin Radicar', 'Cant. Glosas Pendientes', 'Valor Glosas Pendientes']
}

# Datos Maestros de Indicadores (Hardcoded inicial)
DATOS_MAESTROS_IND_INICIAL = [
    ['FACTURACIÓN', 'Dir. Facturación', 'Facturación oportuna (≤72h egreso)', 0.95, 'MAX', '>95%'],
    ['FACTURACIÓN', 'Dir. Facturación', 'Radicación oportuna (≤22 días)', 0.98, 'MAX', '>98%'],
    ['CUENTAS MÉDICAS', 'Jefatura Cuentas Médicas', '% de glosas aceptadas en el mes', 0.02, 'MIN', '<2%'],
    ['ADMISIONES', 'Coordinación Admisiones', '% de facturas anuladas por falta de autorización', 0.01, 'MIN', '≤ 1%'],
    ['AUTORIZACIONES', 'Coord. Autorizaciones', '% de autorizaciones generadas en ≤7 horas', 1.00, 'MAX', '100%'],
    ['CARTERA', 'Jefatura de Cartera', 'Recuperación de Glosa', 0.85, 'MAX', '> 85%'],
    ['CARTERA', 'Jefatura de Cartera', '% de cartera vencida >60 días', 0.60, 'MIN', '< 60%']
]

# --- ESTILOS CSS PERSONALIZADOS ---
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
    .kpi-meta {{ font-size: 12px; color: #27ae60; font-weight: bold; margin-top: 5px; }}
    h1, h2, h3 {{ color: {COLOR_PRIMARY}; }}
    .stButton>button {{ background-color: {COLOR_PRIMARY}; color: white; border-radius: 5px; }}
    .stButton>button:hover {{ background-color: #552b80; border-color: #552b80; }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# GESTIÓN DE DATOS (MOCK / SESSION STATE)
# ==============================================================================
# Nota: En un entorno real con persistencia, aquí iría la conexión a Firebase.
# Para este demo, usaremos st.session_state para simular la base de datos.

def init_session_state():
    """Inicializa datos ficticios si no existen en sesión."""
    
    # 1. Usuarios
    if 'db_usuarios' not in st.session_state:
        st.session_state.db_usuarios = pd.DataFrame([
            ['Administrador', 'Agosto2025', 'ADMIN', 'TODAS'],
            ['Gerente', '1234', 'CEO', 'TODAS'],
            ['LiderFacturacion', '1234', 'LIDER', 'FACTURACIÓN']
        ], columns=['USUARIO', 'PASSWORD', 'ROL', 'AREA_ACCESO'])

    # 2. Logs
    if 'db_logs' not in st.session_state:
        st.session_state.db_logs = pd.DataFrame(columns=['FECHA', 'USUARIO', 'ACCION', 'DETALLE'])

    # 3. Indicadores (Con datos aleatorios simulados para demo)
    if 'db_indicadores' not in st.session_state:
        import random
        df = pd.DataFrame(DATOS_MAESTROS_IND_INICIAL, columns=['ÁREA', 'RESPONSABLE', 'INDICADOR', 'META_VALOR', 'LOGICA', 'META_TEXTO'])
        # Poblar con datos simulados
        for m in MESES:
            # Generar valor aleatorio cercano a la meta para simular realidad
            df[m] = df.apply(lambda x: max(0, min(1, x['META_VALOR'] + random.uniform(-0.1, 0.05))), axis=1)
        st.session_state.db_indicadores = df

    # 4. Datos Maestros Operativos (Tablas vacías o simuladas)
    if 'dfs_master' not in st.session_state:
        data = {}
        for key, cols in ESTRUCTURA_COLUMNAS.items():
            df = pd.DataFrame(columns=cols)
            # Fila de ejemplo vacía para que el editor se vea bien
            # df.loc[0] = [None] * len(cols) 
            data[key] = df
        st.session_state.dfs_master = data

init_session_state()

# --- FUNCIONES DE ACCESO A DATOS ---
def autenticar(user, pwd):
    df = st.session_state.db_usuarios
    row = df[df['USUARIO'] == user]
    if not row.empty:
        if str(row.iloc[0]['PASSWORD']).strip() == str(pwd).strip():
            return row.iloc[0]
    return None

def registrar_log(usuario, accion, detalle):
    nuevo = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), usuario, accion, detalle]], 
                         columns=['FECHA', 'USUARIO', 'ACCION', 'DETALLE'])
    st.session_state.db_logs = pd.concat([st.session_state.db_logs, nuevo], ignore_index=True)

def obtener_indicadores():
    return st.session_state.db_indicadores

def guardar_indicadores(df):
    st.session_state.db_indicadores = df

# ==============================================================================
# INTERFAZ DE USUARIO
# ==============================================================================

if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- PANTALLA DE LOGIN ---
if st.session_state.user_info is None:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image(LOGO_DEFAULT_URL, width=250)
        st.markdown(f"<h3 style='text-align: center; color: {COLOR_SECONDARY};'>Portal Ciclo de Ingresos</h3>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.markdown("##### Iniciar Sesión")
            u = st.text_input("Usuario", placeholder="Ej: Administrador")
            p = st.text_input("Contraseña", type="password", placeholder="••••••")
            
            if st.form_submit_button("INGRESAR", use_container_width=True):
                auth = autenticar(u, p)
                if auth is not None:
                    st.session_state.user_info = auth
                    registrar_log(u, "Login", "Exitoso")
                    st.toast(f"Bienvenido, {u}!", icon="👋")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. (Prueba: Administrador / Agosto2025)")
        
        st.info("ℹ️ Credenciales Demo: **Administrador** / **Agosto2025**")
    st.stop()

# --- APP PRINCIPAL ---
user_data = st.session_state.user_info
rol = user_data['ROL']
area_perm = user_data['AREA_ACCESO']
user_name = user_data['USUARIO']

# Barra Lateral
with st.sidebar:
    st.image(LOGO_DEFAULT_URL, use_column_width=True)
    st.markdown(f"""
        <div style="background-color: white; padding: 10px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #eee;">
            <div style="font-weight: bold; color: {COLOR_PRIMARY}">👤 {user_name}</div>
            <div style="font-size: 12px; color: #666;">Rol: {rol}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Menú
    menu_opts = ["📊 Dashboard", "📈 Tablero Operativo"]
    if rol in ['ADMIN', 'ADMIN_DELEGADO', 'LIDER']: menu_opts.append("📝 Reportar Datos")
    if rol in ['ADMIN', 'ADMIN_DELEGADO']: menu_opts.append("⚙️ Configuración")
    
    op = st.radio("Navegación:", menu_opts)
    
    st.markdown("---")
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.user_info = None
        st.rerun()

# Cabecera
st.title(op.replace('📊 ', '').replace('📈 ', '').replace('📝 ', '').replace('⚙️ ', ''))

# --- LÓGICA DE LAS VISTAS ---

# 1. DASHBOARD
if "Dashboard" in op:
    df = obtener_indicadores()
    
    # Filtrar por área si no es ADMIN/CEO
    if area_perm != 'TODAS':
        df = df[df['ÁREA'] == area_perm]
    
    if df.empty:
        st.info("No hay indicadores asignados a tu área.")
    else:
        # Filtros Superiores
        col_f1, col_f2 = st.columns(2)
        areas_disponibles = ['TODAS'] + list(df['ÁREA'].unique())
        filtro_area = col_f1.selectbox("Filtrar por Área", areas_disponibles)
        
        df_view = df if filtro_area == 'TODAS' else df[df['ÁREA'] == filtro_area]
        
        # Selección de KPI
        kpis = df_view['INDICADOR'].unique()
        kpi_sel = st.selectbox("Seleccionar Indicador para Detalle", kpis)
        
        # Obtener datos del KPI seleccionado
        row = df_view[df_view['INDICADOR'] == kpi_sel].iloc[0]
        meta_val = row['META_VALOR']
        meta_txt = row['META_TEXTO']
        
        # Datos para gráfico
        y_vals = []
        x_vals = []
        ultimo_valor = 0
        ultimo_mes = ""
        
        for m in MESES:
            if pd.notna(row[m]):
                y_vals.append(row[m])
                x_vals.append(m)
                ultimo_valor = row[m]
                ultimo_mes = m
        
        # Tarjeta Resumen
        c_kpi, c_chart = st.columns([1, 3])
        
        with c_kpi:
            color_delta = "normal"
            delta_val = f"Meta: {meta_txt}"
            
            # Comparación visual simple
            is_good = False
            if row['LOGICA'] == 'MAX': is_good = ultimo_valor >= meta_val
            else: is_good = ultimo_valor <= meta_val
            
            color_val = "#27ae60" if is_good else "#c0392b"
            
            st.markdown(f"""
                <div class="kpi-card" style="border-left-color: {color_val}">
                    <div class="kpi-title">Último Cierre ({ultimo_mes})</div>
                    <div class="kpi-value" style="color: {color_val}">{ultimo_valor:.1%}</div>
                    <div class="kpi-meta">{delta_val}</div>
                </div>
            """, unsafe_allow_html=True)
            
            st.info(f"**Responsable:**\n{row['RESPONSABLE']}")

        with c_chart:
            fig = go.Figure()
            # Línea de Meta
            fig.add_trace(go.Scatter(
                x=MESES, y=[meta_val]*len(MESES),
                name='Meta', line=dict(color='gray', dash='dash', width=1)
            ))
            # Línea Real
            fig.add_trace(go.Scatter(
                x=x_vals, y=y_vals,
                name='Real', mode='lines+markers+text',
                line=dict(color=COLOR_PRIMARY, width=3),
                marker=dict(size=8),
                text=[f"{v:.1%}" for v in y_vals],
                textposition="top center"
            ))
            
            fig.update_layout(
                title=f"Evolución: {kpi_sel}",
                yaxis=dict(tickformat=".0%", title="Cumplimiento"),
                xaxis=dict(title="Periodo"),
                margin=dict(l=20, r=20, t=40, b=20),
                height=350,
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("### 📋 Detalle Tabular")
        st.dataframe(df_view.style.format({m: "{:.1%}" for m in MESES}), use_container_width=True)

# 2. TABLERO OPERATIVO (EDICIÓN DE MASTERS)
elif "Tablero Operativo" in op:
    st.info("💡 Este módulo permite la gestión de los archivos planos maestros.")
    
    tab_nombres = list(ESTRUCTURA_COLUMNAS.keys())
    tabs = st.tabs(tab_nombres)
    
    for i, key in enumerate(tab_nombres):
        with tabs[i]:
            df_curr = st.session_state.dfs_master[key]
            
            if rol == 'CEO':
                st.dataframe(df_curr, use_container_width=True)
            else:
                edited_df = st.data_editor(df_curr, num_rows="dynamic", use_container_width=True, key=f"editor_{key}")
                
                if st.button(f"Guardar Cambios en {key}", key=f"btn_{key}"):
                    st.session_state.dfs_master[key] = edited_df
                    registrar_log(user_name, "Edición Operativa", f"Tabla {key}")
                    st.success("✅ Datos actualizados correctamente en memoria.")

# 3. REPORTAR INDICADORES
elif "Reportar Datos" in op:
    df_ind = obtener_indicadores()
    
    # Filtrar areas permitidas
    areas = df_ind['ÁREA'].unique()
    if area_perm != 'TODAS': areas = [a for a in areas if a == area_perm]
    
    col1, col2 = st.columns(2)
    area_sel = col1.selectbox("Seleccionar Área", areas)
    mes_sel = col2.selectbox("Mes de Reporte", MESES)
    
    st.markdown("---")
    st.markdown(f"**Ingreso de datos para: {area_sel} - {mes_sel}**")
    
    # Filtrar DF para editar
    df_filtered = df_ind[df_ind['ÁREA'] == area_sel].copy()
    
    with st.form("form_reporte"):
        inputs = {}
        for idx, row in df_filtered.iterrows():
            st.markdown(f"##### {row['INDICADOR']}")
            st.caption(f"Meta: {row['META_TEXTO']} ({row['RESPONSABLE']})")
            
            val_actual = row[mes_sel] if pd.notna(row[mes_sel]) else 0.0
            # Input numérico en porcentaje (0-100)
            inputs[idx] = st.number_input(
                "Resultado (%)", 
                min_value=0.0, max_value=100.0, 
                value=float(val_actual)*100, 
                step=0.01,
                key=f"in_{idx}"
            )
            st.markdown("---")
            
        if st.form_submit_button("💾 Guardar Reporte", use_container_width=True):
            # Actualizar DF Principal
            for idx, val in inputs.items():
                df_ind.at[idx, mes_sel] = val / 100.0 # Convertir de nuevo a decimal
            
            guardar_indicadores(df_ind)
            registrar_log(user_name, "Reporte Indicador", f"{area_sel} - {mes_sel}")
            st.success("Datos guardados exitosamente.")
            time.sleep(1)
            st.rerun()

# 4. ADMINISTRACIÓN
elif "Configuración" in op:
    tab_usr, tab_logs = st.tabs(["👥 Gestión de Usuarios", "📜 Auditoría"])
    
    with tab_usr:
        st.subheader("Usuarios del Sistema")
        
        # Mostrar tabla (ocultando password)
        df_users = st.session_state.db_usuarios
        st.dataframe(df_users[['USUARIO', 'ROL', 'AREA_ACCESO']], use_container_width=True)
        
        with st.expander("➕ Crear Nuevo Usuario"):
            with st.form("new_user"):
                nu = st.text_input("Usuario")
                np = st.text_input("Contraseña", type="password")
                nr = st.selectbox("Rol", ["LIDER", "CEO", "ADMIN_DELEGADO"])
                na = st.selectbox("Área", ["TODAS"] + list(obtener_indicadores()['ÁREA'].unique()))
                
                if st.form_submit_button("Crear"):
                    if nu and np:
                        new_row = pd.DataFrame([[nu, np, nr, na]], columns=df_users.columns)
                        st.session_state.db_usuarios = pd.concat([df_users, new_row], ignore_index=True)
                        registrar_log(user_name, "Crear Usuario", nu)
                        st.success("Usuario creado.")
                        st.rerun()
                    else:
                        st.warning("Complete todos los campos.")

    with tab_logs:
        st.subheader("Registro de Actividad")
        st.dataframe(
            st.session_state.db_logs.sort_values(by="FECHA", ascending=False), 
            use_container_width=True
        )

# Pie de página
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #95a5a6; font-size: 0.8rem;'>"
    "Ciclo de Ingresos Christus Health © 2025 | v2.1.0"
    "</div>", 
    unsafe_allow_html=True
)
