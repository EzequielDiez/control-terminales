import streamlit as st
import pandas as pd
import os

# Configuración de la página
st.set_page_config(
    page_title="Control Centralizado - Terminales Portuarias",
    page_icon="⚓",
    layout="wide"
)

# Estilos CSS para el diseño compacto y la navegación tipo enlace (sin los radios circulares)
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    h1 { font-size: 1.8rem !important; margin-bottom: 0px !important; }
    h3 { font-size: 1.2rem !important; margin-top: 5px !important; }
    .stMetric { background-color: #f8f9fa; padding: 8px 12px; border-radius: 6px; border: 1px solid #e9ecef; }
    
    /* Estilo para los botones de navegación de la barra lateral */
    [data-testid="stSidebar"] .stButton button {
        width: 100%;
        text-align: left;
        border: none;
        background-color: transparent;
        padding: 6px 10px;
        margin: 2px 0px;
        font-size: 1rem;
        border-radius: 4px;
        color: #31333F;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: #f0f2f6;
        color: #000000;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚓ Control Centralizado de Terminales Portuarias")

# --- GESTIÓN DEL ESTADO DE NAVEGACIÓN ---
if 'pagina_activa' not in st.session_state:
    st.session_state['pagina_activa'] = 'Dashboard'

# --- MENÚ DE NAVEGACIÓN EN LA SIDEBAR ---
st.sidebar.title("Navegación")
st.sidebar.markdown("<br>", unsafe_allow_html=True)

# Botón DASHBOARD (Se pone activo/negrita si está seleccionado)
is_dash_active = st.session_state['pagina_activa'] == 'Dashboard'
dash_label = "👉 **DASHBOARD**" if is_dash_active else "DASHBOARD"
if st.sidebar.button(dash_label, key="btn_dash"):
    st.session_state['pagina_activa'] = 'Dashboard'
    st.rerun()

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.markdown("**TERMINALES**")

# Botón COFCO
is_cofco_active = st.session_state['pagina_activa'] == 'COFCO'
cofco_label = "👉 **COFCO**" if is_cofco_active else "- COFCO"
if st.sidebar.button(cofco_label, key="btn_cofco"):
    st.session_state['pagina_activa'] = 'COFCO'
    st.rerun()

# Botón Próximamente
is_prox_active = st.session_state['pagina_activa'] == 'Próximamente'
prox_label = "👉 **Próximamente (Otras Terminales)**" if is_prox_active else "- Próximamente (Otras Terminales)"
if st.sidebar.button(prox_label, key="btn_prox"):
    st.session_state['pagina_activa'] = 'Próximamente'
    st.rerun()


# --- SECCIÓN: DASHBOARD GENERAL ---
if st.session_state['pagina_activa'] == 'Dashboard':
    st.subheader("📊 Dashboard Global de Habilitaciones")
    
    csv_empleados = "cofco_empleados_plantas.csv"
    
    if os.path.exists(csv_empleados):
        df_emp = pd.read_csv(csv_empleados)
        
        # Desplegables limpios sin selección por defecto
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            terminales_disp = ["Seleccione Terminal...", "COFCO"]
            term_elegida = st.selectbox("Terminal", options=terminales_disp, label_visibility="visible")
            
        with d_col2:
            plantas_disp = df_emp['planta'].unique().tolist() if 'planta' in df_emp.columns else []
            planta_elegida = st.selectbox("Planta", options=["Seleccione Planta..."] + plantas_disp, label_visibility="visible")
            
        st.markdown("<hr style='margin: 15px 0px;'>", unsafe_allow_html=True)
        
        # Validación: solo se muestra información si ambos selectores tienen una opción válida elegida
        if term_elegida != "Seleccione Terminal..." and planta_elegida != "Seleccione Planta...":
            df_filtrado = df_emp[df_emp['planta'] == planta_elegida].copy()
            
            def formatear_estado(val):
                return "🟢 Habilitado" if 'lightgreen' in str(val).lower() else "🔴 Inhabilitado"
                
            df_filtrado['Estado'] = df_filtrado['estado_color'].apply(formatear_estado)
            
            total_en_planta = len(df_filtrado)
            habilitados = len(df_filtrado[df_filtrado['Estado'] == "🟢 Habilitado"])
            inhabilitados = len(df_filtrado[df_filtrado['Estado'] == "🔴 Inhabilitado"])
            
            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("Personal en Planta", total_en_planta)
            m_col2.metric("Habilitados", habilitados)
            m_col3.metric("Inhabilitados / Pendientes", inhabilitados)
            
            st.markdown(f"### Listado de Personal: {term_elegida} › {planta_elegida}")
            
            busq_dash = st.text_input("🔍 Buscar empleado por nombre o DNI:", placeholder="Escribe para filtrar...")
            if busq_dash:
                df_filtrado = df_filtrado[
                    df_filtrado['nombre'].str.contains(busq_dash, case=False, na=False) |
                    df_filtrado['dni'].astype(str).str.contains(busq_dash, case=False, na=False)
                ]
                
            st.dataframe(
                df_filtrado[['nombre', 'dni', 'cuil', 'Estado']],
                column_config={
                    "nombre": "Apellido y Nombre",
                    "dni": "DNI",
                    "cuil": "CUIL",
                    "Estado": "Estado Operativo"
                },
                use_container_width=True,
                hide_index=True,
                height=380
            )
            
            st.download_button(
                f"📥 Descargar Reporte - {term_elegida} ({planta_elegida})",
                data=df_filtrado.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"dashboard_{term_elegida}_{planta_elegida}.csv",
                mime="text/csv"
            )
        else:
            st.info("👆 Por favor, seleccione una **Terminal** y una **Planta** en los desplegables superiores para visualizar el personal habilitado e inhabilitado.")
    else:
        st.warning("⚠️ No se encontró el archivo de empleados. Ejecuta primero el script de scraping (`python scraper/cofco_scraper.py`).")

# --- SECCIÓN: TERMINALES -> COFCO ---
elif st.session_state['pagina_activa'] == 'COFCO':
    st.subheader("📋 Panel de Control: COFCO International")
    
    csv_pendientes = "cofco_pendientes.csv"
    csv_empleados = "cofco_empleados_plantas.csv"
    
    if os.path.exists(csv_pendientes) and os.path.exists(csv_empleados):
        df_pen = pd.read_csv(csv_pendientes)
        df_emp = pd.read_csv(csv_empleados)
        
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
                filtro_est = st.multiselect("Estado", options=estados_disp, default=estados_disp, key="f_est")
            with f_col2:
                busqueda = st.text_input("🔍 Buscar requerimiento o categoría:", key="f_busq", placeholder="Escribe para filtrar...")
                
            df_f = df_pen[df_pen['estado'].isin(filtro_est)]
            if busqueda:
                df_f = df_f[
                    df_f['tipo_requerimiento'].str.contains(busqueda, case=False, na=False) |
                    df_f['categoria'].str.contains(busqueda, case=False, na=False)
                ]
                
            st.dataframe(
                df_f,
                column_config={
                    "categoria": "Entidad",
                    "tipo_requerimiento": "Requerimiento",
                    "plantas": "Plantas",
                    "situacion": "Situación",
                    "estado": "Estado",
                    "dias_por_vencer": "Días",
                    "periodo": "Período"
                },
                use_container_width=True,
                hide_index=True,
                height=350
            )
            
            st.download_button("📥 Descargar CSV Filtrado", data=df_f.to_csv(index=False).encode('utf-8-sig'), file_name="cofco_pendientes_filtrado.csv", mime="text/csv")
            
        with tab2:
            st.markdown("### Seleccione una planta para desplegar el personal:")
            plantas_disp = df_emp['planta'].unique().tolist()
            planta_elegida = st.selectbox("Planta:", options=["Seleccione una planta..."] + plantas_disp, key="sel_planta_det")
            
            if planta_elegida != "Seleccione una planta...":
                df_emp_f = df_emp[df_emp['planta'] == planta_elegida].copy()
                
                def formatear_estado(val):
                    return "🟢 Habilitado" if 'lightgreen' in str(val).lower() else "🔴 Inhabilitado"
                    
                df_emp_f['Estado'] = df_emp_f['estado_color'].apply(formatear_estado)
                
                st.dataframe(
                    df_emp_f[['nombre', 'dni', 'cuil', 'Estado']],
                    column_config={
                        "nombre": "Apellido y Nombre",
                        "dni": "DNI",
                        "cuil": "CUIL",
                        "Estado": "Estado en Planta"
                    },
                    use_container_width=True,
                    hide_index=True,
                    height=350
                )
                
                st.download_button(f"📥 Descargar Reporte {planta_elegida}", data=df_emp_f.to_csv(index=False).encode('utf-8-sig'), file_name=f"empleados_{planta_elegida}.csv", mime="text/csv")
            else:
                st.info("👆 Seleccione una planta en el selector superior para ver el listado de empleados.")
    else:
        st.warning("⚠️ No se encontraron los archivos CSV. Ejecuta primero el script de scraping (`python scraper/cofco_scraper.py`).")

# --- SECCIÓN: TERMINALES -> PRÓXIMAMENTE ---
elif st.session_state['pagina_activa'] == 'Próximamente':
    st.subheader("🚧 Próximamente")
    st.info("Este módulo estará disponible cuando se integren nuevas terminales portuarias al sistema.")