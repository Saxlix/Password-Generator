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
    handlers=[logging.FileHandler("app.log", encoding="utf-8"), logging.StreamHandler(sys.stdout)]
)

class PhraseDatabase:
    def __init__(self, db_path='passwords.db'):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute('''CREATE TABLE IF NOT EXISTS generated_phrases (id INTEGER PRIMARY KEY AUTOINCREMENT, phrase TEXT NOT NULL, word_count INTEGER NOT NULL, separator TEXT NOT NULL, strength TEXT NOT NULL, date TEXT NOT NULL, image_path TEXT)''')
        conn.commit()
        conn.close()
        logging.info("DB init success.")