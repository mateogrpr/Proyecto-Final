"""Test de report.py"""

from report import generate_report

# Simular datos reales (como los de tu sistema)
cpu = 8.7
ram = {"percent": 58.8, "total_gb": 15.8, "used_gb": 9.3, "available_gb": 6.5}
disk = {"percent": 87.4, "total_gb": 465.1, "used_gb": 406.3, "free_gb": 58.8}

diagnostics = [
    {"metric": "CPU", "level": "normal",
     "message": "El uso de CPU esta en un nivel normal (8.7%)."},
    {"metric": "RAM", "level": "normal",
     "message": "El uso de RAM esta en un nivel normal (58.8%)."},
    {"metric": "Disco", "level": "warning",
     "message": "El espacio en disco esta por encima del 85% de uso (87.4%)."},
]

recommendations = [
    {"metric": "Disco", "level": "warning", "steps": [
        "Revisa la Papelera de reciclaje.",
        "Usa Limpieza de disco desde el menu Inicio.",
        "Revisa la carpeta de Descargas.",
    ]},
]

texto = generate_report(cpu, ram, disk, diagnostics, recommendations)
print(texto)

# Verificaciones
assert "PC RESCUE" in texto
assert "Fecha:" in texto
assert "Hora:" in texto
assert "8.7%" in texto
assert "58.8%" in texto
assert "87.4%" in texto
assert "ADVERTENCIA" in texto
assert "Papelera" in texto
assert "tecnico especializado" in texto

# Test con todo None
texto_vacio = generate_report(None, None, None, [], [])
assert "No se pudo leer" in texto_vacio
assert "No se detectaron" in texto_vacio

print("\n[OK] Todas las verificaciones de report.py pasaron")
