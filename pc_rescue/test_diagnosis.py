"""Test rápido de diagnosis.py — ejecutar con: python test_diagnosis.py"""

from diagnosis import evaluate_cpu, evaluate_ram, evaluate_disk, run_all_diagnostics

print("=== CPU ===")
for val in [15, 82, 97, None]:
    r = evaluate_cpu(val)
    print(f"  {val}% -> [{r['level']}] {r['message'][:70]}...")

print("\n=== RAM ===")
for val in [45, 85, 96, None]:
    r = evaluate_ram(val)
    print(f"  {val}% -> [{r['level']}] {r['message'][:70]}...")

print("\n=== Disco ===")
for val in [50, 87, 98, None]:
    r = evaluate_disk(val)
    print(f"  {val}% -> [{r['level']}] {r['message'][:70]}...")

print("\n=== run_all_diagnostics (simulando tu sistema: CPU=15, RAM=58, Disco=87) ===")
results = run_all_diagnostics(15, 58, 87)
for r in results:
    print(f"  {r['metric']}: [{r['level']}] {r['message'][:70]}...")

# Verificaciones automáticas
assert evaluate_cpu(15)["level"] == "normal"
assert evaluate_cpu(82)["level"] == "warning"
assert evaluate_cpu(97)["level"] == "critical"
assert evaluate_cpu(None)["level"] == "error"

assert evaluate_ram(45)["level"] == "normal"
assert evaluate_ram(85)["level"] == "warning"
assert evaluate_ram(96)["level"] == "critical"

assert evaluate_disk(50)["level"] == "normal"
assert evaluate_disk(87)["level"] == "warning"
assert evaluate_disk(98)["level"] == "critical"

assert len(run_all_diagnostics(10, 20, 30)) == 3

print("\n[OK] Todas las verificaciones pasaron")
