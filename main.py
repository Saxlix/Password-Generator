import sys
import random
import sqlite3
import os
import logging
from io import BytesIO
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont, QImage
from PyQt5.uic import loadUi
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)


class PhraseDatabase:
    def __init__(self, db_path='passwords.db'):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS generated_phrases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phrase TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    separator TEXT NOT NULL,
                    strength TEXT NOT NULL,
                    date TEXT NOT NULL,
                    image_path TEXT
                )
            ''')
            conn.commit()
            logging.info("DB init success.")
        except sqlite3.Error as e:
            logging.error(f"DB init error: {e}")
        finally:
            if conn:
                conn.close()

    def save_phrase(self, phrase, word_count, separator, strength, image_path):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                INSERT INTO generated_phrases (phrase, word_count, separator, strength, date, image_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (phrase, word_count, separator, strength, current_date, image_path))
            conn.commit()
            logging.info(f"Saved row ID: {cursor.lastrowid}")
        except sqlite3.Error as e:
            logging.error(f"Save error: {e}")
        finally:
            if conn:
                conn.close()

    def get_all_phrases(self):
        conn = None
        data = []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT date, phrase, strength FROM generated_phrases ORDER BY id DESC")
            data = cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Read error: {e}")
        finally:
            if conn:
                conn.close()
        return data


class DicewareGenerator:
    def __init__(self, dictionary_path="diceware_words.txt"):
        self.dictionary_path = dictionary_path
        self.words = []
        self.separators = ["-", "_", ".", "$", "*", "!", "#", "~"]
        self._load_dictionary()

    def _load_dictionary(self):
        if os.path.exists(self.dictionary_path):
            try:
                with open(self.dictionary_path, "r", encoding="utf-8") as file:
                    self.words = [line.strip() for line in file if line.strip()]
                if not self.words:
                    self._set_fallback_words("Dictionary empty.")
                else:
                    logging.info(f"Loaded words: {len(self.words)}")
            except Exception as e:
                self._set_fallback_words(f"Read error: {e}")
        else:
            self._set_fallback_words("File not found.")

    def _set_fallback_words(self, message):
        logging.warning(message)
        self.words = ["дом", "гора", "солнце", "кошка", "поезд", "стол", "студент", "микрофон", "река"]

    def generate(self, word_count, min_len, max_len):
        filtered = [w for w in self.words if min_len <= len(w) <= max_len]
        if not filtered:
            logging.warning("No words found matching criteria.")
            return None, None
        selected_words = [random.choice(filtered) for _ in range(word_count)]
        random_sep = random.choice(self.separators)
        phrase = random_sep.join(selected_words)
        return phrase, random_sep


class AdvancedDicewareApp(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._data_layer()
        self._logic()
        self._bind_signals()
        self._apply_qss()

    def _setup_ui(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(base_dir, "window.ui")
        loadUi(ui_path, self)

    def _data_layer(self):
        self.db = PhraseDatabase()

    def _logic(self):
        self.generator = DicewareGenerator()

    def _bind_signals(self):
        self.spin_min_len.valueChanged.connect(self._update_length_constraints)
        self.btn_generate.clicked.connect(self._on_generate_clicked)
        self.btn_copy.clicked.connect(self._on_copy_clicked)
        self.btn_export.clicked.connect(self._on_export_clicked)

    def _apply_qss(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: "Segoe UI", Arial;
                font-size: 14px;
                color: #2d3436;
            }
            QLabel {
                font-weight: 600;
            }
            QSpinBox {
                background-color: #ffffff;
                border: 1px solid #b2bec3;
                border-radius: 6px;
                padding: 6px;
                min-width: 90px;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 2px solid #b2bec3;
                border-radius: 8px;
                padding: 8px;
                color: #2d3436;
            }
            QLineEdit:focus {
                border: 2px solid #0984e3;
            }
            QPushButton {
                background-color: #0984e3;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0284c7;
            }
            QPushButton#btn_generate {
                background-color: #10b981;
                font-size: 15px;
            }
            QPushButton#btn_generate:hover {
                background-color: #059669;
            }
            QLabel#lbl_image_preview {
                border: 2px dashed #b2bec3;
                background-color: #ffffff;
                color: #636e72;
                border-radius: 8px;
                font-weight: normal;
            }
        """)

    def _update_length_constraints(self):
        if self.spin_min_len.value() > self.spin_max_len.value():
            self.spin_max_len.setValue(self.spin_min_len.value())

    def _evaluate_strength(self, word_count):
        if word_count <= 4:
            return "Слабый пароль. Рекомендуется увеличить количество слов.", "color: #e67e22; font-weight: bold;"
        elif word_count <= 6:
            return "Хороший и надежный пароль", "color: #27ae60; font-weight: bold;"
        elif word_count <= 8:
            return "Отличная защита (высокая стойкость)", "color: #2980b9; font-weight: bold;"
        else:
            return "Максимальный уровень стойкости", "color: #8e44ad; font-weight: bold;"

    def _on_generate_clicked(self):
        word_count = self.spin_word_count.value()
        min_len = self.spin_min_len.value()
        max_len = self.spin_max_len.value()

        if min_len > max_len:
            QMessageBox.warning(self, "Ошибка валидации",
                                "Минимальная длина слова не может превышать максимальную.")
            return

        phrase, separator = self.generator.generate(word_count, min_len, max_len)

        if not phrase:
            QMessageBox.warning(self, "Внимание",
                                f"Не удалось найти слова длиной от {min_len} до {max_len} букв.\n"
                                "Пожалуйста, измените настройки диапазона.")
            return

        self.txt_result.setText(phrase)

        status_text, status_style = self._evaluate_strength(word_count)
        self.lbl_strength.setText(f"Надежность пароля: {status_text}")
        self.lbl_strength.setStyleSheet(status_style)

        img_path = self._create_password_image(phrase)

        try:
            pil_img = Image.open(img_path)
            pil_img = pil_img.resize((600, 130), Image.Resampling.LANCZOS)

            byte_array = BytesIO()
            pil_img.save(byte_array, format='PNG')
            qt_image = QImage.fromData(byte_array.getvalue())
            pixmap = QPixmap.fromImage(qt_image)

            self.lbl_image_preview.setPixmap(pixmap)
            self.lbl_image_preview.setScaledContents(True)
        except Exception as e:
            logging.error(f"Image scaling error: {e}")

        self.db.save_phrase(phrase, word_count, separator, status_text, img_path)

    def _create_password_image(self, text):
        img = Image.new('RGB', (800, 200), color='#ffffff')
        canvas = ImageDraw.Draw(img)

        try:
            font_title = ImageFont.truetype("arial.ttf", 24)
            font_password = ImageFont.truetype("arial.ttf", 28)
        except IOError:
            try:
                font_title = ImageFont.load_default(size=24)
                font_password = ImageFont.load_default(size=28)
            except TypeError:
                font_title = ImageFont.load_default()
                font_password = ImageFont.load_default()

        canvas.text((40, 40), "Ваш сгенерированный пароль:", fill='#7f8c8d', font=font_title)
        canvas.text((40, 100), text, fill='#2c3e50', font=font_password)

        filename = "password_card.png"
        img.save(filename)
        return filename

    def _on_copy_clicked(self):
        phrase = self.txt_result.text()
        if phrase:
            clipboard = QApplication.clipboard()
            clipboard.setText(phrase)

            self.btn_copy.setText("Скопировано")
            self.btn_copy.setEnabled(False)
            QTimer.singleShot(1500, lambda: [self.btn_copy.setText("Копировать"), self.btn_copy.setEnabled(True)])
            logging.info("Copied to clipboard.")
        else:
            QMessageBox.warning(self, "Внимание", "Сначала сгенерируйте фразу.")