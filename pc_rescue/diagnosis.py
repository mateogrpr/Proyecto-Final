"""
diagnosis.py — Reglas de diagnóstico del sistema.

Este módulo evalúa las métricas obtenidas por metrics.py y determina
si representan un estado normal, una advertencia o una situación crítica.

IMPORTANTE: Un valor elevado NO demuestra por sí solo la causa de un problema.
Los mensajes de este módulo explican qué significa el valor, sin afirmar
que sea la causa directa de un fallo.

Cada función recibe un valor numérico y devuelve un diccionario con:
    - level: "normal", "warning" o "critical"
    - message: Texto explicativo para el usuario

Puedes probar estas funciones directamente en la consola:

    from diagnosis import evaluate_cpu, evaluate_ram, evaluate_disk
    print(evaluate_cpu(92))
    print(evaluate_ram(45))
    print(evaluate_disk(88))
"""


# ─────────────────────────────────────────────
# Umbrales configurables
# ─────────────────────────────────────────────
# Estos valores definen cuándo una métrica pasa de "normal" a "advertencia"
# o de "advertencia" a "crítica". Puedes ajustarlos según tu criterio.
# Por ejemplo, si consideras que 70% de CPU ya es preocupante, cambia
# CPU_WARNING a 70.

CPU_WARNING = 80    # % de CPU para mostrar advertencia
CPU_CRITICAL = 95   # % de CPU para mostrar alerta crítica

RAM_WARNING = 80    # % de RAM para mostrar advertencia
RAM_CRITICAL = 95   # % de RAM para mostrar alerta crítica

DISK_WARNING = 85   # % de disco para mostrar advertencia
DISK_CRITICAL = 95  # % de disco para mostrar alerta crítica


# ─────────────────────────────────────────────
# Funciones de evaluación
# ─────────────────────────────────────────────

def evaluate_cpu(percent):
    """Evalúa el porcentaje de uso de la CPU.

    Args:
        percent (float): Porcentaje de uso de CPU (0.0 a 100.0).

    Returns:
        dict con 'level' ("normal"/"warning"/"critical") y 'message' (str).
        Devuelve None si percent es None (métrica no disponible).
    """
    if percent is None:
        return {
            "level": "error",
            "message": "No se pudo leer el uso de la CPU.",
        }

    if percent >= CPU_CRITICAL:
        return {
            "level": "critical",
            "message": (
                f"El uso de CPU es muy elevado ({percent}%). "
                "Esto puede indicar que algún programa está consumiendo "
                "muchos recursos, aunque también puede ser temporal "
                "(por ejemplo, durante una actualización o instalación). "
                "Conviene investigar qué proceso está usando más CPU."
            ),
        }
    elif percent >= CPU_WARNING:
        return {
            "level": "warning",
            "message": (
                f"El uso de CPU está por encima de lo habitual ({percent}%). "
                "Esto no necesariamente indica un problema permanente. "
                "Puede deberse a programas exigentes que se están ejecutando "
                "en este momento."
            ),
        }
    else:
        return {
            "level": "normal",
            "message": f"El uso de CPU está en un nivel normal ({percent}%).",
        }


def evaluate_ram(percent):
    """Evalúa el porcentaje de uso de la memoria RAM.

    Args:
        percent (float): Porcentaje de uso de RAM (0.0 a 100.0).

    Returns:
        dict con 'level' y 'message'. None-safe.
    """
    if percent is None:
        return {
            "level": "error",
            "message": "No se pudo leer el uso de la memoria RAM.",
        }

    if percent >= RAM_CRITICAL:
        return {
            "level": "critical",
            "message": (
                f"La memoria RAM está casi llena ({percent}%). "
                "Cuando la RAM se agota, Windows usa el disco como memoria "
                "auxiliar (archivo de paginación), lo que puede hacer que "
                "el equipo se sienta muy lento. "
                "Revisar qué aplicaciones están usando más memoria puede ayudar."
            ),
        }
    elif percent >= RAM_WARNING:
        return {
            "level": "warning",
            "message": (
                f"El uso de RAM es alto ({percent}%). "
                "Puede que tengas muchas aplicaciones abiertas o que alguna "
                "esté usando más memoria de la esperada. "
                "Si notas lentitud, podría estar relacionado con esto."
            ),
        }
    else:
        return {
            "level": "normal",
            "message": f"El uso de RAM está en un nivel normal ({percent}%).",
        }


def evaluate_disk(percent):
    """Evalúa el porcentaje de uso del disco principal.

    Args:
        percent (float): Porcentaje de uso del disco (0.0 a 100.0).

    Returns:
        dict con 'level' y 'message'. None-safe.
    """
    if percent is None:
        return {
            "level": "error",
            "message": "No se pudo leer el uso del disco.",
        }

    if percent >= DISK_CRITICAL:
        return {
            "level": "critical",
            "message": (
                f"El disco principal está casi lleno ({percent}%). "
                "Cuando queda muy poco espacio libre, Windows puede volverse "
                "inestable: las actualizaciones pueden fallar, los programas "
                "podrían no guardar archivos correctamente, y el rendimiento "
                "general puede verse afectado."
            ),
        }
    elif percent >= DISK_WARNING:
        return {
            "level": "warning",
            "message": (
                f"El espacio en disco está por encima del {DISK_WARNING}% "
                f"de uso ({percent}%). "
                "Aún hay espacio disponible, pero es recomendable revisar "
                "si hay archivos innecesarios que se puedan eliminar para "
                "evitar problemas a futuro."
            ),
        }
    else:
        return {
            "level": "normal",
            "message": f"El espacio en disco está en un nivel normal ({percent}%).",
        }


def run_all_diagnostics(cpu_percent, ram_percent, disk_percent):
    """Ejecuta los tres diagnósticos y devuelve una lista de resultados.

    Esto simplifica la llamada desde app.py: en lugar de llamar a las tres
    funciones por separado, se llama a una sola que devuelve todo.

    Args:
        cpu_percent: Porcentaje de CPU (float o None).
        ram_percent: Porcentaje de RAM (float o None).
        disk_percent: Porcentaje de disco (float o None).

    Returns:
        list de dicts, cada uno con 'metric', 'level' y 'message'.
    """
    return [
        {"metric": "CPU", **evaluate_cpu(cpu_percent)},
        {"metric": "RAM", **evaluate_ram(ram_percent)},
        {"metric": "Disco", **evaluate_disk(disk_percent)},
    ]


def get_system_overall_status(diagnostics):
    """Determina el estado general del sistema a partir de los diagnósticos.

    Args:
        diagnostics: Lista devuelta por run_all_diagnostics.

    Returns:
        dict con:
            - status_text: 'Todo correcto', 'Atención recomendada' o 'Problema detectado'
            - level: 'normal', 'warning', 'critical' o 'error'
            - summary: Explicación concisa y equilibrada
    """
    if not diagnostics:
        return {
            "status_text": "Sin diagnóstico",
            "level": "error",
            "summary": "No se han recopilado métricas suficientes aún.",
        }

    levels = [d.get("level") for d in diagnostics]

    if "critical" in levels:
        crit_metrics = [d.get("metric") for d in diagnostics if d.get("level") == "critical"]
        return {
            "status_text": "Problema detectado",
            "level": "critical",
            "summary": (
                f"Recurso(s) en nivel crítico: {', '.join(crit_metrics)}. "
                "Conviene revisar los procesos activos o el espacio disponible para evitar lentitud."
            ),
        }
    elif "warning" in levels:
        warn_metrics = [d.get("metric") for d in diagnostics if d.get("level") == "warning"]
        return {
            "status_text": "Atención recomendada",
            "level": "warning",
            "summary": (
                f"Recurso(s) con uso elevado: {', '.join(warn_metrics)}. "
                "Esto puede deberse a tareas en ejecución y no necesariamente indica una falla permanente."
            ),
        }
    elif all(lvl == "normal" for lvl in levels):
        return {
            "status_text": "Todo correcto",
            "level": "normal",
            "summary": (
                "Todos los recursos monitoreados se encuentran en parámetros normales y estables."
            ),
        }
    else:
        return {
            "status_text": "Lectura parcial",
            "level": "error",
            "summary": "Algunas métricas no pudieron consultarse con certeza.",
        }
