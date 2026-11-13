import os
import time
from datetime import datetime
import pandas as pd
from playwright.sync_api import sync_playwright

URL_LOGIN_BUNGE = "https://controldocumentario.com/Login.aspx"
URL_VENCIMIENTOS = "https://controldocumentario.com/Vencimientos.aspx?menu=11"

USUARIO_BUNGE = os.getenv("BUNGE_USER")
CONTRASEÑA_BUNGE = os.getenv("BUNGE_PASS")

if not USUARIO_BUNGE or not CONTRASEÑA_BUNGE:
    raise ValueError("Error: No se encontraron las credenciales BUNGE_USER o BUNGE_PASS en las variables de entorno.")

def calcular_dias_restantes(fecha_str):
    """Devuelve los días hasta el vencimiento. Si no es fecha válida, devuelve None."""
    try:
        fecha_vto = datetime.strptime(fecha_str.strip(), "%d/%m/%Y").date()
        hoy = datetime.now().date()
        return (fecha_vto - hoy).days
    except Exception:
        return None

def extraer_tabla_recursos(page):
    """Extrae filas y columnas de documentos desde #ctl00_ContentPlaceHolderMain_tbVencimientos."""
    return page.evaluate("""() => {
        const tbl = document.querySelector('#ctl00_ContentPlaceHolderMain_tbVencimientos');
        if (!tbl) return [];
        const rows = Array.from(tbl.querySelectorAll('tr'));
        if (rows.length < 2) return [];
        
        const headers = Array.from(rows[0].querySelectorAll('th')).map(th => th.getAttribute('title') || th.innerText.trim());
        let lista = [];
        
        for (let i = 1; i < rows.length; i++) {
            const tds = Array.from(rows[i].querySelectorAll('td'));
            if (tds.length < 3) continue;
            
            const id_recurso = tds[0].innerText.trim();
            const nombre = tds[1].innerText.trim();
            const estadoCol = tds[2].innerText.trim();
            const rowId = rows[i].id || '';
            const bgEstado = tds[2].style.backgroundColor || '';
            
            let docs = [];
            for (let j = 3; j < tds.length; j++) {
                docs.push({
                    documento: headers[j] || 'Documento',
                    valor: tds[j].innerText.trim(),
                    bg: tds[j].style.backgroundColor || ''
                });
            }
            
            lista.push({
                id_recurso: id_recurso,
                nombre: nombre,
                estado_col: estadoCol,
                row_id: rowId,
                bg_estado: bgEstado,
                docs: docs
            });
        }
        return lista;
    }""")

def ejecutar_scraping_bunge():
    os.makedirs("screenshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()
        page.set_default_timeout(60000)

        # -------------------------------------------------------------
        # 1. LOGIN Y SELECCIÓN DE PERFIL BUNGE
        # -------------------------------------------------------------
        print("1. Abriendo portal de Bunge (Control Documentario)...")
        page.goto(URL_LOGIN_BUNGE)
        page.wait_for_load_state("networkidle")

        print("2. Ingresando credenciales...")
        page.fill("#lgLogin_UserName", USUARIO_BUNGE)
        page.fill("#lgLogin_Password", CONTRASEÑA_BUNGE)
        page.click("#lgLogin_LoginButton", timeout=90000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        if page.locator("#pnPerfiles").is_visible():
            print("3. Seleccionando perfil BUNGE...")
            opciones = page.locator("#ddlPerfiles_ddlCompanies option").all()
            for opt in opciones:
                texto = opt.inner_text()
                val = opt.get_attribute("value")
                if "BUNGE" in texto.upper() and val:
                    page.select_option("#ddlPerfiles_ddlCompanies", val)
                    break
            if page.locator("#btEntrar").is_visible():
                page.click("#btEntrar", timeout=90000)
                page.wait_for_load_state("networkidle")
                time.sleep(2)

        # -------------------------------------------------------------
        # 2. NAVEGAR A SOLAPA VENCIMIENTOS
        # -------------------------------------------------------------
        print("4. Navegando a la solapa Vencimientos...")
        if page.locator("#ctl00_ctl20_hlVencimientos").is_visible():
            page.click("#ctl00_ctl20_hlVencimientos", timeout=90000)
        else:
            page.goto(URL_VENCIMIENTOS)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        sectores = page.evaluate("""() => {
            const sel = document.querySelector('#ctl00_ContentPlaceHolderMain_cmbSector');
            if (!sel) return [];
            return Array.from(sel.options)
                .filter(o => o.value !== '')
                .map(o => ({ value: o.value, nombre: o.text.trim() }));
        }""")

        print(f"5. Sectores/Plantas detectados: {[s['nombre'] for s in sectores]}")

        empleados_plantas = []
        empresa_pendientes = []
        trabajadores_pendientes = []
        vehiculos_pendientes = []

        # -------------------------------------------------------------
        # 3. RECORRER CADA PLANTA (Muelle RAM y Muelles PSM)
        # -------------------------------------------------------------
        for sector in sectores:
            val_sector = sector["value"]
            nombre_planta = sector["nombre"]
            print(f"   -> Consultando planta: {nombre_planta} (ID: {val_sector})...")

            # Asegurar tipo recurso = Personal ("0") antes de buscar
            try:
                cmb_tipo = page.locator("#ctl00_ContentPlaceHolderMain_cmbTipoRecurso")
                if cmb_tipo.is_visible() and cmb_tipo.input_value() != "0":
                    with page.expect_navigation(wait_until="networkidle", timeout=60000):
                        cmb_tipo.select_option("0")
                    time.sleep(1)
            except Exception:
                pass

            page.evaluate(f"""() => {{
                const sel = document.querySelector('#ctl00_ContentPlaceHolderMain_cmbSector');
                sel.value = '{val_sector}';
                sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}""")
            time.sleep(1.5)
            page.wait_for_load_state("networkidle")

            page.click("#ctl00_ContentPlaceHolderMain_btBuscar", timeout=90000)
            time.sleep(1.5)
            page.wait_for_load_state("networkidle")

            try:
                ddl_pages = page.locator("#ctl00_ContentPlaceHolderMain_ddlPages")
                if ddl_pages.is_visible() and ddl_pages.input_value() != "100":
                    with page.expect_navigation(wait_until="networkidle", timeout=60000):
                        ddl_pages.select_option("100")
                    time.sleep(1.5)
            except Exception:
                page.wait_for_load_state("networkidle")
                time.sleep(2)

            page.wait_for_selector("#ctl00_ContentPlaceHolderMain_tbVencimientos", timeout=30000)

            # A) DOCUMENTACIÓN DE EMPRESA (<= 15 días o vencido/rojo)
            docs_empresa = page.evaluate("""() => {
                const tbl = document.querySelector('#ctl00_ContentPlaceHolderMain_tbEstadoProveedor');
                if (!tbl) return [];
                const headers = Array.from(tbl.querySelectorAll('tr:first-child th')).map(th => th.getAttribute('title') || th.innerText.trim());
                const cells = Array.from(tbl.querySelectorAll('tr:nth-child(2) td'));
                let res = [];
                cells.forEach((td, idx) => {
                    res.push({
                        documento: headers[idx] || 'Documento Empresa',
                        valor: td.innerText.trim(),
                        bg: td.style.backgroundColor || ''
                    });
                });
                return res;
            }""")

            for d in docs_empresa:
                dias = calcular_dias_restantes(d["valor"])
                es_rojo = "ffc7ce" in d["bg"].lower() or "red" in d["bg"].lower()
                if es_rojo or (dias is not None and dias <= 15):
                    estado_txt = "Vencido" if (es_rojo or (dias is not None and dias < 0)) else "Por Vencer"
                    empresa_pendientes.append({
                        "nombre": "HL Control Services",
                        "documento": d["documento"],
                        "planta": nombre_planta,
                        "vencimiento": d["valor"],
                        "dias_restantes": dias if dias is not None else -1,
                        "estado": estado_txt
                    })

            # B) PERSONAL Y SUS DOCUMENTOS (<= 15 días o vencido/rojo)
            datos_personal = extraer_tabla_recursos(page)

            for emp in datos_personal:
                es_hab = ("habilitado" in emp["row_id"].lower() and "inabilitado" not in emp["row_id"].lower()) or ("c6efce" in emp["bg_estado"].lower())

                empleados_plantas.append({
                    "planta": nombre_planta,
                    "nombre": emp["nombre"],
                    "dni": emp["id_recurso"],
                    "cuil": "",
                    "estado_color": "lightgreen" if es_hab else "lightcoral",
                    "vigencia_hasta": emp["estado_col"]
                })

                for doc in emp["docs"]:
                    dias = calcular_dias_restantes(doc["valor"])
                    es_rojo = "ffc7ce" in doc["bg"].lower() or "red" in doc["bg"].lower()
                    if es_rojo or (dias is not None and dias <= 15):
                        estado_txt = "Vencido" if (es_rojo or (dias is not None and dias < 0)) else "Por Vencer"
                        trabajadores_pendientes.append({
                            "nombre": emp["nombre"],
                            "dni": emp["id_recurso"],
                            "documento": doc["documento"],
                            "planta": nombre_planta,
                            "vencimiento": doc["valor"],
                            "dias_restantes": dias if dias is not None else -1,
                            "estado": estado_txt
                        })

            # C) VEHÍCULOS / MÁQUINAS (cambiar cmbTipoRecurso a "2" y buscar)
            try:
                cmb_tipo = page.locator("#ctl00_ContentPlaceHolderMain_cmbTipoRecurso")
                if cmb_tipo.is_visible():
                    with page.expect_navigation(wait_until="networkidle", timeout=60000):
                        cmb_tipo.select_option("2")
                    time.sleep(1)

                    page.click("#ctl00_ContentPlaceHolderMain_btBuscar", timeout=90000)
                    time.sleep(1.5)
                    page.wait_for_load_state("networkidle")

                    if page.locator("#ctl00_ContentPlaceHolderMain_tbVencimientos").is_visible():
                        datos_vehiculos = extraer_tabla_recursos(page)
                        for veh in datos_vehiculos:
                            datos_auto = f"{veh['nombre']} ({veh['id_recurso']})".strip() if veh['id_recurso'] else veh['nombre']
                            for doc in veh["docs"]:
                                dias = calcular_dias_restantes(doc["valor"])
                                es_rojo = "ffc7ce" in doc["bg"].lower() or "red" in doc["bg"].lower()
                                if es_rojo or (dias is not None and dias <= 15):
                                    estado_txt = "Vencido" if (es_rojo or (dias is not None and dias < 0)) else "Por Vencer"
                                    vehiculos_pendientes.append({
                                        "nombre": datos_auto,
                                        "documento": doc["documento"],
                                        "planta": nombre_planta,
                                        "vencimiento": doc["valor"],
                                        "dias_restantes": dias if dias is not None else -1,
                                        "estado": estado_txt
                                    })
            except Exception as e_veh:
                print(f"      Aviso vehículos ({nombre_planta}): {e_veh}")

        # Guardar CSVs ordenados alfabéticamente
        df_emp_plantas = pd.DataFrame(empleados_plantas, columns=["planta", "nombre", "dni", "cuil", "estado_color", "vigencia_hasta"])
        if not df_emp_plantas.empty:
            df_emp_plantas = df_emp_plantas.sort_values(by=["planta", "nombre"], key=lambda col: col.str.lower()).reset_index(drop=True)
        df_emp_plantas.to_csv("bunge_empleados_plantas.csv", index=False, encoding="utf-8-sig")

        df_emp_pend = pd.DataFrame(empresa_pendientes, columns=["nombre", "documento", "planta", "vencimiento", "dias_restantes", "estado"])
        if not df_emp_pend.empty:
            df_emp_pend = df_emp_pend.sort_values(by="documento", key=lambda col: col.str.lower()).reset_index(drop=True)
        df_emp_pend.to_csv("bunge_empresa_pendientes.csv", index=False, encoding="utf-8-sig")

        df_trab_pend = pd.DataFrame(trabajadores_pendientes, columns=["nombre", "dni", "documento", "planta", "vencimiento", "dias_restantes", "estado"])
        if not df_trab_pend.empty:
            df_trab_pend = df_trab_pend.sort_values(by=["nombre", "documento"], key=lambda col: col.str.lower()).reset_index(drop=True)
        df_trab_pend.to_csv("bunge_trabajadores_pendientes.csv", index=False, encoding="utf-8-sig")

        df_veh_pend = pd.DataFrame(vehiculos_pendientes, columns=["nombre", "documento", "planta", "vencimiento", "dias_restantes", "estado"])
        if not df_veh_pend.empty:
            df_veh_pend = df_veh_pend.sort_values(by=["nombre", "documento"], key=lambda col: col.str.lower()).reset_index(drop=True)
        df_veh_pend.to_csv("bunge_vehiculos_pendientes.csv", index=False, encoding="utf-8-sig")

        browser.close()
        print(f"¡Bunge finalizado! Empresa: {len(df_emp_pend)} | Trabajadores: {len(df_trab_pend)} | Vehículos: {len(df_veh_pend)}")

if __name__ == "__main__":
    ejecutar_scraping_bunge()
