import streamlit as st
import pandas as pd
from datetime import datetime

class ModuloInventario:
    def __init__(self, db):
        self.db = db

def registrar_evento(self, accion, detalle):
    try:
        user_info = st.session_state.get('user_data', {})
        usuario = user_info.get('usuario', 'Admin_Inventario')
        log_entry = {
            "usuario": usuario,
            "accion": accion.upper(),
            "modulo": "INVENTARIO",
            "detalle": detalle
        }
        self.db.table("logs_sistema").insert(log_entry).execute()
    except Exception as e:
        print(f"Error en registro de log: {e}")

def aplicar_estilo_semaforo(self, row):
    try:
        valor = float(row.get('CANTIDAD', 0))
    except:
        valor = 0
    color = 'background-color: #ff4b4b; color: white;' if valor <= 15 else \
            'background-color: #f9d71c; color: black;' if valor <= 50 else \
            'background-color: #00c853; color: white;'
    estilos = []
    for col in row.index:
        estilos.append(color if col == 'CANTIDAD' else '')
    return estilos

def render(self):
    st.header("📦 Gestión de Inventario - SONIX LTD.")
    try:
        prods = self.db.table("productos").select("*").execute().data
        df = pd.DataFrame(prods) if prods else pd.DataFrame()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return

    if not df.empty:
        df = df.reset_index(drop=True)
        df.columns = [c.upper() for c in df.columns]
        df = df.loc[:, ~df.columns.duplicated()]
        mapeos = {'COSTO_UNIT': 'COSTO UNIT', 'UBICACION': 'UBICACIÓN'}
        df.rename(columns=mapeos, inplace=True)
        df['ID'] = pd.to_numeric(df.get('ID'), errors='coerce').fillna(0).astype(int)
        df['CANTIDAD'] = pd.to_numeric(df.get('CANTIDAD'), errors='coerce').fillna(0.0).astype(float)
        df['COSTO UNIT'] = pd.to_numeric(df.get('COSTO UNIT'), errors='coerce').fillna(0.0).astype(float)
        df['TOTAL'] = df['CANTIDAD'] * df['COSTO UNIT']

    tab1, tab2, tab3 = st.tabs(["📋 Existencias", "➕ Nuevo", "🛠️ Editar"])

    with tab1:
        self.render_existencias(df)
    with tab2:
        self.formulario_nuevo()
    with tab3:
        if not df.empty:
            self.seccion_edicion_busqueda(df)
        else:
            st.info("No hay productos.")

def render_existencias(self, df):
    st.subheader("Control de Stock")
    if df.empty:
        st.info("Inventario vacío.")
        return
    c1, c2 = st.columns([1, 2])
    filtro = c1.selectbox("Filtrar:", ["Todos", "🔴 Crítico", "🟡 Atención", "🟢 Óptimo"])
    busqueda = c2.text_input("🔍 Buscar:", key="inv_search_main")
    df_v = df.copy()
    if "Crítico" in filtro: df_v = df_v[df_v['CANTIDAD'] <= 15]
    elif "Atención" in filtro: df_v = df_v[(df_v['CANTIDAD'] > 15) & (df_v['CANTIDAD'] <= 50)]
    elif "Óptimo" in filtro: df_v = df_v[df_v['CANTIDAD'] > 50]
    if busqueda:
        df_v = df_v[df_v['DESCRIPCION'].str.contains(busqueda, case=False, na=False)]
    cols = [c for c in ['ID', 'REFERENCIA', 'MARCA', 'DESCRIPCION', 'UBICACIÓN', 'CANTIDAD', 'COSTO UNIT', 'TOTAL'] if c in df_v.columns]
    st.dataframe(df_v[cols].style.apply(self.aplicar_estilo_semaforo, axis=1), use_container_width=True, hide_index=True)

def seccion_edicion_busqueda(self, df):
    st.subheader("Edición")
    opciones = {f"ID: {r['ID']} | {r['DESCRIPCION']}": r['ID'] for _, r in df.iterrows()}
    seleccion = st.selectbox("Seleccione:", ["-- Seleccione --"] + list(opciones.keys()))
    if seleccion != "-- Seleccione --":
        id_sel = opciones[seleccion]
        item = df[df['ID'] == id_sel].iloc[0]
        with st.form("form_edit_final"):
            n_ref = st.text_input("Referencia", value=str(item.get('REFERENCIA', '')))
            n_desc = st.text_input("Descripción", value=str(item.get('DESCRIPCION', '')))
            c1, c2 = st.columns(2)
            n_cant = c1.number_input("Cantidad", value=float(item.get('CANTIDAD', 0)))
            n_costo = c2.number_input("Costo", value=float(item.get('COSTO UNIT', 0)))
            if st.form_submit_button("💾 Guardar"):
                self.db.table("productos").update({
                    "REFERENCIA": n_ref.upper(),
                    "DESCRIPCION": n_desc.upper(),
                    "CANTIDAD": n_cant,
                    "COSTO_UNIT": n_costo,
                    "TOTAL": n_cant * n_costo
                }).eq("ID", id_sel).execute()
                st.success("Actualizado")
                st.rerun()

def formulario_nuevo(self):
    with st.form("form_nuevo_final", clear_on_submit=True):
        f_ref = st.text_input("Referencia")
        f_desc = st.text_input("Descripción")
        c1, c2 = st.columns(2)
        f_cant = c1.number_input("Cantidad", min_value=0.0)
        f_costo = c2.number_input("Costo", min_value=0.0)
        if st.form_submit_button("🚀 Registrar"):
            if f_ref and f_desc:
                self.db.table("productos").insert({
                    "REFERENCIA": f_ref.upper(),
                    "DESCRIPCION": f_desc.upper(),
                    "CANTIDAD": f_cant,
                    "COSTO_UNIT": f_costo,
                    "TOTAL": f_cant * f_costo
                }).execute()
                st.success("Registrado")
                st.rerun()
