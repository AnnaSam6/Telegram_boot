import json
import logging
import random
import os
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# Загружаем настройки
load_dotenv()

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключение к БД
def get_db():
    return psycopg2.connect(
        host="localhost",
        database="english_bot_db",
        user="postgres",
        password="postgres"  # твой пароль от PostgreSQL
    )

# Создаем таблицы при запуске
def create_tables():
    conn = get_db()
    cur = conn.cursor()
    
    # 1. Таблица пользователей
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE,
            name VARCHAR(100)
        )
    """)
    
    # 2. Таблица слов (общая для всех)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id SERIAL PRIMARY KEY,
            russian VARCHAR(100),
            english VARCHAR(100)
        )
    """)
    
    # 3. Таблица моих слов (каждого пользователя)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS my_words (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            russian VARCHAR(100),
            english VARCHAR(100),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Добавляем 10 начальных слов
    cur.execute("SELECT COUNT(*) FROM words")
    if cur.fetchone()[0] == 0:
        words = [
            ('красный', 'red'),
            ('синий', 'blue'),
            ('зеленый', 'green'),
            ('желтый', 'yellow'),
            ('черный', 'black'),
            ('белый', 'white'),
            ('я', 'I'),
            ('ты', 'you'),
            ('он', 'he'),
            ('она', 'she')
        ]
        for rus, eng in words:
            cur.execute("INSERT INTO words (russian, english) VALUES (%s, %s)", (rus, eng))
    
    conn.commit()
    cur.close()
    conn.close()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Сохраняем пользователя в БД
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (telegram_id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING", 
                (user.id, user.first_name))
    conn.commit()
    cur.close()
    conn.close()
    
    await update.message.reply_text(
        f"Привет {user.first_name}!\n"
        "Я бот для изучения английского.\n\n"
        "Команды:\n"
        "/learn - Учить слова\n"
        "/add - Добавить свое слово\n"
        "/mywords - Мои слова\n"
        "/delete - Удалить слово"
    )

# Команда /learn - учить слова
async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cur = conn.cursor()
    
    # Берем 4 случайных слова
    cur.execute("SELECT russian, english FROM words ORDER BY RANDOM() LIMIT 4")
    words = cur.fetchall()
    
    if not words:
        await update.message.reply_text("Нет слов для изучения")
        return
    
    # Выбираем правильное
    correct = random.choice(words)
    question = correct[0]  # русское слово
    answer = correct[1]   # английское
    
    # Создаем кнопки с вариантами
    buttons = []
    for word in words:
        buttons.append([InlineKeyboardButton(word[1], callback_data=f"check_{word[1]}")])
    
    # Сохраняем правильный ответ
    context.user_data['correct'] = answer
    
    await update.message.reply_text(
        f"Как переводится: {question}?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    cur.close()
    conn.close()

# Проверка ответа
async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_answer = query.data.replace("check_", "")
    correct = context.user_data.get('correct', '')
    
    if user_answer == correct:
        await query.edit_message_text("✅ Правильно!")
    else:
        await query.edit_message_text(f"❌ Неправильно. Правильно: {correct}")

# Команда /add - добавить слово
async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Напиши слово и перевод через тире:\n"
        "Пример: собака-dog"
    )
    context.user_data['waiting_for_word'] = True

# Обработка добавления слова
async def save_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_word'):
        text = update.message.text
        if '-' in text:
            rus, eng = text.split('-', 1)
            rus, eng = rus.strip(), eng.strip()
            
            # Сохраняем в БД
            conn = get_db()
            cur = conn.cursor()
            
            # Находим ID пользователя
            cur.execute("SELECT id FROM users WHERE telegram_id = %s", (update.effective_user.id,))
            user = cur.fetchone()
            
            if user:
                # Сохраняем слово ТОЛЬКО для этого пользователя
                cur.execute(
                    "INSERT INTO my_words (user_id, russian, english) VALUES (%s, %s, %s)",
                    (user[0], rus, eng)
                )
                conn.commit()
                
                # Считаем сколько слов у пользователя
                cur.execute("SELECT COUNT(*) FROM my_words WHERE user_id = %s", (user[0],))
                count = cur.fetchone()[0]
                
                await update.message.reply_text(
                    f"✅ Слово добавлено!\n"
                    f"Теперь у тебя {count} слов"
                )
            else:
                await update.message.reply_text("Ошибка: пользователь не найден")
            
            cur.close()
            conn.close()
        
        context.user_data['waiting_for_word'] = False

# Команда /mywords - мои слова
async def my_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cur = conn.cursor()
    
    # Находим ID пользователя
    cur.execute("SELECT id FROM users WHERE telegram_id = %s", (update.effective_user.id,))
    user = cur.fetchone()
    
    if user:
        # Берем слова только этого пользователя
        cur.execute("SELECT id, russian, english FROM my_words WHERE user_id = %s", (user[0],))
        words = cur.fetchall()
        
        if words:
            text = "📚 Твои слова:\n\n"
            for word in words:
                text += f"{word[0]}. {word[1]} - {word[2]}\n"
            text += "\nЧтобы удалить: /delete номер"
        else:
            text = "У тебя пока нет своих слов. Добавь через /add"
    else:
        text = "Сначала напиши /start"
    
    await update.message.reply_text(text)
    cur.close()
    conn.close()

# Команда /delete - удалить слово
async def delete_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Напиши номер слова для удаления (см. в /mywords)\n"
        "Пример: 1"
    )
    context.user_data['waiting_for_delete'] = True

# Обработка удаления
async def process_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_delete'):
        try:
            word_id = int(update.message.text)
            
            conn = get_db()
            cur = conn.cursor()
            
            # Находим пользователя
            cur.execute("SELECT id FROM users WHERE telegram_id = %s", (update.effective_user.id,))
            user = cur.fetchone()
            
            if user:
                # Удаляем ТОЛЬКО слово этого пользователя
                cur.execute(
                    "DELETE FROM my_words WHERE id = %s AND user_id = %s",
                    (word_id, user[0])
                )
                conn.commit()
                
                if cur.rowcount > 0:
                    await update.message.reply_text("✅ Слово удалено")
                else:
                    await update.message.reply_text("❌ Не найдено такое слово")
            
            cur.close()
            conn.close()
            
        except ValueError:
            await update.message.reply_text("Напиши номер цифрой")
        
        context.user_data['waiting_for_delete'] = False

# Главная функция
def main():
    # Создаем таблицы при запуске
    create_tables()
    
    # Получаем токен бота
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Ошибка: добавь BOT_TOKEN в файл .env")
        return
    
    # Создаем приложение
    app = Application.builder().token(token).build()
    
    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("learn", learn))
    app.add_handler(CommandHandler("add", add_word))
    app.add_handler(CommandHandler("mywords", my_words))
    app.add_handler(CommandHandler("delete", delete_word))
    
    # Обработчики сообщений
    app.add_handler(CallbackQueryHandler(check_answer, pattern="^check_"))
    app.add_handler(MessageHandler(None, save_word))
    app.add_handler(MessageHandler(None, process_delete))
    
    # Запускаем бота
    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()
