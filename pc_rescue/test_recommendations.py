"""Test de recommendations.py"""

from recommendations import get_recommendations, format_recommendations_text

# Caso 1: todo normal -> no deberia haber recomendaciones
diags_ok = [
    {"metric": "CPU", "level": "normal", "message": "..."},
    {"metric": "RAM", "level": "normal", "message": "..."},
    {"metric": "Disco", "level": "normal", "message": "..."},
]
recs = get_recommendations(diags_ok)
assert len(recs) == 0, "No deberia haber recomendaciones si todo esta normal"
print("[OK] Todo normal -> 0 recomendaciones")

# Caso 2: disco warning (tu caso real)
diags_disk = [
    {"metric": "CPU", "level": "normal", "message": "..."},
    {"metric": "RAM", "level": "normal", "message": "..."},
    {"metric": "Disco", "level": "warning", "message": "..."},
]
recs = get_recommendations(diags_disk)
assert len(recs) == 1, "Deberia haber 1 recomendacion (disco)"
assert recs[0]["metric"] == "Disco"
assert len(recs[0]["steps"]) > 0, "Debe tener al menos un paso"
print("[OK] Disco warning -> 1 recomendacion con pasos")

# Caso 3: todo critical
diags_crit = [
    {"metric": "CPU", "level": "critical", "message": "..."},
    {"metric": "RAM", "level": "critical", "message": "..."},
    {"metric": "Disco", "level": "critical", "message": "..."},
]
recs = get_recommendations(diags_crit)
assert len(recs) == 3, "Deberia haber 3 recomendaciones"
print("[OK] Todo critical -> 3 recomendaciones")

# Caso 4: formato de texto
text = format_recommendations_text(recs)
assert "Recomendaciones" in text
assert "CPU" in text
assert "1." in text
print("[OK] Formato de texto contiene encabezado, metrica y pasos numerados")

# Mostrar ejemplo de formato
print("\n--- Ejemplo de texto formateado (Disco warning) ---")
recs_disk = get_recommendations(diags_disk)
print(format_recommendations_text(recs_disk))

print("[OK] Todas las verificaciones pasaron")
