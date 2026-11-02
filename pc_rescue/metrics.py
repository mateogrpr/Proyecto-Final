"""
metrics.py — Obtención de métricas del sistema.

Este módulo contiene funciones que leen datos reales de CPU, RAM, disco,
GPU y temperaturas del equipo usando psutil, PDH nativo de Windows (Performance
Data Helper) y sensores de hardware cuando están disponibles.

Cada función devuelve datos reales obtenidos de fuentes fiables del sistema,
o None si un valor o sensor no se encuentra disponible (sin inventar datos).
"""

import ctypes
import os
import re
import shutil
import subprocess
import threading
import time
from ctypes import wintypes
import psutil


def init_cpu_monitoring():
    """Inicializa la medición de CPU llamando una primera vez con interval=None."""
    try:
        psutil.cpu_percent(interval=None)
    except Exception:
        pass


def get_cpu_percent(non_blocking=True):
    """Devuelve el porcentaje de uso actual de la CPU.

    Args:
        non_blocking: Si es True, usa interval=None para no congelar la GUI
                      y devolver el uso acumulado desde la última llamada.
                      Si es False, espera 1 segundo (útil para pruebas en consola).

    Returns:
        float: Porcentaje de uso (0.0 a 100.0), o None si falla.
    """
    try:
        if non_blocking:
            return psutil.cpu_percent(interval=None)
        return psutil.cpu_percent(interval=1)
    except Exception:
        return None


def get_ram_info():
    """Devuelve información sobre la memoria RAM.

    Returns:
        dict con claves:
            - percent (float): Porcentaje de uso (0.0 a 100.0)
            - total_gb (float): RAM total en gigabytes
            - used_gb (float): RAM en uso en gigabytes
            - available_gb (float): RAM disponible en gigabytes
        O None si falla.
    """
    try:
        mem = psutil.virtual_memory()
        return {
            "percent": mem.percent,
            "total_gb": round(mem.total / (1024 ** 3), 1),
            "used_gb": round(mem.used / (1024 ** 3), 1),
            "available_gb": round(mem.available / (1024 ** 3), 1),
        }
    except Exception:
        return None


def get_disk_info(path="C:\\"):
    """Devuelve información sobre el disco principal.

    Args:
        path: Ruta del disco a consultar. Por defecto "C:\\" (Windows).

    Returns:
        dict con claves:
            - percent (float): Porcentaje de uso (0.0 a 100.0)
            - total_gb (float): Espacio total en gigabytes
            - used_gb (float): Espacio usado en gigabytes
            - free_gb (float): Espacio libre en gigabytes
        O None si falla.
    """
    try:
        disk = psutil.disk_usage(path)
        return {
            "percent": disk.percent,
            "total_gb": round(disk.total / (1024 ** 3), 1),
            "used_gb": round(disk.used / (1024 ** 3), 1),
            "free_gb": round(disk.free / (1024 ** 3), 1),
        }
    except Exception:
        return None


# =====================================================================
#  MONITORIZACIÓN REAL DE GPU (PDH NATIVO DE WINDOWS Y NVIDIA-SMI)
# =====================================================================

class _WindowsGpuMonitor:
    """Lee el porcentaje de utilización real de la GPU en Windows sin lanzar subprocesses.

    Utiliza los contadores PDH nativos de Windows (\\GPU Engine(*)\\Utilization Percentage)
    mediante ctypes.windll.pdh. Funciona en Windows 10 y 11 para GPU Intel, AMD y NVIDIA,
    con un consumo de CPU prácticamente nulo (~0.0%).
    """

    def __init__(self):
        self._pdh = None
        self._h_query = None
        self._h_counter = None
        self._initialized = False
        self._lock = threading.Lock()
        self._init_pdh()

    def _init_pdh(self):
        with self._lock:
            try:
                self._pdh = getattr(ctypes.windll, "pdh", None)
                if not self._pdh:
                    return

                h_q = wintypes.HANDLE()
                status = self._pdh.PdhOpenQueryW(None, 0, ctypes.byref(h_q))
                if status != 0:
                    return
                self._h_query = h_q

                h_c = wintypes.HANDLE()
                status = self._pdh.PdhAddEnglishCounterW(
                    self._h_query,
                    r"\GPU Engine(*)\Utilization Percentage",
                    0,
                    ctypes.byref(h_c),
                )
                if status != 0:
                    self._pdh.PdhCloseQuery(self._h_query)
                    self._h_query = None
                    return
                self._h_counter = h_c

                # Muestreo inicial para que PDH establezca la línea base de tiempo
                self._pdh.PdhCollectQueryData(self._h_query)
                self._initialized = True
            except Exception:
                self._initialized = False

    def get_gpu_percent(self):
        """Devuelve el porcentaje de utilización de GPU en [0.0, 100.0] o None."""
        if not self._initialized or not self._h_query or not self._h_counter:
            return None

        with self._lock:
            try:
                status = self._pdh.PdhCollectQueryData(self._h_query)
                if status != 0:
                    return None

                class PDH_FMT_COUNTERVALUE(ctypes.Structure):
                    _fields_ = [("CStatus", wintypes.DWORD), ("doubleValue", ctypes.c_double)]

                class PDH_FMT_COUNTERVALUE_ITEM_W(ctypes.Structure):
                    _fields_ = [("szName", wintypes.LPWSTR), ("FmtValue", PDH_FMT_COUNTERVALUE)]

                buf_size = wintypes.DWORD(0)
                item_count = wintypes.DWORD(0)
                # PDH_FMT_DOUBLE = 0x00000200
                res = self._pdh.PdhGetFormattedCounterArrayW(
                    self._h_counter, 0x00000200, ctypes.byref(buf_size), ctypes.byref(item_count), None
                )
                # 0x800007D2 = PDH_MORE_DATA
                if res != 0 and (res & 0xFFFFFFFF) != 0x800007D2:
                    return None

                if buf_size.value == 0 or item_count.value == 0:
                    return 0.0

                buf = (ctypes.c_byte * buf_size.value)()
                res = self._pdh.PdhGetFormattedCounterArrayW(
                    self._h_counter, 0x00000200, ctypes.byref(buf_size), ctypes.byref(item_count), buf
                )
                if res != 0:
                    return None

                items = ctypes.cast(buf, ctypes.POINTER(PDH_FMT_COUNTERVALUE_ITEM_W))

                # Agrupamos por proceso (PID) tomando el motor más exigido en cada uno,
                # que es el estándar de medición del Administrador de Tareas de Windows.
                proc_usage = {}
                for i in range(item_count.value):
                    val = items[i].FmtValue.doubleValue
                    if val > 0:
                        name = items[i].szName or ""
                        pid = name.split("_")[1] if "pid_" in name else name
                        if pid not in proc_usage or val > proc_usage[pid]:
                            proc_usage[pid] = val

                total = sum(proc_usage.values())
                return round(max(0.0, min(100.0, total)), 1)
            except Exception:
                return None

    def close(self):
        """Libera la consulta PDH."""
        with self._lock:
            if self._h_query and self._pdh:
                try:
                    self._pdh.PdhCloseQuery(self._h_query)
                except Exception:
                    pass
                self._h_query = None
                self._h_counter = None
                self._initialized = False


_gpu_monitor_instance = None
_gpu_monitor_lock = threading.Lock()


def init_gpu_monitoring():
    """Inicializa el monitor de GPU PDH."""
    global _gpu_monitor_instance
    with _gpu_monitor_lock:
        if _gpu_monitor_instance is None:
            _gpu_monitor_instance = _WindowsGpuMonitor()


def close_gpu_monitoring():
    """Cierra y libera los recursos del monitor de GPU."""
    global _gpu_monitor_instance
    with _gpu_monitor_lock:
        if _gpu_monitor_instance is not None:
            _gpu_monitor_instance.close()
            _gpu_monitor_instance = None


def get_gpu_percent():
    """Devuelve el uso de GPU actual en porcentaje real (0.0 a 100.0) o None.

    Prioriza nvidia-smi para tarjetas dedicadas NVIDIA si está disponible,
    o el contador de rendimiento de GPU de Windows (PDH) en caso contrario.
    """
    # 1. Probar nvidia-smi si existe
    smi = _get_nvidia_smi_path()
    if smi:
        try:
            res = subprocess.run(
                [smi, "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=1.0,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            if res.returncode == 0 and res.stdout.strip():
                val = float(res.stdout.strip().splitlines()[0])
                return round(max(0.0, min(100.0, val)), 1)
        except Exception:
            pass

    # 2. Usar monitor PDH nativo de Windows
    global _gpu_monitor_instance
    if _gpu_monitor_instance is None:
        init_gpu_monitoring()

    if _gpu_monitor_instance is not None:
        return _gpu_monitor_instance.get_gpu_percent()

    return None


# =====================================================================
#  OBTENCIÓN DE TEMPERATURAS REALES (CPU Y GPU)
# =====================================================================
#
#  Sistema de respaldo ordenado (por prioridad):
#
#    1. WinTmp / LibreHardwareMonitor via pythonnet (CPU + GPU).
#       Requiere permisos de administrador para leer sensores de CPU.
#       Se inicializa una sola vez; reutiliza la instancia de Computer.
#
#    2. nvidia-smi (solo GPU NVIDIA).
#       No requiere admin. Solo disponible en equipos con GPU NVIDIA.
#
#    3. Win32_PerfFormattedData_Counters_ThermalZoneInformation (CPU).
#       Contadores de rendimiento de Windows que reportan la temperatura
#       de zonas térmicas ACPI en Kelvin. NO requiere admin.
#
#    4. LHM / OHM WMI namespace o MSAcpi_ThermalZoneTemperature (CPU + GPU).
#       Solo funcionan si hay un monitor de hardware corriendo como servicio
#       o si se ejecuta con permisos de administrador.
#
#  Si ningún método devuelve un valor válido, se muestra N/D.
# =====================================================================

import json as _json_mod  # import local para evitar conflictos con el json de nivel de módulo

_nvidia_smi_path = None
_nvidia_smi_checked = False

_temperature_cache = {"cpu": None, "gpu": None}
_temp_cache_lock = threading.Lock()
_last_temp_query_time = 0.0
_is_probing_temp = False

# --- Diagnóstico y acceso a WinTmp ---
_wintmp_status = {
    "tried": False,
    "available": False,
    "error": None,
}


def _query_wintmp_temperatures():
    """Paso 1: Intenta obtener temperaturas mediante la biblioteca WinTmp.

    Usa WinTmp.CPU_Temp() y WinTmp.GPU_Temp() si están disponibles.
    Registra el estado y errores para diagnóstico.
    """
    global _wintmp_status
    results = {"cpu": None, "gpu": None}

    # Si ya se intentó y falló el import (por dependencias faltantes/no admin), no reintentar continuamente
    if _wintmp_status["tried"] and not _wintmp_status["available"]:
        return results

    _wintmp_status["tried"] = True

    try:
        import WinTmp

        # CPU Temp
        if hasattr(WinTmp, "CPU_Temp"):
            try:
                c_val = WinTmp.CPU_Temp()
                if isinstance(c_val, (int, float)) and 0.0 < float(c_val) < 125.0:
                    results["cpu"] = round(float(c_val), 1)
            except Exception as e:
                _wintmp_status["error"] = f"WinTmp.CPU_Temp: {e}"

        # GPU Temp
        if hasattr(WinTmp, "GPU_Temp"):
            try:
                g_val = WinTmp.GPU_Temp()
                if isinstance(g_val, (int, float)) and 0.0 < float(g_val) < 125.0:
                    results["gpu"] = round(float(g_val), 1)
            except Exception as e:
                _wintmp_status["error"] = f"WinTmp.GPU_Temp: {e}"

        _wintmp_status["available"] = True
    except Exception as e:
        _wintmp_status["available"] = False
        _wintmp_status["error"] = str(e)

    return results


# --- Estado del backend WinTmp / LibreHardwareMonitor (pythonnet) ---
_lhm_computer = None        # Instancia de Hardware.Computer (reutilizable)
_lhm_initialized = False    # True después del primer intento de inicialización
_lhm_available = False       # True si Open() fue exitoso
_lhm_init_lock = threading.Lock()
_lhm_Hardware = None         # Referencia al módulo LibreHardwareMonitor.Hardware


def _init_lhm_backend():
    """Inicializa LibreHardwareMonitor via pythonnet (una sola vez).

    Usa la DLL incluida en el paquete WinTmp pero configura el Computer
    con solo CPU y GPU habilitados (sin Memory) para evitar el crash por
    falta de RAMSPDToolkit/SMBus sin permisos de administrador.

    Returns:
        bool: True si la inicialización fue exitosa.
    """
    global _lhm_computer, _lhm_initialized, _lhm_available, _lhm_Hardware

    with _lhm_init_lock:
        if _lhm_initialized:
            return _lhm_available

        _lhm_initialized = True
        try:
            import clr
            # Localizar la DLL de LibreHardwareMonitor empaquetada con WinTmp
            import importlib.util
            wintmp_spec = importlib.util.find_spec("WinTmp")
            if wintmp_spec is None or wintmp_spec.origin is None:
                return False

            wintmp_dir = os.path.dirname(wintmp_spec.origin)
            dll_path = os.path.join(wintmp_dir, "LibreHardwareMonitorLib.dll")
            if not os.path.isfile(dll_path):
                return False

            clr.AddReference(dll_path)
            from LibreHardwareMonitor import Hardware
            _lhm_Hardware = Hardware

            hw = Hardware.Computer()
            hw.IsCpuEnabled = True
            hw.IsGpuEnabled = True
            # Deshabilitar Memory para evitar crash por RAMSPDToolkit sin admin
            hw.IsMemoryEnabled = False
            hw.IsMotherboardEnabled = False
            hw.IsStorageEnabled = False
            hw.IsNetworkEnabled = False
            hw.IsControllerEnabled = False
            hw.IsBatteryEnabled = False
            hw.IsPsuEnabled = False
            hw.Open()

            _lhm_computer = hw
            _lhm_available = True
            return True

        except Exception:
            _lhm_available = False
            return False


def _close_lhm_backend():
    """Cierra la instancia de LibreHardwareMonitor si está activa."""
    global _lhm_computer, _lhm_available
    with _lhm_init_lock:
        if _lhm_computer is not None:
            try:
                _lhm_computer.Close()
            except Exception:
                pass
            _lhm_computer = None
            _lhm_available = False


def _query_lhm_temperatures():
    """Obtiene temperaturas de CPU y GPU via LibreHardwareMonitor / pythonnet.

    Returns:
        dict: {'cpu': float o None, 'gpu': float o None}
    """
    results = {"cpu": None, "gpu": None}

    if not _lhm_available or _lhm_computer is None or _lhm_Hardware is None:
        return results

    GPU_TYPES = (
        _lhm_Hardware.HardwareType.GpuNvidia,
        _lhm_Hardware.HardwareType.GpuAmd,
        _lhm_Hardware.HardwareType.GpuIntel,
    )

    try:
        for h in _lhm_computer.Hardware:
            h.Update()

            for sensor in h.Sensors:
                if sensor.SensorType != _lhm_Hardware.SensorType.Temperature:
                    continue

                s_val = sensor.Value
                if s_val is None:
                    continue

                val_f = float(s_val)
                # Validar rango razonable
                if not (0.0 < val_f < 125.0):
                    continue

                s_name = str(sensor.Name)

                # CPU: preferir "CPU Package", luego cualquier "Core"
                if h.HardwareType == _lhm_Hardware.HardwareType.Cpu:
                    if results["cpu"] is None or "Package" in s_name:
                        results["cpu"] = round(val_f, 1)

                # GPU
                elif h.HardwareType in GPU_TYPES:
                    if results["gpu"] is None:
                        results["gpu"] = round(val_f, 1)

    except Exception:
        pass

    return results


def _get_nvidia_smi_path():
    """Localiza el ejecutable de nvidia-smi de forma rápida."""
    global _nvidia_smi_path, _nvidia_smi_checked
    if _nvidia_smi_checked:
        return _nvidia_smi_path

    _nvidia_smi_checked = True
    path = shutil.which("nvidia-smi.exe") or shutil.which("nvidia-smi")
    if path and os.path.isfile(path):
        _nvidia_smi_path = path
        return _nvidia_smi_path

    candidates = [
        r"C:\Windows\System32\nvidia-smi.exe",
        r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            _nvidia_smi_path = c
            return _nvidia_smi_path

    _nvidia_smi_path = None
    return None


def _query_nvidia_gpu_temp():
    """Obtiene la temperatura de GPU via nvidia-smi.

    Returns:
        float o None: Temperatura en °C, o None si no disponible.
    """
    smi = _get_nvidia_smi_path()
    if not smi:
        return None
    try:
        res = subprocess.run(
            [smi, "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=1.0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        if res.returncode == 0 and res.stdout.strip():
            val = float(res.stdout.strip().splitlines()[0])
            if 0.0 < val < 125.0:
                return round(val, 1)
    except Exception:
        pass
    return None


def _query_thermal_zone_temperature():
    """Obtiene la temperatura de CPU via contadores de rendimiento de Windows.

    Usa Win32_PerfFormattedData_Counters_ThermalZoneInformation, que reporta
    la temperatura de zonas térmicas ACPI en Kelvin. NO requiere permisos
    de administrador.

    Returns:
        float o None: Temperatura de CPU en °C, o None si no disponible.
    """
    # 1. Intentar via WMI nativo de Python (ultrarrápido, ~0.05s)
    try:
        import pythoncom
        import wmi
        pythoncom.CoInitialize()
        try:
            w = wmi.WMI()
            items = w.Win32_PerfFormattedData_Counters_ThermalZoneInformation()
            for item in items:
                temp_k = getattr(item, "Temperature", None)
                if temp_k is not None:
                    temp_c = float(temp_k) - 273.15
                    if 0.0 < temp_c < 125.0:
                        return round(temp_c, 1)
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        pass

    # 2. Respaldo via PowerShell con timeout estricto
    ps_cmd = (
        "Get-CimInstance Win32_PerfFormattedData_Counters_ThermalZoneInformation "
        "-ErrorAction SilentlyContinue | Select-Object Name, Temperature | ConvertTo-Json"
    )
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=3.0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        if res.returncode == 0 and res.stdout.strip():
            data = _json_mod.loads(res.stdout.strip())
            if isinstance(data, dict):
                data = [data]

            for item in data:
                temp_k = item.get("Temperature")
                if temp_k is not None:
                    temp_c = float(temp_k) - 273.15
                    if 0.0 < temp_c < 125.0:
                        return round(temp_c, 1)
    except Exception:
        pass
    return None


_last_wmi_hwmonitor_query = 0.0
_wmi_hwmonitor_available = None


def _query_wmi_hwmonitor_temperatures():
    """Respaldo: intenta obtener temperaturas vía LHM/OHM WMI namespace o ACPI root/wmi.

    Returns:
        dict: {'cpu': float o None, 'gpu': float o None}
    """
    global _last_wmi_hwmonitor_query, _wmi_hwmonitor_available
    results = {"cpu": None, "gpu": None}

    # Si ya se comprobó que no hay soporte, no repetir cada tick (consultar cada 30 segundos)
    now = time.time()
    if _wmi_hwmonitor_available is False and (now - _last_wmi_hwmonitor_query < 30.0):
        return results

    _last_wmi_hwmonitor_query = now

    ps_cmd = (
        "$lhm = Get-CimInstance -Namespace root/LibreHardwareMonitor -Query "
        "\"SELECT Name, SensorType, Value FROM Sensor WHERE SensorType='Temperature'\" -ErrorAction SilentlyContinue; "
        "if ($lhm) { $lhm | Select-Object Name, Value | ConvertTo-Json; exit } "
        "$ohm = Get-CimInstance -Namespace root/OpenHardwareMonitor -Query "
        "\"SELECT Name, SensorType, Value FROM Sensor WHERE SensorType='Temperature'\" -ErrorAction SilentlyContinue; "
        "if ($ohm) { $ohm | Select-Object Name, Value | ConvertTo-Json; exit } "
        "$acpi = Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue; "
        "if ($acpi) { $acpi | Select-Object CurrentTemperature | ConvertTo-Json; exit }"
    )

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=2.0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        if res.returncode == 0 and res.stdout.strip():
            data = _json_mod.loads(res.stdout.strip())
            if isinstance(data, dict):
                data = [data]

            for item in data:
                # ACPI Thermal Zone (décimas de Kelvin)
                if "CurrentTemperature" in item:
                    temp_k = float(item["CurrentTemperature"])
                    temp_c = (temp_k - 2732.0) / 10.0
                    if 0.0 < temp_c < 125.0 and results["cpu"] is None:
                        results["cpu"] = round(temp_c, 1)

                # LHM / OHM sensor data
                name = str(item.get("Name", "")).lower()
                val = item.get("Value")
                if val is not None:
                    try:
                        f_val = float(val)
                        if 0.0 < f_val < 125.0:
                            if "cpu" in name or "package" in name or "core" in name:
                                if results["cpu"] is None:
                                    results["cpu"] = round(f_val, 1)
                            elif "gpu" in name and results["gpu"] is None:
                                results["gpu"] = round(f_val, 1)
                    except (ValueError, TypeError):
                        pass

            _wmi_hwmonitor_available = True
        else:
            _wmi_hwmonitor_available = False
    except Exception:
        _wmi_hwmonitor_available = False

    return results


def _query_sensors_backend():
    """Consulta todas las fuentes de temperatura en orden de prioridad.

    Sistema de respaldo ordenado:
      1. WinTmp (CPU_Temp, GPU_Temp).
      2. LibreHardwareMonitor via pythonnet (CPU + GPU).
      3. nvidia-smi (solo GPU NVIDIA).
      4. Win32_PerfFormattedData_Counters_ThermalZoneInformation (CPU, no requiere admin).
      5. LHM/OHM WMI namespace o MSAcpi_ThermalZoneTemperature (respaldo general).
    """
    results = {"cpu": None, "gpu": None}

    # --- Fuente 1: WinTmp ---
    wintmp_temps = _query_wintmp_temperatures()
    if wintmp_temps["cpu"] is not None:
        results["cpu"] = wintmp_temps["cpu"]
    if wintmp_temps["gpu"] is not None:
        results["gpu"] = wintmp_temps["gpu"]

    # --- Fuente 2: LibreHardwareMonitor via pythonnet (si WinTmp no devolvió ambos) ---
    if results["cpu"] is None or results["gpu"] is None:
        if not _lhm_initialized:
            _init_lhm_backend()

        if _lhm_available:
            lhm_temps = _query_lhm_temperatures()
            if results["cpu"] is None and lhm_temps["cpu"] is not None:
                results["cpu"] = lhm_temps["cpu"]
            if results["gpu"] is None and lhm_temps["gpu"] is not None:
                results["gpu"] = lhm_temps["gpu"]

    # --- Fuente 3: nvidia-smi (solo GPU) ---
    if results["gpu"] is None:
        nvidia_temp = _query_nvidia_gpu_temp()
        if nvidia_temp is not None:
            results["gpu"] = nvidia_temp

    # --- Fuente 4: ThermalZoneInformation (solo CPU, no requiere admin) ---
    if results["cpu"] is None:
        tz_temp = _query_thermal_zone_temperature()
        if tz_temp is not None:
            results["cpu"] = tz_temp

    # --- Fuente 5: WMI HW Monitor / ACPI (respaldo general) ---
    if results["cpu"] is None or results["gpu"] is None:
        wmi_temps = _query_wmi_hwmonitor_temperatures()
        if results["cpu"] is None and wmi_temps["cpu"] is not None:
            results["cpu"] = wmi_temps["cpu"]
        if results["gpu"] is None and wmi_temps["gpu"] is not None:
            results["gpu"] = wmi_temps["gpu"]

    # --- Actualizar caché protegido por Lock ---
    with _temp_cache_lock:
        _temperature_cache["cpu"] = results["cpu"]
        _temperature_cache["gpu"] = results["gpu"]


def get_temperatures():
    """Devuelve las temperaturas reales de CPU y GPU en grados Celsius.

    Returns:
        dict:
            - 'cpu': float en °C, o None si no hay sensor disponible.
            - 'gpu': float en °C, o None si no hay sensor disponible.
    """
    global _last_temp_query_time, _is_probing_temp

    now = time.time()
    # Actualizar en segundo plano cada 3 segundos para no bloquear la interfaz
    if now - _last_temp_query_time > 3.0 and not _is_probing_temp:
        _last_temp_query_time = now
        _is_probing_temp = True

        def _worker():
            global _is_probing_temp
            try:
                _query_sensors_backend()
            finally:
                _is_probing_temp = False

        threading.Thread(target=_worker, daemon=True).start()

    with _temp_cache_lock:
        return dict(_temperature_cache)


def get_temperature_backend_diagnostic():
    """Devuelve información de diagnóstico sobre las fuentes de temperatura."""
    return {
        "wintmp": dict(_wintmp_status),
        "lhm_available": _lhm_available,
        "nvidia_smi": _nvidia_smi_path is not None,
        "cache": dict(_temperature_cache),
    }


def close_temperature_monitoring():
    """Libera los recursos de monitorización de temperatura (LHM, etc.)."""
    _close_lhm_backend()
