import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.connection = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        self.create_tables()
    
    def create_tables(self):
        with self.connection.cursor() as cursor:
            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(100),
                    first_name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица базовых слов (для всех)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS base_words (
                    id SERIAL PRIMARY KEY,
                    russian VARCHAR(100) NOT NULL,
                    english VARCHAR(100) NOT NULL,
                    category VARCHAR(50)
                )
            """)
            
            # Таблица пользовательских слов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_words (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    russian VARCHAR(100) NOT NULL,
                    english VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица статистики (3+ таблицы!)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_stats (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    word_id INTEGER,
                    correct_answers INTEGER DEFAULT 0,
                    wrong_answers INTEGER DEFAULT 0
                )
            """)
            
            self.connection.commit()
    
    def add_user(self, telegram_id, username, first_name):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (telegram_id, username, first_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (telegram_id) DO NOTHING
            """, (telegram_id, username, first_name))
            self.connection.commit()
    
    def get_user_words(self, telegram_id):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT uw.id, uw.russian, uw.english 
                FROM user_words uw
                JOIN users u ON uw.user_id = u.id
                WHERE u.telegram_id = %s
            """, (telegram_id,))
            return cursor.fetchall()
    
    def add_user_word(self, telegram_id, russian, english):
        with self.connection.cursor() as cursor:
            # Получаем user_id
            cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
            user = cursor.fetchone()
            
            if user:
                cursor.execute("""
                    INSERT INTO user_words (user_id, russian, english)
                    VALUES (%s, %s, %s)
                """, (user[0], russian, english))
                self.connection.commit()
                return True
            return False
    
    def delete_user_word(self, telegram_id, word_id):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM user_words uw
                USING users u
                WHERE uw.id = %s 
                AND uw.user_id = u.id 
                AND u.telegram_id = %s
            """, (word_id, telegram_id))
            self.connection.commit()
            return cursor.rowcount > 0
