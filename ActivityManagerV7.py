#Cronometro corregido en este proyecto

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, filedialog
import time
import winsound
import threading
import os
import io
import matplotlib.pyplot as plt
from reportlab.lib.utils import ImageReader
import json
import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape


DATA_FILE = os.path.join(os.path.dirname(__file__), "actividades.json")
DEFECTOS_FILE = os.path.join(os.path.dirname(__file__), "Defectos.json")

class TimeTracker:
    def __init__(self, root):
        self.root = root
        self.zafkiel_mode = False
        self.alarm_triggered = False
        self.root.title("Seguimiento de Actividades")
        self.root.geometry("750x550")
        self.allow_comment_choice = False
        
        self.alarm_window = None
        self.alarm_playing = False
        self.alarm_thread = None
        self.alarm_start_time = None
        
        # Guardar la hora de inicio de la aplicación para calcular un timestamp robusto
        self.app_start_time = time.time()
        self.monotonic_start = time.monotonic()
        
        # Estados
        self.running = False
        self.inactive_running = False

        # Marcas de inicio para tiempos activo/inactivo
        self.start_time = 0
        self.inactive_start = None  # None indica que no se inició inactividad

        # Acumuladores en segundos
        self.active_seconds = 0
        self.inactive_seconds = 0
        
        self.extra_running = False
        self.extra_start = None
        self.extra_seconds = 0
        
        # Datos de la actividad
        self.activity = ""
        self.comment = ""
        self.project = ""
        self.stop_timestamp = ""         # Timestamp cuando se presiona "Detener"
        self.creation_timestamp = ""     # Timestamp de creación de la actividad
        self.comment_timing = ""         # "inicio" o "final"
        
        self.ensure_data_file()
        self.ensure_defectos_file()
        
        # Reloj actual
        self.label_clock = tk.Label(root, text="00:00:00", font=("Arial", 20))
        self.update_clock()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Texto "LA HORA ES:"
        self.label_time_text = tk.Label(root, text="LA HORA ES:", font=("Arial", 12, "bold"), fg="white", bg="black")
        self.label_time_text.pack(fill='x')
        self.label_clock.pack()

        # Separador
        separator_1 = tk.Label(root, text="", height=2)
        separator_1.pack()

        # Contenedores de tiempo
        frame_timers = tk.Frame(root)
        frame_timers.pack()
        
        # Tiempo en activo
        self.label_active_title = tk.Label(frame_timers, text="Tiempo en activo", font=("Arial", 12))
        self.label_active_title.grid(row=0, column=0, padx=10)
        self.label_timer = tk.Label(frame_timers, text="00:00:00", font=("Arial", 16))
        self.label_timer.grid(row=1, column=0, padx=10)
        
        # Tiempo de inactividad
        self.label_inactive_title = tk.Label(frame_timers, text="Tiempo Inactividad", font=("Arial", 12))
        self.label_inactive_title.grid(row=0, column=1, padx=10)
        self.label_inactive_timer = tk.Label(frame_timers, text="00:00:00", font=("Arial", 16))
        self.label_inactive_timer.grid(row=1, column=1, padx=10)
        
        self.label_extra_title = tk.Label(frame_timers, text="Tiempo Extra", font=("Arial", 12))
        self.label_extra_title.grid(row=0, column=2, padx=10)
        self.label_extra_timer = tk.Label(frame_timers, text="00:00:00", font=("Arial", 16))
        self.label_extra_timer.grid(row=1, column=2, padx=10)

        # Separador
        separator_2 = tk.Label(root, text="", height=2)
        separator_2.pack()
        
        # Nuevo frame para mostrar el proyecto actual (ocupando toda la fila)
        project_frame = tk.Frame(root)
        project_frame.pack(fill="x", pady=5)
        # Encabezado sin el estilo especial
        tk.Label(
            project_frame, 
            text="PROYECTO ACTUAL", 
            font=("Arial", 12, "bold")
        ).pack(fill="x")
        # Label con el nombre del proyecto, con fondo negro, texto blanco y ajuste del texto
        self.label_current_project = tk.Label(
            project_frame,
            text=(self.project if self.project else "No seleccionado"),
            font=("Arial", 12, "bold"),
            bg="black",
            fg="white",
            wraplength=600  # Ajusta este valor según el ancho deseado
        )
        self.label_current_project.pack(fill="x")
        
        # Agregar un frame para mostrar "ALUMNO" y "PROFESOR" con sus áreas de entrada
        info_frame = tk.Frame(project_frame)
        info_frame.pack(fill="x", padx=10, pady=(20,5))

        label_alumno = tk.Label(info_frame, text="ALUMNO", font=("Arial", 11, "bold"))
        label_alumno.grid(row=0, column=0, sticky="w", padx=(150, 0))  # 20 píxeles a la izquierda

        label_profesor = tk.Label(info_frame, text="PROFESOR", font=("Arial", 11, "bold"))
        label_profesor.grid(row=0, column=1, sticky="e", padx=(0, 130))  # 20 píxeles a la derecha

        self.alumno_entry = tk.Entry(info_frame, font=("Arial", 10, "bold"), bg="black", fg="white", justify="center")
        self.alumno_entry.grid(row=1, column=0, sticky="we", padx=40, pady=(5,0))

        self.profesor_entry = tk.Entry(info_frame, font=("Arial", 10, "bold"), bg="black", fg="white", justify="center")
        self.profesor_entry.grid(row=1, column=1, sticky="we", padx=40, pady=(5,0))

        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=1)

        # Botones
        button_frame = tk.Frame(root)
        button_frame.pack()

        # Columna 1: Proyectos
        button_col1 = tk.Frame(button_frame)
        button_col1.grid(row=0, column=0, padx=10, pady=10)
        self.button_new_project = tk.Button(button_col1, text="Nuevo Proyecto", command=self.create_project)
        self.button_new_project.pack(fill='x', pady=5)
        self.button_select_project = tk.Button(button_col1, text="Seleccionar Proyecto", command=self.select_project)
        self.button_select_project.pack(fill='x', pady=5)
        # Nuevo botón "Tabla Actividades"
        self.button_table = tk.Button(button_col1, text="Tabla Actividades", command=self.show_table)
        self.button_table.pack(fill='x', pady=5)
        
        # Nuevo botón: Guardar
        self.button_guardar = tk.Button(button_col1, text="Guardar", command=self.guardar)
        self.button_guardar.pack(fill='x', pady=5)
        
        # Columna 2: Control de tiempo
        button_col2 = tk.Frame(button_frame)
        button_col2.grid(row=0, column=1, padx=10, pady=10)
        self.button_start = tk.Button(button_col2, text="Iniciar", command=self.start_timer, state=tk.DISABLED)
        self.button_start.pack(fill='x', pady=5)
        self.button_pause = tk.Button(button_col2, text="Pausar", command=self.pause_timer, state=tk.DISABLED)
        self.button_pause.pack(fill='x', pady=5)
        self.button_stop = tk.Button(button_col2, text="Detener", command=self.stop_timer, state=tk.DISABLED)
        self.button_stop.pack(fill='x', pady=5)

        # Columna 3: Gráficas y borrado
        button_col3 = tk.Frame(button_frame)
        button_col3.grid(row=0, column=2, padx=10, pady=10)
        self.button_graph = tk.Button(button_col3, text="Mostrar Gráfico", command=self.show_graph)
        self.button_graph.pack(fill='x', pady=5)
        self.button_clear = tk.Button(button_col3, text="Borrar Datos", command=self.clear_data)
        self.button_clear.pack(fill='x', pady=5)
        self.button_pdf = tk.Button(button_col3, text="PDF", command=self.export_table_to_pdf)
        self.button_pdf.pack(fill='x', pady=5)
        self.button_formulario = tk.Button(button_col3, text="Formulario", command=self.formulario)
        self.button_formulario.pack(fill='x', pady=5)
        self.button_formulario.config(state=tk.DISABLED)  # Desactivado inicialmente

        # Separador final
        separator_3 = tk.Label(root, text="", height=2)
        separator_3.pack()
        
        # Nuevo frame para el footer que contendrá la etiqueta y el checkbutton
        footer_frame = tk.Frame(root)
        footer_frame.pack(side="bottom", fill="x", padx=10, pady=5)

        # Etiqueta en el lado izquierdo del footer
        footer_label = tk.Label(footer_frame, text="Activity Manager v.0.9.9", font=("Arial", 10, "bold"), fg="black", cursor="hand2")
        footer_label.pack(side="left")
        
        # Checkbutton en el lado derecho para "Always on Top"
        self.top_var = tk.BooleanVar(value=False)
        top_check = tk.Checkbutton(footer_frame, text="Top", variable=self.top_var, command=self.toggle_top)
        top_check.pack(side="right")
        
        # Luego, en la función que maneja el click de la etiqueta:
        def on_footer_label_click(event):
            user_input = simpledialog.askstring("Texto", "¿Que es lo que necesitas?")
            if not user_input:
                return
            if user_input == "Chaos control":
                self.comment = "ACCELERATE_ALARM"
                messagebox.showinfo("Comando", "The ultimate power")
            elif user_input == "The world":
                self.comment = "ACCELERATE_ALARM"
                messagebox.showinfo("Comando", "Control de tiempo activado.")
            elif user_input == "Kaguya":
                self.allow_comment_choice = True
                messagebox.showinfo("Comando", "El Re'em") # Opción de ingreso de comentarios habilitada
            elif user_input == "Yuzuru":
                self.allow_comment_choice = False
                messagebox.showinfo("Comando", "El Na'ash") # Opción de ingreso de comentarios deshabilitada
            elif user_input == "Zafkiel":
                self.zafkiel_mode = True
                messagebox.showinfo("Comando", "Yud Bet")
            # Si no coincide con ninguna, no se realiza ninguna acción.
        # Y asegúrate de que se haga el bind del evento:
        footer_label.bind("<Button-1>", on_footer_label_click)

        self.update_clock()

    def formulario(self):
        # Si la ventana ya existe, se eleva (lift) y no se crea otra
        if hasattr(self, "formulario_window") and self.formulario_window is not None:
            self.formulario_window.lift()
            return

        self.formulario_window = tk.Toplevel(self.root)
        self.formulario_window.title("Formulario")
        self.formulario_window.resizable(False, False)
        # Ensanchar la ventana (por ejemplo, 800px de ancho y 400px de alto)
        self.formulario_window.geometry("800x400")

        # Frame contenedor con borde negro, pegado al borde superior e izquierdo
        border_frame = tk.Frame(self.formulario_window, bd=2, relief="solid")
        border_frame.pack(anchor="nw", padx=20, pady=(0,20))

        # Título centrado
        title_label = tk.Label(border_frame, text="TIPOS DE DEFECTOS", font=("Arial", 12, "bold"))
        title_label.pack(pady=10)

        # Frame para las dos columnas, centrado
        columns_frame = tk.Frame(border_frame)
        columns_frame.pack(padx=10, pady=10)

        # Columna 1
        col1 = tk.Frame(columns_frame)
        col1.pack(side="left", padx=20, pady=5)
        defects_col1 = [
            "-10 Documentación",
            "-20 Sintaxis",
            "-30 Construcción, Empacar",
            "-40 Asignación",
            "-50 Interfaz"
        ]
        for item in defects_col1:
            tk.Label(col1, text=item, font=("Arial", 10), anchor="w").pack(pady=1, fill="x")

        # Columna 2
        col2 = tk.Frame(columns_frame)
        col2.pack(side="left", padx=20, pady=5)
        defects_col2 = [
            "-60 Chequeo",
            "-70 Datos",
            "-80 Función",
            "-90 Sistema",
            "-100 Ambiente"
        ]
        for item in defects_col2:
            tk.Label(col2, text=item, font=("Arial", 10), anchor="w").pack(pady=1, fill="x")
            
            # Debajo del recuadro negro, se inserta el siguiente texto centrado
        tk.Label(self.formulario_window, 
                text="FORMATO DEL REGISTRO DE DEFECTOS", 
                font=("Arial", 12, "bold"),
                anchor="center").pack(fill="x", pady=(10,0))

        # Debajo del recuadro, se crea un frame extra para mostrar la información del proyecto
        extra_info_frame = tk.Frame(self.formulario_window)
        extra_info_frame.pack(anchor="w", padx=20, pady=(10,0))

        # Se crean dos columnas: izquierda y derecha
        left_frame = tk.Frame(extra_info_frame)
        left_frame.pack(side="left", anchor="w")

        right_frame = tk.Frame(extra_info_frame)
        right_frame.pack(side="left", anchor="w", padx=(50,0))  # Se agrega un poco de espacio horizontal entre ambas

        data = self.load_data()
        if self.project in data:
            alumno_val = data[self.project].get("Alumno", "")
            profesor_val = data[self.project].get("Profesor", "")
        else:
            alumno_val = ""
            profesor_val = ""
            
        # Columna izquierda: Estudiante e Instructor
        est_frame = tk.Frame(left_frame)
        est_frame.pack(anchor="w", fill="x")
        tk.Label(est_frame, text="ESTUDIANTE: ", font=("Arial", 10), anchor="w").pack(side="left")
        tk.Label(est_frame, text=alumno_val, font=("Arial", 10, "underline"), anchor="w").pack(side="left")

        inst_frame = tk.Frame(left_frame)
        inst_frame.pack(anchor="w", fill="x")
        tk.Label(inst_frame, text="INSTRUCTOR: ", font=("Arial", 10), anchor="w").pack(side="left")
        tk.Label(inst_frame, text=profesor_val, font=("Arial", 10, "underline"), anchor="w").pack(side="left")

        # Columna derecha: Fecha y Programa #
        fecha_val = datetime.datetime.now().strftime("%d/%m/%Y")
        program_val = ""  # Aquí asigna el valor de "PROGRAMA #" si lo tienes.
        fecha_frame = tk.Frame(right_frame)
        fecha_frame.pack(anchor="w", fill="x")
        tk.Label(fecha_frame, text="FECHA: ", font=("Arial", 10), anchor="w").pack(side="left")
        tk.Label(fecha_frame, text=fecha_val, font=("Arial", 10, "underline"), anchor="w").pack(side="left")

        prog_frame = tk.Frame(right_frame)
        prog_frame.pack(anchor="w", fill="x")
        tk.Label(prog_frame, text="PROGRAMA #: ", font=("Arial", 10), anchor="w").pack(side="left")
        tk.Label(prog_frame, text=program_val, font=("Arial", 10, "underline"), anchor="w").pack(side="left")




        # Asegurarse de que al cerrar la ventana se borre la referencia
        self.formulario_window.protocol("WM_DELETE_WINDOW", self.close_formulario)

    def close_formulario(self):
        if hasattr(self, "formulario_window") and self.formulario_window is not None:
            self.formulario_window.destroy()
            self.formulario_window = None


    def guardar(self):
        # Evita que se abran múltiples ventanas
        if hasattr(self, "guardar_window") and self.guardar_window is not None:
            self.guardar_window.lift()
            return

        self.guardar_window = tk.Toplevel(self.root)
        self.guardar_window.title("Opciones de guardado")
        tk.Label(
            self.guardar_window,
            text="¿Qué desea hacer con los datos ingresados en 'ALUMNO' y 'PROFESOR'?",
            font=("Arial", 10, "bold")
        ).pack(padx=10, pady=10)

        btn_frame = tk.Frame(self.guardar_window)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="BLOQUEAR", command=self.opcion_guardar).pack(side="left", padx=5)
        tk.Button(btn_frame, text="EDITAR", command=self.opcion_editar).pack(side="left", padx=5)

        self.guardar_window.protocol("WM_DELETE_WINDOW", self.cerrar_guardar_window)

    def opcion_guardar(self):
        # Acción para BLOQUEAR, por ejemplo, guardar en Actividades.json
        messagebox.showinfo("Bloquear", "Datos guardados correctamente en Actividades.json.")
        
        # Al presionar BLOQUEAR, se almacenan los datos de las cajas de texto dentro del proyecto actual en actividades.json
        data = self.load_data()  # Recupera los datos existentes
        if self.project not in data:
            data[self.project] = {}
        
        data[self.project]["Alumno"] = self.alumno_entry.get()
        data[self.project]["Profesor"] = self.profesor_entry.get()
        
        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False)
        
        # Deshabilitar los campos para que no se puedan editar
        self.alumno_entry.config(state=tk.DISABLED)
        self.profesor_entry.config(state=tk.DISABLED)
        
        self.cerrar_guardar_window()


    def ensure_defectos_file(self):
        if not os.path.exists(DEFECTOS_FILE):
            with open(DEFECTOS_FILE, "w", encoding="utf-8") as file:
                json.dump({}, file, ensure_ascii=False)
    
    def load_defectos(self):
        if os.path.exists(DEFECTOS_FILE):
            with open(DEFECTOS_FILE, "r", encoding="utf-8") as file:
                try:
                    return json.load(file)
                except json.JSONDecodeError:
                    return {}
        return {}

    def opcion_editar(self):
        # Habilitar nuevamente la edición de los campos
        self.alumno_entry.config(state=tk.NORMAL)
        self.profesor_entry.config(state=tk.NORMAL)
        
        messagebox.showinfo("Editar", "Modo edición activado.")
        self.cerrar_guardar_window()

    def cerrar_guardar_window(self):
        if hasattr(self, "guardar_window") and self.guardar_window is not None:
            self.guardar_window.destroy()
            self.guardar_window = None


    def toggle_top(self):
        self.root.attributes("-topmost", self.top_var.get())

    def ensure_data_file(self):
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", encoding="utf-8") as file:
                json.dump({}, file, ensure_ascii=False)
    
    def update_clock(self):
        try:
            if not self.root.winfo_exists():
                return
            now = time.strftime("%I:%M:%S %p")
            self.label_clock.config(text=now)
            self.root.after(1000, self.update_clock)
        except tk.TclError:
            # La ventana se pudo haber destruido; ignorar el error
            pass
        
    def on_close(self):
        self.root.quit()
        self.root.destroy()
    
    def create_project(self):
        project_name = simpledialog.askstring("Nuevo Proyecto", "Ingrese el nombre del proyecto:")
        if project_name:
            data = self.load_data()
            if project_name not in data:
                data[project_name] = {}
                with open(DATA_FILE, "w", encoding="utf-8") as file:
                    json.dump(data, file, ensure_ascii=False)
                messagebox.showinfo("Proyecto Creado", f"Proyecto '{project_name}' creado con éxito.")
            self.project = project_name
            self.button_start.config(state=tk.NORMAL)
    
    def select_project(self):
        data = self.load_data()
        if not data:
            messagebox.showinfo("Error", "No hay proyectos disponibles.")
            return
        
        project_names = list(data.keys())
        if not project_names:
            messagebox.showinfo("Error", "No hay proyectos disponibles para seleccionar.")
            return
        
        select_window = tk.Toplevel(self.root)
        select_window.title("Seleccionar Proyecto")
        tk.Label(select_window, text="Seleccione un Proyecto:").pack(pady=5)
        
        project_var = tk.StringVar(select_window)
        project_combobox = ttk.Combobox(select_window, textvariable=project_var, values=project_names, state="readonly")
        project_combobox.pack(pady=5)
        project_combobox.current(0)
        
        def confirm_selection():
            self.project = project_var.get()
            self.label_current_project.config(text=self.project)  # Actualizar el nombre del proyecto en la GUI
            self.button_start.config(state=tk.NORMAL)

            # Activar el botón "Formulario" (y otros, si lo deseas)
            self.button_formulario.config(state=tk.NORMAL)

            # Cargar los datos de "Alumno" y "Profesor" para el proyecto seleccionado
            data = self.load_data()
            if self.project in data:
                alumno = data[self.project].get("Alumno", "")
                profesor = data[self.project].get("Profesor", "")
                # Habilitamos brevemente las cajas para actualizar su contenido
                self.alumno_entry.config(state=tk.NORMAL)
                self.alumno_entry.delete(0, tk.END)
                self.alumno_entry.insert(0, alumno)
                self.alumno_entry.config(state=tk.DISABLED)
                
                self.profesor_entry.config(state=tk.NORMAL)
                self.profesor_entry.delete(0, tk.END)
                self.profesor_entry.insert(0, profesor)
                self.profesor_entry.config(state=tk.DISABLED)
            
            messagebox.showinfo("Proyecto Seleccionado", f"Proyecto '{self.project}' seleccionado.")
            select_window.destroy()
        
        tk.Button(select_window, text="Seleccionar", command=confirm_selection).pack(pady=5)
    
    def start_timer(self):
        if not self.project:
            messagebox.showinfo("Error", "Seleccione o cree un proyecto primero.")
            return
        # Se abre el diálogo para seleccionar la actividad.
        self.open_activity_selection_dialog()
    
    def open_activity_selection_dialog(self):
        activity_window = tk.Toplevel(self.root)
        activity_window.title("Seleccionar Actividad")
        tk.Label(activity_window, text="Seleccione la actividad:").pack(pady=5)
        activities = ["Planificación", "Análisis", "Codificación", "Pruebas", "Lanzamiento", "Revisión", "Revisión de Código", "Diagramar", "Reunión"]
        activity_var = tk.StringVar(activity_window)
        activity_combobox = ttk.Combobox(activity_window, textvariable=activity_var, values=activities, state="readonly")
        activity_combobox.pack(pady=5)
        activity_combobox.current(0)
        
        def accept_activity():
            self.activity = activity_var.get()
            activity_window.destroy()
            # Si la opción está habilitada, preguntamos al usuario;
            # de lo contrario, se fija la opción por defecto ("final")
            if self.allow_comment_choice:
                if messagebox.askyesno("Comentarios", "¿Desea añadir comentarios al inicio?"):
                    self.comment_timing = "inicio"
                    self.open_comment_dialog()
                    return
                else:
                    self.comment_timing = "final"
            else:
                self.comment_timing = "final"
            # Se registra inmediatamente el timestamp de creación y se inicia el contador
            self.creation_timestamp = datetime.datetime.now().isoformat()
            self.running = True
            self.inactive_running = False
            self.start_time = time.monotonic()
            self.inactive_start = None
            self.update_timer()
            self.button_start.config(state=tk.DISABLED)
            self.button_pause.config(state=tk.NORMAL)
            self.button_stop.config(state=tk.NORMAL)
        tk.Button(activity_window, text="Aceptar", command=accept_activity).pack(pady=5)
    
    def open_comment_dialog(self):
        comment_window = tk.Toplevel(self.root)
        comment_window.title("Añadir Comentario")
        tk.Label(comment_window, text="Ingrese comentario:").pack(pady=5)
        comment_text = tk.Text(comment_window, width=50, height=10)
        comment_text.pack(pady=5)
        
        def confirm_comment():
            comment = comment_text.get("1.0", tk.END).strip()
            if not comment:
                messagebox.showwarning("Advertencia", "El comentario es obligatorio")
                return
            self.comment = comment
            comment_window.destroy()
            # Si se añaden comentarios al inicio, se registra el timestamp de creación al confirmar
            if self.comment_timing == "inicio":
                self.creation_timestamp = datetime.datetime.now().isoformat()
                self.running = True
                self.inactive_running = False
                self.start_time = time.monotonic()
                self.inactive_start = None
                self.update_timer()
                self.button_start.config(state=tk.DISABLED)
                self.button_pause.config(state=tk.NORMAL)
                self.button_stop.config(state=tk.NORMAL)
        
        tk.Button(comment_window, text="Confirmar", command=confirm_comment).pack(pady=5)
    
    def open_comment_dialog_final(self):
        comment_window = tk.Toplevel(self.root)
        comment_window.title("Añadir Comentario Final")
        tk.Label(comment_window, text="Ingrese comentario:").pack(pady=5)
        comment_text = tk.Text(comment_window, width=50, height=10)
        comment_text.pack(pady=5)
        
        def confirm_comment_final():
            comment = comment_text.get("1.0", tk.END).strip()
            if not comment:
                messagebox.showwarning("Advertencia", "El comentario es obligatorio")
                return
            self.comment = comment
            comment_window.destroy()
            self.save_activity()
            self.reset_timers()
        
        tk.Button(comment_window, text="Confirmar", command=confirm_comment_final).pack(pady=5)
    
    # Modified update_timer
    def update_timer(self):
        # Verificar que la ventana siga activa
        if not self.root.winfo_exists():
            return
        if self.running:
            elapsed = int(time.monotonic() - self.start_time)
            if self.zafkiel_mode:
                elapsed *= 360  # Incrementa de 10 en 10 segundos
            total_active = self.active_seconds + elapsed
            if self.comment == "ACCELERATE_ALARM" and 60 <= total_active < 3600:
                total_active = 3600
            hrs, rem = divmod(total_active, 3600)
            mins, secs = divmod(total_active, 60)
            self.label_timer.config(text=f"{hrs:02d}:{mins:02d}:{secs:02d}")

            # Si se llega o sobrepasa 60 minutos y aún no se activó la alarma:
            if total_active >= 3600 and not self.alarm_triggered:
                # Asegurarse de que se registre exactamente 3600 segundos como tiempo en activo
                needed = 3600 - self.active_seconds
                if needed < 0:
                    needed = 0
                self.active_seconds += needed
                self.label_timer.config(text="01:00:00")
                self.alarm_triggered = True
                self.running = False
                self.start_alarm()
                # Iniciar el contador extra sin acumulado predeterminado
                self.extra_seconds = 0
                self.extra_start = time.monotonic()
                self.extra_running = True
                self.update_extra_timer()
            else:
                self.root.after(1000, self.update_timer)

    def update_extra_timer(self):
        # Actualiza el contador "Extra" mientras la alarma ha sido activada
        if not self.root.winfo_exists():
            return
        if self.extra_running and self.extra_start is not None:
            elapsed = int(time.monotonic() - self.extra_start)
            if self.zafkiel_mode:
                elapsed *= 360  # Ajuste en modo Zafkiel
            total_extra = self.extra_seconds + elapsed
            hrs, rem = divmod(total_extra, 3600)
            mins, secs = divmod(rem, 60)  # Ahora se usa el residuo para calcular minutos y segundos
            self.label_extra_timer.config(text=f"{hrs:02d}:{mins:02d}:{secs:02d}")
            self.root.after(1000, self.update_extra_timer)

    def start_alarm(self):
        # Crear ventana de alarma si no existe
        if self.alarm_window is None or not tk.Toplevel.winfo_exists(self.alarm_window):
            self.alarm_window = tk.Toplevel(self.root)
            self.alarm_window.title("Alarma")
            tk.Label(self.alarm_window, text="¡60 minutos alcanzados!", font=("Arial", 14)).pack(padx=20, pady=20)
            tk.Button(self.alarm_window, text="Cerrar Alarma", command=self.stop_alarm).pack(pady=10)
            self.alarm_window.protocol("WM_DELETE_WINDOW", self.stop_alarm)
            # Iniciar sonido de alarma en bucle (usa sonido del sistema)
            import winsound
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_LOOP | winsound.SND_ASYNC)

    def stop_alarm(self):
        # Detener el sonido de alarma y cerrar la ventana
        import winsound
        winsound.PlaySound(None, winsound.SND_PURGE)
        if self.alarm_window is not None:
            self.alarm_window.destroy()
            self.alarm_window = None

    def update_inactive_timer(self):
        if not self.root.winfo_exists():
            return
        if self.inactive_running and self.inactive_start is not None:
            elapsed = int(time.monotonic() - self.inactive_start)
            if self.zafkiel_mode:
                elapsed *= 360  # Se aplica el factor Zafkiel en inactividad
            total_inactive = self.inactive_seconds + elapsed
            hrs, rem = divmod(total_inactive, 3600)
            mins, secs = divmod(total_inactive, 60)
            self.label_inactive_timer.config(text=f"{hrs:02d}:{mins:02d}:{secs:02d}")
            self.root.after(1000, self.update_inactive_timer)
    
    def pause_timer(self):
        # Si la alarma se activó, alterna entre el contador extra y el inactivo
        if self.alarm_triggered:
            if self.extra_running:
                elapsed = int(time.monotonic() - self.extra_start)
                if self.zafkiel_mode:
                    elapsed *= 360  # Factor Zafkiel para tiempo extra
                self.extra_seconds += elapsed
                self.extra_running = False
                # Inicia el contador de inactividad
                self.inactive_running = True
                self.inactive_start = time.monotonic()
                self.update_inactive_timer()
            elif self.inactive_running:
                elapsed = int(time.monotonic() - self.inactive_start)
                if self.zafkiel_mode:
                    elapsed *= 10
                self.inactive_seconds += elapsed
                self.inactive_running = False
                # Reanuda el tiempo extra sin reiniciar el acumulado previo
                self.extra_start = time.monotonic()
                self.extra_running = True
                self.update_extra_timer()
            else:
                # Si ninguno está corriendo, reanuda el contador extra
                self.extra_start = time.monotonic()
                self.extra_running = True
                self.update_extra_timer()
        else:
            # Comportamiento normal cuando aún no se activa la alarma
            if self.running:
                self.running = False
                elapsed = int(time.monotonic() - self.start_time)
                if self.zafkiel_mode:
                    elapsed *= 360  # <--- Cambia aquí de 10 a 360 para el tiempo activo
                self.active_seconds += elapsed
                self.inactive_running = True
                self.inactive_start = time.monotonic()
                self.update_inactive_timer()
            else:
                if self.inactive_start is not None:
                    elapsed = int(time.monotonic() - self.inactive_start)
                    if self.zafkiel_mode:
                        elapsed *= 360  # Se aplica el factor Zafkiel en inactividad
                    self.inactive_seconds += elapsed
                self.inactive_running = False
                self.inactive_start = None
                self.running = True
                self.start_time = time.monotonic()
                self.update_timer()
    
    # Modified stop_timer
    def stop_timer(self):
        if not self.activity:
            return

        # Actualizar el tiempo pendiente de acumulación en cada contador
        if self.running and self.start_time:
            elapsed = int(time.monotonic() - self.start_time)
            if self.zafkiel_mode:
                elapsed *= 360  # Se aplica el mismo factor que en update_timer
            self.active_seconds += elapsed
            self.running = False

        if self.inactive_running and self.inactive_start is not None:
            elapsed = int(time.monotonic() - self.inactive_start)
            if self.zafkiel_mode:
                elapsed *= 360  # Se aplica el factor Zafkiel en inactividad
            self.inactive_seconds += elapsed
            self.inactive_running = False

        if self.extra_running and self.extra_start is not None:
            elapsed = int(time.monotonic() - self.extra_start)
            if self.zafkiel_mode:
                elapsed *= 360  # Factor correspondiente para tiempo extra
            self.extra_seconds += elapsed
            self.extra_running = False

        # Timestamp del botón "Detener"
        self.stop_timestamp = datetime.datetime.now().isoformat()

        # Procede según el tiempo de comentario (inicio o final)
        if self.comment_timing == "final":
            self.open_comment_dialog_final()
        else:
            self.save_activity()
            self.reset_timers()

        # Reiniciar la bandera de alarma
        self.alarm_triggered = False
    
    def reset_timers(self):
        self.active_seconds = 0
        self.inactive_seconds = 0
        self.extra_seconds = 0      # Reiniciar contador extra
        self.inactive_start = None
        self.extra_start = None      # Reiniciar inicio extra
        self.label_timer.config(text="00:00:00")
        self.label_inactive_timer.config(text="00:00:00")
        self.label_extra_timer.config(text="00:00:00")  # Actualizar etiqueta de tiempo extra
        self.button_start.config(state=tk.NORMAL)
        self.button_pause.config(state=tk.DISABLED)
        self.button_stop.config(state=tk.DISABLED)
        self.activity = ""
        self.comment = ""
    
    def save_activity(self):
        data = self.load_data()
        if self.project not in data:
            data[self.project] = {}

        # Crear una clave única combinando la actividad y el timestamp de creación
        unique_key = f"{self.activity}_{self.creation_timestamp}"
        
        # Convertir los segundos acumulados a minutos usando redondeo
        active_minutes = int(round(self.active_seconds / 60))
        extra_minutes = int(round(self.extra_seconds / 60))
        total_minutes = int(round((self.active_seconds + self.extra_seconds) / 60))
        inactive_minutes = int(round(self.inactive_seconds / 60))

        data[self.project][unique_key] = {
            "actividad": self.activity,
            "activo": active_minutes,      # Tiempo en activo sin tiempo extra
            "extra": extra_minutes,        # Tiempo extra acumulado (minutos)
            "total": total_minutes,        # Suma de tiempo activo y extra (minutos)
            "inactivo": inactive_minutes,
            "timestamp": self.creation_timestamp,
            "comentario": self.comment,
            "timestamp_detener": self.stop_timestamp
        }
        
        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False)
    
    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as file:
                try:
                    return json.load(file)
                except json.JSONDecodeError:
                    return {}
        return {}
    
    def show_graph(self):
        data = self.load_data()
        if not data:
            messagebox.showinfo("Error", "No hay datos para mostrar.")
            return
        if not self.project:
            messagebox.showinfo("Error", "No ha seleccionado ningún proyecto.")
            return

        # Agrupar actividades por el campo "actividad"
        project_data = data[self.project]
        grupos = {}
        total_active_time = 0
        total_inactive_time = 0

        for key, detalles in project_data.items():
            act = detalles.get("actividad", "Desconocido")
            activo = detalles.get("activo", 0) + detalles.get("extra", 0)
            inactivo = detalles.get("inactivo", 0)
            if act in grupos:
                grupos[act]["activo"] += activo
                grupos[act]["inactivo"] += inactivo
            else:
                grupos[act] = {"activo": activo, "inactivo": inactivo}
            total_active_time += activo
            total_inactive_time += inactivo

        labels = list(grupos.keys())
        active_times = [grupos[act]["activo"] for act in labels]
        inactive_times = [grupos[act]["inactivo"] for act in labels]
        
        x = range(len(labels))
        graph_window = tk.Toplevel(self.root)
        graph_window.title("Gráficas de Actividades")
        
        notebook = ttk.Notebook(graph_window)
        notebook.pack(fill='both', expand=True)
        
        # Gráfica de barras
        bar_frame = tk.Frame(notebook)
        notebook.add(bar_frame, text="Gráfica de Barras")
        fig, ax1 = plt.subplots(figsize=(8, 6))
        bar_width = 0.35
        ax1.bar([p - bar_width/2 for p in x], active_times, width=bar_width, label="Activo", align="center")
        ax1.bar([p + bar_width/2 for p in x], inactive_times, width=bar_width, label="Inactivo", align="center")
        max_bar_height = max([a + i for a, i in zip(active_times, inactive_times)]) if (active_times or inactive_times) else 5
        ax1.set_ylim(0, max_bar_height + 5)
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, rotation=45, ha="right")
        ax1.set_ylabel("Minutos")
        ax1.legend()
        plt.subplots_adjust(bottom=0.3)  # Ajusta este valor según la longitud de las etiquetas
        canvas = FigureCanvasTkAgg(fig, master=bar_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Gráfica de pastel
        pie_frame = tk.Frame(notebook)
        notebook.add(pie_frame, text="Gráfica de Pastel")
        total_time = total_active_time + total_inactive_time
        if total_time == 0:
            tk.Label(pie_frame, text="No hay datos suficientes para mostrar la gráfica de pastel.", font=("Arial", 12)).pack(pady=10)
        else:
            pie_container = tk.Frame(pie_frame)
            pie_container.pack(fill="both", expand=True)
            pie_chart_frame = tk.Frame(pie_container)
            pie_chart_frame.pack(side="left", fill="both", expand=True)
            total_time_frame = tk.Frame(pie_container)
            total_time_frame.pack(side="right", padx=20, pady=10)
            fig2, ax2 = plt.subplots(figsize=(6, 6))
            labels_pie = ["Tiempo Activo", "Tiempo Inactivo"]
            sizes_pie = [total_active_time, total_inactive_time]
            ax2.pie(sizes_pie, labels=labels_pie, autopct='%1.1f%%', startangle=90, colors=["#66b3ff", "#ff6666"])
            ax2.axis("equal")
            canvas2 = FigureCanvasTkAgg(fig2, master=pie_chart_frame)
            canvas2.draw()
            canvas2.get_tk_widget().pack(fill='both', expand=True)
            total_time_label_1 = tk.Label(total_time_frame, text=f"Tiempo Total Activo: {total_active_time} minutos", font=('Arial', 12))
            total_time_label_1.pack(pady=5)
            total_time_label_2 = tk.Label(total_time_frame, text=f"Tiempo Total Inactivo: {total_inactive_time} minutos", font=('Arial', 12))
            total_time_label_2.pack(pady=5)
        plt.tight_layout()
    
    def show_table(self):
        if not self.project:
            messagebox.showinfo("Error", "No ha seleccionado ningún proyecto.")
            return
        data = self.load_data()
        if self.project not in data or not data[self.project]:
            messagebox.showinfo("Info", "No hay actividades registradas para este proyecto.")
            return

        table_window = tk.Toplevel(self.root)
        self.table_window = table_window
        table_window.title(f"Tabla Actividades - {self.project}")
        table_window.protocol("WM_DELETE_WINDOW", self.on_table_window_close)
        
        tree_frame = tk.Frame(table_window)
        tree_frame.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(tree_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        
        # Configuración del estilo para el encabezado
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview.Heading",
                        font=("Arial", 11, "bold"),
                        foreground="white",
                        background="black")
        style.map("Treeview.Heading", background=[("active", "black")])

        columns = ("Fecha", "Inicio", "Fin", "Interrupción", "A tiempo", "Actividad", "Comentarios")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)
        scrollbar.config(command=tree.yview)
        for col in columns:
            tree.heading(col, text=col.upper(), anchor=tk.CENTER)
            tree.column(col, anchor=tk.CENTER)
        tree.pack(fill="both", expand=True)
        
        project_data = data[self.project]
        for key, detalles in project_data.items():
            # Omitir claves que no sean diccionarios (como "Alumno" y "Profesor")
            if key in ("Alumno", "Profesor") or not isinstance(detalles, dict):
                continue

            creation_ts = detalles.get("timestamp", "")
            try:
                creation_dt = datetime.datetime.fromisoformat(creation_ts)
                dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                fecha = f"{dias[creation_dt.weekday()]}, {creation_dt.day:02d} {meses[creation_dt.month - 1]} {creation_dt.year}"
                inicio = creation_dt.strftime("%H:%M:%S")
            except Exception:
                fecha = creation_ts
                inicio = ""
            stop_ts = detalles.get("timestamp_detener", "")
            try:
                stop_dt = datetime.datetime.fromisoformat(stop_ts)
                fin = stop_dt.strftime("%H:%M:%S")
            except Exception:
                fin = stop_ts
            
            interrupcion = detalles.get("inactivo", 0)
            a_tiempo = detalles.get("activo", 0) + detalles.get("extra", 0)
            actividad = detalles.get("actividad", "")
            tree.insert("", "end", iid=key, values=(fecha, inicio, fin, interrupcion, a_tiempo, actividad, "Ver"))
        
        tree.bind("<ButtonRelease-1>", lambda event: self.on_tree_item_click(event, tree, project_data))
    
    def on_table_window_close(self):
        # Si la ventana de comentarios está abierta, se cierra
        if hasattr(self, "comment_window") and self.comment_window is not None:
            self.comment_window.destroy()
            self.comment_window = None
        # Cierra la ventana de tabla y limpia la variable de instancia
        if hasattr(self, "table_window") and self.table_window is not None:
            self.table_window.destroy()
            self.table_window = None
    
    def on_tree_item_click(self, event, tree, project_data):
        region = tree.identify("region", event.x, event.y)
        if region == "cell":
            col = tree.identify_column(event.x)
            # La columna "Comentarios" es la séptima (ej. "#7")
            if col == "#7":
                rowid = tree.identify_row(event.y)
                if rowid:
                    values = tree.item(rowid, "values")
                    # Usar el iid (unique_key) para recuperar los detalles exactos
                    comentario = project_data.get(rowid, {}).get("comentario", "")
                    actividad = project_data.get(rowid, {}).get("actividad", "")
                    self.show_comment_window(actividad, comentario)
                    
    def show_comment_window(self, actividad, comentario):
        # Si ya existe la ventana de comentarios y sigue activa, simplemente la mostramos
        if hasattr(self, "comment_window") and self.comment_window is not None:
            try:
                self.comment_window.lift()
                return
            except tk.TclError:
                # La ventana pudo haber sido destruida, continuamos
                self.comment_window = None

        self.comment_window = tk.Toplevel(self.root)
        self.comment_window.title(f"Comentarios - {actividad}")
        # Al cerrar la ventana, se libera la variable de instancia:
        self.comment_window.protocol("WM_DELETE_WINDOW", lambda: self._close_comment_window())

        tk.Label(self.comment_window, text="Comentarios:", font=("Arial", 12, "bold")).pack(pady=5)
        text_widget = tk.Text(self.comment_window, wrap="word", width=60, height=10)
        text_widget.insert("1.0", comentario)
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(padx=10, pady=10)
        tk.Button(self.comment_window, text="Cerrar", command=lambda: self._close_comment_window()).pack(pady=5)

    def _close_comment_window(self):
        if self.comment_window is not None:
            self.comment_window.destroy()
            self.comment_window = None
    
    def clear_data(self):
        # Si ya existe la ventana, la mostramos y no se crea otra.
        if hasattr(self, "clear_window") and self.clear_window is not None:
            try:
                self.clear_window.lift()
                return
            except tk.TclError:
                self.clear_window = None

        self.clear_window = tk.Toplevel(self.root)
        self.clear_window.title("Borrar Datos")
        self.clear_window.protocol("WM_DELETE_WINDOW", self._close_clear_window)
        tk.Label(self.clear_window, text="Seleccione la acción a realizar:", font=("Arial", 12, "bold")).pack(pady=10)

        def delete_all_data():
            if messagebox.askyesno("Confirmación", "¿Está seguro de que desea borrar TODOS los datos?"):
                with open(DATA_FILE, "w", encoding="utf-8") as file:
                    json.dump({}, file, ensure_ascii=False)
                messagebox.showinfo("Datos Borrados", "Todos los datos han sido borrados.")
                self.project = ""
                self.activity = ""
                self.button_start.config(state=tk.DISABLED)
            self._close_clear_window()

        def delete_project():
            data = self.load_data()
            projects = list(data.keys())
            if not projects:
                messagebox.showinfo("Información", "No hay proyectos para borrar.")
                self._close_clear_window()
                return
            project_window = tk.Toplevel(self.root)
            project_window.title("Borrar Proyecto")
            tk.Label(project_window, text="Seleccione el proyecto a borrar:", font=("Arial", 12)).pack(pady=10)
            project_var = tk.StringVar(project_window)
            project_combobox = ttk.Combobox(project_window, textvariable=project_var, values=projects, state="readonly")
            project_combobox.pack(pady=5)
            project_combobox.current(0)

            def confirm_delete_project():
                selected_project = project_var.get()
                if messagebox.askyesno("Confirmación", f"¿Está seguro de que desea borrar el proyecto '{selected_project}'?"):
                    del data[selected_project]
                    with open(DATA_FILE, "w", encoding="utf-8") as file:
                        json.dump(data, file, ensure_ascii=False)
                    messagebox.showinfo("Proyecto Borrado", f"El proyecto '{selected_project}' ha sido borrado.")
                    if self.project == selected_project:
                        self.project = ""
                        self.button_start.config(state=tk.DISABLED)
                project_window.destroy()
                self._close_clear_window()

            tk.Button(project_window, text="Borrar Proyecto", command=confirm_delete_project).pack(pady=10)

        btn_frame = tk.Frame(self.clear_window)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Borrar Todos", command=delete_all_data).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Borrar Proyecto", command=delete_project).pack(side=tk.LEFT, padx=5)
        tk.Button(self.clear_window, text="Cancelar", command=self._close_clear_window).pack(pady=5)


    def _close_clear_window(self):
        if hasattr(self, "clear_window") and self.clear_window is not None:
            self.clear_window.destroy()
            self.clear_window = None


    def export_table_to_pdf(self):
        data = self.load_data()
        if self.project not in data or not data[self.project]:
            messagebox.showinfo("Info", "No hay actividades registradas para este proyecto.")
            return

        # Permitir al usuario elegir dónde guardar el PDF y el nombre del archivo
        pdf_file = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            initialfile=f"{self.project}_tabla.pdf",
            title="Guardar PDF"
        )
        if not pdf_file:
            return

        project_data = data[self.project]
        # Obtener fecha de inicio del proyecto
        timestamps = []
        for act, detalles in project_data.items():
            ts = detalles.get("timestamp", "")
            try:
                dt = datetime.datetime.fromisoformat(ts)
                timestamps.append(dt)
            except Exception:
                continue
        if timestamps:
            min_dt = min(timestamps)
            weekday = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][min_dt.weekday()]
            month = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"][min_dt.month - 1]
            project_start = f"{weekday} {min_dt.day} de {month} de {min_dt.year}"
        else:
            project_start = "N/A"
        now = datetime.datetime.now()
        weekday_now = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][now.weekday()]
        month_now = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"][now.month - 1]
        print_date = f"{weekday_now} {now.day} de {month_now} de {now.year}"

        # Crear canvas en orientación horizontal
        c = canvas.Canvas(pdf_file, pagesize=landscape(letter))
        width, height = landscape(letter)

        # Función para dibujar el encabezado en cada página
        def draw_header(y_pos):
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(width / 2, y_pos, f"Nombre del Proyecto: {self.project}")
            y_pos -= 20
            c.setFont("Helvetica", 12)
            c.drawCentredString(width / 2, y_pos, f"Fecha de inicio del proyecto: {project_start}  -  Fecha de impresión: {print_date}")
            return y_pos - 30

        # -- Página 1: Gráfica de Barras --
        y = height - 50
        y = draw_header(y)

        # Agrupar actividades por el campo "actividad"
        grupos = {}
        for key, detalles in project_data.items():
            act = detalles.get("actividad", "Desconocido")
            activo = detalles.get("activo", 0) + detalles.get("extra", 0)
            inactivo = detalles.get("inactivo", 0)
            if act in grupos:
                grupos[act]["activo"] += activo
                grupos[act]["inactivo"] += inactivo
            else:
                grupos[act] = {"activo": activo, "inactivo": inactivo}
        labels = list(grupos.keys())
        active_times = [grupos[act]["activo"] for act in labels]
        inactive_times = [grupos[act]["inactivo"] for act in labels]

        fig, ax1 = plt.subplots(figsize=(8, 6))
        bar_width = 0.35
        x = range(len(labels))
        ax1.bar([p - bar_width / 2 for p in x], active_times, width=bar_width, label="Activo", align="center")
        ax1.bar([p + bar_width / 2 for p in x], inactive_times, width=bar_width, label="Inactivo", align="center")
        max_bar_height = max([a + i for a, i in zip(active_times, inactive_times)]) if (active_times or inactive_times) else 5
        ax1.set_ylim(0, max_bar_height + 5)
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, rotation=45)
        ax1.set_ylabel("Minutos")
        ax1.legend()
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="PNG")
        plt.close(fig)
        buf.seek(0)
        image_reader = ImageReader(buf)
        image_width = width - 100
        image_height = image_width * 0.75
        c.drawImage(image_reader, 50, y - image_height, width=image_width, height=image_height)
        c.showPage()


        # -- Página 2: Gráfica de Pastel --
        y = height - 50
        y = draw_header(y)
        # Calcular tiempos totales
        total_active_time = sum(active_times)
        total_inactive_time = sum(inactive_times)
        total_time = total_active_time + total_inactive_time

        if total_time == 0:
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(width / 2, y - 100, "No hay datos suficientes para mostrar la gráfica de pastel.")
        else:
            fig2, ax2 = plt.subplots(figsize=(6, 6))
            labels_pie = ["Tiempo Activo", "Tiempo Inactivo"]
            sizes_pie = [total_active_time, total_inactive_time]
            colors = ["#66b3ff", "#ff6666"]
            ax2.pie(sizes_pie, labels=labels_pie, autopct='%1.1f%%', startangle=90, colors=colors)
            ax2.axis("equal")
            ax2.legend(labels_pie, loc="upper right", bbox_to_anchor=(1.4, 0.5))
            plt.tight_layout()

            buf2 = io.BytesIO()
            fig2.savefig(buf2, format="PNG")
            plt.close(fig2)
            buf2.seek(0)
            image_reader2 = ImageReader(buf2)
            image_width = width - 250
            image_height = image_width
            center_x = (width - image_width) / 2
            c.drawImage(image_reader2, center_x, y - image_height, width=image_width, height=image_height)
            c.setFont("Helvetica-Bold", 12)
            text_y = y - image_height + 520
            c.drawCentredString(width / 2, text_y, f"TIEMPO TOTAL ACTIVO: {total_active_time} minutos")
            c.drawCentredString(width / 2, text_y - 20, f"TIEMPO TOTAL INACTIVO: {total_inactive_time} minutos")
        c.showPage()

        # -- Página 3 en adelante: Tabla --
        y = height - 50
        y = draw_header(y)

        # Función auxiliar para envolver texto
        def wrap_text(text, max_width, c, fontName, fontSize):
            words = text.split()
            lines = []
            current_line = ""
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                if c.stringWidth(test_line, fontName, fontSize) <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            return lines

        # Determinar anchos de columnas
        padding = 10
        c.setFont("Helvetica-Bold", 10)
        max_fecha_width = c.stringWidth("Fecha", "Helvetica-Bold", 10)
        for act, detalles in project_data.items():
            try:
                dt = datetime.datetime.fromisoformat(detalles.get("timestamp", ""))
                weekday_dt = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][dt.weekday()]
                month_dt = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"][dt.month - 1]
                fecha_temp = f"{weekday_dt} {dt.day} de {month_dt} de {dt.year}"
            except Exception:
                fecha_temp = detalles.get("timestamp", "")
            temp_width = c.stringWidth(fecha_temp, "Helvetica", 10)
            if temp_width > max_fecha_width:
                max_fecha_width = temp_width
        col0_width = max_fecha_width + padding

        fixed_width = 70
        comment_width = 200
        col6_width = comment_width
        col_widths = [col0_width] + [fixed_width] * 5 + [col6_width]
        x_positions = []
        pos = 50
        for w in col_widths:
            x_positions.append(pos)
            pos += w

        headers = ["Fecha", "Inicio", "Fin", "Interrupción", "A tiempo", "Actividad", "Comentarios"]
        row_height_default = 15
        c.setFont("Helvetica-Bold", 10)
        for i, header in enumerate(headers):
            c.setFillColorRGB(0, 0, 0)
            c.rect(x_positions[i], y - 3, col_widths[i], row_height_default, fill=1, stroke=0)
            c.setLineWidth(1)
            c.setStrokeColorRGB(0, 0, 0)
            c.setFillColorRGB(1, 1, 1)
            center_x = x_positions[i] + col_widths[i] / 2
            c.drawCentredString(center_x, y - 3 + (row_height_default / 2) - 3, header)
        y -= (row_height_default - 6)

        c.setFont("Helvetica", 10)
        line_height = 10

        for j, (actividad, detalles) in enumerate(project_data.items()):
            try:
                creation_dt = datetime.datetime.fromisoformat(detalles.get("timestamp", ""))
                weekday_dt = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][creation_dt.weekday()]
                month_dt = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"][creation_dt.month - 1]
                fecha = f"{weekday_dt} {creation_dt.day} de {month_dt} de {creation_dt.year}"
                inicio = creation_dt.strftime("%H:%M:%S")
            except Exception:
                fecha = detalles.get("timestamp", "")
                inicio = ""
            stop_ts = detalles.get("timestamp_detener", "")
            try:
                stop_dt = datetime.datetime.fromisoformat(stop_ts)
                fin = stop_dt.strftime("%H:%M:%S")
            except Exception:
                fin = stop_ts

            interrupcion = str(detalles.get("inactivo", 0))
            a_tiempo = str(detalles.get("activo", 0) + detalles.get("extra", 0))
            # Usar solo el campo "actividad" para mostrar el nombre
            real_activity = detalles.get("actividad", "")
            comment = detalles.get("comentario", "")
            comment_lines = wrap_text(comment, col_widths[6] - 4, c, "Helvetica", 10)
            num_comment_lines = max(len(comment_lines), 1)
            extra_padding = 8
            current_row_height = max(row_height_default, num_comment_lines * line_height) + extra_padding

            # Reemplazamos la variable 'actividad' por 'real_activity'
            row = [fecha, inicio, fin, interrupcion, a_tiempo, real_activity]
            for i, cell in enumerate(row):
                center_x = x_positions[i] + col_widths[i] / 2
                text_y = y - current_row_height / 2 - 3
                c.setFillColorRGB(0, 0, 0)
                c.drawCentredString(center_x, text_y, str(cell))
                c.setLineWidth(1)
                c.setStrokeColorRGB(0, 0, 0)
                if j > 0:
                    c.line(x_positions[i], y, x_positions[i] + col_widths[i], y)
                c.line(x_positions[i], y - current_row_height, x_positions[i] + col_widths[i], y - current_row_height)
            center_x_comment = x_positions[6] + col_widths[6] / 2
            total_text_height = num_comment_lines * line_height
            extra_top_margin = 5
            text_y = y - extra_top_margin - ((current_row_height - extra_padding - total_text_height) / 2 + line_height/2)

            for line in comment_lines:
                c.drawCentredString(center_x_comment, text_y, line)
                text_y -= line_height
            c.setLineWidth(1)
            c.setStrokeColorRGB(0, 0, 0)
            if j > 0:
                c.line(x_positions[6], y, x_positions[6] + col_widths[6], y)
            c.line(x_positions[6], y - current_row_height, x_positions[6] + col_widths[6], y - current_row_height)

            y -= current_row_height
            if y < 50:
                c.showPage()
                y = height - 50
                y = draw_header(y)

        c.save()
        messagebox.showinfo("PDF Exportado", f"PDF exportado exitosamente a {pdf_file}")


root = tk.Tk()
app = TimeTracker(root)
root.mainloop()
