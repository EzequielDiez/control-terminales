# ⚓ Control Centralizado de Terminales Portuarias

Sistema automatizado de web scraping para la gestión y seguimiento del estado de documentación, vencimientos e instalaciones de personal en contratistas de terminales portuarias (COFCO / ABSSA), complementado con un dashboard interactivo web de diseño compacto.

---

## 🛠️ Tecnologías Utilizadas
* **Python** (Lógica principal y manipulación de datos con Pandas)
* **Playwright** (Automatización y web scraping del portal)
* **Streamlit** (Interfaz gráfica del Dashboard web)
* **GitHub Codespaces** (Entorno de desarrollo persistente)

---

## 📋 Pasos para la Puesta en Marcha

### 1. Configuración de Credenciales (Variables de Entorno)
El scraper lee de forma segura tu usuario y contraseña mediante variables del sistema para evitar exponer credenciales en el repositorio. Ejecuta estos comandos en tu terminal de Codespaces (reemplazando con tus datos reales):

```bash
export COFCO_USER='tu_usuario_real'
export COFCO_PASS='tu_contraseña_real'
```

*Nota: Si deseas que las credenciales queden guardadas de forma persistente entre sesiones y reinicios, puedes añadirlas a tu perfil de terminal con:*
```bash
echo "export COFCO_USER='tu_usuario_real'" >> ~/.bashrc
echo "export COFCO_PASS='tu_contraseña_real'" >> ~/.bashrc
```

---

### 2. Instalación de Dependencias del Sistema
Dado que Playwright requiere dependencias subyacentes en entornos Linux limpios para ejecutar el navegador de forma headless, asegúrate de instalar las librerías de Chromium junto con los requerimientos de Python:

```bash
playwright install-deps chromium
pip install -r scraper/requirements.txt
```

---

### 3. Ejecución del Scraper (Actualización de Datos)
El scraper se encarga de iniciar sesión de manera automatizada, sortear modales de soporte, recorrer la paginación de documentos pendientes y consultar el estado operativo del personal planta por planta (*Timbues*, *Aceitera GYO* y *Fertilizante NPC*), generando los archivos CSV locales necesarios para el dashboard.

```bash
python scraper/cofco_scraper.py
```

---

### 4. Lanzamiento de la Aplicación Web (Dashboard)
Una vez generados y actualizados los archivos de datos (`cofco_pendientes.csv` y `cofco_empleados_plantas.csv`), inicia la interfaz web interactiva con Streamlit:

```bash
streamlit run app.py
```

Streamlit te proporcionará un enlace local para abrir el panel de control directamente en tu navegador y navegar entre el **Dashboard** general y el **Detalle por Terminal**.