import os
import time
import pandas as pd
from playwright.sync_api import sync_playwright

URL_LOGIN_CARGILL = "https://aplicacion.pronexo.cl/Common/frmLogin.aspx"
URL_PENDIENTES = "https://aplicacion.pronexo.cl/ModContratista/frmGestionAntecedentesPendientes_Cont.aspx"
URL_ACCESO_GONOGO = "https://aplicacion.pronexo.cl/ModContratista/frmControlAccesoCargillGoNoGoCont.aspx"

USUARIO_CARGILL = os.getenv("CARGILL_USER")
CONTRASEÑA_CARGILL = os.getenv("CARGILL_PASS")

if not USUARIO_CARGILL or not CONTRASEÑA_CARGILL:
    raise ValueError("Error: No se encontraron las credenciales CARGILL_USER o CARGILL_PASS en las variables de entorno.")

def ejecutar_scraping_cargill():
    os.makedirs("screenshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

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
        documentos_empresa = []
        try:
            page.wait_for_selector("#dtEmpresaGPC", timeout=10000)
            documentos_empresa = page.evaluate("""() => {
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

        df_empresa = pd.DataFrame(documentos_empresa)
        if df_empresa.empty:
            df_empresa = pd.DataFrame(columns=["documento", "tope_entrega", "periodo", "cliente", "estado"])
        df_empresa.to_csv("cargill_empresa_pendientes.csv", index=False, encoding="utf-8-sig")

        # -------------------------------------------------------------
        # 3. REQUISITOS PENDIENTES DE TRABAJADORES (DETALLE POR LINK)
        # -------------------------------------------------------------
        print("5. Recorriendo requisitos pendientes de trabajadores...")
        trabajadores_pendientes_detalle = []

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
                                        estado_texto: cols[8] ? cols[8].innerText.trim() : 'Rechazado'
                                    });
                                }
                            });
                            return data;
                        }""")

                        for emp in empleados_afectados:
                            trabajadores_pendientes_detalle.append({
                                "nombre": emp["nombre"],
                                "dni": emp["dni"],
                                "requisito_pendiente": nombre_requisito,
                                "estado": emp["estado_texto"]
                            })
                except Exception as ex:
                    print(f"Aviso procesando requerimiento #{i}: {ex}")
        except Exception as e:
            print(f"Aviso en tabla de requerimientos: {e}")

        df_trab_pend = pd.DataFrame(trabajadores_pendientes_detalle)
        if df_trab_pend.empty:
            df_trab_pend = pd.DataFrame(columns=["nombre", "dni", "requisito_pendiente", "estado"])
        df_trab_pend.to_csv("cargill_trabajadores_pendientes.csv", index=False, encoding="utf-8-sig")

        # -------------------------------------------------------------
        # 4. CONTROL DE ACCESO GO / NO GO (PLANTAS Y HABILITACIONES)
        # -------------------------------------------------------------
        print("6. Navegando a Control de Acceso Go/No Go...")
        page.goto(URL_ACCESO_GONOGO)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        print("7. Aplicando filtros y ejecutando búsqueda...")
        try:
            # Si el panel de filtros está colapsado, abrirlo
            if page.locator("#btnFiltroMaster").is_visible():
                filtro_card = page.locator("#ctl00_ContentPlaceHolder1_contentFiltro")
                if not filtro_card.is_visible():
                    page.click("#btnFiltroMaster")
                    time.sleep(1)

            # Clic en el botón Buscar
            btn_buscar = page.locator("#ctl00_ContentPlaceHolder1_btnBuscar")
            if btn_buscar.is_visible():
                btn_buscar.click()
            else:
                page.evaluate("() => { if (typeof WebForm_DoPostBackWithOptions === 'function') { WebForm_DoPostBackWithOptions(new WebForm_PostBackOptions('ctl00$ContentPlaceHolder1$btnBuscar', '', true, '', '', false, false)); } }")
            
            page.wait_for_load_state("networkidle")
            time.sleep(3)
        except Exception as e:
            print(f"Aviso al buscar en Go/No Go: {e}")

        # Configurar la grilla para mostrar 100 registros en la misma página
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
        for p in personal_acceso:
            nombre_completo = f"{p['apellidos']} {p['nombre']}".strip()
            es_autorizado = "autorizado" in p['estado_autorizacion'].lower() and "no" not in p['estado_autorizacion'].lower()
            
            empleados_plantas_cargill.append({
                "planta": p['instalacion'] if p['instalacion'] else "Cargill General",
                "nombre": nombre_completo,
                "dni": p['dni'],
                "cuil": "",
                "estado_color": "lightgreen" if es_autorizado else "lightcoral",
                "estado_acceso": p['estado_autorizacion'],
                "servicio": p['servicio']
            })

        df_emp_plantas = pd.DataFrame(empleados_plantas_cargill)
        if df_emp_plantas.empty:
            df_emp_plantas = pd.DataFrame(columns=["planta", "nombre", "dni", "cuil", "estado_color", "estado_acceso", "servicio"])
            
        df_emp_plantas.to_csv("cargill_empleados_plantas.csv", index=False, encoding="utf-8-sig")

        browser.close()
        print("¡Scraping completo de Cargill finalizado con éxito!")

if __name__ == "__main__":
    ejecutar_scraping_cargill()