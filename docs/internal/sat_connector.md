# SAT CFDI Download Connector

Esta guía resume cómo configurar el nodo de descarga masiva de CFDI.

Este conector utiliza `usage_mode: step_and_tool` para funcionar en flujos con o sin el nodo de IA.

1. **Obtener archivos de e‑firma**
   - Ingresa al portal del SAT y descarga tu archivo `.cer` y la clave privada `.key`.
   - Conserva la contraseña de la clave.

2. **Registrar credenciales en Kyra**
   - Usa el servicio de credenciales para guardar tu e‑firma con `provider="sat"` y, opcionalmente, el `chat_id` de la sesión.
   - La combinación del archivo `.key` y la contraseña se cifra usando el mismo esquema que los tokens sensibles.

3. **Campos de entrada del nodo**
   - `fecha_inicio`: fecha inicial de búsqueda (AAAA-MM-DD).
   - `fecha_fin`: fecha final de búsqueda (AAAA-MM-DD).
   - `tipo`: `"I"` para ingresos o `"E"` para egresos.
   - `rfc`: RFC del emisor o receptor para control de cuota diaria.
   - `dest_dir` (opcional): carpeta donde se guardarán los XML (si no se indica se usa un directorio temporal seguro).

4. **Salida**
   - Diccionario con `file_paths`, una lista de rutas a los XML descargados.

5. **Límites**
   - El conector controla un máximo de 50 solicitudes por RFC al día. Si se supera, devuelve un error.
