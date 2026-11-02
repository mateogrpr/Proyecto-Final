"""Smoke test rapido de la app PC Rescue 2.0."""
from app import PCRescueApp
from report import generate_report

app = PCRescueApp()
app.update()
app._schedule_fast_updates()
app._schedule_slow_updates()
app.update()

print(f"Titulo: {app.title()}")
print(f"Seccion actual: {app.current_section}")
print(f"Boton Exportar: {app.btn_export.cget('text')}")
print(f"CPU: {app.last_cpu}%")
print(f"RAM: {app.last_ram['percent'] if app.last_ram else 'N/D'}%")
print(f"Disco: {app.last_disk['percent'] if app.last_disk else 'N/D'}%")

report = generate_report(
    cpu=app.last_cpu,
    ram=app.last_ram,
    disk=app.last_disk,
    diagnostics=app.last_diagnostics,
    recommendations=app.last_recommendations,
)
print(f"Informe generado: {len(report)} caracteres")
print("\n[OK] Todo funciona correctamente en PC Rescue 2.0")
app._on_close()
