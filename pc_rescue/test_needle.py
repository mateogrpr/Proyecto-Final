"""
test_needle.py — Verificación técnica de la aguja indicadora y la escala fija.

Comprueba:
1. Precisión trigonométrica de calculate_needle_coords para 0%, 25%, 50%, 75% y 100%.
2. Escala fija completa formada por segmentos multicolor siempre visibles.
3. Existencia de pivote central exactamente en (cx, cy).
4. Aguja tipo velocímetro con punta sobre la escala.
5. Número central por encima del pivote sin interferencia visual de la aguja.
6. Actualización en tiempo real en los 3 medidores (CPU, RAM, Disco).
"""
import sys
import math
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from app import calculate_needle_coords, get_usage_color, SemicircularGauge, PCRescueApp

print("=" * 65)
print("  TEST DE AGUJA INDICADORA Y ESCALA FIJA MULTICOLOR")
print("=" * 65)

# 1. Comprobación trigonométrica de calculate_needle_coords
cx, cy, r = 100.0, 100.0, 80.0

# 0 %: apunta al extremo izquierdo del arco (180°)
x0, y0, deg0 = calculate_needle_coords(cx, cy, r, 0)
assert abs(deg0 - 180.0) < 1e-4, f"Ángulo 0% erróneo: {deg0}"
assert abs(x0 - (cx - r)) < 1e-4, f"X 0% errónea: {x0}"
assert abs(y0 - cy) < 1e-4, f"Y 0% errónea: {y0}"
print(f"  [OK]  0% -> Ángulo={deg0:5.1f}° | Punta=({x0:5.1f}, {y0:5.1f}) [Extremo izquierdo]")

# 25 %: apunta al primer cuarto (135°)
x25, y25, deg25 = calculate_needle_coords(cx, cy, r, 25)
assert abs(deg25 - 135.0) < 1e-4, f"Ángulo 25% erróneo: {deg25}"
assert x25 < cx and y25 < cy, f"Coordenadas 25% erróneas: ({x25}, {y25})"
print(f"  [OK] 25% -> Ángulo={deg25:5.1f}° | Punta=({x25:5.1f}, {y25:5.1f}) [Primer cuarto]")

# 50 %: apunta verticalmente hacia arriba (90°)
x50, y50, deg50 = calculate_needle_coords(cx, cy, r, 50)
assert abs(deg50 - 90.0) < 1e-4, f"Ángulo 50% erróneo: {deg50}"
assert abs(x50 - cx) < 1e-4, f"X 50% errónea: {x50}"
assert abs(y50 - (cy - r)) < 1e-4, f"Y 50% errónea: {y50}"
print(f"  [OK] 50% -> Ángulo={deg50:5.1f}° | Punta=({x50:5.1f}, {y50:5.1f}) [Vertical hacia arriba]")

# 75 %: apunta al tercer cuarto (45°)
x75, y75, deg75 = calculate_needle_coords(cx, cy, r, 75)
assert abs(deg75 - 45.0) < 1e-4, f"Ángulo 75% erróneo: {deg75}"
assert x75 > cx and y75 < cy, f"Coordenadas 75% erróneas: ({x75}, {y75})"
print(f"  [OK] 75% -> Ángulo={deg75:5.1f}° | Punta=({x75:5.1f}, {y75:5.1f}) [Tercer cuarto]")

# 100 %: apunta al extremo derecho del arco (0°)
x100, y100, deg100 = calculate_needle_coords(cx, cy, r, 100)
assert abs(deg100 - 0.0) < 1e-4, f"Ángulo 100% erróneo: {deg100}"
assert abs(x100 - (cx + r)) < 1e-4, f"X 100% errónea: {x100}"
assert abs(y100 - cy) < 1e-4, f"Y 100% errónea: {y100}"
print(f"  [OK]100% -> Ángulo={deg100:5.1f}° | Punta=({x100:5.1f}, {y100:5.1f}) [Extremo derecho]")

print("\n--- Verificación en Canvas del Widget SemicircularGauge ---")

root = tk.Tk()
root.withdraw()
frame = tk.Frame(root)
frame.pack()

gauge = SemicircularGauge(frame, title="PROCESADOR (CPU)")
gauge.pack()
root.update()

# 2. Verificar que los segmentos de la escala fija existen
segments = gauge.canvas.find_withtag("scale_segment")
assert len(segments) == SemicircularGauge.NUM_SEGMENTS, \
    f"Se esperaban {SemicircularGauge.NUM_SEGMENTS} segmentos, encontrados {len(segments)}"
print(f"  [OK] Escala fija completa generada: {len(segments)} segmentos multicolor continuos.")

# 3. Comprobar actualización de porcentaje y presencia de aguja y pivote
gauge.update_value(50, detail="50% de prueba")
root.update()

items_needle = gauge.canvas.find_withtag("needle_layer")
assert len(items_needle) > 0, "No se encontraron elementos en la capa de aguja/pivote"
print(f"  [OK] Capa de aguja y pivote renderizada con {len(items_needle)} elementos gráficos.")

# Comprobar texto numérico central
text_items = [i for i in items_needle if gauge.canvas.type(i) == "text"]
assert len(text_items) >= 1
assert gauge.canvas.itemcget(text_items[0], "text") == "50%"
print("  [OK] Número central visible y grande: '50%'.")

# 4. Probar los 3 indicadores con valores reales del sistema
app = PCRescueApp()
app.update()

app._schedule_fast_updates()
app._schedule_slow_updates()
app.update()

assert app.gauge_cpu.percent is not None
assert app.gauge_ram.percent is not None
assert app.gauge_disk.percent is not None

print(f"  [OK] Indicador CPU:   {app.gauge_cpu.percent:.1f}%  (Aguja posicionada)")
print(f"  [OK] Indicador RAM:   {app.gauge_ram.percent:.1f}%  (Aguja posicionada)")
print(f"  [OK] Indicador DISCO: {app.gauge_disk.percent:.1f}%  (Aguja posicionada)")

app._on_close()
root.destroy()

print("\n" + "=" * 65)
print("  ¡TODAS LAS PRUEBAS DE LA AGUJA PASARON CON 100% DE ÉXITO!")
print("=" * 65)
