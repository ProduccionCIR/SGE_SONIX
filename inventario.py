import streamlit as st
import pandas as pd
import io
from datetime import datetime

class ModuloInventario:
    def __init__(self, db):
        self.db = db

    def registrar_evento(self, accion, detalle):
        """Registra la actividad en la tabla central de auditoría de MasterIT."""
        try:
            usuario = st.session_state.get('usuario', 'Admin_Inventario')
            log_entry = {
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "modulo": "INVENTARIO",
                "usuario": usuario,
                "accion": accion,
                "detalle": detalle
            }
            self.db.client.table("logs").insert(log_entry).execute()
        except Exception as e:
            st.error(f"Error al sincronizar log con MasterIT: {e}")

    def aplicar_estilo_semaforo(self, row):
        """Lógica visual: Rojo (<=15), Amarillo (16-50), Verde (>50)"""
        try:
            valor = float(row.get('CANTIDAD', 0))
        except:
            valor = 0
            
        color = 'background-color: #ff4b4b; color: white;' if valor <= 15 else \
                'background-color: #f9d71c; color: black;' if valor <= 50 else \
                'background-color: #00c853; color: white;'
        
        estilos = []
        for col in row.index:
            if col == 'CANTIDAD': 
                estilos.append(color)
            else: 
                estilos.append('')
        return estilos

    def render(self):
        st.header("📦 Gestión de Inventario - DANA")
        
        # 1. Carga de datos
        prods = self.db.fetch("productos")
        df = pd.DataFrame(prods) if prods else pd.DataFrame()
        
        if not df.empty:
            df.columns = [c.upper() for c in df.columns]
            df['ID'] = pd.to_numeric(df['ID'], errors='coerce').fillna(0).astype(int)
            df['CANTIDAD'] = pd.to_numeric(df['CANTIDAD'], errors='coerce').fillna(0.0).astype(float)
            df['COSTO UNIT'] = pd.to_numeric(df['COSTO UNIT'], errors='coerce').fillna(0.0).astype(float)
            df['TOTAL'] = df['CANTIDAD'] * df['COSTO UNIT']

        tab1, tab2, tab3 = st.tabs([
            "📋 Existencias Actuales", 
            "➕ Nuevo Producto", 
            "🛠️ Modificar / Actualizar"
        ])

        with tab1:
            self.render_existencias(df)

        with tab2:
            self.formulario_nuevo()

        with tab3:
            if not df.empty:
                self.seccion_edicion_busqueda(df)
            else:
                st.info("No hay productos registrados para editar.")

    def render_existencias(self, df):
        st.subheader("Control de Stock y Valorización")
        if df.empty:
            st.info("El inventario está vacío.")
            return

        c1, c2 = st.columns([1, 2])
        filtro_stock = c1.selectbox("Filtrar Stock:", ["Todos", "🔴 Crítico", "🟡 Atención", "🟢 Óptimo"])
        busqueda = c2.text_input("🔍 Buscar por descripción, marca o referencia:", key="inv_search_main")
        
        df_v = df.copy()
        if "Crítico" in filtro_stock: df_v = df_v[df_v['CANTIDAD'] <= 15]
        elif "Atención" in filtro_stock: df_v = df_v[(df_v['CANTIDAD'] > 15) & (df_v['CANTIDAD'] <= 50)]
        elif "Óptimo" in filtro_stock: df_v = df_v[df_v['CANTIDAD'] > 50]
        
        if busqueda:
            df_v = df_v[
                df_v['DESCRIPCION'].str.contains(busqueda, case=False, na=False) | 
                df_v['MARCA'].str.contains(busqueda, case=False, na=False) |
                df_v['REFERENCIA'].str.contains(busqueda, case=False, na=False)
            ]
        
        cols_mostrar = ['ID', 'REFERENCIA', 'MARCA', 'TIPO', 'DESCRIPCION', 'UBICACIÓN', 'CANTIDAD', 'COSTO UNIT', 'TOTAL', 'EMPAQUE']
        st.dataframe(
            df_v[cols_mostrar].style.apply(self.aplicar_estilo_semaforo, axis=1), 
            use_container_width=True, hide_index=True
        )

    def seccion_edicion_busqueda(self, df):
        st.subheader("Edición de Artículos")
        opciones = {f"ID: {r['ID']} | {r['DESCRIPCION']}": r['ID'] for _, r in df.iterrows()}
        seleccion = st.selectbox("Seleccione artículo para editar:", ["-- Seleccione --"] + list(opciones.keys()))

        if seleccion != "-- Seleccione --":
            id_sel = opciones[seleccion]
            item = df[df['ID'] == id_sel].iloc[0]

            with st.form("form_edit_full_v2"):
                st.info(f"Modificando Registro ID: {id_sel}")
                c1, c2, c3 = st.columns(3)
                n_ref = c1.text_input("Referencia", value=str(item.get('REFERENCIA', '')))
                n_marca = c2.text_input("Marca", value=str(item.get('MARCA', '')))
                n_tipo = c3.text_input("Tipo", value=str(item.get('TIPO', '')))
                
                n_desc = st.text_input("Descripción", value=str(item.get('DESCRIPCION', '')))
                
                c4, c5, c6 = st.columns(3)
                n_ubica = c4.text_input("Ubicación", value=str(item.get('UBICACIÓN', '')))
                n_cant = c5.number_input("Cantidad", value=float(item.get('CANTIDAD', 0)))
                n_costo = c6.number_input("Costo Unitario ($)", value=float(item.get('COSTO UNIT', 0)), format="%.2f")
                
                if st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True):
                    self.db.client.table("productos").update({
                        "REFERENCIA": n_ref, "MARCA": n_marca, "TIPO": n_tipo,
                        "DESCRIPCION": n_desc, "UBICACIÓN": n_ubica, "CANTIDAD": n_cant,
                        "COSTO UNIT": n_costo, "TOTAL": n_cant * n_costo
                    }).eq("ID", id_sel).execute()
                    
                    self.registrar_evento("ACTUALIZACIÓN", f"ID {id_sel}: {n_desc}")
                    st.success("✅ Cambios guardados.")
                    st.rerun()

    def formulario_nuevo(self):
        """Formulario de registro: EL ID SE OMITE PORQUE ES AUTO-GENERADO POR SUPABASE"""
        with st.form("form_nuevo_identity", clear_on_submit=True):
            st.subheader("➕ Registro de Nuevo Producto")
            st.caption("El ID será asignado automáticamente por el sistema.")
            
            c1, c2 = st.columns(2)
            ref = c1.text_input("Referencia")
            marca = c2.text_input("Marca")
            
            desc = st.text_input("Descripción Completa")
            
            c3, c4, c5 = st.columns(3)
            tipo = c3.text_input("Tipo")
            ubica = c4.text_input("Ubicación en Bodega")
            um = c5.text_input("U/M (Unidad, Par, Caja)")
            
            c6, c7, c8 = st.columns(3)
            cant = c6.number_input("Cantidad Inicial", min_value=0.0)
            costo = c7.number_input("Costo Unitario ($)", min_value=0.0, format="%.2f")
            emp = c8.text_input("Detalle Empaque")
            
            if st.form_submit_button("🚀 Registrar en Inventario", use_container_width=True):
                if not desc or not marca:
                    st.error("❌ La Marca y la Descripción son obligatorias.")
                else:
                    # IMPORTANTE: No incluimos 'ID' en el diccionario para evitar el error 428C9
                    nuevo_producto = {
                        "REFERENCIA": ref, "MARCA": marca, "DESCRIPCION": desc,
                        "TIPO": tipo, "UBICACIÓN": ubica, "CANTIDAD": cant, 
                        "COSTO UNIT": costo, "TOTAL": cant * costo, 
                        "EMPAQUE": emp, "U/M": um
                    }
                    self.db.client.table("productos").insert(nuevo_producto).execute()
                    
                    self.registrar_evento("CREACIÓN", f"Nuevo producto registrado: {desc}")
                    st.success("✅ Producto registrado exitosamente.")
                    st.rerun()