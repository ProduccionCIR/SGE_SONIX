import streamlit as st
import pandas as pd
from datetime import datetime

class ModuloInventario:
    def __init__(self, db):
        self.db = db

    def registrar_evento(self, accion, detalle):
        """Registra la actividad en la tabla de auditoría central."""
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
        st.header("📦 Gestión de Inventario - SONIX LTD.")
        
        # 1. CARGA Y LIMPIEZA CRÍTICA DE DATOS
        try:
            prods = self.db.table("productos").select("*").execute().data
            df = pd.DataFrame(prods) if prods else pd.DataFrame()
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            return
        
        if not df.empty:
            # --- PROTECCIÓN CONTRA ERROR DE STYLER ---
            # Resetear índice para asegurar que sea único (0, 1, 2...)
            df = df.reset_index(drop=True)
            
            # Convertir todas las columnas a MAYÚSCULAS
            df.columns = [c.upper() for c in df.columns]
            
            # Eliminar columnas duplicadas (ej: si existía 'cantidad' y 'CANTIDAD')
            df = df.loc[:, ~df.columns.duplicated()]
            
            # Mapeo de nombres de DB a nombres de visualización
            mapeos = {
                'COSTO_UNIT': 'COSTO UNIT',
                'UBICACION': 'UBICACIÓN'
            }
            df.rename(columns=mapeos, inplace=True)

            # Conversión de tipos de datos segura
            df['id'] = pd.to_numeric(df.get('id'), errors='coerce').fillna(0).astype(int)
            df['CANTIDAD'] = pd.to_numeric(df.get('CANTIDAD'), errors='coerce').fillna(0.0).astype(float)
            df['COSTO UNIT'] = pd.to_numeric(df.get('COSTO UNIT'), errors='coerce').fillna(0.0).astype(float)
            
            # Calcular TOTAL dinámicamente
            df['TOTAL'] = df['CANTIDAD'] * df['COSTO UNIT']

        # 2. TABS DE NAVEGACIÓN
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
                st.info("No hay productos registrados.")

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
        
        # Definir columnas a mostrar (solo las que existan realmente)
        cols_finales = [c for c in ['ID', 'REFERENCIA', 'MARCA', 'TIPO', 'DESCRIPCION', 'UBICACIÓN', 'CANTIDAD', 'COSTO UNIT', 'TOTAL'] if c in df_v.columns]
        
        st.dataframe(
            df_v[cols_finales].style.apply(self.aplicar_estilo_semaforo, axis=1), 
            use_container_width=True, hide_index=True
        )

    def seccion_edicion_busqueda(self, df):
        st.subheader("Edición de Artículos")
        # Diccionario para búsqueda rápida por ID
        opciones = {f"ID: {r['ID']} | {r['REFERENCIA']} - {r['MARCA']}": r['ID'] for _, r in df.iterrows()}
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
                    # Guardar con nombres estandarizados de Supabase
                    self.db.table("productos").update({
                        "REFERENCIA": n_ref.strip().upper(), 
                        "MARCA": n_marca.strip().upper(), 
                        "TIPO": n_tipo.strip().upper(),
                        "DESCRIPCION": n_desc.strip().upper(), 
                        "UBICACION": n_ubica.strip().upper(),
                        "CANTIDAD": n_cant,
                        "COSTO_UNIT": n_costo,
                        "TOTAL": n_cant * n_costo
                    }).eq("ID", id_sel).execute()
                    
                    self.registrar_evento("ACTUALIZACIÓN", f"ID {id_sel}: {n_desc}")
                    st.success("✅ Cambios aplicados.")
                    st.rerun()

    def formulario_nuevo(self):
        with st.form("form_nuevo_inv", clear_on_submit=True):
            st.subheader("➕ Registro de Nuevo Producto")
            
            c1, c2 = st.columns(2)
            ref = c1.text_input("Referencia")
            marca = c2.text_input("Marca")
            
            desc = st.text_input("Descripción Completa")
            
            c3, c4, c5 = st.columns(3)
            tipo = c3.text_input("Tipo")
            ubica = c4.text_input("Ubicación en Bodega")
            um = c5.text_input("U/M (Unidad, Par, Caja)")
            
            c6, c7 = st.columns(2)
            cant = c6.number_input("Cantidad Inicial", min_value=0.0)
            costo = c7.number_input("Costo Unitario ($)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("🚀 Registrar en Inventario", use_container_width=True):
                if not desc or not ref:
                    st.error("❌ Los campos Referencia y Descripción son obligatorios.")
                else:
                    nuevo = {
                        "REFERENCIA": ref.strip().upper(), 
                        "MARCA": marca.strip().upper(), 
                        "DESCRIPCION": desc.strip().upper(),
                        "TIPO": tipo.strip().upper(), 
                        "UBICACION": ubica.strip().upper(), 
                        "CANTIDAD": cant, 
                        "COSTO_UNIT": costo, 
                        "TOTAL": cant * costo
                    }
                    try:
                        self.db.table("productos").insert(nuevo).execute()
                        self.registrar_evento("CREACIÓN", f"Nuevo: {ref}")
                        st.success("✅ Producto registrado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
