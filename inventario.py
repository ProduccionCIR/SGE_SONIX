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
            
            # Asegurar tipos de datos para cálculos
            df['CANTIDAD'] = pd.to_numeric(df['CANTIDAD'], errors='coerce').fillna(0)
            df['COSTO_UNIT'] = pd.to_numeric(df['COSTO_UNIT'], errors='coerce').fillna(0)
            df['TOTAL'] = df['CANTIDAD'] * df['COSTO_UNIT']

        tab1, tab2, tab3 = st.tabs(["📋 Existencias", "➕ Nuevo Producto", "🛠️ Editar Existente"])

        with tab1:
            self.render_existencias(df)
        with tab2:
            self.formulario_nuevo()
        with tab3:
            if not df.empty:
                self.seccion_edicion_busqueda(df)
            else:
                st.info("No hay productos registrados.")

    def render_existencias(self, df):
        st.subheader("Control de Stock")
        if df.empty:
            st.info("El inventario está vacío.")
            return
        
        c1, c2 = st.columns([1, 2])
        filtro = c1.selectbox("Filtrar por Stock:", ["Todos", "🔴 Crítico", "🟡 Atención", "🟢 Óptimo"])
        busqueda = c2.text_input("🔍 Buscar (Referencia o Descripción):", key="inv_search_main")
        
        df_v = df.copy()
        if "Crítico" in filtro: df_v = df_v[df_v['CANTIDAD'] <= 15]
        elif "Atención" in filtro: df_v = df_v[(df_v['CANTIDAD'] > 15) & (df_v['CANTIDAD'] <= 50)]
        elif "Óptimo" in filtro: df_v = df_v[df_v['CANTIDAD'] > 50]
        
        if busqueda:
            df_v = df_v[df_v['DESCRIPCION'].str.contains(busqueda, case=False, na=False) | 
                        df_v['REFERENCIA'].str.contains(busqueda, case=False, na=False)]
        
        cols_mostrar = ['ID', 'REFERENCIA', 'MARCA', 'DESCRIPCION', 'TIPO', 'UBICACION', 'CANTIDAD', 'COSTO_UNIT', 'TOTAL']
        st.dataframe(df_v[cols_mostrar].style.apply(self.aplicar_estilo_semaforo, axis=1), use_container_width=True, hide_index=True)

    def seccion_edicion_busqueda(self, df):
        st.subheader("Edición de Artículos")
        opciones = {f"REF: {r['REFERENCIA']} | {r['DESCRIPCION']} (ID: {r['ID']})": r['ID'] for _, r in df.iterrows()}
        seleccion = st.selectbox("Seleccione producto para modificar:", ["-- Seleccione --"] + list(opciones.keys()))

        if seleccion != "-- Seleccione --":
            id_sel = opciones[seleccion]
            item = df[df['ID'] == id_sel].iloc[0]

            with st.form("form_edit_full"):
                st.info(f"Modificando ID: {id_sel}")
                c1, c2 = st.columns(2)
                n_ref = c1.text_input("Referencia", value=str(item.get('REFERENCIA', '')))
                n_marca = c2.text_input("Marca", value=str(item.get('MARCA', '')))
                
                n_desc = st.text_input("Descripción", value=str(item.get('DESCRIPCION', '')))
                
                c3, c4 = st.columns(2)
                n_tipo = c3.text_input("Tipo", value=str(item.get('TIPO', '')))
                n_ubic = c4.text_input("Ubicación", value=str(item.get('UBICACION', '')))
                
                c5, c6 = st.columns(2)
                n_cant = c5.number_input("Cantidad", value=float(item.get('CANTIDAD', 0)))
                n_costo = c6.number_input("Costo Unitario", value=float(item.get('COSTO_UNIT', 0)))

                if st.form_submit_button("💾 Actualizar Producto"):
                    self.db.table("productos").update({
                        "REFERENCIA": n_ref.upper(),
                        "MARCA": n_marca.upper(),
                        "DESCRIPCION": n_desc.upper(),
                        "TIPO": n_tipo.upper(),
                        "UBICACION": n_ubic.upper(),
                        "CANTIDAD": n_cant,
                        "COSTO_UNIT": n_costo,
                        "TOTAL": n_cant * n_costo
                    }).eq("ID", id_sel).execute()
                    
                    self.registrar_evento("ACTUALIZACIÓN", f"REF {n_ref} ID {id_sel}")
                    st.success("✅ Cambios guardados.")
                    st.rerun()

    def formulario_nuevo(self):
        with st.form("form_nuevo_full", clear_on_submit=True):
            st.subheader("➕ Registro de Producto")
            c1, c2 = st.columns(2)
            f_ref = c1.text_input("Referencia *")
            f_marca = c2.text_input("Marca")
            
            f_desc = st.text_input("Descripción *")
            
            c3, c4 = st.columns(2)
            f_tipo = c3.text_input("Tipo (Ej: Repuesto, Herramienta)")
            f_ubic = c4.text_input("Ubicación en Bodega")
            
            c5, c6 = st.columns(2)
            f_cant = c5.number_input("Cantidad Inicial", min_value=0.0, step=1.0)
            f_costo = c6.number_input("Costo Unitario ($)", min_value=0.0)

            if st.form_submit_button("🚀 Guardar en Base de Datos"):
                if f_ref and f_desc:
                    nuevo_prod = {
                        "REFERENCIA": f_ref.upper(),
                        "MARCA": f_marca.upper(),
                        "DESCRIPCION": f_desc.upper(),
                        "TIPO": f_tipo.upper(),
                        "UBICACION": f_ubic.upper(),
                        "CANTIDAD": f_cant,
                        "COSTO_UNIT": f_costo,
                        "TOTAL": f_cant * f_costo
                    }
                    self.db.table("productos").insert(nuevo_prod).execute()
                    self.registrar_evento("CREACIÓN", f"Nuevo REF: {f_ref}")
                    st.success("✅ Producto registrado exitosamente.")
                    st.rerun()
                else:
                    st.error("❌ Referencia y Descripción son obligatorios.")
