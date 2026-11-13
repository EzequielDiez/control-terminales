import os
import re
import time
from datetime import datetime, timedelta
import pandas as pd
from playwright.sync_api import sync_playwright

URL_LOGIN = "https://soluciones-us.abssa.net/NID/GS/WEB/index.aspx?enc=gW5mxPA936+SDqSGbzIqijm+O64SoDpI1PmUJjcBYdg="

USUARIO = os.getenv("COFCO_USER")
CONTRASEÑA = os.getenv("COFCO_PASS")

if not USUARIO or not CONTRASEÑA:
    raise ValueError("Error: No se encontraron las credenciales COFCO_USER o COFCO_PASS en las variables de entorno.")

def parsear_dias_y_fecha(dias_str):
    """Convierte dias_por_vencer de ABSSA a entero y estima la fecha de vencimiento."""
    hoy = datetime.now().date()
    limpio = str(dias_str).strip()
    if limpio.lstrip("-").isdigit():
        dias = int(limpio)
        fecha_vto = (hoy + timedelta(days=dias)).strftime("%d/%m/%Y")
        return dias, fecha_vto
    return None, "-"

def normalizar_estado(estado_raw, dias):
    est = str(estado_raw).strip()
    if "vencid" in est.lower() or (dias is not None and dias < 0):
        return "Vencido"
    if "por vencer" in est.lower() or (dias is not None and 0 <= dias <= 15):
        return "Por Vencer"
    return est if est else "Pendiente"

def ejecutar_scraping_cofco():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(60000)

        print("1. Abriendo portal de COFCO...")
        page.goto(URL_LOGIN)

        try:
            if page.locator("#barraaceptacion").is_visible():
                page.evaluate("PonerCookie()")
                page.wait_for_timeout(1000)
        except Exception:
            pass

        print("2. Ingresando credenciales...")
        page.fill("#txtUsername", USUARIO)
        page.fill("#txtPassword", CONTRASEÑA)
        page.click("#btnContinuar", timeout=90000)
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        try:
            page.evaluate("""() => {
                const modal = document.getElementById('modalSoporte');
                if (modal) modal.remove();
                document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                document.body.classList.remove('modal-open');
            }""")
        except Exception:
            pass

        print("3. Extrayendo Documentación Pendiente / Vencida...")
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
                    if (cols.length >= 7) {
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
                except Exception:
                    break
            pagina_actual += 1

        print("4. Extrayendo Estado por Plantas...")
        plantas_a_recorrer = [
            {"rubro": "59", "planta": "1804", "nombre_planta": "TIMBUES"},
            {"rubro": "70", "planta": "25", "nombre_planta": "ACEITERA GYO"},
            {"rubro": "70", "planta": "1", "nombre_planta": "FERTILIZANTE NPC"}
        ]

        todos_los_empleados_plantas = []

        for item in plantas_a_recorrer:
            print(f"Consultando planta: {item['nombre_planta']}...")
            try:
                page.goto("https://soluciones-us.abssa.net/NID/GS/WEB/gs_contratista_resumen.aspx?ID=526")
                page.wait_for_load_state("networkidle")

                try:
                    page.click("#ctl00_MainContent_btnver")
                    page.wait_for_load_state("networkidle")
                except Exception:
                    pass

                page.select_option("#ctl00_MainContent_cmbRubro", item["rubro"])
                page.wait_for_timeout(500)
                page.select_option("#ctl00_MainContent_cmbPlantas", item["planta"])
                page.wait_for_timeout(500)

                page.click("#ctl00_MainContent_btnBuscar")
                page.wait_for_load_state("networkidle")
                time.sleep(2)

                while True:
                    empleados_pagina = page.evaluate(f"""() => {{
                        const rows = document.querySelectorAll('#ctl00_MainContent_DGEmpDet tr');
                        let data = [];
                        rows.forEach(row => {{
                            const cols = row.querySelectorAll('td');
                            if (cols.length >= 3) {{
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

                    try:
                        btn_sig = page.locator("#ctl00_MainContent_btnSiguiente")
                        if btn_sig.is_visible() and btn_sig.is_enabled():
                            btn_sig.click()
                            page.wait_for_load_state("networkidle")
                            time.sleep(1.5)
                        else:
                            break
                    except Exception:
                        break

            except Exception as ex:
                print(f"Error al consultar planta {item['nombre_planta']}: {ex}")

        browser.close()

        # Guardar nómina por plantas (para Dashboard Global)
        df_empleados = pd.DataFrame(todos_los_empleados_plantas)
        if df_empleados.empty:
            df_empleados = pd.DataFrame(columns=["planta", "nombre", "dni", "cuil", "estado_color"])
        else:
            df_empleados = df_empleados.sort_values(by=["planta", "nombre"], key=lambda col: col.str.lower()).reset_index(drop=True)
        df_empleados.to_csv("cofco_empleados_plantas.csv", index=False, encoding="utf-8-sig")

        # Diccionario Nombre -> DNI para cruzar en pendientes de trabajadores
        mapa_dni = {}
        for _, r in df_empleados.iterrows():
            nom_key = str(r["nombre"]).strip().upper()
            if nom_key and str(r["dni"]).strip():
                mapa_dni[nom_key] = str(r["dni"]).strip()

        # Clasificar pendientes en Empresa, Trabajadores y Vehículos con esquema unificado
        emp_list, trab_list, veh_list = [], [], []

        for item in todos_los_pendientes:
            cat = item["categoria"]
            doc = item["tipo_requerimiento"]
            planta = item["plantas"] if item["plantas"] else "-"
            dias, fecha_vto = parsear_dias_y_fecha(item["dias_por_vencer"])
            estado_norm = normalizar_estado(item["estado"], dias)

            # Extraer nombre entre paréntesis: ej. "Documentos del Empleado (ACOSTA MAXIMILIANO)"
            match_paren = re.search(r"\(([^)]+)\)", cat)
            entidad_nombre = match_paren.group(1).strip() if match_paren else cat.strip()

            cat_lower = cat.lower()
            if "empresa" in cat_lower:
                emp_list.append({
                    "nombre": "HL Control Services",
                    "documento": doc,
                    "planta": planta,
                    "vencimiento": fecha_vto,
                    "dias_restantes": dias,
                    "estado": estado_norm
                })
            elif "veh" in cat_lower or "rodado" in cat_lower or "equip" in cat_lower or "maquin" in cat_lower:
                veh_list.append({
                    "nombre": entidad_nombre,
                    "documento": doc,
                    "planta": planta,
                    "vencimiento": fecha_vto,
                    "dias_restantes": dias,
                    "estado": estado_norm
                })
            else:
                dni_encontrado = mapa_dni.get(entidad_nombre.upper(), "-")
                trab_list.append({
                    "nombre": entidad_nombre,
                    "dni": dni_encontrado,
                    "documento": doc,
                    "planta": planta,
                    "vencimiento": fecha_vto,
                    "dias_restantes": dias,
                    "estado": estado_norm
                })

        df_emp_out = pd.DataFrame(emp_list, columns=["nombre", "documento", "planta", "vencimiento", "dias_restantes", "estado"])
        if not df_emp_out.empty:
            df_emp_out = df_emp_out.sort_values(by="documento", key=lambda c: c.str.lower()).reset_index(drop=True)
        df_emp_out.to_csv("cofco_empresa_pendientes.csv", index=False, encoding="utf-8-sig")

        df_trab_out = pd.DataFrame(trab_list, columns=["nombre", "dni", "documento", "planta", "vencimiento", "dias_restantes", "estado"])
        if not df_trab_out.empty:
            df_trab_out = df_trab_out.sort_values(by=["nombre", "documento"], key=lambda c: c.str.lower()).reset_index(drop=True)
        df_trab_out.to_csv("cofco_trabajadores_pendientes.csv", index=False, encoding="utf-8-sig")

        df_veh_out = pd.DataFrame(veh_list, columns=["nombre", "documento", "planta", "vencimiento", "dias_restantes", "estado"])
        if not df_veh_out.empty:
            df_veh_out = df_veh_out.sort_values(by=["nombre", "documento"], key=lambda c: c.str.lower()).reset_index(drop=True)
        df_veh_out.to_csv("cofco_vehiculos_pendientes.csv", index=False, encoding="utf-8-sig")

        print(f"¡COFCO finalizado! Empresa: {len(df_emp_out)} | Trabajadores: {len(df_trab_out)} | Vehículos: {len(df_veh_out)}")

if __name__ == "__main__":
    ejecutar_scraping_cofco()
