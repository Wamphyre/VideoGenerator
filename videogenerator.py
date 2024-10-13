import os
import sys
import subprocess
from moviepy.editor import *
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import re
import platform
from PIL import Image
import numpy as np
import psutil
import io
import threading
import time

class StdoutRedirector(io.StringIO):
    def __init__(self, write_func, progress_func):
        self.write_func = write_func
        self.progress_func = progress_func
        super().__init__()

    def write(self, string):
        self.write_func(string.strip())
        if string.startswith('t:'):
            try:
                progress = float(string.split()[1])
                self.progress_func(progress)
            except:
                pass

def obtener_numero_pista(nombre_archivo):
    match = re.search(r'^(\d+)', os.path.splitext(nombre_archivo)[0])
    if match:
        return int(match.group(1))
    match = re.search(r'(\d+)', os.path.splitext(nombre_archivo)[0])
    if match:
        return int(match.group(1))
    return nombre_archivo

def procesar_audio(archivo_path):
    try:
        return AudioFileClip(archivo_path)
    except Exception as e:
        print(f"No se pudo cargar el archivo {archivo_path}: {str(e)}")
        return None

def crear_video(directorio_audio, imagen_path, output_path, codec='none', add_info=print, update_progress=None):
    formatos_audio = ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma']
    archivos_audio = [f for f in os.listdir(directorio_audio) if os.path.splitext(f.lower())[1] in formatos_audio]
    
    archivos_audio.sort(key=obtener_numero_pista)
    
    add_info("Orden de los archivos de audio:")
    for archivo in archivos_audio:
        add_info(f"{obtener_numero_pista(archivo)}: {archivo}")

    clips_audio = []
    for i, archivo in enumerate(archivos_audio):
        clip = procesar_audio(os.path.join(directorio_audio, archivo))
        if clip is not None:
            clips_audio.append(clip)
        add_info(f"Procesado: {archivo}")
        if update_progress:
            update_progress(i / len(archivos_audio) * 30)  # 30% del progreso para procesar audio

    audio_final = concatenate_audioclips(clips_audio)

    add_info("Procesando imagen...")

    imagen_pil = Image.open(imagen_path)
    ancho_video, alto_video = 1920, 1080
    ancho_imagen, alto_imagen = imagen_pil.size
    
    escala_ancho = ancho_video / ancho_imagen
    escala_alto = alto_video / alto_imagen
    escala = min(escala_ancho, escala_alto)
    
    nuevo_ancho = int(ancho_imagen * escala)
    nuevo_alto = int(alto_imagen * escala)
    imagen_redimensionada = imagen_pil.resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)
    
    x = (ancho_video - nuevo_ancho) // 2
    y = (alto_video - nuevo_alto) // 2
    
    fondo = Image.new('RGB', (ancho_video, alto_video), color='black')
    fondo.paste(imagen_redimensionada, (x, y))
    
    video = ImageClip(np.array(fondo))
    video = video.set_duration(audio_final.duration)

    video = video.fx(vfx.fadeout, duration=4)
    video = video.fx(vfx.fadein, duration=4)

    video_final = video.set_audio(audio_final)

    add_info("Configurando parámetros de codificación...")

    if update_progress:
        update_progress(35)  # 35% del progreso después de procesar la imagen

    # Configuración optimizada para AMD RADEON RX580 usando H.265 (HEVC) o H.264
    if codec in ['h265', 'h264'] and platform.system() == 'Windows':
        if codec == 'h264':
            ffmpeg_params = [
                "-c:v", "h264_amf",
                "-quality", "quality",
                "-rc", "vbr_latency",
                "-qp_i", "18", "-qp_p", "20", "-qp_b", "22",
                "-b:v", "10M",
                "-maxrate", "15M",
                "-bufsize", "15M",
                "-g", "250",
                "-bf", "3",
                "-profile:v", "high",
                "-level", "5.1"
            ]
        else:  # h265
            ffmpeg_params = [
                "-c:v", "hevc_amf",
                "-quality", "quality",
                "-rc", "vbr_latency",
                "-qp_i", "18", "-qp_p", "20", "-qp_b", "22",
                "-b:v", "10M",
                "-maxrate", "15M",
                "-bufsize", "15M",
                "-g", "250",
                "-bf", "3",
                "-profile:v", "main",
                "-level", "5.1"
            ]
    else:
        ffmpeg_params = ["-c:v", "libx265", "-crf", "23", "-preset", "medium"]

    # Optimización: Ajustar el número de hilos basado en la carga del sistema
    cpu_count = psutil.cpu_count(logical=False)
    cpu_usage = psutil.cpu_percent(interval=1)
    if cpu_usage < 50:
        n_threads = cpu_count
    else:
        n_threads = max(1, cpu_count - 2)

    add_info(f"Iniciando la generación del video con {n_threads} hilos...")

    # Crear un StdoutRedirector que use la función add_info y update_progress
    redirector = StdoutRedirector(add_info, lambda p: update_progress(35 + p * 0.65) if update_progress else None)

    # Redirigir la salida estándar y de error a nuestro redirector
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = redirector
    sys.stderr = redirector

    try:
        video_final.write_videofile(output_path, codec='libx265', audio_codec='aac', fps=50, 
                                    preset='medium', audio_bitrate='320k', 
                                    threads=n_threads, ffmpeg_params=ffmpeg_params)
    finally:
        # Restaurar la salida estándar y de error
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    add_info("Video generado con éxito.")
    if update_progress:
        update_progress(100)

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.title("VideoGenerator v1.1 (Optimizado para AMD)")
        self.master.geometry("900x500")
        self.master.resizable(False, False)
        
        # Establecer el icono de la aplicación
        if getattr(sys, 'frozen', False):
            # Si es un ejecutable compilado
            application_path = sys._MEIPASS
        else:
            # Si es un script .py
            application_path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(application_path, 'icon.ico')
        self.master.iconbitmap(icon_path)
        
        self.pack(fill=tk.BOTH, expand=True)
        self.codec_var = tk.StringVar(value="none")
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        style = ttk.Style()
        style.configure('TButton', font=('Arial', 12))

        selection_frame = ttk.Frame(main_frame)
        selection_frame.pack(fill=tk.X, pady=10)

        self.directorio_btn = ttk.Button(selection_frame, text="Seleccionar directorio de audio", command=self.seleccionar_directorio)
        self.directorio_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.imagen_btn = ttk.Button(selection_frame, text="Seleccionar imagen", command=self.seleccionar_imagen)
        self.imagen_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.salida_btn = ttk.Button(selection_frame, text="Seleccionar directorio de salida", command=self.seleccionar_directorio_salida)
        self.salida_btn.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.nombre_btn = ttk.Button(selection_frame, text="Especificar nombre del archivo", command=self.especificar_nombre_archivo)
        self.nombre_btn.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        selection_frame.grid_columnconfigure(0, weight=1)
        selection_frame.grid_columnconfigure(1, weight=1)

        option_frame = ttk.Frame(main_frame)
        option_frame.pack(fill=tk.X, pady=10)

        self.h265_radio = ttk.Radiobutton(option_frame, text="Usar GPU AMD con códec H.265 (Solo Windows)", 
                                          variable=self.codec_var, value="h265")
        self.h265_radio.pack(side=tk.LEFT, padx=5)

        self.h264_radio = ttk.Radiobutton(option_frame, text="Usar GPU AMD con códec H.264 (Solo Windows)", 
                                          variable=self.codec_var, value="h264")
        self.h264_radio.pack(side=tk.LEFT, padx=5)

        self.generar_btn = ttk.Button(option_frame, text="Generar video", command=self.generar_video)
        self.generar_btn.pack(side=tk.RIGHT, padx=5)

        self.progress = ttk.Progressbar(main_frame, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(fill=tk.X, pady=10)

        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.info_text = tk.Text(info_frame, height=10, wrap=tk.WORD)
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(info_frame, orient="vertical", command=self.info_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.info_text.configure(yscrollcommand=scrollbar.set)

        self.quit = ttk.Button(main_frame, text="SALIR", command=self.master.destroy)
        self.quit.pack(side=tk.BOTTOM, pady=10)

    def add_info(self, message):
        self.info_text.insert(tk.END, str(message) + "\n")
        self.info_text.see(tk.END)
        self.info_text.update()

    def update_progress(self, value):
        self.progress['value'] = value
        self.progress.update()

    def seleccionar_directorio(self):
        self.directorio_audio = filedialog.askdirectory()
        if self.directorio_audio:
            self.add_info(f"Directorio de audio seleccionado: {self.directorio_audio}")

    def seleccionar_imagen(self):
        self.imagen_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png")])
        if self.imagen_path:
            self.add_info(f"Imagen seleccionada: {self.imagen_path}")

    def seleccionar_directorio_salida(self):
        self.directorio_salida = filedialog.askdirectory()
        if self.directorio_salida:
            self.add_info(f"Directorio de salida seleccionado: {self.directorio_salida}")

    def especificar_nombre_archivo(self):
        self.nombre_archivo = simpledialog.askstring("Nombre del archivo", "Ingrese el nombre del archivo de video (sin extensión):")
        if self.nombre_archivo:
            self.nombre_archivo = self.nombre_archivo.strip()
            if not self.nombre_archivo.endswith('.mp4'):
                self.nombre_archivo += '.mp4'
            self.add_info(f"Nombre del archivo especificado: {self.nombre_archivo}")

    def generar_video(self):
        if not hasattr(self, 'directorio_audio') or not hasattr(self, 'imagen_path') or not hasattr(self, 'directorio_salida'):
            messagebox.showerror("Error", "Por favor, selecciona el directorio de audio, la imagen y el directorio de salida")
            return

        if not hasattr(self, 'nombre_archivo'):
            self.nombre_archivo = "video_musical.mp4"

        output_path = os.path.join(self.directorio_salida, self.nombre_archivo)
        
        counter = 1
        nombre_base, extension = os.path.splitext(self.nombre_archivo)
        while os.path.exists(output_path):
            output_path = os.path.join(self.directorio_salida, f"{nombre_base}_{counter}{extension}")
            counter += 1

        self.add_info("Iniciando generación del video...")
        self.progress['value'] = 0
        
        # Deshabilitar botones durante la generación
        self.generar_btn['state'] = 'disabled'
        self.directorio_btn['state'] = 'disabled'
        self.imagen_btn['state'] = 'disabled'
        self.salida_btn['state'] = 'disabled'
        self.nombre_btn['state'] = 'disabled'
        
        # Iniciar la generación del video en un hilo separado
        threading.Thread(target=self.generar_video_thread, args=(output_path,), daemon=True).start()

    def generar_video_thread(self, output_path):
        try:
            crear_video(self.directorio_audio, self.imagen_path, output_path, 
                        self.codec_var.get(), self.add_info, self.update_progress)
            self.master.after(0, self.video_generado_exitosamente, output_path)
        except Exception as e:
            self.master.after(0, self.mostrar_error, str(e))
        finally:
            self.master.after(0, self.habilitar_botones)

    def video_generado_exitosamente(self, output_path):
        self.add_info(f"Video generado correctamente: {output_path}")
        messagebox.showinfo("Éxito", f"Video generado correctamente: {output_path}")

    def mostrar_error(self, mensaje_error):
        self.add_info(f"Error al generar el video: {mensaje_error}")
        messagebox.showerror("Error", f"Error al generar el video: {mensaje_error}")

    def habilitar_botones(self):
        self.generar_btn['state'] = 'normal'
        self.directorio_btn['state'] = 'normal'
        self.imagen_btn['state'] = 'normal'
        self.salida_btn['state'] = 'normal'
        self.nombre_btn['state'] = 'normal'

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        # Si es un ejecutable compilado, no necesitamos ocultar la consola
        root = tk.Tk()
        app = Application(master=root)
        app.mainloop()
    else:
        # Si se ejecuta como script, ocultamos la consola en Windows
        if sys.platform.startswith('win'):
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        root = tk.Tk()
        app = Application(master=root)
        app.mainloop()