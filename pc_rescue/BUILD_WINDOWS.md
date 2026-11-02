# Reconstruir PC Rescue en Windows

Ejecuta estos comandos en PowerShell desde la carpeta `pc_rescue` (la que contiene `app.py` y `PC_Rescue.spec`). Se recomienda Python 3.11 de 64 bits.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --clean --noconfirm PC_Rescue.spec
```

El ejecutable queda en `dist\PC_Rescue.exe`. Para comprobar primero la aplicación sin empaquetar:

```powershell
python app.py
```

La compilación usa `PC_Rescue.spec`, que incluye explícitamente `speedtest` aunque la importación se realice al ejecutar la prueba de red. No copies la carpeta `build` ni el ejecutable antiguo del RAR al proyecto limpio antes de compilar.
