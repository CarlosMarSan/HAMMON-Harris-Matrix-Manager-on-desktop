# Establecer el backend antes de cualquier import de pyplot
import matplotlib
matplotlib.use('TkAgg')  # Usa un backend compatible con NetGraph

# Ahora sí importa el resto
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox, Scrollbar, simpledialog, colorchooser
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import FancyArrowPatch
from matplotlib.lines import Line2D
from matplotlib import colormaps as cmaps
from collections import deque, defaultdict
import re
import unicodedata
import time
from tkinter import PhotoImage
import os
import sys

class GraphApp:
    
    def __init__(self, root):
        self.root = root
        self.root.title("HAMMON: Harris Matrix Manager on desktop")
        self.root.geometry("900x600")

        # ICONO
        # Ruta absoluta al directorio donde está el script
        if hasattr(sys, '_MEIPASS'):
            ruta_base = sys._MEIPASS  # Directorio temporal donde PyInstaller descomprime todo
        else:
            ruta_base = os.path.dirname(os.path.abspath(__file__))

        ruta_icono = os.path.join(ruta_base, "StoneMaskIcon.png")

        icon = PhotoImage(file=ruta_icono)
        root.iconphoto(True, icon)

        # Variables importantes
        # Archivo cargado
        self.uploaded_file = None
        # Base de datos
        self.BD = None
        # Treeviews - Indican qué se dibuja en el grafo/ Se les aplica filtrado
        self.relations_tab_tree = None
        self.equivalences_tab_tree = None
        self.nodes_fact_tab_tree = None
        self.facts_tab_tree = None
        self.nodes_tab_tree = None
        # Grafo que se dibuja
        self.graph = nx.DiGraph()
        # Contador para el "Codigo"
        self.code_counter = 0
        # Pilas UNDO y REDO
        self.undo_stack = []
        self.redo_stack = []
        # Variables que guardan los nodos no dibujados e indican cuándo mostrarlos
        self.not_drawn_nodes = set()
        # Variable para mostrar la leyenda
        self.show_legend_graph = False
        self.show_legend_matrix = False
        # Variable para indicar redundancia
        self.redundancy = False

        # Crear la BD
        self.upload_BD(self.graph_default())
        
        # Marco para la tabla de herramientas
        self.toolbar_container()

        # Crear los Notebook para contener las pestañas
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=7)
        self.root.columnconfigure(1, weight=2)
        frame1 = tk.Frame(self.root)
        frame2 = tk.Frame(self.root)
        frame1.grid(row=0, column=0, sticky="nsew")
        frame2.grid(row=0, column=1, sticky="nsew")

        self.create_fig_notebook(frame1)
        
        self.create_notebook(frame2)
        self.create_filter_container(frame2)

        # Actualizar BD
        self.update_all()

        # Asociar el evento de cierre de la ventana principal
        root.protocol("WM_DELETE_WINDOW", self.cerrar_ventana_principal)

    # Organización de los widgets
    
    def toolbar_container(self):

        self.menu_bar = tk.Menu(root)
        root.config(menu=self.menu_bar)

        archivo_menu = tk.Menu(self.menu_bar, tearoff=0)
        archivo_menu.add_command(label="Nuevo", command=lambda: self.new_file())
        archivo_menu.add_command(label="Cargar CSV", command=lambda: self.upload_CSV())
        archivo_menu.add_command(label="Guardar", command=lambda: self.save_csv())
        archivo_menu.add_command(label="Guardar como", command=lambda: self.download_csv())
        self.menu_bar.add_cascade(label="Archivo", menu=archivo_menu)

        self.menu_bar.add_command(label="← Undo", command=lambda: self.undo(), state="disabled")
        self.menu_bar.add_command(label="Redo →", command=lambda: self.redo(), state="disabled")
        # self.menu_bar.add_command(label="Redundancia", command=lambda: self.change_redundancy())
        self.submenu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Opciones", menu=self.submenu)
        self.submenu.add_checkbutton(label="Redundancia", variable=self.redundancy, command=lambda: self.change_redundancy())

    def create_fig_notebook(self, master_frame):
        notebook_frame = tk.Frame(master_frame)
        #notebook_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        notebook_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        self.fig_notebook = ttk.Notebook(notebook_frame)
        self.fig_notebook.pack(fill=tk.BOTH, expand=True)

        # Crear pestañas
        frame_graph = self.create_graph_tab()
        frame_matrix = self.create_matrix_tab()

        # Añadir pestañas al notebook
        self.fig_notebook.add(frame_graph, text="🏺Grafo")
        self.fig_notebook.add(frame_matrix, text="▦ Matriz")

    def create_graph_tab(self):
        frame = tk.Frame(self.fig_notebook)
        #self.frame_grafo.grid(rowspan=2, column=0, sticky="nsew")
        #frame_grafo.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        self.fig_graph, self.ax_graph = plt.subplots()
        self.ax_graph.axis('off')
        # G = nx.erdos_renyi_graph(10, 0.3)
        # nx.draw(G, ax=ax, with_labels=True, node_color='lightblue', edge_color='gray')

        self.canvas_graph = FigureCanvasTkAgg(self.fig_graph, master=frame)
        self.canvas_graph.draw()
        self.canvas_graph.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.toolbar_graph = self.Toolbar(self.canvas_graph, frame)
        show_legend_button = tk.Button(self.toolbar_graph, text="Mostrar leyenda", command=lambda: (self.toggle_button_style(show_legend_button), self.toggle_show_legend_graph()), height=1)
        show_legend_button.pack(side=tk.LEFT, padx=2, pady=2)
        self.toolbar_graph.update()
        self.toolbar_graph.pack(fill=tk.X)

        return frame
    
    def create_matrix_tab(self):
        frame = tk.Frame(self.fig_notebook)
        #self.frame_grafo.grid(rowspan=2, column=0, sticky="nsew")
        #frame_grafo.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        self.fig_matrix, self.ax_matrix = plt.subplots()
        self.ax_matrix.axis('off')
        # G = nx.erdos_renyi_graph(10, 0.3)
        # nx.draw(G, ax=ax, with_labels=True, node_color='lightblue', edge_color='gray')

        self.canvas_matrix = FigureCanvasTkAgg(self.fig_matrix, master=frame)
        self.canvas_matrix.draw()
        self.canvas_matrix.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.toolbar_matrix = self.Toolbar(self.canvas_matrix, frame)
        show_legend_button = tk.Button(self.toolbar_matrix, text="Mostrar leyenda", command=lambda: (self.toggle_button_style(show_legend_button), self.toggle_show_legend_matrix()), height=1)
        show_legend_button.pack(side=tk.LEFT, padx=2, pady=2)
        self.toolbar_matrix.update()
        self.toolbar_matrix.pack(fill=tk.X)

        return frame

    def create_notebook(self, master_frame):
        notebook_frame = tk.Frame(master_frame)
        #notebook_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        notebook_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(notebook_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Crear pestañas
        frame_relations = self.create_relations_tab(notebook)
        frame_equivalences = self.create_equivalences_tab(notebook)
        frame_facts = self.create_facts_tab(notebook)
        frame_nodes = self.create_nodes_tab(notebook)
        frame_custom = self.create_custom_tab(notebook)

        # Añadir pestañas al notebook
        notebook.add(frame_nodes, text="Unidades")
        notebook.add(frame_relations, text="Relaciones")
        notebook.add(frame_equivalences, text="Equivalencias")
        notebook.add(frame_facts, text="Hechos")
        notebook.add(frame_custom, text="Estética")

    def create_relations_tab(self, notebook):
        frame = tk.Frame(notebook, padx=10, pady=10)
        tk.Label(frame, text="RELACIONES", font=("Arial", 12, "bold")).pack()

        # Obtener lista de códigos de los nodos existentes
        nodes_codes = list(self.BD[self.BD["Tipo"].isin(["P","N"])]["Codigo"])

        # Treeview
        columns = ["Unidad 1", "Unidad 2"]
        self.relations_tab_tree = ttk.Treeview(frame, columns=columns, height=3, show="headings")
        tree_width = self.relations_tab_tree.winfo_width()
        for col in columns:
            self.relations_tab_tree.heading(col, text=col)
            self.relations_tab_tree.column(col, anchor="center", width=tree_width // len(columns))
        self.relations_tab_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame control
        control_frame = tk.Frame(frame)
        control_frame.pack(fill=tk.BOTH, padx=10, pady=10)

        # Añadir
        add_frame = tk.Frame(control_frame, highlightbackground="#000000", highlightthickness=2)
        add_button = tk.Button(add_frame, text="Añadir")
        add_button.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)
        
        self.node1_entry_rel = ttk.Combobox(add_frame, width=5, values=nodes_codes, state="readonly")
        self.node1_entry_rel.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)

        self.node2_entry_rel = ttk.Combobox(add_frame, width=5, values=nodes_codes, state="readonly")
        self.node2_entry_rel.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)

        if nodes_codes:
            self.node1_entry_rel.set(nodes_codes[0])
            self.node2_entry_rel.set(nodes_codes[0])
        else:
            self.node1_entry_rel.set('')
            self.node2_entry_rel.set('')
        
        self.node1_entry_rel.bind("<MouseWheel>", self.block_scroll)       # Windows
        self.node1_entry_rel.bind("<Button-4>", self.block_scroll)         # Linux scroll up
        self.node1_entry_rel.bind("<Button-5>", self.block_scroll)         # Linux scroll down
        self.node2_entry_rel.bind("<MouseWheel>", self.block_scroll)       # Windows
        self.node2_entry_rel.bind("<Button-4>", self.block_scroll)         # Linux scroll up
        self.node2_entry_rel.bind("<Button-5>", self.block_scroll)         # Linux scroll down

        add_button.config(command=lambda: self.add_relation())

        add_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Eliminar
        remove_frame = tk.Frame(control_frame)
        remove_button = tk.Button(remove_frame, text="Eliminar")
        remove_button.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)

        remove_button.config(command=lambda: self.delete_relations(self.relations_tab_tree.selection()))

        remove_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        return frame

    def create_equivalences_tab(self, notebook):
        frame = tk.Frame(notebook, padx=10, pady=10)
        tk.Label(frame, text="EQUIVALENCIAS", font=("Arial", 12, "bold")).pack()

        # Obtener lista de códigos de los nodos existentes
        nodes_codes = list(self.BD[self.BD["Tipo"].isin(["P","N"])]["Codigo"])
        
        # Treeview
        columns = ["Unidad 1", "Unidad 2"]
        self.equivalences_tab_tree = ttk.Treeview(frame, columns=columns, height=3, show="headings")
        tree_width = self.equivalences_tab_tree.winfo_width()
        for col in columns:
            self.equivalences_tab_tree.heading(col, text=col)
            self.equivalences_tab_tree.column(col, anchor="center", width=tree_width//len(columns))
        self.equivalences_tab_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame control
        control_frame = tk.Frame(frame)
        control_frame.pack(fill=tk.BOTH, padx=10, pady=10)

        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
        control_frame.columnconfigure(2, weight=1)
        control_frame.columnconfigure(3, weight=1)

        # Añadir
        add_frame = tk.Frame(control_frame, highlightbackground="#000000", highlightthickness=2)
        add_button = tk.Button(add_frame, text="Añadir")
        add_button.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)
        
        self.node1_entry_equi = ttk.Combobox(add_frame, width=5, values=nodes_codes, state="readonly")
        self.node1_entry_equi.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)
        
        self.node2_entry_equi = ttk.Combobox(add_frame, width=5, values=nodes_codes, state="readonly")
        self.node2_entry_equi.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)

        if nodes_codes:
            self.node1_entry_equi.set(nodes_codes[0])
            self.node2_entry_equi.set(nodes_codes[0])
        else:
            self.node1_entry_equi.set('')
            self.node2_entry_equi.set('')

        self.node1_entry_equi.bind("<MouseWheel>", self.block_scroll)       # Windows
        self.node1_entry_equi.bind("<Button-4>", self.block_scroll)         # Linux scroll up
        self.node1_entry_equi.bind("<Button-5>", self.block_scroll)         # Linux scroll down
        self.node2_entry_equi.bind("<MouseWheel>", self.block_scroll)       # Windows
        self.node2_entry_equi.bind("<Button-4>", self.block_scroll)         # Linux scroll up
        self.node2_entry_equi.bind("<Button-5>", self.block_scroll)         # Linux scroll down

        add_button.config(command=lambda: self.add_equivalence())

        add_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Eliminar
        remove_frame = tk.Frame(control_frame)
        remove_button = tk.Button(remove_frame, text="Eliminar")
        remove_button.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)

        remove_button.config(command=lambda: self.delete_equivalences(self.equivalences_tab_tree.selection()))

        remove_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        return frame

    def create_facts_tab(self, notebook):
        notebook_frame = tk.Frame(notebook)
        #notebook_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        notebook_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(notebook_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Crear pestañas
        frame_units = self.create_facts_units_tab(notebook)
        frame_grouping = self.create_facts_grouping_tab(notebook)

        # Añadir pestañas al notebook
        notebook.add(frame_units, text="Información Interna")
        notebook.add(frame_grouping, text="Agrupamiento")

        return notebook_frame

    def create_facts_units_tab(self, notebook):
        frame = tk.Frame(notebook, padx=10, pady=10)
        tk.Label(frame, text="INFORMACIÓN INTERNA", font=("Arial", 12, "bold")).pack()
        
        # Frame para el treeview el el scrollbar
        frame_tree = tk.Frame(frame)
        frame_tree.pack_propagate(False)
        frame_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Treeview
        self.nodes_fact_tab_tree = ttk.Treeview(frame_tree, columns=("Unidad 1", "Unidad 2"), height=3, show="headings")
        # self.nodes_fact_tab_tree.heading("Unidad 1", text="Unidad 1")
        # self.nodes_fact_tab_tree.heading("Unidad 2", text="Unidad 2")
        self.nodes_fact_tab_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.nodes_fact_tab_tree.bind("<Double-1>", lambda event: self.edit_node_fact())

        # Scrollbar horizontal
        h_scroll = ttk.Scrollbar(frame_tree, orient="horizontal", command=self.nodes_fact_tab_tree.xview)
        self.nodes_fact_tab_tree.configure(xscrollcommand=h_scroll.set)  # Vincular el scrollbar al treeview
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Frame control
        control_frame = tk.Frame(frame)
        control_frame.pack(fill=tk.BOTH, padx=10, pady=10)

        # Añadir
        add_button = tk.Button(control_frame, text="Añadir", command=lambda: self.add_node_fact())
        #add_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        add_button.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Eliminar
        remove_button = tk.Button(control_frame, text="Eliminar", command=lambda: self.delete_nodes_fact())
        #remove_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        remove_button.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        return frame
    
    def create_facts_grouping_tab(self, notebook):
        frame = tk.Frame(notebook, padx=10, pady=10)
        tk.Label(frame, text="AGRUPAMIENTO", font=("Arial", 12, "bold")).pack()

        # Obtener lista de códigos de los nodos existentes
        nodes_codes = list(self.BD[self.BD["Tipo"] == "H"]["Codigo"])

        # Treeview
        columns = ["Hecho", "Unidades"]
        self.facts_tab_tree = ttk.Treeview(frame, columns=columns, height=3, show="headings")
        tree_width = self.facts_tab_tree.winfo_width()
        for col in columns:
            self.facts_tab_tree.heading(col, text=col)
            self.facts_tab_tree.column(col, anchor="center", width=tree_width // len(columns))
        self.facts_tab_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame control
        control_frame = tk.Frame(frame)
        control_frame.pack(fill=tk.BOTH, padx=10, pady=10)

        # Añadir
        add_frame = tk.Frame(control_frame, highlightbackground="#000000", highlightthickness=2)
        add_button = tk.Button(add_frame, text="Añadir")
        add_button.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)

        self.node1_entry_facts = ttk.Combobox(add_frame, width=5, values=nodes_codes, state="readonly")
        self.node1_entry_facts.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)

        self.node2_entry_facts = ttk.Combobox(add_frame, width=5, values=nodes_codes, state="readonly")
        self.node2_entry_facts.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)

        if nodes_codes:
            self.node1_entry_facts.set(nodes_codes[0])
            self.node2_entry_facts.set(nodes_codes[0])
        else:
            self.node1_entry_facts.set('')
            self.node2_entry_facts.set('')
        
        self.node1_entry_facts.bind("<MouseWheel>", self.block_scroll)       # Windows
        self.node1_entry_facts.bind("<Button-4>", self.block_scroll)         # Linux scroll up
        self.node1_entry_facts.bind("<Button-5>", self.block_scroll)         # Linux scroll down
        self.node2_entry_facts.bind("<MouseWheel>", self.block_scroll)       # Windows
        self.node2_entry_facts.bind("<Button-4>", self.block_scroll)         # Linux scroll up
        self.node2_entry_facts.bind("<Button-5>", self.block_scroll)         # Linux scroll down

        add_button.config(command=lambda: self.add_fact())

        add_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Eliminar
        remove_frame = tk.Frame(control_frame)
        remove_button = tk.Button(remove_frame, text="Eliminar")
        remove_button.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)

        remove_button.config(command=lambda: self.delete_facts(self.facts_tab_tree.selection()))

        remove_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Entry
        entry_frame = tk.Frame(control_frame)
        #facts_list = list(self.BD[self.BD["Tipo"] == "H"]["Codigo"])
        button = tk.Button(entry_frame, text="Aplicar", command=lambda: self.update_all())
        button.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, pady=5)

        self.facts_entry = tk.Entry(entry_frame)
        self.facts_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, pady=5)


        entry_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        return frame

    def create_nodes_tab(self, notebook):
        frame = tk.Frame(notebook, padx=10, pady=10)
        tk.Label(frame, text="UNIDADES", font=("Arial", 12, "bold")).pack()
        
        # Frame para el treeview el el scrollbar
        frame_tree = tk.Frame(frame)
        frame_tree.pack_propagate(False)
        frame_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Treeview
        self.nodes_tab_tree = ttk.Treeview(frame_tree, columns=("Unidad 1", "Unidad 2"), height=3, show="headings")
        self.nodes_tab_tree.heading("Unidad 1", text="Unidad 1")
        self.nodes_tab_tree.heading("Unidad 2", text="Unidad 2")
        self.nodes_tab_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.nodes_tab_tree.bind("<Double-1>", lambda event: self.edit_node())

        # Scrollbar horizontal
        h_scroll = ttk.Scrollbar(frame_tree, orient="horizontal", command=self.nodes_tab_tree.xview)
        self.nodes_tab_tree.configure(xscrollcommand=h_scroll.set)  # Vincular el scrollbar al treeview
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Frame control
        control_frame = tk.Frame(frame)
        control_frame.pack(fill=tk.BOTH, padx=10, pady=10)

        # Añadir
        add_button = tk.Button(control_frame, text="Añadir", command=lambda: self.add_node())
        #add_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        add_button.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Eliminar
        remove_button = tk.Button(control_frame, text="Eliminar", command=lambda: self.delete_nodes())
        #remove_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        remove_button.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        return frame

    def create_custom_tab(self, notebook):
        frame = tk.Frame(notebook, padx=10, pady=10)
        tk.Label(frame, text="EDICIÓN ESTÉTICA", font=("Arial", 12, "bold")).pack()

        # ------- Contenedor con canvas + scrollbar --------
        container = tk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(container)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        canvas.configure(yscrollcommand=scrollbar.set)

        # Frame dentro del canvas
        control_frame = tk.Frame(canvas)

        # Añadir el frame al canvas y guardar el ID de la ventana
        window_id = canvas.create_window((0, 0), window=control_frame, anchor="nw")

        # Ajustar scrollregion al tamaño del contenido
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        control_frame.bind("<Configure>", on_frame_configure)

        # Ajustar el ancho del control_frame al ancho del canvas
        def resize_frame(event):
            canvas.itemconfig(window_id, width=event.width)

        canvas.bind("<Configure>", resize_frame)

        # Configurar columnas
        for i in range(4):
            control_frame.columnconfigure(i, weight=1)
        
        # Definir la función para el desplazamiento con la rueda del ratón
        def on_mouse_wheel(event):
            # Verificar si el contenido es desplazable
            start, end = canvas.yview()
            if end - start >= 1.0:
                return  # No hay nada que desplazar, salir de la función
            
            if event.delta:  # Windows
                canvas.yview_scroll(-1 * (event.delta // 120), "units")
            else:  # Linux/Mac
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")

        # Función que se ejecuta cuando el ratón entra en el control_frame
        def mouse_enter(event):
            canvas.bind_all("<MouseWheel>", on_mouse_wheel)  # Vincula el evento al canvas solo si el ratón está sobre control_frame
            canvas.bind_all("<Button-4>", on_mouse_wheel)   # Linux (scroll arriba)
            canvas.bind_all("<Button-5>", on_mouse_wheel)   # Linux (scroll abajo)

        # Función que se ejecuta cuando el ratón sale de control_frame
        def mouse_leave(event):
            canvas.unbind_all("<MouseWheel>")  # Desvincula el evento cuando el ratón sale del control_frame
            canvas.unbind_all("<Button-4>")   # Linux (scroll arriba)
            canvas.unbind_all("<Button-5>")   # Linux (scroll abajo)

        # Detectar cuando el ratón entra o sale de control_frame
        control_frame.bind("<Enter>", mouse_enter)
        control_frame.bind("<Leave>", mouse_leave)

        # --------- RELACIONES ---------
        #region

        # Label
        tk.Label(control_frame, text="RELACIONES", font=("Arial", 12, "bold")).grid(row=0, columnspan=4, pady=15)

        # Color
        self.relation_color = "#000000"
        tk.Button(control_frame, text="Color", command=lambda: self.edit_color("Relation")).grid(row=1, column=0, padx=5, pady=5)

        # Estilo de línea
        style_label = tk.Label(control_frame, text="Línea")
        style_label.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        style_values = ["solid", "dashed", "dashdot", "dotted"]
        self.style_relations = ttk.Combobox(control_frame, values=style_values, state="readonly")
        self.style_relations.set("solid")
        self.style_relations.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        self.style_relations.bind("<<ComboboxSelected>>", self.draw_figure_event)
        self.style_relations.bind("<MouseWheel>", self.block_scroll)       # Windows
        self.style_relations.bind("<Button-4>", self.block_scroll)         # Linux scroll up
        self.style_relations.bind("<Button-5>", self.block_scroll)         # Linux scroll down

        # Estilo de flecha
        arrowstyle_label = tk.Label(control_frame, text="Flecha")
        arrowstyle_label.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        arrowstyle_values = ["-", "<-", "->", "<->", "<|-", "-|>", "<|-|>", "]-", "-[", "]-[", "|-|", "]->", "<-["]
        self.arrowstyle_relations = ttk.Combobox(control_frame, values=arrowstyle_values, state="readonly")
        self.arrowstyle_relations.set("-")
        self.arrowstyle_relations.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        self.arrowstyle_relations.bind("<<ComboboxSelected>>", self.draw_figure_event)
        self.arrowstyle_relations.bind("<MouseWheel>", self.block_scroll)       # Windows
        self.arrowstyle_relations.bind("<Button-4>", self.block_scroll)         # Linux scroll up
        self.arrowstyle_relations.bind("<Button-5>", self.block_scroll)         # Linux scroll down

        # Tamaño de la flecha
        tk.Label(control_frame, text="Anchura").grid(row=4, column=0, pady=10)
        self.width_relations = tk.Scale(control_frame, from_=1, to=8, orient="horizontal", command=self.draw_figure_event)
        self.width_relations.grid(row=4, column=1, pady=10)
        #endregion

        # --------- EQUIVALENCIAS ---------
        #region

        # Label
        tk.Label(control_frame, text="EQUIVALENCIAS", font=("Arial", 12, "bold")).grid(row=5, columnspan=4, pady=15)

        # Color
        self.equi_color = "#000000"
        tk.Button(control_frame, text="Color", command=lambda: self.edit_color("Equivalence")).grid(row=6, column=0, padx=5, pady=5)

        # Estilo de línea
        style_label = tk.Label(control_frame, text="Línea")
        style_label.grid(row=7, column=0, padx=10, pady=10, sticky="ew")

        style_values = ["solid", "dashed", "dashdot", "dotted"]
        self.style_equivalences = ttk.Combobox(control_frame, values=style_values, state="readonly")
        self.style_equivalences.set("solid")
        self.style_equivalences.grid(row=7, column=1, padx=10, pady=10, sticky="ew")
        self.style_equivalences.bind("<<ComboboxSelected>>", self.draw_figure_event)
        self.style_equivalences.bind("<MouseWheel>", self.block_scroll)       # Windows
        self.style_equivalences.bind("<Button-4>", self.block_scroll)         # Linux scroll up
        self.style_equivalences.bind("<Button-5>", self.block_scroll)         # Linux scroll down

        # Estilo de flecha
        arrowstyle_label = tk.Label(control_frame, text="Flecha")
        arrowstyle_label.grid(row=8, column=0, padx=10, pady=10, sticky="ew")

        arrowstyle_values = ["-", "<-", "->", "<->", "<|-", "-|>", "<|-|>", "]-", "-[", "]-[", "|-|", "]->", "<-["]
        self.arrowstyle_equivalences = ttk.Combobox(control_frame, values=arrowstyle_values, state="readonly")
        self.arrowstyle_equivalences.set("-")
        self.arrowstyle_equivalences.grid(row=8, column=1, padx=10, pady=10, sticky="ew")
        self.arrowstyle_equivalences.bind("<<ComboboxSelected>>", self.draw_figure_event)
        self.arrowstyle_equivalences.bind("<MouseWheel>", self.block_scroll)       # Windows
        self.arrowstyle_equivalences.bind("<Button-4>", self.block_scroll)         # Linux scroll up
        self.arrowstyle_equivalences.bind("<Button-5>", self.block_scroll)         # Linux scroll down

        # Tamaño de la flecha
        tk.Label(control_frame, text="Anchura").grid(row=9, column=0, pady=10)
        self.width_equivalences = tk.Scale(control_frame, from_=1, to=8, orient="horizontal", command=self.draw_figure_event)
        self.width_equivalences.grid(row=9, column=1, pady=10)
        #endregion

        # --------- FASES ---------
        # region

        # Label
        tk.Label(control_frame, text="FASES", font=("Arial", 12, "bold")).grid(row=10, columnspan=4, pady=15)
        
        # Treeview
        columns = ["Fase", "Color"]
        self.phase_color_tab_tree = ttk.Treeview(control_frame, columns=columns, height=5, show="headings")
        for col in columns:
            self.phase_color_tab_tree.heading(col, text=col)
            self.phase_color_tab_tree.column(col, anchor="center")
        
        phases = self.BD['Fase'].unique()
        for phase in phases:
            if phase != '':
                self.phase_color_tab_tree.insert("", "end", values=(str(phase), "#0080ff"))
        self.phase_color_tab_tree.grid(row=11, columnspan=4, padx=5, pady=10)

        #self.phase_color_tab_tree.bind("<Double-1>", lambda event: self.edit_phase_color())
        self.phase_color_tab_tree.bind("<Double-1>", lambda event: self.edit_phase_color())
        
        #endregion

        return frame

    def create_filter_container(self, master_frame):
        
        # Frame del filtrado
        control_frame = tk.Frame(master_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Etiqueta
        tk.Label(control_frame, text="FILTRADO", font=("Arial", 12, "bold")).pack(fill=tk.BOTH)

        # Frame control
        frame1 = tk.Frame(control_frame)

        self.filtro = ""
        
        frame11 = tk.Frame(frame1)
        frame11.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, pady=5)

        btn_filtrar = tk.Button(frame11, text="🔍 Filtrar", command=lambda: (self.update_filter(), self.update_all()))
        btn_filtrar.pack(fill=tk.X, expand=True, padx=5, pady=5)

        btn_zoom = tk.Button(frame11, text="Zoom", command=lambda: (self.update_filter(), self.update_zoom()))
        btn_zoom.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        frame12 = tk.Frame(frame1)
        frame12.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5, pady=5)
        
        self.filtro_entry = tk.Entry(frame12)
        self.filtro_entry.pack(fill=tk.X, expand=True, padx=5, pady=5)

        self.filter_options_menubutton = tk.Menubutton(frame12, text="Opciones", relief=tk.RAISED)
        menu = tk.Menu(self.filter_options_menubutton, tearoff=0)
        self.filterApplyMayMin = tk.BooleanVar(value=False)
        self.filterApplyFullWords = tk.BooleanVar(value=False)
        self.filterApplyDiacritics = tk.BooleanVar(value=False)
        menu.add_checkbutton(label="Coincidir mayúsculas y minúsculas", variable=self.filterApplyMayMin, command=lambda: (self.update_filter(), self.update_all()))
        menu.add_checkbutton(label="Coincidir palabras completas", variable=self.filterApplyFullWords, command=lambda: (self.update_filter(), self.update_all()))
        menu.add_checkbutton(label="Coincidir diacríticos", variable=self.filterApplyDiacritics, command=lambda: (self.update_filter(), self.update_all()))
        self.filter_options_menubutton["menu"] = menu
        self.filter_options_menubutton.pack(fill=tk.X, expand=True, padx=5, pady=5)

        frame_listbox = tk.Frame(frame1)
        frame_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)

        self.filter_listbox = tk.Listbox(frame_listbox, selectmode=tk.MULTIPLE, height=3, exportselection=False)
        self.filter_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(frame_listbox, orient=tk.VERTICAL)
        scrollbar.pack(fill=tk.BOTH, side=tk.LEFT)

        for col in self.BD.columns:
            self.filter_listbox.insert(tk.END, str(col))        

        self.filter_listbox.config(yscrollcommand = scrollbar.set) 
        scrollbar.config(command = self.filter_listbox.yview) 

        frame1.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        frame2 = tk.Frame(control_frame)

        btn_save = tk.Button(frame2, text="Guardar", command=lambda: self.download_filtered_csv())
        btn_save.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        frame2.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        """frame3 = tk.Frame(control_frame)

        btn_zoom = tk.Button(frame3, text="Zoom", command=lambda: self.update_zoom())
        btn_zoom.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        frame3.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)"""

    # Cerrar ventanas

    def cerrar_ventana_principal(self):
        if len(self.undo_stack) > 0:
            respuesta = messagebox.askyesnocancel(
                "Cambios no guardados",
                "Tienes cambios sin guardar. ¿Deseas guardar antes de salir?"
            )
            if respuesta is None:
                # Cancelar el cierre
                return
            elif respuesta:
                # Guardar antes de salir
                if self.uploaded_file == None:
                    self.download_csv()
                else:
                    self.save_csv()

        print("Cerrando la ventana principal...")
        root.quit()  # Termina el bucle principal de tkinter
        root.destroy()  # Asegura que todos los recursos de la ventana sean liberados
        exit()  # Finaliza el programa completamente (si es necesario)

    # Grafo default
    
    def graph_default(self):

        # Inicializar lista de lista
        data = [["T", "Unexcavated", "", "", "P", "", ""],
                ["Unexcavated", "G", "", "", "P", "", ""],
                ["G", "", "", "", "P", "", ""]]

        # Crear el pandas Dataframe
        df = pd.DataFrame(data, columns=['Nombre', 'Hijos', 'Equivalencias', 'Hecho', 'Tipo', 'Fase', 'Descripcion'])

        return df

    # Cargar el BD

    def upload_BD(self, df=None):
        # Limpiar estructuras previas
        self.clean_structures()
        
        # Crear un DataFrame para 'tabla', con las columnas del CSV más 'Codigo'
        self.BD = df
        self.BD.insert(0, "Codigo", None)

        for idx, row in df.iterrows():
            # Codigo
            # codigo = self.generate_numerical_code()  # Supongo que esta función existe
            codigo = self.BD.at[idx, "Nombre"]
            self.BD.at[idx, "Codigo"] = codigo

        for idx, row in df.iterrows():
            # Hijos
            sons = str(row.get("Hijos", "")).split(',') if pd.notna(row.get("Hijos")) else []
            sons_codes = []
            for son in sons:
                son = son.strip()
                if son:
                    son_code = self.name_to_code(son)
                    sons_codes.append(son_code)
            sons_codes = ",".join(map(str, sons_codes))
            self.BD.at[idx, "Hijos"] = sons_codes
        
            # Equivalences
            equis = str(row.get("Equivalencias", "")).split(',') if pd.notna(row.get("Equivalencias")) else []
            equis_codes = []
            for equi in equis:
                equi = equi.strip()
                if equi:
                    equi_code = self.name_to_code(equi)
                    equis_codes.append(equi_code)
            equis_codes = ",".join(map(str, equis_codes))
            self.BD.at[idx, "Equivalencias"] = equis_codes
        
            # Facts
            fact_values = str(row.get("Hecho", "")).split(',') if pd.notna(row.get("Hecho")) else []
            fact_codes = []
            for fact in fact_values:
                fact = fact.strip()
                if fact:
                    fact_code = self.name_to_code(fact)
                    fact_codes.append(fact_code)
            fact_codes = ",".join(map(str, fact_codes))
            self.BD.at[idx, "Hecho"] = fact_codes
        
        #print(self.BD)

    # Funciones de cargar/descargar archivo

    def upload_CSV(self):
        # Cargar archivo
        file = filedialog.askopenfilename(title="Seleccionar archivo CSV", filetypes=[("Archivos CSV", "*.csv")])

        if not file:
            return
        
        try:
            df = pd.read_csv(file, sep=";", engine='python', dtype=str)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo CSV.\n{str(e)}")
            return
        
        df.columns = df.columns.str.strip()  # Limpiar espacios en los nombres de las columnas
        df = df.fillna("")  # Reemplazar NaN con cadenas vacías
        df = df.astype(str)

        def limpiar_lista_string(s):
            return ",".join(part.strip() for part in s.split(",")) if isinstance(s, str) else s

        for col in df.columns:
            if df[col].dtype == "object" or df[col].dtype == "string":
                if col in ("Nombre", "Hijos", "Equivalencias", "Hecho", "Tipo", "Fase"):
                    df[col] = df[col].map(limpiar_lista_string)

        #df = df.applymap(lambda x: x.replace(" ", "") if isinstance(x, str) else x)
        #print(df) 

        # Si la revisión del archivo es correcta
        if self.check_file(df):

            # Cargar a BD
            self.upload_BD(df)

            # Actualizar
            self.reset_apply_facts()
            self.reset_filter_widgets_PART_1()
            #self.update_all()
            self.update_nodes_tab()
            self.update_relations_tab()
            self.update_equivalences_tab()
            self.update_facts_tab()
            self.update_widgets()
            self.reset_custom_tab()
            self.reset_filter_widgets_PART_2()
            self.draw_figure()
            if len(self.not_drawn_nodes) > 0:
                mensaje = "Las siguientes unidades estratigráficas no tienen padre, hijos o equivalencias, por lo que no se han dibujado:\n"
                mensaje += ", ".join(self.not_drawn_nodes)
                messagebox.showinfo("Advertencia", mensaje)
            self.uploaded_file = file
        print("Uploading finished")

    def check_file(self, df):
        main_columns = ["Nombre", "Hijos", "Equivalencias", "Hecho", "Tipo", "Fase", "Descripcion"]

        # Comprobar que las columnas principales existen
        if not all(col in df.columns for col in main_columns):
            messagebox.showerror("Error", f"El archivo CSV no contiene alguna de las siguientes columnas: {main_columns}.")
            return False
        
        # Comprobar que en las columnas no existe una columna con el nombre 'Codigo'
        if 'Codigo' in df.columns:
            messagebox.showerror("Error", f"El archivo CSV no puede contener una columna de nombre 'Codigo'.")
            return False
        
        # Comprobar que no hay dos columnas con el mismo nombre
        # Cuando hay dos columnas con el mismo nombre en el CSV, la segunda columna con el mismo nombre se carga con “nombre.X”, siendo X el número de veces que se repite.
        if any(df.columns.duplicated()):
            messagebox.showerror("Error", f"El archivo CSV contiene columnas duplicadas.")
            return False

        # ---- NAME ----
        # Comprobar que en "Nombre" no hay nombres con , o ;
        df_with_commas_semicolons = df[df['Nombre'].str.contains('[,;]', regex=True)]
        if len(df_with_commas_semicolons) > 0:
            messagebox.showerror("Error", f"No puede haber caracteres ',' o ';' dentro del nombre. Unidades {list(df_with_commas_semicolons["Nombre"])}")
            return False

        # Comprobar que no hay filas sin nombre
        df_without_name = df[df['Nombre'] == '']
        # print(df_without_name)
        if len(df_without_name) > 0:
            messagebox.showerror("Error", f"No puede haber filas sin 'Nombre'. Filas: {df_without_name.index.tolist()}")
            return False
    
        # Encontrar índices de las filas duplicadas en la columna 'Nombre'
        df_duplicated_names = df[df['Nombre'].duplicated()]
        if len(df_duplicated_names) > 0:
            messagebox.showerror("Error", f"No puede haber duplicados en 'Nombre'. Filas: {list(df_duplicated_names["Nombre"])}")
            return False
        
        names = []
        sons = []
        equi = []
        facts = []
        for _, row in df.iterrows():
            names.append(row.get("Nombre", ""))
            sons.append(str(row.get("Hijos", "")).split(',') if pd.notna(row.get("Hijos")) else [])
            equi.append(str(row.get("Equivalencias", "")).split(',') if pd.notna(row.get("Equivalencias")) else [])
            facts.append(str(row.get("Hecho", "")).split(',') if pd.notna(row.get("Hecho")) else [])

        # Comprobar que los valores en 'Hijos', 'Equivalencias' y 'Hecho' están en 'Nombre', si no están vacíos
        for index, (hijos, equivalencias, nodos_hechos) in enumerate(zip(sons, equi, facts)):
            for hijo in hijos:
                if hijo and hijo not in names:
                    messagebox.showerror("Error", f"El valor '{hijo}' en 'Hijos' no está en 'Nombre'. Fila {index}")
                    return False
            for equivalente in equivalencias:
                if equivalente and equivalente not in names:
                    messagebox.showerror("Error", f"El valor '{equivalente}' en 'Equivalencias' no está en 'Nombre'. Fila {index}")
                    return False
            for nodo_hecho in nodos_hechos:
                if nodo_hecho and nodo_hecho not in names:
                    messagebox.showerror("Error", f"El valor '{nodo_hecho}' en 'Hecho' no está en 'Nombre'. Fila {index}")
                    return False
        
        # Comprobar que no está el mismo valor en "Nombre", "Hijos", "Equivalencias" o "Hecho" en la misma fila
        def indices_con_duplicados(df):
            columnas = ['Nombre', 'Hijos', 'Equivalencias', 'Hecho']
            # indices = []
            duplicates = []

            for idx, row in df.iterrows():
                # Obtener valores, convertirlos en string y filtrar vacíos
                valores = self.get_values_from_string(",".join([str(row["Nombre"]), str(row["Hijos"]), str(row["Equivalencias"]), str(row["Hecho"])]))
                #print(f"{valores} <=> {set(valores)}; {len(valores)} <=> {len(set(valores))}")
                if len(valores) != len(set(valores)):
                    # indices.append(idx)
                    duplicates.append(str(row["Nombre"]))

            return duplicates
        duplicados = indices_con_duplicados(df)

        if len(duplicados) > 0:
            messagebox.showerror("Error", f"No puede haber valores duplicados en 'Nombre', 'Hijos', 'Equivalencias' y 'Hecho'. Unidades: {duplicados}")
            return False
        
        # No puede haber ciclos padre-hijo
        # Crear un grafo dirigido
        G = nx.DiGraph()

        # Llenar el grafo con las relaciones padre-hijo
        for index, row in df.iterrows():
            father = row['Nombre']
            # print(f"FATHER: {father}")
            sons = row.get("Hijos", "").split(',') if pd.notna(row.get("Hijos")) else []
            for son in sons:
                G.add_edge(father, son)
                """# PARENT EQUIVALENCES
                print("FATHER")
                equi_str_father = df.loc[df["Nombre"] == father, "Equivalencias"].values
                father_equis = []
                if len(equi_str_father) > 0 and isinstance(equi_str_father[0], str) and not equi_str_father[0].isspace():  # Verificar si hay hijos
                    father_equis = equi_str_father[0].split(",")  # Convertir a lista
                if len(father_equis) > 0:
                    for father_equi in father_equis:
                            if father_equi != '':
                                print(f"{father_equi} - {son}")
                                G.add_edge(father_equi, son)
                # SON EQUIVALENCES
                print("SON")
                #son_equis = self.get_equivalences(son)
                equi_str_son = df.loc[df["Nombre"] == son, "Equivalencias"].values
                son_equis = []
                if len(equi_str_son) > 0 and isinstance(equi_str_son[0], str) and not equi_str_son[0].isspace():  # Verificar si hay hijos
                    son_equis = equi_str_son[0].split(",")  # Convertir a lista
                if len(son_equis) > 0:
                    for son_equi in son_equis:
                            if son_equi != '':
                                print(f"{father} - {son_equi}")
                                G.add_edge(father, son_equi)"""
            facts = row.get("Hecho", "").split(',') if pd.notna(row.get("Hecho")) else []
            for fact in facts:
                G.add_edge(father, fact)

        # Detectar ciclos
        cycles = list(nx.simple_cycles(G))

        # Comprobar si existen ciclos
        if cycles:
            mensaje = "Se han encontrado ciclos: "
            for cycle in cycles:
                mensaje += "".join(" -> ".join(cycle)) + "; "
            messagebox.showerror("Error", mensaje)
            return False

        # La equivalencia se debe indicar en 'Equivalencias' de ambos nodos
        for name, equivalences in zip(names, equi):
            for eq in equivalences:
                # Comprobar bidireccionalidad
                if eq and name not in df[df['Nombre'] == eq]['Equivalencias'].values[0]:
                    messagebox.showerror("Error", f"La equivalencia entre '{name}' y '{eq}' no es bidireccional.")
                    return False
                if name and eq:
                    # Comprobar que los nodos en cada equivalencia tienen los mismos padres
                    if not self.contains_both(df, name, eq, 'Hijos'):
                        messagebox.showerror("Error", f"Los nodos equivalentes '{name}' y '{eq}' no tienen los mismos padres")
                        return False
                    # Comprobar que los nodos en cada equivalencia tienen los mismos hijos
                    # Paso 1-3: dividir, limpiar espacios y convertir en conjuntos
                    set_a = set(item.strip() for item in df[df['Nombre'] == name]['Hijos'].values[0].split(','))
                    set_b = set(item.strip() for item in df[df['Nombre'] == eq]['Hijos'].values[0].split(','))
                    if set_a != set_b:
                        messagebox.showerror("Error", f"Los nodos equivalentes '{name}' y '{eq}' no tienen los mismos hijos")
                        return False
        
    
        # Comprobar que no haya valores duplicados en 'Hecho'
        df_all_facts = df['Hecho'].str.split(',').explode()
        df_all_facts = df_all_facts[df_all_facts != '']
        duplicated_values = df_all_facts[df_all_facts.duplicated()]

        if len(duplicated_values) > 0:
            messagebox.showerror("Error", f"No puede haber duplicados en 'Hecho'. Unidades: {list(df.loc[duplicated_values.index.tolist(), "Nombre"])}")
            return False

        # Comprobar que no hay filas sin tipo
        df_without_type = df[df['Tipo'] == '']
        if len(df_without_type) > 0:
            messagebox.showerror("Error", f"No puede haber filas sin 'Tipo'. Unidades: {list(df_without_type["Nombre"])}")
            return False
        
        # Comprobar que en 'Tipo' solo hay tres valores: 'P' o 'N' o 'H'
        df_incorrect_type = df[~df["Tipo"].isin(["P", "N", "H"])]
        if len(df_incorrect_type) > 0:
            messagebox.showerror("Error", f"La columna 'Tipo' solo puede contener los valores 'P', 'N' o 'H'. Unidades {list(df_incorrect_type["Nombre"])}")
            return False
        
        # Comprobar que los nodos 'P' y 'N' no tienen información en 'Hecho'
        df_PN = df[df["Tipo"].isin(['P','N'])]
        df_incorrect_PN = df_PN[df_PN["Hecho"] != ""]
        if len(df_incorrect_PN) > 0:
            messagebox.showerror("Error", f"Los nodos 'P' y 'N' no pueden tener valores en 'Hecho'. Unidades {list(df_incorrect_PN["Nombre"])}")
            return False
        
        # Comprobar que los nodos 'H' no tienen información en 'Hijos' o 'Equivalencias'
        df_H = df[df["Tipo"] == "H"]
        df_incorrect_H = df_H[(df_H["Hijos"] != "") | (df_H["Equivalencias"] != "")]
        if len(df_incorrect_H) > 0:
            messagebox.showerror("Error", f"Los nodos 'H' no pueden tener valores en 'Hijos' o 'Equivalencias'. Unidades {list(df_incorrect_H["Nombre"])}")
            return False
        
        # Comprobar que en las relaciones y equivalencias de las unidades no hay hechos
        fact_names = set(df_H['Nombre'].tolist())

        def contiene_nombre(cadena):
            if pd.isna(cadena):
                return False
            valores = set(map(str.strip, cadena.split(',')))
            return not fact_names.isdisjoint(valores)
        
        filtro = df_PN['Hijos'].apply(contiene_nombre) | df_PN['Equivalencias'].apply(contiene_nombre)
        df_facts_in_rel_eq = df_PN[filtro].copy()
        if len(df_facts_in_rel_eq) > 0:
            messagebox.showerror("Error", f"Los nodos 'H' no pueden estar en 'Hijos' o 'Equivalencias'. Unidades {list(df_facts_in_rel_eq["Nombre"])}")
            return False

        return True

    def new_file(self):
        respuesta = messagebox.askyesnocancel("Aviso", f"Al generar un nuevo archivo se perderá todo el progreso. ¿Continuar?")

        if respuesta is None:
            return
        elif respuesta:
            self.uploaded_file = None # No hay un archivo "original" sobre el que guardar
            self.upload_BD(self.graph_default())
            self.update_all()
        else:
            return
        
    def download_csv(self):
        # Crear un DataFrame con los datos
        df_to_download = self.BD.copy()

        for idx, row in self.BD.iterrows():
            for col in ["Hijos", "Equivalencias", "Hecho"]:
                elements = str(row.get(col, "")).split(',') if pd.notna(row.get(col)) else []
                elements_codes = []
                for element in elements:
                    element = element.strip()
                    if element:
                        element_code = self.code_to_name(element)
                        elements_codes.append(element_code)
                elements_codes = ",".join(map(str, elements_codes))
                df_to_download.at[idx, col] = elements_codes
        
        df_to_download = df_to_download.drop(df_to_download.columns[0], axis=1).copy()

        # Abrir cuadro de diálogo para elegir ubicación
        archivo = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv")],
            title="Guardar archivo CSV"
        )

        if not archivo:
            return  # El usuario canceló la operación

        try:
            # Guardar el DataFrame como CSV
            df_to_download.to_csv(archivo, sep=";", index=False, encoding="utf-8-sig")
            self.uploaded_file = archivo
            messagebox.showinfo("Éxito", "El archivo CSV se ha guardado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el archivo: {e}")

    def save_csv(self):
        # Verificar si se ha cargado un archivo previamente
        if self.uploaded_file == None:
            messagebox.showerror("Error", "No hay un archivo CSV cargado para sobrescribir.")
            return

        # Crear un DataFrame con los datos
        df_to_save = self.BD.copy()

        for idx, row in self.BD.iterrows():
            for col in ["Hijos", "Equivalencias", "Hecho"]:
                elements = str(row.get(col, "")).split(',') if pd.notna(row.get(col)) else []
                elements_codes = []
                for element in elements:
                    element = element.strip()
                    if element:
                        element_code = self.code_to_name(element)
                        elements_codes.append(element_code)
                elements_codes = ",".join(map(str, elements_codes))
                df_to_save.at[idx, col] = elements_codes

        df_to_save = df_to_save.drop(df_to_save.columns[0], axis=1).copy()

        try:
            # Sobrescribir el archivo original
            df_to_save.to_csv(self.uploaded_file, sep=";", index=False, encoding="utf-8-sig")
            messagebox.showinfo("Éxito", "El archivo CSV se ha guardado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el archivo: {e}")

    def download_filtered_csv(self):
        # Tomar todos los nodos en los treeview de relaciones y equivalencias
        open_nodes = []
        closed_nodes = []
        closed_indexes = []

        for item in self.relations_tab_tree.get_children():
            item = self.relations_tab_tree.item(item, "values")
            open_nodes.append(item[0]) # Padre
            open_nodes.append(item[1]) # Hijo
        
        for item in self.equivalences_tab_tree.get_children():
            item = self.equivalences_tab_tree.item(item, "values")
            open_nodes.append(item[0]) # Nodo 1
            open_nodes.append(item[1]) # Nodo 2
        
        open_nodes = list(set(open_nodes))

        while len(open_nodes) > 0:
            
            # Tomamos el primer nodo
            node = open_nodes.pop()
            df_row = self.BD[self.BD["Codigo"] == node]
            row_index = self.BD[self.BD["Codigo"] == node].index[0]
            #print(df_row)
            #print(self.BD.at[row_index, "Tipo"])

            if self.BD.at[row_index, "Tipo"] == "H":
                fact_nodes = str(self.BD.at[row_index, "Hecho"]).split(',') if pd.notna(self.BD.at[row_index, "Hecho"]) else []
                for fact_node in fact_nodes:
                    if fact_node not in closed_nodes:
                        open_nodes.append(fact_node)
                closed_nodes.append(node)
            else:
                closed_nodes.append(node)
            closed_indexes.append(row_index)
        
        closed_nodes = list(set(closed_nodes))
        closed_indexes = list(set(closed_indexes))
        indexes_of_rows_to_delete = [i for i in range(len(self.BD)) if i not in closed_indexes]
        #print(indexes_of_rows_to_delete)

        df_to_download = self.BD.copy()
        df_to_download = df_to_download.drop(indexes_of_rows_to_delete)
        #df_to_download = df_to_download.reset_index(drop=True, inplace=True)

        for idx, row in df_to_download.iterrows():
            code = str(row.get("Codigo", ""))
            for col in ["Hijos", "Equivalencias", "Hecho"]:
                elements = str(row.get(col, "")).split(',') if pd.notna(row.get(col)) else []
                elements_codes = []
                for element in elements:
                    element = element.strip()
                    if element and element in closed_nodes:
                        if col == "Hijos" and not self.exists_relation(self.find_fact_with_path(code), self.find_fact_with_path(element)):
                            continue
                        if col == "Equivalencias" and not self.exists_equivalencie(self.find_fact_with_path(code), self.find_fact_with_path(element)):
                            continue
                        element_code = self.code_to_name(element)
                        elements_codes.append(element_code)
                elements_codes = ",".join(map(str, elements_codes))
                df_to_download.at[idx, col] = elements_codes


        df_to_download = df_to_download.drop(df_to_download.columns[0], axis=1).copy()
        #df_to_download = df_to_download.reindex(columns=['Nombre', 'Hijos', 'Equivalencias', 'Hecho', 'Tipo', 'Fase', 'Descripcion'])

        print(df_to_download)

        # Abrir cuadro de diálogo para elegir ubicación
        archivo = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv")],
            title="Guardar archivo CSV"
        )

        if not archivo:
            return  # El usuario canceló la operación

        try:
            # Guardar el DataFrame como CSV
            df_to_download.to_csv(archivo, sep=";", index=False, encoding="utf-8-sig")
            self.uploaded_file = archivo
            messagebox.showinfo("Éxito", "El archivo CSV se ha guardado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el archivo: {e}")

    # Funciones de actualización

    def update_all(self):
        self.todos_los_hechos = {
            str(row['Codigo']): set(row['Hecho'].split(','))
            for _, row in self.BD.iterrows()
        }
        self.entries_strings = self.get_values_from_string(str(self.facts_entry.get()))
        self.hechos_visibles = {clave: valor for clave, valor in self.todos_los_hechos.items() if clave in self.entries_strings}

        self.update_nodes_tab()
        self.update_relations_tab()
        self.update_equivalences_tab()
        self.update_facts_tab()
        self.update_widgets()
        self.draw_figure()
        # print(self.BD)
    
    def draw_figure_event(self, event):
        self.update_widgets()
        self.draw_figure()
    
    def update_relations_tab(self):
        inicio = time.time()
        searching_fact_time = 0

        # Limpiar el Treeview
        self.clean_tree(self.relations_tab_tree)

        # Cargar datos de la BD
        for _, row in self.BD.iterrows():
            node_type = str(row["Tipo"]).strip()
            if node_type == "P" or node_type == "N":
                parent_code = str(row["Codigo"]).strip()
                sons_codes = str(row.get("Hijos", "")).split(',') if pd.notna(row.get("Hijos")) else []
                for son_code in sons_codes:
                    son_code = son_code.strip()
                    if son_code:
                        #inicio_fact = time.time()
                        parent_code = self.find_fact_with_path(parent_code)
                        son_code = self.find_fact_with_path(son_code)
                        #searching_fact_time = searching_fact_time + (time.time() - inicio_fact)
                        if parent_code == son_code:
                            continue
                        codes = [parent_code, son_code]
                        if not self.exists_relation(parent_code, son_code):
                            if (self.value_in_treeview(self.nodes_tab_tree, parent_code, "Codigo") or self.value_in_treeview(self.nodes_tab_tree, son_code, "Codigo")
                             or self.value_in_treeview(self.nodes_fact_tab_tree, parent_code, "Codigo") or self.value_in_treeview(self.nodes_fact_tab_tree, son_code, "Codigo")):
                                self.relations_tab_tree.insert("", "end", values=codes)
        fin = time.time()
        upload_relations_time = fin - inicio
        # print(f"upload_relations: {upload_relations_time: 4f} segundos")
        """print(f"searching_fact_time: {searching_fact_time: 4f} segundos")
        if searching_fact_time > 0:
            print(f"percentage of time seaching facts: {(searching_fact_time * 100)/upload_relations_time}%")
        print(f"tiempo_total: {tiempos['Total'] : 4f} segundos")
        if tiempos["Contenedores"] > 0:
            print(f"tiempo_contenedores: {tiempos['Contenedores'] : 4f} segundos. {(tiempos['Contenedores'] * 100 / tiempos['Total']) : 4f}%")
        if tiempos["Rutas"] > 0:
            print(f"tiempo_rutas: {tiempos['Rutas'] : 4f} segundos. {(tiempos['Rutas'] * 100 / tiempos['Total']) : 4f}%")
        if tiempos["Jerarquia"] > 0:
            print(f"tiempo_jerarquia: {tiempos['Jerarquia'] : 4f} segundos. {(tiempos['Jerarquia'] * 100 / tiempos['Total']) : 4f}%")"""
        
    def update_equivalences_tab(self):
        inicio = time.time()

        # Limpiar el Treeview
        self.clean_tree(self.equivalences_tab_tree)

        # Cargar datos de la BD
        for _, row in self.BD.iterrows():
            node_type = str(row["Tipo"]).strip()
            if node_type == "P" or node_type == "N":
                main_code = str(row["Codigo"]).strip()
                equis_codes = str(row.get("Equivalencias", "")).split(',') if pd.notna(row.get("Equivalencias")) else []
                for equi_code in equis_codes:
                    equi_code = equi_code.strip()
                    if equi_code:
                        main_code = self.find_fact_with_path(main_code)
                        equi_code = self.find_fact_with_path(equi_code)
                        if main_code == equi_code:
                            continue
                        codes = [main_code, equi_code]
                        if not self.exists_equivalencie(main_code, equi_code) and main_code != equi_code:
                            if (self.value_in_treeview(self.nodes_tab_tree, main_code, "Codigo") or self.value_in_treeview(self.nodes_tab_tree, equi_code, "Codigo")
                             or self.value_in_treeview(self.nodes_fact_tab_tree, main_code, "Codigo") or self.value_in_treeview(self.nodes_fact_tab_tree, equi_code, "Codigo")):
                                self.equivalences_tab_tree.insert("", "end", values=codes)
        # print(f"upload_equivalences: {time.time() - inicio: 4f} segundos")

    def update_facts_tab(self):
        inicio = time.time()

        # Limpiar el Treeview
        self.clean_tree(self.facts_tab_tree)

        # Cargar datos de la BD
        for _, row in self.BD.iterrows():
            main_code = str(row["Codigo"]).strip()
            node_type = str(row["Tipo"]).strip()
            if node_type == "H":
                facts_codes = str(row.get("Hecho", "")).split(',') if pd.notna(row.get("Hecho")) else []
                for fact_code in facts_codes:
                    fact_code = fact_code.strip()
                    if fact_code:
                        codes = [main_code, fact_code]
                        if not self.exists_fact(main_code, fact_code):
                            if (self.value_in_treeview(self.nodes_tab_tree, main_code, "Codigo") or self.value_in_treeview(self.nodes_tab_tree, fact_code, "Codigo")
                             or self.value_in_treeview(self.nodes_fact_tab_tree, main_code, "Codigo") or self.value_in_treeview(self.nodes_fact_tab_tree, fact_code, "Codigo")):
                                self.facts_tab_tree.insert("", "end", values=codes)
        # print(f"upload_facts: {time.time() - inicio: 4f} segundos")
           
    def update_nodes_tab(self):
        inicio = time.time()

        # Excluir columnas "Hijos", "Equivalencias" y "Facts"
        columns_NODES = [col for col in self.BD.columns if col not in ["Hijos", "Equivalencias", "Hecho"]]

        # Limpiar el Treeview
        self.clean_tree(self.nodes_tab_tree)
        self.clean_tree(self.nodes_fact_tab_tree)

        # Asignar las nuevas columnas
        self.nodes_tab_tree["columns"] = columns_NODES
        self.nodes_fact_tab_tree["columns"] = columns_NODES

        # Configurar encabezados
        for col in columns_NODES:
            if col == "Codigo":
                self.nodes_tab_tree.heading(col, text="")
                self.nodes_tab_tree.column(col, width=0, stretch=False)  # Opcional: Alinear contenido
                self.nodes_fact_tab_tree.heading(col, text="")
                self.nodes_fact_tab_tree.column(col, width=0, stretch=False)  # Opcional: Alinear contenido
            else:
                self.nodes_tab_tree.heading(col, text=col)
                self.nodes_tab_tree.column(col, anchor="center", stretch=False)  # Opcional: Alinear contenido
                self.nodes_fact_tab_tree.heading(col, text=col)
                self.nodes_fact_tab_tree.column(col, anchor="center", stretch=False)  # Opcional: Alinear contenido

        # Cargar datos de la BD
        for _, row in self.BD.iterrows():
            if self.pass_filter(row):
                if str(row.get("Tipo", "")) in ["P", "N"]:
                    self.nodes_tab_tree.insert("", "end", values=[row[col] for col in columns_NODES])
                elif str(row.get("Tipo", "")) == "H":
                    self.nodes_fact_tab_tree.insert("", "end", values=[row[col] for col in columns_NODES])
        # print(f"upload_nodes: {time.time() - inicio: 4f} segundos")

    def update_filter(self):

        self.filtro = self.filtro_entry.get()

    def reset_custom_tab(self):

        print("Reset done")
        self.relation_color = "#000000"
        self.style_relations.set("solid")
        self.arrowstyle_relations.set("-")
        self.width_relations.set(1)

        self.equi_color = "#000000"
        self.style_equivalences.set("solid")
        self.arrowstyle_equivalences.set("-")
        self.width_equivalences.set(1)

        # self.facts_entry.delete(0, tk.END)

        self.clean_tree(self.phase_color_tab_tree)

        phases = self.BD['Fase'].unique()
        #print(phases)
        for phase in phases:
            if phase != '':
                self.phase_color_tab_tree.insert("", "end", values=(str(phase), "#0080FF"))
        
    def reset_filter_widgets_PART_1(self):

        # WIDGETS DE FILTRADO
        self.filtro = ""
        self.filtro_entry.delete(0, tk.END)
        self.filter_listbox.delete(0, tk.END)
        self.filterApplyMayMin.set(False)
        self.filterApplyFullWords.set(False)
        self.filterApplyDiacritics.set(False)
        
    def reset_filter_widgets_PART_2(self):
        for col in self.BD.columns:
            self.filter_listbox.insert(tk.END, str(col)) 
    
    def reset_apply_facts(self):
        self.facts_entry.delete(0, tk.END)

        self.todos_los_hechos.clear()
        self.entries_strings.clear()
        self.hechos_visibles.clear()

    def update_widgets(self):
        inicio = time.time()

        # TABS DE RELACIÓN, EQUIVALENCIAS Y HECHOS
        nodes_codes_PN = list(self.BD[self.BD["Tipo"].isin(["P","N"])]["Codigo"])
        nodes_codes_H = list(self.BD[self.BD["Tipo"] == "H"]["Codigo"])
        
        # Actualizar nodos en las entries de relación
        self.node1_entry_rel.config(values=nodes_codes_PN)
        self.node2_entry_rel.config(values=nodes_codes_PN)
        self.node1_entry_equi.config(values=nodes_codes_PN)
        self.node2_entry_equi.config(values=nodes_codes_PN)
        self.node1_entry_facts.config(values=nodes_codes_H)
        self.node2_entry_facts.config(values=nodes_codes_PN)

        if nodes_codes_PN:
            self.node1_entry_rel.set(nodes_codes_PN[0])
            self.node2_entry_rel.set(nodes_codes_PN[0])
            self.node1_entry_equi.set(nodes_codes_PN[0])
            self.node2_entry_equi.set(nodes_codes_PN[0])
            self.node2_entry_facts.set(nodes_codes_PN[0])
        else:
            self.node1_entry_rel.set('')
            self.node2_entry_rel.set('')
            self.node1_entry_equi.set('')
            self.node2_entry_equi.set('')
            self.node2_entry_facts.set('')
        
        if nodes_codes_H:
            self.node1_entry_facts.set(nodes_codes_H[0])
        else:
            self.node1_entry_facts.set('')
        
        # ÁRBOL DE COLOR DE FASES
        delete_items_list = []
        for item in self.phase_color_tab_tree.get_children():
            #print(f"{self.phase_color_tab_tree.item(item, "values")[0]} in {self.BD["Fase"].unique()} = {self.phase_color_tab_tree.item(item, "values")[0] in self.BD["Fase"].unique()}")
            if self.phase_color_tab_tree.item(item, "values")[0] not in self.BD["Fase"].unique():
                delete_items_list.append(item)

        for item in delete_items_list:
            #print(f"Fase {item} eliminada !!!!")
            self.phase_color_tab_tree.delete(item)
        
        # print(f"upload_widgets: {time.time() - inicio: 4f} segundos")
  
    def update_undo_redo_status(self):
        
        if len(self.undo_stack) == 0:
            self.menu_bar.entryconfig("← Undo", state="disabled")
        else:
            self.menu_bar.entryconfig("← Undo", state="normal")

        if len(self.redo_stack) == 0:
            self.menu_bar.entryconfig("Redo →", state="disabled")
        else:
            self.menu_bar.entryconfig("Redo →", state="normal")

    # Funciones de limpieza

    def clean_tree(self, tree):
        if tree is not None:
            # Limpiar datos antiguos
            for item in tree.get_children():
                tree.delete(item)

    def clean_structures(self):
        self.BD = None
        self.clean_tree(self.relations_tab_tree)
        self.clean_tree(self.equivalences_tab_tree)
        self.clean_tree(self.facts_tab_tree)
        self.clean_tree(self.nodes_tab_tree)
        self.clean_tree(self.nodes_fact_tab_tree)
        self.graph.clear()
        self.code_counter = 0
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.not_drawn_nodes.clear()
        # self.show_legend_graph = False
        # self.show_legend_matrix = False
        self.redundancy = False

    # Funciones de dibujo

    def draw_figure(self):
        self.draw_graph()
        self.draw_matrix()
   
    def draw_graph(self):

        tiempos = {}
        inicio = time.time()

        self.not_drawn_nodes.clear()

        self.ax_graph.clear()
        self.ax_graph.set_frame_on(False)
        self.ax_graph.axis("off")
        self.fig_graph.subplots_adjust(left=0, right=1, top=1, bottom=0)

        # Crear los diccionarios para acceso rápido
        type_dict = dict(zip(self.BD['Codigo'], self.BD['Tipo']))
        phase_dict = dict(zip(self.BD['Codigo'], self.BD['Fase']))

        # Obtener relaciones y equivalencias
        relations = self.get_edgelist_from_treeview(self.relations_tab_tree)
        equivalences = self.get_edgelist_from_treeview(self.equivalences_tab_tree)

        self.graph = nx.DiGraph()
        G_aux = nx.DiGraph()

        nodes_in_relations = set()
        for rel in relations + equivalences:
            nodes_in_relations.update(rel)

        for node, nodeType in zip(self.BD['Codigo'], self.BD['Tipo']):
            if node in nodes_in_relations:
                self.graph.add_node(node)
                G_aux.add_node(node)
            else:
                if nodeType in ["P", "N"]:
                    self.not_drawn_nodes.add(node)

        self.graph.add_edges_from(relations)
        G_aux.add_edges_from(relations)

        # Mejorar el filtrado de equivalencias
        nodes_set = set(self.graph.nodes)
        equivalences = [e for e in equivalences if all(node in nodes_set for node in e) and not self.exists_relation(e[0], e[1])]


        if not self.redundancy:
            self.graph = nx.transitive_reduction(self.graph)

        self.assign_levels()
        self.assign_levels_AUX(G_aux)

        # Posicionamiento de nodos
        self.pos = nx.multipartite_layout(G_aux, subset_key="subset")
        self.pos = {n: (y, -x) for n, (x, y) in self.pos.items()}
        etiquetas = {n: f"{n[:11]}" for n in self.graph.nodes}

        # Alinear nodos equivalentes
        for n1, n2 in equivalences:
            if n1 in self.pos and n2 in self.pos:
                avg_y = (self.pos[n1][1] + self.pos[n2][1]) / 2
                if self.pos[n1][0] != self.pos[n2][0]:
                    self.pos[n1] = (self.pos[n1][0], avg_y)
                    self.pos[n2] = (self.pos[n2][0], avg_y)
                else:
                    # continue
                    x1, y1 = self.pos[n1]
                    x2, y2 = self.pos[n2]
                    
                    # Crear una curva de Bezier entre los nodos
                    rad = 0.3 if y1 != y2 else 0.15  # Curvatura adaptativa
                    
                    arrow = FancyArrowPatch(
                        (x1, y1), (x2, y2),
                        connectionstyle=f"arc3,rad={rad}",
                        arrowstyle=self.arrowstyle_equivalences.get(),
                        color=self.equi_color,
                        linewidth=self.width_equivalences.get(),
                        linestyle=self.style_equivalences.get(),
                        mutation_scale=15,
                    )
                    self.ax_graph.add_patch(arrow)

        # Dibujar líneas de separación
        y_levels = sorted(set(y for _, y in self.pos.values()))
        for y, y_next in zip(y_levels[:-1], y_levels[1:]):
            espacio = y/2 + y_next/2
            self.ax_graph.hlines(espacio, xmin=-1, xmax=1, colors='gray', linestyles='dashed', alpha=0.6)

        inicio_nodos = time.time()

        # Agrupar nodos por forma
        nodos_por_forma = {'s': [], 'o': [], 'h': []}
        colores_por_nodo = {}

        for nodo in self.graph.nodes:
            tipo = type_dict.get(nodo, "N")  # Valor por defecto "N"
            if tipo == "P":
                forma = "s"
            elif tipo == "N":
                forma = "o"
            elif tipo == "H":
                forma = "h"
            else:
                forma = "o"

            nodos_por_forma[forma].append(nodo)
            colores_por_nodo[nodo] = self.obtener_rgb_por_phase(phase_dict.get(nodo, "Default"))

        for forma, nodos in nodos_por_forma.items():
            if nodos:
                colores = [colores_por_nodo[n] for n in nodos]
                nx.draw_networkx_nodes(self.graph, self.pos, nodelist=nodos, node_color=colores,
                                    node_shape=forma, node_size=4500, ax=self.ax_graph)

        tiempos['Nodos'] = time.time() - inicio_nodos
        inicio_edges_and_labels = time.time()

        # Dibujar aristas y etiquetas
        nx.draw_networkx_edges(self.graph, self.pos, ax=self.ax_graph, arrows=True,
                            edge_color=self.relation_color, style=self.style_relations.get(),
                            arrowstyle=self.arrowstyle_relations.get(), width=self.width_relations.get())

        if equivalences:
            nx.draw_networkx_edges(self.graph, self.pos, edgelist=equivalences, ax=self.ax_graph, arrows=True,
                                edge_color=self.equi_color, style=self.style_equivalences.get(),
                                arrowstyle=self.arrowstyle_equivalences.get(), width=self.width_equivalences.get())

        nx.draw_networkx_labels(self.graph, self.pos, labels=etiquetas, font_size=10, ax=self.ax_graph)

        tiempos['Edges and labels'] = time.time() - inicio_edges_and_labels
        inicio_leyenda = time.time()

        # Leyenda
        if self.show_legend_graph:
            legend_elements = [
                Line2D([0], [0], marker='s', color='w', markerfacecolor='gray', markersize=10, label='Nodo Positivo'),
                Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markersize=10, label='Nodo Negativo'),
                Line2D([0], [0], marker='h', color='w', markerfacecolor='gray', markersize=10, label='Nodo Hecho'),
                Line2D([0], [0], color='black', lw=2, label='Relación o Equivalencia')
            ]
            self.ax_graph.legend(handles=legend_elements, loc='upper right')

        tiempos['Leyenda'] = time.time() - inicio_leyenda
        inicio_draw = time.time()

        self.canvas_graph.draw()

        tiempos['Draw'] = time.time() - inicio_draw
        tiempos['Total'] = time.time() - inicio

        # print(f"Tiempo total: {tiempos['Total']: 4f} segundos.")
        # print(f"Tiempo nodos: {tiempos['Nodos']: 4f} segundos. {(tiempos['Nodos'] * 100 / tiempos['Total']):4f}%")
        # print(f"Tiempo aristas y etiquetas: {tiempos['Edges and labels']: 4f} segundos. {(tiempos['Edges and labels'] * 100 / tiempos['Total']):4f}%")
        # print(f"Tiempo leyenda: {tiempos['Leyenda']: 4f} segundos. {(tiempos['Leyenda'] * 100 / tiempos['Total']):4f}%")
        # print(f"Tiempo draw: {tiempos['Draw']: 4f} segundos. {(tiempos['Draw'] * 100 / tiempos['Total']):4f}%")

    def assign_levels(self):
        """Asigna niveles a los nodos del diagrama de Hasse."""
        niveles = {}
        fuentes = [n for n in self.graph.nodes if self.graph.in_degree(n) == 0]
        cola = [(n, 0) for n in fuentes]

        while cola:
            nodo, nivel = cola.pop(0)
            niveles[nodo] = nivel
            for sucesor in self.graph.successors(nodo):
                cola.append((sucesor, nivel + 1))

        nx.set_node_attributes(self.graph, niveles, "subset")
    
    def assign_levels_AUX(self, graph):
        """Asigna niveles a los nodos del diagrama de Hasse."""
        niveles = {}
        fuentes = [n for n in graph.nodes if graph.in_degree(n) == 0]
        cola = [(n, 0) for n in fuentes]

        while cola:
            nodo, nivel = cola.pop(0)
            niveles[nodo] = nivel
            for sucesor in graph.successors(nodo):
                cola.append((sucesor, nivel + 1))

        nx.set_node_attributes(graph, niveles, "subset")

    def draw_matrix(self):

        inicio = time.time()

        self.ax_matrix.clear()
        self.ax_matrix.set_frame_on(False)
        self.ax_matrix.axis('on')

        # Obtener nodos en orden
        nodos = list(self.graph.nodes)
        if len(nodos) <= 0:
            self.ax_matrix.axis('off')  # Oculta ejes, ticks y labels
            self.canvas_matrix.draw()
            return

        # Obtener la matriz de adyacencia
        matrix = nx.to_numpy_array(self.graph, nodelist=nodos, dtype=int)

        # Incluir equivalencias
        for i, nodoA in enumerate(nodos):
            for j, nodoB in enumerate(nodos):
                if self.exists_equivalencie(nodoA, nodoB):
                    matrix[i][j] = 2

        cmap = cmaps["Blues"]

        if self.show_legend_matrix:

            num_color_labels = 1

            if self.relations_tab_tree.get_children():
                num_color_labels += 1
            if self.equivalences_tab_tree.get_children():
                num_color_labels += 1

            # Configuración de colormap
            cmap_pos = np.linspace(0.0, 1.0, num_color_labels).tolist()
            cmap_pos.reverse()

            # Crear leyenda manualmente
            legend_elements = [
                Line2D([0], [0], marker='s', color='k', markerfacecolor=cmap(cmap_pos.pop()), markersize=10, label="Nada")
            ]
            if self.relations_tab_tree.get_children():
                legend_elements.append(Line2D([0], [0], marker='s', color='k', markerfacecolor=cmap(cmap_pos.pop()), markersize=10, label="Relación"))
            if self.equivalences_tab_tree.get_children():
                legend_elements.append(Line2D([0], [0], marker='s', color='k', markerfacecolor=cmap(cmap_pos.pop()), markersize=10, label="Equivalencia"))
        
            self.ax_matrix.legend(handles=legend_elements, loc="upper right")

        # Añadir etiquetas
        self.ax_matrix.set_xticks(ticks=np.arange(len(self.graph.nodes)), labels=self.graph.nodes)
        self.ax_matrix.set_yticks(ticks=np.arange(len(self.graph.nodes)), labels=self.graph.nodes)

        # Anadir títulos de los ejes
        self.ax_matrix.set_xlabel("Hijos", loc='right')
        self.ax_matrix.set_ylabel("Padres", loc='bottom')
        self.ax_matrix.yaxis.set_label_position("right")
        
        self.ax_matrix.matshow(matrix, cmap=cmap)
        self.canvas_matrix.draw()
        # print(f"draw_matrix: {time.time() - inicio: 4f} segundos.")
 
    def toggle_show_legend_graph(self):
        self.show_legend_graph = not self.show_legend_graph
        self.draw_graph()
    
    def toggle_show_legend_matrix(self):
        self.show_legend_matrix = not self.show_legend_matrix
        self.draw_matrix()
    
    def change_redundancy(self):
        
        self.redundancy = not self.redundancy

        self.draw_figure()
    
    # Funciones de adición

    def add_relation(self):

        node_origin = self.node1_entry_rel.get()
        node_destination = self.node2_entry_rel.get()

        # Verificar si la relación causaría un ciclo
        if self.has_cycle(node_origin, node_destination):
            messagebox.showerror("Error", f"Agregar la relación {node_origin} → {node_destination} crearía un ciclo.")
            return
        
        # Verificar equivalencias del nodo destino
        node_destination_equivalences = self.BD[self.BD["Codigo"]==node_destination]["Equivalencias"].values[0].split(",")
        for equi in node_destination_equivalences:
            if equi != '':
                # Verificar padres
                if not self.exists_relation(node_origin, equi):
                    messagebox.showerror("Error", f"El nodo equivalente a {node_destination}, {equi}, no es hijo de {node_origin}")
                    return
        
        # Verificar equivalencias del nodo origen
        node_origin_equivalences = self.BD[self.BD["Codigo"]==node_origin]["Equivalencias"].values[0].split(",")
        for equi in node_origin_equivalences:
            if equi != '':
                # Verificar hijos
                if not self.exists_relation(equi, node_destination):
                    messagebox.showerror("Error", f"El nodo equivalente a {node_origin}, {equi}, no es padre de {node_destination}")
                    return

        # Verificar si ya existe como relación
        if self.exists_relation(node_origin, node_destination):
            messagebox.showerror("Error", f"Ya existe una relación {node_origin} - {node_destination}")
            return
        
        # Verificar si ya existe como equivalencia
        if self.exists_equivalencie(node_origin, node_destination):
            messagebox.showerror("Error", f"Ya existe una equivalencia {node_origin} - {node_destination}")
            return
        
        # AÑADIR A UNDO
        self.undo_stack.append(self.BD.copy())
        self.redo_stack.clear()
        self.update_undo_redo_status()
        
        # Obtener el índice de la fila correspondiente
        idx = self.BD.index[self.BD["Codigo"] == node_origin][0]

        self.BD.at[idx, "Hijos"] = self.add_string(self.BD.at[idx, "Hijos"], node_destination)
        
        # ACTUALIZAR BD
        self.update_all()
    
    def add_equivalence(self):

        node_A = self.node1_entry_equi.get()
        node_B = self.node2_entry_equi.get()

        # Verificar si la equivalencia causaría un ciclo
        if self.has_cycle(node_A, node_B) or self.has_cycle(node_B, node_A):
            messagebox.showerror("Error", f"Agregar la equivalencia {node_A} = {node_B} crearía un ciclo.")
            return

        # Verificar los padres
        if not self.check_same_parents(node_A, node_B):
            messagebox.showerror("Error", f"{node_A} y {node_B} no tienen los mismos padres")
            return
        
        # Verificar los hijos
        if not self.check_same_sons(node_A, node_B):
            messagebox.showerror("Error", f"{node_A} y {node_B} no tienen los mismos hijos")
            return

        # Verificar si ya existe como relación
        if self.exists_relation(node_A, node_B):
            messagebox.showerror("Error", f"Ya existe una relación {node_A} - {node_B}")
            return
        
        # Verificar si ya existe como equivalencia
        if self.exists_equivalencie(node_A, node_B):
            messagebox.showerror("Error", f"Ya existe una equivalencia {node_A} - {node_B}")
            return
        
        # AÑADIR A UNDO
        self.undo_stack.append(self.BD.copy())
        self.redo_stack.clear()
        self.update_undo_redo_status()
        
        # Obtener el índice de la fila correspondiente
        idx_A = self.BD.index[self.BD["Codigo"] == node_A][0]
        idx_B = self.BD.index[self.BD["Codigo"] == node_B][0]
        
        self.BD.at[idx_A, "Equivalencias"] = self.add_string(self.BD.at[idx_A, "Equivalencias"], node_B)
        self.BD.at[idx_B, "Equivalencias"] = self.add_string(self.BD.at[idx_B, "Equivalencias"], node_A)
        
        # ACTUALIZAR BD
        self.update_all()
        #self.update_equivalences_tab()
        #self.update_widgets()
        #self.draw_figure()

    def add_fact(self):

        node_fact = self.node1_entry_facts.get()
        node_inside = self.node2_entry_facts.get()

        # Verificar si el hecho causaría un ciclo
        if self.has_cycle(node_fact, node_inside):
            messagebox.showerror("Error", f"Agregar el hecho {node_fact} → {node_inside} crearía un ciclo.")
            return
        
        # Verificar si ya existe como relación
        if self.exists_relation(node_fact, node_inside):
            messagebox.showerror("Error", f"Ya existe una relación {node_fact} - {node_inside}")
            return
        
        # Verificar si ya existe como equivalencia
        if self.exists_equivalencie(node_fact, node_inside):
            messagebox.showerror("Error", f"Ya existe una equivalencia {node_fact} - {node_inside}")
            return
        
        # Verificar si ya existe como hecho
        nodes_already_in_facts = set()
        for _, row in self.BD.iterrows():
            node_type = str(row["Tipo"]).strip()
            if node_type == "H":
                facts_codes = str(row.get("Hecho", "")).split(',') if pd.notna(row.get("Hecho")) else []
                for fact_code in facts_codes:
                    fact_code = fact_code.strip()
                    if fact_code:
                        nodes_already_in_facts.add(fact_code)
        
        if node_inside in nodes_already_in_facts:
            messagebox.showerror("Error", f"{node_inside} ya está dentro de otro hecho")
            return

        # AÑADIR A UNDO
        self.undo_stack.append(self.BD.copy())
        self.redo_stack.clear()
        self.update_undo_redo_status()
        
        # Obtener el índice de la fila correspondiente
        idx = self.BD.index[self.BD["Codigo"] == node_fact][0]

        self.BD.at[idx, "Hecho"] = self.add_string(self.BD.at[idx, "Hecho"], node_inside)
        
        # ACTUALIZAR BD
        self.update_all()
        #self.update_facts_tab()
        #self.update_widgets()
        #self.draw_figure()

    def add_node(self):
        popup = tk.Toplevel(root)
        popup.title("Añadir Nodo")
        popup.geometry("300x200")
        popup.grab_set()

        self.save_node_button = tk.Button(popup, text="Añadir", state="disabled")
        self.error_label = tk.Label(popup, text="", fg="red")

        # Excluir columnas "Hijos" y "Equivalencias" para las que se mostrará la tabla
        columns = [col for col in self.BD.columns if col not in ["Codigo", "Hijos", "Equivalencias", "Hecho"]]

        entries = []

        for i, col in enumerate(columns):  # Excluimos "Codigo"
            tk.Label(popup, text=col).grid(row=i, column=0)
            if col == "Tipo":
                entry = ttk.Combobox(popup, textvariable=tk.StringVar(), state="readonly")
                entry['values'] = ('P', 'N')
                entry.current(0)
            else:
                if col == "Nombre":
                    self.OG_name_entry = None
                    self.name_entry_var = tk.StringVar()
                    self.name_entry = tk.Entry(popup, textvariable=self.name_entry_var)
                    self.name_entry_var.trace_add("write", self.validate_entry)  # Ejecuta validar_entry cuando el texto cambia
                    entry = self.name_entry
                else:
                    entry = tk.Entry(popup)
            entry.grid(row=i, column=1)
            entries.append(entry)
        
        self.error_label.grid(row=len(columns), columnspan=2, padx=10, pady=10)

        self.save_node_button.grid(row=(len(columns)+1), columnspan=2, pady=10)
        self.save_node_button.config(command=lambda: self.save_node(columns, entries, popup))

        # Si el usuario cierra la ventana con la "X", también restauramos el bloqueo
        popup.protocol("WM_DELETE_WINDOW", lambda: (popup.destroy(), self.root.grab_set()))

    def add_node_fact(self):
        popup = tk.Toplevel(root)
        popup.title("Añadir Nodo")
        popup.geometry("300x200")
        popup.grab_set()

        self.save_node_button = tk.Button(popup, text="Añadir", state="disabled")
        self.error_label = tk.Label(popup, text="", fg="red")

        # Excluir columnas "Hijos" y "Equivalencias" para las que se mostrará la tabla
        columns = [col for col in self.BD.columns if col not in ["Codigo", "Hijos", "Equivalencias", "Hecho"]]

        entries = []

        for i, col in enumerate(columns):  # Excluimos "Codigo"
            tk.Label(popup, text=col).grid(row=i, column=0)
            if col == "Tipo":
                entry = ttk.Combobox(popup, textvariable=tk.StringVar(), state="readonly")
                entry['values'] = ('H')
                entry.current(0)
            else:
                if col == "Nombre":
                    self.OG_name_entry = None
                    self.name_entry_var = tk.StringVar()
                    self.name_entry = tk.Entry(popup, textvariable=self.name_entry_var)
                    self.name_entry_var.trace_add("write", self.validate_entry)  # Ejecuta validar_entry cuando el texto cambia
                    entry = self.name_entry
                else:
                    entry = tk.Entry(popup)
            entry.grid(row=i, column=1)
            entries.append(entry)
        
        self.error_label.grid(row=len(columns), columnspan=2, padx=10, pady=10)

        self.save_node_button.grid(row=(len(columns)+1), columnspan=2, pady=10)
        self.save_node_button.config(command=lambda: self.save_node(columns, entries, popup))

        # Si el usuario cierra la ventana con la "X", también restauramos el bloqueo
        popup.protocol("WM_DELETE_WINDOW", lambda: (popup.destroy(), self.root.grab_set()))

    
    def save_node(self, columns, entries, popup):
        
        # AÑADIR A UNDO
        self.undo_stack.append(self.BD.copy())
        self.redo_stack.clear()
        self.update_undo_redo_status()

        nuevos_valores_dict = {col: "" for col in self.BD.columns}  # Inicializar todas las columnas con valores vacíos
        
        # Llenar los valores correspondientes en el diccionario
        for col, valor in zip(columns, [entry.get() for entry in entries]):  # "columnas" solo tiene Codigo, Nombre, Tipo
            if col in (["Nombre", "Fase"]):
                valor = valor.strip()
            nuevos_valores_dict[col] = valor
            if col == "Fase" and self.value_in_treeview(self.phase_color_tab_tree, valor, "Fase") == False and valor != '':
                print("Nueva fase añadida!!!!")
                self.phase_color_tab_tree.insert("", "end", values=(str(valor), "#0000FF"))

        # nuevos_valores_dict['Codigo'] = self.generate_numerical_code()    
        nuevos_valores_dict['Codigo'] = nuevos_valores_dict['Nombre']

        # Insertar el nuevo nodo en self.BD con los valores correctos
        new_idx = len(self.BD)
        self.BD.loc[new_idx] = nuevos_valores_dict

        # Destruir la ventana
        popup.destroy()
        self.root.grab_set()

        # ACTUALIZAR
        self.update_all()
        #self.update_nodes_tab()
        #self.update_widgets()

    # Funciones de eliminación

    def delete_relations(self, rows_selected):

        # AÑADIR A UNDO
        self.undo_stack.append(self.BD.copy())
        self.redo_stack.clear()
        self.update_undo_redo_status()
        
        # Eliminamos los nodos seleccionados
        if rows_selected:
            for row in rows_selected:
                item = self.relations_tab_tree.item(row, "values")
                node_origin = item[0]
                node_destination = item[1]
                node_origin_idx = self.BD.index[self.BD["Codigo"] == node_origin][0]
                self.BD.at[node_origin_idx, "Hijos"] = self.delete_string(self.BD.iloc[node_origin_idx]["Hijos"], node_destination)
        
        # ACTUALIZAR BD
        self.update_all()
        #self.update_relations_tab()
        #self.update_widgets()
        #self.draw_figure()
    
    def delete_equivalences(self, rows_selected):

        # AÑADIR A UNDO
        self.undo_stack.append(self.BD.copy())
        self.redo_stack.clear()
        self.update_undo_redo_status()
        
        # Eliminamos los nodos seleccionados
        if rows_selected:
            for row in rows_selected:
                item = self.equivalences_tab_tree.item(row, "values")
                node1 = item[0]
                node2 = item[1]
                node1_idx = self.BD.index[self.BD["Codigo"] == node1][0]
                node2_idx = self.BD.index[self.BD["Codigo"] == node2][0]
                self.BD.at[node1_idx, "Equivalencias"] = self.delete_string(self.BD.iloc[node1_idx]["Equivalencias"], node2)
                self.BD.at[node2_idx, "Equivalencias"] = self.delete_string(self.BD.iloc[node2_idx]["Equivalencias"], node1)
        
        # ACTUALIZAR BD
        self.update_all()
        #self.update_equivalences_tab()
        #self.update_widgets()
        #self.draw_figure()

    def delete_facts(self, rows_selected):

        # AÑADIR A UNDO
        self.undo_stack.append(self.BD.copy())
        self.redo_stack.clear()
        self.update_undo_redo_status()
        
        # Eliminamos los nodos seleccionados
        if rows_selected:
            for row in rows_selected:
                item = self.facts_tab_tree.item(row, "values")
                node_origin = item[0]
                node_destination = item[1]
                node_origin_idx = self.BD.index[self.BD["Codigo"] == node_origin][0]
                self.BD.at[node_origin_idx, "Hecho"] = self.delete_string(self.BD.iloc[node_origin_idx]["Hecho"], node_destination)
        
        # ACTUALIZAR BD
        self.update_all()
        #self.update_facts_tab()
        #self.update_widgets()
        #self.draw_figure()

    def delete_nodes(self):

        # AÑADIR A UNDO
        self.undo_stack.append(self.BD.copy())
        self.redo_stack.clear()
        self.update_undo_redo_status()

        selected = self.nodes_tab_tree.selection()

        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione un nodo para eliminar.")
            return

        confirmacion = messagebox.askyesno("Confirmar", "¿Seguro que quieres eliminar este nodo?")
        if not confirmacion:
            return
        
        rows_to_delete = []
        for item in selected:
            valores = self.nodes_tab_tree.item(item, "values")  # Obtener los valores de la fila seleccionada
            columns = self.nodes_tab_tree.cget("columns")
            row_idx = self.BD[self.BD["Codigo"] == valores[columns.index("Codigo")]].index
            rows_to_delete.append(row_idx[0])

            if not row_idx.empty:
                for col in ["Hijos", "Equivalencias", "Hecho"]:
                    for idx in range(len(self.BD)):
                        self.BD.at[idx, col] = self.delete_string(self.BD.iloc[idx][col], valores[columns.index("Codigo")])
    
                
        # Eliminar de la tabla
        self.BD.drop(rows_to_delete, inplace=True)

        # Resetear el índice para evitar problemas futuros
        self.BD.reset_index(drop=True, inplace=True)

        # ACTUALIZAR
        self.update_all()
    
    def delete_nodes_fact(self):

        # AÑADIR A UNDO
        self.undo_stack.append(self.BD.copy())
        self.redo_stack.clear()
        self.update_undo_redo_status()

        selected = self.nodes_fact_tab_tree.selection()

        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione un nodo para eliminar.")
            return

        confirmacion = messagebox.askyesno("Confirmar", "¿Seguro que quieres eliminar este nodo?")
        if not confirmacion:
            return
        
        rows_to_delete = []
        for item in selected:
            valores = self.nodes_fact_tab_tree.item(item, "values")  # Obtener los valores de la fila seleccionada
            columns = self.nodes_fact_tab_tree.cget("columns")
            row_idx = self.BD[self.BD["Codigo"] == valores[columns.index("Codigo")]].index
            rows_to_delete.append(row_idx[0])

            if not row_idx.empty:
                for col in ["Hijos", "Equivalencias", "Hecho"]:
                    for idx in range(len(self.BD)):
                        self.BD.at[idx, col] = self.delete_string(self.BD.iloc[idx][col], valores[columns.index("Codigo")])
    
                
        # Eliminar de la tabla
        self.BD.drop(rows_to_delete, inplace=True)

        # Resetear el índice para evitar problemas futuros
        self.BD.reset_index(drop=True, inplace=True)

        # ACTUALIZAR
        self.update_all()

    # Funciones de edición

    def edit_node(self):

        popup = tk.Toplevel(root)
        popup.title("Editar Nodo")
        popup.geometry("300x200")
        popup.grab_set()

        self.save_node_button = tk.Button(popup, text="Guardar", state="disabled")
        self.error_label = tk.Label(popup, text="", fg="red")

        columns = self.nodes_tab_tree.cget("columns")
        code_index = columns.index("Codigo")

        item_id = self.nodes_tab_tree.selection()
        valores = self.nodes_tab_tree.item(item_id, "values")
        code = valores[code_index]

        valores = [val for col, val in zip(columns, valores) if col != "Codigo"]
        columns = [col for col in columns if col != "Codigo"]

        entries = []

        for i, col in enumerate(columns):  # Excluimos "Codigo"
            tk.Label(popup, text=col).grid(row=i, column=0)
            if col == "Tipo":
                entry = ttk.Combobox(popup, textvariable=tk.StringVar(), state="readonly")
                entry['values'] = ('P', 'N', 'H')
                entry.set(valores[i])
            else:
                if col == "Nombre":
                    self.OG_name_entry = valores[i]
                    self.name_entry_var = tk.StringVar()
                    self.name_entry = tk.Entry(popup, textvariable=self.name_entry_var)
                    self.name_entry_var.trace_add("write", self.validate_entry)  # Ejecuta validar_entry cuando el texto cambia
                    entry = self.name_entry
                else:
                    entry = tk.Entry(popup)
            entry.insert(0, valores[i])
            entry.grid(row=i, column=1)
            entries.append(entry)
        
        self.error_label.grid(row=len(columns), columnspan=2, padx=10, pady=10)

        self.save_node_button.grid(row=(len(columns)+1), columnspan=2, pady=10)
        self.save_node_button.config(command=lambda: self.save_node_edition(columns, entries, popup, code))

        # Si el usuario cierra la ventana con la "X", también restauramos el bloqueo
        popup.protocol("WM_DELETE_WINDOW", lambda: (popup.destroy(), self.root.grab_set()))
    
    def edit_node_fact(self):

        popup = tk.Toplevel(root)
        popup.title("Editar Nodo")
        popup.geometry("300x200")
        popup.grab_set()

        self.save_node_button = tk.Button(popup, text="Guardar", state="disabled")
        self.error_label = tk.Label(popup, text="", fg="red")

        columns = self.nodes_fact_tab_tree.cget("columns")
        code_index = columns.index("Codigo")

        item_id = self.nodes_fact_tab_tree.selection()
        valores = self.nodes_fact_tab_tree.item(item_id, "values")
        code = valores[code_index]

        valores = [val for col, val in zip(columns, valores) if col != "Codigo"]
        columns = [col for col in columns if col != "Codigo"]

        entries = []

        for i, col in enumerate(columns):  # Excluimos "Codigo"
            tk.Label(popup, text=col).grid(row=i, column=0)
            if col == "Tipo":
                entry = ttk.Combobox(popup, textvariable=tk.StringVar(), state="readonly")
                entry['values'] = ('P', 'N', 'H')
                entry.set(valores[i])
            else:
                if col == "Nombre":
                    self.OG_name_entry = valores[i]
                    self.name_entry_var = tk.StringVar()
                    self.name_entry = tk.Entry(popup, textvariable=self.name_entry_var)
                    self.name_entry_var.trace_add("write", self.validate_entry)  # Ejecuta validar_entry cuando el texto cambia
                    entry = self.name_entry
                else:
                    entry = tk.Entry(popup)
            entry.insert(0, valores[i])
            entry.grid(row=i, column=1)
            entries.append(entry)
        
        self.error_label.grid(row=len(columns), columnspan=2, padx=10, pady=10)

        self.save_node_button.grid(row=(len(columns)+1), columnspan=2, pady=10)
        self.save_node_button.config(command=lambda: self.save_node_edition(columns, entries, popup, code))

        # Si el usuario cierra la ventana con la "X", también restauramos el bloqueo
        popup.protocol("WM_DELETE_WINDOW", lambda: (popup.destroy(), self.root.grab_set()))
    
    def save_node_edition(self, columns, entries, popup, code):
        
        # AÑADIR A UNDO
        self.undo_stack.append(self.BD.copy())
        self.redo_stack.clear()
        self.update_undo_redo_status()

        idx = self.BD.index[self.BD["Codigo"] == code][0]
        
        # Llenar los valores correspondientes en el diccionario
        for col, valor in zip(columns, [entry.get() for entry in entries]):  # "columnas" solo tiene Codigo, Nombre, Tipo
            if col in (["Nombre", "Fase"]):
                valor = valor.strip()
            if col == "Tipo" and self.BD.at[idx, col] != valor:
                if ((self.BD.at[idx, col] in ("P", "N") and valor == "H")
                    or (self.BD.at[idx, col]  == "H" and valor in ("P", "N"))):
                    for c in ["Hijos", "Equivalencias", "Hecho"]:
                        for i in range(len(self.BD)):
                            self.BD.at[i, c] = self.delete_string(self.BD.iloc[i][c], code)
                            if i == idx:
                                self.BD.at[i, c] = ""
                    entry_new_text = self.delete_string(self.facts_entry.get(), code)
                    self.facts_entry.delete(0, tk.END)
                    self.facts_entry.insert(0, entry_new_text)
            if col == "Fase":
                if self.value_in_treeview(self.phase_color_tab_tree, valor, "Fase") == False and valor != '':
                    print("Nueva fase añadida!!!!")
                    self.phase_color_tab_tree.insert("", "end", values=(str(valor), "#0000FF"))

            self.BD.at[idx, col] = valor

        # Cambiar el valor del código
        old_code = self.BD.at[idx, "Codigo"]
        new_code = self.BD.at[idx, "Nombre"]
        self.BD.at[idx, "Codigo"] = self.BD.at[idx, "Nombre"]

        for col in ["Hijos", "Equivalencias", "Hecho"]:
            self.BD[col] = self.BD[col].apply(self.substitute_substring_in_string, args=(old_code, new_code))

        # Destruir la ventana
        popup.destroy()
        self.root.grab_set()

        # ACTUALIZAR
        self.update_all()
        # self.update_nodes_tab()
        # self.update_widgets()
        # self.draw_figure()

    def edit_color(self, color_container):
        color = colorchooser.askcolor(title="Selecciona un color")[1]
        if color:
            if color_container == "Relation":
                self.relation_color = color
            elif color_container == "Equivalence":
                self.equi_color = color
            #self.update_all()
            self.draw_figure()

    def edit_phase_color(self):
        color = colorchooser.askcolor(title="Selecciona un color")[1]
        if color:
            item_id = self.phase_color_tab_tree.selection()[0]
            item = self.phase_color_tab_tree.item(item_id)["values"]
            self.phase_color_tab_tree.item(item_id, values=(item[0], color))
            #self.update_all()
            self.draw_figure()
            
    # Funciones de filtrado

    def pass_filter(self, to_filter_list):

        #print(list(to_filter_list))
        
        if self.filtro == "":
            #print("VACÍO")
            return True
        
        selected_columns = [i for i in self.filter_listbox.curselection()]
        if len(selected_columns) == 0:
            selected_columns = list(range(len(self.BD.columns)))

        selected_columns = [str(col) for col in self.BD.columns[selected_columns]]

        # CAMBIAR LA FORMA EN LA QUE SE CREA el nuevo 'to_filter_list'
        # Para phase deben añadirse el nodo hecho ¿y/o? los nodos que engloba

        # Tomamos la lista y limpiamos espacios en cada elemento
        filter_list = [item.strip() for item in self.filtro.split(",")]

        # Tomamos solo las columnas seleccionadas y limpiamos espacios
        to_filter_list = [str(item).strip() for item in to_filter_list[selected_columns].tolist()]

        # print(f"{to_filter_list} {type(to_filter_list)}")

        # Quitamos las comas
        # to_filter_list = " ".join(to_filter_list).strip(",")

        # Convertimos todas las mayúculas a minúsculas
        if not self.filterApplyMayMin.get():
            filter_list = [f.lower() for f in filter_list]
            to_filter_list = [f.lower() for f in to_filter_list]

        # Eliminamos diacríticos
        if not self.filterApplyDiacritics.get():
            for i, f in enumerate(filter_list):
                f = unicodedata.normalize('NFD', f)
                f = "".join(c for c in f if unicodedata.category(c) != 'Mn')
                filter_list[i] = f
            for i, f in enumerate(to_filter_list):
                f = unicodedata.normalize('NFD', f)
                f = "".join(c for c in f if unicodedata.category(c) != 'Mn')
                to_filter_list[i] = f
        # to_filter_list = unicodedata.normalize('NFD', to_filter_list)
        # to_filter_list = "".join(c for c in to_filter_list if unicodedata.category(c) != 'Mn')
        
        if not self.filterApplyFullWords.get():
            # print(f"{filter_list} <=> {to_filter_list} = {any(elem_fl in elem_tfl for elem_fl in filter_list for elem_tfl in to_filter_list)}")
            return any(elem_fl in elem_tfl for elem_fl in filter_list for elem_tfl in to_filter_list)
        else:
            # print(f"{filter_list} <=> {to_filter_list} = {any(elem in to_filter_list for elem in filter_list)}")
            return any(elem in to_filter_list for elem in filter_list)

    # Funciones de zoom

    def zoom_on_nodes(self, selected_nodes):
        if not selected_nodes:
            return
        
        # Calcular los límites del zoom basado en los nodos seleccionados
        margin = 0.2
        x_min, x_max, y_min, y_max = float('inf'), -float('inf'), float('inf'), -float('inf')
        
        for node in selected_nodes:
            x, y = self.pos[node]
            x_min = min(x_min, x - margin)
            x_max = max(x_max, x + margin)
            y_min = min(y_min, y - margin)
            y_max = max(y_max, y + margin)
        
        # Ajustar los límites del gráfico
        self.ax_graph.set_xlim(x_min, x_max)
        self.ax_graph.set_ylim(y_min, y_max)
        #plt.draw()
        self.canvas_graph.draw()

    def update_zoom(self):
        #selected_indices = listbox.curselection()
        #selected_nodes = [int(listbox.get(i).split()[1]) for i in selected_indices]

        selected_nodes = []
        for _, row in self.BD.iterrows():
            self.pass_filter(row)
            if self.pass_filter(row):
                node_code = str(row.get("Codigo",""))
                if (self.value_in_treeview(self.relations_tab_tree, node_code, "Unidad 1") or
                    self.value_in_treeview(self.relations_tab_tree, node_code, "Unidad 2") or
                    self.value_in_treeview(self.equivalences_tab_tree, node_code, "Unidad 1") or
                    self.value_in_treeview(self.equivalences_tab_tree, node_code, "Unidad 2")):
                    selected_nodes.append(node_code)
        print(selected_nodes)
        # Hacer el zoom en los nodos seleccionados
        self.zoom_on_nodes(selected_nodes)
        #canvas.draw()
        self.canvas_graph.draw()

    # UNDO

    def undo(self):
        """Deshacer la última acción"""
        if not self.undo_stack:
            return
        
        previous_db = self.undo_stack.pop()
        self.redo_stack.append(self.BD.copy())
        self.BD = previous_db.copy()

        self.update_undo_redo_status()
        
        self.update_all()
    
    # REDO

    def redo(self):
        """Rehacer la última acción deshecha"""
        if not self.redo_stack:
            return
        
        previous_db = self.redo_stack.pop()
        self.undo_stack.append(self.BD.copy())
        self.BD = previous_db.copy()

        self.update_undo_redo_status()

        self.update_all()

    # Funciones para botones

    def toggle_button_style(self, btn):
        if btn.config('relief')[-1] == 'raised':
            btn.config(relief='sunken', bg='white')
        else:
            btn.config(relief='raised', bg=self.toolbar_graph.cget("bg"))
    
    # Funciones auxiliares
    
    def has_cycle(self, nodeA, nodeB):
        return self.search_cycle(nodeA, nodeB)

    def search_cycle(self, node_origin, node_destination):
        """Verifica si agregar node_destination como hijo de node_origin crearía un ciclo."""
        to_visit = [node_destination]  # Comenzamos desde el nodo destino
        to_visit.extend(self.get_equivalences(node_destination))
        visited = set()

        while to_visit:
            current = to_visit.pop()
            # current_equivalences = self.get_equivalences(current)
            if current in visited:
                continue
            visited.add(current)
            # visited.union(set(current_equivalences))

            # Si encontramos el nodo de origen en la rama, hay un ciclo
            if current == node_origin:
                # print(f"{node_origin}, {node_destination}, {visited}")
                return True

            # Obtener los hijos del nodo actual
            sons_str = self.BD.loc[self.BD["Codigo"] == current, "Hijos"].values
            if len(sons_str) > 0 and isinstance(sons_str[0], str):  # Verificar si hay hijos
                sons_list = sons_str[0].split(",")  # Convertir a lista
                to_visit.extend(sons_list)  # Agregar hijos a la pila de búsqueda
                for son in sons_list:
                    son_equis = self.get_equivalences(son)
                    for son_equi in son_equis:
                        if son_equi not in visited:
                            to_visit.append(son_equi)

        # print(f"{node_origin}, {node_destination}, {visited}")
        return False  # No se encontró ciclo
    
    def check_same_parents(self, nodeA, nodeB):
        return self.contains_both(self.BD, nodeA, nodeB, 'Hijos')
    
    def check_same_sons(self, nodeA, nodeB):
        return self.BD[self.BD['Codigo'] == nodeA]['Hijos'].values[0] == self.BD[self.BD['Codigo'] == nodeB]['Hijos'].values[0]
    
    def contains_both(self, df, nodeA, nodeB, column):
        # print(f"{nodeA} - {nodeB}")
        return df[column].apply(lambda x: self.contains_both_check(x, nodeA, nodeB)).all()

    def contains_both_check(self, val, nodeA, nodeB):
        val = val.split(",")
        contains_nodeA = nodeA in val
        contains_nodeB = nodeB in val
        # print(f"{contains_nodeA}, {contains_nodeB} in {val}")
        return (contains_nodeA and contains_nodeB) or (not contains_nodeA and not contains_nodeB)

    def exists_tuple(self, tree, values_to_search):
        for item in tree.get_children():  # Recorrer todas las filas
            row_values = tree.item(item, "values")  # Obtener los valores de la fila
            if tuple(values_to_search) == row_values:  # Comparar con la tupla buscada
                return True  # La tupla existe
        return False  # No se encontró
    
    def exists_relation(self, node1, node2):
        values_to_search_1 = [node1, node2]
        values_to_search_2 = [node2, node1]

        if self.exists_tuple(self.relations_tab_tree, values_to_search_1):
            return True
        if self.exists_tuple(self.relations_tab_tree, values_to_search_2):
            return True
        return False

    def exists_equivalencie(self, node1, node2):
        values_to_search_1 = [node1, node2]
        values_to_search_2 = [node2, node1]

        if self.exists_tuple(self.equivalences_tab_tree, values_to_search_1):
            return True
        if self.exists_tuple(self.equivalences_tab_tree, values_to_search_2):
            return True
        return False
    
    def exists_fact(self, node1, node2):
        values_to_search_1 = [node1, node2]
        values_to_search_2 = [node2, node1]

        if self.exists_tuple(self.facts_tab_tree, values_to_search_1):
            return True
        if self.exists_tuple(self.facts_tab_tree, values_to_search_2):
            return True
        return False

    def name_to_code(self, name):
        return self.BD.loc[self.BD['Nombre'] == name, 'Codigo'].iloc[0]

    def code_to_name(self, code):
        return self.BD.loc[self.BD['Codigo'] == code, 'Nombre'].iloc[0]
    
    def generate_numerical_code(self):
        indice = self.code_counter
        self.code_counter = self.code_counter + 1
        return f"{indice:d}"  

    def get_edgelist_from_treeview(self, tree):
        edgelist = []
        #print([str(tree.item(child, "values")) for child in tree.get_children()])
        for child in tree.get_children():
            values = tree.item(child, "values")  # Obtiene los valores de la fila
            if len(values) >= 2:  # Asegurar que haya al menos dos columnas
                edgelist.append([values[0], values[1]])
        return edgelist
    
    def get_equivalences(self, node):
        equi_str = self.BD.loc[self.BD["Codigo"] == node, "Equivalencias"].values
        equi_list = []
        if len(equi_str) > 0 and isinstance(equi_str[0], str):  # Verificar si hay hijos
            equi_list = equi_str[0].split(",")  # Convertir a lista
            return equi_list
        return equi_list

    def add_string(self, original_str, new_value):
        """Añade un nuevo valor a una cadena separada por comas, evitando duplicados."""
        if pd.isna(original_str) or original_str == "":
            return new_value  # Si está vacío, simplemente asignamos el nuevo valor
        
        sons_list = original_str.split(",")  # Convertimos la cadena en lista
        sons_list.append(new_value)  # Agregamos el nuevo valor
        return ",".join(sons_list)  # Convertimos de vuelta a string

    def delete_string(self, original_str, str_to_delete):
        # Convertir la cadena a lista separada por comas
        list = original_str.split(',')
        # Filtrar la lista para eliminar la cadena deseada
        filtered_list = [item for item in list if item != str_to_delete]
        # Unir la lista de nuevo en un solo string
        return ','.join(filtered_list)
    
    def substitute_substring_in_string(self, original_str, original_substring, new_substring):
        if pd.isna(original_str) or original_str == "":
            return original_str
        partes = original_str.split(",")
        partes = [new_substring if parte.strip() == original_substring else parte for parte in partes]
        return ",".join(partes)

    def get_values_from_string(self, entry_string):
        values = [v.strip() for v in entry_string.split(',') if v.strip()]
        return values

    def value_in_treeview(self, tree, valor, columna):
        columns = tree["columns"]
        if columna in columns:
            column_idx = columns.index(columna)
        else:
            print("No existe la columna")
            return False
        
        for item in tree.get_children():
            # Obtener los valores de la fila
            valores = tree.item(item, "values")
            if valores and valores[column_idx] == valor:  # Compara el valor con la tupla de valores
                return True
        return False

    def obtener_rgb_por_phase(self, phase_val):
        # Obtiene todas las filas del Treeview
        for item in self.phase_color_tab_tree.get_children():
            # Obtiene los valores de la fila
            values = self.phase_color_tab_tree.item(item, "values")
            
            # Suponiendo que Fase está en la columna 0, R en 1, G en 2, B en 3
            phase, color = values
            
            # Si encontramos la fase que estamos buscando, retornamos los valores R, G y B
            if phase == phase_val:
                return color
        return "#0080FF"  # Si no se encuentra la fase, devolvemos azul genérico

    def search_path_to_objective(self, origen, objetivo):
        """Expande sin recursión para encontrar la ruta completa hasta el objetivo."""
        """self.todos_los_hechos = {
            str(row['Codigo']): set(row['Hecho'].split(','))
            for _, row in self.BD.iterrows()
        }"""

        cola = deque([(origen, [origen])])  # (actual, camino)

        while cola:
            actual, camino = cola.popleft()
            elementos = self.todos_los_hechos.get(actual, [])

            for elem in elementos:
                if elem == objetivo:
                    return camino + [elem]
                elif elem in self.todos_los_hechos:
                    cola.append((elem, camino + [elem]))

        return None  # No se encontró camino

    def find_fact_with_path(self, objetivo):
        
        inicio = time.time()
        beginning = time.time()

        """self.todos_los_hechos = {
            str(row['Codigo']): set(row['Hecho'].split(','))
            for _, row in self.BD.iterrows()
        }
        self.entries_strings = self.get_values_from_string(str(self.facts_entry.get()))
        self.hechos_visibles = {clave: valor for clave, valor in self.todos_los_hechos.items() if clave in self.entries_strings}"""

        contenido_en = defaultdict(set)

        # Relaciones inversas
        for hecho, elementos in self.todos_los_hechos.items():
            for elem in elementos:
                if elem in self.todos_los_hechos:
                    contenido_en[elem].add(hecho)
        
        tiempo_contenedores = time.time() - beginning
        beginning = time.time()

        # Buscamos rutas completas desde hechos visibles
        rutas = {}
        for hecho in self.hechos_visibles:
            camino = self.search_path_to_objective(hecho, objetivo)
            if camino:
                rutas[hecho] = camino

        if not rutas:
            return objetivo  # No se encontró en ningún hecho visible
        
        tiempo_rutas = time.time() - beginning
        beginning = time.time()

        # Ahora subimos en la jerarquía para encontrar el más externo
        visitados = set()
        cola = deque(rutas.keys())
        resultado = set(rutas.keys())

        while cola:
            actual = cola.popleft()
            visitados.add(actual)

            for contenedor in contenido_en.get(actual, []):
                if contenedor in self.hechos_visibles and contenedor not in visitados:
                    resultado.discard(actual)
                    resultado.add(contenedor)
                    cola.append(contenedor)

        tiempo_jerarquia = time.time() - beginning
        tiempo_total = time.time() - inicio

        if resultado:
            hecho_externo = resultado.pop()
            #return hecho_externo, rutas[hecho_externo]
            return hecho_externo

        return objetivo
    
    def find_fact_with_path_with_times(self, objetivo):

        tiempos = {}
        tiempos['Total'] = 0.0
        tiempos['Contenedores'] = 0.0
        tiempos['Rutas'] = 0.0
        tiempos['Jerarquia'] = 0.0
        
        inicio = time.time()
        beginning = time.time()

        """self.todos_los_hechos = {
            str(row['Codigo']): set(row['Hecho'].split(','))
            for _, row in self.BD.iterrows()
        }
        self.entries_strings = self.get_values_from_string(str(self.facts_entry.get()))
        self.hechos_visibles = {clave: valor for clave, valor in self.todos_los_hechos.items() if clave in self.entries_strings}"""

        contenido_en = defaultdict(set)

        # Relaciones inversas
        for hecho, elementos in self.todos_los_hechos.items():
            for elem in elementos:
                if elem in self.todos_los_hechos:
                    contenido_en[elem].add(hecho)
        
        tiempo_contenedores = time.time() - beginning
        tiempos["Contenedores"] = tiempo_contenedores
        beginning = time.time()

        # Buscamos rutas completas desde hechos visibles
        rutas = {}
        for hecho in self.hechos_visibles:
            camino = self.search_path_to_objective(hecho, objetivo)
            if camino:
                rutas[hecho] = camino

        tiempo_rutas = time.time() - beginning
        tiempos["Rutas"] = tiempo_rutas
        beginning = time.time()

        if not rutas:
            tiempos["Total"] = time.time() - inicio
            return objetivo, tiempos  # No se encontró en ningún hecho visible
        

        # Ahora subimos en la jerarquía para encontrar el más externo
        visitados = set()
        cola = deque(rutas.keys())
        resultado = set(rutas.keys())

        while cola:
            actual = cola.popleft()
            visitados.add(actual)

            for contenedor in contenido_en.get(actual, []):
                if contenedor in self.hechos_visibles and contenedor not in visitados:
                    resultado.discard(actual)
                    resultado.add(contenedor)
                    cola.append(contenedor)

        tiempo_jerarquia = time.time() - beginning
        tiempos["Jerarquia"] = tiempo_jerarquia
        tiempo_total = time.time() - inicio
        tiempos["Total"] = tiempo_total

        if resultado:
            hecho_externo = resultado.pop()
            #return hecho_externo, rutas[hecho_externo]
            return hecho_externo, tiempos

        return objetivo, tiempos

    def block_scroll(self, event):
        return "break"

    def validate_entry(self, *args):
        texto = self.name_entry.get().strip()
        #print(f"{texto} in {list(self.BD["Nombre"])} -> {texto in list(self.BD["Nombre"])}")
        if texto == "":
            self.error_label.config(text="⚠️ El campo 'Nombre' no puede estar vacío.")
            self.save_node_button.config(state="disabled")
        elif re.search(r'[;,]', texto):
            self.error_label.config(text=f"⚠️ No puede haber ',' ni ';' en el campo 'Nombre'")
            self.save_node_button.config(state="disabled")
        elif texto in list(self.BD["Nombre"]) and texto != self.OG_name_entry:
            self.error_label.config(text=f"🚫 '{texto}' no está permitido.")
            self.save_node_button.config(state="disabled")
        else:
            self.error_label.config(text="")
            self.save_node_button.config(state="normal")

    # Clases

    class Toolbar(NavigationToolbar2Tk):

        # Sobrescribimos la lista de herramientas para quitar el botón de "Configure subplots"
        toolitems = [
            ('Home', 'Resetear a la vista original', 'home', 'home'),
            ('Back', 'Vista anterior', 'back', 'back'),
            ('Forward', 'Vista posterior', 'forward', 'forward'),
            ('Pan', 'Moverse con el botón izq. del ratón', 'move', 'pan'),
            ('Zoom', 'Zoom con rectángulo', 'zoom_to_rect', 'zoom'),
            # 'Subplots' ha sido eliminado
            ('Save', 'Guardar la figura', 'filesave', 'save_figure'),
        ]

        def set_message(self, s):
            pass

        def save_figure(self, *args, **kwargs):
            root.withdraw()

            width_px = simpledialog.askinteger("Guardar imagen", "Ingrese ancho en píxeles:", initialvalue=100, minvalue=100, maxvalue=5000)
            if not width_px:
                root.deiconify()
                return 

            height_px = simpledialog.askinteger("Guardar imagen", "Ingrese alto en píxeles:", initialvalue=100, minvalue=100, maxvalue=5000)

            if width_px and height_px:
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("SVG files", "*.svg"), ("All Files", "*.*")]
                )

                if file_path:
                    fig = self.canvas.figure
                    dpi = 100

                    # Guardar tamaño original
                    original_size = fig.get_size_inches()

                    # Cambiar tamaño solo para guardar
                    fig.set_size_inches(width_px / dpi, height_px / dpi)
                    fig.savefig(file_path, dpi=dpi)

                    # Restaurar tamaño original
                    fig.set_size_inches(original_size)
                    self.canvas.draw()  # Redibujar para aplicar tamaño original de nuevo en pantalla

            root.deiconify()
    

if __name__ == "__main__":


    root = tk.Tk()
    app = GraphApp(root)
    root.mainloop()
