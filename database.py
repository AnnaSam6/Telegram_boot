"""
Модуль для работы с SQLite базой данных.
Содержит инициализацию БД и управление подключениями.
"""

import sqlite3
import logging
from typing import Generator
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных SQLite."""
    
    def __init__(self, db_path: str = 'english_vocabulary.db'):
        """
        Инициализация подключения к БД.
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Контекстный менеджер для получения соединения с БД.
        
        Yields:
            sqlite3.Connection: Соединение с базой данных
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка базы данных: {e}")
            raise
        finally:
            conn.close()
    
    def init_db(self) -> None:
        """
        Инициализация базы данных и создание таблиц.
        
        Создает 4 таблицы:
        1. users - информация о пользователях
        2. standard_words - общий словарь для всех пользователей
        3. user_words - персональные слова пользователей
        4. learning_statistics - статистика изучения
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица стандартных слов (общий словарь)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS standard_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    english TEXT NOT NULL UNIQUE,
                    russian TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    difficulty_level INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица пользовательских слов (персональные)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    english TEXT NOT NULL,
                    russian TEXT NOT NULL,
                    topic TEXT,
                    mastered BOOLEAN DEFAULT FALSE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    UNIQUE(user_id, english)
                )
            ''')
            
            # Таблица статистики обучения
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    word_id INTEGER NOT NULL,
                    word_type TEXT NOT NULL CHECK(word_type IN ('standard', 'user')),
                    correct_attempts INTEGER DEFAULT 0,
                    total_attempts INTEGER DEFAULT 0,
                    last_practiced TIMESTAMP,
                    next_review TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            logger.info("Таблицы базы данных созданы успешно")
            
            # Заполняем стандартные слова, если таблица пуста
            cursor.execute("SELECT COUNT(*) FROM standard_words")
            if cursor.fetchone()[0] == 0:
                self._populate_standard_words(cursor)
                logger.info("Стандартные слова добавлены в базу данных")
    
    def _populate_standard_words(self, cursor: sqlite3.Cursor) -> None:
        """
        Заполнение таблицы стандартными словами для изучения.
        
        Args:
            cursor: Курсор базы данных
        """
        words = [
            # Цвета (colors)
            ("red", "красный", "colors", 1),
            ("blue", "синий", "colors", 1),
            ("green", "зеленый", "colors", 1),
            ("yellow", "желтый", "colors", 1),
            ("black", "черный", "colors", 1),
            
            # Местоимения (pronouns)
            ("I", "я", "pronouns", 1),
            ("you", "ты/вы", "pronouns", 1),
            ("he", "он", "pronouns", 1),
            ("she", "она", "pronouns", 1),
            ("it", "оно", "pronouns", 1),
            
            # Животные (animals)
            ("cat", "кот", "animals", 2),
            ("dog", "собака", "animals", 2),
            ("bird", "птица", "animals", 2),
            ("fish", "рыба", "animals", 2),
            
            # Еда (food)
            ("apple", "яблоко", "food", 2),
            ("bread", "хлеб", "food", 2),
            ("water", "вода", "food", 2),
            ("milk", "молоко", "food", 2),
            
            # Семья (family)
            ("mother", "мать", "family", 3),
            ("father", "отец", "family", 3),
            ("brother", "брат", "family", 3),
            ("sister", "сестра", "family", 3),
        ]
        
        cursor.executemany(
            '''INSERT INTO standard_words (english, russian, topic, difficulty_level) 
               VALUES (?, ?, ?, ?)''',
            words
        )
