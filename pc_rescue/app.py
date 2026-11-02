"""
PC Rescue — Aplicación de diagnóstico de sistema y rendimiento para Windows.

Versión 2.0 Profesional:
    - Paleta de color oscura de nivel comercial (#10121B, #171A28, #1D2233, #4385F5).
    - Barra lateral con navegación fija y bloque de Herramientas (CMD y PowerShell).
    - Medidores semicirculares dinámicos (velocímetro) con redibujado adaptativo.
    - Monitoreo en tiempo real de CPU, RAM y Almacenamiento.
    - Diagnóstico de red (WiFi/Ethernet) y prueba real de velocidad no bloqueante.
    - Especificaciones detalladas de hardware y tabla interactiva de controladores.
    - Diagnósticos, recomendaciones y exportación de informes a archivo TXT.
"""

import math
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Compatibilidad con bootloader de PyInstaller en modo ventana sin consola (console=False)
if sys.stdout is None or not hasattr(sys.stdout, "fileno"):
    try:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass
if sys.stderr is None or not hasattr(sys.stderr, "fileno"):
    try:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass

# Módulos del proyecto
from metrics import (
    init_cpu_monitoring, get_cpu_percent, get_ram_info, get_disk_info,
    init_gpu_monitoring, close_gpu_monitoring, get_gpu_percent, get_temperatures,
    close_temperature_monitoring
)
from diagnosis import run_all_diagnostics, get_system_overall_status
from recommendations import get_recommendations, format_recommendations_text
from report import generate_report
from overlay import OverlayConfig, GamingOverlayWindow, OverlayConfigDialog
import network_utils
import hardware_utils
import terminal_utils


def resource_path(relative_path):
    """Obtiene la ruta absoluta a un recurso, compatible con desarrollo y PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


# =====================================================================
#  PALETA DE COLORES PROFESIONAL — DIRECCIÓN VISUAL PC RESCUE 2.0
# =====================================================================
C_BG_MAIN       = "#10121B"  # Fondo principal de la ventana
C_BG_SIDEBAR    = "#171A28"  # Barra lateral fija
C_BG_CARD       = "#1D2233"  # Tarjetas y paneles principales
C_BG_CARD_SEC   = "#22283B"  # Paneles secundarios / fondos interiores
C_BORDER        = "#303750"  # Bordes discretos de paneles

# Colores de interacción y acento
C_ACCENT        = "#4385F5"  # Azul principal de interacción
C_ACCENT_HOVER  = "#5B9BFF"  # Azul hover
C_INFO_CYAN     = "#48B5FF"  # Azul claro para información
C_BTN_SEC       = "#262D42"  # Botón secundario
C_BTN_SEC_HOVER = "#343D59"  # Botón secundario hover

# Colores de estado real
C_GREEN         = "#18C995"  # Estados normales
C_YELLOW        = "#FFB020"  # Advertencias
C_RED           = "#FF5D67"  # Errores y atención crítica

# Tipografía y contraste
C_TEXT_TITLE    = "#F4F6FC"  # Texto principal / Títulos
C_TEXT_BODY     = "#D5DCED"  # Texto regular
C_TEXT_MUTED    = "#A6B0C8"  # Texto secundario
C_TEXT_DIM      = "#737D95"  # Texto apagado / metadatos


def get_color_by_level(level):
    """Retorna el color corporativo correspondiente al nivel de diagnóstico."""
    if level == "critical":
        return C_RED
    elif level == "warning":
        return C_YELLOW
    elif level == "normal":
        return C_GREEN
    return C_TEXT_MUTED


# =====================================================================
#  INTERPOLACIÓN CROMÁTICA DINÁMICA PARA MEDIDORES
# =====================================================================

# Paradas de color definidas como (porcentaje, color_hex).
# Puntos de referencia requeridos:
#   - 0%:   #00E676 (verde)
#   - 25%:  #76FF03 (verde lima)
#   - 50%:  #FFEB3B (amarillo)
#   - 57.5%:#FFC107 (amarillo anaranjado)
#   - 65%:  #FF9800 (naranja)
#   - 80%:  #FF5722 (rojo anaranjado)
#   - 100%: #FF1744 (rojo intenso)
_GAUGE_COLOR_STOPS = [
    (0,    "#00E676"),   # Verde
    (25,   "#76FF03"),   # Verde lima
    (50,   "#FFEB3B"),   # Amarillo
    (57.5, "#FFC107"),   # Amarillo anaranjado
    (65,   "#FF9800"),   # Naranja
    (80,   "#FF5722"),   # Rojo anaranjado
    (100,  "#FF1744"),   # Rojo intenso
]


def _hex_to_rgb(hex_color):
    """Convierte un color hexadecimal '#RRGGBB' a una tupla (R, G, B)."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _rgb_to_hex(r, g, b):
    """Convierte una tupla (R, G, B) a formato hexadecimal '#RRGGBB'."""
    return f"#{int(round(r)):02X}{int(round(g)):02X}{int(round(b)):02X}"


def get_usage_color(percentage):
    """Devuelve el color RGB/Hex interpolado para un porcentaje real entre 0 y 100.

    Puntos de control:
      -   0 %: #00E676 (verde intenso)
      -  25 %: #76FF03 (verde lima)
      -  50 %: #FFEB3B (amarillo)
      -  65 %: #FF9800 (naranja)
      -  80 %: #FF5722 (rojo anaranjado)
      - 100 %: #FF1744 (rojo vivo)

    Manejo de casos especiales:
      - Si percentage es None o no numérico, devuelve el color neutral "#737D95"
        en lugar de interpretarlo erróneamente como 0 %.
      - Valores fuera de rango se acotan al intervalo [0.0, 100.0].

    Args:
        percentage: Valor numérico (int, float) o None.

    Returns:
        str: Color en formato hexadecimal '#RRGGBB'.
    """
    if percentage is None:
        return "#737D95"

    try:
        p = float(percentage)
    except (ValueError, TypeError):
        return "#737D95"

    p = max(0.0, min(100.0, p))

    stops = _GAUGE_COLOR_STOPS
    if p <= stops[0][0]:
        return stops[0][1]
    if p >= stops[-1][0]:
        return stops[-1][1]

    for i in range(len(stops) - 1):
        p_low, c_low = stops[i]
        p_high, c_high = stops[i + 1]

        if p_low <= p <= p_high:
            t = (p - p_low) / (p_high - p_low) if p_high != p_low else 0.0
            r1, g1, b1 = _hex_to_rgb(c_low)
            r2, g2, b2 = _hex_to_rgb(c_high)
            r = r1 + (r2 - r1) * t
            g = g1 + (g2 - g1) * t
            b = b1 + (b2 - b1) * t
            return _rgb_to_hex(r, g, b)

    return stops[-1][1]


# Alias retrocompatible
get_gauge_color = get_usage_color


# =====================================================================
#  CÁLCULO TRIGONOMÉTRICO DE AGUJA INDICADORA
# =====================================================================
def calculate_needle_coords(cx, cy, radius, percentage):
    """Calcula las coordenadas (tip_x, tip_y) de la aguja y su ángulo en grados.

    La escala semicircular se extiende de 180° (0 %, izquierda) a 0° (100 %, derecha).
    El 50 % corresponde exactamente a la vertical superior (90°).

    Args:
        cx (float): Coordenada X del centro inferior (pivote).
        cy (float): Coordenada Y del centro inferior (pivote).
        radius (float): Longitud efectiva de la aguja hacia el arco.
        percentage (float): Valor numérico de porcentaje entre 0 y 100.

    Returns:
        tuple: (tip_x, tip_y, angle_deg)
            - 0 %: apunta al extremo izquierdo (180°, tip_x = cx - radius, tip_y = cy).
            - 25 %: apunta al primer cuarto (135°).
            - 50 %: apunta verticalmente hacia arriba (90°, tip_x = cx, tip_y = cy - radius).
            - 75 %: apunta al tercer cuarto (45°).
            - 100 %: apunta al extremo derecho (0°, tip_x = cx + radius, tip_y = cy).
    """
    p = max(0.0, min(100.0, float(percentage if percentage is not None else 0.0)))
    angle_deg = 180.0 - (p / 100.0) * 180.0
    angle_rad = math.radians(angle_deg)
    tip_x = cx + radius * math.cos(angle_rad)
    tip_y = cy - radius * math.sin(angle_rad)
    return tip_x, tip_y, angle_deg


# =====================================================================
#  COMPONENTE: MEDIDOR SEMICIRCULAR DINÁMICO (TIPO VELOCÍMETRO)
# =====================================================================
class SemicircularGauge(tk.Frame):
    """Medidor tipo velocímetro con escala fija multicolor y aguja móvil.

    - Escala fija continua formada por 50 segmentos multicolores desde verde (#00E676)
      hasta rojo vivo (#FF1744).
    - Aguja indicadora blanca estilizada que pivota en el centro inferior y apunta
      al valor porcentual real.
    - Pivote central cromado y lectura numérica destacada que no es atravesada
      ni oscurecida por la aguja.
    """

    NUM_SEGMENTS = 60

    def __init__(self, parent, title="RECURSO", *args, **kwargs):
        super().__init__(parent, bg=C_BG_CARD, *args, **kwargs)
        self.title_text = title
        self.percent = 0.0
        self._target_percent = 0.0
        self._display_percent = 0.0
        self._has_data = False
        self._anim_timer = None
        self.level = "normal"
        self.detail_text = ""

        # Etiqueta superior del recurso
        self.title_lbl = tk.Label(
            self, text=self.title_text, font=("Segoe UI", 9, "bold"),
            fg=C_TEXT_MUTED, bg=C_BG_CARD
        )
        self.title_lbl.pack(pady=(10, 2))

        # Canvas para el medidor
        self.canvas = tk.Canvas(
            self, width=200, height=125, bg=C_BG_CARD,
            highlightthickness=0, bd=0
        )
        self.canvas.pack(pady=(0, 2))

        # Etiqueta de detalle inferior (GB usados, libres, etc.)
        self.detail_lbl = tk.Label(
            self, text="", font=("Segoe UI", 8),
            fg=C_TEXT_DIM, bg=C_BG_CARD
        )
        self.detail_lbl.pack(pady=(0, 8))

        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.redraw()

    def update_value(self, percent, level="normal", detail=""):
        """Actualiza el porcentaje, posición de la aguja y texto descriptivo."""
        self.level = level
        self.detail_text = detail
        self.detail_lbl.config(text=detail)

        if percent is None:
            self._has_data = False
            self.percent = None
            self._target_percent = 0.0
            self._display_percent = 0.0
            self._draw_needle()
            return

        was_empty = not self._has_data
        self._has_data = True
        self.percent = max(0.0, min(100.0, float(percent)))
        self._target_percent = self.percent

        if was_empty:
            # En la primera lectura real, posicionar la aguja de inmediato
            self._display_percent = self.percent
            self._draw_needle()
        else:
            # En lecturas continuas, transicionar suavemente
            self._start_needle_animation()

    def _start_needle_animation(self):
        """Inicia o actualiza la transición fluida de la aguja."""
        if self._anim_timer is not None:
            try:
                self.after_cancel(self._anim_timer)
            except Exception:
                pass
            self._anim_timer = None
        self._step_needle_animation()

    def _step_needle_animation(self):
        """Paso de animación de aguja con decaimiento suave no bloqueante."""
        if not self.winfo_exists():
            return

        diff = self._target_percent - self._display_percent
        if abs(diff) < 0.35:
            self._display_percent = self._target_percent
            self._anim_timer = None
            self._draw_needle()
        else:
            step = diff * 0.35
            if abs(step) < 0.4:
                step = 0.4 if diff > 0 else -0.4
            self._display_percent += step
            self._draw_needle()
            try:
                self._anim_timer = self.after(25, self._step_needle_animation)
            except (tk.TclError, RuntimeError):
                self._anim_timer = None

    def redraw(self):
        """Redibuja la escala completa fija con segmentos multicolor y la aguja."""
        c = self.canvas
        c.delete("all")

        w = c.winfo_width()
        h = c.winfo_height()
        if w < 30 or h < 30:
            w, h = 200, 125

        margin = 16
        line_width = 11
        r = min((w - margin * 2) / 2, h - margin - 10)
        cx = w / 2
        cy = h - 16

        self._geom = (cx, cy, r, line_width)

        x0, y0 = cx - r, cy - r
        x1, y1 = cx + r, cy + r

        # 1. Pista de fondo oscura
        c.create_arc(
            x0, y0, x1, y1,
            start=0, extent=180,
            style="arc", width=line_width + 4,
            outline="#161B29", tags="track_bg"
        )

        # 2. Escala fija completa formada por segmentos de colores continuos
        # La escala permanece siempre fija y visible de 0% a 100%
        n = self.NUM_SEGMENTS
        step_deg = 180.0 / n
        # Superposición angular calibrada para garantizar continuidad total entre
        # segmentos adyacentes y eliminar cualquier microfisura o espacio oscuro
        # provocado por la rasterización discreta de píxeles en Windows GDI / Tkinter.
        overlap = 0.85

        for i in range(n):
            p_seg = (i + 0.5) / n * 100.0
            color = get_usage_color(p_seg)
            start_angle = 180.0 - (i * step_deg)
            extent_angle = -(step_deg + overlap)

            c.create_arc(
                x0, y0, x1, y1,
                start=start_angle, extent=extent_angle,
                style="arc", width=line_width,
                outline=color, tags="scale_segment"
            )

        # 3. Etiquetas de escala fijas en los extremos (0% y 100%)
        # Ubicadas limpiamente debajo de los extremos del arco para evitar recortes
        c.create_text(x0 + 4, cy + 7, text="0%", fill=C_TEXT_DIM, font=("Segoe UI", 7, "bold"))
        c.create_text(x1 - 6, cy + 7, text="100%", fill=C_TEXT_DIM, font=("Segoe UI", 7, "bold"))

        # 4. Dibujar aguja y elementos centrales
        self._draw_needle()

    def _draw_needle(self):
        """Dibuja o actualiza la aguja indicadora móvil y el número central."""
        if not hasattr(self, "_geom"):
            return

        c = self.canvas
        c.delete("needle_layer")

        cx, cy, r, line_width = self._geom

        # 1. Aguja indicadora tipo velocímetro
        if self._has_data and self.percent is not None:
            p = max(0.0, min(100.0, self._display_percent))
            needle_len = r - 4
            tip_x, tip_y, angle_deg = calculate_needle_coords(cx, cy, needle_len, p)
            angle_rad = math.radians(angle_deg)

            # Base cónica elegante para la aguja
            base_w = 2.4
            perp_x = math.sin(angle_rad) * base_w
            perp_y = math.cos(angle_rad) * base_w

            p1 = (cx - perp_x, cy - perp_y)
            p2 = (cx + perp_x, cy + perp_y)
            p3 = (tip_x, tip_y)

            # Cuerpo de la aguja (blanco brillante con contorno gris claro de alto contraste)
            c.create_polygon(
                p1[0], p1[1], p2[0], p2[1], p3[0], p3[1],
                fill="#FFFFFF", outline="#E2E8F0", width=1,
                tags="needle_layer"
            )

            # Mirilla / punta indicadora sobre la escala
            c.create_oval(
                tip_x - 2, tip_y - 2, tip_x + 2, tip_y + 2,
                fill="#FFFFFF", outline="#CBD5E1",
                tags="needle_layer"
            )

        # 2. Pivote central en (cx, cy)
        piv_r = 6.0
        c.create_oval(
            cx - piv_r, cy - piv_r, cx + piv_r, cy + piv_r,
            fill="#E2E8F0", outline="#64748B", width=1,
            tags="needle_layer"
        )
        c.create_oval(
            cx - 2.5, cy - 2.5, cx + 2.5, cy + 2.5,
            fill="#10121B", outline="",
            tags="needle_layer"
        )

        # 3. Número de porcentaje grande en el centro, por encima del pivote
        # La pequeña placa del mismo color de la tarjeta evita que la aguja
        # atraviese visualmente los dígitos, garantizando máxima legibilidad.
        text_y = cy - (r * 0.44)
        if self._has_data and self.percent is not None:
            pct_val = int(round(self.percent))
            txt = f"{pct_val}%"
            txt_color = C_TEXT_TITLE
        else:
            txt = "—"
            txt_color = C_TEXT_MUTED

        c.create_rectangle(
            cx - 26, text_y - 12, cx + 26, text_y + 12,
            fill=C_BG_CARD, outline="",
            tags="needle_layer"
        )

        c.create_text(
            cx, text_y,
            text=txt,
            fill=txt_color,
            font=("Segoe UI", 18, "bold"),
            tags="needle_layer"
        )

    def destroy(self):
        """Detiene cualquier temporizador de animación pendiente antes de destruir."""
        if self._anim_timer is not None:
            try:
                self.after_cancel(self._anim_timer)
            except Exception:
                pass
            self._anim_timer = None
        super().destroy()


# =====================================================================
#  BOTÓN MODERNO CON HOVER
# =====================================================================
class ModernButton(tk.Button):
    """Botón estilizado para tema oscuro con transiciones de color hover."""

    def __init__(self, master, bg_normal=C_ACCENT, bg_hover=C_ACCENT_HOVER, **kw):
        super().__init__(
            master, bg=bg_normal, activebackground=bg_hover,
            relief="flat", cursor="hand2", bd=0, **kw
        )
        self.bg_normal = bg_normal
        self.bg_hover = bg_hover
        self.bind("<Enter>", lambda e: self.config(bg=self.bg_hover) if self["state"] != "disabled" else None)
        self.bind("<Leave>", lambda e: self.config(bg=self.bg_normal) if self["state"] != "disabled" else None)


# =====================================================================
#  VENTANA PRINCIPAL: PC RESCUE 2.0
# =====================================================================
class PCRescueApp(tk.Tk):
    """Aplicación principal de escritorio PC Rescue."""

    def __init__(self):
        super().__init__()

        self.title("PC Rescue — Diagnóstico y Rendimiento")
        self.geometry("1060x720")
        self.minsize(920, 600)
        self.configure(bg=C_BG_MAIN)

        # Identidad de aplicación en barra de tareas de Windows (AppUserModelID)
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("pc_rescue.diagnostics.2.0")
        except Exception:
            pass

        # Configurar icono oficial de PC Rescue
        self._setup_window_icon()

        # Inicialización de monitoreo
        init_cpu_monitoring()
        init_gpu_monitoring()

        # Configuración del Overlay Gaming
        self.overlay_config = OverlayConfig()
        self.overlay_window = None

        # Variables de control
        self.current_section = "inicio"
        self._is_running = True
        self._fast_timer = None
        self._slow_timer = None

        # Caché de datos
        self.last_cpu = 0.0
        self.last_ram = None
        self.last_disk = None
        self.last_diagnostics = []
        self.last_recommendations = []
        self.last_overall_status = None
        self.last_speed_test = None

        self._is_testing_speed = False
        self._hardware_data = None
        self._drivers_cache = []
        self._is_loading_drivers = False

        # Construcción visual
        self._setup_styles()
        self._build_layout()

        # Restaurar estado del overlay si estaba habilitado en preferencias
        if self.overlay_config.get("enabled", False):
            self._start_overlay()
        else:
            self._update_overlay_ui_state(is_active=False)

        # Sección inicial
        self._switch_section("inicio")

        # Monitoreo automático
        self._schedule_fast_updates()
        self._schedule_slow_updates()

        # Cierre controlado
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_window_icon(self):
        """Aplica el icono corporativo a la ventana y barra de tareas."""
        ico_file = resource_path(os.path.join("assets", "icon.ico"))
        png_file = resource_path(os.path.join("assets", "icon.png"))
        if os.path.isfile(ico_file):
            try:
                self.iconbitmap(ico_file)
            except Exception:
                pass
        if os.path.isfile(png_file):
            try:
                self._app_icon_img = tk.PhotoImage(file=png_file)
                self.iconphoto(True, self._app_icon_img)
            except Exception:
                pass

    def _setup_styles(self):
        """Aplica estilos consistentes a los controles ttk."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Tabla Treeview para controladores
        style.configure(
            "Drivers.Treeview",
            background=C_BG_CARD_SEC,
            foreground=C_TEXT_BODY,
            fieldbackground=C_BG_CARD_SEC,
            borderwidth=0,
            font=("Segoe UI", 9),
            rowheight=26,
        )
        style.configure(
            "Drivers.Treeview.Heading",
            background=C_BG_SIDEBAR,
            foreground=C_TEXT_TITLE,
            font=("Segoe UI", 9, "bold"),
            borderwidth=1,
            relief="flat"
        )
        style.map(
            "Drivers.Treeview",
            background=[("selected", C_ACCENT)],
            foreground=[("selected", "#ffffff")]
        )

        # Combobox
        style.configure(
            "TCombobox",
            fieldbackground=C_BG_CARD_SEC,
            background=C_BG_SIDEBAR,
            foreground=C_TEXT_TITLE,
            arrowcolor=C_TEXT_TITLE
        )

    def _safe_after(self, ms, func, *args):
        """Ejecuta una llamada after protegida contra cierres de ventana."""
        if not self._is_running:
            return
        try:
            self.after(ms, func, *args)
        except (tk.TclError, RuntimeError):
            pass

    # ─────────────────────────────────────────────────────────────────
    #  ESTRUCTURA PRINCIPAL (BARRA LATERAL + CONTENIDO)
    # ─────────────────────────────────────────────────────────────────
    def _build_layout(self):
        """Crea la barra lateral fija y el contenedor principal para las vistas."""
        # 1. Barra Lateral Fija
        self.sidebar = tk.Frame(self, bg=C_BG_SIDEBAR, width=225)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self._build_sidebar_content()

        # 2. Contenedor de Vistas a la Derecha
        self.content_container = tk.Frame(self, bg=C_BG_MAIN)
        self.content_container.pack(side="right", fill="both", expand=True)

        # 3. Instanciación única de las 3 Vistas
        self.view_inicio = tk.Frame(self.content_container, bg=C_BG_MAIN)
        self.view_wifi = tk.Frame(self.content_container, bg=C_BG_MAIN)
        self.view_componentes = tk.Frame(self.content_container, bg=C_BG_MAIN)

        self._build_view_inicio()
        self._build_view_wifi()
        self._build_view_componentes()

    def _build_sidebar_content(self):
        """Construye el logotipo, menú principal, accesos a terminales y pie."""
        # --- Encabezado de la barra lateral ---
        brand_frame = tk.Frame(self.sidebar, bg=C_BG_SIDEBAR)
        brand_frame.pack(fill="x", padx=18, pady=(22, 18))

        logo_row = tk.Frame(brand_frame, bg=C_BG_SIDEBAR)
        logo_row.pack(anchor="w")

        # Insignia de marca minimalista
        logo_badge = tk.Canvas(logo_row, width=24, height=24, bg=C_ACCENT, highlightthickness=0)
        logo_badge.pack(side="left", padx=(0, 8))
        logo_badge.create_text(12, 12, text="PC", fill="#ffffff", font=("Segoe UI", 9, "bold"))

        tk.Label(
            logo_row, text="PC RESCUE", font=("Segoe UI", 12, "bold"),
            fg=C_TEXT_TITLE, bg=C_BG_SIDEBAR
        ).pack(side="left")

        tk.Label(
            brand_frame, text="Diagnóstico y Rendimiento",
            font=("Segoe UI", 8), fg=C_TEXT_DIM, bg=C_BG_SIDEBAR
        ).pack(anchor="w", pady=(3, 0))

        tk.Frame(self.sidebar, bg=C_BORDER, height=1).pack(fill="x", padx=16, pady=(8, 14))

        # --- Navegación Principal ---
        tk.Label(
            self.sidebar, text="VISTAS PRINCIPALES", font=("Segoe UI", 7, "bold"),
            fg=C_TEXT_DIM, bg=C_BG_SIDEBAR, padx=18
        ).pack(anchor="w", pady=(0, 4))

        self.nav_buttons = {}
        nav_items = [
            ("inicio", "  Inicio", "inicio"),
            ("wifi", "  WiFi y Red", "wifi"),
            ("componentes", "  Componentes", "componentes"),
        ]

        for key, text, section_id in nav_items:
            btn = tk.Button(
                self.sidebar,
                text=text,
                anchor="w",
                font=("Segoe UI", 10),
                fg=C_TEXT_BODY,
                bg=C_BG_SIDEBAR,
                activebackground=C_BTN_SEC,
                activeforeground=C_TEXT_TITLE,
                relief="flat",
                bd=0,
                cursor="hand2",
                padx=16,
                pady=10,
                command=lambda s=section_id: self._switch_section(s)
            )
            btn.pack(fill="x", padx=10, pady=2)
            btn.bind("<Enter>", lambda e, b=btn, k=key: self._on_nav_hover(b, k, True))
            btn.bind("<Leave>", lambda e, b=btn, k=key: self._on_nav_hover(b, k, False))
            self.nav_buttons[key] = btn

        # --- Bloque de Herramientas y Terminales ---
        tk.Frame(self.sidebar, bg=C_BORDER, height=1).pack(fill="x", padx=16, pady=(16, 12))

        tk.Label(
            self.sidebar, text="HERRAMIENTAS", font=("Segoe UI", 7, "bold"),
            fg=C_TEXT_DIM, bg=C_BG_SIDEBAR, padx=18
        ).pack(anchor="w", pady=(0, 6))

        # Botón CMD
        self.btn_cmd = tk.Button(
            self.sidebar,
            text="  >_  CMD",
            anchor="w",
            font=("Segoe UI", 9, "bold"),
            fg=C_TEXT_BODY,
            bg=C_BG_CARD_SEC,
            activebackground=C_BTN_SEC_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=14,
            pady=8,
            command=self._launch_cmd_terminal
        )
        self.btn_cmd.pack(fill="x", padx=12, pady=3)
        self.btn_cmd.bind("<Enter>", lambda e: self.btn_cmd.config(bg=C_BTN_SEC_HOVER, fg=C_TEXT_TITLE))
        self.btn_cmd.bind("<Leave>", lambda e: self.btn_cmd.config(bg=C_BG_CARD_SEC, fg=C_TEXT_BODY))

        # Botón PowerShell
        self.btn_pwsh = tk.Button(
            self.sidebar,
            text="  PS  PowerShell",
            anchor="w",
            font=("Segoe UI", 9, "bold"),
            fg=C_TEXT_BODY,
            bg=C_BG_CARD_SEC,
            activebackground=C_BTN_SEC_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=14,
            pady=8,
            command=self._launch_powershell_terminal
        )
        self.btn_pwsh.pack(fill="x", padx=12, pady=3)
        self.btn_powershell = self.btn_pwsh
        self.btn_pwsh.bind("<Enter>", lambda e: self.btn_pwsh.config(bg=C_BTN_SEC_HOVER, fg=C_TEXT_TITLE))
        self.btn_pwsh.bind("<Leave>", lambda e: self.btn_pwsh.config(bg=C_BG_CARD_SEC, fg=C_TEXT_BODY))

        # --- Bloque de Overlay Gaming ---
        tk.Frame(self.sidebar, bg=C_BORDER, height=1).pack(fill="x", padx=16, pady=(16, 12))

        overlay_hdr = tk.Frame(self.sidebar, bg=C_BG_SIDEBAR)
        overlay_hdr.pack(fill="x", padx=18, pady=(0, 6))

        tk.Label(
            overlay_hdr, text="OVERLAY GAMING", font=("Segoe UI", 7, "bold"),
            fg=C_TEXT_DIM, bg=C_BG_SIDEBAR
        ).pack(side="left")

        self.lbl_overlay_status = tk.Label(
            overlay_hdr, text="● Inactivo", font=("Segoe UI", 7, "bold"),
            fg=C_TEXT_DIM, bg=C_BG_SIDEBAR
        )
        self.lbl_overlay_status.pack(side="right")

        # Botón conmutador del Overlay
        self.btn_toggle_overlay = tk.Button(
            self.sidebar,
            text="  ⚡  Activar Overlay",
            anchor="w",
            font=("Segoe UI", 9, "bold"),
            fg=C_TEXT_BODY,
            bg=C_BG_CARD_SEC,
            activebackground=C_BTN_SEC_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=14,
            pady=8,
            command=self._toggle_overlay
        )
        self.btn_toggle_overlay.pack(fill="x", padx=12, pady=3)
        self.btn_toggle_overlay.bind("<Enter>", lambda e: self._on_overlay_btn_hover(True))
        self.btn_toggle_overlay.bind("<Leave>", lambda e: self._on_overlay_btn_hover(False))

        # Botón de configuración del Overlay
        self.btn_config_overlay = tk.Button(
            self.sidebar,
            text="  ⚙  Configurar Overlay",
            anchor="w",
            font=("Segoe UI", 8),
            fg=C_TEXT_MUTED,
            bg=C_BG_SIDEBAR,
            activebackground=C_BTN_SEC,
            activeforeground=C_TEXT_TITLE,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=14,
            pady=5,
            command=self._open_overlay_config
        )
        self.btn_config_overlay.pack(fill="x", padx=12, pady=(1, 3))
        self.btn_config_overlay.bind("<Enter>", lambda e: self.btn_config_overlay.config(bg=C_BTN_SEC, fg=C_TEXT_TITLE))
        self.btn_config_overlay.bind("<Leave>", lambda e: self.btn_config_overlay.config(bg=C_BG_SIDEBAR, fg=C_TEXT_MUTED))

        # --- Pie de la barra lateral ---
        footer = tk.Frame(self.sidebar, bg=C_BG_SIDEBAR)
        footer.pack(side="bottom", fill="x", padx=18, pady=16)

        tk.Label(
            footer, text="PC Rescue v2.0 • Windows",
            font=("Segoe UI", 8), fg=C_TEXT_DIM, bg=C_BG_SIDEBAR
        ).pack(anchor="w")

    def _on_nav_hover(self, btn, key, is_hover):
        """Efecto hover en las opciones de navegación inactivas."""
        if self.current_section == key:
            return
        if is_hover:
            btn.config(bg=C_BTN_SEC, fg=C_TEXT_TITLE)
        else:
            btn.config(bg=C_BG_SIDEBAR, fg=C_TEXT_BODY)

    def _switch_section(self, section_id):
        """Alterna entre vistas sin reconstruir widgets."""
        self.current_section = section_id

        for key, btn in self.nav_buttons.items():
            if key == section_id:
                btn.config(bg=C_ACCENT, fg="#ffffff", font=("Segoe UI", 10, "bold"))
            else:
                btn.config(bg=C_BG_SIDEBAR, fg=C_TEXT_BODY, font=("Segoe UI", 10))

        self.view_inicio.pack_forget()
        self.view_wifi.pack_forget()
        self.view_componentes.pack_forget()

        if section_id == "inicio":
            self.view_inicio.pack(fill="both", expand=True)
        elif section_id == "wifi":
            self.view_wifi.pack(fill="both", expand=True)
            self._refresh_wifi_data()
        elif section_id == "componentes":
            self.view_componentes.pack(fill="both", expand=True)
            if self._hardware_data is None:
                self._load_hardware_in_background()

    def _launch_cmd_terminal(self):
        """Abre Símbolo del sistema (CMD) en una ventana independiente."""
        success, detail = terminal_utils.open_cmd()
        if not success:
            messagebox.showerror(
                "Error al abrir CMD",
                f"No se pudo iniciar el Símbolo del sistema:\n\n{detail}"
            )

    def _launch_powershell_terminal(self):
        """Abre PowerShell en una ventana independiente."""
        success, detail = terminal_utils.open_powershell()
        if not success:
            messagebox.showerror(
                "Error al abrir PowerShell",
                f"No se pudo iniciar la terminal PowerShell:\n\n{detail}"
            )

    # ─────────────────────────────────────────────────────────────────
    #  CONTROL DEL OVERLAY GAMING
    # ─────────────────────────────────────────────────────────────────
    def _toggle_overlay(self):
        """Activa o desactiva la ventana flotante de Gaming Overlay."""
        if self.overlay_window is None:
            self._start_overlay()
        else:
            self._stop_overlay()

    def _start_overlay(self):
        """Crea y muestra el Gaming Overlay."""
        if self.overlay_window is not None:
            return

        self.overlay_window = GamingOverlayWindow(
            self, self.overlay_config, on_close_callback=self._on_overlay_closed
        )
        self.overlay_config.set("enabled", True)
        self._update_overlay_ui_state(is_active=True)

        # Actualización inmediata con los datos actuales
        temps = get_temperatures()
        gpu_pct = get_gpu_percent()
        self.overlay_window.update_metrics(
            self.last_cpu, temps.get("cpu"), gpu_pct, temps.get("gpu"), self.last_ram
        )

    def _stop_overlay(self):
        """Cierra el Gaming Overlay inmediatamente."""
        if self.overlay_window is not None:
            try:
                self.overlay_window.destroy()
            except Exception:
                pass
            self.overlay_window = None

        self.overlay_config.set("enabled", False)
        self._update_overlay_ui_state(is_active=False)

    def _on_overlay_closed(self):
        """Notificación cuando el overlay se destruye."""
        self.overlay_window = None
        self._update_overlay_ui_state(is_active=False)

    def _update_overlay_ui_state(self, is_active):
        """Actualiza el texto y colores del interruptor e indicador de estado."""
        if not hasattr(self, "btn_toggle_overlay") or not hasattr(self, "lbl_overlay_status"):
            return

        if is_active:
            self.lbl_overlay_status.config(text="● Activo", fg=C_GREEN)
            self.btn_toggle_overlay.config(
                text="  ✓  Overlay Activo (Ocultar)",
                bg=C_ACCENT,
                fg="#ffffff"
            )
        else:
            self.lbl_overlay_status.config(text="● Inactivo", fg=C_TEXT_DIM)
            self.btn_toggle_overlay.config(
                text="  ⚡  Activar Overlay",
                bg=C_BG_CARD_SEC,
                fg=C_TEXT_BODY
            )

    def _on_overlay_btn_hover(self, is_hover):
        """Efecto visual hover en el botón conmutador del overlay."""
        if self.overlay_window is not None:
            self.btn_toggle_overlay.config(bg=C_ACCENT_HOVER if is_hover else C_ACCENT)
        else:
            self.btn_toggle_overlay.config(
                bg=C_BTN_SEC_HOVER if is_hover else C_BG_CARD_SEC,
                fg=C_TEXT_TITLE if is_hover else C_TEXT_BODY
            )

    def _open_overlay_config(self):
        """Abre el diálogo modal de configuración del overlay."""
        OverlayConfigDialog(self, self.overlay_config, on_applied_callback=self._on_overlay_config_applied)

    def _on_overlay_config_applied(self):
        """Reaplica la configuración si el overlay está activo."""
        if self.overlay_window is not None:
            self.overlay_window.apply_config()

    # ─────────────────────────────────────────────────────────────────
    #  SECCIÓN 1: INICIO (MONITOREO EN TIEMPO REAL)
    # ─────────────────────────────────────────────────────────────────
    def _build_view_inicio(self):
        """Construye la vista de Inicio con medidores y diagnóstico."""
        main_pad = tk.Frame(self.view_inicio, bg=C_BG_MAIN, padx=26, pady=20)
        main_pad.pack(fill="both", expand=True)

        # 1. Cabecera
        header_row = tk.Frame(main_pad, bg=C_BG_MAIN)
        header_row.pack(fill="x", pady=(0, 14))

        title_box = tk.Frame(header_row, bg=C_BG_MAIN)
        title_box.pack(side="left")

        tk.Label(
            title_box, text="Estado general del sistema",
            font=("Segoe UI", 18, "bold"), fg=C_TEXT_TITLE, bg=C_BG_MAIN
        ).pack(anchor="w")

        tk.Label(
            title_box, text="Monitoreo continuo de recursos principales y diagnóstico automático",
            font=("Segoe UI", 9), fg=C_TEXT_MUTED, bg=C_BG_MAIN
        ).pack(anchor="w", pady=(1, 0))

        # Botón de exportación
        self.btn_export = ModernButton(
            header_row, text="Exportar informe", font=("Segoe UI", 9, "bold"),
            fg="#ffffff", bg_normal=C_BTN_SEC, bg_hover=C_BTN_SEC_HOVER,
            padx=16, pady=7, command=self._export_report
        )
        self.btn_export.pack(side="right")

        # 2. Tarjeta de Estado General
        self.status_card = tk.Frame(
            main_pad, bg=C_BG_CARD, padx=16, pady=12,
            highlightthickness=1, highlightbackground=C_BORDER
        )
        self.status_card.pack(fill="x", pady=(0, 14))

        status_left = tk.Frame(self.status_card, bg=C_BG_CARD)
        status_left.pack(side="left", fill="x", expand=True)

        self.status_badge = tk.Label(
            status_left, text="Iniciando monitoreo...",
            font=("Segoe UI", 11, "bold"), fg=C_TEXT_TITLE, bg=C_BG_CARD
        )
        self.status_badge.pack(anchor="w")

        self.status_desc = tk.Label(
            status_left, text="Recopilando métricas del sistema en tiempo real...",
            font=("Segoe UI", 9), fg=C_TEXT_MUTED, bg=C_BG_CARD, wraplength=680, justify="left"
        )
        self.status_desc.pack(anchor="w", pady=(2, 0))

        # 3. Fila de Medidores Semicirculares
        gauges_row = tk.Frame(main_pad, bg=C_BG_MAIN)
        gauges_row.pack(fill="x", pady=(0, 14))
        gauges_row.columnconfigure(0, weight=1)
        gauges_row.columnconfigure(1, weight=1)
        gauges_row.columnconfigure(2, weight=1)

        # CPU
        self.gauge_cpu_frame = tk.Frame(gauges_row, bg=C_BG_CARD, highlightthickness=1, highlightbackground=C_BORDER)
        self.gauge_cpu_frame.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        self.gauge_cpu = SemicircularGauge(self.gauge_cpu_frame, title="PROCESADOR (CPU)")
        self.gauge_cpu.pack(fill="both", expand=True)

        # RAM
        self.gauge_ram_frame = tk.Frame(gauges_row, bg=C_BG_CARD, highlightthickness=1, highlightbackground=C_BORDER)
        self.gauge_ram_frame.grid(row=0, column=1, padx=4, sticky="nsew")
        self.gauge_ram = SemicircularGauge(self.gauge_ram_frame, title="MEMORIA RAM")
        self.gauge_ram.pack(fill="both", expand=True)

        # Disco
        self.gauge_disk_frame = tk.Frame(gauges_row, bg=C_BG_CARD, highlightthickness=1, highlightbackground=C_BORDER)
        self.gauge_disk_frame.grid(row=0, column=2, padx=(8, 0), sticky="nsew")
        self.gauge_disk = SemicircularGauge(self.gauge_disk_frame, title="DISCO PRINCIPAL")
        self.gauge_disk.pack(fill="both", expand=True)

        # 4. Panel de Diagnóstico y Recomendaciones
        diag_container = tk.Frame(main_pad, bg=C_BG_CARD, highlightthickness=1, highlightbackground=C_BORDER)
        diag_container.pack(fill="both", expand=True)

        diag_hdr = tk.Frame(diag_container, bg=C_BG_CARD, padx=14, pady=8)
        diag_hdr.pack(fill="x")

        tk.Label(
            diag_hdr, text="DIAGNÓSTICO AUTOMÁTICO Y RECOMENDACIONES",
            font=("Segoe UI", 9, "bold"), fg=C_TEXT_MUTED, bg=C_BG_CARD
        ).pack(side="left")

        text_frame = tk.Frame(diag_container, bg=C_BG_CARD_SEC)
        text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        sb = tk.Scrollbar(text_frame, orient="vertical")
        sb.pack(side="right", fill="y")

        self.txt_diagnosis = tk.Text(
            text_frame, wrap="word", font=("Segoe UI", 9),
            fg=C_TEXT_BODY, bg=C_BG_CARD_SEC,
            relief="flat", padx=12, pady=10,
            yscrollcommand=sb.set, bd=0
        )
        self.txt_diagnosis.pack(fill="both", expand=True)
        sb.config(command=self.txt_diagnosis.yview)

        # Tags de color para el diagnóstico
        self.txt_diagnosis.tag_configure("title", font=("Segoe UI", 10, "bold"), foreground=C_TEXT_TITLE)
        self.txt_diagnosis.tag_configure("ok", foreground=C_GREEN, font=("Segoe UI", 9, "bold"))
        self.txt_diagnosis.tag_configure("warn", foreground=C_YELLOW, font=("Segoe UI", 9, "bold"))
        self.txt_diagnosis.tag_configure("crit", foreground=C_RED, font=("Segoe UI", 9, "bold"))
        self.txt_diagnosis.tag_configure("body", foreground=C_TEXT_BODY, font=("Segoe UI", 9))
        self.txt_diagnosis.tag_configure("note", foreground=C_TEXT_DIM, font=("Segoe UI", 8, "italic"))
        self.txt_diagnosis.tag_configure("rec_hdr", foreground=C_ACCENT, font=("Segoe UI", 9, "bold"))
        self.txt_diagnosis.tag_configure("rec_step", foreground=C_TEXT_MUTED, font=("Segoe UI", 9))

        self.txt_diagnosis.insert("1.0", "Iniciando diagnóstico automático...", "note")
        self.txt_diagnosis.config(state="disabled")

    # ─────────────────────────────────────────────────────────────────
    #  CICLOS DE ACTUALIZACIÓN AUTOMÁTICA
    # ─────────────────────────────────────────────────────────────────
    def _schedule_fast_updates(self):
        """Actualiza CPU y RAM cada 1 segundo sin bloquear la interfaz."""
        if not self._is_running:
            return

        try:
            cpu_val = get_cpu_percent(non_blocking=True)
            self.last_cpu = cpu_val

            ram_data = get_ram_info()
            self.last_ram = ram_data

            if hasattr(self, 'gauge_cpu') and cpu_val is not None:
                cpu_lvl = "critical" if cpu_val >= 95 else ("warning" if cpu_val >= 80 else "normal")
                self.gauge_cpu.update_value(
                    cpu_val, level=cpu_lvl,
                    detail="Uso actual en tiempo real"
                )

            if hasattr(self, 'gauge_ram') and ram_data:
                ram_pct = ram_data["percent"]
                ram_lvl = "critical" if ram_pct >= 95 else ("warning" if ram_pct >= 80 else "normal")
                ram_detail = f"{ram_data['used_gb']} GB de {ram_data['total_gb']} GB ({ram_data['available_gb']} GB libres)"
                self.gauge_ram.update_value(
                    ram_pct, level=ram_lvl,
                    detail=ram_detail
                )

            self._update_diagnosis_display()

            # Actualizar Gaming Overlay si está activo
            if self.overlay_window is not None and getattr(self.overlay_window, "_is_active", False):
                gpu_val = get_gpu_percent()
                temps = get_temperatures()
                self.overlay_window.update_metrics(
                    cpu_val, temps.get("cpu"), gpu_val, temps.get("gpu"), ram_data
                )
        except Exception:
            pass

        if self._is_running:
            self._fast_timer = self.after(1000, self._schedule_fast_updates)

    def _schedule_slow_updates(self):
        """Actualiza el estado de Almacenamiento cada 5 segundos."""
        if not self._is_running:
            return

        try:
            disk_data = get_disk_info()
            self.last_disk = disk_data

            if hasattr(self, 'gauge_disk') and disk_data:
                disk_pct = disk_data["percent"]
                disk_lvl = "critical" if disk_pct >= 95 else ("warning" if disk_pct >= 85 else "normal")
                disk_detail = f"{disk_data['used_gb']} GB usados de {disk_data['total_gb']} GB ({disk_data['free_gb']} GB libres)"
                self.gauge_disk.update_value(
                    disk_pct, level=disk_lvl,
                    detail=disk_detail
                )

            self._update_diagnosis_display()
        except Exception:
            pass

        if self._is_running:
            self._slow_timer = self.after(5000, self._schedule_slow_updates)

    def _update_diagnosis_display(self):
        """Calcula el estado general y formatea los diagnósticos con sus recomendaciones."""
        if self.last_cpu is None or self.last_ram is None or self.last_disk is None:
            return

        diags = run_all_diagnostics(
            self.last_cpu,
            self.last_ram["percent"] if self.last_ram else None,
            self.last_disk["percent"] if self.last_disk else None
        )
        self.last_diagnostics = diags
        self.last_recommendations = get_recommendations(diags)

        overall = get_system_overall_status(diags)
        self.last_overall_status = overall

        badge_text = overall.get("status_text", "Estado desconocido")
        badge_color = get_color_by_level(overall.get("level", "normal"))
        self.status_badge.config(text=f"● {badge_text}", fg=badge_color)
        self.status_desc.config(text=overall.get("summary", ""))

        txt = self.txt_diagnosis
        txt.config(state="normal")
        txt.delete("1.0", "end")

        for d in diags:
            lvl = d.get("level", "normal")
            tag_name = "ok" if lvl == "normal" else ("warn" if lvl == "warning" else "crit")
            label_text = "NORMAL" if lvl == "normal" else ("ADVERTENCIA" if lvl == "warning" else "ATENCIÓN")

            txt.insert("end", f"[{label_text}] ", tag_name)
            txt.insert("end", f"{d.get('metric')}: ", "title")
            txt.insert("end", f"{d.get('message')}\n\n", "body")

        txt.insert(
            "end",
            "Nota: Un valor elevado en un momento dado no indica necesariamente una falla permanente.\n"
            "El consumo varía según las aplicaciones y procesos en ejecución.\n\n",
            "note"
        )

        if self.last_recommendations:
            txt.insert("end", "Recomendaciones sugeridas:\n", "rec_hdr")
            for rec in self.last_recommendations:
                lvl_label = "Advertencia" if rec.get("level") == "warning" else "Atención"
                txt.insert("end", f"  • {rec.get('metric')} ({lvl_label}):\n", "title")
                for i, step in enumerate(rec.get("steps", []), 1):
                    txt.insert("end", f"     {i}. {step}\n", "rec_step")
                txt.insert("end", "\n")
        else:
            txt.insert("end", "Todos los parámetros se encuentran en niveles normales y estables.\n", "ok")

        txt.config(state="disabled")

    # ─────────────────────────────────────────────────────────────────
    #  SECCIÓN 2: WIFI Y RED
    # ─────────────────────────────────────────────────────────────────
    def _build_view_wifi(self):
        """Construye la vista de red y prueba de velocidad."""
        pad = tk.Frame(self.view_wifi, bg=C_BG_MAIN, padx=26, pady=20)
        pad.pack(fill="both", expand=True)

        # 1. Cabecera
        header = tk.Frame(pad, bg=C_BG_MAIN)
        header.pack(fill="x", pady=(0, 14))

        tk.Label(
            header, text="Conexión de red e Internet",
            font=("Segoe UI", 18, "bold"), fg=C_TEXT_TITLE, bg=C_BG_MAIN
        ).pack(anchor="w")

        tk.Label(
            header, text="Monitoreo del adaptador de red y medición real de velocidad bajo demanda",
            font=("Segoe UI", 9), fg=C_TEXT_MUTED, bg=C_BG_MAIN
        ).pack(anchor="w", pady=(1, 0))

        # 2. Información de Conexión
        conn_card = tk.Frame(pad, bg=C_BG_CARD, padx=18, pady=14, highlightthickness=1, highlightbackground=C_BORDER)
        conn_card.pack(fill="x", pady=(0, 16))

        tk.Label(
            conn_card, text="INFORMACIÓN DE CONEXIÓN ACTUAL",
            font=("Segoe UI", 9, "bold"), fg=C_TEXT_MUTED, bg=C_BG_CARD
        ).pack(anchor="w", pady=(0, 10))

        grid_info = tk.Frame(conn_card, bg=C_BG_CARD)
        grid_info.pack(fill="x")
        grid_info.columnconfigure(0, weight=1)
        grid_info.columnconfigure(1, weight=1)
        grid_info.columnconfigure(2, weight=1)
        grid_info.columnconfigure(3, weight=1)

        self.wifi_type_val = self._create_info_item(grid_info, 0, "Tipo de conexión", "Consultando...")
        self.wifi_ssid_val = self._create_info_item(grid_info, 1, "Red / SSID", "Consultando...")
        self.wifi_ip_val = self._create_info_item(grid_info, 2, "Dirección IP local", "Consultando...")
        self.wifi_state_val = self._create_info_item(grid_info, 3, "Acceso a Internet", "Consultando...")

        self.wifi_adapter_lbl = tk.Label(
            conn_card, text="Adaptador en uso: Consultando...",
            font=("Segoe UI", 8), fg=C_TEXT_DIM, bg=C_BG_CARD
        )
        self.wifi_adapter_lbl.pack(anchor="w", pady=(10, 0))

        # 3. Panel de Medición de Velocidad
        speed_panel = tk.Frame(pad, bg=C_BG_CARD, padx=18, pady=16, highlightthickness=1, highlightbackground=C_BORDER)
        speed_panel.pack(fill="x", pady=(0, 14))

        panel_top = tk.Frame(speed_panel, bg=C_BG_CARD)
        panel_top.pack(fill="x", pady=(0, 14))

        speed_title_box = tk.Frame(panel_top, bg=C_BG_CARD)
        speed_title_box.pack(side="left")

        tk.Label(
            speed_title_box, text="MEDICIÓN DE VELOCIDAD DE INTERNET",
            font=("Segoe UI", 11, "bold"), fg=C_TEXT_TITLE, bg=C_BG_CARD
        ).pack(anchor="w")

        self.lbl_speed_status = tk.Label(
            speed_title_box, text="Pulsa el botón para iniciar una medición real.",
            font=("Segoe UI", 9), fg=C_TEXT_MUTED, bg=C_BG_CARD
        )
        self.lbl_speed_status.pack(anchor="w", pady=(2, 0))

        self.btn_speedtest = ModernButton(
            panel_top, text="Probar velocidad", font=("Segoe UI", 10, "bold"),
            fg="#ffffff", bg_normal=C_ACCENT, bg_hover=C_ACCENT_HOVER,
            padx=18, pady=8, command=self._start_speed_test
        )
        self.btn_speedtest.pack(side="right")

        res_grid = tk.Frame(speed_panel, bg=C_BG_CARD)
        res_grid.pack(fill="x", pady=(0, 10))
        res_grid.columnconfigure(0, weight=1)
        res_grid.columnconfigure(1, weight=1)
        res_grid.columnconfigure(2, weight=1)

        self.card_download = self._create_speed_metric_card(res_grid, 0, "VELOCIDAD DE DESCARGA", "-- Mbps", "0 MB/s", C_GREEN)
        self.card_upload = self._create_speed_metric_card(res_grid, 1, "VELOCIDAD DE CARGA", "-- Mbps", "0 MB/s", C_INFO_CYAN)
        self.card_ping = self._create_speed_metric_card(res_grid, 2, "LATENCIA (PING)", "-- ms", "Tiempo de respuesta", C_YELLOW)

        self.lbl_speed_meta = tk.Label(
            speed_panel, text="Última prueba realizada: Ninguna en esta sesión.",
            font=("Segoe UI", 8), fg=C_TEXT_DIM, bg=C_BG_CARD
        )
        self.lbl_speed_meta.pack(anchor="w")

        # 4. Nota sobre Consumo de Datos
        note_card = tk.Frame(pad, bg=C_BG_CARD_SEC, padx=14, pady=10, highlightthickness=1, highlightbackground=C_BORDER)
        note_card.pack(fill="x")

        tk.Label(
            note_card, text="Información sobre la prueba y consumo de datos:",
            font=("Segoe UI", 8, "bold"), fg=C_ACCENT, bg=C_BG_CARD_SEC
        ).pack(anchor="w")

        explanation = (
            "• Conversión de unidades: 1 MB/s (megabyte por segundo) equivale aproximadamente a 8 Mbps (megabits por segundo).\n"
            "• La prueba transfiere paquetes de prueba reales para medir el rendimiento y consume entre 20 y 45 MB de datos.\n"
            "• La latencia refleja la respuesta hacia el servidor de prueba seleccionado y no el ping en todos los servicios web."
        )
        tk.Label(
            note_card, text=explanation, font=("Segoe UI", 8),
            fg=C_TEXT_MUTED, bg=C_BG_CARD_SEC, justify="left"
        ).pack(anchor="w", pady=(3, 0))

    def _create_info_item(self, parent, col, title, initial_val):
        """Crea una celda de información de red."""
        box = tk.Frame(parent, bg=C_BG_CARD)
        box.grid(row=0, column=col, padx=4, sticky="w")

        tk.Label(box, text=title, font=("Segoe UI", 8), fg=C_TEXT_DIM, bg=C_BG_CARD).pack(anchor="w")
        val_lbl = tk.Label(box, text=initial_val, font=("Segoe UI", 10, "bold"), fg=C_TEXT_TITLE, bg=C_BG_CARD)
        val_lbl.pack(anchor="w")
        return val_lbl

    def _create_speed_metric_card(self, parent, col, title, initial_val, sub_val, accent_color):
        """Crea una tarjeta de resultado de velocidad."""
        outer = tk.Frame(parent, bg=C_BORDER)
        outer.grid(row=0, column=col, padx=5, sticky="nsew")

        card = tk.Frame(outer, bg=C_BG_CARD_SEC, padx=14, pady=12)
        card.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), fg=C_TEXT_MUTED, bg=C_BG_CARD_SEC).pack(anchor="w")

        val_lbl = tk.Label(card, text=initial_val, font=("Segoe UI", 20, "bold"), fg=accent_color, bg=C_BG_CARD_SEC)
        val_lbl.pack(anchor="w", pady=(4, 2))

        sub_lbl = tk.Label(card, text=sub_val, font=("Segoe UI", 8), fg=C_TEXT_DIM, bg=C_BG_CARD_SEC)
        sub_lbl.pack(anchor="w")

        return {"val": val_lbl, "sub": sub_lbl, "color": accent_color}

    def _refresh_wifi_data(self):
        """Consulta en segundo plano el estado de red."""
        def worker():
            conn = network_utils.get_connection_info()
            self._safe_after(0, lambda: self._apply_wifi_data(conn))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_wifi_data(self, conn):
        """Aplica la información de red a la interfaz."""
        if not self._is_running:
            return

        conn_type = conn.get("connection_type", "Desconocido")
        self.wifi_type_val.config(text=conn_type)

        ssid_text = conn.get("ssid", "No disponible")
        self.wifi_ssid_val.config(text=ssid_text)

        ip_text = conn.get("local_ip", "No disponible")
        self.wifi_ip_val.config(text=ip_text)

        has_net = conn.get("internet_access", False)
        net_text = "Conectado a Internet" if has_net else "Sin conexión a Internet"
        net_color = C_GREEN if has_net else C_RED
        self.wifi_state_val.config(text=net_text, fg=net_color)

        adapter_name = conn.get("adapter_name", "Desconocido")
        link_speed = conn.get("link_speed", "")
        speed_txt = f" • Enlace: {link_speed}" if link_speed and link_speed != "No disponible" else ""
        self.wifi_adapter_lbl.config(text=f"Adaptador en uso: {adapter_name}{speed_txt}")

    def _start_speed_test(self):
        """Ejecuta la prueba de velocidad en segundo plano."""
        if self._is_testing_speed:
            return

        self._is_testing_speed = True
        self.btn_speedtest.config(state="disabled", text="Midiendo...")
        self.lbl_speed_status.config(text="Iniciando prueba de velocidad real...", fg=C_ACCENT)

        def progress_cb(msg):
            self._safe_after(0, lambda: self.lbl_speed_status.config(text=msg))

        def worker():
            res = network_utils.run_speed_test(progress_callback=progress_cb)
            self._safe_after(0, lambda: self._on_speed_test_finished(res))

        threading.Thread(target=worker, daemon=True).start()

    def _on_speed_test_finished(self, res):
        """Aplica los resultados del test de velocidad."""
        self._is_testing_speed = False
        self.btn_speedtest.config(state="normal", text="Probar velocidad")

        if res.get("success"):
            self.last_speed_test = res
            dl = res["download_mbps"]
            ul = res["upload_mbps"]
            ping = res["ping_ms"]
            dl_mbs = res["download_mbs"]
            ul_mbs = res["upload_mbs"]

            self.card_download["val"].config(text=f"{dl} Mbps")
            self.card_download["sub"].config(text=f"~{dl_mbs} MB/s de descarga")

            self.card_upload["val"].config(text=f"{ul} Mbps")
            self.card_upload["sub"].config(text=f"~{ul_mbs} MB/s de subida")

            self.card_ping["val"].config(text=f"{ping} ms")
            self.card_ping["sub"].config(text="Latencia al servidor")

            self.lbl_speed_status.config(text="Prueba completada con éxito.", fg=C_GREEN)
            self.lbl_speed_meta.config(
                text=f"Última medición: {res['timestamp']} • Servidor: {res.get('server_name', 'Cercano')}"
            )
        else:
            err_msg = res.get("error", "Error desconocido")
            self.lbl_speed_status.config(text=f"Aviso: {err_msg}", fg=C_RED)
            if self.last_speed_test:
                self.lbl_speed_meta.config(
                    text=f"(La última medición falló. Datos anteriores conservados: {self.last_speed_test['timestamp']})"
                )

    # ─────────────────────────────────────────────────────────────────
    #  SECCIÓN 3: COMPONENTES DE HARDWARE Y CONTROLADORES
    # ─────────────────────────────────────────────────────────────────
    def _build_view_componentes(self):
        """Construye la vista de hardware y tabla de drivers."""
        pad = tk.Frame(self.view_componentes, bg=C_BG_MAIN, padx=26, pady=20)
        pad.pack(fill="both", expand=True)

        header = tk.Frame(pad, bg=C_BG_MAIN)
        header.pack(fill="x", pady=(0, 10))

        tk.Label(
            header, text="Componentes de hardware y controladores",
            font=("Segoe UI", 18, "bold"), fg=C_TEXT_TITLE, bg=C_BG_MAIN
        ).pack(anchor="w")

        tk.Label(
            header, text="Especificaciones reales del equipo y consulta de drivers instalados",
            font=("Segoe UI", 9), fg=C_TEXT_MUTED, bg=C_BG_MAIN
        ).pack(anchor="w", pady=(1, 0))

        # Tarjetas de Hardware
        self.hw_container = tk.Frame(pad, bg=C_BG_CARD, padx=16, pady=12, highlightthickness=1, highlightbackground=C_BORDER)
        self.hw_container.pack(fill="x", pady=(0, 14))

        tk.Label(
            self.hw_container, text="ESPECIFICACIONES DE HARDWARE",
            font=("Segoe UI", 9, "bold"), fg=C_TEXT_MUTED, bg=C_BG_CARD
        ).pack(anchor="w", pady=(0, 8))

        self.hw_grid = tk.Frame(self.hw_container, bg=C_BG_CARD)
        self.hw_grid.pack(fill="x")
        self.hw_grid.columnconfigure(0, weight=1)
        self.hw_grid.columnconfigure(1, weight=1)
        self.hw_grid.columnconfigure(2, weight=1)

        self.card_hw_cpu = self._create_hw_card(self.hw_grid, 0, 0, "PROCESADOR (CPU)", "Consultando...")
        self.card_hw_gpu = self._create_hw_card(self.hw_grid, 0, 1, "TARJETA GRÁFICA (GPU)", "Consultando...")
        self.card_hw_ram = self._create_hw_card(self.hw_grid, 0, 2, "MEMORIA RAM FÍSICA", "Consultando...")
        self.card_hw_board = self._create_hw_card(self.hw_grid, 1, 0, "PLACA MADRE Y BIOS", "Consultando...")
        self.card_hw_disk = self._create_hw_card(self.hw_grid, 1, 1, "ALMACENAMIENTO", "Consultando...")
        self.card_hw_os = self._create_hw_card(self.hw_grid, 1, 2, "SISTEMA OPERATIVO", "Consultando...")

        # Sección de Controladores
        drivers_box = tk.Frame(pad, bg=C_BG_CARD, padx=16, pady=12, highlightthickness=1, highlightbackground=C_BORDER)
        drivers_box.pack(fill="both", expand=True)

        toolbar = tk.Frame(drivers_box, bg=C_BG_CARD)
        toolbar.pack(fill="x", pady=(0, 8))

        tk.Label(
            toolbar, text="CONTROLADORES DETECTADOS",
            font=("Segoe UI", 9, "bold"), fg=C_TEXT_MUTED, bg=C_BG_CARD
        ).pack(side="left")

        self.lbl_drivers_count = tk.Label(
            toolbar, text="(Consultando...)",
            font=("Segoe UI", 8), fg=C_TEXT_DIM, bg=C_BG_CARD
        )
        self.lbl_drivers_count.pack(side="left", padx=(6, 0))

        self.btn_refresh_drivers = ModernButton(
            toolbar, text="Actualizar información", font=("Segoe UI", 8, "bold"),
            fg="#ffffff", bg_normal=C_BTN_SEC, bg_hover=C_BTN_SEC_HOVER,
            padx=12, pady=4, command=self._reload_drivers
        )
        self.btn_refresh_drivers.pack(side="right")

        # Filtros
        filter_bar = tk.Frame(drivers_box, bg=C_BG_CARD)
        filter_bar.pack(fill="x", pady=(0, 8))

        tk.Label(filter_bar, text="Categoría:", font=("Segoe UI", 8), fg=C_TEXT_MUTED, bg=C_BG_CARD).pack(side="left")
        self.combo_category = ttk.Combobox(
            filter_bar, state="readonly", width=18, style="TCombobox",
            values=[
                "Todos", "Pantalla / GPU", "Red / Conectividad", "Audio",
                "Bluetooth", "USB / Periféricos", "Almacenamiento", "Chipset / Sistema", "Otros dispositivos"
            ]
        )
        self.combo_category.current(0)
        self.combo_category.pack(side="left", padx=(6, 16))
        self.combo_category.bind("<<ComboboxSelected>>", lambda e: self._apply_driver_filters())

        tk.Label(filter_bar, text="Buscar:", font=("Segoe UI", 8), fg=C_TEXT_MUTED, bg=C_BG_CARD).pack(side="left")
        self.entry_search = tk.Entry(
            filter_bar, bg=C_BG_CARD_SEC, fg=C_TEXT_TITLE, insertbackground=C_TEXT_TITLE,
            relief="flat", font=("Segoe UI", 9), highlightthickness=1, highlightbackground=C_BORDER
        )
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.entry_search.bind("<KeyRelease>", lambda e: self._apply_driver_filters())

        # Tabla Treeview
        table_frame = tk.Frame(drivers_box, bg=C_BG_CARD_SEC)
        table_frame.pack(fill="both", expand=True)

        cols = ("device", "category", "manufacturer", "version", "date", "status")
        self.tree_drivers = ttk.Treeview(
            table_frame, columns=cols, show="headings",
            style="Drivers.Treeview", selectmode="browse"
        )

        self.tree_drivers.heading("device", text="Dispositivo")
        self.tree_drivers.heading("category", text="Categoría")
        self.tree_drivers.heading("manufacturer", text="Fabricante / Proveedor")
        self.tree_drivers.heading("version", text="Versión")
        self.tree_drivers.heading("date", text="Fecha")
        self.tree_drivers.heading("status", text="Estado")

        self.tree_drivers.column("device", width=250, minwidth=140)
        self.tree_drivers.column("category", width=130, minwidth=100)
        self.tree_drivers.column("manufacturer", width=150, minwidth=100)
        self.tree_drivers.column("version", width=100, minwidth=80)
        self.tree_drivers.column("date", width=85, minwidth=70)
        self.tree_drivers.column("status", width=65, minwidth=50)

        tree_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree_drivers.yview)
        self.tree_drivers.configure(yscrollcommand=tree_scroll.set)

        self.tree_drivers.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

    def _create_hw_card(self, parent, row, col, title, initial_body):
        """Crea una tarjeta para una categoría de hardware."""
        card = tk.Frame(parent, bg=C_BG_CARD_SEC, padx=10, pady=8, highlightthickness=1, highlightbackground=C_BORDER)
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

        tk.Label(card, text=title, font=("Segoe UI", 7, "bold"), fg=C_ACCENT, bg=C_BG_CARD_SEC).pack(anchor="w")

        body_lbl = tk.Label(
            card, text=initial_body, font=("Segoe UI", 8),
            fg=C_TEXT_BODY, bg=C_BG_CARD_SEC, justify="left", wraplength=210
        )
        body_lbl.pack(anchor="w", pady=(2, 0))
        return body_lbl

    def _load_hardware_in_background(self):
        """Carga en segundo plano la información de hardware y controladores."""
        def worker():
            hw = hardware_utils.get_hardware_info()
            drvs = hardware_utils.get_installed_drivers()
            self._safe_after(0, lambda: self._apply_hardware_and_drivers(hw, drvs))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_hardware_and_drivers(self, hw, drivers):
        """Aplica los datos de hardware y controladores."""
        if not self._is_running:
            return

        self._hardware_data = hw
        self._drivers_cache = drivers

        # CPU
        cpu = hw["cpu"]
        self.card_hw_cpu.config(
            text=f"{cpu['name']}\nNúcleos: {cpu['physical_cores']} físicos / {cpu['logical_cores']} lógicos\nFrecuencia máx: {cpu['max_freq_ghz']}"
        )

        # GPU
        if hw["gpus"]:
            gpu_lines = [f"{g['name']} ({g['vram']})" for g in hw["gpus"]]
            self.card_hw_gpu.config(text="\n".join(gpu_lines))
        else:
            self.card_hw_gpu.config(text="No se detectó GPU dedicada")

        # RAM
        ram = hw["ram"]
        ram_txt = f"Total: {ram['total_gb']} GB\nMódulos: {ram['modules_count']}"
        if ram["modules"]:
            m_first = ram["modules"][0]
            ram_txt += f" ({m_first['capacity_gb']}GB @ {m_first['speed']})"
        self.card_hw_ram.config(text=ram_txt)

        # Placa Madre y BIOS
        board = hw["motherboard"]
        self.card_hw_board.config(
            text=f"{board['manufacturer']} {board['product']}\nBIOS: {board['bios_version']} ({board['bios_date']})"
        )

        # Almacenamiento
        storage = hw["storage"]
        drive_txt = []
        for d in storage["physical_drives"][:2]:
            if d.get("size_gb") and d["size_gb"] != "N/D":
                drive_txt.append(f"{d['model']} ({d['size_gb']} GB)")
            else:
                drive_txt.append(d["model"])
        if not drive_txt:
            drive_txt = ["Unidad estándar"]
        self.card_hw_disk.config(text="\n".join(drive_txt))

        # Sistema Operativo
        sys_os = hw["os"]
        self.card_hw_os.config(
            text=f"{sys_os['name']}\nVersión: {sys_os['version']} ({sys_os['architecture']})\nEquipo: {sys_os['computer_name']}"
        )

        self._apply_driver_filters()

    def _reload_drivers(self):
        """Recarga la lista de controladores bajo demanda."""
        if self._is_loading_drivers:
            return

        self._is_loading_drivers = True
        self.btn_refresh_drivers.config(state="disabled", text="Consultando...")
        self.lbl_drivers_count.config(text="(Consultando al sistema...)")

        def worker():
            drvs = hardware_utils.get_installed_drivers()
            self._safe_after(0, lambda: self._on_drivers_reloaded(drvs))

        threading.Thread(target=worker, daemon=True).start()

    def _on_drivers_reloaded(self, drvs):
        """Aplica la recarga de controladores."""
        self._is_loading_drivers = False
        self.btn_refresh_drivers.config(state="normal", text="Actualizar información")
        self._drivers_cache = drvs
        self._apply_driver_filters()

    def _apply_driver_filters(self):
        """Filtra y muestra los controladores coincidentes."""
        category = self.combo_category.get()
        query = self.entry_search.get()

        filtered = hardware_utils.filter_drivers(self._drivers_cache, search_query=query, category=category)

        for item in self.tree_drivers.get_children():
            self.tree_drivers.delete(item)

        for d in filtered:
            provider = d['provider'] if d['provider'] != 'N/D' else d['manufacturer']
            self.tree_drivers.insert(
                "", "end",
                values=(d["device_name"], d["category"], provider, d["version"], d["date"], d["status"])
            )

        self.lbl_drivers_count.config(text=f"({len(filtered)} de {len(self._drivers_cache)} encontrados)")

    # ─────────────────────────────────────────────────────────────────
    #  EXPORTACIÓN DE INFORME TXT
    # ─────────────────────────────────────────────────────────────────
    def _export_report(self):
        """Genera y guarda un informe TXT estructurado."""
        try:
            report_text = generate_report(
                cpu=self.last_cpu,
                ram=self.last_ram,
                disk=self.last_disk,
                diagnostics=self.last_diagnostics,
                recommendations=self.last_recommendations,
                network_test=self.last_speed_test,
                overall_status=self.last_overall_status
            )

            file_path = filedialog.asksaveasfilename(
                title="Guardar informe de PC Rescue",
                defaultextension=".txt",
                filetypes=[("Archivo de texto", "*.txt"), ("Todos los archivos", "*.*")],
                initialdir=str(Path.home() / "Documents"),
                initialfile=f"informe_pc_rescue_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )

            if not file_path:
                return

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report_text)

            messagebox.showinfo(
                "Informe guardado",
                f"El informe se guardó correctamente en:\n\n{file_path}"
            )
        except PermissionError:
            messagebox.showerror(
                "Permisos insuficientes",
                "No se pudo escribir en la carpeta seleccionada. Elige otra ubicación."
            )
        except Exception as e:
            messagebox.showerror(
                "Error al exportar",
                f"Ocurrió un error inesperado al guardar el archivo:\n{e}"
            )

    # ─────────────────────────────────────────────────────────────────
    #  CIERRE SEGURO
    # ─────────────────────────────────────────────────────────────────
    def _on_close(self):
        """Cancela temporizadores y cierra la ventana de forma limpia."""
        self._is_running = False
        if self._fast_timer:
            try:
                self.after_cancel(self._fast_timer)
            except Exception:
                pass
        if self._slow_timer:
            try:
                self.after_cancel(self._slow_timer)
            except Exception:
                pass
        if self.overlay_window is not None:
            try:
                self.overlay_window.destroy()
            except Exception:
                pass
            self.overlay_window = None
        close_gpu_monitoring()
        close_temperature_monitoring()
        self.destroy()


# =====================================================================
#  PUNTO DE ENTRADA
# =====================================================================
if __name__ == "__main__":
    app = PCRescueApp()
    app.mainloop()
