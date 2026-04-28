import streamlit as st
import pandas as pd
import datetime

class ModuloClientes:
    def __init__(self, db):
        self.db = db
        self.tabla = "clientes"

    def registrar_log(self, accion, detalle):
        """Registra la actividad en la tabla de auditoría global."""
        user_info = st.session_state.get('user_data', {})
        log_data = {
            "usuario": user_info.get('usuario', 'Sistema'),
            "rol": user_info.get('rol', 'N/A'),
            "accion": accion,
            "modulo": "Clientes",
            "detalle": detalle,
            "fecha": datetime.datetime.now().isoformat()
        }
        try:
            self.db.table("logs_sistema").insert(log_data).execute()
        except:
            pass

    def render(self):
        st.header("👥 Cartera de Clientes")
        user_info = st.session_state.get('user_data', {})
        rol_actual = user_info.get('rol')
        usuario_actual = user_info.get('usuario')

        # --- 1. FORMULARIO DE REGISTRO (Accesible para todos) ---
        with st.expander("➕ Registrar Nuevo Cliente", expanded=False):
            with st.form("form_nuevo_cliente", clear_on_submit=True):
                c1, c2 = st.columns(2)
                nombre = c1.text_input("Nombre / Razón Social").strip().upper()
                # Variable en Python 'id_fiscal', pero se guarda en columna 'identificacion'
                id_fiscal = c2.text_input("Identificación (RUC / Cédula / Pasaporte)").strip().upper()
                
                tel = c1.text_input("Teléfono / WhatsApp")
                mail = c2.text_input("Correo Electrónico")
                
                dir = st.text_area("Dirección").strip().upper()

                if st.form_submit_button("💾 Guardar Cliente", use_container_width=True):
                    if nombre and id_fiscal:
                        nuevo_c = {
                            "nombre": nombre,
                            "identificacion": id_fiscal, # Columna real en DB
                            "telefono": tel,
                            "email": mail,           # Columna real en DB
                            "direccion": dir,
                            "registrado_por": usuario_actual,
                            "fecha_registro": datetime.date.today().isoformat()
                        }
                        try:
                            self.db.table(self.tabla).insert(nuevo_c).execute()
                            self.registrar_log("Creación", f"Cliente {nombre} registrado por {usuario_actual}")
                            st.success(f"✅ Cliente {nombre} guardado correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}. Verifique las columnas en Supabase.")
                    else:
                        st.warning("⚠️ Nombre e Identificación son requeridos.")

        # --- 2. BÚSQUEDA Y LISTADO ---
        st.markdown("---")
        busqueda = st.text_input("🔍 Buscar cliente (Nombre, ID o Email)...").strip().upper()
        
        try:
            res = self.db.table(self.tabla).select("*").order("nombre").execute().data
        except:
            res = []
            st.error("Error al conectar con la tabla 'clientes'.")
        
        if res:
            df = pd.DataFrame(res)
            if busqueda:
                mask = df.apply(lambda row: busqueda in str(row).upper(), axis=1)
                df = df[mask]
            
            # Mostrar tabla principal
            st.dataframe(df, width="stretch", hide_index=True)

            # --- 3. PANEL DE GESTIÓN ---
            st.subheader("🛠️ Gestión de Cuenta")
            opciones = {f"{c['nombre']} [{c['identificacion']}]": c for c in res}
            sel = st.selectbox("Seleccione un cliente:", ["-- Seleccionar --"] + list(opciones.keys()))

            if sel != "-- Seleccionar --":
                cli = opciones[sel]
                tab_editar, tab_estado = st.tabs(["📝 Editar / Eliminar", "📑 Estado de Cuenta"])

                with tab_editar:
                    # ✅ EDICIÓN: Permitida para todos los roles
                    with st.form(f"edit_cli_{cli['id']}"):
                        st.write(f"✍️ Editando: **{cli['nombre']}**")
                        e_nom = st.text_input("Nombre", value=cli['nombre'])
                        e_id = st.text_input("Identificación", value=cli['identificacion'])
                        e_tel = st.text_input("Teléfono", value=cli.get('telefono', ''))
                        e_cor = st.text_input("Email", value=cli.get('email', ''))
                        e_dir = st.text_area("Dirección", value=cli.get('direccion', ''))
                        
                        if st.form_submit_button("💾 Actualizar Información", use_container_width=True):
                            upd = {
                                "nombre": e_nom.upper(),
                                "identificacion": e_id.upper(),
                                "telefono": e_tel,
                                "email": e_cor,
                                "direccion": e_dir.upper()
                            }
                            self.db.table(self.tabla).update(upd).eq("id", cli['id']).execute()
                            self.registrar_log("Edición", f"Datos de {e_nom} actualizados por {usuario_actual}")
                            st.success("Cambios guardados.")
                            st.rerun()

                    # 🚫 ELIMINACIÓN: Solo administrador y master_it
                    if rol_actual in ["administrador", "master_it"]:
                        st.markdown("---")
                        st.error("⚠️ Zona de Eliminación")
                        confirmar = st.checkbox(f"Confirmo que deseo ELIMINAR a {cli['nombre']}")
                        if st.button("🗑️ Eliminar Registro", type="primary", disabled=not confirmar, use_container_width=True):
                            self.db.table(self.tabla).delete().eq("id", cli['id']).execute()
                            self.registrar_log("Eliminación", f"Cliente {cli['nombre']} borrado por {usuario_actual}")
                            st.error("Cliente eliminado.")
                            st.rerun()
                    else:
                        st.info("ℹ️ Tienes permiso para editar, pero la eliminación es solo para administradores.")

                with tab_estado:
                    st.write(f"### 📊 Estado de Cuenta: {cli['nombre']}")
                    try:
                        # Consultar ventas cruzando con el ID del cliente
                        ventas = self.db.table("ventas").select("*").eq("id_cliente", cli['id']).order("fecha", desc=True).execute().data
                        if ventas:
                            df_v = pd.DataFrame(ventas)
                            
                            # Validar columna 'estado' para evitar errores visuales
                            if 'estado' not in df_v.columns: df_v['estado'] = 'PENDIENTE'
                            
                            c1, c2 = st.columns(2)
                            pend = df_v[df_v['estado'] == 'PENDIENTE']['total'].sum()
                            pago = df_v[df_v['estado'] == 'PAGADA']['total'].sum()
                            
                            c1.metric("Saldo Pendiente", f"${pend:,.2f}", delta="- CxC", delta_color="inverse")
                            c2.metric("Total Cobrado", f"${pago:,.2f}")
                            
                            st.dataframe(df_v[['fecha', 'nro_factura', 'usuario', 'total', 'estado']], width="stretch", hide_index=True)
                        else:
                            st.info("No hay historial de facturación para este cliente.")
                    except:
                        st.warning("⚠️ No se pudo cargar el estado de cuenta. Verifique la tabla 'ventas'.")
        else:
            st.info("No hay clientes registrados.")