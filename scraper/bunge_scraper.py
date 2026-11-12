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
    """Devuelve los días hasta el vencimiento. Si no es una fecha válida (ej. 'Inhabilitado'), devuelve None."""
    try:
        fecha_vto = datetime.strptime(fecha_str.strip(), "%d/%m/%Y").date()
        hoy = datetime.now().date()
        return (fecha_vto - hoy).days
    except Exception:
        return None

def ejecutar_scraping_bunge():
    os.makedirs("screenshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()

        # -------------------------------------------------------------
        # 1. LOGIN Y SELECCIÓN DE PERFIL BUNGE
        # -------------------------------------------------------------
        print("1. Abriendo portal de Bunge (Control Documentario)...")
        page.goto(URL_LOGIN_BUNGE)
        page.wait_for_load_state("networkidle")

        print("2. Ingresando credenciales...")
        page.fill("#lgLogin_UserName", USUARIO_BUNGE)
        page.fill("#lgLogin_Password", CONTRASEÑA_BUNGE)
        page.click("#lgLogin_LoginButton")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        if page.locator("#pnPerfiles").is_visible():
            print("3. Seleccionando perfil BUNGE...")
            # Buscar opción que contenga BUNGE si hay varias
            opciones = page.locator("#ddlPerfiles_ddlCompanies option").all()
            for opt in opciones:
                texto = opt.inner_text()
                val = opt.get_attribute("value")
                if "BUNGE" in texto.upper() and val:
                    page.select_option("#ddlPerfiles_ddlCompanies", val)
                    break
            if page.locator("#btEntrar").is_visible():
                page.click("#btEntrar")
                page.wait_for_load_state("networkidle")
                time.sleep(2)

        # -------------------------------------------------------------
        # 2. NAVEGAR A SOLAPA VENCIMIENTOS
        # -------------------------------------------------------------
        print("4. Navegando a la solapa Vencimientos...")
        if page.locator("#ctl00_ctl20_hlVencimientos").is_visible():
            page.click("#ctl00_ctl20_hlVencimientos")
        else:
            page.goto(URL_VENCIMIENTOS)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Obtener las plantas/sectores disponibles en el desplegable
        sectores = page.evaluate("""() => {
            const sel = document.querySelector('#ctl00_ContentPlaceHolderMain_cmbSector');
            if (!sel) return [];
            return Array.from(sel.options)
                .filter(o => o.value !== '')
                .map(o => ({ value: o.value, nombre: o.text.trim() }));
        }""")

        print(f"5. Sectores/Plantas detectados: {[s['nombre'] for s in sectores]}")

        empleados_plantas = []
        vencimientos_proximos = []

        # -------------------------------------------------------------
        # 3. RECORRER CADA PLANTA (Muelle RAM y Muelles PSM)
        # -------------------------------------------------------------
        for sector in sectores:
            val_sector = sector["value"]
            nombre_planta = sector["nombre"]
            print(f"   -> Consultando planta: {nombre_planta} (ID: {val_sector})...")

            # Seleccionar sector en el select nativo (compatible con Select2) y disparar change
            page.evaluate(f"""() => {{
                const sel = document.querySelector('#ctl00_ContentPlaceHolderMain_cmbSector');
                sel.value = '{val_sector}';
                sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}""")
            time.sleep(1)

            # Pulsar Buscar
            page.click("#ctl00_ContentPlaceHolderMain_btBuscar")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # Asegurar que muestre hasta 100 registros por página si existe el paginador
            try:
                if page.locator("#ctl00_ContentPlaceHolderMain_ddlPages").is_visible():
                    val_actual = page.locator("#ctl00_ContentPlaceHolderMain_ddlPages").input_value()
                    if val_actual != "100":
                        page.select_option("#ctl00_ContentPlaceHolderMain_ddlPages", "100")
                        page.wait_for_load_state("networkidle")
                        time.sleep(2)
            except Exception:
                pass

            # A) EXTRAER DOCUMENTACIÓN DE EMPRESA (#ctl00_ContentPlaceHolderMain_tbEstadoProveedor)
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
                # Filtrar: solo vencidos, rechazados/inhabilitados o que venzan en <= 15 días
                if es_rojo or (dias is not None and dias <= 15):
                    estado_txt = "Vencido / Observado" if (es_rojo or (dias is not None and dias < 0)) else f"Por Vencer ({dias} días)"
                    vencimientos_proximos.append({
                        "planta": nombre_planta,
                        "tipo": "Empresa",
                        "nombre": "HL CONTROL SERVICES SA",
                        "dni": "-",
                        "documento": d["documento"],
                        "vencimiento": d["valor"],
                        "dias_restantes": dias if dias is not None else -1,
                        "estado": estado_txt
                    })

            # B) EXTRAER PERSONAL Y SUS DOCUMENTOS (#ctl00_ContentPlaceHolderMain_tbVencimientos)
            datos_personal = page.evaluate("""() => {
                const tbl = document.querySelector('#ctl00_ContentPlaceHolderMain_tbVencimientos');
                if (!tbl) return [];
                const rows = Array.from(tbl.querySelectorAll('tr'));
                if (rows.length < 2) return [];
                
                const headers = Array.from(rows[0].querySelectorAll('th')).map(th => th.getAttribute('title') || th.innerText.trim());
                let lista = [];
                
                for (let i = 1; i < rows.length; i++) {
                    const tds = Array.from(rows[i].querySelectorAll('td'));
                    if (tds.length < 3) continue;
                    
                    const dni = tds[0].innerText.trim();
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
                        dni: dni,
                        nombre: nombre,
                        estado_col: estadoCol,
                        row_id: rowId,
                        bg_estado: bgEstado,
                        docs: docs
                    });
                }
                return lista;
            }""")

            for emp in datos_personal:
                es_hab = ("habilitado" in emp["row_id"].lower() and "inabilitado" not in emp["row_id"].lower()) or ("c6efce" in emp["bg_estado"].lower())
                
                empleados_plantas.append({
                    "planta": nombre_planta,
                    "nombre": emp["nombre"],
                    "dni": emp["dni"],
                    "cuil": "",
                    "estado_color": "lightgreen" if es_hab else "lightcoral",
                    "vigencia_hasta": emp["estado_col"]
                })

                # Revisar documentos individuales del empleado (solo <= 15 días o vencidos/rojos)
                for doc in emp["docs"]:
                    dias = calcular_dias_restantes(doc["valor"])
                    es_rojo = "ffc7ce" in doc["bg"].lower() or "red" in doc["bg"].lower()
                    if es_rojo or (dias is not None and dias <= 15):
                        estado_txt = "Vencido / Inhabilitado" if (es_rojo or (dias is not None and dias < 0)) else f"Por Vencer ({dias} días)"
                        vencimientos_proximos.append({
                            "planta": nombre_planta,
                            "tipo": "Personal",
                            "nombre": emp["nombre"],
                            "dni": emp["dni"],
                            "documento": doc["documento"],
                            "vencimiento": doc["valor"],
                            "dias_restantes": dias if dias is not None else -1,
                            "estado": estado_txt
                        })

        # Ordenar alfabéticamente y guardar CSVs
        df_emp = pd.DataFrame(empleados_plantas)
        if df_emp.empty:
            df_emp = pd.DataFrame(columns=["planta", "nombre", "dni", "cuil", "estado_color", "vigencia_hasta"])
        else:
            df_emp = df_emp.sort_values(by=["planta", "nombre"], key=lambda col: col.str.lower()).reset_index(drop=True)
        df_emp.to_csv("bunge_empleados_plantas.csv", index=False, encoding="utf-8-sig")

        df_vtos = pd.DataFrame(vencimientos_proximos)
        if df_vtos.empty:
            df_vtos = pd.DataFrame(columns=["planta", "tipo", "nombre", "dni", "documento", "vencimiento", "dias_restantes", "estado"])
        else:
            df_vtos = df_vtos.sort_values(by=["dias_restantes", "nombre"]).reset_index(drop=True)
        df_vtos.to_csv("bunge_vencimientos_proximos.csv", index=False, encoding="utf-8-sig")

        browser.close()
        print(f"¡Scraping de Bunge finalizado! ({len(df_emp)} registros de personal, {len(df_vtos)} alertas <= 15 días)")

if __name__ == "__main__":
    ejecutar_scraping_bunge()