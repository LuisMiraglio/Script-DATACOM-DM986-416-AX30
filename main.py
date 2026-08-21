# main.py
import threading
import os
import sys
from datetime import datetime

import tkinter as tk
from tkinter import ttk, font
from tkinter import messagebox



def resource_path(relative_path: str) -> str:
    """Ruta compatible con ejecución normal y PyInstaller --onefile."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)

from logic_414 import ConfiguradorModem414

try:
    from logic_416 import ConfiguradorModem416
except Exception:
    ConfiguradorModem416 = None

try:
    from logic_414Q import ConfiguradorModem414Q
except Exception:
    ConfiguradorModem414Q = None


# ============================================================
# SCROLLABLE FRAME
# ============================================================
class ScrollableFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.canvas = tk.Canvas(
            self,
            highlightthickness=0,
            bg="#F4F6F8"
        )

        self.v_scroll = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview
        )

        self.canvas.configure(
            yscrollcommand=self.v_scroll.set
        )

        self.v_scroll.pack(
            side="right",
            fill="y"
        )

        self.canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.inner = ttk.Frame(self.canvas)

        self.inner_id = self.canvas.create_window(
            (0, 0),
            window=self.inner,
            anchor="nw"
        )

        self.inner.bind(
            "<Configure>",
            self._on_frame_configure
        )

        self.canvas.bind(
            "<Configure>",
            self._on_canvas_configure
        )

        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.inner)

    def _on_frame_configure(self, _event=None):
        self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        )

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(
            self.inner_id,
            width=event.width
        )

    def _bind_mousewheel(self, widget):
        widget.bind(
            "<Enter>",
            lambda _e: self._activate_mousewheel()
        )

        widget.bind(
            "<Leave>",
            lambda _e: self._deactivate_mousewheel()
        )

    def _activate_mousewheel(self):
        self.canvas.bind_all(
            "<MouseWheel>",
            self._on_mousewheel
        )

        self.canvas.bind_all(
            "<Button-4>",
            self._on_mousewheel_linux
        )

        self.canvas.bind_all(
            "<Button-5>",
            self._on_mousewheel_linux
        )

    def _deactivate_mousewheel(self):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(
            int(-1 * (event.delta / 120)),
            "units"
        )

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(
                -1,
                "units"
            )

        elif event.num == 5:
            self.canvas.yview_scroll(
                1,
                "units"
            )


# ============================================================
# UI PRINCIPAL
# ============================================================
class MainApp:

    def __init__(self, root: tk.Tk):
        self.root = root

        self.root.title(
            "Configurador Automático Datacom DM986"
        )

        # ========================================================
        # VENTANA
        # ========================================================
        self.root.geometry("1050x900")
        self.root.minsize(900, 760)
        self.root.resizable(True, True)

        self.root.configure(
            bg="#F4F6F8"
        )

        # ========================================================
        # ICONO
        # ========================================================
        try:
            self.root.iconbitmap(
                resource_path("assets/icons/icono.ico")
            )
        except Exception:
            pass

        # ========================================================
        # PALETA - IDENTIDAD VISUAL CONECTAR
        # ========================================================
        self.primary_color = "#1F3859"
        self.primary_dark = "#172D49"

        self.accent_color = "#F15A3A"
        self.topbar_color = "#0099BC"

        self.bg_color = "#F4F6F8"
        self.card_color = "#FFFFFF"

        self.text_color = "#1F2937"
        self.secondary_text = "#667085"

        self.success_color = "#16803C"
        self.error_color = "#C62828"
        self.warning_color = "#D97706"

        self.border_color = "#D7DDE5"

        # ========================================================
        # VARIABLES
        # ========================================================
        self.modelo = tk.StringVar(
            value="DM986-416 AX30"
        )

        self.browser_choice = tk.StringVar(
            value="Google Chrome"
        )

        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.ssid_name = tk.StringVar()
        self.wpa_password = tk.StringVar()
        self.new_password = tk.StringVar()

        self.status_var = tk.StringVar(
            value="Listo para iniciar"
        )

        self.current_step_var = tk.StringVar(
            value="Sin proceso activo"
        )

        self.progress_text_var = tk.StringVar(
            value="0 / 10"
        )

        self.percent_var = tk.StringVar(
            value="0 %"
        )

        self.summary_model_var = tk.StringVar(
            value=self.modelo.get()
        )

        self.result_var = tk.StringVar(
            value="LISTO PARA CONFIGURAR"
        )

        # ========================================================
        # ESTADOS DE CHECKLIST
        # ========================================================
        self.steps = [
            "Acceso al equipo",
            "VLAN 500",
            "VLAN 600",
            "WiFi 5 GHz",
            "Seguridad WiFi 5 GHz",
            "WiFi 2.4 GHz",
            "Seguridad WiFi 2.4 GHz",
            "Contraseña administrador",
            "TR-069",
            "Remote Access HTTPS",
        ]

        self.step_states = {
            step: "pending"
            for step in self.steps
        }

        self.step_labels = {}

        # ========================================================
        # FUENTES
        # ========================================================
        self.title_font = font.Font(
            family="Segoe UI",
            size=17,
            weight="bold"
        )

        self.subtitle_font = font.Font(
            family="Segoe UI",
            size=11
        )

        self.header_font = font.Font(
            family="Segoe UI",
            size=11,
            weight="bold"
        )

        self.normal_font = font.Font(
            family="Segoe UI",
            size=10
        )

        self.small_font = font.Font(
            family="Segoe UI",
            size=9
        )

        self.result_font = font.Font(
            family="Segoe UI",
            size=13,
            weight="bold"
        )

        # ========================================================
        # ESTILOS TTK
        # ========================================================
        self.style = ttk.Style()

        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure(
            "TFrame",
            background=self.bg_color
        )

        self.style.configure(
            "Card.TFrame",
            background=self.card_color
        )

        self.style.configure(
            "TLabel",
            background=self.bg_color,
            foreground=self.text_color,
            font=self.normal_font
        )

        self.style.configure(
            "Card.TLabel",
            background=self.card_color,
            foreground=self.text_color,
            font=self.normal_font
        )

        self.style.configure(
            "Section.TLabel",
            background=self.card_color,
            foreground=self.text_color,
            font=self.header_font
        )

        self.style.configure(
            "Status.TLabel",
            background=self.card_color,
            foreground=self.primary_color,
            font=self.normal_font
        )

        self.style.configure(
            "TProgressbar",
            troughcolor="#E5E7EB",
            background=self.primary_color,
            thickness=12
        )

        # ========================================================
        # HEADER
        # ========================================================
        self.top_accent = tk.Frame(
            self.root,
            bg=self.topbar_color,
            height=5
        )

        self.top_accent.pack(
            fill=tk.X
        )

        self.top_accent.pack_propagate(False)

        self.header_frame = tk.Frame(
            self.root,
            bg=self.primary_color,
            height=64
        )

        self.header_frame.pack(
            fill=tk.X
        )

        self.header_frame.pack_propagate(False)

        tk.Label(
            self.header_frame,
            text="CONFIGURADOR AUTOMÁTICO DATACOM DM986",
            bg=self.primary_color,
            fg="white",
            font=self.title_font
        ).pack(
            pady=(10, 0)
        )

        tk.Label(
            self.header_frame,
            text="Configuración y validación automática de equipos",
            bg=self.primary_color,
            fg="#DCE6F2",
            font=self.small_font
        ).pack()

        self.bottom_accent = tk.Frame(
            self.root,
            bg=self.accent_color,
            height=3
        )

        self.bottom_accent.pack(
            fill=tk.X
        )

        self.bottom_accent.pack_propagate(False)

        # ========================================================
        # ÁREA SCROLLABLE
        # ========================================================
        self.scroll_area = ScrollableFrame(
            self.root
        )

        self.scroll_area.pack(
            fill=tk.BOTH,
            expand=True
        )

        # Contenedor central
        self.main_frame = ttk.Frame(
            self.scroll_area.inner,
            padding="20"
        )

        self.main_frame.pack(
            fill=tk.BOTH,
            expand=True
        )

        # ========================================================
        # SELECTOR DE MODELO
        # ========================================================
        self._crear_selector_modelo()

        # ========================================================
        # NAVEGADOR
        # ========================================================
        self._crear_selector_navegador()

        # ========================================================
        # FORMULARIO
        # ========================================================
        self._crear_formulario()

        # ========================================================
        # BOTÓN PRINCIPAL
        # ========================================================
        self._crear_boton_principal()

        # ========================================================
        # ESTADO GENERAL
        # ========================================================
        self._crear_estado_general()

        # ========================================================
        # CHECKLIST
        # ========================================================
        self._crear_checklist()

        # ========================================================
        # REGISTRO
        # ========================================================
        self._crear_registro()

        # ========================================================
        # FOOTER
        # ========================================================
        footer = ttk.Frame(
            self.root,
            style="TFrame"
        )

        footer.pack(
            fill=tk.X,
            side=tk.BOTTOM,
            pady=4
        )

        ttk.Label(
            footer,
            text="© Luis Miraglio | miraglioluis1@gmail.com",
            font=self.small_font
        ).pack(
            side=tk.RIGHT,
            padx=15
        )

    # ============================================================
    # CREAR SELECTOR DE MODELO
    # ============================================================
    def _crear_selector_modelo(self):

        frame = tk.Frame(
            self.main_frame,
            bg=self.card_color,
            bd=1,
            relief=tk.SOLID
        )

        frame.pack(
            fill=tk.X,
            pady=(0, 12)
        )

        tk.Label(
            frame,
            text="SELECCIONÁ EL MODELO",
            bg=self.card_color,
            fg=self.text_color,
            font=self.header_font
        ).pack(
            anchor="w",
            padx=18,
            pady=(14, 8)
        )

        button_frame = tk.Frame(
            frame,
            bg=self.card_color
        )

        button_frame.pack(
            padx=18,
            pady=(0, 16),
            anchor="w"
        )

        self.model_buttons = {}

        modelos = [
            "DM986-414",
            "DM986-414 Q",
            "DM986-416 AX30"
        ]

        for modelo in modelos:

            btn = tk.Button(
                button_frame,
                text=modelo,
                width=20,
                height=2,
                font=("Segoe UI", 10, "bold"),
                command=lambda m=modelo: self._select_model(m),
                relief=tk.FLAT,
                cursor="hand2"
            )

            btn.pack(
                side=tk.LEFT,
                padx=(0, 10)
            )

            self.model_buttons[modelo] = btn

        self._refresh_model_buttons()

    # ============================================================
    # SELECTOR NAVEGADOR
    # ============================================================
    def _crear_selector_navegador(self):

        frame = tk.Frame(
            self.main_frame,
            bg=self.card_color,
            bd=1,
            relief=tk.SOLID
        )

        frame.pack(
            fill=tk.X,
            pady=(0, 12)
        )

        content = tk.Frame(
            frame,
            bg=self.card_color
        )

        content.pack(
            fill=tk.X,
            padx=18,
            pady=14
        )

        tk.Label(
            content,
            text="Navegador:",
            bg=self.card_color,
            fg=self.text_color,
            font=self.normal_font
        ).pack(
            side=tk.LEFT
        )

        self.cb_browser = ttk.Combobox(
            content,
            state="readonly",
            width=25,
            textvariable=self.browser_choice,
            values=[
                "Google Chrome",
                "Microsoft Edge",
                "Firefox",
                "Autodetectar"
            ]
        )

        self.cb_browser.pack(
            side=tk.LEFT,
            padx=(10, 8)
        )

        tk.Label(
            content,
            text="Recomendado: Google Chrome",
            bg=self.card_color,
            fg=self.success_color,
            font=self.small_font
        ).pack(
            side=tk.LEFT
        )

    # ============================================================
    # FORMULARIO
    # ============================================================
    def _crear_formulario(self):

        frame = tk.Frame(
            self.main_frame,
            bg=self.card_color,
            bd=1,
            relief=tk.SOLID
        )

        frame.pack(
            fill=tk.X,
            pady=(0, 12)
        )

        tk.Label(
            frame,
            text="INFORMACIÓN DEL EQUIPO",
            bg=self.card_color,
            fg=self.text_color,
            font=self.header_font
        ).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="w",
            padx=18,
            pady=(14, 10)
        )

        campos = [
            (
                "Usuario del módem",
                self.username,
                False
            ),
            (
                "Contraseña actual",
                self.password,
                True
            ),
            (
                "Nombre de red Wi-Fi (SSID)",
                self.ssid_name,
                False
            ),
            (
                "Contraseña Wi-Fi",
                self.wpa_password,
                True
            ),
            (
                "Nueva contraseña admin",
                self.new_password,
                True
            ),
        ]

        self.entries = {}

        for i, (label, variable, password) in enumerate(
            campos,
            start=1
        ):

            tk.Label(
                frame,
                text=label,
                bg=self.card_color,
                fg=self.text_color,
                font=self.normal_font
            ).grid(
                row=i,
                column=0,
                sticky="w",
                padx=(18, 12),
                pady=7
            )

            entry = ttk.Entry(
                frame,
                textvariable=variable,
                width=38
            )

            entry.grid(
                row=i,
                column=1,
                sticky="w",
                pady=7
            )

            self.entries[label] = entry

            if password:

                entry.configure(
                    show="*"
                )

                show_var = tk.BooleanVar(
                    value=False
                )

                btn_show = ttk.Checkbutton(
                    frame,
                    text="Mostrar",
                    variable=show_var,
                    command=lambda e=entry, v=show_var:
                        self._toggle_password(e, v)
                )

                btn_show.grid(
                    row=i,
                    column=2,
                    sticky="w",
                    padx=10
                )

        # Línea de validación
        self.validation_var = tk.StringVar(
            value=""
        )

        self.validation_label = tk.Label(
            frame,
            textvariable=self.validation_var,
            bg=self.card_color,
            fg=self.error_color,
            font=self.small_font
        )

        self.validation_label.grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="w",
            padx=18,
            pady=(5, 14)
        )

    # ============================================================
    # BOTÓN PRINCIPAL
    # ============================================================
    def _crear_boton_principal(self):

        frame = tk.Frame(
            self.main_frame,
            bg=self.bg_color
        )

        frame.pack(
            fill=tk.X,
            pady=(5, 12)
        )

        self.btn_run = tk.Button(
            frame,
            text="▶  INICIAR CONFIGURACIÓN",
            command=self.on_run,
            bg=self.primary_color,
            activebackground=self.primary_dark,
            fg="white",
            activeforeground="white",
            font=("Segoe UI", 11, "bold"),
            width=28,
            height=2,
            relief=tk.FLAT,
            cursor="hand2"
        )

        self.btn_run.pack()

    # ============================================================
    # ESTADO GENERAL
    # ============================================================
    def _crear_estado_general(self):

        frame = tk.Frame(
            self.main_frame,
            bg=self.card_color,
            bd=1,
            relief=tk.SOLID
        )

        frame.pack(
            fill=tk.X,
            pady=(0, 12)
        )

        tk.Label(
            frame,
            text="ESTADO DE LA CONFIGURACIÓN",
            bg=self.card_color,
            fg=self.text_color,
            font=self.header_font
        ).pack(
            anchor="w",
            padx=18,
            pady=(14, 8)
        )

        info = tk.Frame(
            frame,
            bg=self.card_color
        )

        info.pack(
            fill=tk.X,
            padx=18
        )

        # Modelo
        tk.Label(
            info,
            text="Modelo:",
            bg=self.card_color,
            fg=self.secondary_text,
            font=self.small_font
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        tk.Label(
            info,
            textvariable=self.summary_model_var,
            bg=self.card_color,
            fg=self.text_color,
            font=self.normal_font
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(5, 25)
        )

        # Estado
        tk.Label(
            info,
            text="Estado:",
            bg=self.card_color,
            fg=self.secondary_text,
            font=self.small_font
        ).grid(
            row=0,
            column=2,
            sticky="w"
        )

        self.status_value_label = tk.Label(
            info,
            textvariable=self.status_var,
            bg=self.card_color,
            fg=self.primary_color,
            font=self.normal_font
        )

        self.status_value_label.grid(
            row=0,
            column=3,
            sticky="w",
            padx=(5, 25)
        )

        # Paso
        tk.Label(
            info,
            text="Paso actual:",
            bg=self.card_color,
            fg=self.secondary_text,
            font=self.small_font
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(8, 0)
        )

        tk.Label(
            info,
            textvariable=self.current_step_var,
            bg=self.card_color,
            fg=self.text_color,
            font=self.normal_font
        ).grid(
            row=1,
            column=1,
            columnspan=3,
            sticky="w",
            padx=(5, 0),
            pady=(8, 0)
        )

        # Progress
        progress_container = tk.Frame(
            frame,
            bg=self.card_color
        )

        progress_container.pack(
            fill=tk.X,
            padx=18,
            pady=(14, 8)
        )

        self.progress = ttk.Progressbar(
            progress_container,
            orient="horizontal",
            mode="determinate",
            maximum=len(self.steps),
            value=0,
            style="TProgressbar"
        )

        self.progress.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True
        )

        tk.Label(
            progress_container,
            textvariable=self.percent_var,
            bg=self.card_color,
            fg=self.text_color,
            font=self.normal_font,
            width=8
        ).pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        # Resultado
        self.result_label = tk.Label(
            frame,
            textvariable=self.result_var,
            bg=self.card_color,
            fg=self.primary_color,
            font=self.result_font
        )

        self.result_label.pack(
            anchor="w",
            padx=18,
            pady=(4, 14)
        )

    # ============================================================
    # CHECKLIST
    # ============================================================
    def _crear_checklist(self):

        frame = tk.Frame(
            self.main_frame,
            bg=self.card_color,
            bd=1,
            relief=tk.SOLID
        )

        frame.pack(
            fill=tk.X,
            pady=(0, 12)
        )

        tk.Label(
            frame,
            text="VERIFICACIONES",
            bg=self.card_color,
            fg=self.text_color,
            font=self.header_font
        ).pack(
            anchor="w",
            padx=18,
            pady=(14, 4)
        )

        tk.Label(
            frame,
            text="✓ Verificado    ● Aplicado sin verificación    ⏳ En proceso    ○ Pendiente    ✕ Error",
            bg=self.card_color,
            fg=self.secondary_text,
            font=self.small_font
        ).pack(
            anchor="w",
            padx=18,
            pady=(0, 8)
        )

        grid_frame = tk.Frame(
            frame,
            bg=self.card_color
        )

        grid_frame.pack(
            fill=tk.X,
            padx=18,
            pady=(0, 14)
        )

        for index, step in enumerate(self.steps):

            row = index // 2
            col = index % 2

            label = tk.Label(
                grid_frame,
                text=f"○  {step}",
                bg=self.card_color,
                fg=self.secondary_text,
                font=self.normal_font,
                anchor="w"
            )

            label.grid(
                row=row,
                column=col,
                sticky="w",
                padx=(0, 60),
                pady=5
            )

            self.step_labels[step] = label

    # ============================================================
    # REGISTRO
    # ============================================================
    def _crear_registro(self):

        frame = tk.Frame(
            self.main_frame,
            bg=self.card_color,
            bd=1,
            relief=tk.SOLID
        )

        frame.pack(
            fill=tk.BOTH,
            expand=True,
            pady=(0, 10)
        )

        tk.Label(
            frame,
            text="REGISTRO DETALLADO DEL PROCESO",
            bg=self.card_color,
            fg=self.text_color,
            font=self.header_font
        ).pack(
            anchor="w",
            padx=18,
            pady=(14, 8)
        )

        container = tk.Frame(
            frame,
            bg=self.card_color
        )

        container.pack(
            fill=tk.BOTH,
            expand=True,
            padx=18,
            pady=(0, 14)
        )

        self.log_scrollbar = ttk.Scrollbar(
            container,
            orient="vertical"
        )

        self.log_scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y
        )

        self.log_text = tk.Text(
            container,
            height=12,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#FBFCFD",
            fg=self.text_color,
            relief=tk.FLAT,
            bd=1,
            state="disabled",
            yscrollcommand=self.log_scrollbar.set
        )

        self.log_text.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True
        )

        self.log_scrollbar.config(
            command=self.log_text.yview
        )

    # ============================================================
    # MODELOS
    # ============================================================
    def _select_model(self, model):

        self.modelo.set(model)

        self.summary_model_var.set(model)

        self._refresh_model_buttons()

        self._on_model_change()

    def _refresh_model_buttons(self):

        selected = self.modelo.get()

        for model, button in self.model_buttons.items():

            if model == selected:

                button.configure(
                    bg=self.primary_color,
                    fg="white",
                    activebackground=self.primary_dark,
                    activeforeground="white",
                    relief=tk.FLAT
                )

            else:

                button.configure(
                    bg="#E9EDF2",
                    fg=self.text_color,
                    activebackground="#D9E1EA",
                    activeforeground=self.text_color,
                    relief=tk.FLAT
                )

    def _on_model_change(self, _event=None):
        pass

    # ============================================================
    # UI ADAPTER
    # ============================================================
    def actualizar_estado(self, msg: str):

        def _update():

            self.status_var.set(
                msg
            )

            self._actualizar_checklist_por_mensaje(
                msg
            )

            timestamp = datetime.now().strftime(
                "%H:%M:%S"
            )

            self.log_text.config(
                state="normal"
            )

            self.log_text.insert(
                tk.END,
                f"{timestamp}  {msg}\n"
            )

            self.log_text.see(
                tk.END
            )

            self.log_text.config(
                state="disabled"
            )

        self.root.after(
            0,
            _update
        )

    # ============================================================
    # CHECKLIST SEGÚN MENSAJES DEL LOGIC
    # ============================================================
    def _actualizar_checklist_por_mensaje(self, msg):

        texto = msg.lower()

        # ========================================================
        # ACCESO
        # ========================================================
        if (
            "esperando interfaz del modem" in texto
            or "esperando interfaz del módem" in texto
        ):
            self._set_step_state(
                "Acceso al equipo",
                "running"
            )

        if "configurando wan vlan 500" in texto:
            self._set_step_state(
                "Acceso al equipo",
                "success"
            )

            self._set_step_state(
                "VLAN 500",
                "running"
            )

        # ========================================================
        # VLAN 500
        # ========================================================
        if (
            "vlan 500 configurada y verificada" in texto
        ):
            self._set_step_state(
                "VLAN 500",
                "success"
            )

        # ========================================================
        # VLAN 600
        # ========================================================
        if "configurando wan vlan 600" in texto:
            self._set_step_state(
                "VLAN 600",
                "running"
            )

        if (
            "vlan 600 configurada y verificada" in texto
        ):
            self._set_step_state(
                "VLAN 600",
                "success"
            )

        # ========================================================
        # WIFI 5
        # ========================================================
        if (
            "abriendo wlan (5ghz)" in texto
            or "configurando wlan 5ghz" in texto
        ):
            self._set_step_state(
                "WiFi 5 GHz",
                "running"
            )

        if (
            "wifi 5 ghz configurado y verificado" in texto
        ):
            self._set_step_state(
                "WiFi 5 GHz",
                "success"
            )

        # ========================================================
        # SEGURIDAD 5
        # ========================================================
        if (
            "configurando seguridad wifi 5ghz" in texto
        ):
            if self.step_states.get("WiFi 5 GHz") == "running":
                self._set_step_state("WiFi 5 GHz", "applied")

            self._set_step_state(
                "Seguridad WiFi 5 GHz",
                "running"
            )

        if (
            "seguridad wifi 5 ghz configurada y verificada"
            in texto
        ):
            self._set_step_state(
                "Seguridad WiFi 5 GHz",
                "success"
            )

        # ========================================================
        # WIFI 2.4
        # ========================================================
        if (
            "configurando wifi 2.4ghz" in texto
            or "configurando wlan 2.4ghz" in texto
        ):
            if self.step_states.get("Seguridad WiFi 5 GHz") == "running":
                self._set_step_state("Seguridad WiFi 5 GHz", "applied")

            self._set_step_state(
                "WiFi 2.4 GHz",
                "running"
            )

        if (
            "wifi 2.4 ghz configurado y verificado" in texto
        ):
            self._set_step_state(
                "WiFi 2.4 GHz",
                "success"
            )

        # ========================================================
        # SEGURIDAD 2.4
        # ========================================================
        if (
            "configurando seguridad wifi 2.4ghz"
            in texto
        ):
            if self.step_states.get("WiFi 2.4 GHz") == "running":
                self._set_step_state("WiFi 2.4 GHz", "applied")

            self._set_step_state(
                "Seguridad WiFi 2.4 GHz",
                "running"
            )

        if (
            "seguridad wifi 2.4 ghz configurada y verificada"
            in texto
        ):
            self._set_step_state(
                "Seguridad WiFi 2.4 GHz",
                "success"
            )

        # ========================================================
        # PASSWORD
        # ========================================================
        if (
            "cambiando contraseña de administrador"
            in texto
        ):
            if self.step_states.get("Seguridad WiFi 2.4 GHz") == "running":
                self._set_step_state("Seguridad WiFi 2.4 GHz", "applied")

            self._set_step_state(
                "Contraseña administrador",
                "running"
            )

        if (
            "contraseña de administrador cambiada y verificada"
            in texto
        ):
            self._set_step_state(
                "Contraseña administrador",
                "success"
            )

        # ========================================================
        # TR069
        # ========================================================
        if (
            "configurando tr-069" in texto
        ):
            if self.step_states.get("Contraseña administrador") == "running":
                self._set_step_state("Contraseña administrador", "applied")

            self._set_step_state(
                "TR-069",
                "running"
            )

        if (
            "tr-069 configurado y verificado"
            in texto
        ):
            self._set_step_state(
                "TR-069",
                "success"
            )

        # ========================================================
        # REMOTE ACCESS
        # ========================================================
        if (
            "configurando remote access" in texto
        ):
            if self.step_states.get("TR-069") == "running":
                self._set_step_state("TR-069", "applied")

            self._set_step_state(
                "Remote Access HTTPS",
                "running"
            )

        if (
            "remote access https configurado y verificado"
            in texto
        ):
            self._set_step_state(
                "Remote Access HTTPS",
                "success"
            )

        # ========================================================
        # FINALIZACIÓN SIN VERIFICACIÓN COMPLETA
        # ========================================================
        if (
            "configuración dm986-414 completada" in texto
            or "configuracion dm986-414 completada" in texto
            or "configuración dm986-414 q completada" in texto
            or "configuracion dm986-414 q completada" in texto
        ):
            for step in self.steps:
                if self.step_states.get(step) == "running":
                    self._set_step_state(step, "applied")

        # ========================================================
        # ERRORES
        # ========================================================
        if msg.startswith("❌"):

            for step in self.steps:

                if self.step_states.get(step) == "running":

                    self._set_step_state(
                        step,
                        "error"
                    )

                    break

    # ============================================================
    # CAMBIAR ESTADO DE PASO
    # ============================================================
    def _set_step_state(self, step, state):

        if step not in self.step_states:
            return

        self.step_states[step] = state

        label = self.step_labels.get(step)

        if not label:
            return

        if state == "pending":

            label.config(
                text=f"○  {step}",
                fg=self.secondary_text
            )

        elif state == "running":

            label.config(
                text=f"⏳  {step}",
                fg=self.primary_color
            )

            self.current_step_var.set(
                step
            )

        elif state == "applied":

            label.config(
                text=f"●  {step}",
                fg=self.warning_color
            )

        elif state == "success":

            label.config(
                text=f"✓  {step}",
                fg=self.success_color
            )

        elif state == "error":

            label.config(
                text=f"✕  {step}",
                fg=self.error_color
            )

        self._actualizar_progreso_real()

    # ============================================================
    # PROGRESO REAL
    # ============================================================
    def _actualizar_progreso_real(self):

        completados = sum(
            1
            for state in self.step_states.values()
            if state == "success"
        )

        total = len(
            self.steps
        )

        self.progress["value"] = completados

        porcentaje = int(
            (completados / total) * 100
        )

        self.progress_text_var.set(
            f"{completados} / {total}"
        )

        self.percent_var.set(
            f"{porcentaje} %"
        )

    # ============================================================
    # MESSAGEBOX
    # ============================================================
    def safe_messagebox(
        self,
        title: str,
        text: str,
        kind: str = "error"
    ):

        def _show():

            if kind == "error":
                messagebox.showerror(
                    title,
                    text
                )

            elif kind == "warning":
                messagebox.showwarning(
                    title,
                    text
                )

            else:
                messagebox.showinfo(
                    title,
                    text
                )

        self.root.after(
            0,
            _show
        )

    # ============================================================
    # NAVEGADOR
    # ============================================================
    def get_browser_choice(self) -> str:

        txt = self.browser_choice.get()

        mapping = {
            "Google Chrome": "chrome",
            "Microsoft Edge": "edge",
            "Firefox": "firefox",
            "Autodetectar": "auto",
        }

        return mapping.get(
            txt,
            "chrome"
        )

    # ============================================================
    # CREDENCIALES
    # ============================================================
    def get_credentials(self) -> dict:

        return {
            "username": self.username.get().strip(),
            "password": self.password.get().strip(),
            "ssid": self.ssid_name.get().strip(),
            "wpa": self.wpa_password.get().strip(),
            "new_password": self.new_password.get().strip(),
        }

    def get_extra_wifi_config(self) -> dict:
        return {
            "enabled": False
        }

    # ============================================================
    # MOSTRAR / OCULTAR PASSWORD
    # ============================================================
    def _toggle_password(
        self,
        entry,
        show_var
    ):

        entry.configure(
            show="" if show_var.get() else "*"
        )

    # ============================================================
    # VALIDACIÓN
    # ============================================================
    def _validate_required(self) -> bool:

        creds = self.get_credentials()

        campos = [
            (
                "Usuario del módem",
                creds["username"]
            ),
            (
                "Contraseña actual",
                creds["password"]
            ),
            (
                "Nombre de red Wi-Fi",
                creds["ssid"]
            ),
            (
                "Contraseña Wi-Fi",
                creds["wpa"]
            ),
            (
                "Nueva contraseña admin",
                creds["new_password"]
            ),
        ]

        faltantes = [
            nombre
            for nombre, valor in campos
            if not valor
        ]

        if faltantes:

            self.validation_var.set(
                "⚠ Completá todos los campos obligatorios."
            )

            return False

        self.validation_var.set("")

        return True

    # ============================================================
    # BOTÓN ENABLE / DISABLE
    # ============================================================
    def set_buttons_enabled(
        self,
        enabled: bool
    ):

        def _set():

            if enabled:

                self.btn_run.config(
                    state="normal",
                    text="▶  INICIAR CONFIGURACIÓN",
                    bg=self.primary_color
                )

            else:

                self.btn_run.config(
                    state="disabled",
                    text="⏳  CONFIGURANDO...",
                    bg="#9CA3AF"
                )

            # Bloqueamos también modelos y navegador
            state = "normal" if enabled else "disabled"

            for button in self.model_buttons.values():

                button.config(
                    state=state
                )

            self.cb_browser.config(
                state="readonly"
                if enabled
                else "disabled"
            )

        self.root.after(
            0,
            _set
        )

    # ============================================================
    # LIMPIAR REGISTRO
    # ============================================================
    def limpiar_registro(self):

        def _clear():

            self.log_text.config(
                state="normal"
            )

            self.log_text.delete(
                "1.0",
                tk.END
            )

            self.log_text.config(
                state="disabled"
            )

        self.root.after(
            0,
            _clear
        )

    # ============================================================
    # REINICIAR CHECKLIST
    # ============================================================
    def _reset_checklist(self):

        for step in self.steps:

            self.step_states[step] = "pending"

            label = self.step_labels.get(step)

            if label:

                label.config(
                    text=f"○  {step}",
                    fg=self.secondary_text
                )

        self.progress["value"] = 0

        self.percent_var.set(
            "0 %"
        )

        self.progress_text_var.set(
            f"0 / {len(self.steps)}"
        )

        self.current_step_var.set(
            "Preparando configuración"
        )

    # ============================================================
    # RUN
    # ============================================================
    def on_run(self):

        if not self._validate_required():

            self.safe_messagebox(
                "Campos incompletos",
                "Completá todos los campos antes de iniciar la configuración.",
                kind="warning"
            )

            return

        model = self.modelo.get()

        self.summary_model_var.set(
            model
        )

        self.limpiar_registro()

        self._reset_checklist()

        self.result_var.set(
            "CONFIGURACIÓN EN PROCESO"
        )

        self.result_label.config(
            fg=self.primary_color
        )

        self.set_buttons_enabled(
            False
        )

        self.actualizar_estado(
            f"Iniciando configuración para {model}..."
        )

        threading.Thread(
            target=self._run_worker,
            daemon=True
        ).start()

    # ============================================================
    # WORKER
    # ============================================================
    def _run_worker(self):

        try:

            model = self.modelo.get()

            if model == "DM986-416 AX30":

                if ConfiguradorModem416 is None:

                    raise Exception(
                        "No se pudo importar logic_416.py "
                        "(ConfiguradorModem416)."
                    )

                logic = ConfiguradorModem416(
                    self
                )

            elif model == "DM986-414 Q":

                if ConfiguradorModem414Q is None:

                    raise Exception(
                        "No se pudo importar logic_414Q.py "
                        "(ConfiguradorModem414Q)."
                    )

                logic = ConfiguradorModem414Q(
                    self
                )

            else:

                logic = ConfiguradorModem414(
                    self
                )

            ok = logic.run()

            if ok:

                self.actualizar_estado(
                    "✅ Proceso finalizado"
                )

                self.root.after(
                    0,
                    self._marcar_resultado_exitoso
                )

            else:

                self.actualizar_estado(
                    "❌ Proceso finalizado con errores"
                )

                self.root.after(
                    0,
                    self._marcar_resultado_error
                )

        except Exception:

            self.actualizar_estado(
                "❌ Error inesperado en la ejecución"
            )

            self.safe_messagebox(
                "Error",
                "Ocurrió un error inesperado al iniciar o ejecutar el proceso.",
                kind="error"
            )

            self.root.after(
                0,
                self._marcar_resultado_error
            )

        finally:

            self.set_buttons_enabled(
                True
            )

    # ============================================================
    # RESULTADO EXITOSO
    # ============================================================
    def _marcar_resultado_exitoso(self):

        verificados = sum(
            1
            for state in self.step_states.values()
            if state == "success"
        )

        aplicados = sum(
            1
            for state in self.step_states.values()
            if state == "applied"
        )

        total = len(
            self.steps
        )

        self.status_var.set(
            "Configuración completada"
        )

        self.current_step_var.set(
            "Proceso finalizado"
        )

        if verificados == total:

            self.result_var.set(
                f"✅ EQUIPO CONFIGURADO Y VERIFICADO CORRECTAMENTE · "
                f"{verificados}/{total} verificaciones"
            )

            self.result_label.config(
                fg=self.success_color
            )

        else:

            self.result_var.set(
                f"⚠ CONFIGURACIÓN FINALIZADA · "
                f"{verificados}/{total} verificaciones confirmadas"
            )

            self.result_label.config(
                fg=self.warning_color
            )

    # ============================================================
    # RESULTADO ERROR
    # ============================================================
    def _marcar_resultado_error(self):

        completados = sum(
            1
            for state in self.step_states.values()
            if state == "success"
        )

        total = len(
            self.steps
        )

        self.status_var.set(
            "Configuración incompleta"
        )

        self.result_var.set(
            f"❌ CONFIGURACIÓN INCOMPLETA · "
            f"{completados}/{total} verificaciones correctas"
        )

        self.result_label.config(
            fg=self.error_color
        )


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":

    root = tk.Tk()

    app = MainApp(
        root
    )

    root.mainloop()