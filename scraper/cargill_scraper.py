import os
import time
from datetime import datetime
import pandas as pd
from playwright.sync_api import sync_playwright

URL_LOGIN_CARGILL = "https://aplicacion.pronexo.cl/Common/frmLogin.aspx"
URL_PENDIENTES = "https://aplicacion.pronexo.cl/ModContratista/frmGestionAntecedentesPendientes_Cont.aspx"
URL_ACCESO_GONOGO = "https://aplicacion.pronexo.cl/ModContratista/frmControlAccesoCargillGoNoGoCont.aspx"

USUARIO_CARGILL = os.getenv("CARGILL_USER")
CONTRASEÑA_CARGILL = os.getenv("CARGILL_PASS")

if not USUARIO_CARGILL or not CONTRASEÑA_CARGILL:
    raise ValueError("Error: No se encontraron las credenciales CARGILL_USER o CARGILL_PASS en las variables de entorno.")

def calcular_dias_pronexo(fecha_str):
    """Parsea fechas dd/mm/yyyy o dd-mm-yyyy y calcula días restantes."""
    limpio = str(fecha_str).strip().replace("-", "/")
    for fmt in ("%d/%m/%Y", "%Y/%m/%d"):
        try:
            fecha_vto = datetime.strptime(limpio, fmt).date()
            hoy = datetime.now().date()
            return (fecha_vto - hoy).days, fecha_vto.strftime("%d/%m/%Y")
        except Exception:
            continue
    return None, (limpio if limpio else "-")

def normalizar_estado(estado_raw, dias):
    est = str(estado_raw).strip()
    # Si tiene fecha válida, la fecha define si está vencido o por vencer
    if dias is not None:
        if dias < 0:
            return "Vencido"
        return "Por Vencer"
    # Si no tiene fecha, evaluamos el texto del portal
    if "vencid" in est.lower() or "rechaz" in est.lower():
        return "Vencido"
    return est if est else "Pendiente"

def ejecutar_scraping_cargill():
    os.makedirs("screenshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(60000)

        # -------------------------------------------------------------
        # 1. LOGIN
        # -------------------------------------------------------------
        print("1. Abriendo portal de Cargill (Pronexo)...")
        page.goto(URL_LOGIN_CARGILL)
        page.wait_for_load_state("networkidle")

        print("2. Ingresando credenciales...")
        page.fill("#txtRut2", USUARIO_CARGILL)
        page.fill("#txtPassword2", CONTRASEÑA_CARGILL)
        page.click("#btnEmpresa")
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # -------------------------------------------------------------
        # 2. DOCUMENTOS PENDIENTES (EMPRESA)
        # -------------------------------------------------------------
        print("3. Navegando a antecedentes pendientes...")
        page.goto(URL_PENDIENTES)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        print("4. Extrayendo documentos pendientes de empresa...")
        documentos_empresa_raw = []
        try:
            page.wait_for_selector("#dtEmpresaGPC", timeout=10000)
            documentos_empresa_raw = page.evaluate("""() => {
                const rows = document.querySelectorAll('#dtEmpresaGPC tbody tr');
                let data = [];
                rows.forEach(row => {
                    const cols = row.querySelectorAll('td');
                    if (cols.length >= 8) {
                        data.push({
                            documento: cols[2] ? cols[2].innerText.trim() : '',
                            tope_entrega: cols[3] ? cols[3].innerText.trim() : '',
                            periodo: cols[5] ? cols[5].innerText.trim() : '',
                            cliente: cols[6] ? cols[6].innerText.trim() : '',
                            estado: cols[7] ? cols[7].innerText.trim() : ''
                        });
                    }
                });
                return data;
            }""")
        except Exception as e:
            print(f"Aviso al extraer documentos de empresa: {e}")

        # -------------------------------------------------------------
        # 3. REQUISITOS PENDIENTES DE TRABAJADORES (DETALLE POR LINK)
        # -------------------------------------------------------------
        print("5. Recorriendo requisitos pendientes de trabajadores...")
        trabajadores_pendientes_raw = []

        try:
            page.wait_for_selector("#dtTrabajadorGPC", timeout=10000)
            total_requisitos = page.locator("#dtTrabajadorGPC tbody tr").count()

            for i in range(total_requisitos):
                try:
                    if page.url != URL_PENDIENTES:
                        page.goto(URL_PENDIENTES)
                        page.wait_for_load_state("networkidle")
                        time.sleep(1)

                    page.wait_for_selector("#dtTrabajadorGPC", timeout=10000)
                    fila = page.locator("#dtTrabajadorGPC tbody tr").nth(i)
                    link_req = fila.locator("a.lnk-trabajador")
                    tope_req = fila.locator("td").nth(3).inner_text().strip() if fila.locator("td").count() > 3 else ""

                    if link_req.count() > 0:
                        nombre_requisito = link_req.inner_text().strip()
                        print(f"   -> Requerimiento #{i+1}: {nombre_requisito}")

                        link_req.click()
                        page.wait_for_load_state("networkidle")
                        time.sleep(2)

                        empleados_afectados = page.evaluate("""() => {
                            const rows = document.querySelectorAll('#dtTrabajadorInd tbody tr');
                            let data = [];
                            rows.forEach(row => {
                                const cols = row.querySelectorAll('td');
                                if (cols.length >= 8) {
                                    data.push({
                                        dni: cols[2] ? cols[2].innerText.trim() : '',
                                        nombre: cols[3] ? cols[3].innerText.trim() : '',
                                        vencimiento: cols[6] ? cols[6].innerText.trim() : '',
                                        estado_texto: cols[8] ? cols[8].innerText.trim() : 'Pendiente'
                                    });
                                }
                            });
                            return data;
                        }""")

                        for emp in empleados_afectados:
                            fecha_ref = emp["vencimiento"] if emp["vencimiento"] else tope_req
                            trabajadores_pendientes_raw.append({
                                "nombre": emp["nombre"],
                                "dni": emp["dni"],
                                "documento": nombre_requisito,
                                "fecha_raw": fecha_ref,
                                "estado_raw": emp["estado_texto"]
                            })
                except Exception as ex:
                    print(f"Aviso procesando requerimiento #{i}: {ex}")
        except Exception as e:
            print(f"Aviso en tabla de requerimientos: {e}")

        # -------------------------------------------------------------
        # 4. CONTROL DE ACCESO GO / NO GO (PLANTAS Y HABILITACIONES)
        # -------------------------------------------------------------
        print("6. Navegando a Control de Acceso Go/No Go...")
        page.goto(URL_ACCESO_GONOGO)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        print("7. Aplicando filtros y ejecutando búsqueda...")
        try:
            if page.locator("#btnFiltroMaster").is_visible():
                filtro_card = page.locator("#ctl00_ContentPlaceHolder1_contentFiltro")
                if not filtro_card.is_visible():
                    page.click("#btnFiltroMaster")
                    time.sleep(1)

            btn_buscar = page.locator("#ctl00_ContentPlaceHolder1_btnBuscar")
            if btn_buscar.is_visible():
                btn_buscar.click()
            else:
                page.evaluate("() => { if (typeof WebForm_DoPostBackWithOptions === 'function') { WebForm_DoPostBackWithOptions(new WebForm_PostBackOptions('ctl00$ContentPlaceHolder1$btnBuscar', '', true, '', '', false, false)); } }")

            page.wait_for_load_state("networkidle")
            time.sleep(3)
        except Exception as e:
            print(f"Aviso al buscar en Go/No Go: {e}")

        try:
            page.wait_for_selector("select[name='dtControlAcceso_length']", timeout=7000)
            page.select_option("select[name='dtControlAcceso_length']", "100")
            time.sleep(2)
        except Exception:
            pass

        print("8. Extrayendo nómina de control de acceso por planta...")
        personal_acceso = []
        try:
            page.wait_for_selector("#dtControlAcceso tbody tr.gv-row", timeout=10000)
            personal_acceso = page.evaluate("""() => {
                const rows = document.querySelectorAll('#dtControlAcceso tbody tr');
                let data = [];
                rows.forEach(row => {
                    const cols = row.querySelectorAll('td');
                    if (cols.length >= 9) {
                        data.push({
                            dni: cols[0] ? cols[0].innerText.trim() : '',
                            apellidos: cols[1] ? cols[1].innerText.trim() : '',
                            nombre: cols[2] ? cols[2].innerText.trim() : '',
                            servicio: cols[5] ? cols[5].innerText.trim() : '',
                            instalacion: cols[6] ? cols[6].innerText.trim() : '',
                            estado_autorizacion: cols[8] ? cols[8].innerText.trim() : ''
                        });
                    }
                });
                return data;
            }""")
        except Exception as e:
            print(f"Aviso al extraer tabla Go/No Go: {e}")

        empleados_plantas_cargill = []
        mapa_planta_dni = {}
        for p_acc in personal_acceso:
            nombre_completo = f"{p_acc['apellidos']} {p_acc['nombre']}".strip()
            es_autorizado = "autorizado" in p_acc['estado_autorizacion'].lower() and "no" not in p_acc['estado_autorizacion'].lower()
            planta_nombre = p_acc['instalacion'] if p_acc['instalacion'] else "Cargill General"

            if p_acc['dni']:
                mapa_planta_dni.setdefault(p_acc['dni'], set()).add(planta_nombre)

            empleados_plantas_cargill.append({
                "planta": planta_nombre,
                "nombre": nombre_completo,
                "dni": p_acc['dni'],
                "cuil": "",
                "estado_color": "lightgreen" if es_autorizado else "lightcoral",
                "estado_acceso": p_acc['estado_autorizacion'],
                "servicio": p_acc['servicio']
            })

        df_emp_plantas = pd.DataFrame(empleados_plantas_cargill)
        if df_emp_plantas.empty:
            df_emp_plantas = pd.DataFrame(columns=["planta", "nombre", "dni", "cuil", "estado_color", "estado_acceso", "servicio"])
        else:
            df_emp_plantas = df_emp_plantas.sort_values(by=["planta", "nombre"], key=lambda col: col.str.lower()).reset_index(drop=True)
        df_emp_plantas.to_csv("cargill_empleados_plantas.csv", index=False, encoding="utf-8-sig")

        # Estandarizar Empresa Pendientes
        emp_std = []
        for d in documentos_empresa_raw:
            dias, fecha_vto = calcular_dias_pronexo(d["tope_entrega"])
            emp_std.append({
                "nombre": "HL Control Services",
                "documento": d["documento"],
                "planta": d["cliente"] if d["cliente"] else "-",
                "vencimiento": fecha_vto,
                "dias_restantes": dias,
                "estado": normalizar_estado(d["estado"], dias)
            })
        df_empresa = pd.DataFrame(emp_std, columns=["nombre", "documento", "planta", "vencimiento", "dias_restantes", "estado"])
        if not df_empresa.empty:
            df_empresa = df_empresa.sort_values(by="documento", key=lambda col: col.str.lower()).reset_index(drop=True)
        df_empresa.to_csv("cargill_empresa_pendientes.csv", index=False, encoding="utf-8-sig")

        # Estandarizar Trabajadores Pendientes
        trab_std = []
        for t in trabajadores_pendientes_raw:
            dias, fecha_vto = calcular_dias_pronexo(t["fecha_raw"])
            plantas_emp = ", ".join(sorted(mapa_planta_dni.get(t["dni"], ["-"])))
            trab_std.append({
                "nombre": t["nombre"],
                "dni": t["dni"],
                "documento": t["documento"],
                "planta": plantas_emp,
                "vencimiento": fecha_vto,
                "dias_restantes": dias,
                "estado": normalizar_estado(t["estado_raw"], dias)
            })
        df_trab_pend = pd.DataFrame(trab_std, columns=["nombre", "dni", "documento", "planta", "vencimiento", "dias_restantes", "estado"])
        if not df_trab_pend.empty:
            df_trab_pend = df_trab_pend.sort_values(by=["nombre", "documento"], key=lambda col: col.str.lower()).reset_index(drop=True)
        df_trab_pend.to_csv("cargill_trabajadores_pendientes.csv", index=False, encoding="utf-8-sig")

        # Archivo vacío estándar de Vehículos para mantener consistencia
        df_veh_vacio = pd.DataFrame(columns=["nombre", "documento", "planta", "vencimiento", "dias_restantes", "estado"])
        df_veh_vacio.to_csv("cargill_vehiculos_pendientes.csv", index=False, encoding="utf-8-sig")

        browser.close()
        print("¡Scraping completo de Cargill finalizado con éxito!")

if __name__ == "__main__":
    ejecutar_scraping_cargill()
