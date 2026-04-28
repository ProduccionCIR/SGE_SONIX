import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

class ModuloConfiguracion:
    def __init__(self, db):
        self.db = db
        # Sincronización exacta con tus tablas de Supabase
        self.tabla_perfiles = "perfiles"
        self.tabla_inventario = "productos"
        self.tabla_logs = "logs_sistema" 
        self.roles_disponibles = ["usuario", "supervisor", "administrador", "master_it"]

    def registrar_log(self, accion, modulo, detalle):
        """
        Registra actividad de forma segura. 
        Nota: 'id' y 'fecha' son automáticos en la DB.
        """
        try:
            session_data = st.session_state.get('user_data')
            if session_data is None:
                user_info = {"usuario": "Sistema", "rol": "N/A"}
            else:
                user_info = session_data

            log_data = {
                "usuario": user_info.get('usuario', 'Sistema'),
                "rol": user_info.get('rol', 'N/A'),
                "accion": str(accion).upper(),
                "modulo": str(modulo).upper(),
                "detalle": str(detalle)
            }
            # No enviamos 'fecha' ni 'id' porque la DB los genera (now() y nextval)
            self.db.table(self.tabla_logs).insert(log_data).execute()
        except Exception as e:
            print(f"Error de Log Interno: {e}")

    def render(self):
        # SEGURIDAD: Validación Master IT
        user_info = st.session_state.get('user_data')
        if not user_info or user_info.get('rol') != "master_it":
            st.error("🚫 Acceso Denegado. Se requiere perfil Master IT.")
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
                                st.success(f"Usuario {u} creado.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

            st.subheader("Usuarios en Base de Datos")
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

        # --- PESTAÑA 2: CARGA MASIVA MULTITABLA ---
        with tab_importacion:
            st.subheader("Importación de Datos (Excel/CSV)")
            tabla_destino = st.selectbox("Seleccione Tabla de Destino:", [self.tabla_inventario, self.tabla_perfiles])
            
            file = st.file_uploader("Subir archivo", type=["xlsx", "csv"])
            if file:
                df_load = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
                df_load.columns = [str(c).strip().upper() for c in df_load.columns]
                st.info(f"Registros detectados: {len(df_load)}")
                st.dataframe(df_load.head(3), use_container_width=True)
                
                if st.button("🚀 Ejecutar Inserción Masiva", type="primary"):
                    try:
                        df_final = df_load.replace({np.nan: None, pd.NA: None, "": None})
                        records = df_final.to_dict(orient='records')
                        
                        lote_limpio = []
                        for r in records:
                            if 'ID' in r: del r['ID'] # Dejamos que Supabase asigne el ID
                            item = {k: (int(v) if isinstance(v, float) and v.is_integer() else v) for k, v in r.items() if k}
                            lote_limpio.append(item)
                        
                        if lote_limpio:
                            self.db.table(tabla_destino).insert(lote_limpio).execute()
                            self.registrar_log("IMPORTACIÓN", tabla_destino, f"Carga de {len(lote_limpio)} filas")
                            st.success(f"Carga finalizada en {tabla_destino}.")
                            st.balloons()
                    except Exception as e:
                        st.error(f"Error en carga masiva: {e}")

        # --- PESTAÑA 3: AUDITORÍA (LOGS) ---
        with tab_logs:
            st.subheader("Historial de logs_sistema")
            c_f1, c_f2 = st.columns(2)
            f_mod = c_f1.text_input("Filtrar Módulo")
            f_usr = c_f2.text_input("Filtrar Usuario")

            raw_logs = self.db.table(self.tabla_logs).select("*").order("fecha", desc=True).limit(200).execute().data
            if raw_logs:
                df_logs = pd.DataFrame(raw_logs)
                # Filtros dinámicos
                if f_mod: df_logs = df_logs[df_logs['modulo'].str.contains(f_mod.upper(), na=False)]
                if f_usr: df_logs = df_logs[df_logs['usuario'].str.contains(f_usr.lower(), na=False)]
                
                # Formateo de fecha para visualización
                if 'fecha' in df_logs.columns:
                    df_logs['fecha'] = pd.to_datetime(df_logs['fecha']).dt.strftime('%d/%m/%Y %H:%M:%S')
                
                st.dataframe(
                    df_logs[['fecha', 'usuario', 'modulo', 'accion', 'detalle']], 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info("No hay registros en la tabla logs_sistema.")

        # --- PESTAÑA 4: MANTENIMIENTO ---
        with tab_sistema:
            st.subheader("Acciones de Base de Datos")
            with st.container(border=True):
                st.error("Zona Crítica: Vaciar Tablas")
                confirm = st.checkbox("Confirmo que deseo eliminar todos los datos de la tabla seleccionada")
                t_clear = st.radio("Tabla a limpiar:", [self.tabla_inventario, self.tabla_logs], horizontal=True)
                
                if st.button(f"🗑️ Vaciar {t_clear.upper()}", disabled=not confirm, type="primary"):
                    self.db.table(t_clear).delete().neq("id", -1).execute()
                    self.registrar_log("MANTENIMIENTO", "DB", f"Vaciado de {t_clear}")
                    st.success(f"Tabla {t_clear} vaciada.")
                    st.rerun()

            if st.button("💾 Exportar Respaldo de Inventario"):
                data_bkp = self.db.table(self.tabla_inventario).select("*").execute().data
                if data_bkp:
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                        pd.DataFrame(data_bkp).to_excel(writer, index=False)
                    st.download_button("📥 Descargar Excel", out.getvalue(), "backup_masterit.xlsx", use_container_width=True)