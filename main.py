import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

# --- CLASE HELPER PARA COMPATIBILIDAD Y LOGS ---
class SupabaseHelper:
    """Centraliza la comunicación con la base de datos y evita errores de DNS."""
    def __init__(self, client):
        self.client = client

    def table(self, table_name):
        return self.client.table(table_name)

    def fetch(self, tabla, select="*"):
        """Trae datos de una tabla de forma segura."""
        try:
            res = self.client.table(tabla).select(select).execute()
            return res.data if hasattr(res, 'data') and res.data else []
        except Exception as e:
            st.error(f"Error en comunicación con la base de datos ({tabla}): {e}")
            return []

    def registrar_log(self, accion, modulo, detalle):
        """Registra auditoría en la tabla logs_sistema."""
        try:
            user_info = st.session_state.get('user_data', {})
            log_data = {
                "usuario": user_info.get('usuario', 'Sistema'),
                "accion": str(accion).upper(),
                "modulo": str(modulo).upper(),
                "detalle": str(detalle)
            }
            self.client.table("logs_sistema").insert(log_data).execute()
        except:
            pass

# --- CARGA DE VARIABLES Y CONEXIÓN ---
if os.path.exists(".env"):
    load_dotenv()

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").strip()
SUPABASE_KEY = (os.environ.get("SUPABASE_KEY") or "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ ERROR CRÍTICO: Credenciales de Supabase no detectadas.")
    st.stop()

try:
    raw_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase = SupabaseHelper(raw_client)
except Exception as e:
    st.error(f"❌ FALLO DE CONEXIÓN: {e}")
    st.stop()

# --- IMPORTACIÓN DE MÓDULOS ---
try:
    from inventario import ModuloInventario
    from cotizaciones import ModuloCotizaciones
    from ventas import ModuloVentas
    from clientes import ModuloClientes
    from contabilidad import ModuloContabilidad
    from configuracion import ModuloConfiguracion
except ImportError as e:
    st.error(f"❌ ERROR DE MÓDULOS: {e}")
    st.stop()

# --- CONFIGURACIÓN INTERFAZ ---
st.set_page_config(page_title="CIR PANAMÁ OS", layout="wide", page_icon="🏗️")

# --- INICIALIZACIÓN DE SESSION STATE ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'rol' not in st.session_state:
    st.session_state.rol = None

# --- LÓGICA DE LOGIN ---
if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center;'>🏗️ CIR PANAMÁ OS</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            u_input = st.text_input("Usuario").lower().strip()
            p_input = st.text_input("Contraseña", type="password").strip()
            submit = st.form_submit_button("Ingresar", use_container_width=True)
            
            if submit:
                # 1. Acceso de emergencia
                if u_input == "temp" and p_input == "1234":
                    user = {"usuario": "soporte", "rol": "master_it", "nombre_completo": "Soporte IT"}
                else:
                    # 2. Consulta Directa a Supabase (Busca usuario Y clave)
                    res = raw_client.table("perfiles").select("*")\
                        .eq("usuario", u_input)\
                        .eq("clave", p_input).execute()
                    user = res.data[0] if res.data else None

                if user:
                    st.session_state.autenticado = True
                    st.session_state.user_data = user
                    st.session_state.rol = str(user.get('rol', 'usuario')).lower()
                    
                    supabase.registrar_log("LOGIN", "ACCESO", f"Usuario {u_input} entró")
                    st.success("Acceso concedido")
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas.")

# --- SISTEMA PRINCIPAL ---
else:
    with st.sidebar:
        st.header("🏗️ CIR PANAMÁ")
        st.write(f"👤 **{st.session_state.user_data.get('nombre_completo', 'Usuario')}**")
        st.caption(f"Rol: {st.session_state.rol.upper()}")
        st.divider()
        
        menu = ["📦 Inventario", "📄 Cotizaciones", "🛒 Ventas", "👥 Clientes", "💰 Contabilidad"]
        if st.session_state.rol in ["master_it", "administrador"]:
            menu.append("⚙️ Configuración")
            
        choice = st.radio("Navegación", menu)
        
        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # --- RENDERIZADO DE MÓDULOS ---
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
        st.error(f"Error en módulo {choice}: {e}")