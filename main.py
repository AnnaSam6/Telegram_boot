import logging
import random
import os
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключение к PostgreSQL
def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "english_bot_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres")
    )

# Создание таблиц
def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    # Таблица 1: Пользователи
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица 2: Общие слова
    cur.execute("""
        CREATE TABLE IF NOT EXISTS base_words (
            id SERIAL PRIMARY KEY,
            russian VARCHAR(100) NOT NULL,
            english VARCHAR(100) NOT NULL
        )
    """)
    
    # Таблица 3: Персональные слова
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_words (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            russian VARCHAR(100) NOT NULL,
            english VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Добавляем 10 базовых слов
    cur.execute("SELECT COUNT(*) FROM base_words")
    if cur.fetchone()[0] == 0:
        words = [
            ('красный', 'red'), ('синий', 'blue'), ('зеленый', 'green'),
            ('желтый', 'yellow'), ('черный', 'black'), ('белый', 'white'),
            ('я', 'I'), ('ты', 'you'), ('он', 'he'), ('она', 'she')
        ]
        for rus, eng in words:
            cur.execute("INSERT INTO base_words (russian, english) VALUES (%s, %s)", (rus, eng))
    
    conn.commit()
    cur.close()
    conn.close()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute(
        "INSERT INTO users (telegram_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (user.id, user.username)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! 🎯\n\n"
        "Команды:\n"
        "/learn - Учить слова (4 варианта)\n"
        "/add - Добавить слово\n"
        "/mywords - Мои слова\n"
        "/delete - Удалить слово\n"
        "/stats - Статистика"
    )

# /learn
async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cur = conn.cursor()
    
    # Берем 4 случайных слова
    cur.execute("SELECT russian, english FROM base_words ORDER BY RANDOM() LIMIT 4")
    words = cur.fetchall()
    
    if not words:
        await update.message.reply_text("Нет слов для изучения")
        return
    
    # Выбираем правильное
    correct = random.choice(words)
    question = correct[0]
    answer = correct[1]
    
    # Кнопки
    buttons = [[InlineKeyboardButton(w[1], callback_data=f"ans_{w[1]}")] for w in words]
    
    context.user_data['correct_answer'] = answer
    context.user_data['question'] = question
    
    await update.message.reply_text(
        f"📚 Как переводится: {question}?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    cur.close()
    conn.close()

# Проверка ответа
async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_answer = query.data.replace("ans_", "")
    correct = context.user_data.get('correct_answer', '')
    
    if user_answer == correct:
        await query.edit_message_text(f"✅ Правильно! {correct}")
    else:
        await query.edit_message_text(f"❌ Неправильно. Правильно: {correct}")

# /add
async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Напиши слово и перевод через тире:\n"
        "Пример: собака-dog"
    )
    return "WAITING_WORD"

# Сохранение слова
async def save_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if '-' in text:
        rus, eng = text.split('-', 1)
        rus, eng = rus.strip(), eng.strip()
        
        conn = get_db()
        cur = conn.cursor()
        
        # ID пользователя
        cur.execute("SELECT id FROM users WHERE telegram_id = %s", (update.effective_user.id,))
        user = cur.fetchone()
        
        if user:
            # Добавляем слово
            cur.execute(
                "INSERT INTO user_words (user_id, russian, english) VALUES (%s, %s, %s)",
                (user[0], rus, eng)
            )
            conn.commit()
            
            # Считаем слова
            cur.execute("SELECT COUNT(*) FROM user_words WHERE user_id = %s", (user[0],))
            count = cur.fetchone()[0]
            
            await update.message.reply_text(
                f"✅ Добавлено! У тебя {count} слов"
            )
        else:
            await update.message.reply_text("Ошибка")
        
        cur.close()
        conn.close()
    
    return ConversationHandler.END

# /mywords
async def my_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM users WHERE telegram_id = %s", (update.effective_user.id,))
    user = cur.fetchone()
    
    if user:
        cur.execute("SELECT id, russian, english FROM user_words WHERE user_id = %s", (user[0],))
        words = cur.fetchall()
        
        if words:
            text = "📖 Твои слова:\n\n"
            for word in words:
                text += f"{word[0]}. {word[1]} - {word[2]}\n"
            text += "\nУдалить: /delete номер"
        else:
            text = "Нет слов. Добавь через /add"
    else:
        text = "Напиши /start"
    
    await update.message.reply_text(text)
    cur.close()
    conn.close()

# /delete
async def delete_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши номер слова для удаления:")
    return "WAITING_DELETE"

# Удаление
async def process_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        word_id = int(update.message.text)
        
        conn = get_db()
        cur = conn.cursor()
        
        # ID пользователя
        cur.execute("SELECT id FROM users WHERE telegram_id = %s", (update.effective_user.id,))
        user = cur.fetchone()
        
        if user:
            # Удаляем ТОЛЬКО слово этого пользователя
            cur.execute(
                "DELETE FROM user_words WHERE id = %s AND user_id = %s",
                (word_id, user[0])
            )
            conn.commit()
            
            if cur.rowcount > 0:
                await update.message.reply_text("✅ Удалено")
            else:
                await update.message.reply_text("❌ Не найдено")
        
        cur.close()
        conn.close()
        
    except ValueError:
        await update.message.reply_text("Нужен номер")
    
    return ConversationHandler.END

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено")
    return ConversationHandler.END

def main():
    # Инициализируем БД
    init_db()
    
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Нет токена в .env")
        return
    
    app = Application.builder().token(token).build()
    
    # Обработчики
    from telegram.ext import ConversationHandler
    
    # Для /add
    add_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_word)],
        states={
            "WAITING_WORD": [MessageHandler(filters.TEXT & ~filters.COMMAND, save_word)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Для /delete
    delete_handler = ConversationHandler(
        entry_points=[CommandHandler("delete", delete_word)],
        states={
            "WAITING_DELETE": [MessageHandler(filters.TEXT & ~filters.COMMAND, process_delete)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("learn", learn))
    app.add_handler(CommandHandler("mywords", my_words))
    app.add_handler(add_handler)
    app.add_handler(delete_handler)
    app.add_handler(CallbackQueryHandler(check_answer, pattern="^ans_"))
    
    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
