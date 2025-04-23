# Script DATACOM DM986-416AX30

## 🖥️ Ejecutable incluido

Este proyecto contiene un ejecutable `.exe` llamado **DATACOM DM986-416AX30**, ubicado en la carpeta `dist/`.

> ⚠️ **Ejecutá este archivo para configurar tu módem DATACOM DM986-416-AX30 de forma automática.**

---

## 🌐 Compatibilidad con Microsoft Edge

Este ejecutable funciona específicamente con la versión **135.0.3179.85** del navegador **Microsoft Edge**.

### ❌ Si tu versión de Edge es diferente, el programa no funcionará correctamente.

---

## ✅ ¿Qué puedo hacer si no tengo esa versión?

Tenés **dos opciones**:

### Opción 1: Instalar la versión compatible de Edge en tu computadora

Podés buscar e instalar manualmente la versión **135.0.3179.85** de Microsoft Edge para garantizar el correcto funcionamiento del ejecutable.

### Opción 2: Reemplazar el driver del proyecto y recompilar

Si preferís usar tu versión actual de Microsoft Edge, podés reemplazar el driver incluido y recompilar el ejecutable. Seguí estos pasos:

1. **Eliminar archivos anteriores del proyecto**:
   - Borrá el archivo `msedgedriver.exe`.
   - Borrá también las carpetas `build/`, `dist/` y el archivo `.spec`.

2. **Descargar el driver compatible con tu navegador**:
   - Abrí Microsoft Edge y accedé a `edge://settings/help` para ver tu versión exacta.
   - Ingresá a la [página oficial de WebDriver de Microsoft](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/).
   - Descargá el archivo `.zip` que corresponda a tu versión de Edge.

3. **Agregar el nuevo driver al proyecto**:
   - Extraé el archivo `.zip`.
   - Copiá el archivo `msedgedriver.exe` extraído a la raíz del proyecto, donde está tu archivo `.py`.

4. **Recompilar el ejecutable**:
   - Abrí el proyecto en **Visual Studio Code**.
   - Abrí una terminal (integrada con `Ctrl + ñ` o desde el menú `Terminal > Nueva terminal`).
   - Ejecutá el siguiente comando para compilar nuevamente el ejecutable:
     ```bash
     pyinstaller --onefile --add-binary "msedgedriver.exe;." "nombre del archivo.py"
     ```
     > Reemplazá `NOMBRE_DEL_SCRIPT.py` por el nombre real de tu archivo Python, por ejemplo: `DM986-416AX30.py`.

5. **Ubicar el nuevo ejecutable**:
   - Luego de la compilación, se generarán nuevamente las carpetas `build/`, `dist/` y un archivo `.spec`.
   - Dentro de `dist/` vas a encontrar el nuevo ejecutable listo para usar con la versión actual de tu navegador Edge.

> 💬 Si elegís esta opción y necesitás ayuda para actualizar el driver o volver a compilar el ejecutable, podés ponerte en contacto conmigo.

---

## ⬇️ Cómo descargar el proyecto

1. Hacé clic en este enlace: [Descargar ZIP](https://github.com/LuisMiraglio/Script-DATACOM-DM986-416-AX30/archive/refs/heads/main.zip)
2. Extraé el archivo ZIP en tu computadora.
3. Entrá a la carpeta `dist/` y ejecutá el archivo **DATACOM_DM986-416AX30.exe**.

> No es necesario instalar nada adicional. Solo asegurate de tener la versión correcta de Microsoft Edge.

---

## 🛠️ Requisitos

- Sistema operativo: Windows 10 o superior
- Microsoft Edge versión 135.0.3179.85 (o compatible con el driver incluido)
- Acceso de administrador para ejecutar configuraciones en el módem

---

## 🧰 Tecnologías usadas

- Python 3
- Selenium
- PyInstaller
