import os
import time
import pandas as pd
from playwright.sync_api import sync_playwright

URL_LOGIN = "https://soluciones-us.abssa.net/NID/GS/WEB/index.aspx?enc=gW5mxPA936+SDqSGbzIqijm+O64SoDpI1PmUJjcBYdg="

# Lee automáticamente las variables de entorno de tu Codespace de forma segura
USUARIO = os.getenv("COFCO_USER")
CONTRASEÑA = os.getenv("COFCO_PASS")

if not USUARIO or not CONTRASEÑA:
    raise ValueError("Error: No se encontraron las credenciales COFCO_USER o COFCO_PASS en las variables de entorno.")

def ejecutar_scraping_cofco():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("1. Abriendo portal de COFCO...")
        page.goto(URL_LOGIN)

        # Aceptar cookies
        try:
            if page.locator("#barraaceptacion").is_visible():
                page.evaluate("PonerCookie()")
                page.wait_for_timeout(1000)
        except Exception:
            pass

        print("2. Ingresando credenciales...")
        page.fill("#txtUsername", USUARIO)
        page.fill("#txtPassword", CONTRASEÑA)
        page.click("#btnContinuar")
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # Remover modal de soporte
        try:
            page.evaluate("""() => {
                const modal = document.getElementById('modalSoporte');
                if (modal) modal.remove();
                document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                document.body.classList.remove('modal-open');
            }""")
        except Exception:
            pass

        print("3. Extrayendo Documentación Vencida/por Vencer (Grilla Principal)...")
        try:
            page.wait_for_selector("#ctl00_MainContent_verdetxvenc", state="attached", timeout=10000)
            page.click("#ctl00_MainContent_verdetxvenc", force=True)
        except Exception as e:
            print("No se pudo hacer clic en el botón de documentos vencidos.")
            raise e

        page.wait_for_load_state("networkidle")

        todos_los_pendientes = []
        pagina_actual = 1
        total_paginas = 4

        while pagina_actual <= total_paginas:
            page.wait_for_selector("#ctl00_MainContent_DGridDOCDET")
            filas = page.evaluate("""() => {
                const rows = document.querySelectorAll('#ctl00_MainContent_DGridDOCDET tr');
                let data = [];
                let currentCorte = 'General';
                rows.forEach(row => {
                    if (row.classList.contains('success')) {
                        const textDiv = row.querySelector('.grillaCorte');
                        if (textDiv) currentCorte = textDiv.innerText;
                        return;
                    }
                    const cols = row.querySelectorAll('td');
                    if(cols.length >= 7) {
                        data.push({
                            categoria: currentCorte,
                            tipo_requerimiento: cols[0] ? cols[0].innerText.trim() : '',
                            plantas: cols[1] ? cols[1].innerText.trim() : '',
                            situacion: cols[2] ? cols[2].innerText.trim() : '',
                            estado: cols[4] ? cols[4].innerText.trim() : '',
                            dias_por_vencer: cols[5] ? cols[5].innerText.trim() : '',
                            periodo: cols[6] ? cols[6].innerText.trim() : ''
                        });
                    }
                });
                return data;
            }""")
            todos_los_pendientes.extend(filas)

            if pagina_actual < total_paginas:
                try:
                    page.click("#ctl00_MainContent_btnSiguiente")
                    page.wait_for_load_state("networkidle")
                    time.sleep(1.5)
                except:
                    break
            pagina_actual += 1

        df_pendientes = pd.DataFrame(todos_los_pendientes)
        df_pendientes.to_csv("cofco_pendientes.csv", index=False, encoding="utf-8-sig")

        print("4. Extrayendo Estado por Plantas (con reseteo de página por cada planta)...")
        
        plantas_a_recorrer = [
            {"rubro": "59", "planta": "1804", "nombre_planta": "TIMBUES"},
            {"rubro": "70", "planta": "25", "nombre_planta": "ACEITERA GYO"},
            {"rubro": "70", "planta": "1", "nombre_planta": "FERTILIZANTE NPC"}
        ]

        todos_los_empleados_plantas = []

        for item in plantas_a_recorrer:
            print(f"Consultando planta: {item['nombre_planta']}...")
            try:
                # Cada vez que cambiamos de planta, volvemos a entrar a la sección de empleados de cero
                page.goto("https://soluciones-us.abssa.net/NID/GS/WEB/gs_contratista_resumen.aspx?ID=526")
                page.wait_for_load_state("networkidle")
                
                try:
                    page.click("#ctl00_MainContent_btnver")
                    page.wait_for_load_state("networkidle")
                except:
                    pass

                # Seleccionamos rubro y planta
                page.select_option("#ctl00_MainContent_cmbRubro", item["rubro"])
                page.wait_for_timeout(500)
                page.select_option("#ctl00_MainContent_cmbPlantas", item["planta"])
                page.wait_for_timeout(500)
                
                # Clic en buscar
                page.click("#ctl00_MainContent_btnBuscar")
                page.wait_for_load_state("networkidle")
                time.sleep(2)

                # Bucle para recorrer todas las páginas de empleados de esta planta desde la página 1
                while True:
                    empleados_pagina = page.evaluate(f"""() => {{
                        const rows = document.querySelectorAll('#ctl00_MainContent_DGEmpDet tr');
                        let data = [];
                        rows.forEach(row => {{
                            const cols = row.querySelectorAll('td');
                            if(cols.length >= 3) {{
                                let colorFondo = cols[cols.length - 1].style.backgroundColor || '';
                                data.push({{
                                    planta: "{item['nombre_planta']}",
                                    nombre: cols[0] ? cols[0].innerText.trim() : '',
                                    dni: cols[1] ? cols[1].innerText.trim() : '',
                                    cuil: cols[2] ? cols[2].innerText.trim() : '',
                                    estado_color: colorFondo
                                }});
                            }}
                        }});
                        return data;
                    }}""")
                    todos_los_empleados_plantas.extend(empleados_pagina)

                    # Verificar si existe un botón de siguiente página disponible para empleados
                    try:
                        btn_sig = page.locator("#ctl00_MainContent_btnSiguiente")
                        if btn_sig.is_visible() and btn_sig.is_enabled():
                            btn_sig.click()
                            page.wait_for_load_state("networkidle")
                            time.sleep(1.5)
                        else:
                            break
                    except:
                        break

            except Exception as ex:
                print(f"Error al consultar planta {item['nombre_planta']}: {ex}")

        browser.close()

        df_empleados = pd.DataFrame(todos_los_empleados_plantas)
        df_empleados.to_csv("cofco_empleados_plantas.csv", index=False, encoding="utf-8-sig")
        print(f"¡Proceso completo! Se guardaron {len(todos_los_empleados_plantas)} registros totales en 'cofco_empleados_plantas.csv'.")

if __name__ == "__main__":
    ejecutar_scraping_cofco()