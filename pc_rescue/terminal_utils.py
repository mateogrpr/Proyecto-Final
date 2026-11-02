"""
terminal_utils.py — Lanzador seguro de consolas independientes para Windows.

Proporciona funciones para abrir CMD (Símbolo del sistema) y PowerShell
en ventanas nativas e independientes de Windows sin bloquear la interfaz gráfica
ni ejecutar comandos automáticos.
"""

import os
import shutil
import subprocess

# En Windows, CREATE_NEW_CONSOLE (0x00000010) fuerza la creación de una consola propia
CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)


def get_cmd_path():
    """Localiza la ruta absoluta al ejecutable cmd.exe."""
    cmd = shutil.which("cmd.exe")
    if cmd and os.path.isfile(cmd):
        return cmd
    sys_root = os.environ.get("SystemRoot", r"C:\Windows")
    candidate = os.path.join(sys_root, "System32", "cmd.exe")
    if os.path.isfile(candidate):
        return candidate
    return None


def get_powershell_path():
    """Localiza la ruta al ejecutable de PowerShell (prioriza pwsh.exe si existe, o powershell.exe)."""
    # 1. Buscar PowerShell moderno (pwsh.exe en PATH o ruta típica de usuario)
    pwsh = shutil.which("pwsh.exe")
    if pwsh and os.path.isfile(pwsh):
        return pwsh, "PowerShell Core"

    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        candidate_pwsh = os.path.join(local_app, "Microsoft", "PowerShell", "pwsh.exe")
        if os.path.isfile(candidate_pwsh):
            return candidate_pwsh, "PowerShell Core"

    # 2. Buscar PowerShell clásico de Windows (powershell.exe)
    ps = shutil.which("powershell.exe")
    if ps and os.path.isfile(ps):
        return ps, "Windows PowerShell"

    sys_root = os.environ.get("SystemRoot", r"C:\Windows")
    candidate_ps = os.path.join(sys_root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    if os.path.isfile(candidate_ps):
        return candidate_ps, "Windows PowerShell"

    return None, "Desconocido"


def open_cmd():
    """Abre una ventana independiente del Símbolo del sistema (CMD).

    Returns:
        tuple (bool, str): (True, path) si tuvo éxito o (False, mensaje_error).
    """
    cmd_path = get_cmd_path()
    if not cmd_path:
        return False, "No se encontró el ejecutable cmd.exe en el sistema."

    try:
        user_home = os.path.expanduser("~")
        subprocess.Popen(
            [cmd_path],
            cwd=user_home,
            creationflags=CREATE_NEW_CONSOLE,
            close_fds=True,
        )
        return True, cmd_path
    except Exception as e:
        return False, f"Error al iniciar CMD: {e}"


def open_powershell():
    """Abre una ventana independiente de PowerShell (Core si está disponible, o Clásico).

    Returns:
        tuple (bool, str): (True, path_o_nombre) si tuvo éxito o (False, mensaje_error).
    """
    ps_path, ps_variant = get_powershell_path()
    if not ps_path:
        return False, "No se encontró ningún ejecutable de PowerShell en el sistema."

    try:
        user_home = os.path.expanduser("~")
        subprocess.Popen(
            [ps_path],
            cwd=user_home,
            creationflags=CREATE_NEW_CONSOLE,
            close_fds=True,
        )
        return True, f"{ps_variant} ({ps_path})"
    except Exception as e:
        return False, f"Error al iniciar PowerShell: {e}"
