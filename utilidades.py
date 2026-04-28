# utilidades.py (Nuevo concepto para permisos)
import streamlit as st

def check_permiso(accion):
    rol = st.session_state.rol
    if rol == "master it": return True
    if accion == "eliminar" and rol == "administrador": return True
    if accion == "modificar" and rol in ["administrador", "supervisor"]: return True
    if accion == "ingresar": return True # Todos pueden ingresar
    return False