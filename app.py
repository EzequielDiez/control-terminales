import streamlit as st
import pandas as pd
import os
import re
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
# HELPERS DE NORMALIZACIÓN Y UNIFICACIÓN DE EMPLEADOS
# =====================================================================
def limpiar_dni(val):
    """Extrae solo los dígitos del DNI para cruzar sin errores de puntos o espacios."""
    if pd.isna(val):
        return ""
    solo_digitos = re.sub(r"\D", "", str(val))
    return solo_digitos if len(solo_digitos) >= 6 else ""

def limpiar_texto_nombre(nombre):
    """Normaliza espacios y mayúsculas de un nombre."""
    return re.sub(r"\s+", " ", str(nombre)).strip().upper()

def clave_nombre_aprox(nombre):
    """Genera una clave ordenada por tokens (ej. 'ACOSTA MAXIMILIANO') para respaldo sin DNI."""
    tokens = [t for t in re.sub(r"[^A-ZÁÉÍÓÚÑ\s]", "", limpiar_texto_nombre(nombre)).split() if len(t) > 1]
    return " ".join(sorted(tokens[:2])) if tokens else ""

def corregir_estados_df(df):
    """Asegura que si los días restantes son >= 0 figure como 'Por Vencer' y no 'Vencido'."""
    if df.empty:
        return df
    df_c = df.copy()
    if 'dias_restantes' in df_c.columns and 'estado' in df_c.columns:
        def ajustar_fila(row):
            val_dias = row['dias_restantes']
            est_actual = str(row['estado']).strip()
            if pd.notna(val_dias) and str(val_dias).replace("-", "").replace(".", "").isdigit():
                d = int(float(val_dias))
                if d >= 0 and "vencid" in est_actual.lower():
                    return "Por Vencer"
            return est_actual
        df_c['estado'] = df_c.apply(ajustar_fila, axis=1)
    return df_c

def contar_vencidos(df):
    """Cuenta como vencidos tanto los 'Vencido' como los 'Pendiente' (sin presentar / sin fecha)."""
    if df.empty or 'estado' not in df.columns:
        return 0
    est_s = df['estado'].astype(str).str.lower()
    return int((est_s.str.contains("vencid", na=False) | est_s.str.contains("pendient", na=False)).sum())

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

def construir_indice_empleados(fuentes_plantas, fuentes_pendientes):
    """
    Unifica los empleados de las 3 terminales por DNI limpio (y respaldo por nombre).
    """
    registros_estado = []
    registros_docs = []
    nombres_por_dni = {}
    dni_por_nombre_aprox = {}

    for nombre_term, df_p in fuentes_plantas:
        if df_p.empty:
            continue
        for _, row in df_p.iterrows():
            nom_raw = limpiar_texto_nombre(row.get('nombre', ''))
            if not nom_raw or nom_raw == "NAN":
                continue
            dni_c = limpiar_dni(row.get('dni', ''))
            c_aprox = clave_nombre_aprox(nom_raw)

            if dni_c:
                nombres_por_dni.setdefault(dni_c, set()).add(nom_raw)
                if c_aprox:
                    dni_por_nombre_aprox[c_aprox] = dni_c

            es_hab = 'lightgreen' in str(row.get('estado_color', '')).lower()
            extra = ""
            if pd.notna(row.get('vigencia_hasta')) and str(row.get('vigencia_hasta')).strip():
                extra = f"Vigencia: {row.get('vigencia_hasta')}"
            elif pd.notna(row.get('servicio')) and str(row.get('servicio')).strip():
                extra = f"Servicio: {row.get('servicio')}"

            registros_estado.append({
                "dni_c": dni_c,
                "c_aprox": c_aprox,
                "nom_raw": nom_raw,
                "terminal": nombre_term,
                "planta": str(row.get('planta', '-')).strip(),
                "estado": "🟢 Habilitado" if es_hab else "🔴 Inhabilitado",
                "detalle": extra if extra else "-"
            })

    for nombre_term, df_t in fuentes_pendientes:
        if df_t.empty:
            continue
        df_t_corr = corregir_estados_df(df_t)
        for _, row in df_t_corr.iterrows():
            nom_raw = limpiar_texto_nombre(row.get('nombre', ''))
            if not nom_raw or nom_raw == "NAN":
                continue
            dni_c = limpiar_dni(row.get('dni', ''))
            c_aprox = clave_nombre_aprox(nom_raw)

            if not dni_c and c_aprox in dni_por_nombre_aprox:
                dni_c = dni_por_nombre_aprox[c_aprox]

            if dni_c:
                nombres_por_dni.setdefault(dni_c, set()).add(nom_raw)

            val_dias = row.get('dias_restantes', '-')
            dias_fmt = int(float(val_dias)) if pd.notna(val_dias) and str(val_dias).replace("-", "").replace(".", "").isdigit() else "-"

            registros_docs.append({
                "dni_c": dni_c,
                "c_aprox": c_aprox,
                "nom_raw": nom_raw,
                "terminal": nombre_term,
                "planta": str(row.get('planta', '-')).strip(),
                "documento": str(row.get('documento', '-')).strip(),
                "vencimiento": str(row.get('vencimiento', '-')).strip(),
                "dias_restantes": dias_fmt,
                "estado": str(row.get('estado', '-')).strip()
            })

    nombre_canonico_dni = {}
    for dni_c, set_noms in nombres_por_dni.items():
        mejor_nombre = sorted(set_noms, key=lambda x: (-len(x), x))[0]
        nombre_canonico_dni[dni_c] = mejor_nombre

    def asignar_clave(dni_c, c_aprox, nom_raw):
        if dni_c:
            return f"DNI:{dni_c}"
        if c_aprox in dni_por_nombre_aprox:
            return f"DNI:{dni_por_nombre_aprox[c_aprox]}"
        return f"NOM:{c_aprox or nom_raw}"

    for r in registros_estado:
        r["clave"] = asignar_clave(r["dni_c"], r["c_aprox"], r["nom_raw"])
    for r in registros_docs:
        r["clave"] = asignar_clave(r["dni_c"], r["c_aprox"], r["nom_raw"])

    claves_unicas = {}
    for r in registros_estado + registros_docs:
        cl = r["clave"]
        if cl not in claves_unicas:
            if cl.startswith("DNI:"):
                dni_num = cl.split(":", 1)[1]
                nom_mostrar = nombre_canonico_dni.get(dni_num, r["nom_raw"])
                etiqueta = f"{nom_mostrar} (DNI: {dni_num})"
            else:
                etiqueta = f"{r['nom_raw']} (Sin DNI)"
            claves_unicas[cl] = (nombre_canonico_dni.get(cl.split(":", 1)[1], r["nom_raw"]) if cl.startswith("DNI:") else r["nom_raw"], etiqueta)

    items_ordenados = sorted(claves_unicas.items(), key=lambda x: x[1][0])
    lista_etiquetas = [item[1][1] for item in items_ordenados]
    mapa_etiqueta_a_clave = {item[1][1]: item[0] for item in items_ordenados}

    df_estado_global = pd.DataFrame(registros_estado)
    df_docs_global = pd.DataFrame(registros_docs)

    return lista_etiquetas, mapa_etiqueta_a_clave, df_estado_global, df_docs_global

# =====================================================================
# FUNCIÓN UNIFICADA PARA RENDERIZAR CADA TERMINAL
# =====================================================================
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
    f_plantas = f"{prefijo_csv}_empleados_plantas.csv"

    if not (os.path.exists(f_emp) or os.path.exists(f_trab) or os.path.exists(f_veh) or os.path.exists(f_plantas)):
        st.warning(f"⚠️ No se encontraron archivos actualizados para {titulo_terminal}. Ejecute el scraper.")
        return

    df_emp = corregir_estados_df(pd.read_csv(f_emp)) if os.path.exists(f_emp) else pd.DataFrame()
    df_trab = corregir_estados_df(pd.read_csv(f_trab)) if os.path.exists(f_trab) else pd.DataFrame()
    df_veh = corregir_estados_df(pd.read_csv(f_veh)) if os.path.exists(f_veh) else pd.DataFrame()
    df_plantas = pd.read_csv(f_plantas) if os.path.exists(f_plantas) else pd.DataFrame()

    if not df_emp.empty and 'nombre' in df_emp.columns:
        df_emp = df_emp.sort_values(by=['nombre', 'documento'], key=lambda c: c.astype(str).str.lower()).reset_index(drop=True)
    if not df_trab.empty and 'nombre' in df_trab.columns:
        df_trab = df_trab.sort_values(by=['nombre', 'documento'], key=lambda c: c.astype(str).str.lower()).reset_index(drop=True)
    if not df_veh.empty and 'nombre' in df_veh.columns:
        df_veh = df_veh.sort_values(by=['nombre', 'documento'], key=lambda c: c.astype(str).str.lower()).reset_index(drop=True)
    if not df_plantas.empty and 'nombre' in df_plantas.columns:
        df_plantas = df_plantas.sort_values(by=['planta', 'nombre'], key=lambda c: c.astype(str).str.lower()).reset_index(drop=True)

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

    nombres_tabs = ["🏢 Pendientes Empresa", "👷‍♂️ Pendientes Trabajadores"]
    if hay_vehiculos:
        nombres_tabs.append("🚛 Pendientes Vehículos")
    nombres_tabs.append("🛡️ Habilitados / Inhabilitados")

    tabs = st.tabs(nombres_tabs)

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

    idx_tab_estado = 2
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
        idx_tab_estado = 3

    with tabs[idx_tab_estado]:
        if not df_plantas.empty:
            f_p1, f_p2, f_p3 = st.columns([1.2, 1.2, 1.6])
            with f_p1:
                plantas_disp = df_plantas['planta'].dropna().unique().tolist()
                filtro_planta = st.multiselect("Planta / Instalación:", options=plantas_disp, default=plantas_disp, key=f"f_planta_hab_{prefijo_csv}")
            with f_p2:
                filtro_hab = st.multiselect("Estado:", options=["🟢 Habilitado", "🔴 Inhabilitado"], default=["🟢 Habilitado", "🔴 Inhabilitado"], key=f"f_est_hab_{prefijo_csv}")
            with f_p3:
                busq_hab = st.text_input("🔍 Buscar empleado (nombre o DNI):", key=f"f_busq_hab_{prefijo_csv}", placeholder="Filtrar...")

            df_p_f = df_plantas[df_plantas['planta'].isin(filtro_planta)].copy()
            df_p_f['Estado'] = df_p_f['estado_color'].apply(lambda x: "🟢 Habilitado" if 'lightgreen' in str(x).lower() else "🔴 Inhabilitado")
            df_p_f = df_p_f[df_p_f['Estado'].isin(filtro_hab)]

            if busq_hab:
                df_p_f = df_p_f[
                    df_p_f['nombre'].astype(str).str.contains(busq_hab, case=False, na=False) |
                    df_p_f['dni'].astype(str).str.contains(busq_hab, case=False, na=False)
                ]

            cols_base = {'nombre': 'Nombre', 'dni': 'DNI', 'planta': 'Planta'}
            if 'servicio' in df_p_f.columns:
                cols_base['servicio'] = 'Servicio'
            if 'vigencia_hasta' in df_p_f.columns:
                cols_base['vigencia_hasta'] = 'Vigencia hasta'
            cols_base['Estado'] = 'Estado'

            df_p_vis = df_p_f[list(cols_base.keys())].rename(columns=cols_base)
            st.dataframe(df_p_vis, use_container_width=True, hide_index=True, height=350)
            st.download_button(
                f"📥 Descargar Habilitados/Inhabilitados ({titulo_terminal})",
                data=df_p_vis.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"{prefijo_csv}_habilitados_inhabilitados.csv",
                mime="text/csv",
                key=f"dl_hab_{prefijo_csv}"
            )
        else:
            st.info("No hay registros de habilitación por planta para esta terminal.")

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

    df_pend_cofco = pd.read_csv("cofco_trabajadores_pendientes.csv") if os.path.exists("cofco_trabajadores_pendientes.csv") else pd.DataFrame()
    df_pend_cargill = pd.read_csv("cargill_trabajadores_pendientes.csv") if os.path.exists("cargill_trabajadores_pendientes.csv") else pd.DataFrame()
    df_pend_bunge = pd.read_csv("bunge_trabajadores_pendientes.csv") if os.path.exists("bunge_trabajadores_pendientes.csv") else pd.DataFrame()

    tab_dash1, tab_dash2 = st.tabs(["🏢 Vista por Terminal y Planta", "👷‍♂️ Consulta Individual por Empleado"])

    # -----------------------------------------------------------------
    # PESTAÑA 1: VISTA POR TERMINAL Y PLANTA (SIN CAMPO DE BÚSQUEDA)
    # -----------------------------------------------------------------
    with tab_dash1:
        d_col1, d_col2 = st.columns(2)
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
                    st.info("No hay personal habilitado en esta planta.")

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

    # -----------------------------------------------------------------
    # PESTAÑA 2: CONSULTA INDIVIDUAL POR EMPLEADO (UNIFICADA)
    # -----------------------------------------------------------------
    with tab_dash2:
        fuentes_plantas = [
            ("CARGILL (PRONEXO)", df_emp_cargill),
            ("COFCO (ABSSA)", df_emp_cofco),
            ("BUNGE (CONTROL DOCUMENTARIO)", df_emp_bunge)
        ]
        fuentes_pend = [
            ("CARGILL (PRONEXO)", df_pend_cargill),
            ("COFCO (ABSSA)", df_pend_cofco),
            ("BUNGE (CONTROL DOCUMENTARIO)", df_pend_bunge)
        ]

        lista_etiquetas, mapa_etiquetas, df_est_glob, df_docs_glob = construir_indice_empleados(fuentes_plantas, fuentes_pend)

        if lista_etiquetas:
            emp_elegido = st.selectbox(
                "Seleccione o escriba su nombre / DNI:",
                options=["Seleccione un empleado..."] + lista_etiquetas,
                key="sel_empleado_individual"
            )

            if emp_elegido != "Seleccione un empleado...":
                clave_sel = mapa_etiquetas[emp_elegido]

                df_est_emp = df_est_glob[df_est_glob['clave'] == clave_sel].copy() if not df_est_glob.empty else pd.DataFrame()
                df_docs_emp = df_docs_glob[df_docs_glob['clave'] == clave_sel].copy() if not df_docs_glob.empty else pd.DataFrame()

                cant_hab = len(df_est_emp[df_est_emp['estado'] == "🟢 Habilitado"]) if not df_est_emp.empty else 0
                cant_inhab = len(df_est_emp[df_est_emp['estado'] == "🔴 Inhabilitado"]) if not df_est_emp.empty else 0
                cant_docs = len(df_docs_emp)

                if cant_inhab == 0 and cant_docs == 0 and cant_hab > 0:
                    st.success(f"✅ **{emp_elegido}** se encuentra **HABILITADO EN TODAS LAS TERMINALES Y PLANTAS** registradas ({cant_hab} instalaciones).")
                elif cant_inhab > 0:
                    st.error(f"⛔ **{emp_elegido}** presenta **INHABILITACIÓN** en {cant_inhab} planta(s). Revise el detalle a continuación.")
                elif cant_docs > 0:
                    st.warning(f"⚠️ **{emp_elegido}** está habilitado actualmente, pero tiene **{cant_docs} documento(s) próximo(s) a vencer o pendiente(s)**.")

                e_col1, e_col2, e_col3 = st.columns(3)
                e_col1.metric("🟢 Plantas Habilitado", cant_hab)
                e_col2.metric("🔴 Plantas Inhabilitado", cant_inhab)
                e_col3.metric("📄 Docs. Vencidos / Por Vencer", cant_docs)

                st.markdown("<hr style='margin: 10px 0px;'>", unsafe_allow_html=True)

                col_e_izq, col_e_der = st.columns([1.1, 1.4])

                with col_e_izq:
                    st.markdown("#### 🏭 Estado por Terminal y Planta")
                    if not df_est_emp.empty:
                        df_est_vis = df_est_emp[['terminal', 'planta', 'estado', 'detalle']].rename(columns={
                            'terminal': 'Terminal',
                            'planta': 'Planta / Instalación',
                            'estado': 'Estado',
                            'detalle': 'Observación'
                        }).sort_values(by=['Terminal', 'Planta / Instalación'])
                        altura_e = (len(df_est_vis) + 1) * 35 + 3
                        st.dataframe(df_est_vis, use_container_width=True, hide_index=True, height=altura_e)
                    else:
                        st.info("No figura asignado en las nóminas de plantas.")

                with col_e_der:
                    st.markdown("#### 📋 Documentación Faltante / Por Vencer")
                    if not df_docs_emp.empty:
                        df_docs_vis = df_docs_emp[['terminal', 'planta', 'documento', 'vencimiento', 'dias_restantes', 'estado']].rename(columns={
                            'terminal': 'Terminal',
                            'planta': 'Planta',
                            'documento': 'Documento',
                            'vencimiento': 'Vencimiento',
                            'dias_restantes': 'Días rest.',
                            'estado': 'Estado'
                        })
                        altura_d = (len(df_docs_vis) + 1) * 35 + 3
                        st.dataframe(df_docs_vis, use_container_width=True, hide_index=True, height=altura_d)
                    else:
                        st.success("🎉 ¡Sin documentación vencida, pendiente ni próxima a vencer!")
        else:
            st.info("No hay datos de empleados cargados todavía.")

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
