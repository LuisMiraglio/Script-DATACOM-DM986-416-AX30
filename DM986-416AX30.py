from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import base64

# Credenciales para login del modem
username = input("Ingrese el nombre de usuario: ")
password = input("Ingrese la contraseña: ")
ssid_name = input("Ingrese el nombre de la red Wi-Fi (SSID): ")
wpa_password = input("Ingrese la contraseña WPA: ")
new_password = input("Ingrese la nueva contraseña para el administrador: ")

# Config Edge
edge_options = Options()
edge_options.add_argument("--ignore-certificate-errors")
edge_options.add_argument("--ignore-ssl-errors")
edge_options.add_argument("--disable-web-security")
edge_options.add_argument("--allow-running-insecure-content")

# Ruta al driver
script_dir = os.path.dirname(os.path.abspath(__file__))
service = Service(os.path.join(script_dir, "msedgedriver.exe"))
driver = webdriver.Edge(service=service, options=edge_options)

try:
    # Ir al login
    driver.get("https://192.168.0.1/admin/login.asp")
    time.sleep(2)  # espera corta inicial

    # Ver si hay iframe
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if iframes:
        driver.switch_to.frame(iframes[0])  # entrar al primer iframe

    # Esperar campo usuario
    username_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "username"))
    )
    username_field.send_keys(username)

    # Contraseña
    password_field = driver.find_element(By.NAME, "password")
    password_field.send_keys(password)
    
    # Codificar
    encoded_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')
    driver.execute_script("""
        document.getElementsByName('encodePassword')[0].value = arguments[0];
        document.getElementsByName('password')[0].disabled = true;
    """, encoded_password)

    # Enviar
    login_button = driver.find_element(By.XPATH, "//input[@type='submit' and @value='Login']")
    login_button.click()

    # Esperar a que el menú de navegación <ul id="nav"> esté presente
    nav_menu = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "nav"))
    )

    # Hacer clic en el enlace "WAN"
    wan_link = nav_menu.find_element(By.XPATH, ".//a[@rel='4' and text()='WAN']")
    wan_link.click()

    # Esperar a que el iframe con id "contentIframe" esté presente
    content_iframe = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "contentIframe"))
    )

    # Cambiar al iframe
    driver.switch_to.frame(content_iframe)

    # Buscar y hacer clic en el checkbox "vlan"
    vlan_checkbox = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @name='vlan' and @value='ON']"))
    )
    vlan_checkbox.click()

    # Ingresar el número 500 en el campo VLAN ID
    vid_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//input[@name='vid']"))
    )
    vid_input.clear()  # Limpiar el campo antes de ingresar el valor
    vid_input.send_keys("500")

    # Seleccionar la opción "IPoE" en el menú desplegable "Channel Mode"
    channel_mode_dropdown = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "adslConnectionMode"))
    )
    for option in channel_mode_dropdown.find_elements(By.TAG_NAME, "option"):
        if option.get_attribute("value") == "1":
            option.click()
            break

    # Marcar el checkbox "chkpt_all" Port Mapping
    chkpt_all_checkbox = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@name='chkpt_all']"))
    )
    chkpt_all_checkbox.click()
    
    # Hacer clic en el botón "Apply Changes" después de marcar el checkbox
    apply_changes_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Apply Changes' and @name='apply']"))
    )
    apply_changes_button.click()
    time.sleep(2)

    # Volver al contexto principal (por si estamos en un iframe aún)
    driver.switch_to.default_content()

    # Esperar a que el menú nav vuelva a estar presente
    nav_menu = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "nav"))
    )

    # Hacer clic en el enlace "WLAN"
    wlan_link = nav_menu.find_element(By.XPATH, ".//a[@rel='3' and text()='WLAN']")
    wlan_link.click()

    # Entrar al iframe WLAN
    content_iframe = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "contentIframe"))
    )
    driver.switch_to.frame(content_iframe)

    # Cambiar SSID
    ssid_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "ssid"))
    )
    ssid_input.clear()
    ssid_input.send_keys(ssid_name)

    # Asegurarse de que la opción "160MHz" esté seleccionada en el menú desplegable
    chanwid_dropdown = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "chanwid"))
    )
    for option in chanwid_dropdown.find_elements(By.TAG_NAME, "option"):
        if option.get_attribute("value") == "3":
            option.click()
            break

    # Asegurarse de que la opción "DFS" esté seleccionada en el menú desplegable "chan_select"
    chan_select_dropdown = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "chan_select"))
    )
    for option in chan_select_dropdown.find_elements(By.TAG_NAME, "option"):
        if option.get_attribute("value") == "0":
            option.click()
            break

    # Asegurarse de que la opción "100%" esté seleccionada en el menú desplegable "txpower"
    txpower_dropdown = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "txpower"))
    )
    for option in txpower_dropdown.find_elements(By.TAG_NAME, "option"):
        if option.get_attribute("value") == "0":
            option.click()
            break

    # Hacer clic en el botón "Apply Changes"
    apply_changes_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Apply Changes' and @name='save']"))
    )
    apply_changes_button.click()
    time.sleep(5)

    # Volver al contexto principal (por si estamos en un iframe aún)
    driver.switch_to.default_content()

    # Esperar que aparezca el menú lateral
    side_menu = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "side"))
    )

    # Esperar y hacer clic en el enlace 'Security'
    security_link = WebDriverWait(side_menu, 10).until(
        EC.element_to_be_clickable((By.XPATH, ".//a[contains(@href, '/wlwpa.asp') and contains(@href, 'wlan_idx=0')]"))
    )
    security_link.click()
    time.sleep(2)

    # Cambiar al iframe 'contentIframe'
    content_iframe = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "contentIframe"))
    )
    driver.switch_to.frame(content_iframe)

    # Ingresar la contraseña WPA en el campo correspondiente
    wpa_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "wpapsk"))
    )
    wpa_input.clear()
    wpa_input.send_keys(wpa_password)

    # Hacer clic en el checkbox para mostrar la contraseña ingresada
    show_password_checkbox = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(1)']"))
    )
    show_password_checkbox.click()

    # Hacer clic en el botón "Apply Changes"
    apply_changes_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
    )
    apply_changes_button.click()
    time.sleep(10)

    # Volver al contexto principal por si estamos en un iframe
    driver.switch_to.default_content()
    
    # Esperar que el menú lateral se recargue después del último Apply Changes
    side_menu = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "side"))
    )

    # Buscar el título <h3> que contiene el enlace wlan1 (2.4GHz)
    wlan1_header = WebDriverWait(side_menu, 10).until(
        EC.element_to_be_clickable((By.XPATH, ".//h3/a[text()='wlan1 (2.4GHz)']"))
    )
    wlan1_header.click()
    time.sleep(2)

    # Cambiar al iframe nuevamente (puede haberse recargado)
    content_iframe = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "contentIframe"))
    )
    driver.switch_to.frame(content_iframe)

    # Cambiar SSID de wlan1
    ssid_input_wlan1 = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "ssid"))
    )
    ssid_input_wlan1.clear()
    ssid_input_wlan1.send_keys(ssid_name)

    # Seleccionar la opción "40MHz" en el campo desplegable "chanwid"
    chanwid_dropdown_wlan1 = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "chanwid"))
    )
    for option in chanwid_dropdown_wlan1.find_elements(By.TAG_NAME, "option"):
        if option.get_attribute("value") == "1":
            option.click()
            break

    # Seleccionar la opción "Auto" en el campo desplegable "chan_select"
    chan_select_dropdown_wlan1 = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "chan_select"))
    )
    for option in chan_select_dropdown_wlan1.find_elements(By.TAG_NAME, "option"):
        if option.get_attribute("value") == "0":
            option.click()
            break

    # Seleccionar la opción "100%" en el campo desplegable "txpower"
    txpower_dropdown_wlan1 = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "txpower"))
    )
    for option in txpower_dropdown_wlan1.find_elements(By.TAG_NAME, "option"):
        if option.get_attribute("value") == "0":
            option.click()
            break

    # Hacer clic en el botón "Apply Changes"
    apply_changes_button_wlan1 = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
    )
    apply_changes_button_wlan1.click()
    time.sleep(5)

     # Volver al contexto principal por si estamos en un iframe
    driver.switch_to.default_content()
    
    # Esperar que el menú lateral se recargue después del último Apply Changes
    side_menu = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "side"))
    )

    # Hacer clic en el enlace 'Security' para wlan1
    security_link_wlan1 = WebDriverWait(side_menu, 10).until(
        EC.element_to_be_clickable((By.XPATH, ".//a[contains(@href, '/wlwpa.asp') and contains(@href, 'wlan_idx=1')]"))
    )
    security_link_wlan1.click()

    # Cambiar al iframe 'contentIframe'
    content_iframe = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "contentIframe"))
    )
    driver.switch_to.frame(content_iframe)

    # Ingresar la contraseña WPA en el campo correspondiente
    wpa_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "wpapsk"))
    )
    wpa_input.clear()
    wpa_input.send_keys(wpa_password)

    # Hacer clic en el checkbox para mostrar la contraseña ingresada
    show_password_checkbox = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(1)']"))
    )
    show_password_checkbox.click()

    # Hacer clic en el botón "Apply Changes"
    apply_changes_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
    )
    apply_changes_button.click()
    time.sleep(10)

     # Volver al contexto principal (por si estamos en un iframe aún)
    driver.switch_to.default_content()

    # Esperar a que el menú nav vuelva a estar presente
    nav_menu = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "nav"))
    )

    # Hacer clic en el enlace 'Admin'
    admin_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@href='javascript:void(0)' and @rel='9']"))
    )
    admin_link.click()

    # Esperar que el menú lateral se cargue
    side_menu = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "side"))
    )

    # Hacer clic en el enlace 'Password'
    password_link = WebDriverWait(side_menu, 10).until(
        EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and @href='password.asp' and text()='Password']"))
    )
    password_link.click()

    # Cambiar al iframe 'contentIframe'
    content_iframe = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "contentIframe"))
    )
    driver.switch_to.frame(content_iframe)

    # Ingresar la contraseña antigua en el campo 'Old Password'
    old_password_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "oldpass"))
    )
    old_password_input.clear()
    old_password_input.send_keys(password)

    # Hacer clic en el checkbox para mostrar la contraseña antigua
    show_old_password_checkbox = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(3)']"))
    )
    show_old_password_checkbox.click()

    # Ingresar la nueva contraseña en el campo 'New Password'
    new_password_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "newpass"))
    )
    new_password_input.clear()
    new_password_input.send_keys(new_password)

    # Hacer clic en el checkbox para mostrar la nueva contraseña
    show_new_password_checkbox = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(1)']"))
    )
    show_new_password_checkbox.click()

    # Ingresar la misma contraseña en el campo 'Confirmed Password'
    confirmed_password_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "confpass"))
    )
    confirmed_password_input.clear()
    confirmed_password_input.send_keys(new_password)

    # Hacer clic en el checkbox para mostrar la contraseña confirmada
    show_confirmed_password_checkbox = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(2)']"))
    )
    show_confirmed_password_checkbox.click()

    # Hacer clic en el botón "Apply Changes"
    apply_changes_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
    )
    apply_changes_button.click()
    time.sleep(5)
    
    # Volver al contexto principal (por si estamos en un iframe aún)
    driver.switch_to.default_content()

    # Esperar a que el menú nav vuelva a estar presente
    nav_menu = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "nav"))
    )

    # Hacer clic en el enlace 'Advance'
    advance_link = WebDriverWait(nav_menu, 10).until(
        EC.element_to_be_clickable((By.XPATH, ".//a[@href='javascript:void(0)' and @rel='7' and text()='Advance']"))
    )
    advance_link.click()

    # Esperar que el menú lateral se cargue
    side_menu = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "side"))
    )

    # Hacer clic en el enlace 'Remote Access'
    remote_access_link = WebDriverWait(side_menu, 10).until(
        EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and @href='rmtacc.asp' and text()='Remote Access']"))
    )
    remote_access_link.click()

    # Cambiar al iframe 'contentIframe'
    content_iframe = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "contentIframe"))
    )
    driver.switch_to.frame(content_iframe)

    # Hacer clic en el checkbox 'w_https'
    https_wan_checkbox = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.NAME, "w_https"))
    )
    https_wan_checkbox.click()

    # Hacer clic en el botón "Apply Changes"
    apply_changes_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='set' and @value='Apply Changes']"))
    )
    apply_changes_button.click()

finally:
    # Mostrar mensaje de finalización mejorado con correo de contacto
    import ctypes
    ctypes.windll.user32.MessageBoxW(
        0, 
        "La configuración del módem y la red Wi-Fi se completó con éxito.\n\n"
        "Si necesitas soporte adicional, no dudes en contactarme:\n"
        "miraglioluis1@gmail.com\n\n"
        "Muchas gracias por utilizar mi Automatización.\n\n"
        "- Luis Miraglio -", 
        "Proceso de Configuración Finalizado", 
        0x40 | 0x1
    )
    time.sleep(15)
    driver.quit()
#Comando para compilar el script en un ejecutable con driver del navegador dentro de la carpeta del Script
#pyinstaller --onefile --add-binary "msedgedriver.exe;." "nombre del archivo.py"