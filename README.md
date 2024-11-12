# VideoGenerator

## Descripción
VideoGenerator es una aplicación avanzada que crea videos musicales combinando archivos de audio con una imagen estática. Está disponible en dos versiones optimizadas:
- Versión Windows: Optimizada para sistemas con GPU AMD usando codificación H.265 (HEVC) vía AMF
- Versión Linux: Optimizada para sistemas con GPU AMD usando codificación VAAPI (H.265/H.264)

## Características
- Interfaz gráfica de usuario intuitiva
- Soporte para múltiples formatos de audio (.mp3, .wav, .ogg, .flac, .aac, .m4a, .wma)
- Ordenamiento automático de pistas de audio por número
- Redimensionamiento y centrado automático de la imagen
- Fade in y fade out de video
- Optimización para GPU AMD:
  - Windows: Codificación H.265 (HEVC) con hevc_amf o H.264
  - Linux: Codificación mediante VAAPI (H.265/H.264)
- Ajuste dinámico del uso de CPU basado en la carga del sistema y número de núcleos
- Visualización detallada del progreso de codificación en tiempo real
- Barra de progreso para seguimiento visual del proceso

## Requisitos

### Windows
- FFmpeg (instalado y accesible desde la línea de comandos)
- Controladores AMD actualizados para soporte AMF
- Python 3.7 o superior (si se instala desde fuente)

### Linux
- FFmpeg con soporte VAAPI
- Mesa VA drivers
- Python 3.7 o superior (si se instala desde fuente)
- Dependencias del sistema:
  ```
  ffmpeg vainfo mesa-va-drivers libva-drm2 libva2 python3-tk python3-pil.imagetk
  ```

## Instalación

### Windows
1. Método instalador:
   - Descarga el instalador VideoGenerator-Setup.exe desde la página de releases
   - Ejecuta el instalador y sigue las instrucciones en pantalla
   - Abre VideoGenerator desde el menú de inicio o el acceso directo

2. Desde fuente:
   ```
   pip install -r requirements.txt
   python videogenerator.py
   ```

### Linux
1. Método paquete DEB (recomendado):
   ```bash
   sudo dpkg -i videogenerator_1.1.deb
   sudo apt-get install -f  # Si hay dependencias faltantes
   ```

2. Desde fuente:
   ```bash
   # Instalar dependencias del sistema
   sudo apt install ffmpeg vainfo mesa-va-drivers libva-drm2 libva2 python3-tk python3-pil.imagetk
   
   # Instalar dependencias de Python
   pip3 install -r requirements.txt
   
   # Ejecutar el programa
   python3 videogenerator.py
   ```

## Uso

1. Inicie el programa:
   - Windows: Desde el menú inicio o ejecutando el .exe
   - Linux: Desde el menú de aplicaciones o mediante terminal (videogenerator)

2. Use la interfaz gráfica para:
   - Seleccionar el directorio que contiene los archivos de audio
   - Elegir una imagen para el fondo del video
   - Seleccionar el directorio de salida para el video generado
   - Especificar un nombre para el archivo de video (opcional)
   - Activar o desactivar el uso de GPU y seleccionar la calidad

3. Haga clic en "Generar video" para iniciar el proceso.

4. El progreso y los mensajes se mostrarán en la ventana de la aplicación.

## Notas
- Para un rendimiento óptimo con GPU AMD:
  - Windows: Asegúrese de tener los controladores más recientes con soporte AMF
  - Linux: Asegúrese de tener los controladores Mesa y VAAPI correctamente instalados
- El uso de CPU se ajusta dinámicamente según la carga del sistema
- El tiempo de procesamiento dependerá de la duración del audio, la potencia del sistema y el uso de GPU vs CPU

## Solución de problemas

### Windows
- Si encuentra errores con AMF, actualice los controladores de AMD
- Verifique que FFmpeg está en el PATH del sistema

### Linux
- Para verificar el soporte VAAPI:
  ```bash
  vainfo
  ```
- Si hay problemas con la GPU, el programa automáticamente usará codificación por CPU
- Verifique la instalación correcta de los controladores Mesa y VAAPI

## Licencia

Este proyecto está licenciado bajo la licencia BSD de 3 cláusulas.

Consulta el archivo LICENSE para más detalles.

La licencia BSD de 3 cláusulas es una licencia de software libre permisiva que permite el uso, la redistribución y la modificación casi sin restricciones, siempre que se mantengan las atribuciones al autor original y la renuncia de garantías.

## Autor

Desarrollado con ❤️ por [Wamphyre](https://github.com/Wamphyre)
Si te gusta puedes comprarme un café en https://ko-fi.com/wamphyre94078
