"""
hardware_utils.py — Consulta de componentes de hardware y controladores para PC Rescue.

Este módulo obtiene información real y no destructiva del hardware y drivers instalados en Windows
mediante consultas PowerShell / CIM (WMI) y psutil.

No requiere privilegios de administrador.
No modifica controladores ni configuraciones del sistema.
"""

import json
import os
import platform
import re
import subprocess
from datetime import datetime
import psutil

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _run_ps_json(script, timeout=12.0):
    """Ejecuta un bloque de PowerShell y retorna la salida parseada como JSON."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
        if res.returncode == 0 and res.stdout.strip():
            return json.loads(res.stdout.strip())
    except Exception:
        pass
    return None


def get_hardware_info():
    """Recopila información de CPU, GPU, Placa madre, RAM, Almacenamiento y Sistema Operativo.

    Returns:
        dict con categorías detalladas.
    """
    info = {
        "os": {
            "name": platform.system() + " " + platform.release(),
            "edition": "Windows",
            "version": platform.version(),
            "architecture": platform.architecture()[0],
            "computer_name": platform.node(),
        },
        "cpu": {
            "name": platform.processor() or "Procesador x86/x64",
            "manufacturer": "No disponible",
            "physical_cores": psutil.cpu_count(logical=False) or "N/D",
            "logical_cores": psutil.cpu_count(logical=True) or "N/D",
            "max_freq_ghz": "N/D",
        },
        "gpus": [],
        "motherboard": {
            "manufacturer": "No disponible",
            "product": "No disponible",
            "bios_version": "No disponible",
            "bios_date": "No disponible",
        },
        "ram": {
            "total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 1),
            "modules_count": "No disponible",
            "modules": [],
        },
        "storage": {
            "physical_drives": [],
            "partitions": [],
        },
    }

    # 1. Obtener particiones activas vía psutil
    try:
        for part in psutil.disk_partitions(all=False):
            if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                info["storage"]["partitions"].append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / (1024 ** 3), 1),
                    "used_gb": round(usage.used / (1024 ** 3), 1),
                    "free_gb": round(usage.free / (1024 ** 3), 1),
                    "percent": usage.percent,
                })
            except Exception:
                pass
    except Exception:
        pass

    # 2. Consultar WMI / CIM en lote para máxima velocidad
    ps_script = """
    $os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture, CSName
    $cpu = Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, Manufacturer
    $gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion, VideoProcessor)
    $board = Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product
    $bios = Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion, ReleaseDate
    $ram = @(Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity, Speed, Manufacturer, DeviceLocator)
    $disk = @(Get-CimInstance Win32_DiskDrive | Select-Object Model, Size, MediaType, InterfaceType)

    [PSCustomObject]@{
        OS = $os
        CPU = $cpu
        GPU = $gpu
        Board = $board
        BIOS = $bios
        RAM = $ram
        Disk = $disk
    } | ConvertTo-Json -Depth 3
    """

    data = _run_ps_json(ps_script, timeout=8.0)
    if not data:
        return info

    # Procesar Sistema Operativo
    if data.get("OS"):
        os_data = data["OS"]
        if os_data.get("Caption"):
            info["os"]["name"] = os_data["Caption"].strip()
            info["os"]["edition"] = os_data["Caption"].strip()
        if os_data.get("Version"):
            info["os"]["version"] = str(os_data["Version"]).strip()
        if os_data.get("OSArchitecture"):
            info["os"]["architecture"] = str(os_data["OSArchitecture"]).strip()
        if os_data.get("CSName"):
            info["os"]["computer_name"] = str(os_data["CSName"]).strip()

    # Procesar CPU
    if data.get("CPU"):
        cpu_data = data["CPU"]
        if cpu_data.get("Name"):
            info["cpu"]["name"] = re.sub(r'\s+', ' ', cpu_data["Name"]).strip()
        if cpu_data.get("Manufacturer"):
            info["cpu"]["manufacturer"] = cpu_data["Manufacturer"].strip()
        if cpu_data.get("NumberOfCores"):
            info["cpu"]["physical_cores"] = cpu_data["NumberOfCores"]
        if cpu_data.get("NumberOfLogicalProcessors"):
            info["cpu"]["logical_cores"] = cpu_data["NumberOfLogicalProcessors"]
        if cpu_data.get("MaxClockSpeed"):
            freq_ghz = round(float(cpu_data["MaxClockSpeed"]) / 1000.0, 2)
            info["cpu"]["max_freq_ghz"] = f"{freq_ghz} GHz"

    # Procesar GPUs
    raw_gpus = data.get("GPU", [])
    if isinstance(raw_gpus, dict):
        raw_gpus = [raw_gpus]
    for g in raw_gpus:
        name = g.get("Name")
        if not name:
            continue
        vram_str = "No disponible"
        adapter_ram = g.get("AdapterRAM")
        if adapter_ram and isinstance(adapter_ram, (int, float)) and adapter_ram > 0:
            # En sistemas de 32 bits a veces AdapterRAM llega truncado a 4GB, si es mayor se muestra en GB
            vram_gb = round(adapter_ram / (1024 ** 3), 1)
            if vram_gb >= 1.0:
                vram_str = f"{vram_gb} GB"
            else:
                vram_mb = round(adapter_ram / (1024 ** 2))
                vram_str = f"{vram_mb} MB"

        info["gpus"].append({
            "name": name.strip(),
            "driver_version": g.get("DriverVersion") or "N/D",
            "vram": vram_str,
            "processor": g.get("VideoProcessor") or "N/D",
        })

    # Procesar Placa madre y BIOS
    if data.get("Board"):
        b = data["Board"]
        info["motherboard"]["manufacturer"] = (b.get("Manufacturer") or "Desconocido").strip()
        info["motherboard"]["product"] = (b.get("Product") or "Desconocido").strip()

    if data.get("BIOS"):
        bio = data["BIOS"]
        info["motherboard"]["bios_version"] = (bio.get("SMBIOSBIOSVersion") or "N/D").strip()
        raw_date = bio.get("ReleaseDate")
        if raw_date:
            # Formatear fecha si viene como /Date(...)/ o YYYYMMDD
            info["motherboard"]["bios_date"] = _clean_date_str(str(raw_date))

    # Procesar Módulos de RAM física
    raw_rams = data.get("RAM", [])
    if isinstance(raw_rams, dict):
        raw_rams = [raw_rams]
    modules_list = []
    for r in raw_rams:
        cap_bytes = r.get("Capacity")
        cap_gb = round(int(cap_bytes) / (1024 ** 3), 1) if cap_bytes else "N/D"
        speed = f"{r.get('Speed')} MHz" if r.get("Speed") else "N/D"
        mfg = (r.get("Manufacturer") or "Genérico").strip()
        slot = (r.get("DeviceLocator") or "Slot").strip()
        modules_list.append({
            "slot": slot,
            "capacity_gb": cap_gb,
            "speed": speed,
            "manufacturer": mfg,
        })
    info["ram"]["modules"] = modules_list
    info["ram"]["modules_count"] = len(modules_list)

    # Procesar Unidades de disco físico
    raw_disks = data.get("Disk", [])
    if isinstance(raw_disks, dict):
        raw_disks = [raw_disks]
    disk_list = []
    for d in raw_disks:
        model = (d.get("Model") or "Disco Genérico").strip()
        size_bytes = d.get("Size")
        size_gb = round(int(size_bytes) / (1024 ** 3), 1) if size_bytes else "N/D"
        m_type = (d.get("MediaType") or "Disco").strip()
        disk_list.append({
            "model": model,
            "size_gb": size_gb,
            "media_type": m_type,
            "interface": d.get("InterfaceType") or "SATA/NVMe",
        })
    # Priorizar unidades de almacenamiento reales (con tamaño numérico) sobre ranuras de tarjetas vacías
    disk_list.sort(key=lambda x: (x["size_gb"] == "N/D", str(x["model"])))
    info["storage"]["physical_drives"] = disk_list

    return info


def _clean_date_str(val):
    """Limpia cadenas de fecha de WMI / JSON a DD/MM/AAAA."""
    if not val:
        return "N/D"
    val = str(val)
    # Formato /Date(1794268800000)/
    m = re.search(r'/Date\((\d+)\)/', val)
    if m:
        try:
            ts = int(m.group(1)) / 1000.0
            return datetime.fromtimestamp(ts).strftime("%d/%m/%Y")
        except Exception:
            pass
    # Formato YYYYMMDD
    if len(val) >= 8 and val[:8].isdigit():
        return f"{val[6:8]}/{val[4:6]}/{val[:4]}"
    return val[:10]


def _categorize_device(device_class, device_name):
    """Mapea una clase o nombre de dispositivo a una categoría amigable."""
    c = (device_class or "").upper()
    n = (device_name or "").upper()

    if "DISPLAY" in c or "VIDEO" in c or "GRAPHIC" in n or "GEFORCE" in n or "RADEON" in n or "NVIDIA" in n or "INTEL(R) HD" in n:
        return "Pantalla / GPU"
    elif "NET" in c or "NETWORK" in c or "WIFI" in n or "WIRELESS" in n or "ETHERNET" in n or "BLUETOOTH" in n:
        if "BLUETOOTH" in c or "BLUETOOTH" in n:
            return "Bluetooth"
        return "Red / Conectividad"
    elif "MEDIA" in c or "AUDIO" in c or "SOUND" in c or "SONIDO" in n or "AUDIO" in n or "REALTEK AUDIO" in n:
        return "Audio"
    elif "BLUETOOTH" in c:
        return "Bluetooth"
    elif "USB" in c or "USB" in n:
        return "USB / Periféricos"
    elif "SCSI" in c or "HDC" in c or "DISK" in c or "STORAGE" in c or "ALMACEN" in n:
        return "Almacenamiento"
    elif "SYSTEM" in c or "CHIPSET" in n or "PROCESSOR" in c or "ACPI" in n:
        return "Chipset / Sistema"
    else:
        return "Otros dispositivos"


def get_installed_drivers():
    """Consulta los controladores firmados instalados en Windows.

    Returns:
        list de dicts con:
            - device_name: Nombre del dispositivo
            - category: Categoría amigable
            - manufacturer: Fabricante del dispositivo
            - provider: Proveedor del driver
            - version: Versión del controlador
            - date: Fecha formateada
            - status: Estado ('OK' u otro)
    """
    ps_script = """
    Get-CimInstance -Query "SELECT DeviceName, DeviceClass, Manufacturer, DriverProviderName, DriverVersion, DriverDate FROM Win32_PnPSignedDriver WHERE DeviceName IS NOT NULL" | Select-Object -First 120 DeviceName, DeviceClass, Manufacturer, DriverProviderName, DriverVersion, DriverDate | ConvertTo-Json -Depth 2
    """

    data = _run_ps_json(ps_script, timeout=15.0)
    if not data:
        return []

    if isinstance(data, dict):
        data = [data]

    drivers = []
    seen = set()

    for d in data:
        name = (d.get("DeviceName") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)

        dev_class = (d.get("DeviceClass") or "").strip()
        cat = _categorize_device(dev_class, name)

        raw_date = d.get("DriverDate")
        date_str = _clean_date_str(raw_date)

        drivers.append({
            "device_name": name,
            "category": cat,
            "manufacturer": (d.get("Manufacturer") or "Genérico").strip(),
            "provider": (d.get("DriverProviderName") or "Microsoft / Fabricante").strip(),
            "version": (d.get("DriverVersion") or "N/D").strip(),
            "date": date_str,
            "status": "OK",
        })

    # Ordenar por nombre de dispositivo
    drivers.sort(key=lambda x: x["device_name"].lower())
    return drivers


def filter_drivers(drivers, search_query="", category="Todos"):
    """Filtra una lista de drivers por texto de búsqueda y por categoría."""
    query = (search_query or "").strip().lower()
    filtered = []

    for d in drivers:
        if category != "Todos" and d["category"] != category:
            continue

        if query:
            match = (
                query in d["device_name"].lower()
                or query in d["manufacturer"].lower()
                or query in d["provider"].lower()
                or query in d["category"].lower()
            )
            if not match:
                continue

        filtered.append(d)

    return filtered
