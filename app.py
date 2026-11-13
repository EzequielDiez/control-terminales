import streamlit as st
import pandas as pd
import os
import requests
import base64
import json

# Configuración de la página
st.set_page_config(
    page_title="Control Centralizado - Terminales Portuarias",
    page_icon="⚓",
    layout="wide"
)

# Función helper para cargar imágenes en Base64 sin pérdida de calidad
def get_base64_img(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

# Función para disparar el workflow en GitHub Actions
def disparar_github_actions():
    token = st.secrets.get("GITHUB_TOKEN")
    if not token:
        st.error("⚠️ Falta configurar GITHUB_TOKEN en los Secrets de Streamlit.")
        return

    url = "https://api.github.com/repos/EzequielDiez/control-terminales/actions/workflows/scraping_diario.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    with st.spinner("Enviando orden de actualización a GitHub Actions..."):
        try:
            res = requests.post(url, headers=headers, json={"ref": "main"})
            if res.status_code == 204:
                st.success("✅ ¡Actualización iniciada en GitHub! Los datos se refrescarán automáticamente en unos 3 minutos.")
            else:
                st.error(f"❌ Error al iniciar workflow ({res.status_code}): {res.text}")
        except Exception as e:
            st.error(f"❌ Error de conexión con GitHub: {e}")

# Estilos CSS optimizados (compactos para evitar scroll en el sidebar)
st.markdown("""
    <style>
    .block-container { padding-top: 3.2rem; padding-bottom: 1rem; }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem; }
    h1 { font-size: 1.8rem !important; margin-bottom: 0px !important; }
    h3 { font-size: 1.2rem !important; margin-top: 5px !important; }
    .stMetric { background-color: #f8f9fa; padding: 8px 12px; border-radius: 6px; border: 1px solid #e9ecef; }
    
    [data-testid="stSidebar"] .stButton button {
        width: 100%;
        text-align: left;
        border: none;
        background-color: transparent;
        padding: 5px 8px;
        margin: 1px 0px;
        font-size: 0.92rem;
        border-radius: 4px;
        color: #31333F;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: #f0f2f6;
        color: #000000;
    }
    
    /* Oculta el menú de opciones superior (Settings / Theme) */
    #MainMenu { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# Pre-carga del logo de HL en Base64
b64_hl = get_base64_img("assets/logoHL.png")

# Logo HL en sidebar
if b64_hl:
    st.sidebar.markdown(
        f'<img src="data:image/png;base64,{b64_hl}" style="width: 175px; height: auto; margin-bottom: 8px;">',
        unsafe_allow_html=True
    )
else:
    st.sidebar.markdown("### 🏢 HL Control Services")

st.sidebar.markdown("### Navegación")

if 'pagina_activa' not in st.session_state:
    st.session_state['pagina_activa'] = 'Dashboard'

# Botón Dashboard
is_dash_active = st.session_state['pagina_activa'] == 'Dashboard'
if st.sidebar.button("👉 **DASHBOARD**" if is_dash_active else "DASHBOARD", key="btn_dash"):
    st.session_state['pagina_activa'] = 'Dashboard'
    st.rerun()

st.sidebar.markdown("<div style='margin-top: 10px; margin-bottom: 4px; font-weight: 700; font-size: 0.85rem; color: #555;'>TERMINALES</div>", unsafe_allow_html=True)

# Botones de Terminales (solo texto en mayúsculas + plataforma)
is_cargill_active = st.session_state['pagina_activa'] == 'Cargill'
if st.sidebar.button("👉 **CARGILL (PRONEXO)**" if is_cargill_active else "- CARGILL (PRONEXO)", key="btn_cargill"):
    st.session_state['pagina_activa'] = 'Cargill'
    st.rerun()

is_cofco_active = st.session_state['pagina_activa'] == 'COFCO'
if st.sidebar.button("👉 **COFCO (ABSSA)**" if is_cofco_active else "- COFCO (ABSSA)", key="btn_cofco"):
    st.session_state['pagina_activa'] = 'COFCO'
    st.rerun()

is_bunge_active = st.session_state['pagina_activa'] == 'Bunge'
if st.sidebar.button("👉 **BUNGE (CONTROL DOCUMENTARIO)**" if is_bunge_active else "- BUNGE (CONTROL DOCUMENTARIO)", key="btn_bunge"):
    st.session_state['pagina_activa'] = 'Bunge'
    st.rerun()

is_prox_active = st.session_state['pagina_activa'] == 'Próximamente'
if st.sidebar.button("👉 **PRÓXIMAMENTE (OTRAS)**" if is_prox_active else "- PRÓXIMAMENTE (OTRAS)", key="btn_prox"):
    st.session_state['pagina_activa'] = 'Próximamente'
    st.rerun()

st.sidebar.markdown("<hr style='margin: 12px 0px;'>", unsafe_allow_html=True)
if st.sidebar.button("🔄 Actualizar Todos los Datos", key="btn_global_scraping"):
    disparar_github_actions()

# =====================================================================
# SECCIÓN: DASHBOARD GENERAL
# =====================================================================
if st.session_state['pagina_activa'] == 'Dashboard':
    st.subheader("📊 Dashboard Global de Habilitaciones")

    # Leyenda compacta de última actualización y estado de errores
    if os.path.exists("estado_scrapers.json"):
        try:
            with open("estado_scrapers.json", "r", encoding="utf-8") as f:
                estado_scr = json.load(f)

            ultima_fecha = estado_scr.get("ultima_ejecucion", "Sin registros")
            errores = [t for t in ["CARGILL", "COFCO", "BUNGE"] if not estado_scr.get(t.capitalize() if t != "COFCO" else "COFCO", {}).get("ok", True)]
            # Compatibilidad con claves exactas del JSON ('COFCO', 'Cargill', 'Bunge')
            errores = []
            for clave_json, nombre_mostrar in [("Cargill", "CARGILL"), ("COFCO", "COFCO"), ("Bunge", "BUNGE")]:
                if clave_json in estado_scr and not estado_scr[clave_json].get("ok", True):
                    errores.append(nombre_mostrar)

            if errores:
                st.caption(f"🔴 **Última actualización:** {ultima_fecha} — ⚠️ Error al sincronizar: **{', '.join(errores)}**")
            else:
                st.caption(f"🟢 **Última actualización:** {ultima_fecha} — Todas las terminales sincronizadas sin errores.")
        except Exception:
            pass

    df_emp_cofco = pd.read_csv("cofco_empleados_plantas.csv") if os.path.exists("cofco_empleados_plantas.csv") else pd.DataFrame()
    df_emp_cargill = pd.read_csv("cargill_empleados_plantas.csv") if os.path.exists("cargill_empleados_plantas.csv") else pd.DataFrame()
    df_emp_bunge = pd.read_csv("bunge_empleados_plantas.csv") if os.path.exists("bunge_empleados_plantas.csv") else pd.DataFrame()

    d_col1, d_col2, d_col3 = st.columns([1.2, 1.2, 1.6])
    with d_col1:
        terminales_disp = ["Seleccione Terminal..."]
        if not df_emp_cargill.empty:
            terminales_disp.append("CARGILL (PRONEXO)")
        if not df_emp_cofco.empty:
            terminales_disp.append("COFCO (ABSSA)")
        if not df_emp_bunge.empty:
            terminales_disp.append("BUNGE (CONTROL DOCUMENTARIO)")
        term_elegida = st.selectbox("Terminal", options=terminales_disp)

    with d_col2:
        if term_elegida == "COFCO (ABSSA)" and not df_emp_cofco.empty:
            plantas_disp = df_emp_cofco['planta'].dropna().unique().tolist()
        elif term_elegida == "CARGILL (PRONEXO)" and not df_emp_cargill.empty:
            plantas_disp = df_emp_cargill['planta'].dropna().unique().tolist()
        elif term_elegida == "BUNGE (CONTROL DOCUMENTARIO)" and not df_emp_bunge.empty:
            plantas_disp = df_emp_bunge['planta'].dropna().unique().tolist()
        else:
            plantas_disp = []
        planta_elegida = st.selectbox("Planta / Instalación", options=["Seleccione Planta..."] + plantas_disp)

    with d_col3:
        busq_dash = st.text_input("🔍 Buscar empleado (nombre o DNI)", placeholder="Filtrar en tiempo real...")

    if term_elegida != "Seleccione Terminal..." and planta_elegida != "Seleccione Planta...":
        if term_elegida == "COFCO (ABSSA)":
            df_target = df_emp_cofco
            prefijo_csv = "COFCO"
        elif term_elegida == "CARGILL (PRONEXO)":
            df_target = df_emp_cargill
            prefijo_csv = "CARGILL"
        else:
            df_target = df_emp_bunge
            prefijo_csv = "BUNGE"

        df_filtrado = df_target[df_target['planta'] == planta_elegida].copy()

        def formatear_estado(val):
            return "Habilitado" if 'lightgreen' in str(val).lower() else "Inhabilitado"

        df_filtrado['Estado'] = df_filtrado['estado_color'].apply(formatear_estado)

        if busq_dash:
            df_filtrado = df_filtrado[
                df_filtrado['nombre'].str.contains(busq_dash, case=False, na=False) |
                df_filtrado['dni'].astype(str).str.contains(busq_dash, case=False, na=False)
            ]

        df_hab = df_filtrado[df_filtrado['Estado'] == "Habilitado"].copy()
        df_inhab = df_filtrado[df_filtrado['Estado'] == "Inhabilitado"].copy()

        m_col1, m_col2, m_col3, m_col4 = st.columns([1, 1, 1, 1.3])
        m_col1.metric("Total en Planta", len(df_filtrado))
        m_col2.metric("🟢 Habilitados", len(df_hab))
        m_col3.metric("🔴 Inhabilitados", len(df_inhab))
        with m_col4:
            st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
            st.download_button(
                f"📥 Descargar CSV ({planta_elegida})",
                data=df_filtrado.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"dashboard_{prefijo_csv}_{planta_elegida}.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.markdown("<hr style='margin: 10px 0px;'>", unsafe_allow_html=True)

        if 'servicio' in df_filtrado.columns:
            cols_mostrar = ['nombre', 'dni', 'servicio']
        elif 'vigencia_hasta' in df_filtrado.columns:
            cols_mostrar = ['nombre', 'dni', 'vigencia_hasta']
        else:
            cols_mostrar = ['nombre', 'dni', 'cuil']
        cols_validas = [c for c in cols_mostrar if c in df_filtrado.columns]

        col_izq, col_der = st.columns(2)

        with col_izq:
            st.markdown(f"#### 🟢 Habilitados ({len(df_hab)})")
            if not df_hab.empty:
                altura_hab = (len(df_hab) + 1) * 35 + 3
                st.dataframe(
                    df_hab[cols_validas],
                    use_container_width=True,
                    hide_index=True,
                    height=altura_hab
                )
            else:
                st.info("No hay personal habilitado con los filtros actuales.")

        with col_der:
            st.markdown(f"#### 🔴 Inhabilitados ({len(df_inhab)})")
            if not df_inhab.empty:
                altura_inhab = (len(df_inhab) + 1) * 35 + 3
                st.dataframe(
                    df_inhab[cols_validas],
                    use_container_width=True,
                    hide_index=True,
                    height=altura_inhab
                )
            else:
                st.success("¡Todo el personal está habilitado!")
    else:
        st.info("👆 Seleccione una **Terminal** y una **Planta / Instalación** en los desplegables superiores.")

# =====================================================================
# SECCIÓN: COFCO
# =====================================================================
elif st.session_state['pagina_activa'] == 'COFCO':
    col_t, col_b = st.columns([4.8, 1.2])
    with col_t:
        st.subheader("Panel de Control: COFCO (ABSSA)")
    with col_b:
        if st.button("🔄 Actualizar", key="btn_scrap_cofco", use_container_width=True):
            disparar_github_actions()

    csv_pen = "cofco_pendientes.csv"
    csv_emp = "cofco_empleados_plantas.csv"

    if os.path.exists(csv_pen) and os.path.exists(csv_emp):
        df_pen = pd.read_csv(csv_pen)
        df_emp = pd.read_csv(csv_emp)

        total_empleados_unicos = df_emp['dni'].nunique() if 'dni' in df_emp.columns else len(df_emp)

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Pendientes", len(df_pen))
        col2.metric("Vencidos", len(df_pen[df_pen['estado'].str.contains("Vencido", case=False, na=False)]))
        col3.metric("Por Vencer", len(df_pen[df_pen['estado'].str.contains("Por Vencer", case=False, na=False)]))
        col4.metric("Pendientes", len(df_pen[df_pen['estado'].str.contains("Pendiente", case=False, na=False)]))
        col5.metric("Empleados Únicos", total_empleados_unicos)

        st.markdown("<hr style='margin: 10px 0px;'>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["📌 Pendientes / Vencimientos", "🏢 Estado de Empleados por Planta"])

        with tab1:
            f_col1, f_col2 = st.columns([1, 2])
            with f_col1:
                estados_disp = df_pen['estado'].unique().tolist()
                filtro_est = st.multiselect("Estado", options=estados_disp, default=estados_disp, key="f_est_cofco")
            with f_col2:
                busqueda = st.text_input("🔍 Buscar requerimiento o categoría:", key="f_busq_cofco", placeholder="Escribe para filtrar...")

            df_f = df_pen[df_pen['estado'].isin(filtro_est)]
            if busqueda:
                df_f = df_f[
                    df_f['tipo_requerimiento'].str.contains(busqueda, case=False, na=False) |
                    df_f['categoria'].str.contains(busqueda, case=False, na=False)
                ]
            st.dataframe(df_f, use_container_width=True, hide_index=True, height=350)
            st.download_button("📥 Descargar CSV Filtrado", data=df_f.to_csv(index=False).encode('utf-8-sig'), file_name="cofco_pendientes_filtrado.csv", mime="text/csv")

        with tab2:
            plantas_disp = df_emp['planta'].unique().tolist()
            planta_elegida = st.selectbox("Planta:", options=["Seleccione una planta..."] + plantas_disp, key="sel_planta_det_cofco")

            if planta_elegida != "Seleccione una planta...":
                df_emp_f = df_emp[df_emp['planta'] == planta_elegida].copy()
                df_emp_f['Estado'] = df_emp_f['estado_color'].apply(lambda x: "🟢 Habilitado" if 'lightgreen' in str(x).lower() else "🔴 Inhabilitado")
                st.dataframe(df_emp_f[['nombre', 'dni', 'cuil', 'Estado']], use_container_width=True, hide_index=True, height=350)
                st.download_button(f"📥 Descargar Reporte {planta_elegida}", data=df_emp_f.to_csv(index=False).encode('utf-8-sig'), file_name=f"empleados_{planta_elegida}.csv", mime="text/csv")
            else:
                st.info("👆 Seleccione una planta en el selector superior.")
    else:
        st.warning("⚠️ No se encontraron archivos de COFCO. Ejecute el scraper.")

# =====================================================================
# SECCIÓN: CARGILL
# =====================================================================
elif st.session_state['pagina_activa'] == 'Cargill':
    col_t, col_b = st.columns([4.8, 1.2])
    with col_t:
        st.subheader("Panel de Control: CARGILL (PRONEXO)")
    with col_b:
        if st.button("🔄 Actualizar", key="btn_scrap_cargill", use_container_width=True):
            disparar_github_actions()

    csv_emp_pend = "cargill_empresa_pendientes.csv"
    csv_trab_pend = "cargill_trabajadores_pendientes.csv"
    csv_acceso = "cargill_empleados_plantas.csv"

    if os.path.exists(csv_emp_pend) or os.path.exists(csv_trab_pend) or os.path.exists(csv_acceso):
        df_cargill_emp = pd.read_csv(csv_emp_pend) if os.path.exists(csv_emp_pend) else pd.DataFrame()
        df_cargill_trab = pd.read_csv(csv_trab_pend) if os.path.exists(csv_trab_pend) else pd.DataFrame()
        df_cargill_acc = pd.read_csv(csv_acceso) if os.path.exists(csv_acceso) else pd.DataFrame()

        c1, c2, c3 = st.columns(3)
        c1.metric("Pendientes Empresa", len(df_cargill_emp))
        c2.metric("Trabajadores Observados", len(df_cargill_trab))
        c3.metric("Total en Control Acceso", len(df_cargill_acc))

        st.markdown("<hr style='margin: 10px 0px;'>", unsafe_allow_html=True)
        tab_c1, tab_c2, tab_c3 = st.tabs(["🏢 Pendientes Empresa", "👷‍♂️ Trabajadores Pendientes", "🛡️ Control de Acceso Go/No Go"])

        with tab_c1:
            if not df_cargill_emp.empty:
                st.dataframe(df_cargill_emp, use_container_width=True, hide_index=True, height=350)
                st.download_button("📥 Descargar Empresa Pendientes", data=df_cargill_emp.to_csv(index=False).encode('utf-8-sig'), file_name="cargill_empresa_pendientes.csv", mime="text/csv")
            else:
                st.info("No hay documentos de empresa pendientes.")

        with tab_c2:
            if not df_cargill_trab.empty:
                st.dataframe(df_cargill_trab, use_container_width=True, hide_index=True, height=350)
                st.download_button("📥 Descargar Trabajadores Pendientes", data=df_cargill_trab.to_csv(index=False).encode('utf-8-sig'), file_name="cargill_trabajadores_pendientes.csv", mime="text/csv")
            else:
                st.info("No hay trabajadores con requerimientos pendientes.")

        with tab_c3:
            if not df_cargill_acc.empty:
                filtro_inst = st.multiselect("Filtrar por Instalación / Planta:", options=df_cargill_acc['planta'].unique().tolist(), default=df_cargill_acc['planta'].unique().tolist())
                df_acc_f = df_cargill_acc[df_cargill_acc['planta'].isin(filtro_inst)].copy()
                df_acc_f['Estado'] = df_acc_f['estado_color'].apply(lambda x: "🟢 Habilitado" if 'lightgreen' in str(x).lower() else "🔴 Inhabilitado")
                st.dataframe(df_acc_f[['nombre', 'dni', 'planta', 'servicio', 'estado_acceso', 'Estado']], use_container_width=True, hide_index=True, height=350)
                st.download_button("📥 Descargar Control de Acceso", data=df_acc_f.to_csv(index=False).encode('utf-8-sig'), file_name="cargill_control_acceso.csv", mime="text/csv")
            else:
                st.info("No hay registros en Control de Acceso.")
    else:
        st.warning("⚠️ No se encontraron archivos de Cargill. Ejecute el scraper.")

# =====================================================================
# SECCIÓN: BUNGE
# =====================================================================
elif st.session_state['pagina_activa'] == 'Bunge':
    col_t, col_b = st.columns([4.8, 1.2])
    with col_t:
        st.subheader("Panel de Control: BUNGE (CONTROL DOCUMENTARIO)")
    with col_b:
        if st.button("🔄 Actualizar", key="btn_scrap_bunge", use_container_width=True):
            disparar_github_actions()

    csv_bunge_vtos = "bunge_vencimientos_proximos.csv"
    csv_bunge_emp = "bunge_empleados_plantas.csv"

    if os.path.exists(csv_bunge_vtos) or os.path.exists(csv_bunge_emp):
        df_bunge_vtos = pd.read_csv(csv_bunge_vtos) if os.path.exists(csv_bunge_vtos) else pd.DataFrame()
        df_bunge_emp = pd.read_csv(csv_bunge_emp) if os.path.exists(csv_bunge_emp) else pd.DataFrame()

        vtos_empresa = len(df_bunge_vtos[df_bunge_vtos['tipo'] == 'Empresa']) if not df_bunge_vtos.empty else 0
        vtos_personal = len(df_bunge_vtos[df_bunge_vtos['tipo'] == 'Personal']) if not df_bunge_vtos.empty else 0
        empleados_unicos = df_bunge_emp['dni'].nunique() if (not df_bunge_emp.empty and 'dni' in df_bunge_emp.columns) else 0

        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Alertas ≤ 15 días (Total)", len(df_bunge_vtos))
        b2.metric("🏢 Docs. Empresa ≤ 15d", vtos_empresa)
        b3.metric("👷‍♂️ Docs. Personal ≤ 15d", vtos_personal)
        b4.metric("Personal Único", empleados_unicos)

        st.markdown("<hr style='margin: 10px 0px;'>", unsafe_allow_html=True)
        tab_b1, tab_b2 = st.tabs(["⚠️ Vencimientos Próximos (≤ 15 días)", "🏢 Estado de Empleados por Planta"])

        with tab_b1:
            if not df_bunge_vtos.empty:
                f_b1, f_b2, f_b3 = st.columns([1.2, 1.2, 1.6])
                with f_b1:
                    plantas_vto = df_bunge_vtos['planta'].unique().tolist()
                    filtro_planta_vto = st.multiselect("Planta / Sector", options=plantas_vto, default=plantas_vto, key="f_planta_bunge")
                with f_b2:
                    tipos_vto = df_bunge_vtos['tipo'].unique().tolist()
                    filtro_tipo_vto = st.multiselect("Categoría", options=tipos_vto, default=tipos_vto, key="f_tipo_bunge")
                with f_b3:
                    busq_bunge = st.text_input("🔍 Buscar empleado o documento:", key="f_busq_bunge", placeholder="Filtrar...")

                df_bv_f = df_bunge_vtos[
                    df_bunge_vtos['planta'].isin(filtro_planta_vto) &
                    df_bunge_vtos['tipo'].isin(filtro_tipo_vto)
                ]
                if busq_bunge:
                    df_bv_f = df_bv_f[
                        df_bv_f['nombre'].str.contains(busq_bunge, case=False, na=False) |
                        df_bv_f['documento'].str.contains(busq_bunge, case=False, na=False) |
                        df_bv_f['dni'].astype(str).str.contains(busq_bunge, case=False, na=False)
                    ]

                st.dataframe(
                    df_bv_f[['planta', 'tipo', 'nombre', 'dni', 'documento', 'vencimiento', 'estado']],
                    use_container_width=True,
                    hide_index=True,
                    height=350
                )
                st.download_button(
                    "📥 Descargar Vencimientos Bunge (≤ 15 días)",
                    data=df_bv_f.to_csv(index=False).encode('utf-8-sig'),
                    file_name="bunge_vencimientos_proximos.csv",
                    mime="text/csv"
                )
            else:
                st.success("✅ No hay documentación vencida ni por vencer en los próximos 15 días en Bunge.")

        with tab_b2:
            if not df_bunge_emp.empty:
                plantas_b_disp = df_bunge_emp['planta'].unique().tolist()
                planta_b_elegida = st.selectbox("Planta / Sector:", options=["Seleccione una planta..."] + plantas_b_disp, key="sel_planta_det_bunge")

                if planta_b_elegida != "Seleccione una planta...":
                    df_be_f = df_bunge_emp[df_bunge_emp['planta'] == planta_b_elegida].copy()
                    df_be_f['Estado'] = df_be_f['estado_color'].apply(lambda x: "🟢 Habilitado" if 'lightgreen' in str(x).lower() else "🔴 Inhabilitado")
                    st.dataframe(
                        df_be_f[['nombre', 'dni', 'vigencia_hasta', 'Estado']],
                        use_container_width=True,
                        hide_index=True,
                        height=350
                    )
                    st.download_button(
                        f"📥 Descargar Nómina {planta_b_elegida}",
                        data=df_be_f.to_csv(index=False).encode('utf-8-sig'),
                        file_name=f"bunge_empleados_{planta_b_elegida}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("👆 Seleccione una planta en el selector superior.")
            else:
                st.info("No hay datos de personal cargados para Bunge.")
    else:
        st.warning("⚠️ No se encontraron archivos de Bunge. Ejecute el scraper.")

elif st.session_state['pagina_activa'] == 'Próximamente':
    st.subheader("🚧 Próximamente")
    st.info("Este módulo estará disponible cuando se integren nuevas terminales portuarias al sistema.")
