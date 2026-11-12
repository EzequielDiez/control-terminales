import os
import time
from playwright.sync_api import sync_playwright

URL_LOGIN_BUNGE = "https://controldocumentario.com/Login.aspx"

USUARIO_BUNGE = os.getenv("BUNGE_USER")
CONTRASEÑA_BUNGE = os.getenv("BUNGE_PASS")

if not USUARIO_BUNGE or not CONTRASEÑA_BUNGE:
    raise ValueError("Error: No se encontraron las credenciales BUNGE_USER o BUNGE_PASS en las variables de entorno.")

def ejecutar_scraping_bunge():
    os.makedirs("screenshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()

        print("1. Abriendo portal de Bunge (Control Documentario)...")
        page.goto(URL_LOGIN_BUNGE)
        page.wait_for_load_state("networkidle")
        page.screenshot(path="screenshots/bunge_1_login.png")

        print("2. Ingresando credenciales...")
        page.fill("#lgLogin_UserName", USUARIO_BUNGE)
        page.fill("#lgLogin_Password", CONTRASEÑA_BUNGE)
        page.click("#lgLogin_LoginButton")
        
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        page.screenshot(path="screenshots/bunge_2_post_login.png")

        # Verificar si aparece el selector de perfiles/empresas (pnPerfiles)
        if page.locator("#pnPerfiles").is_visible():
            print("3. Se detectó pantalla de selección de perfil/empresa...")
            opciones = page.locator("#ddlPerfiles_ddlCompanies option").all_inner_texts()
            print(f"   Perfiles disponibles: {opciones}")
            page.screenshot(path="screenshots/bunge_3_perfiles.png")
            
            # Si hay botón entrar, hacemos clic (o seleccionamos Bunge si aparece en el combo)
            if page.locator("#btEntrar").is_visible():
                page.click("#btEntrar")
                page.wait_for_load_state("networkidle")
                time.sleep(3)
                page.screenshot(path="screenshots/bunge_4_home.png")
        else:
            print("3. Ingreso directo sin selector de perfiles.")
            page.screenshot(path="screenshots/bunge_4_home.png")

        print(f"URL actual tras login: {page.url}")
        browser.close()
        print("¡Prueba de login en Bunge finalizada!")

if __name__ == "__main__":
    ejecutar_scraping_bunge()