"""Test de manejo de errores"""
from diagnosis import run_all_diagnostics
from recommendations import get_recommendations

# Simular que todas las metricas fallan (None)
diagnostics = run_all_diagnostics(None, None, None)

for d in diagnostics:
    assert d["level"] == "error", f"Deberia ser error, es {d['level']}"
    print(f"  {d['metric']}: [{d['level']}] {d['message']}")

# Las recomendaciones no deberian generarse para errores
recs = get_recommendations(diagnostics)
assert len(recs) == 0, "No deberia haber recomendaciones para errores"
print("\n[OK] Metricas None manejadas correctamente")

# Simular mezcla: CPU falla, RAM normal, Disco critical
diagnostics = run_all_diagnostics(None, 45, 98)
assert diagnostics[0]["level"] == "error"    # CPU
assert diagnostics[1]["level"] == "normal"   # RAM
assert diagnostics[2]["level"] == "critical" # Disco
print("[OK] Mezcla de estados manejada correctamente")

recs = get_recommendations(diagnostics)
assert len(recs) == 1  # Solo disco critical
assert recs[0]["metric"] == "Disco"
print("[OK] Recomendaciones solo para metricas con problemas reales")

print("\n[OK] Todas las pruebas de error pasaron")
