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