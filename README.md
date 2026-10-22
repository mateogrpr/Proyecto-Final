Voy a desarrollar PC Rescue, una microherramienta de escritorio hecha en Python para Windows que ayuda a las personas a detectar problemas comunes en su computadora y saber cómo actuar.

Sus funciones principales serán:

- Monitoreo: mostrar el uso del procesador (CPU), la memoria RAM y el espacio disponible en el disco.
- Diagnóstico automático: detectar valores que puedan indicar problemas y clasificarlos mediante alertas.
- Recomendaciones: explicar las posibles causas y ofrecer pasos para revisar cada problema.
- Generación de informes: exportar los resultados del análisis y las recomendaciones a un archivo de texto (`.txt`).

La aplicación utilizará `tkinter` para la interfaz gráfica y `psutil` para obtener información del sistema.

Objetivo: completar una versión funcional en tres días, aprendiendo Python durante el desarrollo. La herramienta analizará y recomendará acciones, pero no realizará cambios peligrosos ni eliminará archivos automáticamente.

Día 1: interfaz y mediciones

    Verificar Python y preparar el entorno.

    Instalar las dependencias.

    Crear la ventana principal.

    Diseñar las secciones de CPU, RAM y almacenamiento.

    Implementar el botón «Analizar».

    Mostrar datos reales del sistema.

    Probar que la aplicación se ejecute correctamente.

Día 2: diagnóstico y recomendaciones

    Crear funciones independientes para evaluar las métricas.

    Definir umbrales razonables y configurables.

    Mostrar alertas con explicaciones.

    Generar recomendaciones según los resultados.

    Manejar errores y situaciones inesperadas.

    Probar distintos escenarios.

Día 3: informes y finalización

    Implementar la exportación a .txt.

    Mejorar la presentación visual.

    Probar los casos normales y los errores.

    Corregir los problemas encontrados.

    Preparar una demostración de la aplicación.

    Documentar cómo instalarla y ejecutarla.