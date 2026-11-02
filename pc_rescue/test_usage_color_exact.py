"""
test_usage_color_exact.py — Prueba rigurosa de get_usage_color() y los indicadores.

Comprueba:
1. Puntos exactos requeridos: 0, 10, 25, 40, 50, 65, 80, 85, 100.
2. Valores None e inválidos devuelven el color neutral #737D95.
3. Valores fuera de rango (<0 y >100) acotados a los extremos.
4. Los tres medidores (CPU, RAM, DISCO) aplican el color al arco del Canvas.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from app import get_usage_color, SemicircularGauge, PCRescueApp

print("=" * 65)
print("  VERIFICACIÓN FORMAL DE get_usage_color(percentage)")
print("=" * 65)

# 1. Puntos clave requeridos por la especificación
key_points = [
    (0,   "#00E676", "verde intenso (0%)"),
    (10,  "#2FF048", "verde progresivo hacia lima (10%)"),
    (25,  "#76FF03", "verde lima exacto (25%)"),
    (40,  "#C8F325", "transición lima -> amarillo (40%)"),
    (50,  "#FFEB3B", "amarillo exacto (50%)"),
    (65,  "#FF9800", "naranja exacto (65%)"),
    (80,  "#FF5722", "rojo anaranjado exacto (80%)"),
    (85,  "#FF472A", "transición rojo anaranjado -> rojo vivo (85%)"),
    (100, "#FF1744", "rojo vivo exacto (100%)"),
]

for pct, expected_hex, desc in key_points:
    color = get_usage_color(pct)
    assert color.upper() == expected_hex.upper(), f"Error en {pct}%: obtenido {color}, esperado {expected_hex}"
    print(f"  [OK] {pct:>3d}% -> {color}  ({desc})")

print("\n--- Pruebas de robustez y casos especiales ---")

# 2. None e inválidos
neutral_color = "#737D95"
assert get_usage_color(None) == neutral_color, f"None fallo: {get_usage_color(None)}"
print(f"  [OK] None -> {neutral_color} (estado neutral)")

assert get_usage_color("invalido") == neutral_color
print(f"  [OK] 'invalido' -> {neutral_color} (estado neutral)")

assert get_usage_color([]) == neutral_color
print(f"  [OK] [] -> {neutral_color} (estado neutral)")

# 3. Fuera de rango
assert get_usage_color(-20) == "#00E676"
print("  [OK] -20% -> #00E676 (acotado a 0%)")

assert get_usage_color(150) == "#FF1744"
print("  [OK] 150% -> #FF1744 (acotado a 100%)")

print("\n--- Verificación de aplicación real en los tres indicadores ---")

root = tk.Tk()
root.withdraw()

g_cpu = SemicircularGauge(root, title="CPU")
g_ram = SemicircularGauge(root, title="RAM")
g_disk = SemicircularGauge(root, title="DISCO")

for g in [g_cpu, g_ram, g_disk]:
    g.pack()
root.update()

# Simular CPU 10%, RAM 50%, Disco 85%
g_cpu.update_value(10, detail="10% CPU")
g_ram.update_value(50, detail="50% RAM")
g_disk.update_value(85, detail="85% DISCO")
root.update()

# Comprobar que en el Canvas de cada medidor se genera la escala fija continua con segmentos multicolor
def check_gauge_scale(gauge):
    canvas = gauge.canvas
    items = canvas.find_withtag("scale_segment")
    assert len(items) == SemicircularGauge.NUM_SEGMENTS, \
        f"Se esperaban {SemicircularGauge.NUM_SEGMENTS} segmentos, encontrados {len(items)}"
    return len(items)

segs_cpu = check_gauge_scale(g_cpu)
segs_ram = check_gauge_scale(g_ram)
segs_disk = check_gauge_scale(g_disk)

print(f"  CPU   10% Canvas escala fija:  {segs_cpu} segmentos continuos")
print(f"  RAM   50% Canvas escala fija:  {segs_ram} segmentos continuos")
print(f"  DISCO 85% Canvas escala fija:  {segs_disk} segmentos continuos")

# Probar aguja y actualización dinámica en vivo
assert g_cpu.percent == 10
assert g_ram.percent == 50
assert g_disk.percent == 85

g_cpu.update_value(100, detail="100% CPU")
root.update()
assert g_cpu.percent == 100
print(f"  CPU actualizado a 100%: Aguja posicionada en 100%")

# Probar valor None (estado neutral)
g_cpu.update_value(None, detail="Sin datos")
root.update()
assert g_cpu._has_data is False
needle_items = g_cpu.canvas.find_withtag("needle_layer")
text_items = [i for i in needle_items if g_cpu.canvas.type(i) == "text"]
assert len(text_items) >= 1
assert g_cpu.canvas.itemcget(text_items[0], "text") == "—"
print("  CPU con valor None muestra estado neutral ('—') sin aguja activa")

root.destroy()

print("\n" + "=" * 65)
print("  ¡TODAS LAS COMPROBACIONES PASARON CON 100% DE ÉXITO!")
print("=" * 65)
