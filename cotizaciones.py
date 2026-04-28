import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import json
import io

class ModuloCotizaciones:
    def __init__(self, db):
        self.db = db

    def generar_pdf_cotizacion(self, datos, cliente_info):
        """Genera el PDF de la Cotización"""
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 8, "DANA INTERNACIONAL", ln=True, align="C")
        pdf.set_font("Arial", "", 8)
        header = "RUC: 12440-181-123510 DV83 | CALLE 15 & 16, ZONA LIBRE DE COLÓN\nTEL: 446-1326 | gerencia@danainternacional.com"
        pdf.multi_cell(0, 4, header, align="C")
        pdf.ln(5)

        pdf.set_font("Arial", "B", 9)
        pdf.cell(95, 6, f"COTIZADO A: {str(cliente_info).upper()}", 0)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, "COTIZACIÓN / PROFORMA", 0, 1, "R")
        
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "", 9)
        pdf.cell(60, 7, f"COT N°: {datos.get('id', 0)}", 1, 0, 'L', True)
        pdf.cell(60, 7, f"FECHA: {datos.get('fecha')}", 1, 0, 'L', True)
        pdf.cell(0, 7, "VALIDEZ: 15 DÍAS", 1, 1, 'L', True)
        pdf.ln(5)

        pdf.set_font("Arial", "B", 8)
        pdf.cell(95, 8, " DESCRIPCION", 1, 0, "L", True)
        pdf.cell(20, 8, " CANT", 1, 0, "C", True)
        pdf.cell(35, 8, " PRECIO", 1, 0, "C", True)
        pdf.cell(35, 8, " TOTAL", 1, 1, "C", True)

        pdf.set_font("Arial", "", 8)
        for item in datos.get('detalles', []):
            pdf.cell(95, 7, f" {item['nombre'][:50]}", 1)
            pdf.cell(20, 7, f" {item['cantidad']}", 1, 0, "C")
            pdf.cell(35, 7, f" ${float(item['precio']):,.2f}", 1, 0, "R")
            pdf.cell(35, 7, f" ${float(item['subtotal']):,.2f}", 1, 1, "R")

        pdf.ln(5)
        pdf.set_x(130)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(35, 8, "TOTAL:", 1, 0, "L", True)
        pdf.cell(35, 8, f"${float(datos['total']):,.2f}", 1, 1, "R", True)
        return bytes(pdf.output(dest='S'))

    def generar_pdf_venta(self, datos_v, cliente_info, n_f):
        """Genera el PDF de la Factura de Venta"""
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 8, "DANA INTERNACIONAL", ln=True, align="C")
        pdf.set_font("Arial", "", 8)
        header = "RUC: 12440-181-123510 DV83 | CALLE 15 & 16, ZONA LIBRE DE COLÓN"
        pdf.multi_cell(0, 4, header, align="C")
        pdf.ln(5)

        pdf.set_font("Arial", "B", 9)
        pdf.cell(95, 6, f"VENDIDO A: {str(cliente_info).upper()}", 0)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, "FACTURA DE VENTA", 0, 1, "R")
        
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "", 9)
        pdf.cell(60, 7, f"FACTURA N°: {n_f}", 1, 0, 'L', True)
        pdf.cell(60, 7, f"FECHA: {datetime.now().strftime('%d/%m/%Y')}", 1, 0, 'L', True)
        pdf.cell(0, 7, "TÉRMINOS: CONTADO", 1, 1, 'L', True)
        pdf.ln(5)

        pdf.set_font("Arial", "B", 8)
        pdf.cell(95, 8, " DESCRIPCION", 1, 0, "L", True)
        pdf.cell(20, 8, " CANT", 1, 0, "C", True)
        pdf.cell(35, 8, " PRECIO", 1, 0, "C", True)
        pdf.cell(35, 8, " TOTAL", 1, 1, "C", True)

        pdf.set_font("Arial", "", 8)
        for item in datos_v.get('detalle', []):
            pdf.cell(95, 7, f" {item['nombre'][:50]}", 1)
            pdf.cell(20, 7, f" {item['cantidad']}", 1, 0, "C")
            pdf.cell(35, 7, f" ${float(item['precio']):,.2f}", 1, 0, "R")
            pdf.cell(35, 7, f" ${float(item['subtotal']):,.2f}", 1, 1, "R")

        pdf.ln(5)
        pdf.set_x(130)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(35, 8, "TOTAL NETO:", 1, 0, "L", True)
        pdf.cell(35, 8, f"${float(datos_v['total']):,.2f}", 1, 1, "R", True)
        return bytes(pdf.output(dest='S'))

    def vista_crear(self):
        if 'cart_cot' not in st.session_state: st.session_state.cart_cot = []
        
        clientes = self.db.fetch("clientes")
        if not clientes:
            st.warning("Registre clientes primero.")
            return
            
        df_c = pd.DataFrame(clientes)
        cli_sel = st.selectbox("👤 Seleccionar Cliente", ["--"] + df_c['nombre'].tolist())
        
        if cli_sel != "--":
            with st.container(border=True):
                prods = self.db.fetch("productos")
                if prods:
                    df_p = pd.DataFrame(prods)
                    df_p['search'] = df_p['ID'].astype(str) + " | " + df_p.get('MARCA', '').astype(str) + " | " + df_p['DESCRIPCION']
                    p_sel = st.selectbox("Buscar Producto", ["--"] + df_p['search'].tolist())
                    
                    if p_sel != "--":
                        it = df_p[df_p['search'] == p_sel].iloc[0]
                        c1, c2, c3 = st.columns(3)
                        precio = c1.number_input("Precio $", value=float(it.get('PRECIO', 0.0)))
                        cant = c2.number_input("Cantidad", min_value=1, value=1)
                        if c3.button("➕ Añadir"):
                            st.session_state.cart_cot.append({
                                "id": int(it['ID']), "nombre": f"{it.get('MARCA', '')} {it['DESCRIPCION']}", 
                                "cantidad": cant, "precio": precio, "subtotal": cant * precio
                            })
                            st.rerun()

            if st.session_state.cart_cot:
                df_res = pd.DataFrame(st.session_state.cart_cot)
                st.table(df_res[['nombre', 'cantidad', 'precio', 'subtotal']])
                total = df_res['subtotal'].sum()
                
                if st.button("💾 Guardar Cotización", type="primary"):
                    payload = {
                        "cliente": cli_sel, "total": total, "detalles": st.session_state.cart_cot,
                        "fecha": datetime.now().strftime("%Y-%m-%d"), "estado": "Pendiente"
                    }
                    self.db.client.table("cotizaciones").insert(payload).execute()
                    st.success("Guardado.")
                    st.session_state.cart_cot = []
                    st.rerun()

    def facturar(self, cot):
        try:
            v_ex = self.db.fetch("ventas")
            n_f = len(v_ex) + 1 if v_ex else 1
            venta = {"num_fact": n_f, "cliente": cot['cliente'], "total": cot['total'], "detalle": cot['detalles'], "fecha": datetime.now().isoformat()}
            self.db.client.table("ventas").insert(venta).execute()
            
            for item in cot['detalles']:
                if item.get('id'):
                    curr = self.db.client.table("productos").select("CANTIDAD").eq("ID", item['id']).execute()
                    if curr.data:
                        self.db.client.table("productos").update({"CANTIDAD": int(curr.data[0]['CANTIDAD']) - int(item['cantidad'])}).eq("ID", item['id']).execute()
            
            self.db.client.table("cotizaciones").update({"estado": "Facturado"}).eq("id", cot['id']).execute()
            pdf_venta = self.generar_pdf_venta(venta, cot['cliente'], n_f)
            
            st.success(f"✅ Factura {n_f} Creada")
            st.download_button("📥 DESCARGAR FACTURA", pdf_venta, f"Factura_{n_f}.pdf", mime="application/pdf")
        except Exception as e: st.error(f"Error: {e}")

    def render(self):
        st.header("📄 Cotizaciones DANA")
        tab1, tab2 = st.tabs(["🆕 Nueva", "📜 Historial"])
        with tab1: self.vista_crear()
        with tab2:
            cots = self.db.fetch("cotizaciones")
            if cots:
                for c in cots:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([2, 1, 1.5])
                        col1.write(f"**{c['cliente']}**")
                        col1.caption(f"ID: {c['id']} | {c['fecha']}")
                        col2.write(f"**${float(c['total']):,.2f}**")
                        col2.write(f"`{c['estado']}`")
                        
                        b1, b2, b3 = col3.columns(3)
                        pdf_c = self.generar_pdf_cotizacion(c, c['cliente'])
                        b1.download_button("📄", pdf_c, f"Cot_{c['id']}.pdf", key=f"pdf_{c['id']}")
                        
                        if b2.button("📝", key=f"ed_{c['id']}"):
                            st.session_state.cart_cot = c['detalles']
                            self.db.client.table("cotizaciones").delete().eq("id", c['id']).execute()
                            st.rerun()
                            
                        if b3.button("🗑️", key=f"del_{c['id']}"):
                            self.db.client.table("cotizaciones").delete().eq("id", c['id']).execute()
                            st.rerun()
                        
                        if c['estado'] == "Pendiente":
                            if st.button("🚀 Facturar", key=f"fac_{c['id']}", use_container_width=True):
                                self.facturar(c)