import streamlit as st
import pandas as pd

class ModuloAdmin:
    def __init__(self, db):
        self.db = db

    def render(self):
        st.header("🛡️ Panel de Control Master IT")
        
        # Pestañas para organizar la administración
        tab1, tab2 = st.tabs(["👤 Gestión de Usuarios", "📜 Auditoría de Logs"])

        with tab1:
            st.subheader("Agregar o Modificar Personal")
            
            # Formulario con diseño limpio
            with st.container(border=True):
                with st.form("registro_usuario", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    
                    id_p = c1.number_input("ID del Perfil (0 para nuevo usuario)", min_value=0, step=1, help="Usa 0 para crear uno nuevo o el ID exacto para editar uno existente.")
                    usuario_n = c1.text_input("Nombre de Usuario / Login", placeholder="ej. jsmith")
                    
                    email_n = c2.text_input("Correo Electrónico", placeholder="empleado@cirpanama.com")
                    rol_n = c2.selectbox("Nivel de Acceso (Rol)", 
                                       ["usuario", "supervisor", "administrador", "master it"],
                                       help="Usuario: Solo entrada. Supervisor: Modifica. Administrador: Borra. Master IT: Todo.")
                    
                    st.divider()
                    btn_guardar = st.form_submit_button("💾 Guardar Cambios en Perfil", use_container_width=True)

                    if btn_guardar:
                        if not usuario_n or not email_n:
                            st.error("Por favor completa los campos de Usuario y Email.")
                        else:
                            datos_perfil = {
                                "usuario": usuario_n,
                                "email": email_n,
                                "rol": rol_n
                            }
                            
                            try:
                                if id_p == 0:
                                    self.db.insert("perfiles", datos_perfil)
                                    st.success(f"✅ Usuario '{usuario_n}' creado exitosamente.")
                                else:
                                    self.db.update("perfiles", datos_perfil, id_p)
                                    st.success(f"✅ Perfil ID {id_p} actualizado correctamente.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al procesar: {e}")

            # Visualización de la tabla actual de perfiles
            st.subheader("Usuarios Registrados")
            perfiles_data = self.db.fetch("perfiles")
            if perfiles_data:
                df_perfiles = pd.DataFrame(perfiles_data)
                # Reordenamos columnas para que sea fácil de leer
                cols = ['id', 'usuario', 'rol', 'email', 'created_at']
                st.dataframe(df_perfiles[[c for c in cols if c in df_perfiles.columns]], 
                             use_container_width=True, 
                             hide_index=True)
                
                # Opción rápida para eliminar (Solo para ti)
                with st.expander("🗑️ Zona de Eliminación de Usuarios"):
                    id_borrar = st.number_input("ID a eliminar", min_value=1, step=1, key="del_user")
                    if st.button("Confirmar Eliminación", type="primary"):
                        self.db.delete("perfiles", id_borrar)
                        st.warning(f"Usuario con ID {id_borrar} eliminado.")
                        st.rerun()
            else:
                st.info("No hay usuarios registrados aparte del Master.")

        with tab2:
            st.subheader("Historial de Movimientos")
            logs = self.db.fetch("logs_sistema")
            if logs:
                st.dataframe(pd.DataFrame(logs).sort_values(by="id", ascending=False), use_container_width=True)
            else:
                st.write("No hay logs registrados todavía.")