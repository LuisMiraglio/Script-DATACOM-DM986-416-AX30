# Configurador Automático Datacom DM986

Aplicación interna en Python + Selenium para automatizar la configuración de ONUs/routers Datacom DM986.

## Modelos soportados

- DM986-416 AX30
- DM986-414
- DM986-414 Q

El AX30 incluye validación paso a paso de VLAN, Wi-Fi, seguridad, contraseña de administrador, TR-069 y Remote Access HTTPS. Los modelos 414 y 414 Q continúan con sus flujos actuales y se irán llevando al mismo esquema de validación durante las pruebas con equipos físicos.

## Estructura

```text
.
├── main.py
├── logic_416.py
├── logic_414.py
├── logic_414Q.py
├── assets/
│   └── icons/
│       └── icono.ico
├── Configurador Datacom.spec
├── requirements.txt
├── requirements-build.txt
├── setup.bat
├── run.bat
├── build.bat
├── clean.bat
├── .gitignore
└── README.md
```

No se incluyen ni se versionan `venv/`, `build/`, `dist/`, `__pycache__/`, logs ni carpetas de backup.

## Preparar el proyecto por primera vez

En Windows, desde la carpeta del proyecto:

```bat
setup.bat
```

El script crea `venv`, actualiza pip e instala Selenium, webdriver-manager y PyInstaller.

> El proyecto está preparado para Python 3.13, que es la versión usada actualmente.

## Ejecutar en desarrollo

```bat
run.bat
```

O manualmente:

```powershell
.\venv\Scripts\Activate.ps1
python main.py
```

## Compilar el EXE

La forma recomendada es:

```bat
build.bat
```

`build.bat`:

1. verifica que exista el entorno virtual;
2. elimina `build/` y `dist/` anteriores;
3. compila usando `Configurador Datacom.spec`;
4. verifica que se haya creado el ejecutable.

Resultado:

```text
dist\Configurador Datacom.exe
```

Ya no es necesario copiar y pegar el comando largo de PyInstaller en PowerShell.

## Limpiar archivos generados

```bat
clean.bat
```

Elimina `build/`, `dist/` y cachés `__pycache__`.

## Navegadores

La aplicación soporta:

- Google Chrome
- Microsoft Edge
- Mozilla Firefox
- Autodetección

Chrome es la opción recomendada.

## Notas

- El equipo debe ser accesible en `192.168.0.1`.
- La PC debe estar conectada correctamente al equipo por LAN/Wi-Fi según el flujo de trabajo.
- El proyecto no guarda backups automáticos ni logs técnicos en archivos locales.
- El navegador queda abierto al finalizar para permitir una verificación visual cuando corresponda.
