import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import time

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

# --- FUNCIONES DE CARGA Y AUTENTICACIÓN ---

def cargar_usuarios():
    """Carga o crea el archivo de usuarios"""
    if not os.path.exists(ARCHIVO_USUARIOS):
        # Crear usuario admin por defecto si no existe archivo
        df_users = pd.DataFrame([
            ['admin', 'admin123', 'ADMIN', 'TODAS'],
            ['ceo', 'ceo123', 'CEO', 'TODAS']
        ], columns=['USUARIO', 'PASSWORD', 'ROL', 'AREA_ACCESO'])
        df_users.to_csv(ARCHIVO_USUARIOS, index=False)
        return df_users
    return pd.read_csv(ARCHIVO_USUARIOS)

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
    cols = ['ÁREA', 'RESPONSABLE', 'INDICADOR', 'META_VALOR', 'LOGICA', 'META_TEXTO'] + MESES
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

# --- LOGIN ---
if st.session_state.user_info is None:
    st.title("🔐 Acceso al Tablero de Indicadores")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            st.markdown("### Iniciar Sesión")
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit_login = st.form_submit_button("Entrar")
            
            if submit_login:
                user = autenticar(username, password)
                if user is not None:
                    st.session_state.user_info = user
                    st.success(f"Bienvenido {user['USUARIO']}")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
    st.stop() # Detener ejecución si no está logueado

# --- APLICACIÓN PRINCIPAL (SOLO SI ESTÁ LOGUEADO) ---

user = st.session_state.user_info
rol = user['ROL']
area_acceso = user['AREA_ACCESO']

# Título y Botón de Salir
c1, c2 = st.columns([5,1])
with c1:
    st.title(f"🏥 Tablero Christus | Rol: {rol}")
with c2:
    if st.button("Cerrar Sesión"):
        st.session_state.user_info = None
        st.rerun()

st.markdown("---")

# Cargar datos
if 'df_datos' not in st.session_state:
    st.session_state.df_datos = cargar_datos()
df = st.session_state.df_datos

# --- DEFINICIÓN DE MENÚ SEGÚN ROL ---
opciones_menu = ["📊 Dashboard Gerencial"]

# Solo líderes y admin pueden ingresar datos
if rol in ['ADMIN', 'LIDER']:
    opciones_menu.append("📝 Ingreso de Resultados")

# Solo admin puede gestionar usuarios
if rol == 'ADMIN':
    opciones_menu.append("👥 Gestión de Usuarios")

# Sidebar
with st.sidebar:
    st.header(f"Hola, {user['USUARIO']}")
    st.info(f"Permisos: {area_acceso}")
    opcion = st.radio("Navegación:", opciones_menu)
    st.markdown("---")
    
    # Descarga solo para Admin y CEO (Opcional, se puede abrir a todos)
    if rol in ['ADMIN', 'CEO']:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Base de Datos", csv, "indicadores_backup.csv", "text/csv")

# --- VISTA: GESTIÓN DE USUARIOS (SOLO ADMIN) ---
if opcion == "👥 Gestión de Usuarios":
    st.header("Gestión de Usuarios y Permisos")
    
    df_users = cargar_usuarios()
    st.dataframe(df_users, hide_index=True)
    
    st.subheader("Crear Nuevo Usuario")
    with st.form("new_user"):
        c1, c2 = st.columns(2)
        new_user = c1.text_input("Nuevo Usuario")
        new_pass = c2.text_input("Contraseña")
        new_rol = c1.selectbox("Rol", ["LIDER", "CEO", "ADMIN"])
        
        # Opciones de área (incluye TODAS y las áreas del archivo de datos)
        areas_disponibles = ['TODAS'] + list(df['ÁREA'].unique())
        new_area = c2.selectbox("Área de Acceso", areas_disponibles)
        
        crear = st.form_submit_button("Crear Usuario")
        
        if crear:
            if new_user and new_pass:
                if new_user in df_users['USUARIO'].values:
                    st.error("El usuario ya existe.")
                else:
                    new_row = pd.DataFrame([[new_user, new_pass, new_rol, new_area]], columns=['USUARIO', 'PASSWORD', 'ROL', 'AREA_ACCESO'])
                    df_users = pd.concat([df_users, new_row], ignore_index=True)
                    guardar_usuarios(df_users)
                    st.success("Usuario creado exitosamente")
                    st.rerun()
            else:
                st.warning("Complete todos los campos")

# --- VISTA: INGRESO DE RESULTADOS ---
elif opcion == "📝 Ingreso de Resultados":
    st.header("Reporte Mensual")
    
    col1, col2 = st.columns(2)
    
    # Filtrar áreas según permisos
    areas_totales = df['ÁREA'].unique()
    if area_acceso != 'TODAS':
        # Solo mostrar el área asignada al usuario
        areas_permitidas = [a for a in areas_totales if a == area_acceso]
    else:
        areas_permitidas = areas_totales
        
    with col1:
        if len(areas_permitidas) > 0:
            area_sel = st.selectbox("Seleccione Área:", areas_permitidas)
        else:
            st.error("No tienes áreas asignadas. Contacta al administrador.")
            st.stop()
            
    with col2:
        mes_sel = st.selectbox("Seleccione Mes:", MESES)
    
    # Mostrar formulario solo si hay área seleccionada
    df_area = df[df['ÁREA'] == area_sel]
    
    with st.form("form_ingreso"):
        inputs = {}
        for idx, row in df_area.iterrows():
            val_actual = row[mes_sel] if pd.notna(row[mes_sel]) else 0.0
            val_actual_pct = val_actual * 100 
            
            st.markdown(f"**{row['INDICADOR']}**")
            st.caption(f"Meta: {row['META_TEXTO']}")
            inputs[idx] = st.number_input(f"Resultado %", value=float(val_actual_pct), step=0.1, key=idx)
            st.markdown("---")
            
        if st.form_submit_button("💾 Guardar"):
            for idx, valor in inputs.items():
                df.at[idx, mes_sel] = valor / 100 
            st.session_state.df_datos = df
            guardar_datos(df)
            st.success(f"Datos guardados para {area_sel}")

# --- VISTA: DASHBOARD ---
elif opcion == "📊 Dashboard Gerencial":
    st.header("Tablero de Mando")
    
    # Filtrar indicadores visibles según rol
    if area_acceso == 'TODAS':
        df_visible = df
    else:
        df_visible = df[df['ÁREA'] == area_acceso]
        
    lista_indicadores = df_visible['INDICADOR'].unique()
    
    if len(lista_indicadores) == 0:
        st.warning("No tienes indicadores asignados para visualizar.")
    else:
        indicador_sel = st.selectbox("🔍 Indicador:", lista_indicadores)
        
        # Lógica de visualización (igual al script anterior)
        fila = df[df['INDICADOR'] == indicador_sel].iloc[0]
        meta = fila['META_VALOR']
        logica = fila['LOGICA']
        
        datos_grafico = [fila[m] if pd.notna(fila[m]) else 0 for m in MESES]
        
        # Tarjetas
        ultimo_mes_con_dato = None
        ultimo_valor = 0
        for m in reversed(MESES):
            if pd.notna(fila[m]):
                ultimo_mes_con_dato = m
                ultimo_valor = fila[m]
                break
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Meta", fila['META_TEXTO'])
        
        delta_color = "normal" if logica == 'MAX' else "inverse"
        
        if ultimo_mes_con_dato:
            diff = ultimo_valor - meta
            c2.metric(f"Último ({ultimo_mes_con_dato})", f"{ultimo_valor*100:.2f}%", f"{diff*100:.2f}%", delta_color=delta_color)
        else:
            c2.metric("Último", "Sin Datos")
            
        c3.info(f"Responsable: {fila['RESPONSABLE']}")
        
        # Gráfico
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=MESES, y=[meta]*len(MESES), mode='lines', name='Meta', line=dict(color='red', dash='dash')))
        
        # Datos reales (sin ceros si es null)
        y_real = [v if v is not None else None for v in [fila[m] for m in MESES]]
        
        fig.add_trace(go.Scatter(x=MESES, y=y_real, mode='lines+markers+text', name='Real', line=dict(color='#0F1C3F'), text=[f"{v*100:.1f}%" if v else "" for v in y_real], textposition="top center"))
        
        fig.update_layout(title=f"Tendencia: {indicador_sel}", template="plotly_white", yaxis_tickformat='.0%')
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Ver Tabla Detallada"):
            st.dataframe(df[df['INDICADOR'] == indicador_sel][['INDICADOR']+MESES].style.format({m: "{:.2%}" for m in MESES}, na_rep=""))
