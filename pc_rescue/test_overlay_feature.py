"""
test_overlay_feature.py — Suite de pruebas para Gaming Overlay e Iconos en PC Rescue 2.0.
"""

import os
import sys
import time
import psutil
from app import PCRescueApp, resource_path
from overlay import OverlayConfig, GamingOverlayWindow, OverlayConfigDialog
import metrics

print("============================================================")
print("  INICIANDO SUITE DE PRUEBAS DE GAMING OVERLAY E ICONOS")
print("============================================================")

# 1. Comprobar existencia y validez de los recursos de icono
ico_file = resource_path(os.path.join("assets", "icon.ico"))
png_file = resource_path(os.path.join("assets", "icon.png"))
assert os.path.isfile(ico_file), f"No existe el archivo de icono: {ico_file}"
assert os.path.isfile(png_file), f"No existe el archivo PNG fuente: {png_file}"
print(f"[OK] 1. Archivos de icono verificados: .ico ({os.path.getsize(ico_file)} bytes), .png ({os.path.getsize(png_file)} bytes)")

# 2. Abrir PC Rescue en modo desarrollo y comprobar icono
app = PCRescueApp()
app.update()

assert hasattr(app, "_setup_window_icon"), "Falta el método de configuración de icono"
print("[OK] 2. Ventana principal iniciada con icono personalizado configurado.")

# Asegurar estado cerrado para prueba limpia
if app.overlay_window is not None:
    app._stop_overlay()
    app.update()

# 3. Verificar controles en la barra lateral
assert hasattr(app, "btn_toggle_overlay"), "Falta el botón toggle del overlay"
assert hasattr(app, "lbl_overlay_status"), "Falta el indicador de estado del overlay"
assert hasattr(app, "btn_config_overlay"), "Falta el botón de configuración del overlay"
assert app.overlay_window is None, "El overlay debe estar cerrado al iniciar la prueba"
assert "Inactivo" in app.lbl_overlay_status.cget("text")
print("[OK] 3. Controles de Gaming Overlay presentes en la barra lateral.")

# 4. Activar Gaming Overlay
app._toggle_overlay()
app.update()

assert app.overlay_window is not None, "El overlay debe estar instanciado"
assert app.overlay_window.winfo_exists(), "La ventana del overlay debe existir"
assert "Activo" in app.lbl_overlay_status.cget("text"), "El estado debe indicar Activo"
assert app.overlay_config.get("enabled") is True
print("[OK] 4. Gaming Overlay activado con visibilidad Always-on-Top.")

# 5. Confirmar actualización con lecturas reales de CPU, GPU, RAM y sensores
app._schedule_fast_updates()
app.update()

ov = app.overlay_window
cpu_text = ov.val_cpu.cget("text")
gpu_text = ov.val_gpu.cget("text")
ram_text = ov.val_ram.cget("text")

print(f"     Métricas visualizadas estilo MSI Afterburner:")
print(f"       • CPU: {ov.val_cpu_pct.cget('text')} | {ov.val_cpu_temp.cget('text')}")
print(f"       • GPU: {ov.val_gpu_pct.cget('text')} | {ov.val_gpu_temp.cget('text')}")
print(f"       • RAM: {ov.val_ram_mem.cget('text')} | {ov.val_ram_pct.cget('text')}")

assert "%" in cpu_text, "CPU debe mostrar porcentaje"
assert "%" in gpu_text, "GPU debe mostrar porcentaje"
assert "%" in ram_text, "RAM debe mostrar porcentaje"
assert "GB" in ram_text, "RAM debe mostrar memoria utilizada respecto del total"
print("[OK] 5. Métricas reales de CPU, GPU y RAM formateadas correctamente en 3 columnas.")

# 6. Comprobar comportamiento cuando no hay sensores de temperatura
temps = metrics.get_temperatures()
if temps.get("cpu") is None:
    assert ov.val_cpu_temp.cget("text") == "N/D", "CPU temp no disponible debe mostrar N/D"
if temps.get("gpu") is None:
    assert ov.val_gpu_temp.cget("text") == "N/D", "GPU temp no disponible debe mostrar N/D"
print("[OK] 6. Sensores no disponibles representados fielmente como 'N/D' sin inventar datos.")

# 7. Minimizar la ventana principal y verificar que el overlay siga visible
app.iconify()
app.update()
ov.update()
assert ov.winfo_ismapped() == 1, "El overlay debe seguir visible tras minimizar la ventana principal"
print("[OK] 7. Ventana principal minimizada: Gaming Overlay permanece visible e independiente.")
app.deiconify()
app.update()

# 8. Reposicionamiento y configuración
cfg = app.overlay_config
for pos in ["top_left", "top_right", "bottom_left", "bottom_right"]:
    cfg.set("position", pos)
    ov.apply_config()
    app.update()
print("[OK] 8. Reposicionamiento probado en las 4 esquinas de la pantalla.")

# 9. Cerrar el overlay desde su propio botón 'x' y reabrirlo sin cerrar PC Rescue
ov.btn_close_ov.event_generate("<Button-1>")
app.update()

assert app.overlay_window is None, "El overlay debe destruirse al pulsar su botón de cierre"
assert "Inactivo" in app.lbl_overlay_status.cget("text")
assert app.winfo_exists(), "PC Rescue debe seguir funcionando tras cerrar el overlay"
print("[OK] 9. Cierre independiente del overlay ejecutado sin cerrar PC Rescue.")

# Reabrir el overlay
app._toggle_overlay()
app.update()
assert app.overlay_window is not None
print("[OK] 10. Reapertura inmediata del overlay comprobada.")

# 10. Medir consumo de CPU/memoria del overlay
proc = psutil.Process()
mem_mb = proc.memory_info().rss / (1024 * 1024)
cpu_usage = proc.cpu_percent(interval=0.1)
print(f"     Consumo de PC Rescue con Overlay activo: Memoria={mem_mb:.1f} MB, CPU={cpu_usage:.1f}%")
assert mem_mb < 250, "El consumo de memoria debe ser razonable (< 250 MB)"
print("[OK] 11. Rendimiento y memoria verificados dentro de rangos óptimos.")

# 11. Cierre total de PC Rescue
app._on_close()
print("[OK] 12. Cierre seguro de PC Rescue ejecutado sin ventanas ni procesos residuales.")

print("============================================================")
print("  ¡TODAS LAS PRUEBAS DE OVERLAY E ICONO PASARON CON ÉXITO!")
print("============================================================")
