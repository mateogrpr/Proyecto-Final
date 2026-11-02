"""
Test final completo — PC Rescue 2.0.
Verifica:
  1. La app abre sin errores y tiene el titulo correcto
  2. Inicializacion correcta de medidores
  3. Actualizacion continua con datos reales
  4. El diagnostico se genera correctamente
  5. Las recomendaciones aparecen cuando hay alertas
  6. La exportacion genera un informe valido
  7. El manejo de errores y ciclos sucesivos funciona
"""
import os
import tempfile
from app import PCRescueApp
from report import generate_report

print("=" * 50)
print("  TEST FINAL - PC Rescue 2.0")
print("=" * 50)

# --- Test 1: La app abre sin errores ---
app = PCRescueApp()
app.update()
assert "PC Rescue" in app.title()
print("[OK] 1. La app abre sin errores con titulo profesional")

# --- Test 2: Medidores inicializados ---
assert app.gauge_cpu is not None
assert app.gauge_ram is not None
assert app.gauge_disk is not None
print("[OK] 2. Medidores semicirculares inicializados")

# --- Test 3: Actualizaciones muestran datos reales ---
app._schedule_fast_updates()
app._schedule_slow_updates()
app.update()

cpu_val = app.last_cpu
ram_val = app.last_ram["percent"] if app.last_ram else None
disk_val = app.last_disk["percent"] if app.last_disk else None

assert cpu_val is not None
assert ram_val is not None
assert disk_val is not None
print(f"[OK] 3. Datos reales: CPU={cpu_val}%, RAM={ram_val}%, Disco={disk_val}%")

# --- Test 4: Diagnostico se genero ---
assert app.last_diagnostics is not None
assert len(app.last_diagnostics) == 3
diag_content = app.txt_diagnosis.get("1.0", "end").strip()
assert len(diag_content) > 0
print("[OK] 4. Diagnostico generado con 3 metricas")

# --- Test 5: Si hay alertas, hay recomendaciones ---
has_alerts = any(
    d["level"] in ("warning", "critical") for d in app.last_diagnostics
)
if has_alerts:
    assert len(app.last_recommendations) > 0
    print("[OK] 5. Alertas detectadas -> recomendaciones generadas")
else:
    assert len(app.last_recommendations) == 0
    print("[OK] 5. Sin alertas -> sin recomendaciones (sistema normal)")

# --- Test 6: Exportacion genera informe valido ---
report_text = generate_report(
    cpu=app.last_cpu,
    ram=app.last_ram,
    disk=app.last_disk,
    diagnostics=app.last_diagnostics,
    recommendations=app.last_recommendations,
)
assert "PC RESCUE" in report_text
assert "Fecha:" in report_text
assert "VALORES MEDIDOS" in report_text
assert "DETALLE DEL DIAGNOSTICO" in report_text
assert "RECOMENDACIONES" in report_text

# Probar que se puede guardar como archivo
temp_path = os.path.join(tempfile.gettempdir(), "test_pc_rescue_report.txt")
with open(temp_path, "w", encoding="utf-8") as f:
    f.write(report_text)

# Verificar que el archivo existe y tiene contenido
assert os.path.exists(temp_path)
with open(temp_path, "r", encoding="utf-8") as f:
    saved_content = f.read()
assert len(saved_content) > 100, "El informe es demasiado corto"
assert saved_content == report_text, "El contenido guardado no coincide"

# Limpiar
os.remove(temp_path)
print(f"[OK] 6. Informe exportado y verificado ({len(report_text)} caracteres)")

# --- Test 7: Multiples ciclos sin errores ---
for i in range(3):
    app._schedule_fast_updates()
    app.update()
print("[OK] 7. 3 ciclos consecutivos sin errores")

# --- Test 8: Nota aclaratoria presente ---
assert "valor elevado" in diag_content.lower() or "no indica" in diag_content.lower()
print("[OK] 8. Nota aclaratoria incluida en el diagnostico")

print("")
print("=" * 50)
print("  TODOS LOS TESTS PASARON")
print("=" * 50)

app._on_close()
