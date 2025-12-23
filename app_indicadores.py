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

# Nombres de archivos operativos (MASTER)
FILES_MASTER = {
    'ADMISIONES': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - ADMISIONES.csv',
    'AUTORIZACIONES': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - AUTORIZACIONES.csv',
    'FACTURACION': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - FACTURACION.csv',
    'RADICACION': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - RADICACION.csv',
    'GLOSAS': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - GLOSAS Y DEVOLUCIONES.csv',
    'CARTERA': 'Tablero_Ciclo_Ingresos_MASTER.xlsx - CARTERA.csv'
}

# --- ESTRUCTURA EXACTA DE COLUMNAS (Para el Editor) ---
ESTRUCTURA_COLUMNAS = {
    'FACTURACION': ['AÑO', 'MES', 'Ranking', 'Aseguradora / Cliente', 'Valor Facturado', '% Participación'],
    'RADICACION': ['AÑO', 'MES', 'Aseguradora', 'No. Facturas', 'Valor Radicado', 'Fecha Corte'],
    'GLOSAS': ['AÑO', 'MES', 'Aseguradora', 'Valor Devoluciones', 'Valor Glosa Inicial', 'Valor Rechazado', 'Valor Aceptado', '% Gestionado'],
    'CARTERA': ['AÑO', 'MES', 'Aseguradora', 'Saldo Inicial', 'Meta Recaudo', 'Recaudo Real', '% Cumplimiento'],
    'AUTORIZACIONES': ['AÑO', 'MES', 'Tipo Solicitud', 'Gestionadas', 'Aprobadas', 'Pendientes', 'Negadas', '% Efectividad'],
    'ADMISIONES': ['AÑO', 'MES', 'Sede / Concepto', 'MES_LETRAS', 'Cantidad Actividades'] 
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

# Meses
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
def cargar_datos_master_disco():
    data = {}
    missing = []
    
    for key, filename in FILES_MASTER.items():
        # Definir estructura esperada
        cols_esperadas = ESTRUCTURA_COLUMNAS.get(key, ['AÑO', 'MES'])
        
        if os.path.exists(filename):
            try:
                try:
                    df = pd.read_csv(filename, sep=',')
                    if len(df.columns) < 2: df = pd.read_csv(filename, sep=';')
                except:
                    df = pd.read_csv(filename, sep=';', encoding='latin1')
                
                # Limpieza de nombres de columnas
                df.columns = df.columns.str.strip()
                
                # Mapeo de columnas si difieren ligeramente
                if key == 'ADMISIONES':
                    df.columns = [c.replace('MES.1', 'MES_LETRAS') if 'MES.' in c else c for c in df.columns]
                
                # Asegurar que existan todas las columnas requeridas
                for col in cols_esperadas:
                    if col not in df.columns:
                        df[col] = None 
                
                # Reordenar y filtrar columnas extrañas
                df = df[cols_esperadas]
                
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
                # Si falla, crear estructura vacía correcta
                data[key] = pd.DataFrame(columns=cols_esperadas)
        else:
            missing.append(filename)
            data[key] = pd.DataFrame(columns=cols_esperadas)
    return data, missing

def guardar_datos_master_disco(dfs):
    for key, df in dfs.items():
        filename = FILES_MASTER[key]
        df.to_csv(filename, index=False)

# Inicializar sesión de datos master
if 'dfs_master' not in st.session_state:
    st.session_state.dfs_master, st.session_state.faltantes_master = cargar_datos_master_disco()

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

if 'df_ind' not in st.session_state:
    st.session_state.df_ind = cargar_datos_ind()
df_ind = st.session_state.df_ind

# --- MENÚ ---
menu = ["📊 Dashboard Indicadores (Oficial)", "📈 Tablero Operativo (Data Master)"]
if rol in ['ADMIN', 'LIDER']:
    menu.append("📝 Reportar Indicador")
if rol == 'ADMIN':
    menu.append("⚙️ Admin Usuarios")

opcion = st.sidebar.radio("Navegación:", menu)

# --- VISTA: TABLERO OPERATIVO MASTER (MODIFICADO) ---
if opcion == "📈 Tablero Operativo (Data Master)":
    
    tab_vis, tab_edit = st.tabs(["📊 Visualización KPIs", "📝 Editor de Datos (Operativo)"])
    
    # -----------------------------------------------
    # PESTAÑA 1: VISUALIZACIÓN
    # -----------------------------------------------
    with tab_vis:
        st.header("Tablero Operativo - Consolidado")
        
        # Filtros de Tiempo
        anios = [2025, 2026]
        meses_dict = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}
        
        c1, c2 = st.columns(2)
        anio_sel = c1.selectbox("Año Op.", anios)
        mes_sel = c2.selectbox("Mes Op.", list(meses_dict.keys()), format_func=lambda x: meses_dict[x], index=10 if anio_sel==2025 else 0)
        
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

        dfs_m = st.session_state.dfs_master
        
        facturado = get_kpi(dfs_m['FACTURACION'], ['Valor Facturado', 'FACTURADO'])
        radicado = get_kpi(dfs_m['RADICACION'], ['Valor Radicado', 'RADICADO'])
        brecha = facturado - radicado
        recaudo = get_kpi(dfs_m['CARTERA'], ['Recaudo Real', 'REAL'])
        meta_rec = get_kpi(dfs_m['CARTERA'], ['Meta Recaudo', 'META'])
        cump = (recaudo / meta_rec) if meta_rec > 0 else 0
        
        # KPIs Glosas
        glosa_inicial = get_kpi(dfs_m['GLOSAS'], ['Valor Glosa Inicial', 'INICIAL'])
        devoluciones = get_kpi(dfs_m['GLOSAS'], ['Valor Devoluciones', 'DEVOLUCIONES'])
        levantado = get_kpi(dfs_m['GLOSAS'], ['Valor Rechazado', 'Rechazado'])
        aceptado = get_kpi(dfs_m['GLOSAS'], ['Valor Aceptado', 'Aceptado'])
        
        def kpi_card_html(title, val, is_pct=False, color="#0F1C3F"):
            fmt = f"{val:.1%}" if is_pct else f"${val:,.0f}"
            return f"""<div class="kpi-card"><div class="kpi-title">{title}</div><div class="kpi-value" style="color:{color}">{fmt}</div></div>"""
        
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(kpi_card_html("Facturado", facturado), unsafe_allow_html=True)
        with k2: st.markdown(kpi_card_html("Radicado", radicado), unsafe_allow_html=True)
        with k3: st.markdown(kpi_card_html("Recaudo Real", recaudo), unsafe_allow_html=True)
        with k4: st.markdown(kpi_card_html("% Cumplimiento", cump, True, "green" if cump >= 0.9 else "orange"), unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("Gestión de Glosas y Devoluciones")
        g1, g2, g3, g4 = st.columns(4)
        with g1: st.markdown(kpi_card_html("Devoluciones", devoluciones), unsafe_allow_html=True)
        with g2: st.markdown(kpi_card_html("Glosa Inicial", glosa_inicial), unsafe_allow_html=True)
        with g3: st.markdown(kpi_card_html("Levantado (Recuperado)", levantado, False, "green"), unsafe_allow_html=True)
        with g4: st.markdown(kpi_card_html("Aceptado (Pérdida)", aceptado, False, "red"), unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("Detalle Operativo (Facturación)")
        df_fac = dfs_m['FACTURACION']
        if not df_fac.empty and 'AÑO' in df_fac.columns:
            mask = (df_fac['AÑO'] == anio_sel) & (df_fac['MES'] == mes_sel)
            st.dataframe(df_fac[mask], use_container_width=True, hide_index=True)
        else:
            st.info("Sin datos para este periodo.")

    # -----------------------------------------------
    # PESTAÑA 2: EDITOR DE DATOS (NUEVO CON FILTRO)
    # -----------------------------------------------
    with tab_edit:
        st.header("📝 Gestión de Datos Operativos (Por Periodo)")
        st.info("Seleccione el periodo específico que desea editar o cargar. Esto evita cargar todo el histórico.")
        
        col_db, col_anio, col_mes = st.columns([2, 1, 1])
        
        with col_db:
            dataset_name = st.selectbox("Base de Datos:", list(FILES_MASTER.keys()))
        with col_anio:
            edit_anio = st.selectbox("Año Edición:", [2025, 2026])
        with col_mes:
            edit_mes = st.selectbox("Mes Edición:", list(range(1, 13)), index=10) # Default Nov
            
        # Cargar DF completo de sesión
        df_full = st.session_state.dfs_master[dataset_name]
        
        # --- FIX: Ensure AÑO and MES exist before filtering ---
        if 'AÑO' not in df_full.columns:
            df_full['AÑO'] = 0
        if 'MES' not in df_full.columns:
            df_full['MES'] = 0
            
        # Ensure correct types for filtering
        df_full['AÑO'] = pd.to_numeric(df_full['AÑO'], errors='coerce').fillna(0).astype(int)
        df_full['MES'] = pd.to_numeric(df_full['MES'], errors='coerce').fillna(0).astype(int)
        
        # Filtrar solo el periodo seleccionado para editar
        if not df_full.empty:
            mask_edit = (df_full['AÑO'] == edit_anio) & (df_full['MES'] == edit_mes)
            df_periodo = df_full[mask_edit].copy()
        else:
            df_periodo = pd.DataFrame(columns=ESTRUCTURA_COLUMNAS[dataset_name])
            
        # Si está vacío el periodo, inicializar con estructura correcta para permitir pegar
        if df_periodo.empty:
            df_periodo = pd.DataFrame(columns=ESTRUCTURA_COLUMNAS[dataset_name])
        
        st.markdown(f"### Editando: {dataset_name} - {edit_mes}/{edit_anio}")
        st.caption("Pegue aquí los datos desde Excel (Ctrl+V). Asegúrese de que las columnas coincidan.")
        
        # Editor
        edited_periodo = st.data_editor(
            df_periodo,
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{dataset_name}_{edit_anio}_{edit_mes}",
            column_config={
                "AÑO": st.column_config.NumberColumn(format="%d", disabled=False),
                "MES": st.column_config.NumberColumn(format="%d", disabled=False),
            }
        )
        
        # Botón Guardar (Lógica de Fusión)
        if st.button(f"💾 Guardar Periodo {edit_mes}/{edit_anio}"):
            # 1. Eliminar datos viejos de este periodo en el DF principal
            # Se usa una máscara segura
            mask_old = (df_full['AÑO'] == edit_anio) & (df_full['MES'] == edit_mes)
            df_clean = df_full[~mask_old]
            
            # 2. Asegurar que los datos nuevos tengan el año/mes correcto
            # Si el usuario pegó datos sin año/mes, se los ponemos
            if not edited_periodo.empty:
                if 'AÑO' in edited_periodo.columns:
                    edited_periodo['AÑO'] = edited_periodo['AÑO'].fillna(edit_anio).astype(int)
                else:
                    edited_periodo['AÑO'] = edit_anio
                    
                if 'MES' in edited_periodo.columns:
                    edited_periodo['MES'] = edited_periodo['MES'].fillna(edit_mes).astype(int)
                else:
                    edited_periodo['MES'] = edit_mes
                    
                # Fix specific for AÑO/MES being 0 or empty after paste if not mapped correctly
                edited_periodo.loc[edited_periodo['AÑO'] == 0, 'AÑO'] = edit_anio
                edited_periodo.loc[edited_periodo['MES'] == 0, 'MES'] = edit_mes
            
            # 3. Concatenar
            df_final = pd.concat([df_clean, edited_periodo], ignore_index=True)
            
            # 4. Actualizar sesión y disco
            st.session_state.dfs_master[dataset_name] = df_final
            filename = FILES_MASTER[dataset_name]
            df_final.to_csv(filename, index=False)
            
            st.success(f"¡Datos del periodo {edit_mes}/{edit_anio} guardados exitosamente!")
            time.sleep(1)
            st.rerun()

# ==========================================
# MODULO 1: ADMIN USUARIOS (Igual al anterior)
# ==========================================
elif opcion == "⚙️ Admin Usuarios":
    st.title("Gestión de Usuarios")
    df_users = cargar_usuarios()
    st.dataframe(df_users, hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Crear Usuario")
        with st.form("new_u"):
            nu = st.text_input("Usuario"); np = st.text_input("Pass"); nr = st.selectbox("Rol", ["LIDER", "CEO", "ADMIN"])
            na = st.selectbox("Área", ['TODAS'] + list(df_ind['ÁREA'].unique()))
            if st.form_submit_button("Crear"):
                if nu and np:
                    new_row = pd.DataFrame([[nu, np, nr, na]], columns=df_users.columns)
                    df_users = pd.concat([df_users, new_row], ignore_index=True)
                    guardar_usuarios(df_users); st.success("Creado"); st.rerun()
    with c2:
        st.subheader("Eliminar")
        u_del = st.selectbox("Eliminar Usuario", df_users['USUARIO'].unique())
        if st.button("Eliminar"):
            if u_del != 'admin':
                df_users = df_users[df_users['USUARIO'] != u_del]
                guardar_usuarios(df_users); st.success("Eliminado"); st.rerun()

# ==========================================
# MODULO 2: REPORTE INDICADORES
# ==========================================
elif opcion == "📝 Reportar Indicador":
    st.header("Reporte Mensual Indicadores")
    areas_posibles = df_ind['ÁREA'].unique()
    if area_permiso != 'TODAS': areas_posibles = [a for a in areas_posibles if a == area_permiso]
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
            for i, v in inputs.items(): df_ind.at[i, mes_sel] = v / 100
            st.session_state.df_ind = df_ind; guardar_datos_ind(df_ind); st.success("Guardado.")

# ==========================================
# MODULO 3: DASHBOARD INDICADORES
# ==========================================
elif opcion == "📊 Dashboard Indicadores (Oficial)":
    st.header("Tablero de Mando - Indicadores")
    df_view = df_ind if area_permiso == 'TODAS' else df_ind[df_ind['ÁREA'] == area_permiso]
    kpi_sel = st.selectbox("Indicador:", df_view['INDICADOR'].unique())
    row = df_ind[df_ind['INDICADOR'] == kpi_sel].iloc[0]
    meta = row['META_VALOR']; logica = row['LOGICA']
    y_data = [row[m] if pd.notna(row[m]) else None for m in MESES]
    last_val = None
    for m in reversed(MESES):
        if pd.notna(row[m]): last_val = row[m]; break
    c1, c2 = st.columns(2)
    c1.metric("Meta", row['META_TEXTO'])
    if last_val is not None:
        color = "normal" if logica == 'MAX' else "inverse"
        c2.metric("Último", f"{last_val:.1%}", f"{last_val-meta:.1%}", delta_color=color)
    else: c2.metric("Último", "Sin Datos")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=MESES, y=[meta]*len(MESES), mode='lines', name='Meta', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=MESES, y=y_data, mode='lines+markers+text', name='Real', line=dict(color='#0F1C3F'), text=[f"{v:.1%}" if v else "" for v in y_data], textposition="top center"))
    fig.update_layout(template="plotly_white", yaxis_tickformat='.0%'); st.plotly_chart(fig, use_container_width=True)
