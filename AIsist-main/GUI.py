import sys
import os
import json
import threading
import sounddevice as sd
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QFrame,
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QSlider, QComboBox, QGroupBox, QStackedWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QPoint, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor

# Импортируем мозг и уши
import brain
from listener import start_listening

if getattr(sys, 'frozen', False):
    # Если запущено как .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Если запущено как скрипт .py
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DEFAULT_CONFIG = {
    "commands": {"открой фотошоп": "C:/Program Files/Adobe/Photoshop.exe"},
    "volume": 80, "mic_index": None, "speaker_index": None, "history": []
}

# ==========================================
# МОСТ ДЛЯ ПЕРЕДАЧИ ОТВЕТОВ ДЖАРВИСА В GUI
# ==========================================
class JarvisSignalBridge(QObject):
    jarvis_spoke = pyqtSignal(str)

signal_bridge = JarvisSignalBridge()
brain.gui_callback = lambda text: signal_bridge.jarvis_spoke.emit(text)

# ==========================================
# ФОНОВЫЙ ПОТОК МИКРОФОНА
# ==========================================
class JarvisThread(QThread):
    text_recognized = pyqtSignal(str)

    def __init__(self, mic_index):
        super().__init__()
        self.mic_index = mic_index
        self.stop_event = threading.Event()

    def run(self):
        def on_speech(text):
            self.text_recognized.emit(text) 
            brain.execute_command(text)           
            
        start_listening(on_speech, self.mic_index, self.stop_event)

    def stop(self):
        self.stop_event.set() 

# ==========================================
# ГЛАВНОЕ ОКНО
# ==========================================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jarvis Hub")
        self.resize(750, 520)
        self.setStyleSheet("background-color: #121212; color: #ffffff; font-family: 'Segoe UI', Arial;")

        self.config = self.load_config()
        self.is_listening = False 
        self.jarvis_thread = None

        threading.Thread(target=brain.run_telegram_bot, daemon=True).start()
        signal_bridge.jarvis_spoke.connect(self.on_jarvis_speech)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- ЛЕВАЯ ЧАСТЬ ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)

        # ВЕРХНЯЯ ПАНЕЛЬ С КНОПКАМИ (Настройки и Выход)
        top_bar = QHBoxLayout()
        
        self.toggle_settings_btn = QPushButton("⚙ Настройки")
        self.toggle_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_settings_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; color: #888888; font-size: 14px; font-weight: bold; text-align: left; } QPushButton:hover { color: #ffffff; }")
        self.toggle_settings_btn.clicked.connect(self.switch_left_panel)
        
        self.exit_btn = QPushButton("❌ Выход")
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; color: #d32f2f; font-size: 14px; font-weight: bold; text-align: right; } QPushButton:hover { color: #ff4d4d; }")
        self.exit_btn.clicked.connect(self.quit_app)

        top_bar.addWidget(self.toggle_settings_btn, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        top_bar.addStretch()
        top_bar.addWidget(self.exit_btn, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        
        left_layout.addLayout(top_bar)

        self.left_stack = QStackedWidget()

        # ЭКРАН 1: КНОПКА ПИТАНИЯ (Изначально КРАСНАЯ = ВЫКЛ)
        self.page_power = QWidget()
        page_power_layout = QVBoxLayout(self.page_power)
        page_power_layout.addStretch()
        
        self.power_btn = QPushButton("ВЫКЛ")
        self.power_btn.setFixedSize(200, 200)
        self.power_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.power_btn.setStyleSheet("QPushButton { background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #8b1c1c, stop:1 #4a0f0f); border-radius: 100px; border: 3px solid #d32f2f; font-size: 28px; font-weight: bold; color: #ffffff; } QPushButton:hover { border: 5px solid #ff4d4d; }")
        self.power_btn.clicked.connect(self.toggle_power)

        page_power_layout.addWidget(self.power_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        page_power_layout.addStretch()

        # ЭКРАН 2: НАСТРОЙКИ
        self.page_settings = QWidget()
        page_settings_layout = QVBoxLayout(self.page_settings)
        page_settings_layout.setSpacing(15)

        group_box_style = """
            QGroupBox { border: 2px solid #2a2a2a; border-radius: 8px; margin-top: 20px; padding-top: 15px; font-weight: bold; color: #888888; } 
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 15px; }
        """

        prog_group = QGroupBox("Команды и пути к программам")
        prog_group.setStyleSheet(group_box_style)
        prog_layout = QVBoxLayout(prog_group)
        self.prog_table = QTableWidget(0, 2)
        self.prog_table.setHorizontalHeaderLabels(["Команда (что сказать)", "Путь к файлу"])
        self.prog_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.prog_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.prog_table.setStyleSheet("QTableWidget { background-color: #1e1e1e; border: 1px solid #2a2a2a; color: white; gridline-color: #333333; }")
        prog_layout.addWidget(self.prog_table)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Добавить")
        del_btn = QPushButton("- Удалить")
        add_btn.setStyleSheet("background-color: #2a2a2a; color: #35d18a; border-radius: 4px; padding: 5px;")
        del_btn.setStyleSheet("background-color: #2a2a2a; color: #d32f2f; border-radius: 4px; padding: 5px;")
        add_btn.clicked.connect(lambda: self.prog_table.insertRow(self.prog_table.rowCount()))
        del_btn.clicked.connect(lambda: self.prog_table.removeRow(self.prog_table.currentRow()))
        btn_layout.addWidget(add_btn); btn_layout.addWidget(del_btn)
        prog_layout.addLayout(btn_layout)
        page_settings_layout.addWidget(prog_group, stretch=2)

        audio_group = QGroupBox("Аудио устройства и громкость")
        audio_group.setStyleSheet(group_box_style)
        audio_layout = QVBoxLayout(audio_group)

        vol_layout = QHBoxLayout()
        vol_layout.addWidget(QLabel("Громкость голоса:"))
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_label = QLabel("80%")
        self.vol_label.setFixedWidth(40)
        self.vol_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.vol_slider.valueChanged.connect(lambda val: self.vol_label.setText(f"{val}%"))
        vol_layout.addWidget(self.vol_slider)
        vol_layout.addWidget(self.vol_label) 
        audio_layout.addLayout(vol_layout)

        mic_layout = QHBoxLayout()
        mic_layout.addWidget(QLabel("Микрофон:"))
        self.mic_combo = QComboBox()
        self.mic_combo.setStyleSheet("background-color: #1e1e1e; border: 1px solid #2a2a2a; color: white; padding: 4px;")
        mic_layout.addWidget(self.mic_combo, stretch=1)
        audio_layout.addLayout(mic_layout)

        speaker_layout = QHBoxLayout()
        speaker_layout.addWidget(QLabel("Динамики:"))
        self.speaker_combo = QComboBox()
        self.speaker_combo.setStyleSheet("background-color: #1e1e1e; border: 1px solid #2a2a2a; color: white; padding: 4px;")
        speaker_layout.addWidget(self.speaker_combo, stretch=1)
        audio_layout.addLayout(speaker_layout)

        self.save_btn = QPushButton("💾 Сохранить настройки")
        self.save_btn.setStyleSheet("background-color: #0078D7; border: none; padding: 10px; border-radius: 4px; color: white; font-weight: bold; margin-top: 10px;")
        self.save_btn.clicked.connect(self.save_config)
        audio_layout.addWidget(self.save_btn)

        page_settings_layout.addWidget(audio_group, stretch=1)
        self.left_stack.addWidget(self.page_power); self.left_stack.addWidget(self.page_settings)
        left_layout.addWidget(self.left_stack)
        main_layout.addWidget(left_panel, stretch=2)

        # --- ПРАВАЯ ЧАСТЬ (История) ---
        right_panel = QFrame()
        right_panel.setFixedWidth(280) 
        right_panel.setStyleSheet("background-color: #1e1e1e; border-left: 2px solid #2a2a2a;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 20, 15, 20)

        history_label = QLabel("ДИАЛОГ С СИСТЕМОЙ")
        history_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        history_label.setStyleSheet("color: #888888; border: none;")
        right_layout.addWidget(history_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("border-top: 1px solid #444; margin-bottom: 10px;")
        right_layout.addWidget(line)

        self.history_list = QListWidget()
        self.history_list.setStyleSheet("QListWidget { border: none; background-color: transparent; font-size: 13px; } QListWidget::item { padding: 6px 0px; }")
        right_layout.addWidget(self.history_list)
        main_layout.addWidget(right_panel)

        self.populate_audio_devices()
        self.apply_config_to_ui()

    # ==========================================
    # ЛОГИКА ВКЛ/ВЫКЛ
    # ==========================================
    def toggle_power(self):
        if not self.is_listening:
            # ВКЛЮЧАЕМ МИКРОФОН (ЗЕЛЕНЫЙ ЦВЕТ)
            mic_idx = self.config.get("mic_index")
            self.jarvis_thread = JarvisThread(mic_idx)
            self.jarvis_thread.text_recognized.connect(self.on_user_speech)
            self.jarvis_thread.start() 
            
            self.is_listening = True
            self.power_btn.setText("ВКЛ")
            self.power_btn.setStyleSheet("QPushButton { background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #1a6b46, stop:1 #0f3d28); border-radius: 100px; border: 3px solid #27a36b; font-size: 28px; font-weight: bold; color: #ffffff; } QPushButton:hover { border: 5px solid #35d18a; }")
        else:
            # ВЫКЛЮЧАЕМ МИКРОФОН (КРАСНЫЙ ЦВЕТ)
            if self.jarvis_thread:
                self.jarvis_thread.stop()
                self.jarvis_thread.wait() 
                self.jarvis_thread = None
                
            self.is_listening = False
            self.power_btn.setText("ВЫКЛ")
            self.power_btn.setStyleSheet("QPushButton { background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #8b1c1c, stop:1 #4a0f0f); border-radius: 100px; border: 3px solid #d32f2f; font-size: 28px; font-weight: bold; color: #ffffff; } QPushButton:hover { border: 5px solid #ff4d4d; }")

    # ПОЛНОЕ ЗАКРЫТИЕ ПРОГРАММЫ
    def quit_app(self):
        if self.jarvis_thread:
            self.jarvis_thread.stop()
            self.jarvis_thread.wait()
        QApplication.quit()
        os._exit(0) # Убивает все фоновые процессы, включая Telegram-бота

    # ==========================================
    # ЛОГИКА ИСТОРИИ (С ЦВЕТАМИ)
    # ==========================================
    def on_user_speech(self, text):
        self.add_history_record(f"👤 Вы: {text}", is_jarvis=False)

    def on_jarvis_speech(self, text):
        self.add_history_record(f"🤖 Джарвис: {text}", is_jarvis=True)

    def add_history_record(self, formatted_text, is_jarvis=False):
        item = QListWidgetItem(formatted_text)
        if is_jarvis: item.setForeground(QColor("#35d18a")) 
        else: item.setForeground(QColor("#ffffff")) 
        self.history_list.insertItem(0, item)
        
        history = self.config.get("history", [])
        history.insert(0, formatted_text)
        if len(history) > 40: 
            history = history[:40]
            self.history_list.takeItem(self.history_list.count() - 1)
        self.config["history"] = history
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    # ==========================================
    # ОСТАЛЬНЫЕ НАСТРОЙКИ
    # ==========================================
    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
            return DEFAULT_CONFIG.copy()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: return DEFAULT_CONFIG.copy()

    def populate_audio_devices(self):
        devices = sd.query_devices()
        self.mic_combo.addItem("Системный по умолчанию", userData=None)
        self.speaker_combo.addItem("Системные по умолчанию", userData=None)
        for i, device in enumerate(devices):
            name = device['name']
            if device['max_input_channels'] > 0: self.mic_combo.addItem(f"🎙 {name}", userData=i)
            if device['max_output_channels'] > 0: self.speaker_combo.addItem(f"🔊 {name}", userData=i)

    def apply_config_to_ui(self):
        vol = self.config.get("volume", 80)
        self.vol_slider.setValue(vol)
        self.vol_label.setText(f"{vol}%")
        
        mic_idx = self.config.get("mic_index")
        if mic_idx is not None:
            index = self.mic_combo.findData(mic_idx)
            if index != -1: self.mic_combo.setCurrentIndex(index)
        speaker_idx = self.config.get("speaker_index")
        if speaker_idx is not None:
            index = self.speaker_combo.findData(speaker_idx)
            if index != -1: self.speaker_combo.setCurrentIndex(index)
        commands = self.config.get("commands", {})
        self.prog_table.setRowCount(0)
        for cmd, path in commands.items():
            row = self.prog_table.rowCount()
            self.prog_table.insertRow(row); self.prog_table.setItem(row, 0, QTableWidgetItem(cmd)); self.prog_table.setItem(row, 1, QTableWidgetItem(path))
        
        self.history_list.clear()
        for text in self.config.get("history", []): 
            item = QListWidgetItem(text)
            if text.startswith("🤖"): item.setForeground(QColor("#35d18a"))
            else: item.setForeground(QColor("#ffffff"))
            self.history_list.addItem(item)

    def save_config(self):
        new_commands = {}
        for row in range(self.prog_table.rowCount()):
            cmd_item = self.prog_table.item(row, 0); path_item = self.prog_table.item(row, 1)
            if cmd_item and path_item:
                cmd_text = cmd_item.text().strip().lower(); path_text = path_item.text().strip()
                if cmd_text and path_text: new_commands[cmd_text] = path_text
        self.config["commands"] = new_commands
        self.config["volume"] = self.vol_slider.value()
        self.config["mic_index"] = self.mic_combo.currentData()
        self.config["speaker_index"] = self.speaker_combo.currentData()
        with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(self.config, f, indent=4, ensure_ascii=False)
        self.save_btn.setText("✅ Успешно сохранено!")
        self.save_btn.setStyleSheet("background-color: #27a36b; border: none; padding: 10px; border-radius: 4px; color: white; font-weight: bold; margin-top: 10px;")
        QTimer.singleShot(2000, lambda: (self.save_btn.setText("💾 Сохранить настройки"), self.save_btn.setStyleSheet("background-color: #0078D7; border: none; padding: 10px; border-radius: 4px; color: white; font-weight: bold; margin-top: 10px;")))

    def switch_left_panel(self):
        if self.left_stack.currentIndex() == 0:
            self.left_stack.setCurrentIndex(1); self.toggle_settings_btn.setText("⬅ Назад к управлению")
        else:
            self.left_stack.setCurrentIndex(0); self.toggle_settings_btn.setText("⚙ Настройки")

    def closeEvent(self, event):
        event.ignore(); self.hide()

# ==========================================
# ПЛАВАЮЩИЙ ВИДЖЕТ
# ==========================================
class FloatingWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window 
        self.old_pos = self.pos() 
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(60, 60)
        self.core_label = QLabel(self)
        self.core_label.setFixedSize(60, 60)
        self.core_label.setStyleSheet("QLabel { background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 rgba(0, 255, 255, 255), stop:1 rgba(0, 50, 150, 200)); border-radius: 30px; border: 2px solid #00ffff; } QLabel:hover { border: 3px solid #ffffff; }")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: 
            self.old_pos = event.globalPosition().toPoint()
        # ЕСЛИ НАЖАТЬ ПРАВОЙ КНОПКОЙ МЫШИ НА ВИДЖЕТ - ПРОГРАММА ЗАКРОЕТСЯ
        elif event.button() == Qt.MouseButton.RightButton:
            self.main_window.quit_app()

    def mouseMoveEvent(self, event):
        if not self.old_pos: return
        delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
        self.move(self.x() + delta.x(), self.y() + delta.y()); self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.main_window.isHidden(): self.main_window.show(); self.main_window.activateWindow() 
            else: self.main_window.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_gui = MainWindow()
    widget = FloatingWidget(main_gui)
    widget.show()
    sys.exit(app.exec())
