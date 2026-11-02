"""
overlay.py — Superposición de rendimiento (Gaming Overlay) para PC Rescue 2.0.

Inspirado en el concepto funcional de MSI Afterburner / RTSS, con identidad visual propia
para PC Rescue:
  - Encabezado: PC RESCUE | GAMING con botón de cierre rápido.
  - CPU: porcentaje de uso y temperatura (°C o N/D si no hay sensor disponible).
  - GPU: utilización del motor gráfico y temperatura (°C o N/D).
  - RAM: memoria utilizada respecto del total (GB) y porcentaje de ocupación.

Características de integración:
  - Always-on-Top flotante sin barra de título nativa ni bordes molestos.
  - Transparencia configurable (60% a 100%) con fondo oscuro moderno (#0A0D14).
  - No roba el foco a los videojuegos ni aplicaciones (WS_EX_NOACTIVATE).
  - Modo clic transparente (click-through) opcional para máxima compatibilidad.
  - Arrastrable a cualquier punto de la pantalla con el botón izquierdo del ratón.
  - La ventana principal de PC Rescue puede minimizarse sin que el overlay desaparezca.
  - Cerrar el overlay no cierra PC Rescue.
  - Al cerrar PC Rescue, el overlay se destruye limpiamente sin dejar procesos residuales.
"""

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk, messagebox


# Constantes de Win32 para ventana no intrusiva
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

# Paleta visual del Overlay (estética MSI Afterburner / PC Rescue Dark)
C_OV_BG         = "#0A0D14"  # Fondo oscuro profundo
C_OV_BORDER     = "#1E293B"  # Borde discreto
C_OV_TEXT       = "#F8FAFC"  # Blanco nítido de alta visibilidad
C_OV_TEXT_DIM   = "#64748B"  # Texto secundario / N/D
C_OV_TEXT_MUTED = "#94A3B8"  # Texto informativo

# Distintivos cromáticos para métricas
C_BADGE_CPU_BG  = "#172554"  # Azul profundo
C_BADGE_CPU_FG  = "#38BDF8"  # Cian / celeste neón

C_BADGE_GPU_BG  = "#064E3B"  # Verde esmeralda profundo
C_BADGE_GPU_FG  = "#34D399"  # Verde menta / lima neón

C_BADGE_RAM_BG  = "#451A03"  # Ámbar oscuro
C_BADGE_RAM_FG  = "#FBBF24"  # Ámbar brillante


def resource_path(relative_path):
    """Obtiene la ruta absoluta a un recurso, compatible con desarrollo y PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


# =====================================================================
#  GESTIÓN DE CONFIGURACIÓN DEL OVERLAY
# =====================================================================
class OverlayConfig:
    """Gestiona la persistencia de las preferencias del Gaming Overlay."""

    CONFIG_FILE = Path.home() / ".pc_rescue_overlay_config.json"

    DEFAULT_SETTINGS = {
        "enabled": False,
        "position": "top_left",       # top_left, top_right, bottom_left, bottom_right, custom
        "custom_x": 20,
        "custom_y": 20,
        "size": "compact",             # compact, large
        "opacity": 0.85,               # 0.5 a 1.0
        "update_interval_ms": 1000,    # 500, 1000, 2000
        "click_through": False,        # Si es True, los clics atraviesan la ventana
    }

    def __init__(self):
        self.settings = dict(self.DEFAULT_SETTINGS)
        self.load()

    def load(self):
        """Carga las preferencias desde archivo JSON si existe."""
        if self.CONFIG_FILE.is_file():
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.settings.update(loaded)
            except Exception:
                pass

    def save(self):
        """Guarda las preferencias actuales en archivo JSON."""
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()


# =====================================================================
#  VENTANA FLOTANTE DEL OVERLAY ESTILO MSI AFTERBURNER
# =====================================================================
class GamingOverlayWindow(tk.Toplevel):
    """Superposición de rendimiento inspirada en MSI Afterburner para PC Rescue."""

    def __init__(self, master, config: OverlayConfig, on_close_callback=None):
        super().__init__(master)
        self.config = config
        self.on_close_callback = on_close_callback
        self._is_active = True

        # Configuración básica de ventana
        self.title("PC Rescue Gaming Overlay")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=C_OV_BORDER)

        # Icono si está disponible
        ico_file = resource_path(os.path.join("assets", "icon.ico"))
        if os.path.isfile(ico_file):
            try:
                self.iconbitmap(ico_file)
            except Exception:
                pass

        # Variables para arrastre con el ratón
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._win_start_x = 0
        self._win_start_y = 0

        # Construir interfaz según configuración
        self._build_ui()
        self.apply_config()

        # Configurar estilos de ventana Win32 para no robar foco
        self._apply_win32_styles()

        # Vinculación de eventos de arrastre
        self._bind_drag_events()

    def _build_ui(self):
        """Construye el encabezado MSI-style y las filas de métricas organizadas en columnas."""
        is_large = self.config.get("size") == "large"
        font_hdr = ("Segoe UI", 8 if is_large else 7, "bold")
        font_badge = ("Segoe UI", 8 if is_large else 7, "bold")
        font_val = ("Consolas", 10 if is_large else 9, "bold")
        font_sub = ("Consolas", 9 if is_large else 8)
        inner_pad_x = 12 if is_large else 10
        inner_pad_y = 7 if is_large else 5

        # Marco interior con borde sutil
        self.inner_frame = tk.Frame(self, bg=C_OV_BG, padx=inner_pad_x, pady=inner_pad_y)
        self.inner_frame.pack(fill="both", expand=True, padx=1, pady=1)

        # 1. Encabezado superior: PC RESCUE | GAMING y botón de cierre
        self.hdr_row = tk.Frame(self.inner_frame, bg=C_OV_BG)
        self.hdr_row.pack(fill="x", pady=(0, 4))

        self.lbl_hdr_title = tk.Label(
            self.hdr_row, text="PC RESCUE  |  GAMING", font=font_hdr,
            fg="#38BDF8", bg=C_OV_BG
        )
        self.lbl_hdr_title.pack(side="left")

        # Botón cerrar discreto (×)
        self.btn_close_ov = tk.Label(
            self.hdr_row, text=" × ", font=("Segoe UI", 9, "bold"),
            fg=C_OV_TEXT_DIM, bg=C_OV_BG, cursor="hand2"
        )
        self.btn_close_ov.pack(side="right")
        self.btn_close_ov.bind("<Button-1>", lambda e: self.destroy())
        self.btn_close_ov.bind("<Enter>", lambda e: self.btn_close_ov.config(fg="#FF5D67"))
        self.btn_close_ov.bind("<Leave>", lambda e: self.btn_close_ov.config(fg=C_OV_TEXT_DIM))

        # Línea divisoria muy discreta
        self.div_line = tk.Frame(self.inner_frame, bg="#1E293B", height=1)
        self.div_line.pack(fill="x", pady=(0, 5))

        # 2. Contenedor Grid para columnas alineadas perfectamente
        self.grid_frame = tk.Frame(self.inner_frame, bg=C_OV_BG)
        self.grid_frame.pack(fill="x")
        self.grid_frame.columnconfigure(0, weight=0)  # Badge
        self.grid_frame.columnconfigure(1, weight=1)  # Métrica principal
        self.grid_frame.columnconfigure(2, weight=1)  # Métrica secundaria / temp

        row_pady = (2, 2) if is_large else (1, 1)

        # Fila CPU
        self.badge_cpu = tk.Label(
            self.grid_frame, text="CPU", font=font_badge,
            fg=C_BADGE_CPU_FG, bg=C_BADGE_CPU_BG,
            padx=5, pady=1, width=4
        )
        self.badge_cpu.grid(row=0, column=0, padx=(0, 8), pady=row_pady, sticky="w")

        self.val_cpu_pct = tk.Label(
            self.grid_frame, text="-- %", font=font_val,
            fg=C_OV_TEXT, bg=C_OV_BG, anchor="w"
        )
        self.val_cpu_pct.grid(row=0, column=1, padx=4, pady=row_pady, sticky="w")

        self.val_cpu_temp = tk.Label(
            self.grid_frame, text="N/D", font=font_sub,
            fg=C_OV_TEXT_DIM, bg=C_OV_BG, anchor="e"
        )
        self.val_cpu_temp.grid(row=0, column=2, padx=(4, 0), pady=row_pady, sticky="e")

        # Fila GPU
        self.badge_gpu = tk.Label(
            self.grid_frame, text="GPU", font=font_badge,
            fg=C_BADGE_GPU_FG, bg=C_BADGE_GPU_BG,
            padx=5, pady=1, width=4
        )
        self.badge_gpu.grid(row=1, column=0, padx=(0, 8), pady=row_pady, sticky="w")

        self.val_gpu_pct = tk.Label(
            self.grid_frame, text="-- %", font=font_val,
            fg=C_OV_TEXT, bg=C_OV_BG, anchor="w"
        )
        self.val_gpu_pct.grid(row=1, column=1, padx=4, pady=row_pady, sticky="w")

        self.val_gpu_temp = tk.Label(
            self.grid_frame, text="N/D", font=font_sub,
            fg=C_OV_TEXT_DIM, bg=C_OV_BG, anchor="e"
        )
        self.val_gpu_temp.grid(row=1, column=2, padx=(4, 0), pady=row_pady, sticky="e")

        # Fila RAM
        self.badge_ram = tk.Label(
            self.grid_frame, text="RAM", font=font_badge,
            fg=C_BADGE_RAM_FG, bg=C_BADGE_RAM_BG,
            padx=5, pady=1, width=4
        )
        self.badge_ram.grid(row=2, column=0, padx=(0, 8), pady=row_pady, sticky="w")

        self.val_ram_mem = tk.Label(
            self.grid_frame, text="-- / -- GB", font=font_val,
            fg=C_OV_TEXT, bg=C_OV_BG, anchor="w"
        )
        self.val_ram_mem.grid(row=2, column=1, padx=4, pady=row_pady, sticky="w")

        self.val_ram_pct = tk.Label(
            self.grid_frame, text="-- %", font=font_sub,
            fg=C_BADGE_RAM_FG, bg=C_OV_BG, anchor="e"
        )
        self.val_ram_pct.grid(row=2, column=2, padx=(4, 0), pady=row_pady, sticky="e")

    # Propiedades retrocompatibles para pruebas que lean .val_cpu.cget("text")
    @property
    def val_cpu(self):
        class _CompositeLabel:
            def __init__(self, p_lbl, t_lbl):
                self._p = p_lbl
                self._t = t_lbl
            def cget(self, key):
                if key == "text":
                    return f"{self._p.cget('text')} | {self._t.cget('text')}"
                return self._p.cget(key)
        return _CompositeLabel(self.val_cpu_pct, self.val_cpu_temp)

    @property
    def val_gpu(self):
        class _CompositeLabel:
            def __init__(self, p_lbl, t_lbl):
                self._p = p_lbl
                self._t = t_lbl
            def cget(self, key):
                if key == "text":
                    return f"{self._p.cget('text')} | {self._t.cget('text')}"
                return self._p.cget(key)
        return _CompositeLabel(self.val_gpu_pct, self.val_gpu_temp)

    @property
    def val_ram(self):
        class _CompositeLabel:
            def __init__(self, m_lbl, p_lbl):
                self._m = m_lbl
                self._p = p_lbl
            def cget(self, key):
                if key == "text":
                    return f"{self._p.cget('text')} | {self._m.cget('text')}"
                return self._m.cget(key)
        return _CompositeLabel(self.val_ram_mem, self.val_ram_pct)

    def _apply_win32_styles(self):
        """Aplica estilos extendidos de Windows para no robar foco ni aparecer en la barra de tareas."""
        try:
            self.update_idletasks()
            hwnd = self.winfo_id()
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            new_style = style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST

            if self.config.get("click_through", False):
                new_style |= WS_EX_TRANSPARENT

            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
        except Exception:
            pass

    def _bind_drag_events(self):
        """Permite mover la ventana haciendo clic y arrastrando con el ratón."""
        if self.config.get("click_through", False):
            return

        widgets = [
            self, self.inner_frame, self.hdr_row, self.lbl_hdr_title,
            self.grid_frame, self.badge_cpu, self.badge_gpu, self.badge_ram,
            self.val_cpu_pct, self.val_cpu_temp,
            self.val_gpu_pct, self.val_gpu_temp,
            self.val_ram_mem, self.val_ram_pct
        ]

        for w in widgets:
            w.bind("<Button-1>", self._on_drag_start)
            w.bind("<B1-Motion>", self._on_drag_motion)
            w.bind("<ButtonRelease-1>", self._on_drag_release)

    def _on_drag_start(self, event):
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self._win_start_x = self.winfo_x()
        self._win_start_y = self.winfo_y()

    def _on_drag_motion(self, event):
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        new_x = max(0, self._win_start_x + dx)
        new_y = max(0, self._win_start_y + dy)
        self.geometry(f"+{new_x}+{new_y}")

    def _on_drag_release(self, event):
        # Guardar posición personalizada
        self.config.set("position", "custom")
        self.config.set("custom_x", self.winfo_x())
        self.config.set("custom_y", self.winfo_y())

    def apply_config(self):
        """Aplica opacidad, posición y geometría configuradas."""
        try:
            opacity = float(self.config.get("opacity", 0.85))
            opacity = max(0.3, min(1.0, opacity))
            self.attributes("-alpha", opacity)
        except Exception:
            pass

        self.reposition()

    def reposition(self):
        """Posiciona la ventana en pantalla según la configuración elegida."""
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        margin = 20
        pos = self.config.get("position", "top_left")

        if pos == "top_left":
            x = margin
            y = margin
        elif pos == "top_right":
            x = screen_w - w - margin
            y = margin
        elif pos == "bottom_left":
            x = margin
            y = screen_h - h - margin - 50  # Margen para barra de tareas
        elif pos == "bottom_right":
            x = screen_w - w - margin
            y = screen_h - h - margin - 50
        elif pos == "custom":
            x = int(self.config.get("custom_x", margin))
            y = int(self.config.get("custom_y", margin))
        else:
            x = margin
            y = margin

        self.geometry(f"+{x}+{y}")

    def update_metrics(self, cpu_pct, cpu_temp, gpu_pct, gpu_temp, ram_data):
        """Actualiza el texto de las métricas en tiempo real.

        Args:
            cpu_pct: float (0 a 100) o None
            cpu_temp: float (°C) o None
            gpu_pct: float (0 a 100) o None
            gpu_temp: float (°C) o None
            ram_data: dict con 'percent', 'used_gb', 'total_gb' o None
        """
        if not self._is_active or not self.winfo_exists():
            return

        # 1. CPU
        if cpu_pct is not None:
            self.val_cpu_pct.config(text=f"{int(round(cpu_pct))} %")
        else:
            self.val_cpu_pct.config(text="-- %")

        if cpu_temp is not None:
            self.val_cpu_temp.config(text=f"{int(round(cpu_temp))} °C", fg=C_OV_TEXT)
        else:
            self.val_cpu_temp.config(text="N/D", fg=C_OV_TEXT_DIM)

        # 2. GPU
        if gpu_pct is not None:
            self.val_gpu_pct.config(text=f"{int(round(gpu_pct))} %")
        else:
            self.val_gpu_pct.config(text="-- %")

        if gpu_temp is not None:
            self.val_gpu_temp.config(text=f"{int(round(gpu_temp))} °C", fg=C_OV_TEXT)
        else:
            self.val_gpu_temp.config(text="N/D", fg=C_OV_TEXT_DIM)

        # 3. RAM
        if ram_data:
            used_gb = ram_data.get("used_gb", 0.0)
            tot_gb = ram_data.get("total_gb", 0.0)
            ram_pct = int(round(ram_data.get("percent", 0)))
            self.val_ram_mem.config(text=f"{used_gb:.1f} / {tot_gb:.1f} GB")
            self.val_ram_pct.config(text=f"{ram_pct} %")
        else:
            self.val_ram_mem.config(text="-- / -- GB")
            self.val_ram_pct.config(text="-- %")

    def destroy(self):
        """Cierre seguro del overlay."""
        self._is_active = False
        if self.on_close_callback:
            try:
                self.on_close_callback()
            except Exception:
                pass
        super().destroy()


# =====================================================================
#  DIÁLOGO DE CONFIGURACIÓN DEL OVERLAY
# =====================================================================
class OverlayConfigDialog(tk.Toplevel):
    """Diálogo modal para configurar posición, tamaño, opacidad y refresco del Overlay."""

    POSITIONS = [
        ("Superior izquierda", "top_left"),
        ("Superior derecha", "top_right"),
        ("Inferior izquierda", "bottom_left"),
        ("Inferior derecha", "bottom_right"),
        ("Posición personalizada (arrastrable)", "custom"),
    ]

    SIZES = [
        ("Compacto (recomendado)", "compact"),
        ("Grande", "large"),
    ]

    OPACITIES = [
        ("60%", 0.60),
        ("70%", 0.70),
        ("80%", 0.80),
        ("85% (recomendado)", 0.85),
        ("90%", 0.90),
        ("95%", 0.95),
        ("100% (sólido)", 1.0),
    ]

    REFRESH_RATES = [
        ("0.5 segundos (muy rápido)", 500),
        ("1.0 segundo (recomendado)", 1000),
        ("2.0 segundos (bajo consumo)", 2000),
    ]

    def __init__(self, master, config: OverlayConfig, on_applied_callback=None):
        super().__init__(master)
        self.config = config
        self.on_applied_callback = on_applied_callback

        self.title("Configuración de Gaming Overlay")
        self.geometry("490x440")
        self.resizable(False, False)
        self.configure(bg="#10121B")

        # Icono
        ico_file = resource_path(os.path.join("assets", "icon.ico"))
        if os.path.isfile(ico_file):
            try:
                self.iconbitmap(ico_file)
            except Exception:
                pass

        # Modal
        self.transient(master)
        self.grab_set()

        self._build_ui()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        w = 490
        h = 440
        pw = self.master.winfo_width()
        ph = self.master.winfo_height()
        px = self.master.winfo_x()
        py = self.master.winfo_y()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

    def _build_ui(self):
        pad = tk.Frame(self, bg="#10121B", padx=24, pady=20)
        pad.pack(fill="both", expand=True)

        # Encabezado
        tk.Label(
            pad, text="Configuración del Gaming Overlay",
            font=("Segoe UI", 13, "bold"), fg="#F4F6FC", bg="#10121B"
        ).pack(anchor="w")

        tk.Label(
            pad, text="Ajusta la apariencia, ubicación y comportamiento de la superposición.",
            font=("Segoe UI", 9), fg="#A6B0C8", bg="#10121B"
        ).pack(anchor="w", pady=(2, 14))

        form = tk.Frame(pad, bg="#171A28", padx=16, pady=14, highlightthickness=1, highlightbackground="#303750")
        form.pack(fill="x", pady=(0, 16))

        # 1. Posición
        row1 = tk.Frame(form, bg="#171A28")
        row1.pack(fill="x", pady=5)
        tk.Label(row1, text="Ubicación inicial:", font=("Segoe UI", 9), fg="#D5DCED", bg="#171A28", width=18, anchor="w").pack(side="left")

        curr_pos = self.config.get("position", "top_left")
        pos_labels = [label for label, val in self.POSITIONS]
        self.cb_pos = ttk.Combobox(row1, values=pos_labels, state="readonly", width=26)
        self.cb_pos.pack(side="left")
        for idx, (label, val) in enumerate(self.POSITIONS):
            if val == curr_pos:
                self.cb_pos.current(idx)
                break
        if self.cb_pos.current() == -1:
            self.cb_pos.current(0)

        # 2. Tamaño
        row2 = tk.Frame(form, bg="#171A28")
        row2.pack(fill="x", pady=5)
        tk.Label(row2, text="Tamaño visual:", font=("Segoe UI", 9), fg="#D5DCED", bg="#171A28", width=18, anchor="w").pack(side="left")

        curr_size = self.config.get("size", "compact")
        size_labels = [label for label, val in self.SIZES]
        self.cb_size = ttk.Combobox(row2, values=size_labels, state="readonly", width=26)
        self.cb_size.pack(side="left")
        for idx, (label, val) in enumerate(self.SIZES):
            if val == curr_size:
                self.cb_size.current(idx)
                break
        if self.cb_size.current() == -1:
            self.cb_size.current(0)

        # 3. Opacidad
        row3 = tk.Frame(form, bg="#171A28")
        row3.pack(fill="x", pady=5)
        tk.Label(row3, text="Opacidad / Transparencia:", font=("Segoe UI", 9), fg="#D5DCED", bg="#171A28", width=18, anchor="w").pack(side="left")

        curr_op = float(self.config.get("opacity", 0.85))
        op_labels = [label for label, val in self.OPACITIES]
        self.cb_op = ttk.Combobox(row3, values=op_labels, state="readonly", width=26)
        self.cb_op.pack(side="left")
        for idx, (label, val) in enumerate(self.OPACITIES):
            if abs(val - curr_op) < 0.03:
                self.cb_op.current(idx)
                break
        if self.cb_op.current() == -1:
            self.cb_op.current(3)

        # 4. Frecuencia de actualización
        row4 = tk.Frame(form, bg="#171A28")
        row4.pack(fill="x", pady=5)
        tk.Label(row4, text="Frecuencia de refresco:", font=("Segoe UI", 9), fg="#D5DCED", bg="#171A28", width=18, anchor="w").pack(side="left")

        curr_rate = int(self.config.get("update_interval_ms", 1000))
        rate_labels = [label for label, val in self.REFRESH_RATES]
        self.cb_rate = ttk.Combobox(row4, values=rate_labels, state="readonly", width=26)
        self.cb_rate.pack(side="left")
        for idx, (label, val) in enumerate(self.REFRESH_RATES):
            if val == curr_rate:
                self.cb_rate.current(idx)
                break
        if self.cb_rate.current() == -1:
            self.cb_rate.current(1)

        # 5. Checkbox click-through
        self.var_click_through = tk.BooleanVar(value=bool(self.config.get("click_through", False)))
        chk = tk.Checkbutton(
            form, text="Modo clic transparente (los clics pasan directo al juego)",
            variable=self.var_click_through,
            font=("Segoe UI", 9), fg="#D5DCED", bg="#171A28",
            selectcolor="#10121B", activebackground="#171A28", activeforeground="#F4F6FC"
        )
        chk.pack(anchor="w", pady=(8, 0))

        # Nota técnica
        note = (
            "• El overlay funciona sobre escritorio, juegos en ventana y ventana sin bordes.\n"
            "• Puedes mover el overlay arrastrándolo con el botón izquierdo del ratón.\n"
            "• Las temperaturas requieren sensores compatibles en el equipo (se muestra N/D si no existen)."
        )
        tk.Label(
            pad, text=note, font=("Segoe UI", 8),
            fg="#737D95", bg="#10121B", justify="left"
        ).pack(anchor="w", pady=(0, 14))

        # Botones inferiores
        btn_row = tk.Frame(pad, bg="#10121B")
        btn_row.pack(fill="x", side="bottom")

        btn_save = tk.Button(
            btn_row, text="Guardar cambios", font=("Segoe UI", 9, "bold"),
            fg="#ffffff", bg="#4385F5", activebackground="#5B9BFF",
            relief="flat", bd=0, padx=16, pady=7, cursor="hand2",
            command=self._save_changes
        )
        btn_save.pack(side="right")

        btn_cancel = tk.Button(
            btn_row, text="Cancelar", font=("Segoe UI", 9),
            fg="#D5DCED", bg="#262D42", activebackground="#343D59",
            relief="flat", bd=0, padx=14, pady=7, cursor="hand2",
            command=self.destroy
        )
        btn_cancel.pack(side="right", padx=(0, 8))

    def _save_changes(self):
        """Aplica y guarda los cambios seleccionados."""
        pos_idx = self.cb_pos.current()
        if pos_idx >= 0:
            self.config.set("position", self.POSITIONS[pos_idx][1])

        size_idx = self.cb_size.current()
        if size_idx >= 0:
            self.config.set("size", self.SIZES[size_idx][1])

        op_idx = self.cb_op.current()
        if op_idx >= 0:
            self.config.set("opacity", self.OPACITIES[op_idx][1])

        rate_idx = self.cb_rate.current()
        if rate_idx >= 0:
            self.config.set("update_interval_ms", self.REFRESH_RATES[rate_idx][1])

        self.config.set("click_through", self.var_click_through.get())
        self.config.save()

        if self.on_applied_callback:
            try:
                self.on_applied_callback()
            except Exception:
                pass

        self.destroy()
