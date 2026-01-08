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
LOGO_DEFAULT_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Christus_Health_Logo.svg/1200px-Christus_Health_Logo.svg.png"

# RUTA EXACTA DE TU BASE DE DATOS
DB_PATH = r"C:\Users\pedro\OneDrive\GENERAL ANTIGUA\Escritorio\mi_proyecto_inventario\Christus_DB_Master.db"

MESES = ['NOV-25', 'DIC-25', 'ENE-26', 'FEB-26', 'MAR-26', 'ABR-26', 'MAY-26', 
         'JUN-26', 'JUL-26', 'AGO-26', 'SEP-26', 'OCT-26', 'NOV-26', 'DIC-26']

# Mapeo de Tablero Operativo: Nombre UI -> Nombre Tabla BD
MAPA_TABLAS_OPERATIVAS = {
    'FACTURACION': 'ope_facturacion',
    'RADICACION': 'ope_radicacion',
    'GLOSAS': 'ope_glosas', # Nota: Antes no teníamos Glosas, la agregamos
    'CARTERA': 'ope_cartera',
    'AUTORIZACIONES': 'ope_autorizaciones',
    'ADMISIONES': 'ope_admisiones',
    'PROVISION': 'ope_provision'
}

# Estructura de columnas para visualización
ESTRUCTURA_COLUMNAS = {
    'FACTURACION': ['AÑO', 'MES', 'Ranking', 'Aseguradora / Cliente', 'Valor Facturado', '% Participación'],
    'RADICACION': ['AÑO', 'MES', 'Aseguradora', 'No. Facturas', 'Valor Radicado', 'Fecha Corte'],
    'GLOSAS': ['AÑO', 'MES', 'Aseguradora', 'Valor Devoluciones', 'Valor Glosa Inicial', 'Valor Rechazado', 'Valor Aceptado', '% Gestionado'],
    'CARTERA': ['AÑO', 'MES', 'Aseguradora', 'Saldo Inicial', 'Meta Recaudo', 'Recaudo Real', '% Cumplimiento'],
    'AUTORIZACIONES': ['AÑO', 'MES', 'Tipo Solicitud', 'Gestionadas', 'Aprobadas', 'Pendientes', 'Negadas', '% Efectividad'],
    'ADMISIONES': ['AÑO', 'MES', 'Sede / Concepto', 'MES_LETRAS', 'Cantidad Actividades', 'Valor Estimado Ingreso', 'Promedio por Paciente'],
    'PROVISION': ['AÑO', 'MES', 'Aseguradora', 'Fecha Corte', 'Prov. Acostados', 'Prov. Ambulatorios', 'Prov. Egresados', 'Facturado Sin Radicar', 'Cant. Glosas Pendientes', 'Valor Glosas Pendientes']
}

# Datos Maestros Iniciales (Para poblar la BD si está vacía)
DATOS_MAESTROS_IND_INICIAL = [
    ['FACTURACIÓN', 'Dir. Facturación', 'Facturación oportuna (≤72h egreso)', 0.95, 'MAX', '>95%'],
    ['FACTURACIÓN', 'Dir. Facturación', 'Radicación oportuna (≤22 días)', 0.98, 'MAX', '>98%'],
    ['CUENTAS MÉDICAS', 'Jefatura Cuentas Médicas', '% de glosas aceptadas en el mes', 0.02, 'MIN', '<2%'],
    ['ADMISIONES', 'Coordinación Admisiones', '% de facturas anuladas por falta de autorización', 0.01, 'MIN', '≤ 1%'],
    ['AUTORIZACIONES', 'Coord. Autorizaciones', '% de autorizaciones generadas en ≤7 horas', 1.00, 'MAX', '100%'],
    ['CARTERA', 'Jefatura de Cartera', 'Recuperación de Glosa', 0.85, 'MAX', '> 85%'],
    ['CARTERA', 'Jefatura de Cartera', '% de cartera vencida >60 días', 0.60, 'MIN', '< 60%']
]

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
    .kpi-meta {{ font-size: 12px; color: #27ae60; font-weight: bold; margin-top: 5px; }}
    h1, h2, h3 {{ color: {COLOR_PRIMARY}; }}
    .stButton>button {{ background-color: {COLOR_PRIMARY}; color: white; border-radius: 5px; }}
    .stButton>button:hover {{ background-color: #552b80; border-color: #552b80; }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# GESTIÓN DE BASE DE DATOS (SQLite)
# ==============================================================================

def get_connection():
    """Establece conexión con la base de datos en la ruta especificada."""
    # Verificar si el directorio existe, si no, intentar crearlo (opcional, pero seguro)
    directory = os.path.dirname(DB_PATH)
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except OSError:
            pass # Si no se puede crear, esperamos que la ruta ya sea válida o el usuario corrija
            
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_db():
    """Inicializa las tablas y datos semilla si no existen."""
    conn = get_connection()
    c = conn.cursor()

    # 1. Tabla Usuarios (Con estructura compatible)
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL,
            area_acceso TEXT NOT NULL
        )
    """)

    # 2. Tabla Logs
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            usuario TEXT,
            accion TEXT,
            detalle TEXT
        )
    """)

    # 3. Tabla Indicadores Metadata (Definición del KPI)
    c.execute("""
        CREATE TABLE IF NOT EXISTS indicadores_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area TEXT,
            responsable TEXT,
            indicador TEXT UNIQUE,
            meta_valor REAL,
            logica TEXT,
            meta_texto TEXT
        )
    """)

    # 4. Tabla Indicadores Valores (Los datos mes a mes)
    c.execute("""
        CREATE TABLE IF NOT EXISTS indicadores_valores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicador_id INTEGER,
            periodo TEXT,
            valor REAL,
            FOREIGN KEY(indicador_id) REFERENCES indicadores_meta(id)
        )
    """)

    # 5. Tablas Operativas (Crear estructura vacía si no existe)
    for nombre_tabla in MAPA_TABLAS_OPERATIVAS.values():
        # Creamos una tabla genérica, las columnas específicas se gestionan al cargar dataframes
        # Aquí usamos JSON o texto flexible para simplificar la creación dinámica si cambia el Excel
        # Pero para que funcione el editor, intentaremos crear una estructura básica o dejar que pandas la cree
        pass 

    conn.commit()

    # --- SEED DATA (Datos de prueba si está vacío) ---
    # Verificar usuarios
    cursor = conn.execute("SELECT count(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        c.executemany("INSERT INTO usuarios (usuario, password, rol, area_acceso) VALUES (?, ?, ?, ?)", [
            ('Administrador', 'Agosto2025', 'ADMIN', 'TODAS'),
            ('Gerente', '1234', 'CEO', 'TODAS'),
            ('LiderFacturacion', '1234', 'LIDER', 'FACTURACIÓN')
        ])
        conn.commit()

    # Verificar indicadores
    cursor = conn.execute("SELECT count(*) FROM indicadores_meta")
    if cursor.fetchone()[0] == 0:
        for row in DATOS_MAESTROS_IND_INICIAL:
            c.execute("INSERT INTO indicadores_meta (area, responsable, indicador, meta_valor, logica, meta_texto) VALUES (?, ?, ?, ?, ?, ?)", row)
        conn.commit()
    
    conn.close()

# Inicializar al arrancar
init_db()

# --- FUNCIONES CRUD SQL ---

def autenticar(user, pwd):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM usuarios WHERE usuario = ? AND password = ?", conn, params=(user, pwd))
    conn.close()
    if not df.empty:
        # Normalizamos nombres de columnas para que coincidan con la app
        return df.iloc[0].rename({'usuario': 'USUARIO', 'rol': 'ROL', 'area_acceso': 'AREA_ACCESO'})
    return None

def registrar_log(usuario, accion, detalle):
    conn = get_connection()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO logs (fecha, usuario, accion, detalle) VALUES (?, ?, ?, ?)", (fecha, usuario, accion, detalle))
    conn.commit()
    conn.close()

def obtener_indicadores_completo():
    """
    Combina metadata y valores para recrear el DataFrame ancho (pivoteado) que usa la UI.
    """
    conn = get_connection()
    
    # 1. Leer Metadata
    df_meta = pd.read_sql("SELECT * FROM indicadores_meta", conn)
    
    # 2. Leer Valores
    df_vals = pd.read_sql("SELECT * FROM indicadores_valores", conn)
    conn.close()
    
    if df_vals.empty:
        # Si no hay valores, devolver solo meta con columnas de meses vacías
        for m in MESES:
            df_meta[m] = 0.0
    else:
        # Pivotear valores: filas=indicador_id, columnas=periodo, valor=valor
        pivot = df_vals.pivot(index='indicador_id', columns='periodo', values='valor')
        # Unir con metadata
        df_meta = df_meta.join(pivot, on='id')
    
    # Renombrar columnas para que coincidan con UI
    df_meta = df_meta.rename(columns={
        'area': 'ÁREA', 'responsable': 'RESPONSABLE', 'indicador': 'INDICADOR',
        'meta_valor': 'META_VALOR', 'logica': 'LOGICA', 'meta_texto': 'META_TEXTO'
    })
    
    return df_meta

def guardar_reporte_indicador(indicador_nombre, mes, valor):
    """Guarda un valor específico en la tabla transaccional."""
    conn = get_connection()
    c = conn.cursor()
    
    # Obtener ID del indicador
    c.execute("SELECT id FROM indicadores_meta WHERE indicador = ?", (indicador_nombre,))
    res = c.fetchone()
    if res:
        ind_id = res[0]
        # Verificar si ya existe el registro para ese mes
        c.execute("SELECT id FROM indicadores_valores WHERE indicador_id = ? AND periodo = ?", (ind_id, mes))
        existe = c.fetchone()
        
        if existe:
            c.execute("UPDATE indicadores_valores SET valor = ? WHERE id = ?", (valor, existe[0]))
        else:
            c.execute("INSERT INTO indicadores_valores (indicador_id, periodo, valor) VALUES (?, ?, ?)", (ind_id, mes, valor))
        conn.commit()
    conn.close()

def obtener_tabla_operativa(nombre_tabla_bd):
    conn = get_connection()
    try:
        df = pd.read_sql(f"SELECT * FROM {nombre_tabla_bd}", conn)
    except:
        df = pd.DataFrame() # Tabla no existe aún
    conn.close()
    return df

def guardar_tabla_operativa(df, nombre_tabla_bd):
    conn = get_connection()
    # Reemplazamos la tabla completa con la edición (para este caso de uso de editor simple)
    # En producción masiva, sería mejor UPDATE por ID.
    df.to_sql(nombre_tabla_bd, conn, if_exists='replace', index=False)
    conn.close()

def crear_usuario_nuevo(u, p, r, a):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO usuarios (usuario, password, rol, area_acceso) VALUES (?, ?, ?, ?)", (u, p, r, a))
        conn.commit()
        exito = True
    except:
        exito = False
    conn.close()
    return exito

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
                    st.error("Credenciales incorrectas.")
        
        st.info(f"📁 Conectado a BD:\n{DB_PATH}")
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
    if rol in ['ADMIN', 'ADMIN_DELEGADO', 'LIDER', 'CEO']: menu_opts.append("📝 Reportar Datos")
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
    df = obtener_indicadores_completo()
    
    # Filtrar por área si no es ADMIN/CEO
    if area_perm != 'TODAS':
        df = df[df['ÁREA'] == area_perm]
    
    if df.empty:
        st.info("No hay indicadores asignados a tu área o la base de datos está vacía.")
    else:
        # Filtros Superiores
        col_f1, col_f2 = st.columns(2)
        areas_disponibles = ['TODAS'] + list(df['ÁREA'].unique())
        filtro_area = col_f1.selectbox("Filtrar por Área", areas_disponibles)
        
        df_view = df if filtro_area == 'TODAS' else df[df['ÁREA'] == filtro_area]
        
        if df_view.empty:
             st.warning("No hay datos para esta selección.")
        else:
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
                if m in row and pd.notna(row[m]):
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
                        <div class="kpi-title">Último Cierre ({ultimo_mes if ultimo_mes else '-'})</div>
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
            # Formatear solo columnas que existen
            format_dict = {m: "{:.1%}" for m in MESES if m in df_view.columns}
            st.dataframe(df_view.style.format(format_dict), use_container_width=True)

# 2. TABLERO OPERATIVO
elif "Tablero Operativo" in op:
    st.info("💡 Gestión de tablas operativas. Los cambios se guardan directamente en la Base de Datos SQL.")
    
    tab_nombres = list(MAPA_TABLAS_OPERATIVAS.keys())
    tabs = st.tabs(tab_nombres)
    
    for i, key in enumerate(tab_nombres):
        with tabs[i]:
            tabla_bd = MAPA_TABLAS_OPERATIVAS[key]
            df_curr = obtener_tabla_operativa(tabla_bd)
            
            # Si la tabla está vacía en BD, intentamos crear un esqueleto con las columnas definidas
            if df_curr.empty and key in ESTRUCTURA_COLUMNAS:
                df_curr = pd.DataFrame(columns=ESTRUCTURA_COLUMNAS[key])
            
            if rol == 'CEO':
                st.dataframe(df_curr, use_container_width=True)
            else:
                edited_df = st.data_editor(df_curr, num_rows="dynamic", use_container_width=True, key=f"editor_{key}")
                
                if st.button(f"💾 Guardar Cambios en {key}", key=f"btn_{key}"):
                    try:
                        guardar_tabla_operativa(edited_df, tabla_bd)
                        registrar_log(user_name, "Edición Operativa", f"Tabla {tabla_bd}")
                        st.success(f"✅ Base de datos {tabla_bd} actualizada exitosamente.")
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

# 3. REPORTAR INDICADORES
elif "Reportar Datos" in op:
    df_ind = obtener_indicadores_completo()
    
    # Filtrar areas permitidas
    areas = df_ind['ÁREA'].unique()
    if area_perm != 'TODAS': areas = [a for a in areas if a == area_perm]
    
    if len(areas) == 0:
        st.error("No tienes áreas asignadas para reportar.")
    else:
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
                
                # Buscar valor actual si existe columna y dato
                val_actual = 0.0
                if mes_sel in row and pd.notna(row[mes_sel]):
                    val_actual = float(row[mes_sel])
                
                # Input numérico en porcentaje (0-100)
                inputs[row['INDICADOR']] = st.number_input(
                    "Resultado (%)", 
                    min_value=0.0, max_value=100.0, 
                    value=val_actual*100, 
                    step=0.01,
                    key=f"in_{idx}"
                )
                st.markdown("---")
                
            if st.form_submit_button("💾 Guardar Reporte", use_container_width=True):
                try:
                    for ind_nom, val in inputs.items():
                        guardar_reporte_indicador(ind_nom, mes_sel, val / 100.0)
                    
                    registrar_log(user_name, "Reporte Indicador", f"{area_sel} - {mes_sel}")
                    st.success("Datos guardados exitosamente en BD.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# 4. ADMINISTRACIÓN
elif "Configuración" in op:
    tab_usr, tab_logs = st.tabs(["👥 Gestión de Usuarios", "📜 Auditoría"])
    
    with tab_usr:
        st.subheader("Usuarios del Sistema")
        
        conn = get_connection()
        df_users = pd.read_sql("SELECT usuario, rol, area_acceso FROM usuarios", conn)
        conn.close()
        
        st.dataframe(df_users, use_container_width=True)
        
        with st.expander("➕ Crear Nuevo Usuario"):
            with st.form("new_user"):
                nu = st.text_input("Usuario")
                np = st.text_input("Contraseña", type="password")
                nr = st.selectbox("Rol", ["LIDER", "CEO", "ADMIN_DELEGADO", "ADMIN"])
                
                # Obtener áreas reales de la BD para el select
                conn = get_connection()
                areas_db = pd.read_sql("SELECT DISTINCT area FROM indicadores_meta", conn)['area'].tolist()
                conn.close()
                na = st.selectbox("Área", ["TODAS"] + areas_db)
                
                if st.form_submit_button("Crear"):
                    if nu and np:
                        if crear_usuario_nuevo(nu, np, nr, na):
                            registrar_log(user_name, "Crear Usuario", nu)
                            st.success("Usuario creado.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Error: El usuario ya existe.")
                    else:
                        st.warning("Complete todos los campos.")

    with tab_logs:
        st.subheader("Registro de Actividad")
        conn = get_connection()
        df_logs = pd.read_sql("SELECT * FROM logs ORDER BY id DESC LIMIT 500", conn)
        conn.close()
        st.dataframe(df_logs, use_container_width=True)

# Pie de página
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #95a5a6; font-size: 0.8rem;'>"
    "Ciclo de Ingresos Christus Health © 2026 | v3.0 SQL"
    "</div>", 
    unsafe_allow_html=True
)
