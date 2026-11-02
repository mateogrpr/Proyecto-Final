"""
report.py — Generacion del informe en formato de texto.

Este modulo recibe las metricas, diagnosticos y recomendaciones del
ultimo analisis, y genera un informe completo en texto plano que se
puede guardar como archivo .txt.

El informe incluye:
    - Fecha y hora del analisis.
    - Estado general del sistema.
    - Valores medidos (CPU, RAM, disco).
    - Diagnostico para cada metrica.
    - Recomendaciones (si las hay).
    - Ultima prueba de conexion/Internet (si existe).

No depende de tkinter — es logica pura de formateo de texto.
"""

from datetime import datetime


def generate_report(cpu, ram, disk, diagnostics, recommendations, network_test=None, overall_status=None):
    """Genera el texto completo del informe.

    Args:
        cpu: Porcentaje de CPU (float) o None si no se pudo leer.
        ram: Dict con percent, total_gb, used_gb, available_gb (o None).
        disk: Dict con percent, total_gb, used_gb, free_gb (o None).
        diagnostics: Lista de dicts del diagnostico (de diagnosis.py).
        recommendations: Lista de dicts de recomendaciones (de recommendations.py).
        network_test: Dict opcional con la ultima medicion de Internet valida.
        overall_status: Dict opcional con status_text, level y summary.

    Returns:
        str: Texto completo del informe, listo para guardar en un .txt.
    """
    lines = []

    # ── Encabezado ──
    lines.append("=" * 64)
    lines.append("              PC RESCUE - INFORME DEL SISTEMA")
    lines.append("=" * 64)
    lines.append("")

    # Fecha y hora del informe
    now = datetime.now()
    lines.append(f"  Fecha: {now.strftime('%d/%m/%Y')} (Fecha de generacion)")
    lines.append(f"  Hora:  {now.strftime('%H:%M:%S')} (Hora de generacion)")
    lines.append("")

    # ── Estado General del Sistema ──
    lines.append("-" * 64)
    lines.append("  ESTADO GENERAL DEL SISTEMA")
    lines.append("-" * 64)
    lines.append("")

    if overall_status and isinstance(overall_status, dict):
        status_text = overall_status.get("status_text", "No determinado")
        summary = overall_status.get("summary", "")
        lines.append(f"  Diagnostico global: [{status_text.upper()}]")
        if summary:
            lines.append(f"  Detalle:            {summary}")
    else:
        # Calcular a partir de diagnostics si no se pasa explícito
        has_critical = any(d.get("level") == "critical" for d in (diagnostics or []))
        has_warning = any(d.get("level") == "warning" for d in (diagnostics or []))
        if has_critical:
            lines.append("  Diagnostico global: [PROBLEMA DETECTADO]")
            lines.append("  Detalle: Se han detectado metricas en nivel critico.")
        elif has_warning:
            lines.append("  Diagnostico global: [ATENCION RECOMENDADA]")
            lines.append("  Detalle: Uno o mas recursos presentan uso por encima de lo habitual.")
        else:
            lines.append("  Diagnostico global: [TODO CORRECTO]")
            lines.append("  Detalle: Todos los parametros monitoreados estan estables.")

    lines.append("")

    # ── Metricas medidas ──
    lines.append("-" * 64)
    lines.append("  VALORES MEDIDOS EN TIEMPO REAL")
    lines.append("-" * 64)
    lines.append("")

    # CPU
    if cpu is not None:
        lines.append(f"  Procesador (CPU):   {cpu}% de uso")
    else:
        lines.append("  Procesador (CPU):   No se pudo leer")

    # RAM
    if ram is not None:
        lines.append(f"  Memoria RAM:        {ram['percent']}% de uso")
        lines.append(
            f"    Detalle:          {ram['used_gb']} GB usados "
            f"de {ram['total_gb']} GB totales"
        )
        lines.append(f"    Disponible:       {ram['available_gb']} GB")
    else:
        lines.append("  Memoria RAM:        No se pudo leer")

    # Disco
    if disk is not None:
        lines.append(f"  Disco principal:    {disk['percent']}% de uso")
        lines.append(
            f"    Detalle:          {disk['used_gb']} GB usados "
            f"de {disk['total_gb']} GB totales"
        )
        lines.append(f"    Espacio libre:    {disk['free_gb']} GB")
    else:
        lines.append("  Disco principal:    No se pudo leer")

    lines.append("")

    # ── Diagnostico detallado ──
    lines.append("-" * 64)
    lines.append("  DETALLE DEL DIAGNOSTICO")
    lines.append("-" * 64)
    lines.append("")

    level_labels = {
        "normal": "NORMAL",
        "warning": "ADVERTENCIA",
        "critical": "ATENCION",
        "error": "ERROR DE LECTURA",
    }

    if diagnostics:
        for diag in diagnostics:
            label = level_labels.get(diag.get("level"), "DESCONOCIDO")
            lines.append(f"  [{label}] {diag.get('metric')}")
            lines.append(f"    {diag.get('message')}")
            lines.append("")
    else:
        lines.append("  No se registraron diagnósticos específicos.")
        lines.append("")

    lines.append(
        "  Nota: Un valor elevado en un momento dado no indica necesariamente"
    )
    lines.append(
        "  un problema permanente. Los valores varian segun las aplicaciones activas."
    )
    lines.append("")

    # ── Recomendaciones ──
    lines.append("-" * 64)
    lines.append("  RECOMENDACIONES SUGERIDAS")
    lines.append("-" * 64)
    lines.append("")

    if recommendations:
        for rec in recommendations:
            level_label = (
                "Advertencia" if rec.get("level") == "warning" else "Atencion"
            )
            lines.append(f"  >> {rec.get('metric')} ({level_label}):")
            for i, step in enumerate(rec.get("steps", []), start=1):
                lines.append(f"     {i}. {step}")
            lines.append("")
    else:
        lines.append("  No se detectaron situaciones que requieran atencion inmediata.")
        lines.append("  El sistema se encuentra en optimas condiciones operativas.")
        lines.append("")

    # ── Ultima prueba de conexion / Internet ──
    lines.append("-" * 64)
    lines.append("  ULTIMA PRUEBA DE VELOCIDAD DE INTERNET")
    lines.append("-" * 64)
    lines.append("")

    if network_test and isinstance(network_test, dict) and network_test.get("success"):
        lines.append(f"  Fecha y hora:       {network_test.get('timestamp', 'N/D')}")
        lines.append(f"  Velocidad Descarga: {network_test.get('download_mbps', 'N/D')} Mbps (~{network_test.get('download_mbs', 'N/D')} MB/s)")
        lines.append(f"  Velocidad Carga:    {network_test.get('upload_mbps', 'N/D')} Mbps (~{network_test.get('upload_mbs', 'N/D')} MB/s)")
        lines.append(f"  Latencia (Ping):    {network_test.get('ping_ms', 'N/D')} ms")
        if network_test.get("server_name"):
            lines.append(f"  Servidor:           {network_test.get('server_name')}")
    else:
        lines.append("  No se ha realizado una prueba de velocidad durante esta sesion.")
        lines.append("  (Puedes ejecutarla desde la seccion WiFi de PC Rescue)")

    lines.append("")

    # ── Pie de pagina ──
    lines.append("=" * 64)
    lines.append("  Informe generado por PC Rescue.")
    lines.append("  Documento meramente orientativo. No reemplaza a un servicio tecnico especializado.")
    lines.append("=" * 64)

    return "\n".join(lines)
