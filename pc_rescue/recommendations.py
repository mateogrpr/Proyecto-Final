"""
recommendations.py — Generación de recomendaciones según el diagnóstico.

Este módulo recibe la lista de diagnósticos (generada por diagnosis.py)
y produce recomendaciones comprensibles para el usuario.

Principios:
    - Las recomendaciones son instrucciones que el usuario puede seguir.
    - NO se ejecuta ninguna acción peligrosa automáticamente.
    - NO se eliminan archivos ni se modifican configuraciones.
    - NO se afirma que un problema se ha solucionado, solo que se ha detectado.

Puedes probar este módulo en la consola:

    from recommendations import get_recommendations
    diagnostics = [
        {"metric": "CPU", "level": "warning", "message": "..."},
        {"metric": "Disco", "level": "critical", "message": "..."},
    ]
    for rec in get_recommendations(diagnostics):
        print(rec)
"""


# ─────────────────────────────────────────────
# Recomendaciones por métrica y nivel
# ─────────────────────────────────────────────
# Cada clave es (métrica, nivel) y el valor es una lista de pasos.
# Solo se incluyen "warning" y "critical" porque "normal" no requiere acción.

_RECOMMENDATIONS = {
    ("CPU", "warning"): [
        "Abre el Administrador de tareas (Ctrl + Shift + Esc).",
        "Ve a la pestaña «Procesos» y ordena por «CPU» para ver qué "
        "programa está usando más procesador.",
        "Si identificas un programa que no necesitas, puedes cerrarlo "
        "desde allí (clic derecho > Finalizar tarea).",
        "Si el uso alto es temporal (por ejemplo, una actualización), "
        "espera unos minutos y vuelve a analizar.",
    ],
    ("CPU", "critical"): [
        "Abre el Administrador de tareas (Ctrl + Shift + Esc) de inmediato.",
        "Ordena los procesos por uso de CPU para identificar cuál consume más.",
        "Si un programa no responde o consume un porcentaje excesivo, "
        "puedes finalizarlo (clic derecho > Finalizar tarea).",
        "Si el problema persiste tras cerrar programas, reiniciar el equipo "
        "puede ayudar a liberar recursos que quedaron bloqueados.",
        "Si la CPU se mantiene alta constantemente sin razón aparente, "
        "podría ser recomendable consultar con un técnico.",
    ],
    ("RAM", "warning"): [
        "Revisa cuántas aplicaciones tienes abiertas. Cada pestaña del "
        "navegador, cada programa abierto, usa memoria.",
        "Cierra las aplicaciones que no estés usando activamente.",
        "Abre el Administrador de tareas (Ctrl + Shift + Esc) y ordena "
        "por «Memoria» para ver qué programa usa más.",
        "Si usas un navegador con muchas pestañas, considera cerrar las "
        "que no necesites o usar una extensión que las suspenda.",
    ],
    ("RAM", "critical"): [
        "Cierra inmediatamente las aplicaciones que no sean esenciales.",
        "Abre el Administrador de tareas (Ctrl + Shift + Esc) y revisa "
        "qué procesos consumen más memoria.",
        "Si el navegador está usando mucha memoria, cierra las pestañas "
        "innecesarias.",
        "Guardar tu trabajo y reiniciar el equipo libera toda la memoria.",
        "Si esto ocurre frecuentemente, el equipo podría beneficiarse "
        "de más memoria RAM (consultar con un técnico).",
    ],
    ("Disco", "warning"): [
        "Revisa la Papelera de reciclaje: los archivos eliminados siguen "
        "ocupando espacio hasta que la vacíes.",
        "Usa la herramienta «Liberador de espacio en disco» de Windows: "
        "busca «Limpieza de disco» en el menú Inicio.",
        "Revisa la carpeta de Descargas: a menudo se acumulan archivos "
        "que ya no necesitas.",
        "Desinstala programas que ya no uses desde Configuracion > "
        "Aplicaciones > Aplicaciones instaladas.",
    ],
    ("Disco", "critical"): [
        "Es importante liberar espacio pronto para evitar problemas con "
        "el sistema operativo.",
        "Vacía la Papelera de reciclaje si tiene archivos.",
        "Usa «Limpieza de disco» (buscar en el menú Inicio) y selecciona "
        "todas las categorías seguras de limpiar.",
        "Revisa las carpetas Descargas, Documentos y Videos por archivos "
        "grandes que puedas mover a un disco externo.",
        "Desinstala programas que no uses desde Configuracion > "
        "Aplicaciones.",
        "Si tras limpiar el espacio sigue siendo insuficiente, considera "
        "usar un disco externo o consultar con un técnico.",
    ],
}


def get_recommendations(diagnostics):
    """Genera recomendaciones basadas en los resultados del diagnóstico.

    Args:
        diagnostics: Lista de dicts con claves 'metric', 'level' y 'message'
                     (como los que devuelve diagnosis.run_all_diagnostics).

    Returns:
        Lista de dicts, cada uno con:
            - metric (str): Nombre de la métrica ("CPU", "RAM", "Disco")
            - level (str): Nivel de la alerta
            - steps (list[str]): Lista de pasos a seguir

        Si todo está normal, devuelve una lista vacía.
    """
    result = []

    for diag in diagnostics:
        metric = diag.get("metric", "")
        level = diag.get("level", "normal")

        # Solo generamos recomendaciones para warning y critical
        key = (metric, level)
        if key in _RECOMMENDATIONS:
            result.append({
                "metric": metric,
                "level": level,
                "steps": _RECOMMENDATIONS[key],
            })

    return result


def format_recommendations_text(recommendations):
    """Formatea las recomendaciones como texto legible para la interfaz.

    Args:
        recommendations: Lista devuelta por get_recommendations().

    Returns:
        str: Texto formateado listo para mostrar, o un mensaje de que
             todo está en orden si no hay recomendaciones.
    """
    if not recommendations:
        return ""

    lines = []
    lines.append("--- Recomendaciones ---")
    lines.append("")

    for rec in recommendations:
        # Encabezado de la recomendación
        metric = rec["metric"]
        level_label = "Advertencia" if rec["level"] == "warning" else "Atencion"
        lines.append(f">> {metric} ({level_label}):")

        # Pasos numerados
        for i, step in enumerate(rec["steps"], start=1):
            lines.append(f"  {i}. {step}")

        lines.append("")  # Línea vacía entre recomendaciones

    return "\n".join(lines)
