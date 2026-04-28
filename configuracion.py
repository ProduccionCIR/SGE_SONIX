import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

class ModuloConfiguracion:
    def __init__(self, db):
        self.db = db
        # Configuración de nombres de tablas en Supabase
        self.tabla_perfiles = "perfiles"
        self.tabla_inventario = "productos"
        self.tabla_logs = "logs_sistema" 
        self.roles_disponibles = ["usuario", "supervisor", "administrador", "master_it"]

    def registrar_log(self, accion, modulo, detalle):
        """Registra la actividad del usuario en la tabla de auditoría"""
        try:
            session_data = st.session_state.get('user_data', {})
            log_data = {
                "usuario": session_data.get('usuario', 'Sistema'),
                "accion": str(accion).upper(),
                "modulo": str(modulo).upper(),
                "detalle": str(detalle)
            }
            self.db.table(self.tabla_logs).insert(log_data).execute()
        except Exception as e:
            print(f"Error al registrar log: {e}")

    def render(self):
        # SEGURIDAD: Solo Master IT puede acceder a esta configuración
        user_info = st.session_state.get('user_data')
        if not user_info or user_info.get('rol') != "master_it":
            st.error("🚫 Acceso Denegado. Se requiere perfil Master IT para realizar cambios de sistema.")
            return

        st.markdown("<h2 style='color: #4A4A4A;'>⚙️ Panel de Control Master IT</h2>", unsafe_allow_html=True)
        
        tab_usuarios, tab_importacion, tab_logs, tab_sistema = st.tabs([
            "👥 Usuarios", 
            "📊 Carga Masiva", 
            "📜 Auditoría Global", 
            "🛡️ Sistema"
        ])

        # --- PESTAÑA 1: GESTIÓN DE USUARIOS ---
        with tab_usuarios:
            with st.expander("➕ Crear Nuevo Acceso"):
                with st.form("f_nuevo_usuario_master"):
                    c1, c2 = st.columns(2)
                    u = c1.text_input("Usuario (Login)").lower().strip()
                    p = c1.text_input("Contraseña", type="password")
                    n = c2.text_input("Nombre Completo")
                    car = c2.text_input("Cargo")
                    r = st.selectbox("Rol del Sistema", self.roles_disponibles)
                    
                    if st.form_submit_button("Registrar Usuario", use_container_width=True):
                        if u and p and n:
                            try:
                                self.db.table(self.tabla_perfiles).insert({
                                    "usuario": u, "clave": p, "nombre_completo": n, "cargo": car, "rol": r
                                }).execute()
                                self.registrar_log("CREACIÓN", "USUARIOS", f"Usuario creado: {u}")
                                st.success(f"Usuario {u} creado exitosamente.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al crear usuario: {e}")

            st.subheader("Usuarios Registrados")
            try:
                usuarios_db = self.db.table(self.tabla_perfiles).select("*").order("usuario").execute().data
                if usuarios_db:
                    for user in usuarios_db:
                        with st.container(border=True):
                            col_i, col_a = st.columns([4, 1])
                            col_i.write(f"👤 **{user.get('nombre_completo')}** | `{user.get('rol')}` | @{user.get('usuario')}")
                            if col_a.button("🗑️", key=f"del_{user.get('id')}"):
                                self.db.table(self.tabla_perfiles).delete().eq("id", user.get('id')).execute()
                                self.registrar_log("ELIMINACIÓN", "USUARIOS", f"Eliminado: {user.get('usuario')}")
                                st.rerun()
            except:
                st.info("Cargando lista de usuarios...")

        # --- PESTAÑA 2: CARGA MASIVA DE EXCEL ---
        with tab_importacion:
            st.subheader("Importación de Inventario")
            st.info("Formato de columnas esperado: REFERENCIA, MARCA, DESCRIPCION, TIPO, UBICACION, CANTIDAD, COSTO_UNIT")
            
            file = st.file_uploader("Subir archivo Excel (.xlsx)", type=["xlsx"])
            if file:
                try:
                    df_load = pd.read_excel(file)
                    # Normalizar nombres de columnas a MAYÚSCULAS
                    df_load.columns = [str(c).strip().upper() for c in df_load.columns]
                    
                    if 'REFERENCIA' not in df_load.columns:
                        st.error("❌ El archivo no contiene la columna obligatoria 'REFERENCIA'.")
                    else:
                        # Limpieza de Referencias y eliminación de duplicados en el mismo archivo
                        df_load['REFERENCIA'] = df_load['REFERENCIA'].astype(str).str.strip().str.upper()
                        df_load = df_load.drop_duplicates(subset=['REFERENCIA'], keep='last')
                        
                        st.success(f"✅ Archivo verificado: {len(df_load)} productos únicos detectados.")
                        st.dataframe(df_load.head(5), use_container_width=True)
                        
                        if st.button("🚀 Iniciar Carga Masiva", type="primary"):
                            # Funciones de limpieza para evitar errores de celdas vacías (NaN)
                            def limpiar_num(v):
                                try:
                                    if pd.isna(v) or v is None: return 0.0
                                    return float(v)
                                except: return 0.0

                            def limpiar_txt(v):
                                if pd.isna(v) or v is None: return ""
                                return str(v).strip()

                            # Procesamiento de cada fila para Supabase
                            lote_limpio = []
                            for _, r in df_load.iterrows():
                                cant = limpiar_num(r.get('CANTIDAD'))
                                costo = limpiar_num(r.get('COSTO_UNIT'))
                                
                                item = {
                                    "REFERENCIA": limpiar_txt(r.get('REFERENCIA')),
                                    "MARCA": limpiar_txt(r.get('MARCA')),
                                    "DESCRIPCION": limpiar_txt(r.get('DESCRIPCION')),
                                    "TIPO": limpiar_txt(r.get('TIPO')),
                                    "UBICACION": limpiar_txt(r.get('UBICACION')),
                                    "CANTIDAD": cant,
                                    "COSTO_UNIT": costo,
                                    "TOTAL": cant * costo
                                }
                                lote_limpio.append(item)
                            
                            if lote_limpio:
                                try:
                                    # El Upsert inserta nuevos o actualiza existentes usando REFERENCIA como llave
                                    self.db.table(self.tabla_inventario).upsert(lote_limpio, on_conflict='REFERENCIA').execute()
                                    self.registrar_log("IMPORTACIÓN", "INVENTARIO", f"Carga masiva: {len(lote_limpio)} registros")
                                    st.success(f"¡Proceso completado! {len(lote_limpio)} productos actualizados/insertados.")
                                    st.balloons()
                                    st.rerun()
                                except Exception as db_err:
                                    st.error(f"Error de base de datos (PGRST): {db_err}")
                except Exception as e:
                    st.error(f"Error al procesar el archivo Excel: {e}")

        # --- PESTAÑA 3: AUDITORÍA Y LOGS ---
        with tab_logs:
            st.subheader("Registro de Actividad del Sistema")
            try:
                logs_db = self.db.table(self.tabla_logs).select("*").order("id", desc=True).limit(150).execute().data
                if logs_db:
                    st.dataframe(pd.DataFrame(logs_db), use_container_width=True, hide_index=True)
                else:
                    st.info("No hay registros disponibles en el historial.")
            except:
                st.warning("No se pudo cargar el historial de logs.")

        # --- PESTAÑA 4: SISTEMA Y MANTENIMIENTO ---
        with tab_sistema:
            st.subheader("Acciones de Mantenimiento")
            
            # Exportar inventario a Excel
            if st.button("💾 Descargar Copia de Seguridad (Excel)"):
                data_inv = self.db.table(self.tabla_inventario).select("*").execute().data
                if data_inv:
                    df_exp = pd.DataFrame(data_inv)
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_exp.to_excel(writer, sheet_name='INVENTARIO_ACTUAL', index=False)
                    st.download_button("📥 Descargar Archivo .xlsx", output.getvalue(), "inventario_respaldo.xlsx", use_container_width=True)

            st.divider()
            st.error("Zona de Peligro (Acciones Irreversibles)")
            
            if st.button("🗑️ Borrar Todo el Inventario"):
                try:
                    # Borrado total mediante una condición siempre verdadera
                    self.db.table(self.tabla_inventario).delete().neq("REFERENCIA", "VACIO_SISTEMA_NULL").execute()
                    self.registrar_log("MANTENIMIENTO", "DB", "Vaciado completo de la tabla productos")
                    st.success("La base de datos de productos ha sido vaciada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo vaciar la tabla: {e}")