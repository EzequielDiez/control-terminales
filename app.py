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

def get_base64_img(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

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

# Estilos CSS
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
    
    #MainMenu { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# Logo HL en sidebar
b64_hl = get_base64_img("assets/logoHL.png")
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

is_dash_active = st.session_state['pagina_activa'] == 'Dashboard'
if st.sidebar.button("👉 **DASHBOARD**" if is_dash_active else "DASHBOARD", key="btn_dash"):
    st.session_state['pagina_activa'] = 'Dashboard'
    st.rerun()

st.sidebar.markdown("<div style='margin-top: 10px; margin-bottom: 4px; font-weight: 700; font-size: 0.85rem; color: #555;'>TERMINALES</div>", unsafe_allow_html=True)

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
# FUNCIÓN UNIFICADA PARA RENDERIZAR CADA TERMINAL
# =====================================================================
def contar_vencidos(df):
    if df.empty or 'estado' not in df.columns:
        return 0
    return int(df['estado'].astype(str).str.contains("vencid", case=False, na=False).sum())

def formatear_tabla_visual(df, columnas_map):
    df_show = df.copy()
    for col in columnas_map.keys():
        if col not in df_show.columns:
            df_show[col] = "-"
    if 'dias_restantes' in df_show.columns:
        df_show['dias_restantes'] = df_show['dias_restantes'].apply(
            lambda x: int(float(x)) if pd.notna(x) and str(x).replace("-", "").replace(".", "").isdigit() else "-"
        )
    df_show = df_show[list(columnas_map.keys())].rename(columns=columnas_map)
    return df_show

def renderizar_panel_terminal(prefijo_csv, titulo_terminal):
    col_t, col_b = st.columns([4.8, 1.2])
    with col_t:
        st.subheader(f"Panel de Control: {titulo_terminal}")
    with col_b:
        if st.button("🔄 Actualizar", key=f"btn_scrap_{prefijo_csv}", use_container_width=True):
            disparar_github_actions()

    f_emp = f"{prefijo_csv}_empresa_pendientes.csv"
    f_trab = f"{prefijo_csv}_trabajadores_pendientes.csv"
    f_veh = f"{prefijo_csv}_vehiculos_pendientes.csv"

    if not (os.path.exists(f_emp) or os.path.exists(f_trab) or os.path.exists(f_veh)):
        st.warning(f"⚠️ No se encontraron archivos actualizados para {titulo_terminal}. Ejecute el scraper.")
        return

    df_emp = pd.read_csv(f_emp) if os.path.exists(f_emp) else pd.DataFrame()
    df_trab = pd.read_csv(f_trab) if os.path.exists(f_trab) else pd.DataFrame()
    df_veh = pd.read_csv(f_veh) if os.path.exists(f_veh) else pd.DataFrame()

    # Asegurar orden alfabético por nombre
    if not df_emp.empty and 'nombre' in df_emp.columns:
        df_emp = df_emp.sort_values(by=['nombre', 'documento'], key=lambda c: c.astype(str).str.lower()).reset_index(drop=True)
    if not df_trab.empty and 'nombre' in df_trab.columns:
        df_trab = df_trab.sort_values(by=['nombre', 'documento'], key=lambda c: c.astype(str).str.lower()).reset_index(drop=True)
    if not df_veh.empty and 'nombre' in df_veh.columns:
        df_veh = df_veh.sort_values(by=['nombre', 'documento'], key=lambda c: c.astype(str).str.lower()).reset_index(drop=True)

    # Métricas superiores unificadas
    pend_emp = len(df_emp)
    venc_emp = contar_vencidos(df_emp)
    pend_trab = len(df_trab)
    venc_trab = contar_vencidos(df_trab)
    hay_vehiculos = not df_veh.empty

    if hay_vehiculos:
        pend_veh = len(df_veh)
        venc_veh = contar_vencidos(df_veh)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Pendientes Empresa", pend_emp)
        c2.metric("Vencidos Empresa", venc_emp)
        c3.metric("Pendientes Trabajadores", pend_trab)
        c4.metric("Vencidos Trabajadores", venc_trab)
        c5.metric("Pendientes Vehículos", pend_veh)
        c6.metric("Vencidos Vehículos", venc_veh)
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pendientes Empresa", pend_emp)
        c2.metric("Vencidos Empresa", venc_emp)
        c3.metric("Pendientes Trabajadores", pend_trab)
        c4.metric("Vencidos Trabajadores", venc_trab)

    st.markdown("<hr style='margin: 10px 0px;'>", unsafe_allow_html=True)

    # Pestañas unificadas
    nombres_tabs = ["🏢 Pendientes Empresa", "👷‍♂️ Pendientes Trabajadores"]
    if hay_vehiculos:
        nombres_tabs.append("🚛 Pendientes Vehículos")

    tabs = st.tabs(nombres_tabs)

    # TAB 1: PENDIENTES EMPRESA
    with tabs[0]:
        if not df_emp.empty:
            cols_emp = {
                "nombre": "Nombre",
                "documento": "Documento",
                "planta": "Planta",
                "vencimiento": "Vencimiento",
                "dias_restantes": "Días restantes",
                "estado": "Estado"
            }
            df_emp_vis = formatear_tabla_visual(df_emp, cols_emp)
            st.dataframe(df_emp_vis, use_container_width=True, hide_index=True, height=350)
            st.download_button(
                "📥 Descargar Pendientes Empresa",
                data=df_emp_vis.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"{prefijo_csv}_empresa_pendientes.csv",
                mime="text/csv",
                key=f"dl_emp_{prefijo_csv}"
            )
        else:
            st.success("✅ No hay documentos pendientes de empresa.")

    # TAB 2: PENDIENTES TRABAJADORES
    with tabs[1]:
        if not df_trab.empty:
            f_col1, f_col2 = st.columns([1.2, 2])
            with f_col1:
                estados_t = df_trab['estado'].dropna().unique().tolist() if 'estado' in df_trab.columns else []
                filtro_est_t = st.multiselect("Estado", options=estados_t, default=estados_t, key=f"f_est_t_{prefijo_csv}")
            with f_col2:
                busq_t = st.text_input("🔍 Buscar trabajador, DNI o documento:", key=f"f_busq_t_{prefijo_csv}", placeholder="Filtrar...")

            df_t_f = df_trab[df_trab['estado'].isin(filtro_est_t)] if estados_t else df_trab
            if busq_t:
                df_t_f = df_t_f[
                    df_t_f['nombre'].astype(str).str.contains(busq_t, case=False, na=False) |
                    df_t_f['dni'].astype(str).str.contains(busq_t, case=False, na=False) |
                    df_t_f['documento'].astype(str).str.contains(busq_t, case=False, na=False)
                ]

            cols_trab = {
                "nombre": "Nombre",
                "dni": "DNI",
                "documento": "Documento",
                "planta": "Planta",
                "vencimiento": "Vencimiento",
                "dias_restantes": "Días restantes",
                "estado": "Estado"
            }
            df_trab_vis = formatear_tabla_visual(df_t_f, cols_trab)
            st.dataframe(df_trab_vis, use_container_width=True, hide_index=True, height=350)
            st.download_button(
                "📥 Descargar Pendientes Trabajadores",
                data=df_trab_vis.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"{prefijo_csv}_trabajadores_pendientes.csv",
                mime="text/csv",
                key=f"dl_trab_{prefijo_csv}"
            )
        else:
            st.success("✅ No hay documentos pendientes de trabajadores.")

    # TAB 3: PENDIENTES VEHÍCULOS (solo si existen registros)
    if hay_vehiculos:
        with tabs[2]:
            cols_veh = {
                "nombre": "Nombre",
                "documento": "Documento",
                "planta": "Planta",
                "vencimiento": "Vencimiento",
                "dias_restantes": "Días restantes",
                "estado": "Estado"
            }
            df_veh_vis = formatear_tabla_visual(df_veh, cols_veh)
            st.dataframe(df_veh_vis, use_container_width=True, hide_index=True, height=350)
            st.download_button(
                "📥 Descargar Pendientes Vehículos",
                data=df_veh_vis.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"{prefijo_csv}_vehiculos_pendientes.csv",
                mime="text/csv",
                key=f"dl_veh_{prefijo_csv}"
            )

# =====================================================================
# SECCIÓN: DASHBOARD GENERAL
# =====================================================================
if st.session_state['pagina_activa'] == 'Dashboard':
    st.subheader("📊 Dashboard Global de Habilitaciones")

    if os.path.exists("estado_scrapers.json"):
        try:
            with open("estado_scrapers.json", "r", encoding="utf-8") as f:
                estado_scr = json.load(f)

            ultima_fecha = estado_scr.get("ultima_ejecucion", "Sin registros")
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
# SECCIONES DE TERMINALES (USANDO EL COMPONENTE UNIFICADO)
# =====================================================================
elif st.session_state['pagina_activa'] == 'COFCO':
    renderizar_panel_terminal("cofco", "COFCO (ABSSA)")

elif st.session_state['pagina_activa'] == 'Cargill':
    renderizar_panel_terminal("cargill", "CARGILL (PRONEXO)")

elif st.session_state['pagina_activa'] == 'Bunge':
    renderizar_panel_terminal("bunge", "BUNGE (CONTROL DOCUMENTARIO)")

elif st.session_state['pagina_activa'] == 'Próximamente':
    st.subheader("🚧 Próximamente")
    st.info("Este módulo estará disponible cuando se integren nuevas terminales portuarias al sistema.")
