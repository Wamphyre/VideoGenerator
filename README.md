# VideoGenerator

## Descripción
VideoGenerator es una aplicación avanzada que crea videos musicales combinando archivos de audio con una imagen estática. Está optimizada para sistemas con CPU AMD Ryzen y GPU AMD Radeon, utilizando codificación H.265 (HEVC) para una mayor eficiencia y calidad.

## Características
- Interfaz gráfica de usuario intuitiva
- Soporte para múltiples formatos de audio (.mp3, .wav, .ogg, .flac, .aac, .m4a, .wma)
- Ordenamiento automático de pistas de audio por número
- Redimensionamiento y centrado automático de la imagen
- Fade in y fade out de video
- Optimización para GPU AMD en Windows utilizando H.265 (HEVC) con hevc_amf o bien la posibilidad de usar H.264
- Ajuste dinámico del uso de CPU basado en la carga del sistema y número de núcleos
- Visualización detallada del progreso de codificación en tiempo real
- Barra de progreso para seguimiento visual del proceso

## Requisitos
- Python 3.7 o superior
- FFmpeg (instalado y accesible desde la línea de comandos)
- Bibliotecas Python: moviepy, Pillow, numpy, psutil

## Instalación (Multiplataforma con Python)

1. Clone el repositorio.

2. Instale las dependencias de Python:
   ```
   pip install -r requirements.txt
   ```

3. Asegúrese de tener FFmpeg instalado en su sistema y accesible desde la línea de comandos.

## Instalación en Windows

- Descarga el instalador VideoGenerator-Setup.exe desde la página de releases.
- Ejecuta el instalador y sigue las instrucciones en pantalla.
- Una vez instalado, puedes abrir VideoGenerator desde el menú de inicio o el acceso directo en el escritorio (si elegiste crearlo durante la instalación).

- Nota: VideoGenerator requiere que tengas instalado FFmpeg en tu sistema. Si no lo tienes instalado, por favor visita ffmpeg.org para descargarlo e instalarlo antes de usar VideoGenerator.

## Uso

1. Ejecute el script mediante terminal:
   ```
   python videogenerator.py
   ```
   O bien haciendo doble click sobre el fichero ejecutable.

2. Use la interfaz gráfica para:
   - Seleccionar el directorio que contiene los archivos de audio
   - Elegir una imagen para el fondo del video
   - Seleccionar el directorio de salida para el video generado
   - Especificar un nombre para el archivo de video (opcional)
   - Activar o desactivar el uso de GPU AMD para codificación H.265 (solo en Windows)

3. Haga clic en "Generar video" para iniciar el proceso.

4. El progreso y los mensajes se mostrarán en la ventana de la aplicación.

## Notas
- Para un rendimiento óptimo en sistemas con GPU AMD, asegúrese de tener los controladores más recientes instalados.
- La codificación H.265 (HEVC) con GPU está optimizada para tarjetas AMD Radeon en sistemas Windows.
- El uso de CPU se ajusta dinámicamente según la carga del sistema para un rendimiento óptimo.
- El tiempo de procesamiento puede variar dependiendo de la duración total del audio, la potencia de su sistema y el uso de GPU vs CPU.

## Solución de problemas
- Si encuentra errores relacionados con FFmpeg, asegúrese de que está correctamente instalado y accesible desde la línea de comandos.
- Para problemas con la codificación de GPU, intente desactivar la opción de uso de GPU y generar el video usando solo la CPU.
- Si la ventana de log no muestra actualizaciones en tiempo real, asegúrese de que su sistema no esté sobrecargado.

## Licencia

Este proyecto está licenciado bajo la licencia BSD de 3 cláusulas.

Consulta el archivo LICENSE para más detalles.

La licencia BSD de 3 cláusulas es una licencia de software libre permisiva que permite el uso, la redistribución y la modificación casi sin restricciones, siempre que se mantengan las atribuciones al autor original y la renuncia de garantías.

## Autor

Desarrollado con ❤️ por [Wamphyre](https://github.com/Wamphyre)
Si te gusta puedes comprarme un café en https://ko-fi.com/wamphyre94078
