"""
network_utils.py — Información de red y prueba de velocidad para PC Rescue.

Este módulo obtiene:
    1. Datos reales de la conexión actual (WiFi o Ethernet, SSID, IP local, adaptador).
    2. Medición real de velocidad (Descarga Mbps, Carga Mbps, Latencia ms) mediante speedtest.
    3. Conversión de unidades (Mbps a MB/s) y notas sobre consumo de datos.

No bloquea la GUI: las mediciones de velocidad se diseñan para ejecutarse en hilos secundarios.
"""

import os
import socket
import subprocess
import sys
from datetime import datetime
import psutil

# Compatibilidad con PyInstaller / modo ventana sin consola (console=False):
# speedtest-cli falla al importar en Python 3 si sys.stdout es None o no tiene fileno().
def _ensure_valid_stdio():
    """Garantiza descriptores de archivo válidos para stdout y stderr."""
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

_ensure_valid_stdio()

# Import lazily: the GUI can start and show its other diagnostics even when
# speedtest-cli is missing or incompatible with the interpreter.
SPEEDTEST_AVAILABLE = True  # The actual import is deferred to run_speed_test().


def check_internet_connectivity(host="1.1.1.1", port=53, timeout=2.0):
    """Comprueba rápidamente si hay acceso a Internet mediante socket TCP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def get_local_ip():
    """Obtiene la dirección IP local utilizada para salir a la red."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1.0)
        # No envía paquetes reales, solo resuelve la interfaz de ruta
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # Fallback usando psutil
        try:
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                        return addr.address
        except Exception:
            pass
        return "No disponible"


def get_wifi_details():
    """Consulta detalles de la interfaz inalámbrica mediante netsh en Windows.

    Returns:
        dict con 'is_wifi_connected', 'ssid', 'adapter_name', 'signal', etc.
    """
    info = {
        "is_wifi_connected": False,
        "ssid": "No disponible",
        "adapter_name": "No disponible",
        "signal": "No disponible",
    }
    try:
        res = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            timeout=3.0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        output = res.stdout

        for line in output.splitlines():
            line_strip = line.strip()
            if ":" not in line_strip:
                continue
            key, val = [x.strip() for x in line_strip.split(":", 1)]
            key_lower = key.lower()

            if "descripci" in key_lower or "description" in key_lower:
                info["adapter_name"] = val
            elif "estado" in key_lower or "state" in key_lower:
                val_clean = val.lower().strip()
                if "desconectado" in val_clean or "disconnected" in val_clean:
                    info["is_wifi_connected"] = False
                elif "conectado" in val_clean or "connected" in val_clean:
                    info["is_wifi_connected"] = True
            elif "ssid" in key_lower and "bssid" not in key_lower:
                if val:
                    info["ssid"] = val
            elif "seal" in key_lower or "signal" in key_lower:
                info["signal"] = val

    except Exception:
        pass

    return info


def get_connection_info():
    """Obtiene el estado completo de la conexión activa (WiFi o Ethernet).

    Returns:
        dict con:
            - is_connected (bool)
            - connection_type: 'WiFi', 'Ethernet' o 'Desconectado'
            - ssid: Nombre de red WiFi o 'No disponible (Conexión cableada)'
            - local_ip: IP v4 local
            - adapter_name: Nombre descriptivo del adaptador en uso
            - internet_access: bool indicando si responde a Internet
            - speed_mbps: Velocidad de enlace del adaptador (si está disponible)
    """
    has_internet = check_internet_connectivity()
    local_ip = get_local_ip()
    wifi_data = get_wifi_details()

    # Identificar interfaz activa principal vía psutil
    active_iface = None
    iface_speed = "No disponible"
    try:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        for name, stat in stats.items():
            if stat.isup:
                # Comprobar si esta interfaz tiene la IP local activa
                iface_addrs = [a.address for a in addrs.get(name, [])]
                if local_ip in iface_addrs:
                    active_iface = name
                    if stat.speed and stat.speed > 0:
                        iface_speed = f"{stat.speed} Mbps"
                    break
    except Exception:
        pass

    # Determinar si es WiFi o Ethernet
    if wifi_data["is_wifi_connected"]:
        conn_type = "WiFi"
        ssid = wifi_data["ssid"] if wifi_data["ssid"] != "No disponible" else "Red Inalámbrica"
        adapter = wifi_data["adapter_name"] if wifi_data["adapter_name"] != "No disponible" else (active_iface or "Adaptador Wi-Fi")
    elif active_iface and ("wi-fi" in active_iface.lower() or "wireless" in active_iface.lower()):
        conn_type = "WiFi"
        ssid = wifi_data["ssid"]
        adapter = active_iface
    elif local_ip != "No disponible" or has_internet:
        conn_type = "Ethernet"
        ssid = "No disponible (Conexión cableada)"
        adapter = active_iface or "Adaptador Ethernet"
    else:
        conn_type = "Desconectado"
        ssid = "No disponible"
        adapter = "Sin adaptador activo"

    return {
        "is_connected": (conn_type != "Desconectado"),
        "connection_type": conn_type,
        "ssid": ssid,
        "local_ip": local_ip,
        "adapter_name": adapter,
        "internet_access": has_internet,
        "link_speed": iface_speed,
    }


def run_speed_test(progress_callback=None):
    """Ejecuta una prueba real de velocidad de Internet (Descarga, Subida, Latencia).

    Args:
        progress_callback: Función opcional callback(step_text) para informar del progreso.

    Returns:
        dict con:
            - success (bool)
            - download_mbps (float)
            - upload_mbps (float)
            - ping_ms (float)
            - download_mbs (float) [MB/s]
            - upload_mbs (float) [MB/s]
            - server_name (str)
            - timestamp (str)
            - error (str o None)
    """
    _ensure_valid_stdio()
    try:
        import speedtest
    except Exception as e:
        return {
            "success": False,
            "error": f"No se pudo cargar speedtest-cli: {e}",
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }

    try:
        if progress_callback:
            progress_callback("Buscando mejor servidor...")

        st = speedtest.Speedtest()
        st.get_best_server()
        ping = round(st.results.ping, 1)
        server = f"{st.results.server.get('sponsor', '')} ({st.results.server.get('name', '')})".strip()

        if progress_callback:
            progress_callback("Midiendo velocidad de descarga...")

        download_bps = st.download()
        download_mbps = round(download_bps / 1_000_000, 2)
        download_mbs = round(download_mbps / 8, 2)

        if progress_callback:
            progress_callback("Midiendo velocidad de carga...")

        upload_bps = st.upload()
        upload_mbps = round(upload_bps / 1_000_000, 2)
        upload_mbs = round(upload_mbps / 8, 2)

        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        return {
            "success": True,
            "download_mbps": download_mbps,
            "upload_mbps": upload_mbps,
            "ping_ms": ping,
            "download_mbs": download_mbs,
            "upload_mbs": upload_mbs,
            "server_name": server or "Servidor más cercano",
            "timestamp": now_str,
            "error": None,
        }

    except socket.gaierror:
        return {
            "success": False,
            "error": "Fallo de resolución DNS o sin conexión a Internet.",
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error de speedtest: {e}",
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }
