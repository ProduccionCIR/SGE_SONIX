import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

# --- CLASE HELPER PARA COMPATIBILIDAD Y LOGS ---
class SupabaseHelper:
    """Evita errores de AttributeError y centraliza la lógica de red."""
    def __init__(self, client):
        self.client = client

    def table(self, table_name):
        return self.client.table(table_name)

    def fetch(self, tabla, select="*"):
        """Trae datos de una tabla de forma segura."""
        try:
            res = self.client.table(tabla).select(select).execute()
            # Validamos que la respuesta contenga datos antes de retornar
            return res.data if hasattr(res, 'data') and res.data else []
        except Exception as e:
            st.error(f"Error en comunicación con la base de datos ({tabla}): {e}")
            return []

    def registrar_log(self, accion, modulo, detalle):
        """Registra auditoría en la tabla logs_sistema."""
        try:
            log_data = {
                "usuario": st.session_state.get('user_data', {}).get('usuario', 'Sistema'),
                "accion": accion,
                "modulo": modulo,
                "detalle": detalle
            }
            self.client.table("logs_sistema").insert(log_data).execute()
        except:
            pass # Evita que el sistema se detenga si falla el log

# --- CARGA DE VARIABLES Y CONEXIÓN CRÍTICA ---
# Cargamos .env si existe (local), Render usará las variables del panel automáticamente
if os.path.exists(".env"):
    load_dotenv()

# Limpieza profunda de strings para evitar errores de DNS (Errno -2)
SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").strip()
SUPABASE_KEY = (os.environ.get("SUPABASE_KEY") or "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ ERROR CRÍTICO: Las credenciales de Supabase no están configuradas en Render.")
    st.info("Ve a la pestaña 'Environment' en Render y agrega SUPABASE_URL y SUPABASE_KEY.")
    st.stop()

# Inicialización del cliente con captura de errores de red
try:
    raw_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase = SupabaseHelper(raw_client)
except Exception as e:
    st.error(f"❌ FALLO DE CONEXIÓN: No se pudo alcanzar el servidor de Supabase. Detalles: {e}")
    st.stop()

# --- IMPORTACIÓN DE MÓDULOS DE NEGOCIO ---
try:
    from inventario import ModuloInventario
    from cotizaciones import ModuloCotizaciones
    from ventas import ModuloVentas
    from clientes import ModuloClientes
    from contabilidad import ModuloContabilidad
    from configuracion import ModuloConfiguracion
except ImportError as e:
    st.error(f"❌ ERROR DE MÓDULOS: Falta un archivo de módulo o hay un error de sintaxis en: {e}")
    st.stop()

# --- CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(page_title="CIR PANAMÁ", layout="wide", page_icon="🤖")

# --- INICIALIZACIÓN DE SESSION STATE ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'rol' not in st.session_state:
    st.session_state.rol = None

# --- LÓGICA DE ACCESO (LOGIN) ---
if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center; color: #707070; font-weight: bold;'>🤖 CIR PANAMÁ</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #A0A0A0;'>Sistema de Gestión Empresarial</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            usuario_input_raw = st.text_input("Usuario")
            clave_input_raw = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Ingresar", use_container_width=True)
            
            if submit:
                try:
                    # Obtenemos todos los perfiles registrados
                    data = supabase.fetch("perfiles")
                    
                    # Normalización para evitar errores de mayúsculas o espacios
                    usuario_clean = usuario_input_raw.strip().lower()
                    clave_clean = clave_input_raw.strip()

                    # Búsqueda del usuario en la lista
                    user = next((u for u in data if str(u.get('usuario','')).lower() == usuario_clean 
                                 and str(u.get('clave','')) == clave_clean), None)

                    # Acceso de emergencia/soporte IT
                    if not user and usuario_clean == "temp" and clave_clean == "1234":
                        user = {"usuario": "Soporte IT", "rol": "master_it", "nombre_completo": "Administrador Temporal"}

                    if user:
                        st.session_state.autenticado = True
                        st.session_state.user_data = user
                        st.session_state.rol = user.get('rol', 'usuario')
                        
                        # Registro de auditoría
                        supabase.registrar_log("Login", "Acceso", f"Usuario {user.get('usuario')} ingresó al sistema")
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas. Verifique usuario y contraseña.")
                except Exception as e:
                    st.error(f"Error de acceso al validar credenciales: {e}")

# --- INTERFAZ PRINCIPAL DEL SISTEMA (POST-LOGIN) ---
else:
    with st.sidebar:
        st.markdown(f"<h2 style='color: #707070; font-weight: bold;'>🏗️ CIR PANAMÁ</h2>", unsafe_allow_html=True)
        st.write(f"Usuario: **{st.session_state.user_data.get('usuario')}**")
        st.write(f"Permisos: `{st.session_state.rol}`")
        st.divider()
        
        opciones = ["📦 Inventario", "📄 Cotizaciones", "🛒 Ventas", "👥 Clientes", "💰 Contabilidad"]
        
        # Control de acceso para configuración
        if st.session_state.rol in ["master_it", "administrador"]:
            opciones.append("⚙️ Configuración")
            
        choice = st.radio("Menú Principal", opciones)
        
        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            supabase.registrar_log("Logout", "Acceso", "Sesión cerrada por el usuario")
            st.session_state.clear()
            st.rerun()

    # --- ENRUTADOR DE MÓDULOS ---
    # Se inyecta la instancia 'supabase' (Helper) a cada clase de módulo
    try:
        if choice == "📦 Inventario":
            ModuloInventario(supabase).render()
        elif choice == "📄 Cotizaciones":
            ModuloCotizaciones(supabase).render()
        elif choice == "🛒 Ventas":
            ModuloVentas(supabase).render()
        elif choice == "👥 Clientes":
            ModuloClientes(supabase).render()
        elif choice == "💰 Contabilidad":
            ModuloContabilidad(supabase).render()
        elif choice == "⚙️ Configuración":
            ModuloConfiguracion(supabase).render()
    except Exception as e:
        st.error(f"Error al cargar el módulo {choice}: {e}")
        st.info("Contacte al soporte técnico de CIR Panamá.")