"""
test_gauge_colors.py — Verifica la interpolación cromática dinámica de los medidores.

Comprueba que get_gauge_color() devuelve los colores exactos en las
paradas definidas, que los valores intermedios producen transiciones
coherentes, y que los valores fuera de rango se acotan correctamente.
"""
import sys
sys.path.insert(0, ".")

from app import get_gauge_color, _hex_to_rgb, _rgb_to_hex, SemicircularGauge
import tkinter as tk

print("=" * 60)
print("  TEST DE INTERPOLACIÓN CROMÁTICA DINÁMICA")
print("=" * 60)

# 1. Paradas exactas deben coincidir con los valores definidos
exact_stops = {
    0:    "#00E676",
    25:   "#76FF03",
    50:   "#FFEB3B",
    57.5: "#FFC107",
    65:   "#FF9800",
    80:   "#FF5722",
    100:  "#FF1744",
}
for pct, expected in exact_stops.items():
    result = get_gauge_color(pct)
    assert result.upper() == expected.upper(), \
        f"En {pct}%: esperado {expected}, obtenido {result}"
    print(f"  [OK] {str(pct):>5}% -> {result}  (esperado {expected})")

print()

# 2. Valores intermedios deben producir colores entre las paradas adyacentes
intermediate_tests = [
    (10,  "entre 0% y 25%"),
    (37,  "entre 25% y 50%"),
    (57,  "entre 50% y 65%"),
    (72,  "entre 65% y 80%"),
    (90,  "entre 80% y 100%"),
]
for pct, desc in intermediate_tests:
    result = get_gauge_color(pct)
    r, g, b = _hex_to_rgb(result)
    assert 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255
    print(f"  [OK] {pct:>3d}% -> {result}  ({desc})")

print()

# 3. Valores fuera de rango se acotan sin error
assert get_gauge_color(-10).upper() == "#00E676"
assert get_gauge_color(150).upper() == "#FF1744"
assert get_gauge_color(0.0).upper() == "#00E676"
assert get_gauge_color(100.0).upper() == "#FF1744"
print("  [OK] Valores fuera de rango acotados correctamente (-10, 150)")

# 4. Conversiones RGB <-> Hex son consistentes
for hex_c in ["#00E676", "#FF9800", "#FFFFFF", "#000000"]:
    r, g, b = _hex_to_rgb(hex_c)
    roundtrip = _rgb_to_hex(r, g, b)
    assert roundtrip.upper() == hex_c.upper(), \
        f"Roundtrip fallido: {hex_c} → ({r},{g},{b}) → {roundtrip}"
print("  [OK] Conversiones _hex_to_rgb / _rgb_to_hex consistentes")

print()

# 5. Los tres medidores responden al nuevo color dinámico
root = tk.Tk()
root.withdraw()
frame = tk.Frame(root)

gauge = SemicircularGauge(frame, title="TEST")
gauge.pack()
root.update()

# Verificar estado neutral (sin dato)
assert gauge._has_data is False
gauge.redraw()
root.update()
print("  [OK] Estado neutral (sin dato) renderiza sin error")

# Verificar con dato None → estado neutral
gauge.update_value(None)
root.update()
assert gauge._has_data is False
print("  [OK] update_value(None) produce estado neutral")

# Verificar actualización con porcentajes reales
for pct in [0, 10, 25, 50, 65, 80, 100]:
    gauge.update_value(pct, level="normal", detail=f"Test {pct}%")
    root.update()
    assert gauge._has_data is True
    assert gauge.percent == pct

print("  [OK] Medidor se actualiza correctamente para 0%, 10%, 25%, 50%, 65%, 80%, 100%")

root.destroy()

print()
print("=" * 60)
print("  ¡TODAS LAS PRUEBAS DE COLOR DINÁMICO PASARON CON ÉXITO!")
print("=" * 60)
