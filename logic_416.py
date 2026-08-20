# logica para configurar Datacom DM986-416 AX30 via Selenium
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
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    UnexpectedAlertPresentException,
)

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
# INICIO BLOQUE AGREGADO - VERIFICACIÓN DE CONFIGURACIÓN WAN
# ============================================================
class ErrorVerificacionConfiguracion(Exception):
    pass
# ============================================================
# FIN BLOQUE AGREGADO - VERIFICACIÓN DE CONFIGURACIÓN WAN
# ============================================================
# ============================================================
# FIN BLOQUE AGREGADO - MANEJO DE ERRORES AMIGABLES
# ============================================================


class ConfiguradorModem416:

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
        # si tu UI tiene safe_messagebox, la usamos; si no, solo status/print
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

    # ============================================================
    # INICIO BLOQUE AGREGADO - VERIFICACIÓN VLAN 500 / VLAN 600
    # ============================================================
    def _abrir_wan(self, timeout=20):
        """
        Abre nuevamente la pantalla WAN y entra en contentIframe.
        No asume que la pantalla anterior haya quedado cargada.
        """
        d = self.driver
        d.switch_to.default_content()

        nav_menu = WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.ID, "nav"))
        )
        wan_link = WebDriverWait(nav_menu, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, ".//a[@rel='4' and normalize-space()='WAN']")
            )
        )
        self._click_safe(wan_link)

        self._switch_to_content_iframe(timeout=timeout)

        # La presencia de VID confirma que la pantalla WAN terminó de cargar.
        WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.NAME, "vid"))
        )

    def _leer_estado_wan_actual(self):
        """
        Lee el estado actualmente visible en la pantalla WAN.
        """
        d = self.driver

        vlan = d.find_element(By.NAME, "vlan")
        vid = d.find_element(By.NAME, "vid")
        adsl = d.find_element(By.NAME, "adslConnectionMode")
        ctype = d.find_element(By.NAME, "ctype")

        ipmode = d.find_element(
            By.XPATH,
            "//input[@type='radio' and @name='ipMode' and @value='1']"
        )

        return {
            "vlan": vlan.is_selected(),
            "vid": (vid.get_attribute("value") or "").strip(),
            "adslConnectionMode": Select(adsl).first_selected_option.get_attribute("value"),
            "ctype": Select(ctype).first_selected_option.get_attribute("value"),
            "dhcp": ipmode.is_selected(),
        }

    def _esperar_wan_objetivo(self, vid_objetivo: str, ctype_objetivo: str, timeout=20):
        """
        Espera hasta que la pantalla WAN refleje exactamente los valores esperados.
        Devuelve True si coincide; False si vence el timeout.
        """
        d = self.driver

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
            WebDriverWait(d, timeout).until(_estado_correcto)
            return True
        except TimeoutException:
            return False

    def _buscar_vlan_en_links(self, vid_objetivo: str, ctype_objetivo: str, timeout=20):
        """
        Si al volver a WAN no quedó seleccionado el enlace esperado,
        recorre los enlaces disponibles en lkname hasta encontrar la VLAN.
        """
        d = self.driver

        try:
            lkname = WebDriverWait(d, timeout).until(
                EC.presence_of_element_located((By.NAME, "lkname"))
            )
        except TimeoutException:
            return False

        opciones = lkname.find_elements(By.TAG_NAME, "option")
        valores = [opt.get_attribute("value") for opt in opciones]

        for valor in valores:
            if not valor or valor == "new":
                continue

            try:
                lkname = WebDriverWait(d, timeout).until(
                    EC.presence_of_element_located((By.NAME, "lkname"))
                )
                Select(lkname).select_by_value(valor)

                # Esperamos a que el firmware procese el cambio de link.
                WebDriverWait(d, timeout).until(
                    lambda _d: _d.find_element(By.NAME, "vid").is_displayed()
                )

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
        """
        Detecta alertas del firmware después de Apply Changes.
        Si el equipo rechaza la configuración, convierte la alerta
        en un error amigable y detiene el proceso.
        """
        d = self.driver

        try:
            WebDriverWait(d, timeout).until(EC.alert_is_present())
        except TimeoutException:
            return

        try:
            alerta = d.switch_to.alert
            texto_alerta = (alerta.text or "").strip()
            alerta.accept()
        except Exception:
            texto_alerta = "El equipo rechazó la configuración."

        detalle = (
            f"\n\nEl equipo informó: {texto_alerta}"
            if texto_alerta
            else ""
        )

        raise ErrorVerificacionConfiguracion(
            f"La VLAN {vid_objetivo} no pudo aplicarse correctamente."
            f"{detalle}\n\n"
            "La configuración fue detenida para evitar continuar con un equipo "
            "parcialmente configurado."
        )

    def _verificar_vlan_persistida(self, vid_objetivo: str, ctype_objetivo: str):
        """
        Verificación fuerte:
        1. vuelve a abrir WAN,
        2. relee los datos guardados por el equipo,
        3. si hace falta recorre los enlaces,
        4. detiene el proceso si la VLAN no quedó persistida.
        """
        self._status(f"Verificando VLAN {vid_objetivo}...")

        # Primero comprobamos si el propio firmware mostró una alerta
        # rechazando los valores enviados.
        self._detectar_alerta_vlan(vid_objetivo, timeout=2)

        try:
            self._abrir_wan(timeout=20)
        except UnexpectedAlertPresentException:
            # Algunos navegadores reportan la alerta recién cuando Selenium
            # intenta cambiar de frame/página.
            self._detectar_alerta_vlan(vid_objetivo, timeout=2)
            raise ErrorVerificacionConfiguracion(
                f"La VLAN {vid_objetivo} no pudo verificarse correctamente.\n\n"
                "La configuración fue detenida para evitar continuar con un equipo "
                "parcialmente configurado."
            )

        # Primero verificamos el link que el equipo muestra al reabrir WAN.
        if self._esperar_wan_objetivo(
            vid_objetivo,
            ctype_objetivo,
            timeout=5
        ):
            self._status(f"✅ VLAN {vid_objetivo} configurada y verificada.")
            return

        # Si no era el link visible, buscamos entre los links existentes.
        if self._buscar_vlan_en_links(
            vid_objetivo,
            ctype_objetivo,
            timeout=15
        ):
            self._status(f"✅ VLAN {vid_objetivo} configurada y verificada.")
            return

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
        """
        Vuelve a abrir la pantalla principal de WLAN 5 GHz.
        """
        d = self.driver
        d.switch_to.default_content()

        nav_menu = WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.ID, "nav"))
        )

        wlan_link = WebDriverWait(nav_menu, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, ".//a[@rel='3' and normalize-space()='WLAN']")
            )
        )
        self._click_safe(wlan_link)

        self._switch_to_content_iframe(timeout=timeout)

        # El SSID confirma que la pantalla terminó de cargar.
        WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.NAME, "ssid"))
        )

    def _leer_estado_wlan_5ghz(self):
        """
        Lee los valores actualmente visibles en WLAN 5 GHz.
        """
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

        # Algunos firmwares pueden no mostrar TX Power.
        txpower = d.find_elements(By.NAME, "txpower")
        if txpower:
            estado["txpower"] = Select(txpower[0]).first_selected_option.get_attribute("value")

        return estado

    def _esperar_wlan_5ghz_objetivo(self, ssid_objetivo: str, timeout=15):
        """
        Espera hasta que la pantalla WLAN 5 GHz refleje los valores esperados.
        """
        d = self.driver

        def _estado_correcto(_driver):
            try:
                estado = self._leer_estado_wlan_5ghz()

                txpower_ok = (
                    estado["txpower"] is None
                    or estado["txpower"] == "0"
                )

                return (
                    estado["ssid"] == ssid_objetivo
                    and estado["chanwid"] == "2"
                    and estado["chan"] == "36"
                    and txpower_ok
                )
            except Exception:
                return False

        try:
            WebDriverWait(d, timeout).until(_estado_correcto)
            return True
        except TimeoutException:
            return False

    def _detectar_alerta_wifi_5ghz(self, timeout=2):
        """
        Detecta si el firmware rechazó la configuración de WLAN 5 GHz
        mediante una alerta JavaScript.
        """
        d = self.driver

        try:
            WebDriverWait(d, timeout).until(EC.alert_is_present())
        except TimeoutException:
            return

        try:
            alerta = d.switch_to.alert
            texto_alerta = (alerta.text or "").strip()
            alerta.accept()
        except Exception:
            texto_alerta = "El equipo rechazó la configuración."

        detalle = (
            f"\n\nEl equipo informó: {texto_alerta}"
            if texto_alerta
            else ""
        )

        self._status("❌ WiFi 5 GHz no pudo aplicarse correctamente.")

        raise ErrorVerificacionConfiguracion(
            "La configuración WiFi 5 GHz no pudo aplicarse correctamente."
            f"{detalle}\n\n"
            "La configuración fue detenida para evitar continuar con un equipo "
            "parcialmente configurado."
        )

    def _verificar_wifi_5ghz_persistido(self, ssid_objetivo: str):
        """
        Verificación fuerte de WLAN 5 GHz:
        1. comprueba alertas del firmware,
        2. vuelve a abrir WLAN 5 GHz,
        3. relee SSID, Channel Width, Channel y TX Power,
        4. continúa solamente si todos los valores persistieron.
        """
        self._status("Verificando WiFi 5 GHz...")

        self._detectar_alerta_wifi_5ghz(timeout=2)

        try:
            self._abrir_wlan_5ghz(timeout=20)
        except UnexpectedAlertPresentException:
            self._detectar_alerta_wifi_5ghz(timeout=2)
            self._status("❌ WiFi 5 GHz no pudo verificarse.")
            raise ErrorVerificacionConfiguracion(
                "La configuración WiFi 5 GHz no pudo verificarse correctamente.\n\n"
                "La configuración fue detenida para evitar continuar con un equipo "
                "parcialmente configurado."
            )

        if self._esperar_wlan_5ghz_objetivo(
            ssid_objetivo=ssid_objetivo,
            timeout=10
        ):
            self._status("✅ WiFi 5 GHz configurado y verificado.")
            return

        try:
            estado = self._leer_estado_wlan_5ghz()
            detalle = (
                "\n\nValores detectados:\n"
                f"- SSID: {estado['ssid']}\n"
                f"- Channel Width: {estado['chanwid']}\n"
                f"- Channel: {estado['chan']}\n"
                f"- TX Power: {estado['txpower'] if estado['txpower'] is not None else 'No disponible'}"
            )
        except Exception:
            detalle = ""

        self._status("❌ WiFi 5 GHz no quedó guardado correctamente.")

        raise ErrorVerificacionConfiguracion(
            "La configuración WiFi 5 GHz no quedó guardada correctamente."
            f"{detalle}\n\n"
            "Se esperaba:\n"
            f"- SSID: {ssid_objetivo}\n"
            "- Channel Width: 80 MHz\n"
            "- Channel: 36\n"
            "- TX Power: máximo/default del equipo\n\n"
            "La configuración fue detenida para evitar continuar con un equipo "
            "parcialmente configurado."
        )
    # ============================================================
    # FIN BLOQUE AGREGADO - VERIFICACIÓN WIFI 5 GHZ
    # ============================================================

    # ============================================================
    # INICIO BLOQUE AGREGADO - VERIFICACIÓN SEGURIDAD WIFI 5 GHZ
    # ============================================================
    def _abrir_seguridad_5ghz(self, timeout=20):
        d = self.driver
        d.switch_to.default_content()

        side_menu = WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.ID, "side"))
        )

        sec_5 = WebDriverWait(side_menu, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, ".//a[contains(@href,'/wlwpa.asp') and contains(@href,'wlan_idx=0')]")
            )
        )
        self._click_safe(sec_5)

        self._switch_to_content_iframe(timeout=timeout)

        WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.ID, "security_method"))
        )

    def _leer_estado_seguridad_5ghz(self):
        d = self.driver
        sec_method = d.find_element(By.ID, "security_method")
        return {
            "security_method": Select(sec_method).first_selected_option.get_attribute("value")
        }

    def _verificar_seguridad_5ghz_persistida(self):
        self._status("Verificando seguridad WiFi 5 GHz...")

        try:
            self._abrir_seguridad_5ghz(timeout=20)
        except UnexpectedAlertPresentException:
            self._status("❌ Seguridad WiFi 5 GHz no pudo verificarse.")
            raise ErrorVerificacionConfiguracion(
                "La seguridad WiFi 5 GHz no pudo verificarse correctamente.\n\n"
                "La configuración fue detenida para evitar continuar con un equipo "
                "parcialmente configurado."
            )

        estado = self._leer_estado_seguridad_5ghz()

        if estado["security_method"] != "20":
            self._status("❌ Seguridad WiFi 5 GHz no quedó guardada correctamente.")
            raise ErrorVerificacionConfiguracion(
                "La seguridad WiFi 5 GHz no quedó guardada correctamente.\n\n"
                f"Valor detectado: {estado['security_method']}\n"
                "Valor esperado: 20 (WPA2-PSK/WPA3-PSK)\n\n"
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

        side_menu = WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.ID, "side"))
        )

        wlan1_header = WebDriverWait(side_menu, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, ".//h3/a[normalize-space()='wlan1 (2.4GHz)']")
            )
        )
        self._click_safe(wlan1_header)

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

    def _verificar_wifi_24ghz_persistido(self, ssid_objetivo: str):
        self._status("Verificando WiFi 2.4 GHz...")

        try:
            self._abrir_wlan_24ghz(timeout=20)
        except UnexpectedAlertPresentException:
            self._status("❌ WiFi 2.4 GHz no pudo verificarse.")
            raise ErrorVerificacionConfiguracion(
                "La configuración WiFi 2.4 GHz no pudo verificarse correctamente.\n\n"
                "La configuración fue detenida para evitar continuar con un equipo "
                "parcialmente configurado."
            )

        estado = self._leer_estado_wlan_24ghz()
        txpower_ok = estado["txpower"] is None or estado["txpower"] == "0"

        if not (
            estado["ssid"] == ssid_objetivo
            and estado["chanwid"] == "0"
            and estado["chan"] == "0"
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
                "Se esperaba:\n"
                f"- SSID: {ssid_objetivo}\n"
                "- Channel Width: 20 MHz\n"
                "- Channel: Auto\n"
                "- TX Power: máximo/default del equipo\n\n"
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

        side_menu = WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.ID, "side"))
        )

        sec_24 = WebDriverWait(side_menu, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, ".//a[contains(@href,'/wlwpa.asp') and contains(@href,'wlan_idx=1')]")
            )
        )
        self._click_safe(sec_24)

        self._switch_to_content_iframe(timeout=timeout)

        WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.ID, "security_method"))
        )

    def _leer_estado_seguridad_24ghz(self):
        d = self.driver
        sec_method = d.find_element(By.ID, "security_method")
        return {
            "security_method": Select(sec_method).first_selected_option.get_attribute("value")
        }

    def _verificar_seguridad_24ghz_persistida(self):
        self._status("Verificando seguridad WiFi 2.4 GHz...")

        try:
            self._abrir_seguridad_24ghz(timeout=20)
        except UnexpectedAlertPresentException:
            self._status("❌ Seguridad WiFi 2.4 GHz no pudo verificarse.")
            raise ErrorVerificacionConfiguracion(
                "La seguridad WiFi 2.4 GHz no pudo verificarse correctamente.\n\n"
                "La configuración fue detenida para evitar continuar con un equipo "
                "parcialmente configurado."
            )

        estado = self._leer_estado_seguridad_24ghz()

        if estado["security_method"] != "20":
            self._status("❌ Seguridad WiFi 2.4 GHz no quedó guardada correctamente.")
            raise ErrorVerificacionConfiguracion(
                "La seguridad WiFi 2.4 GHz no quedó guardada correctamente.\n\n"
                f"Valor detectado: {estado['security_method']}\n"
                "Valor esperado: 20 (WPA2-PSK/WPA3-PSK)\n\n"
                "La configuración fue detenida para evitar continuar con un equipo "
                "parcialmente configurado."
            )

        self._status("✅ Seguridad WiFi 2.4 GHz configurada y verificada.")
    # ============================================================
    # FIN BLOQUE AGREGADO - VERIFICACIÓN SEGURIDAD WIFI 2.4 GHZ
    # ============================================================

    # ============================================================
    # INICIO BLOQUE AGREGADO - VERIFICACIÓN CAMBIO DE CONTRASEÑA ADMIN
    # ============================================================
    def _verificar_cambio_password(self, timeout=15):
        """
        Verifica la respuesta real del firmware después de aplicar
        el cambio de contraseña de administrador.

        Éxito esperado del AX30:
            Change setting successfully!

        Cualquier otra respuesta visible se considera fallo y detiene
        la configuración.
        """
        d = self.driver

        self._status("Verificando cambio de contraseña de administrador...")

        # La respuesta del firmware se muestra dentro del iframe de contenido.
        try:
            d.switch_to.default_content()
        except Exception:
            pass

        try:
            self._switch_to_content_iframe(timeout=timeout)
        except Exception:
            # Si ya estamos en el frame correcto, continuamos igualmente.
            pass

        texto_exito = "Change setting successfully!"

        try:
            WebDriverWait(d, timeout).until(
                lambda _d: texto_exito.lower() in _d.page_source.lower()
                or "password has already been used" in _d.page_source.lower()
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

        # Capturamos el mensaje conocido de contraseña ya utilizada.
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
    # FIN BLOQUE AGREGADO - VERIFICACIÓN CAMBIO DE CONTRASEÑA ADMIN
    # ============================================================

    # ============================================================
    # INICIO BLOQUE AGREGADO - VERIFICACIÓN TR-069
    # ============================================================
    def _abrir_tr069(self, timeout=20):
        """
        Abre nuevamente Admin -> TR-069 y espera a que la pantalla
        esté realmente disponible.
        """
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
        """
        Lee los valores que el firmware expone en TR-069.
        """
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
        """
        Devuelve True si el firmware expone la contraseña en claro.
        Devuelve False si la oculta, la deja vacía o la enmascara.
        """
        if valor is None:
            return False

        valor = valor.strip()

        if not valor:
            return False

        # Algunos firmwares devuelven asteriscos/puntos en lugar del valor real.
        caracteres_mascara = set("*•●.")
        if set(valor).issubset(caracteres_mascara):
            return False

        return True

    def _procesar_alerta_tr069(self, timeout=2):
        """
        Si el firmware muestra una alerta luego de Apply, la acepta.
        Si el texto indica claramente un error, detiene la configuración.
        """
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
        """
        Verificación fuerte de TR-069:
        1. procesa cualquier respuesta/alerta del firmware,
        2. vuelve a abrir Admin -> TR-069,
        3. relee los valores persistidos,
        4. valida URL, usuario y Connection Request Username,
        5. valida passwords si el firmware los vuelve a exponer en claro.
        """
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

        # Si el firmware deja leer las contraseñas, también las comprobamos.
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
            self._status(
                "✅ TR-069 configurado y verificado en todos los campos visibles."
            )
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
                (By.XPATH, ".//a[@href='javascript:void(0)' and @rel='7' and normalize-space()='Advance']")
            )
        )
        self._click_safe(advance_tab)

        side_menu = WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.ID, "side"))
        )

        remote_link = WebDriverWait(side_menu, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, ".//a[@target='contentIframe' and @href='rmtacc.asp' and normalize-space()='Remote Access']")
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

    def _switch_to_first_iframe_if_present(self):
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            self.driver.switch_to.frame(iframes[0])

    def _switch_to_content_iframe(self, timeout=15):
        d = self.driver
        d.switch_to.default_content()
        WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "contentIframe")))

    def _select_value_by_name(self, name: str, value: str, timeout=15):
        el = WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((By.NAME, name)))
        Select(el).select_by_value(str(value))

    def _select_value_by_id(self, el_id: str, value: str, timeout=15):
        el = WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((By.ID, el_id)))
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
            self._status("✅ Configuración DM986-416 AX30 completada.")
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
        # INICIO BLOQUE AGREGADO - ERROR DE VERIFICACIÓN DE CONFIGURACIÓN
        # ============================================================
        except ErrorVerificacionConfiguracion as e:
            self._msgbox_error("Configuración incompleta", str(e))
            return False
        # ============================================================
        # FIN BLOQUE AGREGADO - ERROR DE VERIFICACIÓN DE CONFIGURACIÓN
        # ============================================================
        # ============================================================
        # FIN BLOQUE AGREGADO - CAPTURA DE ERRORES AMIGABLES
        # ============================================================

        except Exception as e:
            self._msgbox_error(
                "Error durante la configuración (416 Q)",
                "Ocurrió un error inesperado durante la configuración.\n\n"
                "La configuración fue detenida para evitar continuar con un equipo parcialmente configurado."
            )
            return False

        finally:
            # NO cerrar el navegador para poder verificar la configuración final
            self._status("Navegador queda abierto para verificación.")
            pass

    # =========================
    # Extras WLAN (defaults + validación)
    # =========================
    def _normalize_extras(self, extras: dict) -> dict:

        if not isinstance(extras, dict):
            extras = {}

        enabled = bool(extras.get("enabled", False))

        # Defaults firmwares 416 Q (según tu HTML)
        out = {
            "enabled": enabled,
            "chanwid_5": extras.get("chanwid_5", "2"),
            "chan_5": extras.get("chan_5", "0"),
            "chanwid_24": extras.get("chanwid_24", "0"),
            "chan_24": extras.get("chan_24", "0"),
        }

        # Si no está habilitado, forzamos defaults (para que quede estable)
        if not enabled:
            out["chanwid_5"] = "2"
            out["chan_5"] = "0"
            out["chanwid_24"] = "0"
            out["chan_24"] = "0"

        return out

    # =========================
    # Lógica del módem (TU FLUJO)
    # =========================
    def configurar_modem(self, creds: dict, extra: dict):
        d = self.driver
        wait = WebDriverWait(d, 20)

        username = creds["username"]
        password = creds["password"]
        ssid_name = creds["ssid"]
        wpa_password = creds["wpa"]
        new_password = creds["new_password"]

        # =========================
        # LOGIN (416 AX30)
        # =========================
        self._status("Accediendo a login del modem (416)...")

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
        user_field = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.NAME, "username")))
        user_field.clear()
        user_field.send_keys(username)

        pass_field = d.find_element(By.NAME, "password")
        pass_field.clear()
        pass_field.send_keys(password)

        # EncodePassword (como tu script original)
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

        # adslConnectionMode = 1
        adsl_sel = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.NAME, "adslConnectionMode")))
        for opt in adsl_sel.find_elements(By.TAG_NAME, "option"):
            if opt.get_attribute("value") == "1":
                self._click_safe(opt)
                break
        time.sleep(1)

        # =========================
        # (FIX) VLAN 500: ctype = 2 (Internet) + ipMode = 1 (DHCP)
        # =========================
        # ctype = 2 (Internet)
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

        # ipMode = 1 (DHCP)
        dhcp_500 = WebDriverWait(d, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='radio' and @name='ipMode' and @value='1']"))
        )
        self._click_safe(dhcp_500)
        time.sleep(1)

        chkpt_all = WebDriverWait(d, 10).until(EC.element_to_be_clickable((By.XPATH, "//input[@name='chkpt_all']")))
        self._click_safe(chkpt_all)
        time.sleep(1)

        apply_500 = WebDriverWait(d, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='apply' and @value='Apply Changes']"))
        )
        self._click_safe(apply_500)

        # ============================================================
        # INICIO BLOQUE AGREGADO - VERIFICACIÓN VLAN 500
        # ============================================================
        # No avanzamos a VLAN 600 hasta comprobar que el equipo
        # realmente persistió VLAN 500 / Internet / DHCP.
        self._verificar_vlan_persistida(
            vid_objetivo="500",
            ctype_objetivo="2"
        )
        # ============================================================
        # FIN BLOQUE AGREGADO - VERIFICACIÓN VLAN 500
        # ============================================================

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

        # ctype = 1 (TR069)
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
        # Tu “doble click” para estabilizar
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

        # ============================================================
        # INICIO BLOQUE AGREGADO - VERIFICACIÓN VLAN 600
        # ============================================================
        # No avanzamos a WLAN hasta comprobar que el equipo
        # realmente persistió VLAN 600 / TR069 / DHCP.
        self._verificar_vlan_persistida(
            vid_objetivo="600",
            ctype_objetivo="1"
        )
        # ============================================================
        # FIN BLOQUE AGREGADO - VERIFICACIÓN VLAN 600
        # ============================================================

        # =========================
        # WLAN 5GHz (416 AX30)
        # =========================
        d.switch_to.default_content()

        self._status("Abriendo WLAN (5GHz)...")
        nav_menu = WebDriverWait(d, 20).until(EC.presence_of_element_located((By.ID, "nav")))

        # Click en WLAN
        wlan_link = WebDriverWait(nav_menu, 20).until(
            EC.element_to_be_clickable((By.XPATH, ".//a[@rel='3' and normalize-space()='WLAN']"))
        )
        self._click_safe(wlan_link)

        # Entrar al iframe del contenido (donde están los selects)
        self._switch_to_content_iframe(timeout=20)

        # Esperar que exista el SSID (señal de que estás en la página WLAN 5GHz)
        ssid_input = WebDriverWait(d, 20).until(EC.presence_of_element_located((By.NAME, "ssid")))
        ssid_input.clear()
        ssid_input.send_keys(ssid_name)
        time.sleep(2)

        # =========================
        # Channel Width / Channel Number (416 AX30)
        # =========================
        self._status("Aplicando Channel Width / Channel Number (5GHz)...")

        # Width 80MHz
        chanwid_el = WebDriverWait(d, 20).until(EC.presence_of_element_located((By.NAME, "chanwid")))
        Select(chanwid_el).select_by_value("2")  # 80MHz
        WebDriverWait(d, 10).until(lambda _d: Select(_d.find_element(By.NAME, "chanwid")).first_selected_option.get_attribute("value") == "2")

        # Channel 36
        chan_el = WebDriverWait(d, 20).until(EC.presence_of_element_located((By.NAME, "chan")))
        Select(chan_el).select_by_value("36")
        WebDriverWait(d, 10).until(lambda _d: Select(_d.find_element(By.NAME, "chan")).first_selected_option.get_attribute("value") == "36")

        # TX Power (si existe en esa pantalla)
        try:
            self._select_value_by_name("txpower", "0", timeout=10)
        except Exception:
            pass

        # Apply Changes WLAN
        apply_btn = WebDriverWait(d, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
        )
        self._click_safe(apply_btn)

        # ============================================================
        # INICIO BLOQUE AGREGADO - VERIFICACIÓN WIFI 5 GHZ
        # ============================================================
        # No avanzamos a Seguridad 5 GHz hasta comprobar que el equipo
        # realmente persistió SSID, Channel Width, Channel y TX Power.
        self._verificar_wifi_5ghz_persistido(
            ssid_objetivo=ssid_name
        )
        # ============================================================
        # FIN BLOQUE AGREGADO - VERIFICACIÓN WIFI 5 GHZ
        # ============================================================

        # =========================
        # Seguridad 5GHz
        # =========================
        d.switch_to.default_content()
        self._status("Configurando seguridad WiFi 5GHz...")
        side_menu = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.ID, "side")))

        sec_5 = WebDriverWait(side_menu, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, ".//a[contains(@href,'/wlwpa.asp') and contains(@href,'wlan_idx=0')]")
            )
        )
        self._click_safe(sec_5)
        time.sleep(2)

        self._switch_to_content_iframe(timeout=15)

        # --- Encryption: WPA2-PSK/WPA3-PSK (value="20") ---
        sec_method = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.ID, "security_method")))
        Select(sec_method).select_by_value("20")  # WPA2-PSK/WPA3-PSK
        # dispara el onchange show_authentication(1)
        try:
            d.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", sec_method)
        except Exception:
            pass
        time.sleep(2)

        # --- WPA-PSK ---
        psk_5 = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.ID, "wpapsk")))
        psk_5.clear()
        psk_5.send_keys(wpa_password)
        time.sleep(2)

        apply_sec5 = WebDriverWait(d, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
        )
        self._click_safe(apply_sec5)

        # ============================================================
        # INICIO BLOQUE AGREGADO - VERIFICACIÓN SEGURIDAD WIFI 5 GHZ
        # ============================================================
        self._verificar_seguridad_5ghz_persistida()
        # ============================================================
        # FIN BLOQUE AGREGADO - VERIFICACIÓN SEGURIDAD WIFI 5 GHZ
        # ============================================================

        # =========================
        # WLAN 2.4GHz
        # =========================
        d.switch_to.default_content()
        self._status("Configurando WiFi 2.4GHz...")
        side_menu = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.ID, "side")))

        wlan1_header = WebDriverWait(side_menu, 10).until(
            EC.element_to_be_clickable((By.XPATH, ".//h3/a[normalize-space()='wlan1 (2.4GHz)']"))
        )
        self._click_safe(wlan1_header)
        time.sleep(2)

        self._switch_to_content_iframe(timeout=15)

        ssid_24 = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.NAME, "ssid")))
        ssid_24.clear()
        ssid_24.send_keys(ssid_name)
        time.sleep(2)

        self._status("Aplicando Channel Width / Channel Number (2.4GHz)...")
        self._select_value_by_name("chanwid", extra["chanwid_24"], timeout=10)
        self._select_value_by_name("chan", extra["chan_24"], timeout=10)
        time.sleep(2)

        self._select_value_by_name("txpower", "0", timeout=10)
        time.sleep(2)

        apply_wifi24 = WebDriverWait(d, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
        )
        self._click_safe(apply_wifi24)

        # ============================================================
        # INICIO BLOQUE AGREGADO - VERIFICACIÓN WIFI 2.4 GHZ
        # ============================================================
        self._verificar_wifi_24ghz_persistido(
            ssid_objetivo=ssid_name
        )
        # ============================================================
        # FIN BLOQUE AGREGADO - VERIFICACIÓN WIFI 2.4 GHZ
        # ============================================================

        # =========================
        # Seguridad 2.4GHz
        # =========================
        d.switch_to.default_content()
        self._status("Configurando seguridad WiFi 2.4GHz...")
        side_menu = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.ID, "side")))

        sec_24 = WebDriverWait(side_menu, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, ".//a[contains(@href,'/wlwpa.asp') and contains(@href,'wlan_idx=1')]")
            )
        )
        self._click_safe(sec_24)
        time.sleep(2)

        self._switch_to_content_iframe(timeout=15)

        # --- Encryption: WPA2-PSK/WPA3-PSK (value="20") ---
        sec_method_24 = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.ID, "security_method")))
        Select(sec_method_24).select_by_value("20")  # WPA2-PSK/WPA3-PSK

        # fuerza el onchange show_authentication(1)
        try:
            d.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", sec_method_24)
        except Exception:
            pass

        time.sleep(2)

        # --- WPA-PSK ---
        psk_24 = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.ID, "wpapsk")))
        psk_24.clear()
        psk_24.send_keys(wpa_password)
        time.sleep(2)

        apply_sec24 = WebDriverWait(d, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
        )

        self._click_safe(apply_sec24)

        # ============================================================
        # INICIO BLOQUE AGREGADO - VERIFICACIÓN SEGURIDAD WIFI 2.4 GHZ
        # ============================================================
        self._verificar_seguridad_24ghz_persistida()
        # ============================================================
        # FIN BLOQUE AGREGADO - VERIFICACIÓN SEGURIDAD WIFI 2.4 GHZ
        # ============================================================

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

        # ============================================================
        # INICIO BLOQUE AGREGADO - VERIFICACIÓN CAMBIO DE CONTRASEÑA ADMIN
        # ============================================================
        self._verificar_cambio_password(timeout=15)
        # ============================================================
        # FIN BLOQUE AGREGADO - VERIFICACIÓN CAMBIO DE CONTRASEÑA ADMIN
        # ============================================================

        # =========================
        # Admin -> TR-069
        # =========================
        d.switch_to.default_content()
        self._status("Configurando TR-069...")

        # asegurar Admin tab
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

        url_input = WebDriverWait(d, 15).until(
            EC.presence_of_element_located((By.NAME, "url"))
        )
        url_input.clear()
        url_input.send_keys("http://172.22.16.109:7995/")

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

        conreqname = WebDriverWait(d, 15).until(
            EC.presence_of_element_located((By.NAME, "conreqname"))
        )
        conreqname.clear()
        conreqname.send_keys("admin")

        conreqpw = WebDriverWait(d, 15).until(
            EC.presence_of_element_located((By.NAME, "conreqpw"))
        )
        conreqpw.clear()
        conreqpw.send_keys("admin")

        apply_tr = WebDriverWait(d, 15).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//input[@type='submit' and @name='save' and (@value='Apply' or @value='Apply Changes')]"
                )
            )
        )
        self._click_safe(apply_tr)

        # ============================================================
        # INICIO BLOQUE AGREGADO - VERIFICACIÓN TR-069
        # ============================================================
        # No avanzamos a Remote Access hasta comprobar que el equipo
        # realmente persistió la configuración TR-069.
        self._verificar_tr069_persistido()
        # ============================================================
        # FIN BLOQUE AGREGADO - VERIFICACIÓN TR-069
        # ============================================================

        # =========================
        # Advance -> Remote Access
        # =========================
        d.switch_to.default_content()
        self._status("Configurando Remote Access (HTTPS)...")

        nav_menu = WebDriverWait(d, 20).until(
            EC.presence_of_element_located((By.ID, "nav"))
        )

        advance_tab = WebDriverWait(nav_menu, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, ".//a[@href='javascript:void(0)' and @rel='7' and normalize-space()='Advance']")
            )
        )
        self._click_safe(advance_tab)

        side_menu = WebDriverWait(d, 20).until(
            EC.presence_of_element_located((By.ID, "side"))
        )

        remote_link = WebDriverWait(side_menu, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, ".//a[@target='contentIframe' and @href='rmtacc.asp' and normalize-space()='Remote Access']")
            )
        )
        self._click_safe(remote_link)

        self._switch_to_content_iframe(timeout=15)

        https_checkbox = WebDriverWait(d, 15).until(
            EC.presence_of_element_located((By.NAME, "w_https"))
        )

        try:
            d.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                https_checkbox
            )
        except Exception:
            pass

        if not https_checkbox.is_selected():
            self._click_safe(https_checkbox)

        WebDriverWait(d, 10).until(
            lambda _d: _d.find_element(By.NAME, "w_https").is_selected()
        )

        apply_remote = WebDriverWait(d, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//input[@type='submit' and @name='set' and @value='Apply Changes']")
            )
        )

        self._click_safe(apply_remote)

        # ============================================================
        # INICIO BLOQUE AGREGADO - VERIFICACIÓN REMOTE ACCESS HTTPS
        # ============================================================
        self._verificar_remote_access_https()
        # ============================================================
        # FIN BLOQUE AGREGADO - VERIFICACIÓN REMOTE ACCESS HTTPS
        # ============================================================
