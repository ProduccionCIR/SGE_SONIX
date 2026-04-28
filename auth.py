import streamlit as st
import pandas as pd

class ModuloAuth:
    def __init__(self, db):
        self.db = db

    def login(self):
        st.title("🛡️ CIR PANAMÁ OS")
        with st.container(border=True):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Ingresar", use_container_width=True):
                df = pd.DataFrame(self.db.fetch("perfiles"))
                user_match = df[df['usuario'] == u] if not df.empty else pd.DataFrame()
                if not user_match.empty:
                    st.session_state.auth = True
                    st.session_state.user = u
                    st.session_state.rol = str(user_match.iloc[0]['rol']).lower()
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")