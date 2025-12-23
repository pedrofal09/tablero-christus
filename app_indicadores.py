import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Tablero Ciclo de Ingresos", layout="wide", page_icon="🔐")

# --- ARCHIVOS ---
ARCHIVO_DATOS = 'datos_indicadores_historico.csv'
ARCHIVO_USUARIOS = 'usuarios.csv'

# --- DATOS MAESTROS (Tus 27 indicadores oficiales) ---
DATOS_MAESTROS = [
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

# --- FUNCIONES ---

def cargar_usuarios():
    if not os.path.exists(ARCHIVO_USUARIOS):
        df_users = pd.DataFrame([
            ['admin', 'admin123', 'ADMIN', 'TODAS'],
            ['ceo', 'ceo123', 'CEO', 'TODAS']
        ], columns=['USUARIO', 'PASSWORD', 'ROL', 'AREA_ACCESO'])
        df_users.to_csv(ARCHIVO_USUARIOS, index=False)
        return df_users
    # Forzar tipo string para evitar problemas con contraseñas numéricas
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

def inicializar_datos():
    df = pd.DataFrame(DATOS_MAESTROS, columns=['ÁREA', 'RESPONSABLE', 'INDICADOR', 'META_VALOR', 'LOGICA', 'META_TEXTO'])
    for mes in MESES:
        df[mes] = None
    return df

def cargar_datos():
    if os.path.exists(ARCHIVO_DATOS):
        try:
            return pd.read_csv(ARCHIVO_DATOS)
        except:
            return inicializar_datos()
    return inicializar_datos()

def guardar_datos(df):
    df.to_csv(ARCHIVO_DATOS, index=False)

# --- ESTADO DE SESIÓN ---
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- PANTALLA LOGIN ---
if st.session_state.user_info is None:
    st.title("🔐 Acceso al Tablero")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
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
    st.subheader(f"👤 {user['USUARIO']}")
    st.caption(f"Rol: {rol} | Acceso: {area_permiso}")
    if st.button("Cerrar Sesión"):
        st.session_state.user_info = None
        st.rerun()
    st.markdown("---")

# Cargar Datos
if 'df_datos' not in st.session_state:
    st.session_state.df_datos = cargar_datos()
df = st.session_state.df_datos

# --- MENÚ DE NAVEGACIÓN ---
menu = ["📊 Dashboard Gerencial"]
if rol in ['ADMIN', 'LIDER']:
    menu.append("📝 Ingreso de Resultados")
if rol == 'ADMIN':
    menu.append("⚙️ Admin Usuarios")

opcion = st.sidebar.radio("Ir a:", menu)

# --- VISTA: ADMIN USUARIOS ---
if opcion == "⚙️ Admin Usuarios":
    st.title("Gestión de Usuarios")
    
    df_users = cargar_usuarios()
    
    # 1. Tabla de Usuarios
    st.subheader("Lista de Usuarios")
    st.dataframe(df_users, hide_index=True, use_container_width=True)
    
    col_a, col_b = st.columns(2)
    
    # 2. Crear Usuario
    with col_a:
        st.subheader("➕ Crear Nuevo Usuario")
        with st.form("crear_user"):
            new_u = st.text_input("Usuario (Login)")
            new_p = st.text_input("Contraseña")
            new_r = st.selectbox("Rol", ["LIDER", "CEO", "ADMIN"])
            areas_disp = ['TODAS'] + list(df['ÁREA'].unique())
            new_area = st.selectbox("Área Asignada", areas_disp)
            
            if st.form_submit_button("Crear"):
                if new_u in df_users['USUARIO'].values:
                    st.error("El usuario ya existe.")
                elif new_u and new_p:
                    new_row = pd.DataFrame([[new_u, new_p, new_r, new_area]], columns=df_users.columns)
                    df_users = pd.concat([df_users, new_row], ignore_index=True)
                    guardar_usuarios(df_users)
                    st.success("Usuario creado.")
                    st.rerun()
                else:
                    st.warning("Faltan datos.")

    # 3. Editar/Eliminar
    with col_b:
        st.subheader("✏️ Editar / Eliminar")
        user_to_edit = st.selectbox("Seleccionar Usuario a editar:", df_users['USUARIO'].unique())
        
        # Obtener datos actuales
        current_data = df_users[df_users['USUARIO'] == user_to_edit].iloc[0]
        
        with st.form("edit_user"):
            edit_pass = st.text_input("Nueva Contraseña", value=current_data['PASSWORD'])
            edit_rol = st.selectbox("Nuevo Rol", ["LIDER", "CEO", "ADMIN"], index=["LIDER", "CEO", "ADMIN"].index(current_data['ROL']))
            
            # Indice seguro para área
            areas_disp = ['TODAS'] + list(df['ÁREA'].unique())
            try:
                idx_area = areas_disp.index(current_data['AREA_ACCESO'])
            except:
                idx_area = 0
            edit_area = st.selectbox("Nueva Área", areas_disp, index=idx_area)
            
            col_save, col_del = st.columns(2)
            with col_save:
                if st.form_submit_button("💾 Guardar Cambios"):
                    df_users.loc[df_users['USUARIO'] == user_to_edit, 'PASSWORD'] = edit_pass
                    df_users.loc[df_users['USUARIO'] == user_to_edit, 'ROL'] = edit_rol
                    df_users.loc[df_users['USUARIO'] == user_to_edit, 'AREA_ACCESO'] = edit_area
                    guardar_usuarios(df_users)
                    st.success("Usuario actualizado.")
                    st.rerun()
            
            with col_del:
                if st.form_submit_button("🗑️ ELIMINAR USUARIO"):
                    if user_to_edit == 'admin':
                        st.error("No se puede eliminar al admin principal.")
                    else:
                        df_users = df_users[df_users['USUARIO'] != user_to_edit]
                        guardar_usuarios(df_users)
                        st.success("Usuario eliminado.")
                        st.rerun()

# --- VISTA: INGRESO DATOS ---
elif opcion == "📝 Ingreso de Resultados":
    st.header("Reporte Mensual")
    c1, c2 = st.columns(2)
    
    # Filtro de áreas según permisos
    areas_posibles = df['ÁREA'].unique()
    if area_permiso != 'TODAS':
        areas_posibles = [a for a in areas_posibles if a == area_permiso]
    
    with c1: 
        if len(areas_posibles) > 0:
            area_sel = st.selectbox("Área:", areas_posibles)
        else:
            st.error("No tienes área asignada.")
            st.stop()
    with c2: mes_sel = st.selectbox("Mes:", MESES)
    
    df_f = df[df['ÁREA'] == area_sel]
    
    with st.form("input_data"):
        inputs = {}
        for idx, row in df_f.iterrows():
            val = row[mes_sel] if pd.notna(row[mes_sel]) else 0.0
            st.markdown(f"**{row['INDICADOR']}** (Meta: {row['META_TEXTO']})")
            inputs[idx] = st.number_input("Resultado %", value=float(val)*100, step=0.1, key=idx)
            st.markdown("---")
        
        if st.form_submit_button("Guardar"):
            for i, v in inputs.items():
                df.at[i, mes_sel] = v / 100
            st.session_state.df_datos = df
            guardar_datos(df)
            st.success("Guardado.")

# --- VISTA: DASHBOARD ---
elif opcion == "📊 Dashboard Gerencial":
    st.header("Tablero de Mando")
    
    # Filtro de visualización según permisos
    if area_permiso == 'TODAS':
        df_view = df
    else:
        df_view = df[df['ÁREA'] == area_permiso]
        
    kpi_sel = st.selectbox("Indicador:", df_view['INDICADOR'].unique())
    
    row = df[df['INDICADOR'] == kpi_sel].iloc[0]
    meta = row['META_VALOR']
    logica = row['LOGICA']
    
    # Datos gráfico
    y_data = [row[m] if pd.notna(row[m]) else None for m in MESES]
    
    # Tarjetas
    last_val, last_mes = None, ""
    for m in reversed(MESES):
        if pd.notna(row[m]):
            last_val = row[m]
            last_mes = m
            break
            
    c1, c2, c3 = st.columns(3)
    c1.metric("Meta", row['META_TEXTO'])
    
    if last_val is not None:
        delta_color = "normal" if logica == 'MAX' else "inverse"
        c2.metric(f"Último ({last_mes})", f"{last_val:.1%}", f"{last_val-meta:.1%}", delta_color=delta_color)
    else:
        c2.metric("Último", "Sin Datos")
        
    c3.info(f"Responsable: {row['RESPONSABLE']}")
    
    # Gráfico
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=MESES, y=[meta]*len(MESES), mode='lines', name='Meta', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=MESES, y=y_data, mode='lines+markers+text', name='Real', line=dict(color='#0F1C3F'), text=[f"{v:.1%}" if v else "" for v in y_data], textposition="top center"))
    fig.update_layout(title=f"Tendencia: {kpi_sel}", template="plotly_white", yaxis_tickformat='.0%')
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("Ver Datos"):
        st.dataframe(df_view[df_view['INDICADOR']==kpi_sel][['INDICADOR']+MESES].style.format({m: "{:.1%}" for m in MESES}, na_rep=""))
