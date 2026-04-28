import streamlit as st
import pandas as pd

class ModuloAuth:
    def __init__(self, db):
        self.db = db

    def login(self):
        # Centrar el logo o título
        st.markdown("<h1 style='text-align: center;'>🛡️ CIR PANAMÁ OS</h1>", unsafe_allow_html=True)
        
        with st.container(border=True):
            # Usamos .lower() y .strip() para evitar errores de dedo
            u = st.text_input("Usuario").lower().strip()
            p = st.text_input("Contraseña", type="password").strip()
            
            if st.button("Ingresar", use_container_width=True):
                if not u or not p:
                    st.warning("Por favor, complete todos los campos.")
                    return

                try:
                    # Consulta directa a Supabase buscando coincidencia de usuario Y clave
                    # Esto es mucho más seguro que bajar toda la tabla
                    res = self.db.table("perfiles")\
                        .select("*")\
                        .eq("usuario", u)\
                        .eq("clave", p)\
                        .execute()

                    if res.data and len(res.data) > 0:
                        user_data = res.data[0]
                        
                        # Guardamos todo el objeto del usuario en el estado
                        st.session_state.auth = True
                        st.session_state.user = u
                        st.session_state.user_data = user_data # Para usar en configuracion.py
                        st.session_state.rol = str(user_data.get('rol', 'usuario')).lower()
                        
                        st.success(f"Bienvenido {user_data.get('nombre_completo', u)}")
                        st.rerun()
                    else:
                        st.error("🚫 Credenciales incorrectas. Verifique usuario y contraseña.")
                        
                except Exception as e:
                    st.error(f"Error de conexión: {e}")

    def logout(self):
        st.session_state.auth = False
        st.session_state.user = None
        st.session_state.user_data = None
        st.session_state.rol = None
        st.rerun()