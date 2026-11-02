"""Test visual + funcional de la interfaz PC Rescue 2.0."""
import os, tempfile
from app import PCRescueApp
from report import generate_report

print("=" * 50)
print("  TEST DE INTERFAZ MEJORADA")
print("=" * 50)

# 1. Abrir sin errores
app = PCRescueApp()
app.update()
assert "PC Rescue" in app.title()
print("[OK] 1. La app abre sin errores")

# 2. Medidores inicializados
assert app.gauge_cpu is not None
assert app.gauge_ram is not None
assert app.gauge_disk is not None
print("[OK] 2. Los 3 medidores inicializados")

# 3. Analizar con datos reales
app._schedule_fast_updates()
app._schedule_slow_updates()
app.update()

assert app.last_cpu is not None
assert app.last_ram is not None
assert app.last_disk is not None
print(f"[OK] 3. Datos reales: CPU={app.last_cpu}%, RAM={app.last_ram['percent']}%, Disco={app.last_disk['percent']}%")

# 4. Diagnostico generado
assert app.last_diagnostics is not None
assert len(app.last_diagnostics) == 3
diag_text = app.txt_diagnosis.get("1.0", "end").strip()
assert len(diag_text) > 0
print("[OK] 4. Diagnostico generado (3 metricas)")

# 5. Alertas y recomendaciones
has_alerts = any(d["level"] in ("warning","critical") for d in app.last_diagnostics)
if has_alerts:
    assert len(app.last_recommendations) > 0
    print(f"[OK] 5. Alertas detectadas, {len(app.last_recommendations)} recomendacion(es)")
else:
    print("[OK] 5. Sin alertas (sistema normal)")

# 6. Medidores tienen porcentaje aplicado
assert app.gauge_cpu.percent is not None
assert app.gauge_ram.percent is not None
assert app.gauge_disk.percent is not None
print("[OK] 6. Los 3 medidores semicirculares tienen valores reales aplicados")

# 7. Exportacion funciona
report_text = generate_report(
    cpu=app.last_cpu, ram=app.last_ram, disk=app.last_disk,
    diagnostics=app.last_diagnostics,
    recommendations=app.last_recommendations,
)
tmp = os.path.join(tempfile.gettempdir(), "test_rescue_visual.txt")
with open(tmp, "w", encoding="utf-8") as f:
    f.write(report_text)
assert os.path.exists(tmp)
with open(tmp, "r", encoding="utf-8") as f:
    assert "PC RESCUE" in f.read()
os.remove(tmp)
print(f"[OK] 7. Informe exportado y verificado ({len(report_text)} chars)")

# 8. Multiples ciclos de actualizacion
for _ in range(3):
    app._schedule_fast_updates()
    app.update()
print("[OK] 8. 3 ciclos consecutivos sin errores")

# 9. Botones de navegacion y terminales presentes
assert "inicio" in app.nav_buttons
assert "wifi" in app.nav_buttons
assert "componentes" in app.nav_buttons
assert app.btn_cmd is not None
assert app.btn_powershell is not None
print("[OK] 9. Navegacion lateral y accesos a terminales presentes")

# 10. Resize no genera errores
app.geometry("1100x750")
app.update()
app.geometry("960x640")
app.update()
print("[OK] 10. Redimensionar ventana sin errores")

print("")
print("=" * 50)
print("  TODOS LOS TESTS PASARON")
print("=" * 50)
app._on_close()
