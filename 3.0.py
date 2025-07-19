from PyQt5.QtWidgets import QMainWindow, QLabel, QFileDialog, QAction, QToolBar, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QColorDialog, QSlider, QScrollArea, QGridLayout, QSizePolicy, QInputDialog, QDialog, QListWidget, QVBoxLayout, QPushButton, QLabel, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QApplication
from PyQt5.QtGui import QPixmap, QPainter, QColor, QImage, QIcon, QFont
from PyQt5.QtCore import Qt, QPoint, QRectF, QSize, QTimer

from collections import deque
import json
import os
import math

# color palette
class PaletteWidget(QWidget):
    def __init__(self, set_color_callback, get_active_color_callback):
        super().__init__()
        self.set_color_callback = set_color_callback
        self.get_active_color_callback = get_active_color_callback
        self.colors = []
        self.buttons = []
        self.grid_cols = 8
        self.grid = QGridLayout()
        self.grid.setSpacing(4)
        self.setLayout(self.grid)
        self.setMinimumWidth(120)

    def set_colors(self, color_list):
        for btn in self.buttons:
            self.grid.removeWidget(btn)
            btn.setParent(None)
        self.buttons.clear()
        self.colors = list(color_list)
        for idx, color in enumerate(self.colors):
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"background: {color.name()}; border: 2px solid {'#333' if color == self.get_active_color_callback() else '#ccc'};")
            btn.clicked.connect(lambda checked=False, i=idx: self.set_color_callback(i))
            self.grid.addWidget(btn, idx // self.grid_cols, idx % self.grid_cols)
            self.buttons.append(btn)
        plus_btn = QPushButton("+")
        plus_btn.setFixedSize(24, 24)
        plus_btn.clicked.connect(lambda checked=False: self.set_color_callback('plus'))
        row = len(self.colors) // self.grid_cols
        col = len(self.colors) % self.grid_cols
        self.grid.addWidget(plus_btn, row, col)
        self.buttons.append(plus_btn)
        self.update()
    
    def set_active_highlight(self):
        for idx, btn in enumerate(self.buttons[:-1]):
            btn.setStyleSheet(f"background: {self.colors[idx].name()}; border: 2px solid {'#333' if self.colors[idx] == self.get_active_color_callback() else '#ccc'};")

# collision version of the pallette
class CollisionPaletteWidget(QWidget):
    def __init__(self, set_color_callback, get_active_color_callback):
        super().__init__()
        self.set_color_callback = set_color_callback
        self.get_active_color_callback = get_active_color_callback
        self.colors = [QColor(255,0,0)]  # allat palette for just red :fire:
        self.buttons = []
        self.grid = QGridLayout()
        self.grid.setSpacing(4)
        self.setLayout(self.grid)
        self.setMinimumWidth(80)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        for idx, color in enumerate(self.colors):
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"background: {color.name()}; border: 2px solid {'#333' if color == self.get_active_color_callback() else '#ccc'};") # yall heard of that ratatouille fleshlight? i know that shit is so tight
            btn.clicked.connect(lambda checked=False, i=idx: self.set_color_callback(i))
            self.grid.addWidget(btn, 0, idx)
            self.buttons.append(btn)
        self.update()

    def set_active_highlight(self):
        for idx, btn in enumerate(self.buttons):
            btn.setStyleSheet(f"background: {self.colors[idx].name()}; border: 2px solid {'#333' if self.colors[idx] == self.get_active_color_callback() else '#ccc'};")

# canvas
class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Father Map Editor 3.0")
        self.resize(1200, 800)

        # area
        self.image_label = QLabel()
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.pixmap = QPixmap(2048, 2048) # default size, i'll add an option to make it bigger later
        self.pixmap.fill(Qt.white)
        self.image_label.setPixmap(self.pixmap)

        # collision layer
        self.collision_layer = QPixmap(self.pixmap.size())
        self.collision_layer.fill(QColor(255,255,255,0))  # transparent
        self.collision_mode = False
        self.collision_color = QColor(255,0,0)
        self.collision_palette = [QColor(255,0,0)]
        self.collision_brush_index = 0

        # set brush
        self.zoom = 1.0
        self.offset = [0.0, 0.0]
        self.last_pan_point = None
        self.drawing = False
        self.brush_size = 1
        self.active_color = QColor(0, 0, 0)
        self.eraser_mode = False
        self.palette_colors = [QColor(0,0,0), QColor(255,255,255)] # add more colors later

        # undo and redo
        self.undo_stack = deque(maxlen=50)
        self.redo_stack = deque(maxlen=50)

        # stamps
        self.stamp_folder = "stamps"
        self.stamps = {}
        self.active_stamp = None
        self.stamp_preview_pos = None
        self.stamp_preview_timer = QTimer()
        self.stamp_preview_timer.timeout.connect(self._update_stamp_preview)
        self.stamp_preview_timer.setInterval(16)  # 60Hz, make this flexivle later

        # prefabs
        self.prefab_folder = "prefabs"
        self.prefabs = {}
        self.active_prefab = None
        self.prefab_preview_pos = None
        self.prefab_objects = []
        self.prefab_preview_timer = QTimer()
        self.prefab_preview_timer.timeout.connect(self._update_prefab_preview)
        self.prefab_preview_timer.setInterval(16)

        # npcs
        self.npc_folder = "npcs"
        self.npcs = {}
        self.active_npc = None
        self.npc_preview_pos = None
        self.npc_objects = []
        self.npc_preview_timer = QTimer()
        self.npc_preview_timer.timeout.connect(self._update_npc_preview)
        self.npc_preview_timer.setInterval(16)

        # triggers
        self.trigger_mode = False
        self.trigger_start_pos = None
        self.trigger_end_pos = None
        self.trigger_rectangles = []
        self.active_trigger_edit = None

        # enemy spawn areas
        self.spawn_mode = False
        self.spawn_areas = []
        self.active_spawn_edit = None

        # grid
        self.show_grid = False
        self.grid_size = 32

        # toolbar
        self._create_toolbar()
        self.trigger_btn.hide()
        self.spawn_btn.hide()

        # other stuff
        self._create_palettes()
        self._create_layout()
        self._load_stamps()
        self._load_prefabs()
        self._load_npcs()
        self._setup_refresh_rate()
        self.image_label.installEventFilter(self)
        self.enemy_list = ["jimmy"] # this is a placeholder in case the team forgets to add enemies

        # tiles (what makes this editor different from ms paint)
        self.tile_stamp_folder = "tiles"
        self.tiles = {}
        self.active_tile_stamp = None
        self.tile_stamp_preview_pos = None
        self._load_tiles()
        self.tile_drawing = False
        self.last_tile_stamp_pos = None

# i lied, here's the actually toolbar
    def _create_toolbar(self):
        toolbar = QToolBar()
        
        # file actions
        open_action = QAction("Open Image", self)
        open_action.triggered.connect(self.open_image)
        toolbar.addAction(open_action)
        
        save_action = QAction("Save Primary Image", self)
        save_action.triggered.connect(self.save_image)
        toolbar.addAction(save_action)
        
        export_action = QAction("Export Map", self)
        export_action.triggered.connect(self.export_all)
        toolbar.addAction(export_action)
        
        import_action = QAction("Import Map", self)
        import_action.triggered.connect(self.import_map_package)
        toolbar.addAction(import_action)
        
        undo_action = QAction("Undo", self)
        undo_action.triggered.connect(self.undo)
        toolbar.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.triggered.connect(self.redo)
        toolbar.addAction(redo_action)

        self.eraser_btn = QPushButton("Eraser OFF")
        self.eraser_btn.setCheckable(True)
        self.eraser_btn.clicked.connect(self.toggle_eraser)
        toolbar.addWidget(self.eraser_btn)

        self.brush_slider = QSlider(Qt.Orientation.Horizontal)
        self.brush_slider.setMinimum(1)
        self.brush_slider.setMaximum(32) # for the crazy people
        self.brush_slider.setValue(self.brush_size)
        self.brush_slider.setFixedWidth(100)
        self.brush_slider.valueChanged.connect(self.set_brush_size)
        toolbar.addWidget(QLabel("Brush Size"))
        toolbar.addWidget(self.brush_slider)

        self.collision_btn = QPushButton("Edit Collision Layer")
        self.collision_btn.setCheckable(True)
        self.collision_btn.clicked.connect(self.toggle_collision_mode)
        toolbar.addWidget(self.collision_btn)

        self.stamp_btn = QPushButton("Place Stamp")
        self.stamp_btn.clicked.connect(self.open_stamp_dialog)
        toolbar.addWidget(self.stamp_btn)

        self.prefab_btn = QPushButton("Place Prefab")
        self.prefab_btn.clicked.connect(self.open_prefab_dialog)
        toolbar.addWidget(self.prefab_btn)

        self.npc_btn = QPushButton("Place NPC")
        self.npc_btn.clicked.connect(self.open_npc_dialog)
        toolbar.addWidget(self.npc_btn)

        self.grid_btn = QPushButton("Show Grid")
        self.grid_btn.setCheckable(True)
        self.grid_btn.clicked.connect(self.toggle_grid)
        toolbar.addWidget(self.grid_btn)

        self.trigger_btn = QPushButton("Create Trigger")
        self.trigger_btn.setCheckable(True)
        self.trigger_btn.clicked.connect(self.toggle_trigger_mode)
        toolbar.addWidget(self.trigger_btn)

        self.spawn_btn = QPushButton("Create Spawn Area")
        self.spawn_btn.setCheckable(True)
        self.spawn_btn.clicked.connect(self.toggle_spawn_mode)
        toolbar.addWidget(self.spawn_btn)

        self.enemy_btn = QPushButton("Edit Enemy List")
        self.enemy_btn.clicked.connect(self.open_enemy_list_dialog)
        toolbar.addWidget(self.enemy_btn)

        self.tile_editor_btn = QPushButton("Tile Editor")
        self.tile_editor_btn.setCheckable(True)
        self.tile_editor_btn.clicked.connect(self.toggle_tile_editor)
        toolbar.addWidget(self.tile_editor_btn)

        self.addToolBar(toolbar)

# palette creation
    def _create_palettes(self):
        self.palette_widget = PaletteWidget(self.set_palette_color, self.get_active_color)
        self.palette_widget.set_colors(self.palette_colors)
        self.palette_scroll = QScrollArea()
        self.palette_scroll.setWidgetResizable(True)
        self.palette_scroll.setWidget(self.palette_widget)
        self.palette_scroll.setMinimumWidth(200)
        self.palette_scroll.setMaximumWidth(350)
        self.palette_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.palette_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.palette_scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        self.collision_palette_widget = CollisionPaletteWidget(self.set_collision_color, self.get_active_collision_color)
        self.collision_palette_scroll = QScrollArea()
        self.collision_palette_scroll.setWidgetResizable(True)
        self.collision_palette_scroll.setWidget(self.collision_palette_widget)
        self.collision_palette_scroll.setMinimumWidth(80)
        self.collision_palette_scroll.setMaximumWidth(120)
        self.collision_palette_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.collision_palette_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.collision_palette_scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.collision_palette_scroll.hide()
# layout
    def _create_layout(self):
        self.log_label = QLabel("Latest log: Ready.")
        self.log_label.setStyleSheet("color: #333; background: #eee; padding: 2px;")
        self.log_label.setFixedHeight(22)
        self.log_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        img_layout = QVBoxLayout()
        img_layout.addWidget(self.image_label)
        img_layout.addWidget(self.log_label)

        img_widget = QWidget()
        img_widget.setLayout(img_layout)
        img_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_layout = QHBoxLayout()
        main_layout.addWidget(img_widget, stretch=3)

        self.sidebar_layout = QVBoxLayout()
        self.sidebar_layout.addWidget(self.palette_scroll, stretch=1)
        self.sidebar_layout.addWidget(self.collision_palette_scroll, stretch=0)
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(self.sidebar_layout)
        main_layout.addWidget(sidebar_widget, stretch=1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
# i may have had a few issues with getting collision mode to work. just a few.
    def toggle_collision_mode(self):
        self.collision_mode = not self.collision_mode
        print(f"Collision mode: {self.collision_mode}")
        
        if self.collision_mode:
            self.palette_scroll.hide()
            self.collision_palette_scroll.show()
            self.collision_btn.setText("Exit Collision Layer")
            self.trigger_btn.show()
            self.spawn_btn.show()
            self.log("Collision mode: ON")
        else:
            self.palette_scroll.show()
            self.collision_palette_scroll.hide()
            self.collision_btn.setText("Edit Collision Layer")
            self.trigger_btn.hide()
            self.spawn_btn.hide()
            if self.trigger_mode:
                self.toggle_trigger_mode()
            if self.spawn_mode:
                self.toggle_spawn_mode()
            self.log("Collision mode: OFF")
        
        self.update_canvas()
# my least favorite part of programming
    def update_canvas(self):
        if not self.pixmap:
            return
            
        canvas = QPixmap(self.image_label.size())
        canvas.fill(QColor(0, 0, 0, 0))
        painter = QPainter(canvas)
        
        source_rect = QRectF(self.offset[0], self.offset[1], 
                            self.image_label.width() / self.zoom, 
                            self.image_label.height() / self.zoom)
        target_rect = QRectF(0, 0, self.image_label.width(), self.image_label.height())
        
        if self.collision_mode:
            painter.setOpacity(0.3)
            painter.drawPixmap(target_rect, self.pixmap, source_rect)
            painter.setOpacity(1.0)
            painter.drawPixmap(target_rect, self.collision_layer, source_rect)
        else:
            painter.drawPixmap(target_rect, self.pixmap, source_rect)

        for prefab_obj in self.prefab_objects:
            img = prefab_obj["image"]
            px = prefab_obj["x"]
            py = prefab_obj["y"]
            
            widget_x = (px - self.offset[0]) * self.zoom
            widget_y = (py - self.offset[1]) * self.zoom
            
            scaled_width = int(img.width() * self.zoom)
            scaled_height = int(img.height() * self.zoom)
            scaled_img = img.scaled(
                scaled_width,
                scaled_height,
                Qt.IgnoreAspectRatio,
                Qt.FastTransformation
            )
            
            if self.collision_mode:
                painter.setOpacity(0.3)
                painter.drawPixmap(int(widget_x), int(widget_y), scaled_img)
                painter.setOpacity(1.0)
            else:
                painter.drawPixmap(int(widget_x), int(widget_y), scaled_img)

        for npc_obj in self.npc_objects:
            img = npc_obj["image"]
            px = npc_obj["x"]
            py = npc_obj["y"]
            
            widget_x = (px - self.offset[0]) * self.zoom
            widget_y = (py - self.offset[1]) * self.zoom
            
            scaled_width = int(img.width() * self.zoom)
            scaled_height = int(img.height() * self.zoom)
            scaled_img = img.scaled(
                scaled_width,
                scaled_height,
                Qt.IgnoreAspectRatio,
                Qt.FastTransformation
            )
            
            painter.drawPixmap(int(widget_x), int(widget_y), scaled_img)

        if self.collision_mode:
            for i, spawn_area in enumerate(self.spawn_areas):
                spawn_x = spawn_area["x"]
                spawn_y = spawn_area["y"]
                
                widget_x = (spawn_x - self.offset[0]) * self.zoom
                widget_y = (spawn_y - self.offset[1]) * self.zoom
                
                size = int(32 * self.zoom)
                
                painter.setBrush(QColor(0, 0, 255, 80))
                painter.setPen(QColor(0, 0, 255, 150))
                painter.drawRect(int(widget_x), int(widget_y), size, size)
                
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Arial", 8))
                painter.drawText(
                    int(widget_x + 2), int(widget_y + 12),
                    f"S{i+1}"
                )

        if self.collision_mode:
            for i, trigger in enumerate(self.trigger_rectangles):
                start_x, start_y = trigger["start"]
                end_x, end_y = trigger["end"]
                
                widget_start_x = (start_x - self.offset[0]) * self.zoom
                widget_start_y = (start_y - self.offset[1]) * self.zoom
                widget_end_x = (end_x - self.offset[0]) * self.zoom
                widget_end_y = (end_y - self.offset[1]) * self.zoom
                
                painter.setBrush(QColor(0, 255, 0, 100))
                painter.setPen(QColor(0, 255, 0, 200))
                painter.drawRect(
                    int(widget_start_x), int(widget_start_y),
                    int(widget_end_x - widget_start_x), int(widget_end_y - widget_start_y)
                )
                
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Arial", 10))
                painter.drawText(
                    int(widget_start_x + 5), int(widget_start_y + 15),
                    f"T{i+1}"
                )

        if self.trigger_mode and self.trigger_start_pos and self.trigger_end_pos:
            if hasattr(self.trigger_start_pos, 'x'):
                start_x = int(self.offset[0] + self.trigger_start_pos.x() / self.zoom)
                start_y = int(self.offset[1] + self.trigger_start_pos.y() / self.zoom)
            else:
                start_x = int(self.offset[0] + self.trigger_start_pos[0] / self.zoom)
                start_y = int(self.offset[1] + self.trigger_start_pos[1] / self.zoom)
                
            if hasattr(self.trigger_end_pos, 'x'):
                end_x = int(self.offset[0] + self.trigger_end_pos.x() / self.zoom)
                end_y = int(self.offset[1] + self.trigger_end_pos.y() / self.zoom)
            else:
                end_x = int(self.offset[0] + self.trigger_end_pos[0] / self.zoom)
                end_y = int(self.offset[1] + self.trigger_end_pos[1] / self.zoom)
            
            widget_start_x = (start_x - self.offset[0]) * self.zoom
            widget_start_y = (start_y - self.offset[1]) * self.zoom
            widget_end_x = (end_x - self.offset[0]) * self.zoom
            widget_end_y = (end_y - self.offset[1]) * self.zoom
            
            painter.setBrush(QColor(0, 255, 0, 50))
            painter.setPen(QColor(0, 255, 0, 150))
            painter.drawRect(
                int(widget_start_x), int(widget_start_y),
                int(widget_end_x - widget_start_x), int(widget_end_y - widget_start_y)
            )

        if self.active_stamp and self.stamp_preview_pos:
            preview_img = self.active_stamp["image"]
            
            img_x = int(self.offset[0] + self.stamp_preview_pos[0] / self.zoom)
            img_y = int(self.offset[1] + self.stamp_preview_pos[1] / self.zoom)
            
            px = (img_x - preview_img.width() // 2 - self.offset[0]) * self.zoom
            py = (img_y - preview_img.height() // 2 - self.offset[1]) * self.zoom
            
            scaled_preview = preview_img.scaled(
                int(preview_img.width() * self.zoom),
                int(preview_img.height() * self.zoom),
                Qt.KeepAspectRatio,
                Qt.FastTransformation
            )
            
            painter.setOpacity(0.7)
            painter.drawPixmap(int(px), int(py), scaled_preview)
            painter.setOpacity(1.0)

        if self.active_prefab and self.prefab_preview_pos:
            preview_img = self.active_prefab["image"]
            
            img_x = int(self.offset[0] + self.prefab_preview_pos[0] / self.zoom)
            img_y = int(self.offset[1] + self.prefab_preview_pos[1] / self.zoom)
            
            px = (img_x - preview_img.width() // 2 - self.offset[0]) * self.zoom
            py = (img_y - preview_img.height() // 2 - self.offset[1]) * self.zoom
            
            scaled_width = int(preview_img.width() * self.zoom)
            scaled_height = int(preview_img.height() * self.zoom)
            scaled_preview = preview_img.scaled(
                scaled_width,
                scaled_height,
                Qt.IgnoreAspectRatio,
                Qt.FastTransformation
            )
            
            painter.setOpacity(0.7)
            painter.drawPixmap(int(px), int(py), scaled_preview)
            painter.setOpacity(1.0)

        if self.active_npc and self.npc_preview_pos:
            preview_img = self.active_npc["image"]
            
            img_x = int(self.offset[0] + self.npc_preview_pos[0] / self.zoom)
            img_y = int(self.offset[1] + self.npc_preview_pos[1] / self.zoom)
            
            px = (img_x - preview_img.width() // 2 - self.offset[0]) * self.zoom
            py = (img_y - preview_img.height() // 2 - self.offset[1]) * self.zoom
            
            scaled_width = int(preview_img.width() * self.zoom)
            scaled_height = int(preview_img.height() * self.zoom)
            scaled_npc_preview = preview_img.scaled(
                scaled_width,
                scaled_height,
                Qt.IgnoreAspectRatio,
                Qt.FastTransformation
            )
            
            painter.setOpacity(0.7)
            painter.drawPixmap(int(px), int(py), scaled_npc_preview)
            painter.setOpacity(1.0)
# this is getting annoying :pensive:
        if self.active_tile_stamp and self.tile_stamp_preview_pos:
            preview_img = self.active_tile_stamp["image"]
            painter.setOpacity(0.5)
            painter.drawPixmap(
                int((self.tile_stamp_preview_pos[0] - self.offset[0]) * self.zoom),
                int((self.tile_stamp_preview_pos[1] - self.offset[1]) * self.zoom),
                int(preview_img.width() * self.zoom),
                int(preview_img.height() * self.zoom),
                preview_img
            )
            painter.setOpacity(1.0)

        if self.show_grid:
            painter.setPen(QColor(255, 0, 0, 100))
            painter.setOpacity(0.5)

            grid_spacing = self.grid_size * self.zoom
            start_x = (-self.offset[0] * self.zoom) % grid_spacing
            start_y = (-self.offset[1] * self.zoom) % grid_spacing

            x = start_x
            while x < self.image_label.width():
                painter.drawLine(int(round(x)), 0, int(round(x)), self.image_label.height())
                x += grid_spacing

            y = start_y
            while y < self.image_label.height():
                painter.drawLine(0, int(round(y)), self.image_label.width(), int(round(y)))
                y += grid_spacing

            painter.setOpacity(1.0)

        painter.end()
        self.image_label.setPixmap(canvas)
        
        if self.collision_mode:
            self.collision_palette_widget.set_active_highlight()
        else:
            self.palette_widget.set_active_highlight()

    def set_brush_size(self, size):
        self.brush_size = max(1, size)
        self.log(f"Brush size: {self.brush_size}")

    def toggle_eraser(self):
        self.eraser_mode = not self.eraser_mode
        self.eraser_btn.setText("Eraser ON" if self.eraser_mode else "Eraser OFF")
        self.log("Eraser mode: " + ("ON" if self.eraser_mode else "OFF"))

    def set_palette_color(self, idx):
        if idx == 'plus':
            c = QColorDialog.getColor(self.active_color, self, "Pick Custom Color")
            if c.isValid():
                self.palette_colors.append(c)
                self.palette_widget.set_colors(self.palette_colors)
                self.active_color = c
                self.palette_widget.set_active_highlight()
                self.log("Added custom color: " + c.name())
            return
        self.active_color = self.palette_colors[idx]
        self.eraser_mode = False
        self.eraser_btn.setChecked(False)
        self.palette_widget.set_active_highlight()
        self.log(f"Selected color: {self.active_color.name()}")

    def get_active_color(self):
        return self.active_color

    def set_collision_color(self, idx):
        self.collision_brush_index = idx
        self.collision_color = self.collision_palette[idx]
        self.collision_palette_widget.set_active_highlight()
        self.log(f"Collision color: {self.collision_color.name()}")

    def get_active_collision_color(self):
        return self.collision_color

    def log(self, msg):
        self.log_label.setText(f"Latest log: {msg}")

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Map Image", "", "Images (*.png)")
        if path:
            self.pixmap = QPixmap(path)
            self.collision_layer = QPixmap(self.pixmap.size())
            self.collision_layer.fill(QColor(255,255,255,0))
            self.log(f"Loaded image: {path} ({self.pixmap.width()}x{self.pixmap.height()})")
            self.offset = [0.0, 0.0]
            self.zoom = 1.0
            self.update_canvas()

    def save_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Map Image", "", "PNG Image (*.png)")
        if path:
            self.pixmap.save(path, "PNG")
            self.log(f"Saved image to {path}")

    def export_all(self):
        """Export map, collision, and JSON data to a zip file"""
        import zipfile
        import tempfile
        import os
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"map_export_{timestamp}.zip"
        zip_path, _ = QFileDialog.getSaveFileName(
            self, "Export Map Package", default_name, "ZIP Files (*.zip)"
        )
        
        if not zip_path:
            return
            
        try:
            with zipfile.ZipFile(zip_path, 'w') as zip_file:
                map_data = self._pixmap_to_bytes(self.pixmap)
                zip_file.writestr("map.png", map_data)
                
                collision_data = self._pixmap_to_bytes(self.collision_layer)
                zip_file.writestr("collision.png", collision_data)
                
                json_data = self._create_export_json()
                zip_file.writestr("map_data.json", json_data.encode('utf-8'))
                
            self.log(f"Exported map package to: {zip_path}")
            
        except Exception as e:
            self.log(f"Export failed: {str(e)}")

    def _pixmap_to_bytes(self, pixmap):
        """Convert QPixmap to bytes for zip export"""
        from PyQt5.QtCore import QBuffer, QIODevice
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        return buffer.data()

    def _create_export_json(self):
        """Create JSON data for export"""
        import json
        from datetime import datetime
        
        prefab_data = []
        for prefab in self.prefab_objects:
            prefab_name = self._find_prefab_name_by_image(prefab["image"])
            prefab_data.append({
                "name": prefab_name,
                "x": prefab["x"],
                "y": prefab["y"]
            })
        
        npc_data = []
        for npc in self.npc_objects:
            npc_name = self._find_npc_name_by_image(npc["image"])
            npc_data.append({
                "name": npc_name,
                "x": npc["x"],
                "y": npc["y"]
            })
        
        trigger_data = []
        for i, trigger in enumerate(self.trigger_rectangles):
            trigger_data.append({
                "id": i + 1,
                "command": trigger["command"],
                "start_x": trigger["start"][0],
                "start_y": trigger["start"][1],
                "end_x": trigger["end"][0],
                "end_y": trigger["end"][1]
            })
        
        spawn_data = []
        for i, spawn in enumerate(self.spawn_areas):
            spawn_data.append({
                "id": i + 1,
                "chunk_x": spawn["x"] // 32,
                "chunk_y": spawn["y"] // 32
            })
        
        export_data = {
            "map_info": {
                "width": self.pixmap.width(),
                "height": self.pixmap.height(),
                "export_date": datetime.now().isoformat()
            },
            "prefabs": prefab_data,
            "npcs": npc_data,
            "triggers": trigger_data,
            "spawn_areas": spawn_data,
            "enemy_list": self.enemy_list
        }
        
        return json.dumps(export_data, indent=2)

    def _find_prefab_name_by_image(self, target_image):
        """Find the prefab name by matching the image"""
        for category, prefabs in self.prefabs.items():
            for prefab in prefabs:
                if prefab["image"].cacheKey() == target_image.cacheKey():
                    return f"{prefab['name']}_{category}"
        return "unknown_prefab"

    def _find_npc_name_by_image(self, target_image):
        """Find the NPC name by matching the image"""
        for category, npcs in self.npcs.items():
            for npc in npcs:
                if npc["image"].cacheKey() == target_image.cacheKey():
                    return f"{npc['name']}_{category}"
        return "unknown_npc"

    def _load_stamps(self):
        """Load stamps organized by categories from the stamps folder"""
        import os
        from PyQt5.QtGui import QPixmap
        
        self.stamps.clear()
        if not os.path.exists(self.stamp_folder):
            os.makedirs(self.stamp_folder)
            self.log("Created stamps folder")
            return
            
        for category in os.listdir(self.stamp_folder):
            category_path = os.path.join(self.stamp_folder, category)
            if os.path.isdir(category_path):
                self.stamps[category] = []
                
                for fname in os.listdir(category_path):
                    if fname.lower().endswith('.png') and not fname.lower().endswith('_collision.png'):
                        name = fname[:-4]
                        img_path = os.path.join(category_path, fname)
                        collision_path = os.path.join(category_path, f"{name}_collision.png")
                        
                        image = QPixmap(img_path)
                        collision = QPixmap(collision_path) if os.path.exists(collision_path) else None
                        
                        self.stamps[category].append({
                            "name": name, 
                            "image": image, 
                            "collision": collision
                        })
        
        total_stamps = sum(len(stamps) for stamps in self.stamps.values())
        self.log(f"Loaded {total_stamps} stamps in {len(self.stamps)} categories")

    def open_stamp_dialog(self):
        """Open dialog to select a stamp from categories"""
        dlg = QDialog(self)
        dlg.setWindowTitle("Select Stamp")
        dlg.resize(400, 500)
        layout = QVBoxLayout()
        
        tree = QTreeWidget()
        tree.setHeaderLabel("Stamp Categories")
        tree.setIconSize(QSize(32, 32))
        
        for category, stamps in self.stamps.items():
            category_item = QTreeWidgetItem([category])
            category_item.setExpanded(True)
            tree.addTopLevelItem(category_item)
            
            for stamp in stamps:
                stamp_item = QTreeWidgetItem([stamp["name"]])
                icon = QIcon(stamp["image"].scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                stamp_item.setIcon(0, icon)
                category_item.addChild(stamp_item)
        
        layout.addWidget(QLabel("Choose a stamp to place:"))
        layout.addWidget(tree)
        
        btn_layout = QHBoxLayout()
        select_btn = QPushButton("Select")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(select_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dlg.setLayout(layout)
        
        def select_stamp():
            current_item = tree.currentItem()
            if current_item and current_item.parent():
                category = current_item.parent().text(0)
                stamp_name = current_item.text(0)
                
                for stamp in self.stamps[category]:
                    if stamp["name"] == stamp_name:
                        self.active_stamp = stamp
                        self.stamp_preview_timer.start()
                        self.log(f"Selected stamp: {stamp_name} from {category}. Click on map to stamp.")
                        self.update_canvas()
                        dlg.accept()
                        return
                self.log("Error: Could not find selected stamp")
            else:
                self.log("Please select a stamp")
        
        select_btn.clicked.connect(select_stamp)
        cancel_btn.clicked.connect(dlg.reject)
        tree.itemDoubleClicked.connect(lambda item, col: select_stamp())
        
        dlg.exec_()

    def _update_stamp_preview(self):
        """Update stamp preview position from cursor"""
        if self.active_stamp:
            from PyQt5.QtGui import QCursor
            global_pos = QCursor.pos()
            widget_pos = self.image_label.mapFromGlobal(global_pos)
            if self.image_label.rect().contains(widget_pos):
                self.stamp_preview_pos = (widget_pos.x(), widget_pos.y())
                self.update_canvas()

    def _stamp_at(self, widget_pos):
        """Place the active stamp at the given widget position"""
        if not self.active_stamp:
            return
            
        self._push_undo_action('stamp')
        
        img = self.active_stamp["image"]
        img_w = img.width()
        img_h = img.height()
        
        img_x = int(self.offset[0] + widget_pos.x() / self.zoom)
        img_y = int(self.offset[1] + widget_pos.y() / self.zoom)
        px = img_x - img_w // 2
        py = img_y - img_h // 2
        
        painter = QPainter(self.pixmap)
        painter.drawPixmap(px, py, img)
        painter.end()
        
        if self.active_stamp["collision"]:
            painter = QPainter(self.collision_layer)
            painter.drawPixmap(px, py, self.active_stamp["collision"])
            painter.end()
        
        self.stamp_preview_timer.stop()
        self.active_stamp = None
        self.stamp_preview_pos = None
        self.log(f"Stamped: {img_w}x{img_h} at ({px},{py})")
        self.update_canvas()

    def _load_prefabs(self):
        """Load prefabs organized by categories from the prefabs folder"""
        import os
        from PyQt5.QtGui import QPixmap
        
        self.prefabs.clear()
        if not os.path.exists(self.prefab_folder):
            os.makedirs(self.prefab_folder)
            self.log("Created prefabs folder")
            return
            
        for category in os.listdir(self.prefab_folder):
            category_path = os.path.join(self.prefab_folder, category)
            if os.path.isdir(category_path):
                self.prefabs[category] = []
                
                for fname in os.listdir(category_path):
                    if fname.lower().endswith('.png') and not fname.lower().endswith('_collision.png'):
                        name = fname[:-4]
                        img_path = os.path.join(category_path, fname)
                        collision_path = os.path.join(category_path, f"{name}_collision.png")
                        
                        image = QPixmap(img_path)
                        collision = QPixmap(collision_path) if os.path.exists(collision_path) else None
                        
                        self.prefabs[category].append({
                            "name": name, 
                            "image": image, 
                            "collision": collision
                        })
        
        total_prefabs = sum(len(prefabs) for prefabs in self.prefabs.values())
        self.log(f"Loaded {total_prefabs} prefabs in {len(self.prefabs)} categories")

    def open_prefab_dialog(self):
        """Open dialog to select a prefab from categories"""
        dlg = QDialog(self)
        dlg.setWindowTitle("Select Prefab")
        dlg.resize(400, 500)
        layout = QVBoxLayout()
        
        tree = QTreeWidget()
        tree.setHeaderLabel("Prefab Categories")
        tree.setIconSize(QSize(32, 32))
        
        for category, prefabs in self.prefabs.items():
            category_item = QTreeWidgetItem([category])
            category_item.setExpanded(True)
            tree.addTopLevelItem(category_item)
            
            for prefab in prefabs:
                prefab_item = QTreeWidgetItem([prefab["name"]])
                icon = QIcon(prefab["image"].scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                prefab_item.setIcon(0, icon)
                category_item.addChild(prefab_item)
        
        layout.addWidget(QLabel("Choose a prefab to place:"))
        layout.addWidget(tree)
        
        btn_layout = QHBoxLayout()
        select_btn = QPushButton("Select")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(select_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dlg.setLayout(layout)
        
        def select_prefab():
            current_item = tree.currentItem()
            if current_item and current_item.parent():
                category = current_item.parent().text(0)
                prefab_name = current_item.text(0)
                
                for prefab in self.prefabs[category]:
                    if prefab["name"] == prefab_name:
                        self.active_prefab = prefab
                        self.prefab_preview_timer.start()
                        self.log(f"Selected prefab: {prefab_name} from {category}. Click on map to place.")
                        self.update_canvas()
                        dlg.accept()
                        return
                self.log("Error: Could not find selected prefab")
            else:
                self.log("Please select a prefab")
        
        select_btn.clicked.connect(select_prefab)
        cancel_btn.clicked.connect(dlg.reject)
        tree.itemDoubleClicked.connect(lambda item, col: select_prefab())
        
        dlg.exec_()

    def _update_prefab_preview(self):
        """Update prefab preview position from cursor"""
        if self.active_prefab:
            from PyQt5.QtGui import QCursor
            global_pos = QCursor.pos()
            widget_pos = self.image_label.mapFromGlobal(global_pos)
            if self.image_label.rect().contains(widget_pos):
                self.prefab_preview_pos = (widget_pos.x(), widget_pos.y())
                self.update_canvas()

    def _place_prefab_at(self, widget_pos):
        """Place the active prefab at the given widget position"""
        if not self.active_prefab:
            return
            
        self._push_undo_action('prefab')
        
        img = self.active_prefab["image"]
        img_w = img.width()
        img_h = img.height()
        
        img_x = int(self.offset[0] + widget_pos.x() / self.zoom)
        img_y = int(self.offset[1] + widget_pos.y() / self.zoom)
        px = img_x - img_w // 2
        py = img_y - img_h // 2
        
        self.prefab_objects.append({
            "image": img,
            "x": px,
            "y": py,
            "collision": self.active_prefab["collision"]
        })
        
        if self.active_prefab["collision"]:
            painter = QPainter(self.collision_layer)
            painter.drawPixmap(px, py, self.active_prefab["collision"])
            painter.end()
        
        self.prefab_preview_timer.stop()
        self.active_prefab = None
        self.prefab_preview_pos = None
        self.log(f"Placed prefab: {img_w}x{img_h} at ({px},{py})")
        self.update_canvas()

    def _load_npcs(self):
        """Load NPCs organized by categories from the npcs folder"""
        import os
        from PyQt5.QtGui import QPixmap
        
        self.npcs.clear()
        if not os.path.exists(self.npc_folder):
            os.makedirs(self.npc_folder)
            self.log("Created npcs folder")
            return
            
        for category in os.listdir(self.npc_folder):
            category_path = os.path.join(self.npc_folder, category)
            if os.path.isdir(category_path):
                self.npcs[category] = []
                
                for fname in os.listdir(category_path):
                    if fname.lower().endswith('.png') and not fname.lower().endswith('_collision.png'):
                        name = fname[:-4]
                        img_path = os.path.join(category_path, fname)
                        collision_path = os.path.join(category_path, f"{name}_collision.png")
                        
                        image = QPixmap(img_path)
                        collision = QPixmap(collision_path) if os.path.exists(collision_path) else None
                        
                        self.npcs[category].append({
                            "name": name, 
                            "image": image, 
                            "collision": collision
                        })
        
        total_npcs = sum(len(npcs) for npcs in self.npcs.values())
        self.log(f"Loaded {total_npcs} NPCs in {len(self.npcs)} categories")

    def open_npc_dialog(self):
        """Open dialog to select an NPC from categories"""
        dlg = QDialog(self)
        dlg.setWindowTitle("Select NPC")
        dlg.resize(400, 500)
        layout = QVBoxLayout()
        
        tree = QTreeWidget()
        tree.setHeaderLabel("NPC Categories")
        tree.setIconSize(QSize(32, 32))
        
        for category, npcs in self.npcs.items():
            category_item = QTreeWidgetItem([category])
            category_item.setExpanded(True)
            tree.addTopLevelItem(category_item)
            
            for npc in npcs:
                npc_item = QTreeWidgetItem([npc["name"]])
                icon = QIcon(npc["image"].scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                npc_item.setIcon(0, icon)
                category_item.addChild(npc_item)
        
        layout.addWidget(QLabel("Choose an NPC to place:"))
        layout.addWidget(tree)
        
        btn_layout = QHBoxLayout()
        select_btn = QPushButton("Select")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(select_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dlg.setLayout(layout)
        
        def select_npc():
            current_item = tree.currentItem()
            if current_item and current_item.parent():
                category = current_item.parent().text(0)
                npc_name = current_item.text(0)
                
                for npc in self.npcs[category]:
                    if npc["name"] == npc_name:
                        self.active_npc = npc
                        self.npc_preview_timer.start()
                        self.log(f"Selected NPC: {npc_name} from {category}. Click on map to place.")
                        self.update_canvas()
                        dlg.accept()
                        return
                self.log("Error: Could not find selected NPC")
            else:
                self.log("Please select an NPC")
        
        select_btn.clicked.connect(select_npc)
        cancel_btn.clicked.connect(dlg.reject)
        tree.itemDoubleClicked.connect(lambda item, col: select_npc())
        
        dlg.exec_()

    def _update_npc_preview(self):
        """Update NPC preview position from cursor"""
        if self.active_npc:
            from PyQt5.QtGui import QCursor
            global_pos = QCursor.pos()
            widget_pos = self.image_label.mapFromGlobal(global_pos)
            if self.image_label.rect().contains(widget_pos):
                self.npc_preview_pos = (widget_pos.x(), widget_pos.y())
                self.update_canvas()

    def _place_npc_at(self, widget_pos):
        """Place the active NPC at the given widget position"""
        if not self.active_npc:
            return
            
        self._push_undo_action('npc')
        
        img = self.active_npc["image"]
        img_w = img.width()
        img_h = img.height()
        
        img_x = int(self.offset[0] + widget_pos.x() / self.zoom)
        img_y = int(self.offset[1] + widget_pos.y() / self.zoom)
        px = img_x - img_w // 2
        py = img_y - img_h // 2
        
        self.npc_objects.append({
            "image": img,
            "x": px,
            "y": py,
            "collision": self.active_npc["collision"]
        })
        
        if self.active_npc["collision"]:
            painter = QPainter(self.collision_layer)
            painter.drawPixmap(px, py, self.active_npc["collision"])
            painter.end()
        
        self.npc_preview_timer.stop()
        self.active_npc = None
        self.npc_preview_pos = None
        self.log(f"Placed NPC: {img_w}x{img_h} at ({px},{py})")
        self.update_canvas()

    def _push_undo_action(self, action_type):
        state = {'type': action_type}
        if action_type == 'paint':
            state['pixmap'] = self.pixmap.copy()
        elif action_type == 'collision':
            state['collision_layer'] = self.collision_layer.copy()
        elif action_type == 'stamp':
            state['pixmap'] = self.pixmap.copy()
            state['collision_layer'] = self.collision_layer.copy()
        elif action_type == 'prefab':
            state['collision_layer'] = self.collision_layer.copy()
            state['prefab_objects'] = self.prefab_objects.copy()
        elif action_type == 'npc':
            state['collision_layer'] = self.collision_layer.copy()
            state['npc_objects'] = self.npc_objects.copy()
        elif action_type == 'trigger':
            state['trigger_rectangles'] = self.trigger_rectangles.copy()
        elif action_type == 'spawn':
            state['spawn_areas'] = self.spawn_areas.copy()
        self.undo_stack.append(state)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            self.log("Nothing to undo.")
            return
        state = self.undo_stack.pop()
        self.redo_stack.append(self._capture_current_state(state['type']))
        self._restore_state(state)
        self.update_canvas()
        self.log("Undo.")

    def redo(self):
        if not self.redo_stack:
            self.log("Nothing to redo.")
            return
        state = self.redo_stack.pop()
        self.undo_stack.append(self._capture_current_state(state['type']))
        self._restore_state(state)
        self.update_canvas()
        self.log("Redo.")

    def _capture_current_state(self, action_type):
        state = {'type': action_type}
        if action_type == 'paint':
            state['pixmap'] = self.pixmap.copy()
        elif action_type == 'collision':
            state['collision_layer'] = self.collision_layer.copy()
        elif action_type == 'stamp':
            state['pixmap'] = self.pixmap.copy()
            state['collision_layer'] = self.collision_layer.copy()
        elif action_type == 'prefab':
            state['collision_layer'] = self.collision_layer.copy()
            state['prefab_objects'] = self.prefab_objects.copy()
        elif action_type == 'npc':
            state['collision_layer'] = self.collision_layer.copy()
            state['npc_objects'] = self.npc_objects.copy()
        elif action_type == 'trigger':
            state['trigger_rectangles'] = self.trigger_rectangles.copy()
        elif action_type == 'spawn':
            state['spawn_areas'] = self.spawn_areas.copy()
        return state

    def _restore_state(self, state):
        if state['type'] == 'paint':
            self.pixmap = state['pixmap']
        elif state['type'] == 'collision':
            self.collision_layer = state['collision_layer']
        elif state['type'] == 'stamp':
            self.pixmap = state['pixmap']
            self.collision_layer = state['collision_layer']
        elif state['type'] == 'prefab':
            self.collision_layer = state['collision_layer']
            self.prefab_objects = state['prefab_objects']
        elif state['type'] == 'npc':
            self.collision_layer = state['collision_layer']
            self.npc_objects = state['npc_objects']
        elif state['type'] == 'trigger':
            self.trigger_rectangles = state['trigger_rectangles']
        elif state['type'] == 'spawn':
            self.spawn_areas = state['spawn_areas']

    def _paint_at(self, widget_pos):
        img_x = int(round(self.offset[0] + (widget_pos.x() - 4) / self.zoom))
        img_y = int(round(self.offset[1] + (widget_pos.y() - 3) / self.zoom))
        
        if not (0 <= img_x < self.pixmap.width() and 0 <= img_y < self.pixmap.height()):
            return
        painter = QPainter(self.pixmap)
        color = QColor(Qt.white) if self.eraser_mode else self.active_color
        painter.setPen(color)
        painter.setBrush(color)
        if self.brush_size == 1:
            painter.drawPoint(img_x, img_y)
        else:
            painter.drawRect(img_x, img_y, self.brush_size, self.brush_size)
        painter.end()
        self.update_canvas()

    def _paint_collision_at(self, widget_pos):
        img_x = int(round(self.offset[0] + (widget_pos.x() - 4) / self.zoom))
        img_y = int(round(self.offset[1] + (widget_pos.y() - 3) / self.zoom))
        
        if not (0 <= img_x < self.collision_layer.width() and 0 <= img_y < self.collision_layer.height()):
            return
        painter = QPainter(self.collision_layer)
        
        if self.eraser_mode:
            color = QColor(255, 255, 255, 0)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
        else:
            color = self.collision_color
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            
        painter.setPen(color)
        painter.setBrush(color)
        if self.brush_size == 1:
            painter.drawPoint(img_x, img_y)
        else:
            painter.drawRect(img_x, img_y, self.brush_size, self.brush_size)
        painter.end()
        self.update_canvas()

    def resizeEvent(self, event):
        self.update_canvas()
        super().resizeEvent(event)

    def toggle_trigger_mode(self):
        """Toggle trigger creation mode"""
        self.trigger_mode = not self.trigger_mode
        self.trigger_btn.setText("Cancel Trigger" if self.trigger_mode else "Create Trigger")
        self.trigger_btn.setChecked(self.trigger_mode)
        
        if self.trigger_mode:
            if not self.collision_mode:
                self.toggle_collision_mode()
            self.log("Trigger mode: ON - Click and drag to create trigger rectangle")
        else:
            self.trigger_start_pos = None
            self.trigger_end_pos = None
            self.log("Trigger mode: OFF")
        
        self.update_canvas()

    def _create_trigger_rectangle(self, start_pos, end_pos):
        """Create a new trigger rectangle"""
        if hasattr(start_pos, 'x'):
            start_x = int(self.offset[0] + start_pos.x() / self.zoom)
            start_y = int(self.offset[1] + start_pos.y() / self.zoom)
        else:
            start_x = int(self.offset[0] + start_pos[0] / self.zoom)
            start_y = int(self.offset[1] + start_pos[1] / self.zoom)
            
        if hasattr(end_pos, 'x'):
            end_x = int(self.offset[0] + end_pos.x() / self.zoom)
            end_y = int(self.offset[1] + end_pos.y() / self.zoom)
        else:
            end_x = int(self.offset[0] + end_pos[0] / self.zoom)
            end_y = int(self.offset[1] + end_pos[1] / self.zoom)
        
        # im tired boss
        start_x = int(start_x)
        start_y = int(start_y)
        end_x = int(end_x)
        end_y = int(end_y)
        
        x1, x2 = min(start_x, end_x), max(start_x, end_x)
        y1, y2 = min(start_y, end_y), max(start_y, end_y)
        
        trigger = {
            "start": (x1, y1),
            "end": (x2, y2),
            "command": ""
        }
        
        self.trigger_rectangles.append(trigger)
        self.active_trigger_edit = len(self.trigger_rectangles) - 1
        
        self._open_trigger_command_dialog()
        
        self.log(f"Created trigger rectangle: ({x1},{y1}) to ({x2},{y2})")
        self.update_canvas()

    def _open_trigger_command_dialog(self):
        """Open dialog to edit trigger command"""
        if self.active_trigger_edit is None:
            return
            
        trigger = self.trigger_rectangles[self.active_trigger_edit]
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit Trigger Command")
        dlg.resize(400, 150)
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Enter command for this trigger:"))
        from PyQt5.QtWidgets import QTextEdit
        command_edit = QTextEdit()
        command_edit.setPlainText(trigger["command"])
        command_edit.setMaximumHeight(80)
        layout.addWidget(command_edit)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dlg.setLayout(layout)
        
        def save_command():
            trigger["command"] = command_edit.toPlainText()
            self.log(f"Trigger command saved: {trigger['command'][:30]}...")
            dlg.accept()
        
        def cancel_command():
            if self.active_trigger_edit is not None:
                self.trigger_rectangles.pop(self.active_trigger_edit)
                self.log("Trigger creation cancelled")
            dlg.reject()
        
        save_btn.clicked.connect(save_command)
        cancel_btn.clicked.connect(cancel_command)
        
        dlg.exec_()
        self.active_trigger_edit = None

    def _delete_trigger(self, trigger_index):
        """Delete a trigger rectangle"""
        if 0 <= trigger_index < len(self.trigger_rectangles):
            trigger = self.trigger_rectangles.pop(trigger_index)
            self.log(f"Deleted trigger: {trigger['command'][:30]}...")
            self.update_canvas()

    def _edit_trigger_command(self, trigger_index):
        """Edit an existing trigger's command"""
        if trigger_index < 0 or trigger_index >= len(self.trigger_rectangles):
            return
            
        trigger = self.trigger_rectangles[trigger_index]
        
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Edit Trigger {trigger_index + 1} Command")
        dlg.resize(400, 150)
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel(f"Enter command for trigger {trigger_index + 1}:"))
        from PyQt5.QtWidgets import QTextEdit
        command_edit = QTextEdit()
        command_edit.setPlainText(trigger["command"])
        command_edit.setMaximumHeight(80)
        layout.addWidget(command_edit)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        delete_btn = QPushButton("Delete Trigger")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout)
        
        dlg.setLayout(layout)
        
        def save_command():
            trigger["command"] = command_edit.toPlainText()
            self.log(f"Trigger {trigger_index + 1} command saved: {trigger['command'][:30]}...")
            dlg.accept()
        
        def delete_trigger():
            self._delete_trigger(trigger_index)
            dlg.accept()
        
        save_btn.clicked.connect(save_command)
        cancel_btn.clicked.connect(dlg.reject)
        delete_btn.clicked.connect(delete_trigger)
        
        dlg.exec_()

    def toggle_spawn_mode(self):
        """Toggle enemy spawn area creation mode"""
        self.spawn_mode = not self.spawn_mode
        self.spawn_btn.setText("Cancel Spawn" if self.spawn_mode else "Create Spawn Area")
        self.spawn_btn.setChecked(self.spawn_mode)
        
        if self.spawn_mode:
            if not self.collision_mode:
                self.toggle_collision_mode()
            self.log("Spawn mode: ON - Click to place enemy spawn area")
        else:
            self.log("Spawn mode: OFF")
        
        self.update_canvas()

    def _create_spawn_area(self, widget_pos):
        """Create a new enemy spawn area at the given position"""
        img_x = int(self.offset[0] + widget_pos.x() / self.zoom)
        img_y = int(self.offset[1] + widget_pos.y() / self.zoom)
        
        spawn_x = (img_x // 32) * 32
        spawn_y = (img_y // 32) * 32
        
        spawn_area = {
            "x": spawn_x,
            "y": spawn_y
        }
        
        self.spawn_areas.append(spawn_area)
        
        self.log(f"Created spawn area at ({spawn_x},{spawn_y})")
        self.update_canvas()

    def _edit_spawn_area(self, spawn_index):
        """Edit an existing spawn area (just delete it)"""
        if spawn_index < 0 or spawn_index >= len(self.spawn_areas):
            return
            
        self._delete_spawn_area(spawn_index)

    def _check_spawn_click(self, widget_pos):
        """Check if user clicked on an existing spawn area to delete it"""
        img_x = int(self.offset[0] + widget_pos.x() / self.zoom)
        img_y = int(self.offset[1] + widget_pos.y() / self.zoom)
        
        for i, spawn_area in enumerate(self.spawn_areas):
            spawn_x = spawn_area["x"]
            spawn_y = spawn_area["y"]
            
            if spawn_x <= img_x < spawn_x + 32 and spawn_y <= img_y < spawn_y + 32:
                self._delete_spawn_area(i)
                return True
        
        return False
# thank you chatgpt!
    def eventFilter(self, obj, event):
        if obj is self.image_label:
            if event.type() == event.MouseMove:
                if self.active_stamp:
                    self.stamp_preview_pos = (event.pos().x(), event.pos().y())
                    self.update_canvas()
                elif self.active_prefab:
                    self.prefab_preview_pos = (event.pos().x(), event.pos().y())
                    self.update_canvas()
                elif self.active_npc:
                    self.npc_preview_pos = (event.pos().x(), event.pos().y())
                    self.update_canvas()
                elif self.trigger_mode and self.trigger_start_pos:
                    self.trigger_end_pos = (event.pos().x(), event.pos().y())
                    self.update_canvas()
                elif self.active_tile_stamp:
                    img_x = self.offset[0] + event.pos().x() / self.zoom
                    img_y = self.offset[1] + event.pos().y() / self.zoom
                    snap_x = int(img_x // 32) * 32
                    snap_y = int(img_y // 32) * 32
                    self.tile_stamp_preview_pos = (snap_x, snap_y)
                    self.update_canvas()
            
            if event.type() == event.MouseButtonPress:
                if event.button() == Qt.MiddleButton:
                    self.last_pan_point = event.pos()
                    self.log("Pan start")
                    return True
                elif event.button() == Qt.LeftButton and self.trigger_mode:
                    self.trigger_start_pos = (event.pos().x(), event.pos().y())
                    self.trigger_end_pos = (event.pos().x(), event.pos().y())
                    self.log("Trigger rectangle started")
                    return True
                elif event.button() == Qt.LeftButton and self.spawn_mode:
                    self._create_spawn_area(event.pos())
                    self.spawn_mode = False
                    self.spawn_btn.setChecked(False)
                    self.spawn_btn.setText("Create Spawn Area")
                    return True
                elif event.button() == Qt.RightButton and self.collision_mode and not self.trigger_mode and not self.spawn_mode:
                    if self._check_trigger_click(event.pos()):
                        return True
                    if self._check_spawn_click(event.pos()):
                        return True
            elif event.type() == event.MouseMove:
                if self.last_pan_point is not None and (event.buttons() & Qt.MiddleButton):
                    delta = event.pos() - self.last_pan_point
                    self.offset[0] -= delta.x() / self.zoom
                    self.offset[1] -= delta.y() / self.zoom
                    self.offset[0] = max(0, min(self.pixmap.width() - 1, self.offset[0]))
                    self.offset[1] = max(0, min(self.pixmap.height() - 1, self.offset[1]))
                    self.last_pan_point = event.pos()
                    self.update_canvas()
                    self.log(f"Panned by {delta}")
                    return True
            elif event.type() == event.MouseButtonRelease:
                if event.button() == Qt.MiddleButton:
                    self.last_pan_point = None
                    self.log("Pan end")
                    return True
                elif event.button() == Qt.LeftButton and self.trigger_mode and self.trigger_start_pos:
                    self._create_trigger_rectangle(self.trigger_start_pos, event.pos())
                    self.trigger_start_pos = None
                    self.trigger_end_pos = None
                    self.trigger_mode = False
                    self.trigger_btn.setChecked(False)
                    self.trigger_btn.setText("Create Trigger")
                    return True

            if event.type() == event.Wheel:
                old_zoom = self.zoom
                zoom_in_factor = 1.1
                zoom_out_factor = 1 / 1.1
                if event.angleDelta().y() > 0:
                    self.zoom *= zoom_in_factor
                    self.log("Zooming in")
                else:
                    self.zoom *= zoom_out_factor
                    self.log("Zooming out")
                self.zoom = max(0.1, min(self.zoom, 10.0))
                mouse_pos = event.pos()
                mouse_img_x = self.offset[0] + mouse_pos.x() / old_zoom
                mouse_img_y = self.offset[1] + mouse_pos.y() / old_zoom
                self.offset[0] = mouse_img_x - mouse_pos.x() / self.zoom
                self.offset[1] = mouse_img_y - mouse_pos.y() / self.zoom
                self.offset[0] = max(0, min(self.pixmap.width() - 1, self.offset[0]))
                self.offset[1] = max(0, min(self.pixmap.height() - 1, self.offset[1]))
                self.update_canvas()
                self.log(f"Zoom: {self.zoom:.3f} at mouse {mouse_pos}")
                return True

            if self.active_stamp:
                if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                    self._stamp_at(event.pos())
                    return True
                elif event.type() == event.MouseButtonRelease:
                    return True
                elif event.type() == event.Leave:
                    self.stamp_preview_pos = None
                    self.update_canvas()
                    return True

            if self.active_prefab:
                if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                    self._place_prefab_at(event.pos())
                    return True
                elif event.type() == event.MouseButtonRelease:
                    return True
                elif event.type() == event.Leave:
                    self.prefab_preview_pos = None
                    self.update_canvas()
                    return True

            if self.active_npc:
                if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                    self._place_npc_at(event.pos())
                    return True
                elif event.type() == event.MouseButtonRelease:
                    return True
                elif event.type() == event.Leave:
                    self.npc_preview_pos = None
                    self.update_canvas()
                    return True

            if not getattr(self, "tile_editor_mode", False):
                if event.type() == event.MouseButtonPress:
                    if event.button() == Qt.LeftButton:
                        if self.collision_mode:
                            self._push_undo_action('collision')
                            self.drawing = True
                            self._paint_collision_at(event.pos())
                        else:
                            self._push_undo_action('paint')
                            self.drawing = True
                            self._paint_at(event.pos())
                elif event.type() == event.MouseMove:
                    if self.drawing and (event.buttons() & Qt.LeftButton):
                        if self.collision_mode:
                            self._paint_collision_at(event.pos())
                        else:
                            self._paint_at(event.pos())
                elif event.type() == event.MouseButtonRelease:
                    if event.button() == Qt.LeftButton:
                        self.drawing = False

            if self.active_tile_stamp:
                if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                    img_x = int(self.offset[0] + event.pos().x() / self.zoom)
                    img_y = int(self.offset[1] + event.pos().y() / self.zoom)
                    snap_x = int(img_x // 32) * 32
                    snap_y = int(img_y // 32) * 32
                    self._place_tile_stamp((snap_x, snap_y))
                    self.update_canvas()
                    self.tile_drawing = True
                    self.last_tile_stamp_pos = (snap_x, snap_y)
                    return True
                elif event.type() == event.MouseMove and self.tile_drawing and (event.buttons() & Qt.LeftButton):
                    img_x = int(self.offset[0] + event.pos().x() / self.zoom)
                    img_y = int(self.offset[1] + event.pos().y() / self.zoom)
                    snap_x = int(img_x // 32) * 32
                    snap_y = int(img_y // 32) * 32
                    if self.last_tile_stamp_pos != (snap_x, snap_y):
                        self._place_tile_stamp((snap_x, snap_y))
                        self.update_canvas()
                        self.last_tile_stamp_pos = (snap_x, snap_y)
                    return True
                elif event.type() == event.MouseButtonRelease and event.button() == Qt.LeftButton:
                    self.tile_drawing = False
                    self.last_tile_stamp_pos = None
                    return True

        return super().eventFilter(obj, event)

    def _check_trigger_click(self, widget_pos):
        """Check if user clicked on an existing trigger to edit it"""
        img_x = int(self.offset[0] + widget_pos.x() / self.zoom)
        img_y = int(self.offset[1] + widget_pos.y() / self.zoom)
        
        for i, trigger in enumerate(self.trigger_rectangles):
            start_x, start_y = trigger["start"]
            end_x, end_y = trigger["end"]
            
            if start_x <= img_x <= end_x and start_y <= img_y <= end_y:
                self._edit_trigger_command(i)
                return True
        
        return False

    def _setup_refresh_rate(self):
        """Set up the stamp preview timer to match display refresh rate"""
        screen = QApplication.primaryScreen()
        refresh_rate = screen.refreshRate()
        if refresh_rate > 0:
            interval = int(1000 / refresh_rate)
            self.stamp_preview_timer.setInterval(interval)
            self.log(f"Stamp preview timer set to {refresh_rate}Hz ({interval}ms)")
        else:
            self.stamp_preview_timer.setInterval(16)
            self.log("Stamp preview timer set to 60Hz (fallback)")

    def toggle_grid(self):
        """Toggle the 32x32 grid overlay"""
        self.show_grid = not self.show_grid
        self.grid_btn.setText("Hide Grid" if self.show_grid else "Show Grid")
        self.log(f"Grid: {'ON' if self.show_grid else 'OFF'}")
        self.update_canvas()

    def _delete_spawn_area(self, spawn_index):
        """Delete a spawn area"""
        if 0 <= spawn_index < len(self.spawn_areas):
            spawn_area = self.spawn_areas.pop(spawn_index)
            self.log(f"Deleted spawn area at ({spawn_area['x']},{spawn_area['y']})")
            self.update_canvas()

    def open_enemy_list_dialog(self):
        """Open dialog to edit the enemy list"""
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit Enemy List")
        dlg.resize(400, 300)
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("List all enemies that can spawn in this world:"))
        layout.addWidget(QLabel("(One enemy per line)"))
        
        from PyQt5.QtWidgets import QTextEdit
        enemy_edit = QTextEdit()
        enemy_edit.setPlainText("\n".join(self.enemy_list))
        layout.addWidget(enemy_edit)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dlg.setLayout(layout)
        
        def save_enemy_list():
            text = enemy_edit.toPlainText()
            self.enemy_list = [line.strip() for line in text.split('\n') if line.strip()]
            self.log(f"Enemy list saved: {len(self.enemy_list)} enemies")
            dlg.accept()
        
        save_btn.clicked.connect(save_enemy_list)
        cancel_btn.clicked.connect(dlg.reject)
        
        dlg.exec_()

    def import_map_package(self):
        """Import a map package from a zip file"""
        import zipfile
        import json
        
        zip_path, _ = QFileDialog.getOpenFileName(
            self, "Import Map Package", "", "ZIP Files (*.zip)"
        )
        
        if not zip_path:
            return
            
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                if "map.png" in zip_file.namelist():
                    map_data = zip_file.read("map.png")
                    self.pixmap = QPixmap()
                    self.pixmap.loadFromData(map_data)
                    self.collision_layer = QPixmap(self.pixmap.size())
                    self.collision_layer.fill(QColor(255,255,255,0))
                
                if "collision.png" in zip_file.namelist():
                    collision_data = zip_file.read("collision.png")
                    self.collision_layer = QPixmap()
                    self.collision_layer.loadFromData(collision_data)
                
                if "map_data.json" in zip_file.namelist():
                    json_data = zip_file.read("map_data.json")
                    self._import_json_data(json_data.decode('utf-8'))
                
            self.log(f"Imported map package from: {zip_path}")
            self.update_canvas()
            
        except Exception as e:
            self.log(f"Import failed: {str(e)}")

    def _import_json_data(self, json_str):
        """Import data from JSON string"""
        import json
        
        try:
            data = json.loads(json_str)
            
            self.prefab_objects.clear()
            self.npc_objects.clear()
            self.trigger_rectangles.clear()
            self.spawn_areas.clear()
            
            for prefab in data.get("prefabs", []):
                prefab_name = prefab["name"]
                if "_" in prefab_name:
                    name, category = prefab_name.rsplit("_", 1)
                else:
                    name = prefab_name
                    category = "default"
                
                actual_prefab = self._find_prefab_by_name_and_category(name, category)
                if actual_prefab:
                    self.prefab_objects.append({
                        "x": prefab["x"],
                        "y": prefab["y"],
                        "image": actual_prefab["image"],
                        "collision": actual_prefab["collision"]
                    })
                else:
                    self.log(f"Warning: Prefab '{prefab_name}' not found, using placeholder")
                    self.prefab_objects.append({
                        "x": prefab["x"],
                        "y": prefab["y"],
                        "image": QPixmap(32, 32),
                        "collision": None
                    })
            
            for npc in data.get("npcs", []):
                npc_name = npc["name"]
                if "_" in npc_name:
                    name, category = npc_name.rsplit("_", 1)
                else:
                    name = npc_name
                    category = "default"
                
                actual_npc = self._find_npc_by_name_and_category(name, category)
                if actual_npc:
                    self.npc_objects.append({
                        "x": npc["x"],
                        "y": npc["y"],
                        "image": actual_npc["image"],
                        "collision": actual_npc["collision"]
                    })
                else:
                    self.log(f"Warning: NPC '{npc_name}' not found, using placeholder")
                    self.npc_objects.append({
                        "x": npc["x"],
                        "y": npc["y"],
                        "image": QPixmap(32, 32),
                        "collision": None
                    })
            
            for trigger in data.get("triggers", []):
                self.trigger_rectangles.append({
                    "start": (trigger["start_x"], trigger["start_y"]),
                    "end": (trigger["end_x"], trigger["end_y"]),
                    "command": trigger["command"]
                })
            
            for spawn in data.get("spawn_areas", []):
                self.spawn_areas.append({
                    "x": spawn["chunk_x"] * 32,
                    "y": spawn["chunk_y"] * 32
                })
            
            self.enemy_list = data.get("enemy_list", ["jimmy"])
            
            self.log(f"Imported: {len(self.prefab_objects)} prefabs, {len(self.npc_objects)} NPCs, {len(self.trigger_rectangles)} triggers, {len(self.spawn_areas)} spawn areas")
            
        except Exception as e:
            self.log(f"JSON import failed: {str(e)}")

    def _find_prefab_by_name_and_category(self, name, category):
        """Find a prefab by name and category"""
        if category in self.prefabs:
            for prefab in self.prefabs[category]:
                if prefab["name"] == name:
                    return prefab
        return None

    def _find_npc_by_name_and_category(self, name, category):
        """Find an NPC by name and category"""
        if category in self.npcs:
            for npc in self.npcs[category]:
                if npc["name"] == name:
                    return npc
        return None

    def _load_tiles(self):
        self.tiles.clear()
        for root, dirs, files in os.walk(self.tile_stamp_folder):
            category = os.path.relpath(root, self.tile_stamp_folder)
            if category == ".":
                category = "Uncategorized"
            if category not in self.tiles:
                self.tiles[category] = []
            for file in files:
                if file.endswith(".png") and not file.endswith("_collision.png"):
                    name = os.path.splitext(file)[0]
                    img = QPixmap(os.path.join(root, file))
                    collision_img = None
                    collision_path = os.path.join(root, f"{name}_collision.png")
                    if os.path.exists(collision_path):
                        collision_img = QPixmap(collision_path)
                    self.tiles[category].append({
                        "name": name,
                        "image": img,
                        "collision": collision_img
                    })

    def open_tile_stamp_dialog(self):
        pass

    def _place_tile_stamp(self, pos):
        if not self.active_tile_stamp or not pos:
            return
        painter = QPainter(self.pixmap)
        painter.drawPixmap(pos[0], pos[1], self.active_tile_stamp["image"])
        painter.end()
        if self.active_tile_stamp["collision"]:
            painter = QPainter(self.collision_layer)
            painter.drawPixmap(pos[0], pos[1], self.active_tile_stamp["collision"])
            painter.end()

    def toggle_tile_editor(self):
        self.tile_editor_mode = not getattr(self, "tile_editor_mode", False)
        self.tile_editor_btn.setChecked(self.tile_editor_mode)
        if self.tile_editor_mode:
            self.palette_scroll.hide()
            self.tile_selector = TileSelectorWidget(self.tiles, self.set_active_tile_stamp, self)
            self.sidebar_layout.addWidget(self.tile_selector)
            self.active_tile_stamp = None
        else:
            if hasattr(self, "tile_selector"):
                self.sidebar_layout.removeWidget(self.tile_selector)
                self.tile_selector.deleteLater()
                del self.tile_selector
            self.palette_scroll.show()
            self.active_tile_stamp = None
        self.update_canvas()

    def set_active_tile_stamp(self, tile):
        self.active_tile_stamp = tile
        self.update_canvas()

class TileSelectorWidget(QWidget):
    def __init__(self, tiles, select_callback, parent=None):
        super().__init__(parent)
        self.tiles = tiles
        self.select_callback = select_callback
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Tile Categories")
        self.tree.setIconSize(QSize(32, 32))
        layout.addWidget(self.tree)

        for category, tiles in self.tiles.items():
            category_item = QTreeWidgetItem([category])
            category_item.setExpanded(False)
            self.tree.addTopLevelItem(category_item)
            for tile in tiles:
                tile_item = QTreeWidgetItem([tile["name"]])
                icon = QIcon(tile["image"])
                tile_item.setIcon(0, icon)
                tile_item.setData(0, Qt.ItemDataRole.UserRole, tile)
                category_item.addChild(tile_item)

        self.tree.itemClicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, item, col):
        if item.parent():
            self.select_callback(item.data(0, Qt.ItemDataRole.UserRole))

    def _close_tile_editor(self):
        parent = self.parent()
        if parent and hasattr(parent, 'toggle_tile_editor'):
            parent.toggle_tile_editor()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = EditorWindow()
    window.show()
    sys.exit(app.exec_())