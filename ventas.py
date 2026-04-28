import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF

class ModuloVentas:
    def __init__(self, db):
        self.db = db

    def generar_pdf_factura(self, datos, es_offshore=False):
        """Genera el PDF y convierte el bytearray a bytes para Streamlit."""
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # Encabezado
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 8, "SONIX LTD.", align="C", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("Arial", "", 8)
        tipo_doc = "OFFSHORE / EXPORT" if es_offshore else "LOCAL (ZONA LIBRE)"
        header = f"RUC: 000000000000 DV00 | COLÓN, PANAMÁ\n{tipo_doc}"
        pdf.multi_cell(0, 4, header, align="C")
        pdf.ln(5)

        # Información Cliente
        pdf.set_font("Arial", "B", 9)
        pdf.cell(95, 6, f"CLIENTE: {str(datos.get('cliente', 'S/N')).upper()}", new_x="RIGHT", new_y="TOP")
        pdf.cell(0, 6, "INVOICE / FACTURA", align="R", new_x="LMARGIN", new_y="NEXT")
        
        # Totales Logísticos desde el detalle
        detalles = datos.get('detalle') or datos.get('detalles') or []
        t_peso = sum(float(i.get('peso', 0)) for i in detalles)
        t_cub = sum(float(i.get('cubicaje', 0)) for i in detalles)
        
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "", 8)
        fecha_f = str(datos.get('fecha', ''))[:10]
        pdf.cell(47, 7, f"FECHA: {fecha_f}", border=1, fill=True, new_x="RIGHT", new_y="TOP")
        pdf.cell(47, 7, f"VIA: {datos.get('via_despacho', 'N/A')}", border=1, fill=True, new_x="RIGHT", new_y="TOP")
        pdf.cell(47, 7, f"PESO TOT: {t_peso:.2f} KG", border=1, fill=True, new_x="RIGHT", new_y="TOP")
        pdf.cell(0, 7, f"CUB TOT: {t_cub:.2f} CBM", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # Tabla de Productos
        pdf.set_font("Arial", "B", 7)
        pdf.cell(75, 8, " DESCRIPCION", border=1, fill=True, new_x="RIGHT", new_y="TOP")
        pdf.cell(15, 8, " CANT", border=1, fill=True, align="C", new_x="RIGHT", new_y="TOP")
        pdf.cell(25, 8, " PESO/CUB", border=1, fill=True, align="C", new_x="RIGHT", new_y="TOP")
        pdf.cell(35, 8, " PRECIO", border=1, fill=True, align="C", new_x="RIGHT", new_y="TOP")
        pdf.cell(35, 8, " TOTAL", border=1, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Arial", "", 7)
        for item in detalles:
            logis = f"{item.get('peso',0)}k/{item.get('cubicaje',0)}m"
            pdf.cell(75, 7, f" {str(item.get('nombre', ''))[:45]}", border=1, new_x="RIGHT", new_y="TOP")
            pdf.cell(15, 7, f" {item.get('cantidad', 0)}", border=1, align="C", new_x="RIGHT", new_y="TOP")
            pdf.cell(25, 7, f" {logis}", border=1, align="C", new_x="RIGHT", new_y="TOP")
            pdf.cell(35, 7, f" ${float(item.get('precio', 0)):,.2f}", border=1, align="R", new_x="RIGHT", new_y="TOP")
            pdf.cell(35, 7, f" ${float(item.get('subtotal', 0)):,.2f}", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

        # Totales Finales
        pdf.ln(5)
        pdf.set_x(130)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(35, 8, "TOTAL:", border=1, fill=True, new_x="RIGHT", new_y="TOP")
        pdf.cell(35, 8, f"${float(datos.get('total', 0)):,.2f}", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

        return bytes(pdf.output())

    def formulario_venta(self, es_offshore=False):
        tipo = "off" if es_offshore else "zlc"
        if f'cart_{tipo}' not in st.session_state: st.session_state[f'cart_{tipo}'] = []

        with st.container(border=True):
            clientes = self.db.fetch("clientes") or []
            df_c = pd.DataFrame(clientes)
            c1, c2, c3 = st.columns([2, 1, 1])
            cli = c1.selectbox(f"Cliente", ["--"] + df_c['nombre'].tolist() if not df_c.empty else ["--"], key=f"cli_{tipo}")
            via = c2.selectbox("Vía", ["Marítima", "Terrestre", "Aérea"," Traspaso"], key=f"via_{tipo}")
            flete = c3.number_input("Flete $", min_value=0.0, step=0.1, key=f"flete_{tipo}")

        # 2. Buscador Tipo Excel (Normalización de Columnas)
        st.write("### 🔍 Buscador de Productos")
        productos = self.db.fetch("productos") or []
        if productos:
            df_raw = pd.DataFrame(productos)
            # Normalizamos nombres a Mayúsculas para evitar errores de Index
            df_raw.columns = [c.upper() for c in df_raw.columns]
            
            # Verificamos columnas mínimas necesarias
            cols_req = ['ID', 'DESCRIPCION', 'CANTIDAD', 'PRECIO']
            cols_ok = [c for c in cols_req if c in df_raw.columns]
            
            df_p = df_raw[cols_ok].copy()
            df_p.insert(0, "SEL", False)
            
            edicion = st.data_editor(
                df_p,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "SEL": st.column_config.CheckboxColumn("S", default=False),
                    "ID": st.column_config.TextColumn("Ref", disabled=True),
                    "DESCRIPCION": st.column_config.TextColumn("Descripción", disabled=True),
                    "CANTIDAD": st.column_config.NumberColumn("Stock", disabled=True),
                    "PRECIO": st.column_config.NumberColumn("Precio", format="$%.2f", disabled=True),
                },
                key=f"editor_{tipo}"
            )

            seleccion = edicion[edicion["SEL"] == True]

            if not seleccion.empty:
                it = seleccion.iloc[0]
                with st.container(border=True):
                    st.markdown(f"📍 **Producto:** `{it.get('ID', 'S/R')}` - {it.get('DESCRIPCION', 'S/D')}")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    # Manejo seguro de tipos de datos
                    v_pre = float(it.get('PRECIO', 0.0))
                    v_can = int(it.get('CANTIDAD', 0))
                    
                    pr = col1.number_input("Precio $", value=v_pre, key=f"pr_{tipo}")
                    ct = col2.number_input("Cant.", min_value=1, max_value=max(1, v_can), key=f"ct_{tipo}")
                    pe = col3.number_input("Peso (KG)", min_value=0.0, step=0.1, key=f"pe_{tipo}")
                    cu = col4.number_input("Cub (CBM)", min_value=0.0, step=0.01, key=f"cu_{tipo}")
                    
                    if st.button("➕ Añadir Línea", use_container_width=True, key=f"add_{tipo}"):
                        st.session_state[f'cart_{tipo}'].append({
                            "id": int(it.get('ID', 0)), "nombre": it.get('DESCRIPCION', 'Sin nombre'), 
                            "cantidad": ct, "precio": pr, "subtotal": ct * pr,
                            "peso": pe, "cubicaje": cu
                        })
                        st.rerun()

        # 3. Resumen y Eliminar Línea
        carrito = st.session_state[f'cart_{tipo}']
        if carrito:
            st.write("---")
            for idx, item in enumerate(carrito):
                with st.container(border=True):
                    c_a, c_b, c_c = st.columns([4, 2, 0.5])
                    c_a.write(f"**{item['nombre']}** (Ref: {item['id']})")
                    c_a.caption(f"Cant: {item['cantidad']} | Peso: {item['peso']}kg | Cub: {item['cubicaje']}m³")
                    c_b.write(f"**${item['subtotal']:,.2f}**")
                    if c_c.button("🗑️", key=f"rm_{tipo}_{idx}"):
                        st.session_state[f'cart_{tipo}'].pop(idx)
                        st.rerun()

            total_v = sum(i['subtotal'] for i in carrito) + flete
            if st.button(f"🚀 Emitir Factura (${total_v:,.2f})", type="primary", use_container_width=True, key=f"btn_{tipo}"):
                payload = {
                    "cliente": cli, "total": total_v, "detalle": carrito,
                    "via_despacho": via, "fecha": datetime.now().isoformat(),
                    "observaciones": f"Logística: {sum(i['peso'] for i in carrito)}kg / {sum(i['cubicaje'] for i in carrito)}m³"
                }
                self.db.client.table("ventas").insert(payload).execute()
                for i in carrito:
                    curr = self.db.client.table("productos").select("CANTIDAD").eq("ID", i['id']).execute()
                    if curr.data:
                        self.db.client.table("productos").update({"CANTIDAD": int(curr.data[0]['CANTIDAD']) - i['cantidad']}).eq("ID", i['id']).execute()
                st.success("Guardado.")
                st.session_state[f'cart_{tipo}'] = []
                st.rerun()

    def render_historial(self):
        st.subheader("📜 Historial")
        ventas = self.db.fetch("ventas") or []
        for v in reversed(ventas):
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"**{v.get('cliente')}**")
                col1.caption(f"Fecha: {v.get('fecha','')[:10]} | {v.get('observaciones')}")
                col2.write(f"**${float(v.get('total',0)):,.2f}**")
                
                try:
                    pdf_data = self.generar_pdf_factura(v)
                    col3.download_button("📄 PDF", pdf_data, f"FAC_{v.get('id')}.pdf", key=f"pdf_{v['id']}")
                except:
                    col3.error("PDF Error")
                
                if col3.button("🗑️", key=f"del_{v['id']}"):
                    self.db.client.table("ventas").delete().eq("id", v['id']).execute()
                    st.rerun()

    def render(self):
        st.header("📄 Ventas SONIX LTD.")
        t1, t2, t3 = st.tabs(["🏢 ZLC", "🚢 Offshore", "📜 Historial"])
        with t1: self.formulario_venta(es_offshore=False)
        with t2: self.formulario_venta(es_offshore=True)
        with t3: self.render_historial()