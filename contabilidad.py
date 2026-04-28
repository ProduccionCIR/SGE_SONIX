import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

class ModuloContabilidad:
    def __init__(self, db):
        self.db = db

    def generar_formato_impresion(self, titulo, datos):
        """Genera HTML para impresión en tamaño Letter (Original y Copia)"""
        fecha = datos.get('fecha') or pd.Timestamp.now().strftime("%d/%m/%Y")
        folio = datos.get('id', '000')
        sujeto = datos.get('cliente') or datos.get('descripcion') or datos.get('banco') or "S/N"
        monto = float(datos.get('total') or datos.get('monto') or 0)
        concepto = datos.get('nota') or datos.get('descripcion') or datos.get('referencia') or "Registro Contable"
        metodo = datos.get('metodo_pago') or "N/A"

        html_content = ""
        for i in range(2):
            tipo = "ORIGINAL" if i == 0 else "COPIA CONTABILIDAD"
            html_content += f"""
            <div style="border: 2px solid #333; padding: 15px; margin-bottom: 40px; font-family: sans-serif; min-height: 420px; color: #333;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div><h2 style="margin:0; color: #004A99;">CIR PANAMÁ</h2><small>Gestión e Inventario Profesional</small></div>
                    <div style="text-align: right;"><h3 style="margin:0;">{titulo}</h3><p style="margin:0; color: red; font-size: 1.2em;">No. {folio}</p></div>
                </div>
                <div style="text-align: center; background: #f0f0f0; margin: 10px 0; padding: 5px;"><b>{tipo}</b></div>
                <table style="width: 100%; margin-top: 10px; line-height: 1.8; border-collapse: collapse;">
                    <tr><td style="border-bottom: 1px solid #eee;"><b>Fecha:</b> {fecha}</td></tr>
                    <tr><td style="border-bottom: 1px solid #eee;"><b>Referencia/Sujeto:</b> {sujeto}</td></tr>
                    <tr><td style="background: #f9f9f9; padding: 10px; border: 1px solid #ccc;">
                        <span style="font-size: 1.1em;"><b>VALOR TOTAL:</b></span> 
                        <span style="font-size: 1.5em; float: right;">${monto:,.2f}</span>
                    </td></tr>
                    <tr><td style="padding: 10px 0;"><b>Detalle:</b> {concepto}</td></tr>
                </table>
                <div style="display: flex; justify-content: space-between; margin-top: 60px;">
                    <div style="width: 40%; border-top: 1px solid #000; text-align: center;"><small>Firma Autorizada</small></div>
                    <div style="width: 40%; border-top: 1px solid #000; text-align: center;"><small>Recibido Conforme</small></div>
                </div>
            </div>
            """
        return f"<div>{html_content}</div><script>window.print();</script>"

    def render(self):
        st.header("📊 Contabilidad y Finanzas CIR")
        
        # 1. CARGA DE DATOS
        ventas = self.db.fetch("ventas")
        recibos = self.db.fetch("recibos")
        gastos = self.db.fetch("gastos")
        depositos = self.db.fetch("depositos")

        # 2. MÉTRICAS DE BALANCE
        t_ingresos = sum(v.get('total', 0) for v in ventas) if ventas else 0.0
        t_gastos = sum(g.get('monto', 0) for g in gastos) if gastos else 0.0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Ingresos (Ventas)", f"${t_ingresos:,.2f}")
        col2.metric("Gastos", f"${t_gastos:,.2f}", delta_color="inverse")
        col3.metric("Utilidad Neta", f"${(t_ingresos - t_gastos):,.2f}")

        # 3. CUENTAS POR COBRAR (CXC)
        st.divider()
        st.subheader("🔍 Cuentas por Cobrar (CXC)")
        if ventas:
            df_v = pd.DataFrame(ventas)
            df_r = pd.DataFrame(recibos) if recibos else pd.DataFrame(columns=['id_venta', 'monto'])
            p_pagos = df_r.groupby('id_venta')['monto'].sum().reset_index() if not df_r.empty else pd.DataFrame(columns=['id_venta', 'monto'])
            p_pagos.columns = ['id_venta', 'total_pagado']
            cxc_df = pd.merge(df_v, p_pagos, left_on='id', right_on='id_venta', how='left').fillna(0)
            cxc_df['saldo'] = cxc_df['total'] - cxc_df['total_pagado']
            pendientes = cxc_df[cxc_df['saldo'] > 0.01]
            if not pendientes.empty:
                st.error(f"Pendiente de cobro: ${pendientes['saldo'].sum():,.2f}")
                with st.expander("Ver detalle CXC"):
                    for _, p in pendientes.iterrows():
                        st.write(f"📌 {p['cliente']} | Factura #{p['id']} | **Saldo: ${p['saldo']:.2f}**")
            else:
                st.success("✅ Cartera al día.")

        # 4. PESTAÑAS DE TRABAJO
        st.divider()
        tabs = st.tabs(["📉 Gastos", "🏦 Depósitos Bancarios", "📄 Recibos de Caja", "📑 Historial Facturas"])

        # --- TAB 1: GASTOS ---
        with tabs[0]:
            with st.expander("📝 Registrar Nuevo Gasto"):
                with st.form("form_gastos"):
                    monto_g = st.number_input("Monto $", min_value=0.0)
                    desc_g = st.text_input("Descripción del Gasto")
                    if st.form_submit_button("💾 Guardar Gasto"):
                        self.db.insert("gastos", {"monto": monto_g, "descripcion": desc_g, "fecha": pd.Timestamp.now().strftime("%Y-%m-%d")})
                        st.rerun()
            if gastos:
                for g in gastos:
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.write(f"📅 {g.get('fecha')} | **{g.get('descripcion')}** | ${g.get('monto'):.2f}")
                        if c2.button("🖨️", key=f"pg_{g['id']}"):
                            st.session_state.print_html = self.generar_formato_impresion("COMPROBANTE DE GASTO", g)

        # --- TAB 2: DEPÓSITOS BANCARIOS (EL FORMULARIO) ---
        with tabs[1]:
            with st.expander("📝 Registrar Nuevo Depósito", expanded=False):
                with st.form("form_dep"):
                    banco = st.selectbox("Banco", ["Banco General", "Banistmo", "BAC", "Global Bank", "Caja de Ahorros", "Otro"])
                    monto_d = st.number_input("Monto Depositado $", min_value=0.0)
                    ref_d = st.text_input("Número de Referencia / ACH")
                    fecha_d = st.date_input("Fecha del Depósito")
                    if st.form_submit_button("💾 Guardar Depósito"):
                        self.db.insert("depositos", {
                            "banco": banco, 
                            "monto": monto_d, 
                            "referencia": ref_d, 
                            "fecha": str(fecha_d)
                        })
                        st.success("Depósito registrado correctamente")
                        st.rerun()
            
            if depositos:
                st.write("### Historial de Movimientos Bancarios")
                for d in depositos:
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.write(f"🏦 **{d.get('banco')}** | Ref: {d.get('referencia')} | Fecha: {d.get('fecha')}")
                        c1.write(f"💰 **Monto: ${d.get('monto', 0):.2f}**")
                        if c2.button("🖨️", key=f"pd_{d['id']}"):
                            st.session_state.print_html = self.generar_formato_impresion("COMPROBANTE DE DEPÓSITO", d)

        # --- TAB 3: RECIBOS DE CAJA ---
        with tabs[2]:
            with st.expander("📝 Generar Recibo de Pago"):
                if ventas:
                    df_v_rec = pd.DataFrame(ventas)
                    opciones = [f"Factura #{x['id']} - {x['cliente']} (${x['total']})" for _, x in df_v_rec.iterrows()]
                    with st.form("f_recibo_f"):
                        sel = st.selectbox("Factura a pagar", opciones)
                        idx = opciones.index(sel)
                        f_sel = df_v_rec.iloc[idx]
                        m_rec = st.number_input("Monto Recibido $", value=float(f_sel['total']))
                        met = st.selectbox("Método", ["Efectivo", "ACH", "Yappy", "Cheque"])
                        if st.form_submit_button("✅ Procesar Recibo"):
                            self.db.insert("recibos", {"cliente": f_sel['cliente'], "monto": m_rec, "metodo_pago": met, "id_venta": int(f_sel['id']), "fecha": pd.Timestamp.now().strftime("%Y-%m-%d")})
                            st.rerun()
            if recibos:
                for r in recibos:
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.write(f"📄 Recibo #{r['id']} | Cliente: **{r.get('cliente')}** | ${r.get('monto'):.2f}")
                        if c2.button("🖨️", key=f"pr_{r['id']}"):
                            st.session_state.print_html = self.generar_formato_impresion("RECIBO DE CAJA", r)

        # --- TAB 4: HISTORIAL FACTURAS ---
        with tabs[3]:
            if ventas:
                bus = st.text_input("🔍 Buscar Factura...").lower()
                for v in ventas:
                    if bus in str(v['id']) or bus in v['cliente'].lower():
                        with st.container(border=True):
                            c1, c2 = st.columns([4, 1])
                            c1.write(f"🧾 Factura #{v['id']} | {v['cliente']} | **Total: ${v['total']:.2f}**")
                            if c2.button("🖨️ Reimprimir", key=f"reim_{v['id']}"):
                                st.session_state.print_html = self.generar_formato_impresion("FACTURA DE VENTA", v)

        # 5. DISPARADOR DE IMPRESIÓN
        if "print_html" in st.session_state:
            components.html(st.session_state.print_html, height=0, width=0)
            del st.session_state.print_html