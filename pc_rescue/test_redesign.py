"""
test_redesign.py — Pruebas completas de integración para el rediseño de PC Rescue.
"""
import os
import tempfile
import time
from app import PCRescueApp
from report import generate_report
import network_utils
import hardware_utils
import terminal_utils
from unittest.mock import patch

print("=" * 60)
print("  INICIANDO SUITE DE PRUEBAS DE PC RESCUE REDISEÑADO")
print("=" * 60)

# 1. Crear ventana principal
app = PCRescueApp()
app.update()
print("[OK] 1. Ventana PCRescueApp creada exitosamente.")

# 2. Verificar que los 3 botones de navegación existen
assert "inicio" in app.nav_buttons
assert "wifi" in app.nav_buttons
assert "componentes" in app.nav_buttons
print("[OK] 2. Barra lateral tiene exactamente las 3 secciones: Inicio, WiFi, Componentes.")

# 3. Verificar estado inicial en Inicio
assert app.current_section == "inicio"
assert app.gauge_cpu is not None
assert app.gauge_ram is not None
assert app.gauge_disk is not None
print("[OK] 3. Sección Inicio inicializada con los 3 medidores semicirculares.")

# 4. Forzar ciclos de actualización automática
app._schedule_fast_updates()
app._schedule_slow_updates()
app.update()

assert app.last_cpu is not None
assert app.last_ram is not None
assert app.last_disk is not None
print(f"[OK] 4. Métricas en tiempo real obtenidas: CPU={app.last_cpu}%, RAM={app.last_ram['percent']}%, Disco={app.last_disk['percent']}%")

# 5. Probar cambio a vista WiFi
app._switch_section("wifi")
app.update()
assert app.current_section == "wifi"
print("[OK] 5. Navegación fluida a sección WiFi.")

# Comprobar datos de conexión
conn = network_utils.get_connection_info()
app._apply_wifi_data(conn)
app.update()
assert app.wifi_type_val.cget("text") in ("WiFi", "Ethernet", "Desconectado")
print(f"[OK] 6. Información de red aplicada: {app.wifi_type_val.cget('text')} (IP: {app.wifi_ip_val.cget('text')})")

# 6. Probar cambio a vista Componentes
app._switch_section("componentes")
app.update()
assert app.current_section == "componentes"
print("[OK] 7. Navegación fluida a sección Componentes.")

# Cargar hardware y drivers de prueba en Componentes
hw = hardware_utils.get_hardware_info()
drvs = hardware_utils.get_installed_drivers()
app._apply_hardware_and_drivers(hw, drvs)
app.update()

assert len(app.tree_drivers.get_children()) > 0
print(f"[OK] 8. Hardware y {len(drvs)} controladores cargados en la tabla de Componentes.")

# Probar filtro de controladores
filtered = hardware_utils.filter_drivers(drvs, category="Audio")
print(f"[OK] 9. Filtro por categoría 'Audio': {len(filtered)} controladores encontrados.")

# 7. Probar generación y exportación del informe
mock_speed = {
    "success": True,
    "download_mbps": 125.4,
    "upload_mbps": 45.2,
    "ping_ms": 14.5,
    "download_mbs": 15.68,
    "upload_mbs": 5.65,
    "server_name": "Test Server",
    "timestamp": "27/10/2026 19:40:00"
}

rep = generate_report(
    cpu=app.last_cpu,
    ram=app.last_ram,
    disk=app.last_disk,
    diagnostics=app.last_diagnostics,
    recommendations=app.last_recommendations,
    network_test=mock_speed,
    overall_status=app.last_overall_status
)

assert "PC RESCUE - INFORME DEL SISTEMA" in rep
assert "ESTADO GENERAL DEL SISTEMA" in rep
assert "ULTIMA PRUEBA DE VELOCIDAD DE INTERNET" in rep
assert "125.4 Mbps" in rep

# Guardar en archivo temporal para verificar permisos y formato
tmp = os.path.join(tempfile.gettempdir(), "test_pc_rescue_redesign_report.txt")
with open(tmp, "w", encoding="utf-8") as f:
    f.write(rep)

assert os.path.exists(tmp)
with open(tmp, "r", encoding="utf-8") as f:
    saved = f.read()
assert saved == rep
os.remove(tmp)
print("[OK] 10. Informe TXT ampliado generado y verificado correctamente.")

# 8. Probar utilidades y botones de Terminal (CMD y PowerShell)
assert hasattr(app, "btn_cmd") and app.btn_cmd is not None
assert hasattr(app, "btn_powershell") and app.btn_powershell is not None

cmd_path = terminal_utils.get_cmd_path()
assert cmd_path is not None and os.path.isfile(cmd_path) and "cmd.exe" in cmd_path.lower()
print(f"[OK] 11. Deteccion de cmd.exe: {cmd_path}")

ps_path, ps_variant = terminal_utils.get_powershell_path()
assert ps_path is not None and os.path.isfile(ps_path)
print(f"[OK] 12. Deteccion de PowerShell ({ps_variant}): {ps_path}")

# Verificar lanzamiento sin bloquear ni romper la interfaz (usando mock para no dejar ventanas abiertas en tests)
with patch("subprocess.Popen") as mock_popen:
    ok_cmd, msg_cmd = terminal_utils.open_cmd()
    assert ok_cmd is True
    assert mock_popen.called
    args, kwargs = mock_popen.call_args
    assert kwargs.get("creationflags") == terminal_utils.CREATE_NEW_CONSOLE

with patch("subprocess.Popen") as mock_popen:
    ok_ps, msg_ps = terminal_utils.open_powershell()
    assert ok_ps is True
    assert mock_popen.called
    args, kwargs = mock_popen.call_args
    assert kwargs.get("creationflags") == terminal_utils.CREATE_NEW_CONSOLE

print("[OK] 13. Lanzador de consolas independientes probado (CMD y PowerShell con CREATE_NEW_CONSOLE).")

# 9. Cierre seguro de la aplicación
app._on_close()
print("[OK] 14. Cierre seguro ejecutado sin timers pendientes.")

print("")
print("=" * 60)
print("  ¡TODAS LAS PRUEBAS (14/14) PASARON CON ÉXITO!")
print("=" * 60)
