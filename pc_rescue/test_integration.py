"""Test de integracion: app.py + metrics.py + diagnosis.py + recommendations.py"""

from app import PCRescueApp

app = PCRescueApp()
app.update()

# Ejecutar actualizacion de metricas en tiempo real
app._schedule_fast_updates()
app._schedule_slow_updates()
app.update()

# Verificar que los datos se actualizaron
cpu_val = app.last_cpu
ram_val = app.last_ram["percent"] if app.last_ram else None
disk_val = app.last_disk["percent"] if app.last_disk else None

print(f"CPU: {cpu_val}%")
print(f"RAM: {ram_val}%")
print(f"Disco: {disk_val}%")

# Verificar que el diagnostico se genero
diag_content = app.txt_diagnosis.get("1.0", "end").strip()
print(f"\n--- Diagnostico mostrado ---")
safe_content = diag_content.encode("ascii", errors="replace").decode("ascii")
print(safe_content)

# Verificaciones
assert cpu_val is not None
assert ram_val is not None
assert disk_val is not None
assert app.last_diagnostics is not None, "No se guardaron los diagnosticos"
assert len(app.last_diagnostics) == 3, "Deberian haber 3 diagnosticos"

print("\n[OK] Todas las verificaciones de integracion pasaron")
app._on_close()
