# main.py - ДОБАВЬТЕ ЭТО В НАЧАЛЕ
import psycopg2
import os

# Подключение к БД
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'english_bot_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'password')
    )

# Создание таблиц
def init_database():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Таблица 1: Пользователи
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(100),
            first_name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица 2: Базовые слова (для всех)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS base_words (
            id SERIAL PRIMARY KEY,
            russian VARCHAR(100) NOT NULL,
            english VARCHAR(100) NOT NULL
        )
    """)
    
    # Таблица 3: Персональные слова пользователей
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_words (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            russian VARCHAR(100) NOT NULL,
            english VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица 4: Статистика (чтобы было 4 таблицы!)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            correct_answers INTEGER DEFAULT 0,
            wrong_answers INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()

# Инициализируем БД при запуске
init_database()

# ДОБАВИТЬ:
from database import Database

db = Database()

# В обработчике start:
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Сохраняем пользователя в БД
    db.add_user(user.id, user.username, user.first_name)
    # ... остальной код

# В обработчике add_word:
async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Получаем данные из сообщения
    text = update.message.text
    parts = text.split('-')
    
    if len(parts) == 2:
        russian, english = parts[0].strip(), parts[1].strip()
        # Сохраняем в БД
        success = db.add_user_word(user_id, russian, english)
        if success:
            await update.message.reply_text(f"Слово '{russian}' добавлено!")
        else:
            await update.message.reply_text("Ошибка при добавлении слова")
