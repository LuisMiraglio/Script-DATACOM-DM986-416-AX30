# logica para configurar Datacom DM986-414 Q via Selenium
import time
import base64

from selenium import webdriver
from selenium.webdriver.common.by import By
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


class ConfiguradorModem414Q:
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

    def _verificar_login_exitoso(self, timeout=15):
        d = self.driver
        try:
            return WebDriverWait(d, timeout).until(
                EC.presence_of_element_located((By.ID, "nav"))
            )
        except TimeoutException as e:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

            try:
                iframes = d.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    try:
                        d.switch_to.frame(iframes[0])
                    except Exception:
                        pass

                user_fields = d.find_elements(By.NAME, "username")
                pass_fields = d.find_elements(By.NAME, "password")
                login_buttons = d.find_elements(By.XPATH, "//input[@type='submit' and @value='Login']")

                if user_fields and pass_fields and login_buttons:
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

    def _switch_to_first_iframe_if_present(self):
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            self.driver.switch_to.frame(iframes[0])

    def _switch_to_content_iframe(self, timeout=15):
        d = self.driver
        d.switch_to.default_content()
        WebDriverWait(d, timeout).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "contentIframe"))
        )

    def _select_value_by_name(self, name: str, value: str, timeout=15):
        el = WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.NAME, name))
        )
        Select(el).select_by_value(str(value))

    # =========================
    # Entrada principal
    # =========================
    def run(self):
        try:
            browser = self.ui.get_browser_choice()
            creds = self.ui.get_credentials()

            self._status("Iniciando navegador...")
            if browser == "auto":
                self.driver = self.autodetectar_navegador()
            else:
                self.driver = self.iniciar_navegador(browser)

            self._status("Navegador inicializado.")
            self.configurar_modem(creds)
            self._status("✅ Configuración DM986-414 Q completada.")
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
                "Error durante la configuración (414 Q)",
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
    # Lógica del módem (TU FLUJO)
    # =========================
    def configurar_modem(self, creds: dict):
        d = self.driver
        WebDriverWait(d, 20)

        username = creds["username"]
        password = creds["password"]
        ssid_name = creds["ssid"]
        wpa_password = creds["wpa"]
        new_password = creds["new_password"]

        # =========================
        # LOGIN (414 Q)
        # =========================
        self._status("Accediendo a login del modem (414 Q)...")

        # ============================================================
        # INICIO BLOQUE AGREGADO - APERTURA SEGURA DEL LOGIN
        # ============================================================
        self._abrir_login_seguro("https://192.168.0.1/admin/login.asp")
        # ============================================================
        # FIN BLOQUE AGREGADO - APERTURA SEGURA DEL LOGIN
        # ============================================================

        time.sleep(2)

        self._switch_to_first_iframe_if_present()

        self._status("Completando credenciales...")
        user_field = WebDriverWait(d, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        user_field.clear()
        user_field.send_keys(username)

        pass_field = d.find_element(By.NAME, "password")
        pass_field.clear()
        pass_field.send_keys(password)

        encoded_password = base64.b64encode(password.encode("utf-8")).decode("utf-8")
        d.execute_script(
            """
            document.getElementsByName('encodePassword')[0].value = arguments[0];
            document.getElementsByName('password')[0].disabled = true;
            """,
            encoded_password
        )

        login_btn = d.find_element(By.XPATH, "//input[@type='submit' and @value='Login']")
        self._click_safe(login_btn)

        self._status("Esperando interfaz del modem...")

        # ============================================================
        # INICIO BLOQUE AGREGADO - VERIFICACIÓN DE LOGIN
        # ============================================================
        nav_menu = self._verificar_login_exitoso(timeout=15)
        # ============================================================
        # FIN BLOQUE AGREGADO - VERIFICACIÓN DE LOGIN
        # ============================================================

        # =========================
        # WAN - VLAN 500
        # =========================
        self._status("Configurando WAN VLAN 500...")
        wan_link = nav_menu.find_element(By.XPATH, ".//a[@rel='4' and normalize-space()='WAN']")
        self._click_safe(wan_link)

        self._switch_to_content_iframe(timeout=15)

        vlan_checkbox = WebDriverWait(d, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @name='vlan']"))
        )
        if not vlan_checkbox.is_selected():
            self._click_safe(vlan_checkbox)
        time.sleep(1)

        vid_input = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.NAME, "vid")))
        vid_input.clear()
        vid_input.send_keys("500")
        time.sleep(1)

        adsl_sel = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.NAME, "adslConnectionMode")))
        for opt in adsl_sel.find_elements(By.TAG_NAME, "option"):
            if opt.get_attribute("value") == "1":
                self._click_safe(opt)
                break
        time.sleep(1)

        ctype_sel_500 = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.NAME, "ctype")))
        found_ctype2 = False
        for opt in ctype_sel_500.find_elements(By.TAG_NAME, "option"):
            if opt.get_attribute("value") == "2":
                self._click_safe(opt)
                found_ctype2 = True
                break
        if not found_ctype2:
            raise Exception("No se encontró la opción ctype=2 (Internet) en VLAN 500.")
        time.sleep(1)

        dhcp_500 = WebDriverWait(d, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='radio' and @name='ipMode' and @value='1']"))
        )
        self._click_safe(dhcp_500)
        time.sleep(1)

        chkpt_all = WebDriverWait(d, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@name='chkpt_all']"))
        )
        self._click_safe(chkpt_all)
        time.sleep(1)

        apply_500 = WebDriverWait(d, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='apply' and @value='Apply Changes']"))
        )
        self._click_safe(apply_500)
        time.sleep(3)

        d.switch_to.default_content()

        # =========================
        # WAN - NEW LINK VLAN 600 (TR069) + DHCP
        # =========================
        self._status("Configurando WAN VLAN 600 (New Link / TR069)...")
        nav_menu = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.ID, "nav")))
        wan_link = nav_menu.find_element(By.XPATH, ".//a[@rel='4' and normalize-space()='WAN']")
        self._click_safe(wan_link)
        time.sleep(1)

        self._switch_to_content_iframe(timeout=15)

        lkname_select = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.NAME, "lkname")))
        found_new = False
        for opt in lkname_select.find_elements(By.TAG_NAME, "option"):
            if opt.get_attribute("value") == "new":
                self._click_safe(opt)
                found_new = True
                break
        if not found_new:
            raise Exception("No se encontró la opción 'new' en lkname (New Link).")
        time.sleep(1)

        vlan_checkbox_new = WebDriverWait(d, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @name='vlan']"))
        )
        if not vlan_checkbox_new.is_selected():
            self._click_safe(vlan_checkbox_new)
        time.sleep(1)

        vid_input_new = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.NAME, "vid")))
        vid_input_new.clear()
        vid_input_new.send_keys("600")
        time.sleep(1)

        adsl_new = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.NAME, "adslConnectionMode")))
        for opt in adsl_new.find_elements(By.TAG_NAME, "option"):
            if opt.get_attribute("value") == "1":
                self._click_safe(opt)
                break
        time.sleep(1)

        ctype_sel = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.NAME, "ctype")))
        for opt in ctype_sel.find_elements(By.TAG_NAME, "option"):
            if opt.get_attribute("value") == "1":
                self._click_safe(opt)
                break
        time.sleep(1)

        dhcp_radio = WebDriverWait(d, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='radio' and @name='ipMode' and @value='1']"))
        )
        self._click_safe(dhcp_radio)
        time.sleep(1)

        chkpt_all_2 = WebDriverWait(d, 10).until(EC.element_to_be_clickable((By.NAME, "chkpt_all")))
        self._click_safe(chkpt_all_2)
        time.sleep(1)
        try:
            self._click_safe(chkpt_all_2)
        except Exception:
            pass
        time.sleep(1)

        apply_600 = WebDriverWait(d, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='apply' and @value='Apply Changes']"))
        )
        self._click_safe(apply_600)
        time.sleep(3)

        # =========================
        # WLAN 5GHz (414Q) - HARDCODE
        # =========================
        d.switch_to.default_content()

        self._status("Abriendo WLAN (5GHz)...")
        nav_menu = WebDriverWait(d, 20).until(EC.presence_of_element_located((By.ID, "nav")))

        wlan_link = WebDriverWait(nav_menu, 20).until(
            EC.element_to_be_clickable((By.XPATH, ".//a[@rel='3' and normalize-space()='WLAN']"))
        )
        self._click_safe(wlan_link)

        self._switch_to_content_iframe(timeout=20)

        ssid_input = WebDriverWait(d, 20).until(EC.presence_of_element_located((By.NAME, "ssid")))
        ssid_input.clear()
        ssid_input.send_keys(ssid_name)
        time.sleep(2)

        self._status("Aplicando Channel Width / Channel Number (5GHz)...")
        chanwid_el = WebDriverWait(d, 20).until(EC.presence_of_element_located((By.NAME, "chanwid")))
        Select(chanwid_el).select_by_value("2")  # 80MHz

        chan_el = WebDriverWait(d, 20).until(EC.presence_of_element_located((By.NAME, "chan")))
        Select(chan_el).select_by_value("36")

        try:
            self._select_value_by_name("txpower", "0", timeout=10)
        except Exception:
            pass

        apply_btn = WebDriverWait(d, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
        )
        self._click_safe(apply_btn)
        time.sleep(3)

        # =========================
        # Seguridad 5GHz
        # =========================
        d.switch_to.default_content()
        self._status("Configurando seguridad WiFi 5GHz...")
        side_menu = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.ID, "side")))

        sec_5 = WebDriverWait(side_menu, 10).until(
            EC.element_to_be_clickable((By.XPATH, ".//a[contains(@href,'/wlwpa.asp') and contains(@href,'wlan_idx=0')]"))
        )
        self._click_safe(sec_5)
        time.sleep(1)

        self._switch_to_content_iframe(timeout=15)

        sec_method = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.ID, "security_method")))
        Select(sec_method).select_by_value("6")  # WPA2 Mixed
        try:
            d.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", sec_method)
        except Exception:
            pass
        time.sleep(1)

        psk_5 = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.ID, "wpapsk")))
        psk_5.clear()
        psk_5.send_keys(wpa_password)
        time.sleep(1)

        apply_sec5 = WebDriverWait(d, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
        )
        self._click_safe(apply_sec5)
        time.sleep(3)

        # =========================
        # WLAN 2.4GHz - HARDCODE
        # =========================
        d.switch_to.default_content()
        self._status("Configurando WiFi 2.4GHz...")
        side_menu = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.ID, "side")))

        wlan1_header = WebDriverWait(side_menu, 10).until(
            EC.element_to_be_clickable((By.XPATH, ".//h3/a[normalize-space()='wlan1 (2.4GHz)']"))
        )
        self._click_safe(wlan1_header)
        time.sleep(1)

        self._switch_to_content_iframe(timeout=15)

        ssid_24 = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.NAME, "ssid")))
        ssid_24.clear()
        ssid_24.send_keys(ssid_name)
        time.sleep(1)

        self._status("Aplicando Channel Width / Channel Number (2.4GHz)...")
        self._select_value_by_name("chanwid", "0", timeout=10)  # 20MHz
        self._select_value_by_name("chan", "0", timeout=10)     # Auto
        time.sleep(1)

        self._select_value_by_name("txpower", "0", timeout=10)
        time.sleep(1)

        apply_wifi24 = WebDriverWait(d, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
        )
        self._click_safe(apply_wifi24)
        time.sleep(3)

        # =========================
        # Seguridad 2.4GHz
        # =========================
        d.switch_to.default_content()
        self._status("Configurando seguridad WiFi 2.4GHz...")
        side_menu = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.ID, "side")))

        sec_24 = WebDriverWait(side_menu, 10).until(
            EC.element_to_be_clickable((By.XPATH, ".//a[contains(@href,'/wlwpa.asp') and contains(@href,'wlan_idx=1')]"))
        )
        self._click_safe(sec_24)
        time.sleep(1)

        self._switch_to_content_iframe(timeout=15)

        sec_method_24 = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.ID, "security_method")))
        Select(sec_method_24).select_by_value("6")  # WPA2 Mixed
        try:
            d.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", sec_method_24)
        except Exception:
            pass
        time.sleep(1)

        psk_24 = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.ID, "wpapsk")))
        psk_24.clear()
        psk_24.send_keys(wpa_password)
        time.sleep(2)

        apply_sec24 = WebDriverWait(d, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
        )
        self._click_safe(apply_sec24)
        time.sleep(3)

        # =========================
        # Admin -> Password
        # =========================
        d.switch_to.default_content()
        self._status("Cambiando contraseña de administrador...")
        admin_tab = WebDriverWait(d, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='javascript:void(0)' and @rel='9']"))
        )
        self._click_safe(admin_tab)

        side_menu = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.ID, "side")))
        password_link = WebDriverWait(side_menu, 10).until(
            EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and @href='password.asp']"))
        )
        self._click_safe(password_link)

        self._switch_to_content_iframe(timeout=15)

        old_pass = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.NAME, "oldpass")))
        old_pass.clear()
        old_pass.send_keys(password)

        new_pass = d.find_element(By.NAME, "newpass")
        new_pass.clear()
        new_pass.send_keys(new_password)

        conf_pass = d.find_element(By.NAME, "confpass")
        conf_pass.clear()
        conf_pass.send_keys(new_password)

        apply_pass = WebDriverWait(d, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
        )
        self._click_safe(apply_pass)
        time.sleep(5)

        # =========================
        # Admin -> TR-069
        # =========================
        d.switch_to.default_content()
        self._status("Configurando TR-069...")

        admin_tab2 = WebDriverWait(d, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//ul[@id='nav']//a[@href='javascript:void(0)' and @rel='9' and normalize-space()='Admin']"))
        )
        self._click_safe(admin_tab2)

        side_menu = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.ID, "side")))
        tr069_link = WebDriverWait(side_menu, 15).until(
            EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and contains(@href,'tr069config.asp')]"))
        )
        try:
            d.execute_script("arguments[0].scrollIntoView({block:'center'});", tr069_link)
        except Exception:
            pass
        self._click_safe(tr069_link)

        self._switch_to_content_iframe(timeout=15)

        url_input = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.NAME, "url")))
        url_input.clear()
        url_input.send_keys("http://172.22.16.109:7995/")
        time.sleep(2)

        u = d.find_element(By.NAME, "username")
        u.clear()
        u.send_keys("admin")

        p = d.find_element(By.NAME, "password")
        p.clear()
        p.send_keys("admin")

        conreqname = d.find_element(By.NAME, "conreqname")
        conreqname.clear()
        conreqname.send_keys("admin")

        conreqpw = d.find_element(By.NAME, "conreqpw")
        conreqpw.clear()
        conreqpw.send_keys("admin")

        apply_tr = WebDriverWait(d, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and (@value='Apply' or @value='Apply Changes')]"))
        )
        self._click_safe(apply_tr)
        time.sleep(5)

        try:
            WebDriverWait(d, 3).until(EC.alert_is_present())
            d.switch_to.alert.accept()
        except Exception:
            pass

        # =========================
        # Advance -> Remote Access
        # =========================
        d.switch_to.default_content()
        self._status("Configurando Remote Access (HTTPS)...")
        nav_menu = WebDriverWait(d, 20).until(EC.presence_of_element_located((By.ID, "nav")))

        advance_tab = WebDriverWait(nav_menu, 15).until(
            EC.element_to_be_clickable((By.XPATH, ".//a[@href='javascript:void(0)' and @rel='7' and normalize-space()='Advance']"))
        )
        try:
            d.execute_script("arguments[0].scrollIntoView({block:'center'});", advance_tab)
        except Exception:
            pass
        self._click_safe(advance_tab)

        side_menu = WebDriverWait(d, 20).until(EC.presence_of_element_located((By.ID, "side")))
        remote_link = WebDriverWait(side_menu, 15).until(
            EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and @href='rmtacc.asp' and normalize-space()='Remote Access']"))
        )
        try:
            d.execute_script("arguments[0].scrollIntoView({block:'center'});", remote_link)
        except Exception:
            pass
        self._click_safe(remote_link)

        self._switch_to_content_iframe(timeout=15)

        https_checkbox = WebDriverWait(d, 15).until(EC.element_to_be_clickable((By.NAME, "w_https")))
        if not https_checkbox.is_selected():
            self._click_safe(https_checkbox)

        apply_remote = WebDriverWait(d, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='set' and @value='Apply Changes']"))
        )
        self._click_safe(apply_remote)

        self._status("Listo. El modem debería quedar configurado.")

        # =========================
        # Admin -> OMCI Information (DESPUÉS de Remote Access), Este bloque se uso para este modelo en especifico porqye no venian configurados para la OLT ZHONE, queda comentado por si en elguna ocacion se tiene que volver a usar
        # =========================
        """d.switch_to.default_content()
        self._status("Abriendo Admin -> OMCI Information...")

        nav_menu = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.ID, "nav")))
        admin_tab3 = WebDriverWait(nav_menu, 15).until(
            EC.element_to_be_clickable((By.XPATH, ".//a[@href='javascript:void(0)' and @rel='9' and normalize-space()='Admin']"))
        )
        self._click_safe(admin_tab3)
        time.sleep(2)

        side_menu = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.ID, "side")))
        omci_link = WebDriverWait(side_menu, 15).until(
            EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and @href='omci_info.asp' and normalize-space()='OMCI Information']"))
        )
        self._click_safe(omci_link)
        time.sleep(2)

        self._switch_to_content_iframe(timeout=15)
        time.sleep(2)

        self._status("Configurando OMCI Vendor ID...")
        omci_vendor = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.NAME, "omci_vendor_id")))
        omci_vendor.clear()
        omci_vendor.send_keys("ZNTS")
        time.sleep(2)

        apply_omci = WebDriverWait(d, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='apply' and @value='Apply Changes']"))
        )
        self._click_safe(apply_omci)
        time.sleep(1)

        for _ in range(2):
            try:
                WebDriverWait(d, 4).until(EC.alert_is_present())
                d.switch_to.alert.accept()
                time.sleep(0.5)
            except Exception:
                break

        self._status("Reinicio detectado. Esperando a que el equipo vuelva (hasta 2 min)...")

        t_end = time.time() + 120
        while time.time() < t_end:
            try:
                d.get("https://192.168.0.1/admin/login.asp")
                WebDriverWait(d, 5).until(EC.presence_of_element_located((By.NAME, "username")))
                self._status("✅ El equipo volvió (login visible).")
                break
            except Exception:
                time.sleep(5)
        else:
            self._status("⚠️ Pasaron 2 minutos y no volvió el login todavía.")"""