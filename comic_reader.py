import sys
import os
import zipfile
import rarfile
import tempfile
import datetime
import json
import locale

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QAction, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QAbstractItemView, QInputDialog, QMessageBox,
    QMenu, QListWidget, QListWidgetItem, QDialog, QTextEdit, QLineEdit,
    QScrollArea
)
from PyQt5.QtGui import QPixmap, QFontDatabase, QFont, QColor, QPalette, QIcon, QPainter, QTransform
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QSize, QTimer, QPoint, QTranslator

from PIL import Image

# WinRAR yolunu ayarla
rarfile.UNRAR_TOOL = r"C:\Program Files\WinRAR\UnRAR.exe"

class FileManager:
    def __init__(self):
        self.temp_dir = None
        self.current_folder = os.path.expanduser("~")
        self.supported_extensions = ['.cbz', '.cbr', '.jpg', '.jpeg', '.png', '.bmp', '.gif']

    def cleanup_temp(self):
        """Geçici dosyaları temizler"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                os.rmdir(self.temp_dir)
            except Exception as e:
                print(f"Geçici dosya temizleme hatası: {e}")
            finally:
                self.temp_dir = None

    def get_file_size_str(self, size_bytes):
        """Dosya boyutunu okunabilir formata çevirir"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def get_file_type(self, file_path):
        """Dosya türünü belirler"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.cbr']:
            return "CBR Dosyası"
        elif ext in ['.cbz']:
            return "CBZ Dosyası"
        elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            return "Resim"
        elif os.path.isdir(file_path):
            return "Klasör"
        else:
            return "Dosya"

    def open_file(self, file_path):
        """Dosyayı açar ve sayfaları döndürür"""
        if not file_path or not os.path.exists(file_path):
            return None, []

        self.cleanup_temp()
        ext = os.path.splitext(file_path)[1].lower()
        self.temp_dir = tempfile.mkdtemp()
        pages = []

        try:
            if ext == '.cbz':
                with zipfile.ZipFile(file_path, 'r') as zf:
                    zf.extractall(self.temp_dir)
                    pages = self._get_image_files(self.temp_dir)
            elif ext == '.cbr':
                with rarfile.RarFile(file_path, 'r') as rf:
                    rf.extractall(self.temp_dir)
                    pages = self._get_image_files(self.temp_dir)
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                pages = [file_path]
                self.temp_dir = None
            else:
                return None, []

            return self.temp_dir, sorted(pages)
        except Exception as e:
            print(f"Dosya açma hatası: {e}")
            self.cleanup_temp()
            return None, []

    def _get_image_files(self, directory):
        """Klasördeki resim dosyalarını bulur"""
        image_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if os.path.splitext(file)[1].lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                    image_files.append(os.path.join(root, file))
        return image_files

    def save_json(self, data, filename):
        """JSON dosyasını kaydeder"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"JSON kaydetme hatası: {e}")
            return False

    def load_json(self, filename):
        """JSON dosyasını yükler"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"JSON yükleme hatası: {e}")
        return {}

    def get_next_file_in_directory(self, current_file):
        """Klasördeki sonraki dosyayı bulur"""
        if not current_file:
            return None

        directory = os.path.dirname(current_file)
        files = sorted([
            f for f in os.listdir(directory)
            if os.path.splitext(f)[1].lower() in self.supported_extensions
        ])
        
        try:
            current_index = files.index(os.path.basename(current_file))
            if current_index < len(files) - 1:
                return os.path.join(directory, files[current_index + 1])
        except ValueError:
            pass
        
        return None

    def save_screenshot(self, pixmap, directory="screenshots"):
        """Ekran görüntüsünü kaydeder"""
        if not os.path.exists(directory):
            os.makedirs(directory)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(directory, filename)

        try:
            pixmap.save(filepath)
            return filepath
        except Exception as e:
            print(f"Ekran görüntüsü kaydetme hatası: {e}")
            return None

class ComicLibrary:
    def __init__(self):
        self.library_file = "library.json"
        self.series = self.load_library()
    
    def load_library(self):
        if os.path.exists(self.library_file):
            try:
                with open(self.library_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_library(self):
        with open(self.library_file, 'w', encoding='utf-8') as f:
            json.dump(self.series, f, ensure_ascii=False, indent=4)
    
    def add_series(self, name, folder_path):
        if name not in self.series:
            self.series[name] = {
                'folder': folder_path,
                'last_read': None,
                'books': []
            }
            self.update_series_books(name)
            self.save_library()
    
    def update_series_books(self, series_name):
        if series_name in self.series:
            folder = self.series[series_name]['folder']
            books = []
            if os.path.exists(folder):
                for item in sorted(os.listdir(folder)):
                    file_path = os.path.join(folder, item)
                    if os.path.isfile(file_path):
                        ext = os.path.splitext(file_path)[1].lower()
                        if ext in ['.cbz', '.cbr']:
                            books.append({
                                'path': file_path,
                                'name': item,
                                'last_page': 0,
                                'last_read_date': None
                            })
            self.series[series_name]['books'] = books
            self.save_library()
    
    def update_last_read(self, file_path, page=0):
        """Son okunan sayfa ve tarihi günceller"""
        for series in self.series.values():
            for book in series['books']:
                if book['path'] == file_path:
                    book['last_page'] = page
                    book['last_read_date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    series['last_read'] = file_path
                    self.save_library()
                    return True
        return False
    
    def get_last_read(self):
        """En son okunan kitabı ve sayfayı döndürür"""
        last_file = None
        last_page = 0
        last_date = None
        
        for series in self.series.values():
            for book in series['books']:
                if book.get('last_read_date'):
                    if not last_date or book['last_read_date'] > last_date:
                        last_file = book['path']
                        last_page = book['last_page']
                        last_date = book['last_read_date']
        
        return last_file, last_page

class ImageManager:
    def __init__(self):
        self.zoom_level = 1.0
        self.zoom_step = 0.1
        self.rotation = 0
        self.scroll_pos = QPoint(0, 0)
        self.double_page_mode = False
        self.image_cache = {}
        self.cache_size = 5  # Önbellekte tutulacak sayfa sayısı
        self.current_pixmap = None

    def clear_cache(self):
        """Önbelleği temizler"""
        self.image_cache.clear()
        self.current_pixmap = None

    def get_cached_image(self, page_path):
        """Önbellekten görüntüyü alır veya yükler"""
        if page_path in self.image_cache:
            return self.image_cache[page_path]
        
        # Önbellek doluysa en eski görüntüyü sil
        if len(self.image_cache) >= self.cache_size:
            oldest_key = next(iter(self.image_cache))
            del self.image_cache[oldest_key]
        
        # Yeni görüntüyü yükle ve önbelleğe ekle
        try:
            pixmap = QPixmap(page_path)
            if not pixmap.isNull():
                self.image_cache[page_path] = pixmap
                return pixmap
        except Exception as e:
            print(f"Görüntü yükleme hatası: {e}")
        return None

    def show_page(self, image_label, pages, current_page):
        """Sayfayı görüntüler"""
        if not pages or not (0 <= current_page < len(pages)):
            return None

        try:
            # Önbellekten görüntüyü al
            pixmap = self.get_cached_image(pages[current_page])
            if not pixmap:
                return None

            # Döndürme
            if self.rotation != 0:
                transform = QTransform()
                transform.rotate(self.rotation)
                pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)

            # Ayna görüntüsü
            if self.mirrored:
                pixmap = pixmap.transformed(QTransform().scale(-1, 1))

            # Ölçeklendirme
            scaled_pixmap = pixmap.scaled(
                image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Görüntüyü ayarla
            image_label.setPixmap(scaled_pixmap)
            self.current_pixmap = scaled_pixmap
            
            return f"Sayfa: {current_page + 1} / {len(pages)}"
        except Exception as e:
            print(f"Sayfa gösterim hatası: {e}")
            return None

class ThemeManager:
    def __init__(self):
        self.themes = {
            "dark": {
                "background": "#2e2e2e",
                "text": "white",
                "button_bg": "#4a90e2",
                "button_hover": "#357ab8",
                "border": "#555",
                "header_bg": "#444",
                "selection_bg": "#4a90e2",
                "scroll_bg": "rgba(0, 0, 0, 0.3)",
                "scroll_handle": "rgba(255, 255, 255, 0.3)"
            },
            "light": {
                "background": "#f0f0f0",
                "text": "black",
                "button_bg": "#007acc",
                "button_hover": "#005fa3",
                "border": "#ddd",
                "header_bg": "#f5f5f5",
                "selection_bg": "#007acc",
                "scroll_bg": "rgba(0, 0, 0, 0.1)",
                "scroll_handle": "rgba(0, 0, 0, 0.2)"
            }
        }
        self.current_theme = "dark"

    def apply_theme(self, window):
        theme = self.themes[self.current_theme]
        
        # Ana pencere stili
        window.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {theme["background"]};
                color: {theme["text"]};
            }}
            QPushButton {{
                background-color: {theme["button_bg"]};
                color: white;
                border-radius: 8px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {theme["button_hover"]};
            }}
            QLabel {{
                color: {theme["text"]};
            }}
            QTableWidget {{
                background-color: {theme["background"]};
                color: {theme["text"]};
                gridline-color: {theme["border"]};
                border: 1px solid {theme["border"]};
            }}
            QHeaderView::section {{
                background-color: {theme["header_bg"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
                padding: 4px;
            }}
            QTableWidget::item:selected {{
                background-color: {theme["selection_bg"]};
                color: white;
            }}
            QScrollBar {{
                background: {theme["scroll_bg"]};
            }}
            QScrollBar::handle {{
                background: {theme["scroll_handle"]};
            }}
        """)

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        return self.current_theme

class ComicReader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_manager = FileManager()
        self.image_manager = ImageManager()
        self.theme_manager = ThemeManager()
        self.library = ComicLibrary()
        self.init_variables()
        self.init_ui()
        self.theme_manager.apply_theme(self)
        self.load_settings()
        self.change_language(self.current_language)
        
        # Performans ayarları
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setUpdatesEnabled(True)

        # Yeni değişkenler
        self.rotation = 0
        self.mirrored = False

    def init_variables(self):
        # Temel değişkenler
        self.setWindowTitle("Çizgi Roman Okuyucu")
        self.setMinimumSize(600, 500)
        self.resize(900, 700)
        self.setWindowState(Qt.WindowMaximized)

        # Sayfa ve görüntüleme değişkenleri
        self.current_page = 0
        self.pages = []
        self.mouse_pos = QPoint(0, 0)

        # Kütüphane ve veri yönetimi
        self.favorites = self.file_manager.load_json("favorites.json")
        self.notes = self.file_manager.load_json("notes.json")

        # Otomatik oynatma ve kaydırma
        self.auto_play = False
        self.auto_play_timer = QTimer(self)
        self.auto_play_timer.timeout.connect(self.auto_next_page)
        self.auto_play_speed = 3000

        self.auto_scroll = False
        self.auto_scroll_timer = QTimer(self)
        self.auto_scroll_timer.timeout.connect(self.auto_scroll_page)
        self.auto_scroll_speed = 50
        self.scroll_direction = 1

        # Animasyon ayarları
        self.animation_duration = 300
        self.animation_type = "slide"
        self.animation_direction = "right"

        # Önizleme ayarları
        self.preview_size = 150
        self.preview_visible = False
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.setInterval(100)
        self.preview_zoom_level = 1.0
        self.preview_zoom_step = 0.1
        self.preview_min_zoom = 0.5
        self.preview_max_zoom = 3.0

        # Dil ve çeviri
        self.translator = QTranslator()
        self.current_language = self.file_manager.load_json("settings.json").get("language", "tr")
        self.languages = {
            "tr": "Türkçe",
            "en": "English",
            "de": "Deutsch",
            "fr": "Français",
            "es": "Español"
        }
        self.translations = self.load_translations()

        # Font ayarları
        font_id = QFontDatabase.addApplicationFont("resources/Roboto-Regular.ttf")
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            self.setFont(QFont(font_family, 11))

    def init_ui(self):
        self.create_menu_bar()
        self.statusBar().showMessage("Hazır")

        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Görüntüleyici butonları
        button_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("⬅️ Önceki")
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setToolTip("Önceki sayfa (Sol Ok)")
        button_layout.addWidget(self.prev_button)

        self.page_label = QLabel("Sayfa: - / -")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("padding: 5px; background: rgba(0,0,0,0.1); border-radius: 3px;")
        button_layout.addWidget(self.page_label)

        self.next_button = QPushButton("Sonraki ➡️")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setToolTip("Sonraki sayfa (Sağ Ok)")
        button_layout.addWidget(self.next_button)

        main_layout.addLayout(button_layout)

        # Görüntü etiketi
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 2px solid #444; border-radius: 8px;")
        self.image_label.setMouseTracking(True)
        self.image_label.mouseMoveEvent = self.mouse_move_event
        main_layout.addWidget(self.image_label)
        
        # Animasyon
        self.anim = QPropertyAnimation(self.image_label, b"geometry")
        self.anim.setDuration(300)
        
        # Kaldığınız yerden devam et butonu
        self.continue_button = QPushButton("📖 Kaldığınız Yerden Devam Et")
        self.continue_button.clicked.connect(self.continue_last_reading)
        self.continue_button.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border-radius: 15px;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357ab8;
            }
        """)
        self.continue_button.setFixedWidth(400)
        self.continue_button.setFixedHeight(60)
        
        # Buton yerleşimini sağlayacak layout
        self.continue_layout = QHBoxLayout()
        self.continue_layout.addStretch()
        self.continue_layout.addWidget(self.continue_button)
        self.continue_layout.addStretch()
        
        # Ana layout içine ekle
        self.continue_container = QWidget()
        self.continue_container.setLayout(self.continue_layout)
        self.continue_container.setStyleSheet("background: transparent;")
        
        # Devam et butonunu ortala
        self.continue_button_pos = QVBoxLayout()
        self.continue_button_pos.addStretch()
        self.continue_button_pos.addWidget(self.continue_container)
        self.continue_button_pos.addStretch()
        
        # Overlay için bir widget
        self.overlay_widget = QWidget(self.image_label)
        self.overlay_widget.setLayout(self.continue_button_pos)
        self.overlay_widget.setGeometry(self.image_label.rect())
        self.overlay_widget.show()
        
        # Buton görünürlüğünü kontrol et
        self.check_continue_button_visibility()

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # Dosya menüsü
        file_menu = menubar.addMenu("Dosya")
        self.create_file_menu(file_menu)
        
        # Kütüphane menüsü
        library_menu = menubar.addMenu("Kütüphane")
        self.create_library_menu(library_menu)
        
        # Görünüm menüsü
        view_menu = menubar.addMenu("Görünüm")
        self.create_view_menu(view_menu)
        
        # Ayarlar menüsü
        settings_menu = menubar.addMenu("⚙️ Ayarlar")
        self.create_settings_menu(settings_menu)

    def create_file_menu(self, menu):
        actions = [
            ("📂 Dosya Aç", "Ctrl+O", "Çizgi roman dosyası aç", self.open_file),
            ("📁 Klasör Aç", "Ctrl+K", "Klasör aç", self.open_folder)
        ]
        self.add_menu_actions(menu, actions)

    def create_library_menu(self, menu):
        # Seri ekleme
        add_series = QAction("Yeni Seri Ekle", self)
        add_series.triggered.connect(self.add_new_series)
        menu.addAction(add_series)
        
        # Kütüphane görüntüleme
        show_library = QAction("Kütüphaneyi Göster", self)
        show_library.triggered.connect(self.show_library)
        menu.addAction(show_library)
        
        # Seri listesi
        series_menu = menu.addMenu("Seriler")
        self.update_series_menu(series_menu)
        
        # Favoriler
        favorites_menu = menu.addMenu("Favoriler")
        self.update_favorites_menu(favorites_menu)

    def create_view_menu(self, menu):
        # Ana görünüm seçenekleri
        view_actions = [
            ("🎨 Tema Değiştir", "Ctrl+T", "Açık/Koyu tema değiştir", self.toggle_theme),
            ("📖 Çift Sayfa Modu", "Ctrl+D", "Çift sayfa modunu aç/kapat", self.toggle_double_page),
            ("▶️ Otomatik Oynat", "Ctrl+P", "Otomatik sayfa geçişini başlat/durdur", self.toggle_auto_play)
        ]
        self.add_menu_actions(menu, view_actions)

        # Alt menüler
        self.create_zoom_menu(menu)
        self.create_rotate_menu(menu)
        self.create_scroll_menu(menu)
        self.create_animation_menu(menu)
        self.create_preview_menu(menu)

    def create_zoom_menu(self, parent):
        zoom_menu = parent.addMenu("🔍 Yakınlaştırma")
        actions = [
            ("➕ Yakınlaştır", "Ctrl++", None, self.zoom_in),
            ("➖ Uzaklaştır", "Ctrl+-", None, self.zoom_out),
            ("↩️ Yakınlaştırmayı Sıfırla", "Ctrl+0", None, self.reset_zoom)
        ]
        self.add_menu_actions(zoom_menu, actions)

    def create_rotate_menu(self, parent):
        rotate_menu = parent.addMenu("🔄 Döndürme")
        actions = [
            ("↩️ Sola Döndür", "Ctrl+R", None, self.rotate_left),
            ("↪️ Sağa Döndür", "Ctrl+Shift+R", None, self.rotate_right),
            ("↩️ Döndürmeyi Sıfırla", "Ctrl+Alt+R", None, self.reset_rotation)
        ]
        self.add_menu_actions(rotate_menu, actions)

    def create_scroll_menu(self, parent):
        scroll_menu = parent.addMenu("📜 Kaydırma")
        
        # Otomatik kaydırma
        auto_scroll = QAction("▶️ Otomatik Kaydır", self)
        auto_scroll.setShortcut("Ctrl+S")
        auto_scroll.triggered.connect(self.toggle_auto_scroll)
        scroll_menu.addAction(auto_scroll)

        # Hız alt menüsü
        speed_menu = scroll_menu.addMenu("⏱️ Hız")
        speeds = [("Yavaş", 100), ("Normal", 50), ("Hızlı", 20)]
        for name, speed in speeds:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, s=speed: self.set_auto_scroll_speed(s))
            speed_menu.addAction(action)

        # Yön alt menüsü
        direction_menu = scroll_menu.addMenu("⬆️ Yön")
        directions = [("Yukarı", -1), ("Aşağı", 1)]
        for name, direction in directions:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, d=direction: self.set_scroll_direction(d))
            direction_menu.addAction(action)

    def create_animation_menu(self, parent):
        anim_menu = parent.addMenu("🎬 Animasyon")
        
        # Tür alt menüsü
        type_menu = anim_menu.addMenu("Tür")
        types = ["slide", "fade", "zoom"]
        for t in types:
            action = QAction(t.capitalize(), self)
            action.triggered.connect(lambda checked, type=t: self.set_animation_type(type))
            type_menu.addAction(action)

        # Yön alt menüsü
        direction_menu = anim_menu.addMenu("Yön")
        directions = ["right", "left", "up", "down"]
        for d in directions:
            action = QAction(d.capitalize(), self)
            action.triggered.connect(lambda checked, dir=d: self.set_animation_direction(dir))
            direction_menu.addAction(action)

        # Hız alt menüsü
        speed_menu = anim_menu.addMenu("Hız")
        speeds = [("Yavaş", 500), ("Normal", 300), ("Hızlı", 100)]
        for name, speed in speeds:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, s=speed: self.set_animation_speed(s))
            speed_menu.addAction(action)

    def create_preview_menu(self, parent):
        preview_toggle = QAction("👁️ Sayfa Önizleme", self)
        preview_toggle.setShortcut("Ctrl+Shift+P")
        preview_toggle.triggered.connect(self.toggle_preview)
        parent.addAction(preview_toggle)

        size_menu = parent.addMenu("📏 Önizleme Boyutu")
        sizes = [("Küçük", 100), ("Orta", 150), ("Büyük", 200)]
        for name, size in sizes:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, s=size: self.set_preview_size(s))
            size_menu.addAction(action)

    def create_settings_menu(self, menu):
        language_menu = menu.addMenu("🌐 Dil")
        for lang_code, lang_name in self.languages.items():
            action = QAction(lang_name, self)
            action.triggered.connect(lambda checked, l=lang_code: self.change_language(l))
            language_menu.addAction(action)

    def add_menu_actions(self, menu, actions):
        for text, shortcut, tooltip, handler in actions:
            action = QAction(text, self)
            if shortcut:
                action.setShortcut(shortcut)
            if tooltip:
                action.setStatusTip(tooltip)
            action.triggered.connect(handler)
            menu.addAction(action)

    def toggle_theme(self):
        theme = self.theme_manager.toggle_theme()
        self.theme_manager.apply_theme(self)
        self.save_settings()
        self.statusBar().showMessage(f"Tema değiştirildi: {theme}")

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Çizgi Roman Dosyası Aç", 
            self.file_manager.current_folder,
            "Tüm Dosyalar (*);;Resim Dosyaları (*.jpg *.jpeg *.png *.bmp *.gif);;CBR/CBZ Dosyaları (*.cbr *.cbz)"
        )
        
        if file_name and os.path.exists(file_name):
            self.file_manager.current_folder = os.path.dirname(file_name)
            self.open_specific_file(file_name)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Klasör Seç",
            self.file_manager.current_folder
        )
        
        if folder:
            self.file_manager.current_folder = folder
            files = []
            for file in sorted(os.listdir(folder)):
                file_path = os.path.join(folder, file)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                        files.append(file_path)
            
            if files:
                self.pages = files
                self.current_page = 0
                self.show_page()
                self.statusBar().showMessage(f"Klasör açıldı: {folder}")
            else:
                QMessageBox.warning(self, "Uyarı", "Klasörde desteklenen resim dosyası bulunamadı.")

    def open_specific_file(self, file_path):
        """Belirli bir dosyayı açar"""
        self.image_manager.clear_cache()  # Önbelleği temizle
        temp_dir, pages = self.file_manager.open_file(file_path)
        if pages:
            self.pages = pages
            self.current_page = 0
            self.show_page()
            self.check_continue_button_visibility()
            
            # Son okunan tarihi güncelle
            for series_name, series in self.library.series.items():
                for book in series['books']:
                    if book['path'] == file_path:
                        book['last_read_date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.library.save_library()
                        break

    def show_page(self):
        """Sayfayı görüntüler"""
        if not self.pages or not (0 <= self.current_page < len(self.pages)):
            return

        try:
            result = self.image_manager.show_page(self.image_label, self.pages, self.current_page)
            if result:
                self.page_label.setText(result)
                # Son okunan sayfayı güncelle
                if self.pages and self.pages[0]:
                    self.library.update_last_read(self.pages[0], self.current_page)
        except Exception as e:
            print(f"Sayfa gösterim hatası: {e}")

    def zoom_in(self):
        message = self.image_manager.zoom_in()
        self.show_page()
        self.statusBar().showMessage(message)

    def zoom_out(self):
        message = self.image_manager.zoom_out()
        if message:
            self.show_page()
            self.statusBar().showMessage(message)

    def reset_zoom(self):
        message = self.image_manager.reset_zoom()
        self.show_page()
        self.statusBar().showMessage(message)

    def rotate_left(self):
        message = self.image_manager.rotate_left()
        self.show_page()
        self.statusBar().showMessage(message)

    def rotate_right(self):
        message = self.image_manager.rotate_right()
        self.show_page()
        self.statusBar().showMessage(message)

    def reset_rotation(self):
        message = self.image_manager.reset_rotation()
        self.show_page()
        self.statusBar().showMessage(message)

    def toggle_double_page(self):
        message = self.image_manager.toggle_double_page()
        self.show_page()
        self.statusBar().showMessage(message)

    def mouse_move_event(self, event):
        self.mouse_pos = event.pos()
        if self.image_manager.zoom_level > 1.0:
            label_size = self.image_label.size()
            pixmap_size = self.image_label.pixmap().size()
            self.image_manager.update_scroll_position(self.mouse_pos, label_size, pixmap_size)
            self.show_page()

    def resizeEvent(self, event):
        """Pencere boyutu değiştiğinde"""
        super().resizeEvent(event)
        self.show_page()
        if hasattr(self, 'overlay_widget') and hasattr(self, 'image_label'):
            self.overlay_widget.setGeometry(self.image_label.rect())

    def closeEvent(self, event):
        """Pencere kapatıldığında temizlik yapar"""
        self.image_manager.clear_cache()
        self.file_manager.cleanup_temp()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.prev_page()
        elif event.key() == Qt.Key_Right:
            self.next_page()
        elif event.key() == Qt.Key_O and event.modifiers() & Qt.ControlModifier:
            self.open_file()
        elif event.key() == Qt.Key_K and event.modifiers() & Qt.ControlModifier:
            self.open_folder()
        elif event.key() == Qt.Key_T and event.modifiers() & Qt.ControlModifier:
            self.toggle_theme()
        elif event.key() == Qt.Key_D and event.modifiers() & Qt.ControlModifier:
            self.toggle_double_page()
        elif event.key() == Qt.Key_P and event.modifiers() & Qt.ControlModifier:
            self.toggle_auto_play()
        elif event.key() == Qt.Key_Space:
            self.toggle_auto_play()
        elif event.key() == Qt.Key_Plus and event.modifiers() & Qt.ControlModifier:
            self.zoom_in()
        elif event.key() == Qt.Key_Minus and event.modifiers() & Qt.ControlModifier:
            self.zoom_out()
        elif event.key() == Qt.Key_0 and event.modifiers() & Qt.ControlModifier:
            self.reset_zoom()
        elif event.key() == Qt.Key_F and event.modifiers() & Qt.ControlModifier:
            self.add_favorite()
        elif event.key() == Qt.Key_F and event.modifiers() & Qt.ControlModifier | Qt.ShiftModifier:
            self.show_favorites()
        elif event.key() == Qt.Key_R and event.modifiers() & Qt.ControlModifier:
            self.rotate_left()
        elif event.key() == Qt.Key_R and event.modifiers() & Qt.ControlModifier | Qt.ShiftModifier:
            self.rotate_right()
        elif event.key() == Qt.Key_R and event.modifiers() & Qt.ControlModifier | Qt.AltModifier:
            self.reset_rotation()
        elif event.key() == Qt.Key_N and event.modifiers() & Qt.ControlModifier:
            self.add_note()
        elif event.key() == Qt.Key_N and event.modifiers() & Qt.ControlModifier | Qt.ShiftModifier:
            self.show_notes()
        elif event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self.toggle_auto_scroll()
        elif event.key() == Qt.Key_P and event.modifiers() & Qt.ControlModifier | Qt.ShiftModifier:
            self.toggle_preview()
        elif event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
        # Dil seçimi kısayolları
        elif event.key() == Qt.Key_T and event.modifiers() & Qt.ControlModifier | Qt.AltModifier:
            self.change_language("tr")
        elif event.key() == Qt.Key_E and event.modifiers() & Qt.ControlModifier | Qt.AltModifier:
            self.change_language("en")
        elif event.key() == Qt.Key_D and event.modifiers() & Qt.ControlModifier | Qt.AltModifier:
            self.change_language("de")
        elif event.key() == Qt.Key_F and event.modifiers() & Qt.ControlModifier | Qt.AltModifier:
            self.change_language("fr")
        elif event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier | Qt.AltModifier:
            self.change_language("es")
        super().keyPressEvent(event)

    def add_new_series(self):
        series_name, ok = QInputDialog.getText(self, "Yeni Seri", "Seri adını girin:")
        if ok and series_name:
            folder = QFileDialog.getExistingDirectory(self, "Seri Klasörünü Seç")
            if folder:
                self.library.add_series(series_name, folder)
                self.statusBar().showMessage(f"Yeni seri eklendi: {series_name}")

    def update_series_menu(self, menu):
        menu.clear()
        for series_name in self.library.series:
            series_action = QAction(series_name, self)
            series_action.triggered.connect(lambda checked, s=series_name: self.open_series(s))
            menu.addAction(series_action)

    def open_series(self, series_name):
        if series_name in self.library.series:
            series = self.library.series[series_name]
            if series['books']:
                self.open_specific_file(series['books'][0]['path'])
                self.current_page = series['books'][0]['last_page']
                self.show_page()

    def update_favorites_menu(self, menu):
        menu.clear()
        for series_name, series in self.library.series.items():
            for book in series['books']:
                if book.get('favorite', False):
                    action = QAction(f"{series_name} - {book['name']}", self)
                    action.triggered.connect(lambda checked, p=book['path']: self.open_specific_file(p))
                    menu.addAction(action)

    def toggle_favorite(self):
        if self.pages and self.pages[0]:
            for series in self.library.series.values():
                for book in series['books']:
                    if book['path'] == self.pages[0]:
                        book['favorite'] = not book.get('favorite', False)
                        self.library.save_library()
                        status = "favorilere eklendi" if book['favorite'] else "favorilerden çıkarıldı"
                        self.statusBar().showMessage(f"Sayfa {status}")
                        break

    def toggle_auto_play(self):
        self.auto_play = not self.auto_play
        if self.auto_play:
            self.auto_play_timer.start(self.auto_play_speed)
            self.statusBar().showMessage("Otomatik oynatma başladı")
        else:
            self.auto_play_timer.stop()
            self.statusBar().showMessage("Otomatik oynatma durduruldu")

    def set_auto_play_speed(self, speed):
        self.auto_play_speed = speed
        if self.auto_play:
            self.auto_play_timer.setInterval(speed)
        self.statusBar().showMessage(f"Oynatma hızı: {3000/speed}x")

    def auto_next_page(self):
        if self.auto_play:
            self.next_page()

    def load_favorites(self):
        favorites_file = "favorites.json"
        if os.path.exists(favorites_file):
            try:
                with open(favorites_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_favorites(self):
        self.file_manager.save_json(self.favorites, "favorites.json")

    def add_favorite(self):
        if not self.pages or self.current_page >= len(self.pages):
            return

        # Etiket al
        tags, ok = QInputDialog.getText(
            self, "Favori Ekle",
            "Etiketleri girin (virgülle ayırın):",
            ""
        )

        if not ok:
            return

        # Ekran görüntüsü al
        pixmap = self.image_label.grab()
        
        # Favoriler klasörünü oluştur
        favorites_dir = "favorites"
        if not os.path.exists(favorites_dir):
            os.makedirs(favorites_dir)

        # Benzersiz dosya adı oluştur
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"favorite_{timestamp}.png"
        filepath = os.path.join(favorites_dir, filename)

        # Görüntüyü kaydet
        pixmap.save(filepath)

        # Favori bilgilerini kaydet
        favorite_info = {
            "filepath": filepath,
            "source_file": self.pages[0] if self.pages else "",
            "page_number": self.current_page + 1,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": f"Sayfa {self.current_page + 1}",
            "tags": [tag.strip() for tag in tags.split(",") if tag.strip()]
        }

        self.favorites.append(favorite_info)
        self.save_favorites()
        self.statusBar().showMessage(f"Favori eklendi: Sayfa {self.current_page + 1}")

    def show_favorites(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Favoriler")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(dialog)

        # Etiket filtresi
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Etiket Filtresi:")
        filter_layout.addWidget(filter_label)
        
        filter_edit = QLineEdit()
        filter_edit.setPlaceholderText("Etiketleri virgülle ayırın")
        filter_layout.addWidget(filter_edit)
        
        layout.addLayout(filter_layout)

        # Favori listesi
        list_widget = QListWidget()
        for fav in self.favorites:
            item = QListWidgetItem()
            tags_text = ", ".join(fav['tags']) if fav['tags'] else "Etiket yok"
            item.setText(f"{fav['title']} - {fav['date']} ({tags_text})")
            item.setData(Qt.UserRole, fav)
            list_widget.addItem(item)
        layout.addWidget(list_widget)

        # Görüntü alanı
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)

        # Butonlar
        button_layout = QHBoxLayout()
        delete_button = QPushButton("❌ Sil")
        delete_button.clicked.connect(lambda: self.delete_favorite(list_widget, image_label))
        button_layout.addWidget(delete_button)

        edit_button = QPushButton("✏️ Düzenle")
        edit_button.clicked.connect(lambda: self.edit_favorite(list_widget))
        button_layout.addWidget(edit_button)

        go_to_button = QPushButton("📖 Git")
        go_to_button.clicked.connect(lambda: self.go_to_favorite(list_widget))
        button_layout.addWidget(go_to_button)

        layout.addLayout(button_layout)

        # Etiket filtresini uygula
        def apply_filter():
            filter_text = filter_edit.text().lower()
            filter_tags = [tag.strip() for tag in filter_text.split(",") if tag.strip()]
            
            list_widget.clear()
            for fav in self.favorites:
                if not filter_tags or any(tag in [t.lower() for t in fav['tags']] for tag in filter_tags):
                    item = QListWidgetItem()
                    tags_text = ", ".join(fav['tags']) if fav['tags'] else "Etiket yok"
                    item.setText(f"{fav['title']} - {fav['date']} ({tags_text})")
                    item.setData(Qt.UserRole, fav)
                    list_widget.addItem(item)

        filter_edit.textChanged.connect(apply_filter)

        # Seçim değiştiğinde görüntüyü güncelle
        list_widget.currentItemChanged.connect(
            lambda current, previous: self.update_favorite_preview(current, image_label)
        )

        dialog.exec_()

    def update_favorite_preview(self, item, image_label):
        if item:
            fav = item.data(Qt.UserRole)
            pixmap = QPixmap(fav['filepath'])
            if not pixmap.isNull():
                image_label.setPixmap(pixmap.scaled(
                    image_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))

    def delete_favorite(self, list_widget, image_label):
        current_item = list_widget.currentItem()
        if current_item:
            fav = current_item.data(Qt.UserRole)
            try:
                os.remove(fav['filepath'])
                self.favorites.remove(fav)
                self.save_favorites()
                list_widget.takeItem(list_widget.row(current_item))
                image_label.clear()
                self.statusBar().showMessage("Favori silindi")
            except Exception as e:
                QMessageBox.warning(self, "Hata", f"Favori silinirken hata oluştu: {str(e)}")

    def go_to_favorite(self, list_widget):
        current_item = list_widget.currentItem()
        if current_item:
            fav = current_item.data(Qt.UserRole)
            if os.path.exists(fav['source_file']):
                self.open_specific_file(fav['source_file'])
                self.current_page = fav['page_number'] - 1
                self.show_page()
                self.statusBar().showMessage(f"Favori sayfasına gidildi: Sayfa {fav['page_number']}")

    def toggle_auto_scroll(self):
        self.auto_scroll = not self.auto_scroll
        if self.auto_scroll:
            self.auto_scroll_timer.start(self.auto_scroll_speed)
            self.statusBar().showMessage("Otomatik kaydırma başladı")
        else:
            self.auto_scroll_timer.stop()
            self.statusBar().showMessage("Otomatik kaydırma durduruldu")

    def set_auto_scroll_speed(self, speed):
        self.auto_scroll_speed = speed
        if self.auto_scroll:
            self.auto_scroll_timer.setInterval(speed)
        self.statusBar().showMessage(f"Kaydırma hızı: {speed}ms")

    def set_scroll_direction(self, direction):
        self.scroll_direction = direction
        self.statusBar().showMessage(f"Kaydırma yönü: {'Yukarı' if direction == -1 else 'Aşağı'}")

    def auto_scroll_page(self):
        if self.auto_scroll and self.image_manager.zoom_level > 1.0:
            pixmap = self.image_label.pixmap()
            if pixmap and not pixmap.isNull():
                label_size = self.image_label.size()
                pixmap_size = pixmap.size()
                
                if self.scroll_direction == 1:  # Aşağı
                    if self.image_manager.scroll_pos.y() + label_size.height() < pixmap_size.height():
                        self.image_manager.scroll_pos.setY(self.image_manager.scroll_pos.y() + 1)
                    else:
                        self.next_page()
                        self.image_manager.scroll_pos.setY(0)
                else:  # Yukarı
                    if self.image_manager.scroll_pos.y() > 0:
                        self.image_manager.scroll_pos.setY(self.image_manager.scroll_pos.y() - 1)
                    else:
                        self.prev_page()
                        if self.pages and self.current_page < len(self.pages):
                            pixmap = QPixmap(self.pages[self.current_page])
                            if not pixmap.isNull():
                                self.image_manager.scroll_pos.setY(pixmap.height() - label_size.height())
                
                self.show_page()

    def set_animation_type(self, anim_type):
        self.animation_type = anim_type
        self.statusBar().showMessage(f"Animasyon türü: {anim_type}")

    def set_animation_direction(self, direction):
        self.animation_direction = direction
        self.statusBar().showMessage(f"Animasyon yönü: {direction}")

    def set_animation_speed(self, speed):
        self.animation_duration = speed
        self.statusBar().showMessage(f"Animasyon hızı: {speed}ms")

    def animate_page_transition(self, next_page_func):
        if self.animation_type == "slide":
            self.animate_slide(next_page_func)
        elif self.animation_type == "fade":
            self.animate_fade(next_page_func)
        elif self.animation_type == "zoom":
            self.animate_zoom(next_page_func)

    def animate_slide(self, next_page_func):
        current_pixmap = self.image_label.pixmap()
        if not current_pixmap:
            next_page_func()
            return

        # Yeni sayfayı yükle
        next_page_func()
        next_pixmap = self.image_label.pixmap()
        if not next_pixmap:
            return

        # Animasyon için geçici etiketler
        current_label = QLabel(self)
        current_label.setPixmap(current_pixmap)
        current_label.setGeometry(self.image_label.geometry())
        current_label.show()

        next_label = QLabel(self)
        next_label.setPixmap(next_pixmap)
        next_label.setGeometry(self.image_label.geometry())
        next_label.show()

        # Animasyon başlangıç ve bitiş pozisyonları
        start_pos = QPoint(0, 0)
        end_pos = QPoint(0, 0)
        
        if self.animation_direction == "right":
            start_pos = QPoint(0, 0)
            end_pos = QPoint(-self.image_label.width(), 0)
        elif self.animation_direction == "left":
            start_pos = QPoint(0, 0)
            end_pos = QPoint(self.image_label.width(), 0)
        elif self.animation_direction == "up":
            start_pos = QPoint(0, 0)
            end_pos = QPoint(0, self.image_label.height())
        elif self.animation_direction == "down":
            start_pos = QPoint(0, 0)
            end_pos = QPoint(0, -self.image_label.height())

        # Animasyon
        anim = QPropertyAnimation(current_label, b"pos")
        anim.setDuration(self.animation_duration)
        anim.setStartValue(start_pos)
        anim.setEndValue(end_pos)
        anim.start()

        # Animasyon bitince temizle
        anim.finished.connect(lambda: self.cleanup_animation(current_label, next_label))

    def animate_fade(self, next_page_func):
        current_pixmap = self.image_label.pixmap()
        if not current_pixmap:
            next_page_func()
            return

        # Yeni sayfayı yükle
        next_page_func()
        next_pixmap = self.image_label.pixmap()
        if not next_pixmap:
            return

        # Animasyon için geçici etiketler
        current_label = QLabel(self)
        current_label.setPixmap(current_pixmap)
        current_label.setGeometry(self.image_label.geometry())
        current_label.show()

        next_label = QLabel(self)
        next_label.setPixmap(next_pixmap)
        next_label.setGeometry(self.image_label.geometry())
        next_label.show()

        # Animasyon
        anim = QPropertyAnimation(current_label, b"windowOpacity")
        anim.setDuration(self.animation_duration)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.start()

        # Animasyon bitince temizle
        anim.finished.connect(lambda: self.cleanup_animation(current_label, next_label))

    def animate_zoom(self, next_page_func):
        current_pixmap = self.image_label.pixmap()
        if not current_pixmap:
            next_page_func()
            return

        # Yeni sayfayı yükle
        next_page_func()
        next_pixmap = self.image_label.pixmap()
        if not next_pixmap:
            return

        # Animasyon için geçici etiketler
        current_label = QLabel(self)
        current_label.setPixmap(current_pixmap)
        current_label.setGeometry(self.image_label.geometry())
        current_label.show()

        next_label = QLabel(self)
        next_label.setPixmap(next_pixmap)
        next_label.setGeometry(self.image_label.geometry())
        next_label.show()

        # Animasyon
        anim = QPropertyAnimation(current_label, b"geometry")
        anim.setDuration(self.animation_duration)
        anim.setStartValue(self.image_label.geometry())
        anim.setEndValue(QRect(
            self.image_label.x() + self.image_label.width()/4,
            self.image_label.y() + self.image_label.height()/4,
            self.image_label.width()/2,
            self.image_label.height()/2
        ))
        anim.start()

        # Animasyon bitince temizle
        anim.finished.connect(lambda: self.cleanup_animation(current_label, next_label))

    def cleanup_animation(self, current_label, next_label):
        current_label.deleteLater()
        next_label.deleteLater()
        self.show_page()

    def toggle_preview(self):
        self.preview_visible = not self.preview_visible
        if self.preview_visible:
            self.preview_zoom_level = 1.0  # Yakınlaştırmayı sıfırla
            self.preview_timer.start()
            self.statusBar().showMessage("Sayfa önizleme açık")
        else:
            self.preview_timer.stop()
            self.statusBar().showMessage("Sayfa önizleme kapalı")

    def set_preview_size(self, size):
        self.preview_size = size
        self.statusBar().showMessage(f"Önizleme boyutu: {size}px")

    def update_preview(self):
        if not self.preview_visible or not self.pages:
            return

        # Önizleme penceresi oluştur
        if not hasattr(self, 'preview_window'):
            self.preview_window = QDialog(self)
            self.preview_window.setWindowTitle("Sayfa Önizleme")
            self.preview_window.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
            self.preview_window.setStyleSheet("background-color: rgba(0, 0, 0, 0.8);")
            
            # Sürükleme için başlık çubuğu
            title_bar = QWidget()
            title_bar.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
            title_bar.setFixedHeight(20)
            title_bar.mousePressEvent = self.preview_mouse_press
            title_bar.mouseMoveEvent = self.preview_mouse_move
            title_bar.mouseReleaseEvent = self.preview_mouse_release
            
            layout = QVBoxLayout(self.preview_window)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(title_bar)
            
            # Önizleme etiketi
            preview_scroll = QScrollArea()
            preview_scroll.setWidgetResizable(True)
            preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            preview_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            preview_scroll.setStyleSheet("QScrollBar {background: rgba(0, 0, 0, 0.3);} QScrollBar:handle {background: rgba(255, 255, 255, 0.3);}")
            
            self.preview_label = QLabel()
            self.preview_label.setAlignment(Qt.AlignCenter)
            self.preview_label.setMouseTracking(True)
            self.preview_label.mousePressEvent = self.preview_clicked
            self.preview_label.wheelEvent = self.preview_wheel
            preview_scroll.setWidget(self.preview_label)
            layout.addWidget(preview_scroll)
            
            # Sayfa numarası ve yakınlaştırma bilgisi
            info_layout = QHBoxLayout()
            
            self.preview_page_label = QLabel()
            self.preview_page_label.setAlignment(Qt.AlignLeft)
            self.preview_page_label.setStyleSheet("color: white;")
            info_layout.addWidget(self.preview_page_label)
            
            self.preview_zoom_label = QLabel()
            self.preview_zoom_label.setAlignment(Qt.AlignRight)
            self.preview_zoom_label.setStyleSheet("color: white;")
            info_layout.addWidget(self.preview_zoom_label)
            
            layout.addLayout(info_layout)
            
            # Navigasyon butonları
            nav_layout = QHBoxLayout()
            
            prev_button = QPushButton("◀")
            prev_button.setStyleSheet("color: white; background: transparent; border: none;")
            prev_button.clicked.connect(self.prev_page)
            nav_layout.addWidget(prev_button)
            
            next_button = QPushButton("▶")
            next_button.setStyleSheet("color: white; background: transparent; border: none;")
            next_button.clicked.connect(self.next_page)
            nav_layout.addWidget(next_button)
            
            layout.addLayout(nav_layout)
            
            self.preview_window.setLayout(layout)

            # Sürükleme için değişkenler
            self.preview_dragging = False
            self.preview_drag_position = QPoint()

        # Önizleme penceresini konumlandır
        if not self.preview_dragging:
            screen_geometry = QApplication.desktop().screenGeometry()
            preview_x = screen_geometry.width() - self.preview_size - 20
            preview_y = 20
            self.preview_window.setGeometry(preview_x, preview_y, self.preview_size, self.preview_size + 90)

        # Önizleme görüntüsünü yükle
        if 0 <= self.current_page < len(self.pages):
            pixmap = QPixmap(self.pages[self.current_page])
            if not pixmap.isNull():
                scaled_size = QSize(
                    int(self.preview_size * self.preview_zoom_level),
                    int(self.preview_size * self.preview_zoom_level)
                )
                scaled = pixmap.scaled(
                    scaled_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled)
                self.preview_page_label.setText(f"Sayfa {self.current_page + 1}/{len(self.pages)}")
                self.preview_zoom_label.setText(f"{int(self.preview_zoom_level * 100)}%")
                self.preview_window.show()
            else:
                self.preview_window.hide()
        else:
            self.preview_window.hide()

    def preview_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.preview_dragging = True
            self.preview_drag_position = event.globalPos() - self.preview_window.frameGeometry().topLeft()
            event.accept()

    def preview_mouse_move(self, event):
        if self.preview_dragging and event.buttons() & Qt.LeftButton:
            self.preview_window.move(event.globalPos() - self.preview_drag_position)
            event.accept()

    def preview_mouse_release(self, event):
        if event.button() == Qt.LeftButton:
            self.preview_dragging = False
            event.accept()

    def preview_clicked(self, event):
        if event.button() == Qt.LeftButton:
            # Tıklanan konuma göre sayfa geçişi
            label_width = self.preview_label.width()
            click_x = event.x()
            
            if click_x < label_width / 3:
                self.prev_page()
            elif click_x > label_width * 2 / 3:
                self.next_page()
            else:
                # Orta kısma tıklandığında önizleme penceresini kapat
                self.toggle_preview()

    def preview_wheel(self, event):
        if event.angleDelta().y() > 0:
            # Yakınlaştır
            if self.preview_zoom_level < self.preview_max_zoom:
                self.preview_zoom_level += self.preview_zoom_step
        else:
            # Uzaklaştır
            if self.preview_zoom_level > self.preview_min_zoom:
                self.preview_zoom_level -= self.preview_zoom_step
        
        # Yakınlaştırma seviyesini sınırla
        self.preview_zoom_level = max(self.preview_min_zoom, min(self.preview_max_zoom, self.preview_zoom_level))
        
        # Görüntüyü güncelle
        self.update_preview()

    def load_translations(self):
        translations = {}
        for lang_code in self.languages.keys():
            try:
                with open(f"translations/{lang_code}.json", 'r', encoding='utf-8') as f:
                    translations[lang_code] = json.load(f)
            except:
                translations[lang_code] = {}
        return translations

    def change_language(self, lang_code):
        self.current_language = lang_code
        self.translator.load(f"translations/{lang_code}")
        QApplication.installTranslator(self.translator)
        self.retranslate_ui()
        self.statusBar().showMessage(self.translate("language_changed"))
        self.save_settings()

    def retranslate_ui(self):
        # Menü çevirileri
        menubar = self.menuBar()
        if menubar.actions():
            try:
                menubar.actions()[0].setText(self.translate("file"))
                menubar.actions()[1].setText(self.translate("library"))
                menubar.actions()[2].setText(self.translate("view"))
                menubar.actions()[3].setText(self.translate("settings"))

                # Alt menü çevirileri
                file_menu = menubar.actions()[0].menu()
                if file_menu and file_menu.actions():
                    file_menu.actions()[0].setText(self.translate("open_file"))
                    file_menu.actions()[1].setText(self.translate("open_folder"))

                library_menu = menubar.actions()[1].menu()
                if library_menu and library_menu.actions():
                    library_menu.actions()[0].setText(self.translate("add_series"))
                    if len(library_menu.actions()) > 1 and library_menu.actions()[1].menu():
                        library_menu.actions()[1].menu().actions()[0].setText(self.translate("add_favorite"))
                        library_menu.actions()[1].menu().actions()[1].setText(self.translate("show_favorites"))
                    if len(library_menu.actions()) > 2 and library_menu.actions()[2].menu():
                        library_menu.actions()[2].menu().actions()[0].setText(self.translate("add_note"))
                        library_menu.actions()[2].menu().actions()[1].setText(self.translate("show_notes"))

                view_menu = menubar.actions()[2].menu()
                if view_menu and view_menu.actions():
                    actions = view_menu.actions()
                    if len(actions) > 0:
                        actions[0].setText(self.translate("toggle_theme"))
                    if len(actions) > 1:
                        actions[1].setText(self.translate("double_page"))
                    if len(actions) > 2:
                        actions[2].setText(self.translate("auto_play"))

                settings_menu = menubar.actions()[3].menu()
                if settings_menu and settings_menu.actions():
                    settings_menu.actions()[0].setText(self.translate("language"))

            except Exception as e:
                print(f"Menü çevirisi hatası: {e}")

        # Buton çevirileri
        if hasattr(self, 'prev_button'):
            self.prev_button.setText(self.translate("prev_page"))
        if hasattr(self, 'next_button'):
            self.next_button.setText(self.translate("next_page"))
        if hasattr(self, 'page_label'):
            self.page_label.setText(self.translate("page"))

    def translate(self, key):
        if key in self.translations[self.current_language]:
            return self.translations[self.current_language][key]
        return key

    def load_settings(self):
        settings = self.file_manager.load_json("settings.json")
        if settings:
            self.theme_manager.current_theme = settings.get("theme", "dark")
            self.theme_manager.apply_theme(self)

    def save_settings(self):
        settings = {
            "theme": self.theme_manager.current_theme,
            "language": self.current_language
        }
        self.file_manager.save_json(settings, "settings.json")

    def add_note(self):
        if not self.pages or self.current_page >= len(self.pages):
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Not Ekle")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Not başlığı
        title_label = QLabel("Başlık:")
        title_input = QLineEdit()
        layout.addWidget(title_label)
        layout.addWidget(title_input)
        
        # Not içeriği
        content_label = QLabel("Not:")
        content_input = QTextEdit()
        layout.addWidget(content_label)
        layout.addWidget(content_input)
        
        # Butonlar
        button_layout = QHBoxLayout()
        save_button = QPushButton("Kaydet")
        cancel_button = QPushButton("İptal")
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        def save_note():
            title = title_input.text()
            content = content_input.toPlainText()
            
            if title and content:
                note = {
                    "title": title,
                    "content": content,
                    "source_file": self.pages[0] if self.pages else "",
                    "page_number": self.current_page + 1,
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                if "notes" not in self.notes:
                    self.notes["notes"] = []
                
                self.notes["notes"].append(note)
                self.file_manager.save_json(self.notes, "notes.json")
                self.statusBar().showMessage(f"Not eklendi: {title}")
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "Uyarı", "Başlık ve not içeriği boş olamaz!")
        
        save_button.clicked.connect(save_note)
        cancel_button.clicked.connect(dialog.reject)
        
        dialog.exec_()

    def show_notes(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Notlar")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # Not listesi
        list_widget = QListWidget()
        if "notes" in self.notes:
            for note in self.notes["notes"]:
                item = QListWidgetItem()
                item.setText(f"{note['title']} - Sayfa {note['page_number']} ({note['date']})")
                item.setData(Qt.UserRole, note)
                list_widget.addItem(item)
        layout.addWidget(list_widget)
        
        # Not içeriği
        content_label = QLabel("Not İçeriği:")
        content_text = QTextEdit()
        content_text.setReadOnly(True)
        layout.addWidget(content_label)
        layout.addWidget(content_text)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        delete_button = QPushButton("❌ Sil")
        edit_button = QPushButton("✏️ Düzenle")
        go_to_button = QPushButton("📖 Git")
        
        button_layout.addWidget(delete_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(go_to_button)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        def show_note_content(item):
            if item:
                note = item.data(Qt.UserRole)
                content_text.setText(note["content"])
        
        def delete_note():
            current_item = list_widget.currentItem()
            if current_item:
                note = current_item.data(Qt.UserRole)
                if "notes" in self.notes:
                    self.notes["notes"].remove(note)
                    self.file_manager.save_json(self.notes, "notes.json")
                    list_widget.takeItem(list_widget.row(current_item))
                    content_text.clear()
                    self.statusBar().showMessage("Not silindi")
        
        def edit_note():
            current_item = list_widget.currentItem()
            if current_item:
                note = current_item.data(Qt.UserRole)
                
                edit_dialog = QDialog(dialog)
                edit_dialog.setWindowTitle("Not Düzenle")
                edit_dialog.setMinimumWidth(400)
                
                edit_layout = QVBoxLayout()
                
                title_label = QLabel("Başlık:")
                title_input = QLineEdit(note["title"])
                edit_layout.addWidget(title_label)
                edit_layout.addWidget(title_input)
                
                content_label = QLabel("Not:")
                content_input = QTextEdit()
                content_input.setText(note["content"])
                edit_layout.addWidget(content_label)
                edit_layout.addWidget(content_input)
                
                button_layout = QHBoxLayout()
                save_button = QPushButton("Kaydet")
                cancel_button = QPushButton("İptal")
                button_layout.addWidget(save_button)
                button_layout.addWidget(cancel_button)
                edit_layout.addLayout(button_layout)
                
                edit_dialog.setLayout(edit_layout)
                
                def save_edited_note():
                    note["title"] = title_input.text()
                    note["content"] = content_input.toPlainText()
                    note["date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    self.file_manager.save_json(self.notes, "notes.json")
                    current_item.setText(f"{note['title']} - Sayfa {note['page_number']} ({note['date']})")
                    show_note_content(current_item)
                    self.statusBar().showMessage("Not düzenlendi")
                    edit_dialog.accept()
                
                save_button.clicked.connect(save_edited_note)
                cancel_button.clicked.connect(edit_dialog.reject)
                
                edit_dialog.exec_()
        
        def go_to_note():
            current_item = list_widget.currentItem()
            if current_item:
                note = current_item.data(Qt.UserRole)
                if os.path.exists(note["source_file"]):
                    self.open_specific_file(note["source_file"])
                    self.current_page = note["page_number"] - 1
                    self.show_page()
                    self.statusBar().showMessage(f"Not sayfasına gidildi: Sayfa {note['page_number']}")
                    dialog.accept()
        
        list_widget.currentItemChanged.connect(show_note_content)
        delete_button.clicked.connect(delete_note)
        edit_button.clicked.connect(edit_note)
        go_to_button.clicked.connect(go_to_note)
        
        dialog.exec_()

    def prev_page(self):
        if self.pages:
            if self.current_page > 0:
                self.current_page -= 2 if self.image_manager.double_page_mode else 1
                self.current_page = max(0, self.current_page)
                self.animate_page_transition(self.show_page)
            else:
                self.statusBar().showMessage("İlk sayfadasınız")

    def next_page(self):
        if self.pages:
            if self.current_page < len(self.pages) - 1:
                step = 2 if self.image_manager.double_page_mode else 1
                if self.current_page + step < len(self.pages):
                    self.current_page += step
                    self.animate_page_transition(self.show_page)
                else:
                    next_file = self.file_manager.get_next_file_in_directory(self.pages[0])
                    if next_file:
                        self.open_specific_file(next_file)
                    else:
                        self.statusBar().showMessage("Son sayfadasınız")
            else:
                next_file = self.file_manager.get_next_file_in_directory(self.pages[0])
                if next_file:
                    self.open_specific_file(next_file)
                else:
                    self.statusBar().showMessage("Son sayfadasınız")

    def rotate_image(self, degrees):
        """Görüntüyü belirtilen derece kadar döndürür"""
        if self.current_image:
            self.rotation = (self.rotation + degrees) % 360
            self.show_page()
            self.statusBar().showMessage(f"Döndürme: {self.rotation}°")

    def mirror_image(self):
        """Görüntüyü yatay olarak aynalar"""
        if self.current_image:
            self.mirrored = not self.mirrored
            self.show_page()
            self.statusBar().showMessage("Ayna görüntüsü " + ("açık" if self.mirrored else "kapalı"))

    def show_library(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Kütüphane")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Arama kutusu
        search_layout = QHBoxLayout()
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("Seri veya kitap ara...")
        search_layout.addWidget(search_edit)
        layout.addLayout(search_layout)
        
        # Seri ve kitap listesi
        splitter = QSplitter(Qt.Horizontal)
        
        # Seri listesi
        series_list = QListWidget()
        series_list.setMinimumWidth(200)
        for series_name in self.library.series:
            series_list.addItem(series_name)
        splitter.addWidget(series_list)
        
        # Kitap listesi
        book_list = QListWidget()
        book_list.setMinimumWidth(400)
        splitter.addWidget(book_list)
        
        layout.addWidget(splitter)
        
        # Seçili kitabın bilgileri
        info_layout = QVBoxLayout()
        info_label = QLabel()
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        layout.addLayout(info_layout)
        
        # Butonlar
        button_layout = QHBoxLayout()
        open_button = QPushButton("Aç")
        open_button.clicked.connect(lambda: self.open_selected_book(book_list, dialog))
        button_layout.addWidget(open_button)
        
        add_series_button = QPushButton("Yeni Seri Ekle")
        add_series_button.clicked.connect(lambda: self.add_new_series(dialog))
        button_layout.addWidget(add_series_button)
        
        refresh_button = QPushButton("Yenile")
        refresh_button.clicked.connect(lambda: self.refresh_library(series_list, book_list))
        button_layout.addWidget(refresh_button)
        
        layout.addLayout(button_layout)
        
        # Seri seçildiğinde kitapları güncelle
        def update_books():
            current_series = series_list.currentItem()
            if current_series:
                series_name = current_series.text()
                book_list.clear()
                if series_name in self.library.series:
                    for book in self.library.series[series_name]['books']:
                        item = QListWidgetItem(book['name'])
                        item.setData(Qt.UserRole, book['path'])
                        book_list.addItem(item)
        
        series_list.currentItemChanged.connect(update_books)
        
        # Kitap seçildiğinde bilgileri güncelle
        def update_info():
            current_book = book_list.currentItem()
            if current_book:
                book_path = current_book.data(Qt.UserRole)
                for series in self.library.series.values():
                    for book in series['books']:
                        if book['path'] == book_path:
                            info = f"""
                            <b>Kitap:</b> {book['name']}<br>
                            <b>Son Okunan Sayfa:</b> {book['last_page'] + 1}<br>
                            <b>Favori:</b> {'Evet' if book.get('favorite', False) else 'Hayır'}<br>
                            <b>Konum:</b> {book_path}
                            """
                            info_label.setText(info)
                            break
        
        book_list.currentItemChanged.connect(update_info)
        
        # Arama fonksiyonu
        def search_items(text):
            text = text.lower()
            series_list.clear()
            for series_name in self.library.series:
                if text in series_name.lower():
                    series_list.addItem(series_name)
                else:
                    # Seri içindeki kitapları kontrol et
                    for book in self.library.series[series_name]['books']:
                        if text in book['name'].lower():
                            series_list.addItem(series_name)
                            break
        
        search_edit.textChanged.connect(search_items)
        
        dialog.exec_()
    
    def open_selected_book(self, book_list, dialog):
        current_item = book_list.currentItem()
        if current_item:
            book_path = current_item.data(Qt.UserRole)
            self.open_specific_file(book_path)
            dialog.accept()
    
    def refresh_library(self, series_list, book_list):
        for series_name in self.library.series:
            self.library.update_series_books(series_name)
        current_series = series_list.currentItem()
        if current_series:
            series_name = current_series.text()
            book_list.clear()
            if series_name in self.library.series:
                for book in self.library.series[series_name]['books']:
                    item = QListWidgetItem(book['name'])
                    item.setData(Qt.UserRole, book['path'])
                    book_list.addItem(item)

    def continue_last_reading(self):
        """Son okunan çizgi romanı açar"""
        last_file, last_page = self.library.get_last_read()
        
        if last_file and os.path.exists(last_file):
            self.open_specific_file(last_file)
            self.current_page = last_page
            self.show_page()
            self.overlay_widget.hide()
            self.statusBar().showMessage(f"Son okunan sayfadan devam ediliyor: Sayfa {last_page + 1}")
        else:
            self.statusBar().showMessage("Daha önce okunan bir çizgi roman bulunamadı")

    def check_continue_button_visibility(self):
        """Devam et butonunun görünürlüğünü kontrol eder"""
        if self.pages:
            # Bir dosya açıksa butonu gizle
            self.overlay_widget.hide()
        else:
            # Dosya açık değilse butonu göster
            self.overlay_widget.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ComicReader()
    window.show()
    sys.exit(app.exec_())
