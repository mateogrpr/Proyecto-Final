# PC Rescue — Panel de Diagnóstico y Rendimiento para Windows

Herramienta de escritorio profesional y ligera para Windows que permite consultar el estado del sistema, medir el rendimiento en tiempo real, analizar la conexión a Internet y consultar los componentes y controladores instalados.

---

## Características Principales

### 1. Sección Inicio
- **Medidores Semicirculares dinámicos (estilo velocímetro)**: Visualización limpia de 0 a 100% para CPU, RAM y Almacenamiento, coloreados según el estado (verde, amarillo, rojo).
- **Actualización automática**: CPU y RAM cada 1 segundo; Almacenamiento cada 5 segundos (sin botones manuales ni bloqueos de interfaz).
- **Indicador de estado general**: Diagnóstico global sintetizado (*Todo correcto*, *Atención recomendada*, *Problema detectado*).
- **Diagnóstico automático y recomendaciones**: Explicaciones claras de por qué un valor está elevado y pasos seguros para revisarlo.
- **Exportación de informes**: Genera un archivo `.txt` estructurado con fecha, hora, métricas, diagnóstico, recomendaciones y prueba de red.

### 2. Sección WiFi y Red
- **Información de conexión en tiempo real**: Tipo de conexión (WiFi o Ethernet), SSID, IP local, nombre del adaptador y estado de conectividad a Internet.
- **Medición de velocidad bajo demanda**: Prueba real de velocidad de Descarga (Mbps / MB/s), Carga (Mbps / MB/s) y Latencia (Ping en ms) mediante `speedtest-cli` en segundo plano sin congelar la interfaz.
- **Aviso informativo**: Explicación clara sobre equivalencias de unidades (8 Mbps ≈ 1 MB/s) y consumo de datos de la prueba.

### 3. Sección Componentes
- **Hardware detallado del equipo**:
  - **Procesador (CPU)**: Fabricante, modelo, núcleos físicos, lógicos y frecuencia máxima.
  - **Tarjeta Gráfica (GPU)**: Identificación de tarjetas detectadas, memoria dedicada y versión de controlador.
  - **Placa Madre**: Fabricante, modelo de placa, versión y fecha del BIOS/UEFI.
  - **Memoria RAM**: Capacidad total, cantidad de módulos/slots, capacidad por módulo y frecuencia.
  - **Almacenamiento**: Discos físicos y particiones lógicas montadas con espacio utilizado y libre.
  - **Sistema Operativo**: Edición de Windows, versión, arquitectura y nombre del equipo.
- **Consulta de Controladores (Drivers)**:
  - Tabla interactiva con dispositivo, categoría, fabricante/proveedor, versión, fecha y estado.
  - Filtro por categoría (Red, Gráficos, Audio, Bluetooth, USB, Almacenamiento, Chipset/Sistema, etc.).
  - Búsqueda en tiempo real por texto.
  - Botón *Actualizar información* para recargar datos sin bloquear la aplicación.

### 4. Herramientas Rápidas del Sistema (Barra Lateral)
- **Acceso Directo a CMD**: Abre una ventana nativa e independiente del Símbolo del sistema (`cmd.exe`).
- **Acceso Directo a PowerShell**: Abre una ventana nativa e independiente de PowerShell (`pwsh.exe` o `powershell.exe`).
- **Lanzamiento no bloqueante**: Utiliza banderas de proceso seguras de Windows (`CREATE_NEW_CONSOLE`) para que las terminales funcionen de forma autónoma sin congelar ni cerrar PC Rescue.

### 5. Overlay Gaming (Superposición de Rendimiento)
- **Superposición Always-on-Top compacta y ligera**: Diseñada para visualizar métricas esenciales durante partidas en modo ventana o ventana sin bordes.
- **Métricas visualizadas**:
  - **CPU**: Utilización real en porcentaje y temperatura en °C.
  - **GPU**: Utilización en tiempo real (vía contadores nativos PDH de Windows o `nvidia-smi`) y temperatura en °C.
  - **RAM**: Porcentaje de memoria utilizada y desglose en GB usados / GB totales.
- **Sin intrusión ni penalización de rendimiento**:
  - No inyecta código ni modifica procesos (compatible con políticas de juego seguro).
  - No roba el foco a los videojuegos (`WS_EX_NOACTIVATE`).
  - Clics transparentes opcionales o arrastre con el ratón.
  - Opciones de ubicación (4 esquinas o posición personalizada), tamaño, opacidad (60% a 100%) y frecuencia de refresco.
  - Cierre seguro: al cerrar PC Rescue el overlay se destruye sin dejar procesos residuales.
- **Detección de temperaturas y sensores**:
  - Las lecturas de temperatura de GPU aprovechan `nvidia-smi` en tarjetas dedicadas NVIDIA.
  - Para temperaturas de CPU y GPUs integradas/AMD en Windows, se enlaza automáticamente con proveedores de sensores estándar como LibreHardwareMonitor o OpenHardwareMonitor si están en ejecución, o zonas térmicas ACPI.
  - En equipos o entornos sin sensores térmicos accesibles a nivel de usuario, la aplicación reporta con precisión `N/D` sin generar alertas falsas ni inventar mediciones ficticias.

---

## Requisitos

- **Sistema Operativo**: Windows 10 o Windows 11.
- **Python**: 3.8 o superior (recomendado 3.11 de 64 bits).
- **Bibliotecas**: `psutil` y `speedtest-cli`.

---

## Instalación y Ejecución

1. Abre una terminal (PowerShell o CMD).
2. Dirígete a la carpeta del proyecto:
   ```powershell
   cd C:\Users\TU_USUARIO\Documents\pc_rescue
   ```
3. Instala las dependencias:
   ```powershell
   pip install -r requirements.txt
   ```
4. Ejecuta la aplicación:
   ```powershell
   python app.py
   ```

---

## Estructura del Código

```
pc_rescue/
├── app.py              # Ventana principal, navegación lateral, interfaz gráfica y medidores Canvas
├── overlay.py          # Superposición Always-on-Top Gaming Overlay y diálogo de configuración
├── metrics.py          # Lectura de CPU, RAM, disco, GPU (PDH/nvidia-smi) y temperaturas reales
├── diagnosis.py        # Umbrales configurables y evaluación global del estado del sistema
├── recommendations.py  # Instrucciones paso a paso según las alertas detectadas
├── network_utils.py    # Información de adaptadores (WiFi/Ethernet) y test de velocidad asíncrono
├── hardware_utils.py   # Consulta de hardware (WMI/CIM/PowerShell) y filtrado de drivers
├── terminal_utils.py   # Lanzador seguro de consolas CMD y PowerShell independientes
├── report.py           # Generación del informe exportable en texto plano (.txt)
├── requirements.txt    # Dependencias del proyecto (psutil, speedtest-cli)
├── PC_Rescue.spec      # Especificación para compilación con PyInstaller
└── README.md           # Documentación del proyecto
```

---

## Generación del Ejecutable (.exe)

Para generar el ejecutable autónomo sin consola para Windows:

```powershell
pip install pyinstaller
python -m PyInstaller --clean --noconfirm PC_Rescue.spec
```

El archivo ejecutable compilado estará disponible en `dist\PC_Rescue.exe`.

---

## Notas de Seguridad y Filosofía
- La herramienta es **estrictamente de diagnóstico y consulta**: no modifica controladores, registros ni configuraciones del sistema.
- Las recomendaciones son sugerencias de mantenimiento y no reemplazan a un técnico calificado.
- Un uso elevado puntual de un recurso es normal durante tareas pesadas y no indica necesariamente una falla permanente.
