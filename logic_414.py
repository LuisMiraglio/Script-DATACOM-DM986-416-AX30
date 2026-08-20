# logica para configurar Datacom DM986-414 via Selenium
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.firefox import GeckoDriverManager


# ============================================================
# INICIO BLOQUE AGREGADO - MANEJO DE ERRORES AMIGABLES
# ============================================================
class ErrorConexionEquipo(Exception):
    pass


class ErrorCredencialesEquipo(Exception):
    pass


class ErrorConfiguracionAmigable(Exception):
    pass


class ErrorInternetODriver(Exception):
    pass
# ============================================================
# FIN BLOQUE AGREGADO - MANEJO DE ERRORES AMIGABLES
# ============================================================


class ConfiguradorModem414:
    """
    Lógica específica Datacom DM986-414 (SIN UI).
    Se ejecuta desde main.py que provee 'ui' con métodos:

      ui.actualizar_estado(str)
      ui.get_browser_choice() -> "chrome" | "edge" | "firefox" | "auto"
      ui.get_credentials() -> dict:
          {"username","password","ssid","wpa","new_password"}
      ui.get_extra_wifi_config() -> dict:
          {
            "enabled": bool,
            "chanwid_5": "0|1|2",     # 20/40/80
            "chan_5": "0|36|40|44|48|149|153|157|161",   # 0 = Auto(DFS)
            "chanwid_24": "0|1",      # 20/40
            "chan_24": "0|5|6|7|8|9|10|11"               # 0 = Auto
          }
    """

    def __init__(self, ui):
        self.ui = ui
        self.driver = None

    # =========================
    # Helpers UI seguros
    # =========================
    def _status(self, msg: str):
        try:
            self.ui.actualizar_estado(msg)
        except Exception:
            print(msg)

    def _msgbox_error(self, title: str, text: str):
        fn = getattr(self.ui, "safe_messagebox", None)
        if callable(fn):
            fn(title, text, kind="error")
        else:
            self._status(f"{title}: {text}")

    # ============================================================
    # INICIO BLOQUE AGREGADO - HELPERS DE ERRORES
    # ============================================================
    def _abrir_login_seguro(self, url: str):
        try:
            self.driver.get(url)
        except WebDriverException as e:
            texto = str(e).upper()
            if (
                "ERR_CONNECTION_TIMED_OUT" in texto
                or "ERR_CONNECTION_REFUSED" in texto
                or "ERR_ADDRESS_UNREACHABLE" in texto
                or "ERR_NAME_NOT_RESOLVED" in texto
                or "ERR_INTERNET_DISCONNECTED" in texto
            ):
                raise ErrorConexionEquipo(
                    "No se pudo acceder al equipo.\n\n"
                    "Verificá que la PC esté conectada a la red Wi-Fi o LAN correcta del dispositivo "
                    "y que la IP 192.168.0.1 sea accesible."
                ) from e
            raise

    def _verificar_login_exitoso_414(self, timeout=15):
        d = self.driver
        try:
            return WebDriverWait(d, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//a[@rel='4' and normalize-space()='WAN']"))
            )
        except TimeoutException as e:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

            try:
                user_fields = d.find_elements(By.NAME, "username")
                pass_fields = d.find_elements(By.NAME, "password")

                if user_fields and pass_fields:
                    raise ErrorCredencialesEquipo(
                        "No se pudo iniciar sesión en el equipo.\n\n"
                        "Revisá que la contraseña ingresada sea correcta."
                    ) from e
            except ErrorCredencialesEquipo:
                raise
            except Exception:
                pass

            raise ErrorConfiguracionAmigable(
                "No se pudo cargar correctamente la interfaz del equipo después del login.\n\n"
                "Verificá la conexión con el dispositivo e intentá nuevamente."
            ) from e
    # ============================================================
    # FIN BLOQUE AGREGADO - HELPERS DE ERRORES
    # ============================================================

    # =========================
    # Driver
    # =========================
    def iniciar_navegador(self, navegador: str):
        try:
            if navegador == "chrome":
                options = ChromeOptions()
                options.add_argument("--ignore-certificate-errors")
                options.add_argument("--ignore-ssl-errors")
                options.add_argument("--disable-web-security")
                options.add_argument("--allow-running-insecure-content")
                return webdriver.Chrome(
                    service=ChromeService(ChromeDriverManager().install()),
                    options=options
                )

            if navegador == "edge":
                options = EdgeOptions()
                options.add_argument("--ignore-certificate-errors")
                options.add_argument("--ignore-ssl-errors")
                options.add_argument("--disable-web-security")
                options.add_argument("--allow-running-insecure-content")
                return webdriver.Edge(
                    service=EdgeService(EdgeChromiumDriverManager().install()),
                    options=options
                )

            if navegador == "firefox":
                options = FirefoxOptions()
                options.accept_insecure_certs = True
                return webdriver.Firefox(
                    service=FirefoxService(GeckoDriverManager().install()),
                    options=options
                )

            raise ValueError(f"Navegador inválido: {navegador}")

        except Exception as e:
            texto = str(e).lower()

            indicadores_internet_driver = [
                "connection",
                "connect",
                "internet",
                "network",
                "name resolution",
                "name or service not known",
                "could not reach host",
                "failed to establish a new connection",
                "max retries exceeded",
                "get_lan_ip",
                "ssl",
                "certificate",
                "webdriver_manager",
                "requests",
                "urlopen error",
                "timed out",
            ]

            if any(ind in texto for ind in indicadores_internet_driver):
                raise ErrorInternetODriver(
                    "No se pudo iniciar el navegador porque no hay conexión a Internet "
                    "o no se pudo descargar/verificar el driver necesario.\n\n"
                    "Verificá la conexión e intentá nuevamente."
                ) from e

            raise

    def autodetectar_navegador(self):
        for nav in ("chrome", "edge", "firefox"):
            try:
                self._status(f"Autodetectar: probando {nav}...")
                return self.iniciar_navegador(nav)
            except Exception:
                continue
        raise Exception("No se encontró ningún navegador compatible instalado.")

    # =========================
    # Selenium helpers
    # =========================
    def _click_safe(self, el):
        try:
            el.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", el)

    def _switch_to_content_iframe(self, timeout=20):
        """
        En 414 el iframe suele estar por NAME o ID.
        Probamos ambas.
        """
        d = self.driver
        d.switch_to.default_content()
        try:
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "contentIframe")))
            return
        except Exception:
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "contentIframe")))

    def _select_by_name_value(self, name: str, value: str, timeout=15):
        el = WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((By.NAME, name)))
        Select(el).select_by_value(str(value))

    # =========================
    # Entrada principal
    # =========================
    def run(self):
        try:
            browser = self.ui.get_browser_choice()
            creds = self.ui.get_credentials()
            extras = self._normalize_extras(self.ui.get_extra_wifi_config())

            self._status("Iniciando navegador...")
            if browser == "auto":
                self.driver = self.autodetectar_navegador()
            else:
                self.driver = self.iniciar_navegador(browser)

            self._status("Navegador inicializado.")
            self.configurar_modem(creds, extras)
            self._status("✅ Configuración DM986-414 completada.")
            return True

        # ============================================================
        # INICIO BLOQUE AGREGADO - CAPTURA DE ERRORES AMIGABLES
        # ============================================================
        except ErrorInternetODriver as e:
            self._msgbox_error("Sin conexión a Internet", str(e))
            return False

        except ErrorConexionEquipo as e:
            self._msgbox_error("Error de conexión", str(e))
            return False

        except ErrorCredencialesEquipo as e:
            self._msgbox_error("Contraseña incorrecta", str(e))
            return False

        except ErrorConfiguracionAmigable as e:
            self._msgbox_error("Error durante la configuración", str(e))
            return False
        # ============================================================
        # FIN BLOQUE AGREGADO - CAPTURA DE ERRORES AMIGABLES
        # ============================================================

        except Exception as e:
            self._msgbox_error(
                "Error durante la configuración (414)",
                "Ocurrió un error inesperado durante la configuración.\n\n"
                "La configuración fue detenida para evitar continuar con un equipo parcialmente configurado."
            )
            return False

        finally:
            # NO cerrar el navegador (modo debug)
            self._status("Navegador queda abierto (modo debug).")
            # no hacemos driver.quit()
            pass

    # =========================
    # Extras WLAN: defaults + validación
    # =========================
    def _normalize_extras(self, extras: dict) -> dict:
        """
        Defaults 414:
          - 5GHz width 80MHz -> "2"
          - 5GHz chan Auto(DFS) -> "0"
          - 2.4GHz width 20MHz -> "0"
          - 2.4GHz chan Auto -> "0"
        """
        if not isinstance(extras, dict):
            extras = {}

        enabled = bool(extras.get("enabled", False))

        out = {
            "enabled": enabled,
            "chanwid_5": extras.get("chanwid_5", "2"),
            "chan_5": extras.get("chan_5", "0"),
            "chanwid_24": extras.get("chanwid_24", "0"),
            "chan_24": extras.get("chan_24", "0"),
        }

        if not enabled:
            out["chanwid_5"] = "2"
            out["chan_5"] = "0"
            out["chanwid_24"] = "0"
            out["chan_24"] = "0"

        return out

    # =========================
    # Lógica del módem (TU FLUJO 414)
    # =========================
    def configurar_modem(self, creds: dict, extra: dict):
        d = self.driver
        wait = WebDriverWait(d, 25)

        username = creds["username"]
        password = creds["password"]
        ssid_name = creds["ssid"]
        wpa_password = creds["wpa"]
        new_password = creds["new_password"]

        # =========================
        # LOGIN (414)
        # =========================
        self._status("Accediendo al modem (414)...")

        # ============================================================
        # INICIO BLOQUE AGREGADO - APERTURA SEGURA DEL LOGIN
        # ============================================================
        self._abrir_login_seguro("http://192.168.0.1")
        # ============================================================
        # FIN BLOQUE AGREGADO - APERTURA SEGURA DEL LOGIN
        # ============================================================

        self._status("Ingresando credenciales...")
        user_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        pass_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        user_field.clear()
        user_field.send_keys(username)
        pass_field.clear()
        pass_field.send_keys(password)
        pass_field.send_keys(Keys.RETURN)

        # ============================================================
        # INICIO BLOQUE AGREGADO - VERIFICACIÓN DE LOGIN
        # ============================================================
        self._verificar_login_exitoso_414(timeout=15)
        # ============================================================
        # FIN BLOQUE AGREGADO - VERIFICACIÓN DE LOGIN
        # ============================================================

        # =========================
        # WAN - VLAN 500
        # =========================
        self._status("Configurando WAN VLAN 500...")
        wan_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@rel='4' and normalize-space()='WAN']")))
        self._click_safe(wan_btn)

        self._switch_to_content_iframe(timeout=20)

        vlan_checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@name='vlan' and @type='checkbox']")))
        # a veces ya viene tildado, evitamos toggle doble
        if not vlan_checkbox.is_selected():
            self._click_safe(vlan_checkbox)

        vid = wait.until(EC.presence_of_element_located((By.NAME, "vid")))
        vid.clear()
        vid.send_keys("500")

        # adslConnectionMode = 1
        adsl = wait.until(EC.presence_of_element_located((By.NAME, "adslConnectionMode")))
        Select(adsl).select_by_value("1")

        # ctype = 2 (Internet) como tu script original
        ctype = wait.until(EC.presence_of_element_located((By.NAME, "ctype")))
        Select(ctype).select_by_value("2")

        # ipMode DHCP = 1
        dhcp = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='radio' and @name='ipMode' and @value='1']")))
        self._click_safe(dhcp)

        chkpt_all = wait.until(EC.element_to_be_clickable((By.NAME, "chkpt_all")))
        self._click_safe(chkpt_all)

        apply_500 = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='apply' and @value='Apply Changes']")))
        self._click_safe(apply_500)
        time.sleep(4)

        # =========================
        # WAN - VLAN 600 NEW LINK (TR069)
        # =========================
        self._status("Configurando WAN VLAN 600 (New Link)...")
        d.switch_to.default_content()

        wan_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@rel='4' and normalize-space()='WAN']")))
        self._click_safe(wan_btn)
        time.sleep(1)

        self._switch_to_content_iframe(timeout=20)

        lkname = wait.until(EC.presence_of_element_located((By.NAME, "lkname")))
        found_new = False
        for opt in lkname.find_elements(By.TAG_NAME, "option"):
            if opt.get_attribute("value") == "new":
                self._click_safe(opt)
                found_new = True
                break
        if not found_new:
            raise Exception("No se encontró la opción 'new' en el selector lkname (New Link).")
        time.sleep(1)

        vlan_checkbox2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @name='vlan']")))
        if not vlan_checkbox2.is_selected():
            self._click_safe(vlan_checkbox2)

        vid2 = wait.until(EC.presence_of_element_located((By.NAME, "vid")))
        vid2.clear()
        vid2.send_keys("600")
        time.sleep(0.6)

        adsl2 = wait.until(EC.presence_of_element_located((By.NAME, "adslConnectionMode")))
        Select(adsl2).select_by_value("1")

        # ctype = 1 (TR069)
        ctype2 = wait.until(EC.presence_of_element_located((By.NAME, "ctype")))
        Select(ctype2).select_by_value("1")

        # ipMode DHCP = 1 (robusto con reintentos)
        self._status("Seleccionando DHCP en New Link...")
        dhcp_xpath = "//input[@type='radio' and @name='ipMode' and @value='1']"
        ok = False
        for _ in range(3):
            try:
                dhcp2 = WebDriverWait(d, 10).until(EC.element_to_be_clickable((By.XPATH, dhcp_xpath)))
                self._click_safe(dhcp2)
                ok = True
                break
            except Exception:
                time.sleep(0.7)
        if not ok:
            raise Exception("No se pudo seleccionar DHCP (ipMode=1) en el New Link (VLAN 600).")

        chkpt_all2 = wait.until(EC.element_to_be_clickable((By.NAME, "chkpt_all")))
        self._click_safe(chkpt_all2)
        time.sleep(0.4)
        try:
            self._click_safe(chkpt_all2)
        except Exception:
            pass
        time.sleep(0.6)

        apply_600 = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='apply' and @value='Apply Changes']")))
        self._click_safe(apply_600)
        time.sleep(4)

        # =========================
        # WLAN 5GHz
        # =========================
        self._status("Configurando WLAN 5GHz...")
        d.switch_to.default_content()

        wlan_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='nav']/li[3]/a")))
        self._click_safe(wlan_btn)

        self._switch_to_content_iframe(timeout=20)

        ssid = wait.until(EC.presence_of_element_located((By.NAME, "ssid")))
        ssid.clear()
        ssid.send_keys(ssid_name)
        time.sleep(0.5)

        # Extras 5GHz: name=chanwid, name=chan
        self._status("Aplicando Channel Width / Channel Number (5GHz)...")
        self._select_by_name_value("chanwid", extra["chanwid_5"], timeout=15)
        self._select_by_name_value("chan", extra["chan_5"], timeout=15)
        time.sleep(0.4)

        # txpower 0
        self._select_by_name_value("txpower", "0", timeout=15)

        apply_w5 = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']")))
        self._click_safe(apply_w5)
        time.sleep(4)

        # =========================
        # Seguridad 5GHz
        # =========================
        self._status("Configurando seguridad WiFi 5GHz...")
        d.switch_to.default_content()

        sec5 = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//a[@target='contentIframe' and contains(@href,'wlwpa.asp') and contains(@href,'wlan_idx=0')]"
        )))
        self._click_safe(sec5)

        self._switch_to_content_iframe(timeout=20)

        # security_method = 6 (como tu script)
        sec_method = wait.until(EC.presence_of_element_located((By.NAME, "security_method")))
        Select(sec_method).select_by_value("6")

        psk = wait.until(EC.presence_of_element_located((By.ID, "wpapsk")))
        psk.clear()
        psk.send_keys(wpa_password)

        apply_sec5 = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']")))
        self._click_safe(apply_sec5)
        time.sleep(4)

        # =========================
        # WLAN 2.4GHz
        # =========================
        self._status("Configurando WLAN 2.4GHz...")
        d.switch_to.default_content()

        wlan1_link = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[3]/div[2]/div[1]/div[1]/div/ul/li[2]/h3/a")))
        self._click_safe(wlan1_link)

        self._switch_to_content_iframe(timeout=20)

        ssid2 = wait.until(EC.presence_of_element_located((By.NAME, "ssid")))
        ssid2.clear()
        ssid2.send_keys(ssid_name)
        time.sleep(0.5)

        self._status("Aplicando Channel Width / Channel Number (2.4GHz)...")
        self._select_by_name_value("chanwid", extra["chanwid_24"], timeout=15)
        self._select_by_name_value("chan", extra["chan_24"], timeout=15)
        time.sleep(0.4)

        self._select_by_name_value("txpower", "0", timeout=15)

        apply_w24 = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']")))
        self._click_safe(apply_w24)
        time.sleep(4)

        # =========================
        # Seguridad 2.4GHz
        # =========================
        self._status("Configurando seguridad WiFi 2.4GHz...")
        d.switch_to.default_content()

        sec24 = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//a[@target='contentIframe' and contains(@href,'wlwpa.asp') and contains(@href,'wlan_idx=1')]"
        )))
        self._click_safe(sec24)

        self._switch_to_content_iframe(timeout=20)

        sec_method2 = wait.until(EC.presence_of_element_located((By.NAME, "security_method")))
        Select(sec_method2).select_by_value("6")

        psk2 = wait.until(EC.presence_of_element_located((By.ID, "wpapsk")))
        psk2.clear()
        psk2.send_keys(wpa_password)

        apply_sec24 = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']")))
        self._click_safe(apply_sec24)
        time.sleep(4)

        # =========================
        # Admin -> Password
        # =========================
        self._status("Cambiando contraseña de administrador...")
        d.switch_to.default_content()

        admin_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='javascript:void(0)' and @rel='9']")))
        self._click_safe(admin_link)

        pass_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@target='contentIframe' and @href='password.asp']")))
        self._click_safe(pass_link)

        self._switch_to_content_iframe(timeout=20)

        oldp = wait.until(EC.presence_of_element_located((By.NAME, "oldpass")))
        oldp.clear()
        oldp.send_keys(password)

        newp = wait.until(EC.presence_of_element_located((By.NAME, "newpass")))
        newp.clear()
        newp.send_keys(new_password)

        confp = wait.until(EC.presence_of_element_located((By.NAME, "confpass")))
        confp.clear()
        confp.send_keys(new_password)

        apply_pass = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']")))
        self._click_safe(apply_pass)
        time.sleep(4)

        # =========================
        # Admin -> TR-069
        # =========================
        self._status("Configurando TR-069...")
        d.switch_to.default_content()

        # aseguramos Admin tab
        try:
            admin_tab = WebDriverWait(d, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//ul[@id='nav']//a[@href='javascript:void(0)' and @rel='9' and normalize-space()='Admin']"))
            )
            self._click_safe(admin_tab)
        except Exception:
            self._click_safe(admin_link)

        side_menu = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.ID, "side")))
        tr069 = WebDriverWait(side_menu, 15).until(
            EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and contains(@href,'tr069config.asp')]"))
        )
        try:
            d.execute_script("arguments[0].scrollIntoView({block:'center'});", tr069)
        except Exception:
            pass
        self._click_safe(tr069)

        self._switch_to_content_iframe(timeout=20)

        url = wait.until(EC.presence_of_element_located((By.NAME, "url")))
        url.clear()
        url.send_keys("http://172.22.16.109:7995/")
        time.sleep(0.6)

        u = d.find_element(By.NAME, "username")
        u.clear()
        u.send_keys("admin")

        p = d.find_element(By.NAME, "password")
        p.clear()
        p.send_keys("admin")

        crn = d.find_element(By.NAME, "conreqname")
        crn.clear()
        crn.send_keys("admin")

        crp = d.find_element(By.NAME, "conreqpw")
        crp.clear()
        crp.send_keys("admin")

        apply_tr = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//input[@type='submit' and @name='save' and (@value='Apply' or @value='Apply Changes')]"
        )))
        self._click_safe(apply_tr)
        time.sleep(3)

        try:
            WebDriverWait(d, 3).until(EC.alert_is_present())
            d.switch_to.alert.accept()
        except Exception:
            pass

        # =========================
        # Advance -> Remote Access
        # =========================
        self._status("Configurando Remote Access (HTTPS)...")
        d.switch_to.default_content()

        advance = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='javascript:void(0)' and @rel='7']")))
        self._click_safe(advance)

        remote = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@target='contentIframe' and @href='rmtacc.asp']")))
        self._click_safe(remote)

        self._switch_to_content_iframe(timeout=20)

        https = wait.until(EC.element_to_be_clickable((By.NAME, "w_https")))
        if not https.is_selected():
            self._click_safe(https)

        apply_remote = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='set' and @value='Apply Changes']")))
        self._click_safe(apply_remote)

        self._status("Listo. El modem 414 debería quedar configurado.")