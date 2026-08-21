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
from selenium.common.exceptions import TimeoutException, WebDriverException, UnexpectedAlertPresentException

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


class ErrorVerificacionConfiguracion(Exception):
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

    # ============================================================
    # INICIO BLOQUE AGREGADO - VERIFICACIÓN VLAN 500 / VLAN 600
    # ============================================================
    def _abrir_wan(self, timeout=20):
        d = self.driver
        d.switch_to.default_content()

        wan_btn = WebDriverWait(d, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@rel='4' and normalize-space()='WAN']"))
        )
        self._click_safe(wan_btn)

        self._switch_to_content_iframe(timeout=timeout)

        WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.NAME, "vid"))
        )

    def _leer_estado_wan_actual(self):
        d = self.driver

        vlan = d.find_element(By.NAME, "vlan")
        vid = d.find_element(By.NAME, "vid")
        adsl = d.find_element(By.NAME, "adslConnectionMode")
        ctype = d.find_element(By.NAME, "ctype")
        dhcp = d.find_element(
            By.XPATH,
            "//input[@type='radio' and @name='ipMode' and @value='1']"
        )

        return {
            "vlan": vlan.is_selected(),
            "vid": (vid.get_attribute("value") or "").strip(),
            "adslConnectionMode": Select(adsl).first_selected_option.get_attribute("value"),
            "ctype": Select(ctype).first_selected_option.get_attribute("value"),
            "dhcp": dhcp.is_selected(),
        }

    def _esperar_wan_objetivo(self, vid_objetivo: str, ctype_objetivo: str, timeout=20):
        def _estado_correcto(_driver):
            try:
                estado = self._leer_estado_wan_actual()
                return (
                    estado["vlan"] is True
                    and estado["vid"] == str(vid_objetivo)
                    and estado["adslConnectionMode"] == "1"
                    and estado["ctype"] == str(ctype_objetivo)
                    and estado["dhcp"] is True
                )
            except Exception:
                return False

        try:
            WebDriverWait(self.driver, timeout).until(_estado_correcto)
            return True
        except TimeoutException:
            return False

    def _buscar_vlan_en_links(self, vid_objetivo: str, ctype_objetivo: str, timeout=20):
        d = self.driver

        try:
            lkname = WebDriverWait(d, timeout).until(
                EC.presence_of_element_located((By.NAME, "lkname"))
            )
        except TimeoutException:
            return False

        valores = [
            opt.get_attribute("value")
            for opt in lkname.find_elements(By.TAG_NAME, "option")
        ]

        for valor in valores:
            if not valor or valor == "new":
                continue

            try:
                lkname = WebDriverWait(d, timeout).until(
                    EC.presence_of_element_located((By.NAME, "lkname"))
                )
                Select(lkname).select_by_value(valor)

                if self._esperar_wan_objetivo(
                    vid_objetivo,
                    ctype_objetivo,
                    timeout=3
                ):
                    return True
            except Exception:
                continue

        return False

    def _detectar_alerta_vlan(self, vid_objetivo: str, timeout=2):
        try:
            WebDriverWait(self.driver, timeout).until(EC.alert_is_present())
        except TimeoutException:
            return

        try:
            alerta = self.driver.switch_to.alert
            texto_alerta = (alerta.text or "").strip()
            alerta.accept()
        except Exception:
            texto_alerta = "El equipo rechazó la configuración."

        self._status(f"❌ VLAN {vid_objetivo} no pudo aplicarse correctamente.")

        raise ErrorVerificacionConfiguracion(
            f"La VLAN {vid_objetivo} no pudo aplicarse correctamente.\n\n"
            f"El equipo informó: {texto_alerta}\n\n"
            "La configuración fue detenida para evitar continuar con un equipo "
            "parcialmente configurado."
        )

    def _verificar_vlan_persistida(self, vid_objetivo: str, ctype_objetivo: str):
        self._status(f"Verificando VLAN {vid_objetivo}...")

        self._detectar_alerta_vlan(vid_objetivo, timeout=2)

        try:
            self._abrir_wan(timeout=20)
        except UnexpectedAlertPresentException:
            self._detectar_alerta_vlan(vid_objetivo, timeout=2)
            raise ErrorVerificacionConfiguracion(
                f"La VLAN {vid_objetivo} no pudo verificarse correctamente."
            )

        if self._esperar_wan_objetivo(
            vid_objetivo,
            ctype_objetivo,
            timeout=5
        ):
            self._status(f"✅ VLAN {vid_objetivo} configurada y verificada.")
            return

        if self._buscar_vlan_en_links(
            vid_objetivo,
            ctype_objetivo,
            timeout=15
        ):
            self._status(f"✅ VLAN {vid_objetivo} configurada y verificada.")
            return

        self._status(f"❌ VLAN {vid_objetivo} no quedó guardada correctamente.")

        raise ErrorVerificacionConfiguracion(
            f"La VLAN {vid_objetivo} no quedó guardada correctamente.\n\n"
            "La configuración fue detenida para evitar continuar con un equipo "
            "parcialmente configurado."
        )
    # ============================================================
    # FIN BLOQUE AGREGADO - VERIFICACIÓN VLAN 500 / VLAN 600
    # ============================================================

    # ============================================================
    # INICIO BLOQUE AGREGADO - VERIFICACIÓN WIFI 5 GHZ
    # ============================================================
    def _abrir_wlan_5ghz(self, timeout=20):
        d = self.driver
        d.switch_to.default_content()

        wlan_btn = WebDriverWait(d, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='nav']/li[3]/a"))
        )
        self._click_safe(wlan_btn)

        self._switch_to_content_iframe(timeout=timeout)

        WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.NAME, "ssid"))
        )

    def _leer_estado_wlan_5ghz(self):
        d = self.driver

        ssid = d.find_element(By.NAME, "ssid")
        chanwid = d.find_element(By.NAME, "chanwid")
        chan = d.find_element(By.NAME, "chan")

        estado = {
            "ssid": (ssid.get_attribute("value") or "").strip(),
            "chanwid": Select(chanwid).first_selected_option.get_attribute("value"),
            "chan": Select(chan).first_selected_option.get_attribute("value"),
            "txpower": None,
        }

        txpower = d.find_elements(By.NAME, "txpower")
        if txpower:
            estado["txpower"] = Select(txpower[0]).first_selected_option.get_attribute("value")

        return estado

    def _detectar_alerta_wifi(self, nombre_bloque: str, timeout=2):
        try:
            WebDriverWait(self.driver, timeout).until(EC.alert_is_present())
        except TimeoutException:
            return

        try:
            alerta = self.driver.switch_to.alert
            texto_alerta = (alerta.text or "").strip()
            alerta.accept()
        except Exception:
            texto_alerta = "El equipo rechazó la configuración."

        self._status(f"❌ {nombre_bloque} no pudo aplicarse correctamente.")

        raise ErrorVerificacionConfiguracion(
            f"{nombre_bloque} no pudo aplicarse correctamente.\n\n"
            f"El equipo informó: {texto_alerta}\n\n"
            "La configuración fue detenida para evitar continuar con un equipo "
            "parcialmente configurado."
        )

    def _verificar_wifi_5ghz_persistido(
        self,
        ssid_objetivo: str,
        chanwid_objetivo: str,
        chan_objetivo: str
    ):
        self._status("Verificando WiFi 5 GHz...")

        self._detectar_alerta_wifi("WiFi 5 GHz", timeout=2)

        try:
            self._abrir_wlan_5ghz(timeout=20)
        except UnexpectedAlertPresentException:
            self._detectar_alerta_wifi("WiFi 5 GHz", timeout=2)
            raise ErrorVerificacionConfiguracion(
                "WiFi 5 GHz no pudo verificarse correctamente."
            )

        estado = self._leer_estado_wlan_5ghz()

        txpower_ok = (
            estado["txpower"] is None
            or estado["txpower"] == "0"
        )

        if not (
            estado["ssid"] == ssid_objetivo
            and estado["chanwid"] == str(chanwid_objetivo)
            and estado["chan"] == str(chan_objetivo)
            and txpower_ok
        ):
            self._status("❌ WiFi 5 GHz no quedó guardado correctamente.")

            raise ErrorVerificacionConfiguracion(
                "La configuración WiFi 5 GHz no quedó guardada correctamente.\n\n"
                "Valores detectados:\n"
                f"- SSID: {estado['ssid']}\n"
                f"- Channel Width: {estado['chanwid']}\n"
                f"- Channel: {estado['chan']}\n"
                f"- TX Power: {estado['txpower'] if estado['txpower'] is not None else 'No disponible'}\n\n"
                "Valores esperados:\n"
                f"- SSID: {ssid_objetivo}\n"
                f"- Channel Width: {chanwid_objetivo}\n"
                f"- Channel: {chan_objetivo}\n"
                "- TX Power: 0\n\n"
                "La configuración fue detenida para evitar continuar con un equipo "
                "parcialmente configurado."
            )

        self._status("✅ WiFi 5 GHz configurado y verificado.")
    # ============================================================
    # FIN BLOQUE AGREGADO - VERIFICACIÓN WIFI 5 GHZ
    # ============================================================

    # ============================================================
    # INICIO BLOQUE AGREGADO - VERIFICACIÓN SEGURIDAD WIFI 5 GHZ
    # ============================================================
    def _abrir_seguridad_5ghz(self, timeout=20):
        d = self.driver
        d.switch_to.default_content()

        sec5 = WebDriverWait(d, timeout).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//a[@target='contentIframe' and contains(@href,'wlwpa.asp') and contains(@href,'wlan_idx=0')]"
            ))
        )
        self._click_safe(sec5)

        self._switch_to_content_iframe(timeout=timeout)

        WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.NAME, "security_method"))
        )

    def _verificar_seguridad_5ghz_persistida(self):
        self._status("Verificando seguridad WiFi 5 GHz...")

        self._detectar_alerta_wifi("Seguridad WiFi 5 GHz", timeout=2)

        try:
            self._abrir_seguridad_5ghz(timeout=20)
        except UnexpectedAlertPresentException:
            self._detectar_alerta_wifi("Seguridad WiFi 5 GHz", timeout=2)
            raise ErrorVerificacionConfiguracion(
                "La seguridad WiFi 5 GHz no pudo verificarse correctamente."
            )

        sec_method = self.driver.find_element(By.NAME, "security_method")
        valor = Select(sec_method).first_selected_option.get_attribute("value")

        if valor != "6":
            self._status("❌ Seguridad WiFi 5 GHz no quedó guardada correctamente.")

            raise ErrorVerificacionConfiguracion(
                "La seguridad WiFi 5 GHz no quedó guardada correctamente.\n\n"
                f"Valor detectado: {valor}\n"
                "Valor esperado: 6\n\n"
                "La configuración fue detenida para evitar continuar con un equipo "
                "parcialmente configurado."
            )

        self._status("✅ Seguridad WiFi 5 GHz configurada y verificada.")
    # ============================================================
    # FIN BLOQUE AGREGADO - VERIFICACIÓN SEGURIDAD WIFI 5 GHZ
    # ============================================================

    # ============================================================
    # INICIO BLOQUE AGREGADO - VERIFICACIÓN WIFI 2.4 GHZ
    # ============================================================
    def _abrir_wlan_24ghz(self, timeout=20):
        d = self.driver
        d.switch_to.default_content()

        wlan1_link = WebDriverWait(d, timeout).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "/html/body/div[3]/div[2]/div[1]/div[1]/div/ul/li[2]/h3/a"
            ))
        )
        self._click_safe(wlan1_link)

        self._switch_to_content_iframe(timeout=timeout)

        WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.NAME, "ssid"))
        )

    def _leer_estado_wlan_24ghz(self):
        d = self.driver

        ssid = d.find_element(By.NAME, "ssid")
        chanwid = d.find_element(By.NAME, "chanwid")
        chan = d.find_element(By.NAME, "chan")

        estado = {
            "ssid": (ssid.get_attribute("value") or "").strip(),
            "chanwid": Select(chanwid).first_selected_option.get_attribute("value"),
            "chan": Select(chan).first_selected_option.get_attribute("value"),
            "txpower": None,
        }

        txpower = d.find_elements(By.NAME, "txpower")
        if txpower:
            estado["txpower"] = Select(txpower[0]).first_selected_option.get_attribute("value")

        return estado

    def _verificar_wifi_24ghz_persistido(
        self,
        ssid_objetivo: str,
        chanwid_objetivo: str,
        chan_objetivo: str
    ):
        self._status("Verificando WiFi 2.4 GHz...")

        self._detectar_alerta_wifi("WiFi 2.4 GHz", timeout=2)

        try:
            self._abrir_wlan_24ghz(timeout=20)
        except UnexpectedAlertPresentException:
            self._detectar_alerta_wifi("WiFi 2.4 GHz", timeout=2)
            raise ErrorVerificacionConfiguracion(
                "WiFi 2.4 GHz no pudo verificarse correctamente."
            )

        estado = self._leer_estado_wlan_24ghz()

        txpower_ok = (
            estado["txpower"] is None
            or estado["txpower"] == "0"
        )

        if not (
            estado["ssid"] == ssid_objetivo
            and estado["chanwid"] == str(chanwid_objetivo)
            and estado["chan"] == str(chan_objetivo)
            and txpower_ok
        ):
            self._status("❌ WiFi 2.4 GHz no quedó guardado correctamente.")

            raise ErrorVerificacionConfiguracion(
                "La configuración WiFi 2.4 GHz no quedó guardada correctamente.\n\n"
                "Valores detectados:\n"
                f"- SSID: {estado['ssid']}\n"
                f"- Channel Width: {estado['chanwid']}\n"
                f"- Channel: {estado['chan']}\n"
                f"- TX Power: {estado['txpower'] if estado['txpower'] is not None else 'No disponible'}\n\n"
                "Valores esperados:\n"
                f"- SSID: {ssid_objetivo}\n"
                f"- Channel Width: {chanwid_objetivo}\n"
                f"- Channel: {chan_objetivo}\n"
                "- TX Power: 0\n\n"
                "La configuración fue detenida para evitar continuar con un equipo "
                "parcialmente configurado."
            )

        self._status("✅ WiFi 2.4 GHz configurado y verificado.")
    # ============================================================
    # FIN BLOQUE AGREGADO - VERIFICACIÓN WIFI 2.4 GHZ
    # ============================================================

    # ============================================================
    # INICIO BLOQUE AGREGADO - VERIFICACIÓN SEGURIDAD WIFI 2.4 GHZ
    # ============================================================
    def _abrir_seguridad_24ghz(self, timeout=20):
        d = self.driver
        d.switch_to.default_content()

        sec24 = WebDriverWait(d, timeout).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//a[@target='contentIframe' and contains(@href,'wlwpa.asp') and contains(@href,'wlan_idx=1')]"
            ))
        )
        self._click_safe(sec24)

        self._switch_to_content_iframe(timeout=timeout)

        WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.NAME, "security_method"))
        )

    def _verificar_seguridad_24ghz_persistida(self):
        self._status("Verificando seguridad WiFi 2.4 GHz...")

        self._detectar_alerta_wifi("Seguridad WiFi 2.4 GHz", timeout=2)

        try:
            self._abrir_seguridad_24ghz(timeout=20)
        except UnexpectedAlertPresentException:
            self._detectar_alerta_wifi("Seguridad WiFi 2.4 GHz", timeout=2)
            raise ErrorVerificacionConfiguracion(
                "La seguridad WiFi 2.4 GHz no pudo verificarse correctamente."
            )

        sec_method = self.driver.find_element(By.NAME, "security_method")
        valor = Select(sec_method).first_selected_option.get_attribute("value")

        if valor != "6":
            self._status("❌ Seguridad WiFi 2.4 GHz no quedó guardada correctamente.")

            raise ErrorVerificacionConfiguracion(
                "La seguridad WiFi 2.4 GHz no quedó guardada correctamente.\n\n"
                f"Valor detectado: {valor}\n"
                "Valor esperado: 6\n\n"
                "La configuración fue detenida para evitar continuar con un equipo "
                "parcialmente configurado."
            )

        self._status("✅ Seguridad WiFi 2.4 GHz configurada y verificada.")
    # ============================================================
    # FIN BLOQUE AGREGADO - VERIFICACIÓN SEGURIDAD WIFI 2.4 GHZ
    # ============================================================

    # ============================================================
    # INICIO BLOQUE AGREGADO - VERIFICACIÓN PASSWORD ADMIN
    # ============================================================
    def _verificar_cambio_password(self, timeout=15):
        d = self.driver

        self._status("Verificando cambio de contraseña de administrador...")

        try:
            d.switch_to.default_content()
        except Exception:
            pass

        try:
            self._switch_to_content_iframe(timeout=timeout)
        except Exception:
            pass

        texto_exito = "Change setting successfully!"

        try:
            WebDriverWait(d, timeout).until(
                lambda _d: (
                    texto_exito.lower() in _d.page_source.lower()
                    or "password has already been used" in _d.page_source.lower()
                )
            )
        except TimeoutException:
            self._status("❌ No se pudo confirmar el cambio de contraseña.")

            raise ErrorVerificacionConfiguracion(
                "No se recibió una confirmación válida del equipo después de cambiar "
                "la contraseña de administrador.\n\n"
                "La configuración fue detenida para evitar continuar con un equipo "
                "parcialmente configurado."
            )

        contenido = d.page_source.lower()

        if texto_exito.lower() in contenido:
            self._status("✅ Contraseña de administrador cambiada y verificada.")
            return

        if "password has already been used" in contenido:
            mensaje_equipo = "The password has already been used"
        else:
            mensaje_equipo = "El equipo rechazó el cambio de contraseña."

        self._status("❌ El equipo rechazó el cambio de contraseña de administrador.")

        raise ErrorVerificacionConfiguracion(
            "La contraseña de administrador no pudo cambiarse correctamente.\n\n"
            f"El equipo informó: {mensaje_equipo}\n\n"
            "La configuración fue detenida para evitar continuar con un equipo "
            "parcialmente configurado."
        )
    # ============================================================
    # FIN BLOQUE AGREGADO - VERIFICACIÓN PASSWORD ADMIN
    # ============================================================

    # ============================================================
    # INICIO BLOQUE AGREGADO - VERIFICACIÓN TR-069
    # ============================================================
    def _abrir_tr069(self, timeout=20):
        d = self.driver
        d.switch_to.default_content()

        admin_tab = WebDriverWait(d, timeout).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//ul[@id='nav']//a[@href='javascript:void(0)' and @rel='9' and normalize-space()='Admin']"
                )
            )
        )
        self._click_safe(admin_tab)

        side_menu = WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.ID, "side"))
        )

        tr069_link = WebDriverWait(side_menu, timeout).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    ".//a[@target='contentIframe' and contains(@href,'tr069config.asp')]"
                )
            )
        )

        try:
            d.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                tr069_link
            )
        except Exception:
            pass

        self._click_safe(tr069_link)

        self._switch_to_content_iframe(timeout=timeout)

        WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.NAME, "url"))
        )

    def _leer_estado_tr069(self):
        d = self.driver

        def _valor(name):
            try:
                el = d.find_element(By.NAME, name)
                return (el.get_attribute("value") or "").strip()
            except Exception:
                return None

        return {
            "url": _valor("url"),
            "username": _valor("username"),
            "password": _valor("password"),
            "conreqname": _valor("conreqname"),
            "conreqpw": _valor("conreqpw"),
        }

    def _password_tr069_verificable(self, valor: str):
        if valor is None:
            return False

        valor = valor.strip()

        if not valor:
            return False

        caracteres_mascara = set("*•●.")
        if set(valor).issubset(caracteres_mascara):
            return False

        return True

    def _procesar_alerta_tr069(self, timeout=2):
        d = self.driver

        try:
            WebDriverWait(d, timeout).until(EC.alert_is_present())
        except TimeoutException:
            return

        try:
            alerta = d.switch_to.alert
            texto = (alerta.text or "").strip()
            alerta.accept()
        except Exception:
            texto = ""

        if texto:
            texto_lower = texto.lower()

            indicadores_error = (
                "error",
                "fail",
                "failed",
                "invalid",
                "incorrect",
                "empty",
                "wrong",
            )

            if any(indicador in texto_lower for indicador in indicadores_error):
                self._status("❌ El equipo rechazó la configuración TR-069.")

                raise ErrorVerificacionConfiguracion(
                    "La configuración TR-069 no pudo aplicarse correctamente.\n\n"
                    f"El equipo informó: {texto}\n\n"
                    "La configuración fue detenida para evitar continuar con un equipo "
                    "parcialmente configurado."
                )

    def _verificar_tr069_persistido(self):
        self._status("Verificando TR-069...")

        self._procesar_alerta_tr069(timeout=2)

        try:
            self._abrir_tr069(timeout=20)
        except UnexpectedAlertPresentException:
            self._procesar_alerta_tr069(timeout=2)

            self._status("❌ TR-069 no pudo verificarse.")

            raise ErrorVerificacionConfiguracion(
                "La configuración TR-069 no pudo verificarse correctamente.\n\n"
                "La configuración fue detenida para evitar continuar con un equipo "
                "parcialmente configurado."
            )

        estado = self._leer_estado_tr069()

        errores = []

        if estado["url"] != "http://172.22.16.109:7995/":
            errores.append(
                f"URL ACS detectada: {estado['url']!r}"
            )

        if estado["username"] != "admin":
            errores.append(
                f"Username detectado: {estado['username']!r}"
            )

        if estado["conreqname"] != "admin":
            errores.append(
                f"Connection Request Username detectado: {estado['conreqname']!r}"
            )

        password_verificada = False
        conreqpw_verificada = False

        if self._password_tr069_verificable(estado["password"]):
            password_verificada = True
            if estado["password"] != "admin":
                errores.append("Password TR-069 no coincide con el valor esperado.")

        if self._password_tr069_verificable(estado["conreqpw"]):
            conreqpw_verificada = True
            if estado["conreqpw"] != "admin":
                errores.append(
                    "Connection Request Password no coincide con el valor esperado."
                )

        if errores:
            self._status("❌ TR-069 no quedó guardado correctamente.")

            raise ErrorVerificacionConfiguracion(
                "La configuración TR-069 no quedó guardada correctamente.\n\n"
                + "\n".join(f"- {error}" for error in errores)
                + "\n\nLa configuración fue detenida para evitar continuar con un equipo "
                  "parcialmente configurado."
            )

        if password_verificada and conreqpw_verificada:
            self._status("✅ TR-069 configurado y verificado completamente.")
        else:
            self._status("✅ TR-069 configurado y verificado en todos los campos visibles.")
    # ============================================================
    # FIN BLOQUE AGREGADO - VERIFICACIÓN TR-069
    # ============================================================

    # ============================================================
    # INICIO BLOQUE AGREGADO - VERIFICACIÓN REMOTE ACCESS HTTPS
    # ============================================================
    def _abrir_remote_access(self, timeout=20):
        d = self.driver
        d.switch_to.default_content()

        nav_menu = WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.ID, "nav"))
        )

        advance_tab = WebDriverWait(nav_menu, timeout).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    ".//a[@href='javascript:void(0)' and @rel='7' and normalize-space()='Advance']"
                )
            )
        )
        self._click_safe(advance_tab)

        side_menu = WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.ID, "side"))
        )

        remote_link = WebDriverWait(side_menu, timeout).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    ".//a[@target='contentIframe' and @href='rmtacc.asp' and normalize-space()='Remote Access']"
                )
            )
        )
        self._click_safe(remote_link)

        self._switch_to_content_iframe(timeout=timeout)

        WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.NAME, "w_https"))
        )

    def _procesar_alerta_remote_access(self, timeout=2):
        d = self.driver

        try:
            WebDriverWait(d, timeout).until(EC.alert_is_present())
        except TimeoutException:
            return

        try:
            alerta = d.switch_to.alert
            texto = (alerta.text or "").strip()
            alerta.accept()
        except Exception:
            texto = ""

        if texto:
            texto_lower = texto.lower()

            indicadores_error = (
                "error",
                "fail",
                "failed",
                "invalid",
                "incorrect",
                "empty",
                "wrong",
            )

            if any(indicador in texto_lower for indicador in indicadores_error):
                self._status("❌ El equipo rechazó la configuración de Remote Access.")

                raise ErrorVerificacionConfiguracion(
                    "Remote Access HTTPS no pudo aplicarse correctamente.\n\n"
                    f"El equipo informó: {texto}\n\n"
                    "La configuración fue detenida."
                )

    def _verificar_remote_access_https(self):
        self._status("Verificando Remote Access HTTPS...")

        self._procesar_alerta_remote_access(timeout=2)

        try:
            self._abrir_remote_access(timeout=20)
        except UnexpectedAlertPresentException:
            self._procesar_alerta_remote_access(timeout=2)

            self._status("❌ Remote Access HTTPS no pudo verificarse.")

            raise ErrorVerificacionConfiguracion(
                "Remote Access HTTPS no pudo verificarse correctamente.\n\n"
                "La configuración fue detenida."
            )

        https_checkbox = WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.NAME, "w_https"))
        )

        if not https_checkbox.is_selected():
            self._status("❌ Remote Access HTTPS no quedó habilitado.")

            raise ErrorVerificacionConfiguracion(
                "Remote Access HTTPS no quedó guardado correctamente.\n\n"
                "El equipo volvió a mostrar la opción HTTPS deshabilitada.\n\n"
                "La configuración fue detenida."
            )

        self._status("✅ Remote Access HTTPS configurado y verificado.")
    # ============================================================
    # FIN BLOQUE AGREGADO - VERIFICACIÓN REMOTE ACCESS HTTPS
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

        except ErrorVerificacionConfiguracion as e:
            self._msgbox_error("Configuración incompleta", str(e))
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

        self._verificar_vlan_persistida(
            vid_objetivo="500",
            ctype_objetivo="2"
        )

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

        self._verificar_vlan_persistida(
            vid_objetivo="600",
            ctype_objetivo="1"
        )

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

        self._verificar_wifi_5ghz_persistido(
            ssid_objetivo=ssid_name,
            chanwid_objetivo=extra["chanwid_5"],
            chan_objetivo=extra["chan_5"]
        )

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

        self._verificar_seguridad_5ghz_persistida()

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

        self._verificar_wifi_24ghz_persistido(
            ssid_objetivo=ssid_name,
            chanwid_objetivo=extra["chanwid_24"],
            chan_objetivo=extra["chan_24"]
        )

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

        self._verificar_seguridad_24ghz_persistida()

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

        self._verificar_cambio_password(timeout=15)

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

        u = WebDriverWait(d, 15).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        u.clear()
        u.send_keys("admin")

        p = WebDriverWait(d, 15).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
        p.clear()
        p.send_keys("admin")

        crn = WebDriverWait(d, 15).until(
            EC.presence_of_element_located((By.NAME, "conreqname"))
        )
        crn.clear()
        crn.send_keys("admin")

        crp = WebDriverWait(d, 15).until(
            EC.presence_of_element_located((By.NAME, "conreqpw"))
        )
        crp.clear()
        crp.send_keys("admin")

        apply_tr = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//input[@type='submit' and @name='save' and (@value='Apply' or @value='Apply Changes')]"
        )))
        self._click_safe(apply_tr)

        self._verificar_tr069_persistido()

        # =========================
        # Advance -> Remote Access
        # =========================
        self._status("Configurando Remote Access (HTTPS)...")
        d.switch_to.default_content()

        advance = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[@href='javascript:void(0)' and @rel='7']")
            )
        )
        self._click_safe(advance)

        remote = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[@target='contentIframe' and @href='rmtacc.asp']")
            )
        )
        self._click_safe(remote)

        self._switch_to_content_iframe(timeout=20)

        https = wait.until(
            EC.element_to_be_clickable((By.NAME, "w_https"))
        )

        if not https.is_selected():
            self._click_safe(https)

        WebDriverWait(d, 10).until(
            lambda _d: _d.find_element(By.NAME, "w_https").is_selected()
        )

        apply_remote = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//input[@type='submit' and @name='set' and @value='Apply Changes']"
                )
            )
        )
        self._click_safe(apply_remote)

        self._verificar_remote_access_https()

        self._status(
            "✅ Todas las configuraciones del DM986-414 fueron aplicadas y verificadas."
        )
