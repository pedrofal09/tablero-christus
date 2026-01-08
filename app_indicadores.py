import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
DB_NAME = "Christus_DB_Master.db"

# --- CONSTANTES DEL NEGOCIO (Listas desplegables) ---
LISTA_ANIOS = [2025, 2026, 2027]
LISTA_MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

ROLES_USUARIOS = ["Admin", "Ceo", "Admin Delegado", "Lider"]
AREAS_ACCESO = ["Todas", "Facturación", "Cuentas Medicas", "Admisiones", "Autorizaciones", "Cartera"]

# Diccionario de tablas operativas
OPCIONES_OPERATIVAS = {
    "Admisiones": "ope_admisiones",
    "Facturación": "ope_facturacion",
    "Autorizaciones": "ope_autorizaciones",
    "Radicación": "ope_radicacion",
    "Cuentas Médicas": "ope_cuentas_medicas",
    "Cartera": "ope_cartera",
    "Provisión": "ope_provision"  # Nueva categoría agregada
}

# --- FUNCIONES DE BASE DE DATOS ---

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # --- BLOQUE DE AUTO-REPARACIÓN (Solución al error "no such column") ---
    try:
        # 1. Verificar qué columnas tiene la tabla 'usuarios' actualmente
        c.execute("PRAGMA table_info(usuarios)")
        columnas_existentes = [row[1] for row in c.fetchall()]
        
        # Si la tabla existe (hay columnas) pero NO tiene 'contrasena'
        if columnas_existentes and 'contrasena' not in columnas_existentes:
            st.toast("🔧 Reparando estructura de base de datos...", icon="🛠️")
            
            # Caso A: Existe 'password' (versión vieja), la renombramos
            if 'password' in columnas_existentes:
                try:
                    c.execute("ALTER TABLE usuarios RENAME COLUMN password TO contrasena")
                    st.toast("✅ Columna 'password' renombrada a 'contrasena'", icon="✅")
                except:
                    # Si falla renombrar (SQLite muy viejo), agregamos la nueva
                    c.execute("ALTER TABLE usuarios ADD COLUMN contrasena TEXT DEFAULT '1234'")
            
            # Caso B: No existe ni password ni contrasena, agregamos la columna
            else:
                c.execute("ALTER TABLE usuarios ADD COLUMN contrasena TEXT DEFAULT '1234'")
                st.toast("✅ Columna 'contrasena' agregada.", icon="✅")
            
            conn.commit()
            
    except Exception as e:
        # Si ocurre un error aquí (ej. la tabla no existe aún), no pasa nada, 
        # se creará en el paso siguiente.
        pass

    # 1. CATEGORÍA: DATOS DE USUARIOS
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            contrasena TEXT NOT NULL,
            rol TEXT NOT NULL,
            area_acceso TEXT NOT NULL,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. CATEGORÍA: BASE DE INDICADORES
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

# --- FUNCIONES DE LÓGICA ---

def crear_usuario(usuario, contrasena, rol, area):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO usuarios (usuario, contrasena, rol, area_acceso) VALUES (?, ?, ?, ?)",
            (usuario, contrasena, rol, area)
        )
        conn.commit()
        return True, "Usuario creado exitosamente."
    except sqlite3.IntegrityError:
        return False, "El nombre de usuario ya existe."
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        conn.close()

def cargar_dataframe(df, nombre_tabla, modo='append'):
    conn = get_connection()
    try:
        # Limpieza: Convertir nombres de columnas a string
        df.columns = df.columns.astype(str)
        # Guardar en SQL
        df.to_sql(nombre_tabla, conn, if_exists=modo, index=False)
        return True, f"✅ Carga Exitosa: {len(df)} registros procesados."
    except Exception as e:
        return False, f"❌ Error: {e}"
    finally:
        conn.close()

def leer_tabla(nombre_tabla):
    conn = get_connection()
    try:
        df = pd.read_sql(f"SELECT * FROM {nombre_tabla}", conn)
    except:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

# --- INTERFAZ DE USUARIO ---

def main():
    st.set_page_config(page_title="Christus Dashboard Manager V2", page_icon="🏥", layout="wide")
    
    # Inicialización con Auto-Reparación
    init_db()

    st.title("🏥 Sistema de Gestión de Datos")
    st.markdown("Plataforma centralizada para Usuarios, Indicadores y Operaciones.")

    # MENÚ PRINCIPAL
    categoria = st.sidebar.radio(
        "📌 SELECCIONA LA CATEGORÍA:",
        ["1. Datos de Usuarios", "2. Base de Indicadores", "3. Tablero Operativo"]
    )

    st.markdown("---")

    # =========================================================
    # 1. CATEGORÍA: DATOS DE USUARIOS
    # =========================================================
    if categoria == "1. Datos de Usuarios":
        st.header("👤 Gestión de Usuarios y Accesos")

        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("Nuevo Usuario")
            with st.form("form_usuarios", clear_on_submit=True):
                u_user = st.text_input("Usuario")
                u_pass = st.text_input("Contraseña", type="password")

                # Listas actualizadas según requerimiento
                u_rol = st.selectbox("Rol Asignado", ROLES_USUARIOS)
                u_area = st.selectbox("Área de Acceso", AREAS_ACCESO)

                if st.form_submit_button("Guardar"):
                    if u_user and u_pass:
                        exito, msg = crear_usuario(u_user, u_pass, u_rol, u_area)
                        if exito: st.success(msg)
                        else: st.error(msg)
                    else:
                        st.warning("Usuario y contraseña son obligatorios.")

        with col2:
            st.subheader("Base de Usuarios")
            df_users = leer_tabla("usuarios")
            if not df_users.empty:
                # Mostrar contraseña oculta si existe la columna
                if 'contrasena' in df_users.columns:
                    df_users['contrasena'] = "****"
                elif 'password' in df_users.columns: # Soporte legacy visual
                    df_users['password'] = "****"
                
                st.dataframe(df_users, use_container_width=True)
            else:
                st.info("No hay usuarios registrados.")

    # =========================================================
    # 2. CATEGORÍA: BASE DE INDICADORES
    # =========================================================
    elif categoria == "2. Base de Indicadores":
        st.header("📊 Base de Indicadores")
        st.info("💡 Columnas esperadas: **ÁREA, RESPONSABLE, INDICADOR**")

        uploaded_kpi = st.file_uploader("Subir Excel/CSV de Indicadores", type=["csv", "xlsx"])

        if uploaded_kpi:
            if st.button("💾 Cargar Indicadores"):
                try:
                    if uploaded_kpi.name.endswith('.csv'): 
                        df = pd.read_csv(uploaded_kpi)
                    else: 
                        df = pd.read_excel(uploaded_kpi)

                    # Normalizamos columnas
                    df.columns = [c.upper() for c in df.columns]

                    ok, msg = cargar_dataframe(df, "catalogo_indicadores", modo="replace")
                    if ok: st.success(msg); st.rerun()
                    else: st.error(msg)
                except Exception as e:
                    st.error(f"Error procesando archivo: {e}")

        st.subheader("Catálogo Actual")
        df_kpi = leer_tabla("catalogo_indicadores")
        st.dataframe(df_kpi, use_container_width=True)

    # =========================================================
    # 3. CATEGORÍA: TABLERO OPERATIVO (Con control de Periodos)
    # =========================================================
    elif categoria == "3. Tablero Operativo":
        st.header("⚙️ Bases del Tablero Operativo")
        st.markdown("Gestión de bases operativas por periodo.")

        # Selector del proceso
        proceso = st.selectbox(
            "Selecciona el Proceso a Cargar/Consultar:",
            list(OPCIONES_OPERATIVAS.keys())
        )
        tabla_destino = OPCIONES_OPERATIVAS[proceso]

        # Ayuda visual de columnas esperadas
        msg_cols = ""
        if proceso == "Provisión":
            msg_cols = "Columnas Clave: Año, Mes, Aseguradora, Fecha Corte, Provisión Acostados, Provisión Egresados, Facturado sin Radicar, Glosas Pendientes..."
        elif proceso == "Admisiones":
            msg_cols = "Columnas Clave: AÑO, MES, Sede, Cantidad Actividades..."

        if msg_cols:
            st.info(f"ℹ️ {msg_cols}")

        # Sección de Carga
        with st.expander(f"📤 Cargar Datos para: {proceso}", expanded=True):

            # --- NUEVO: SELECTORES DE PERIODO ---
            st.markdown("##### 📅 Definir Periodo de la Información")
            c_anio, c_mes = st.columns(2)
            anio_sel = c_anio.selectbox("Año de Gestión", LISTA_ANIOS)
            mes_sel = c_mes.selectbox("Mes de Gestión", LISTA_MESES)

            st.markdown("---")
            uploaded_ope = st.file_uploader(f"Subir Archivo ({proceso})", type=["csv", "xlsx"])

            if uploaded_ope:
                col_mode, col_btn = st.columns([2, 1])
                with col_mode:
                    modo = st.radio("Método:", ["Agregar (Append)", "Reemplazar (Replace)"], horizontal=True)
                    modo_sql = 'append' if 'Append' in modo else 'replace'

                with col_btn:
                    st.write("")
                    if st.button(f"Procesar {proceso}"):
                        try:
                            if uploaded_ope.name.endswith('.csv'): df = pd.read_csv(uploaded_ope)
                            else: df = pd.read_excel(uploaded_ope)
                            
                            # --- ESTAMPADO DE FECHA Y PERIODO ---
                            df['periodo_anio'] = anio_sel
                            df['periodo_mes'] = mes_sel
                            df['fecha_carga_sistema'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                            ok, msg = cargar_dataframe(df, tabla_destino, modo=modo_sql)
                            if ok: st.success(msg); st.rerun()
                            else: st.error(msg)
                        except Exception as e:
                            st.error(f"Error: {e}")

        # Sección de Visualización
        st.subheader(f"Vista de Datos: {proceso}")
        df_ope = leer_tabla(tabla_destino)
        if not df_ope.empty:
            # Filtros simples
            if 'periodo_anio' in df_ope.columns:
                filtro_anio = st.multiselect("Filtrar por Año:", df_ope['periodo_anio'].unique(), default=df_ope['periodo_anio'].unique())
                if filtro_anio:
                    df_ope = df_ope[df_ope['periodo_anio'].isin(filtro_anio)]

            st.dataframe(df_ope, use_container_width=True)
            st.metric("Total Registros", len(df_ope))
        else:
            st.warning(f"La base de datos de {proceso} está vacía.")

if __name__ == "__main__":
    main()
