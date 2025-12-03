import logging
import random
import os
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
WAITING_WORD, WAITING_DELETE = range(2)

# Подключение к PostgreSQL
def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "english_bot_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres")
    )

# Создание ВСЕХ 4 таблиц
def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    # 1. Таблица пользователей
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. Таблица базовых слов (10 слов для всех)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS base_words (
            id SERIAL PRIMARY KEY,
            russian VARCHAR(100) NOT NULL,
            english VARCHAR(100) NOT NULL
        )
    """)
    
    # 3. Таблица персональных слов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_words (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            russian VARCHAR(100) NOT NULL,
            english VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 4. Таблица статистики (4-я таблица!)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS learning_stats (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            correct_answers INTEGER DEFAULT 0,
            wrong_answers INTEGER DEFAULT 0,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Добавляем 10 базовых слов если их нет
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
    print("✅ База данных создана (4 таблицы)")

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_db()
    cur = conn.cursor()
    
    # Регистрируем пользователя
    cur.execute(
        "INSERT INTO users (telegram_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (user.id, user.username)
    )
    
    # Создаем запись статистики
    cur.execute("SELECT id FROM users WHERE telegram_id = %s", (user.id,))
    user_id = cur.fetchone()[0]
    
    cur.execute(
        """INSERT INTO learning_stats (user_id) VALUES (%s) 
           ON CONFLICT (user_id) DO NOTHING""",
        (user_id,)
    )
    
    conn.commit()
    cur.close()
    conn.close()
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для изучения английских слов.\n\n"
        "📚 Команды:\n"
        "/learn - Учить слова (4 варианта ответа)\n"
        "/add - Добавить свое слово\n"
        "/mywords - Мои слова\n"
        "/delete - Удалить слово\n"
        "/stats - Моя статистика\n"
        "/help - Помощь"
    )

# Команда /learn - тест с 4 вариантами
async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cur = conn.cursor()
    
    # Берем 4 случайных слова из ОБЩИХ слов
    cur.execute("SELECT russian, english FROM base_words ORDER BY RANDOM() LIMIT 4")
    words = cur.fetchall()
    
    if not words:
        await update.message.reply_text("Пока нет слов для изучения")
        return
    
    # Выбираем правильный ответ
    correct_word = random.choice(words)
    question = correct_word[0]  # русское слово
    correct_answer = correct_word[1]  # английский перевод
    
    # Создаем 4 кнопки с вариантами
    buttons = []
    all_answers = [word[1] for word in words]  # все английские слова
    random.shuffle(all_answers)  # перемешиваем
    
    for answer in all_answers:
        buttons.append([InlineKeyboardButton(answer, callback_data=f"answer_{answer}")])
    
    # Сохраняем правильный ответ
    context.user_data['correct_answer'] = correct_answer
    context.user_data['question'] = question
    
    await update.message.reply_text(
        f"❓ Как переводится слово: <b>{question}</b>?",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    cur.close()
    conn.close()

# Проверка ответа и обновление статистики
async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_answer = query.data.replace("answer_", "")
    correct_answer = context.user_data.get('correct_answer', '')
    
    conn = get_db()
    cur = conn.cursor()
    
    # Находим ID пользователя
    cur.execute("SELECT id FROM users WHERE telegram_id = %s", (update.effective_user.id,))
    user = cur.fetchone()
    
    if user:
        user_id = user[0]
        
        # Обновляем статистику
        if user_answer == correct_answer:
            # Правильный ответ
            cur.execute("""
                UPDATE learning_stats 
                SET correct_answers = correct_answers + 1,
                    last_active = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (user_id,))
            await query.edit_message_text(f"✅ <b>Правильно!</b>\n{correct_answer}", parse_mode='HTML')
        else:
            # Неправильный ответ
            cur.execute("""
                UPDATE learning_stats 
                SET wrong_answers = wrong_answers + 1,
                    last_active = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (user_id,))
            await query.edit_message_text(
                f"❌ <b>Неправильно!</b>\nПравильный ответ: <b>{correct_answer}</b>",
                parse_mode='HTML'
            )
        
        conn.commit()
    
    cur.close()
    conn.close()

# Команда /add
async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Напиши слово на русском и перевод на английском через дефис:\n\n"
        "Пример: <code>собака-dog</code>\n"
        "Пример: <code>компьютер-computer</code>",
        parse_mode='HTML'
    )
    return WAITING_WORD

# Сохранение нового слова
async def save_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if '-' not in text:
        await update.message.reply_text("❌ Используй формат: слово-перевод")
        return ConversationHandler.END
    
    parts = text.split('-', 1)
    russian = parts[0].strip()
    english = parts[1].strip()
    
    if not russian or not english:
        await update.message.reply_text("❌ Оба слова должны быть не пустые")
        return ConversationHandler.END
    
    conn = get_db()
    cur = conn.cursor()
    
    # Находим ID пользователя
    cur.execute("SELECT id FROM users WHERE telegram_id = %s", (update.effective_user.id,))
    user = cur.fetchone()
    
    if user:
        user_id = user[0]
        
        # Добавляем слово ТОЛЬКО для этого пользователя
        cur.execute("""
            INSERT INTO user_words (user_id, russian, english)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, russian, english) DO NOTHING
        """, (user_id, russian, english))
        
        # Считаем сколько слов у пользователя
        cur.execute("SELECT COUNT(*) FROM user_words WHERE user_id = %s", (user_id,))
        count = cur.fetchone()[0]
        
        conn.commit()
        
        if cur.rowcount > 0:
            await update.message.reply_text(
                f"✅ Слово добавлено!\n"
                f"📊 Теперь у тебя <b>{count}</b> персональных слов",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("ℹ️ Это слово уже есть в твоем словаре")
    else:
        await update.message.reply_text("❌ Сначала напиши /start")
    
    cur.close()
    conn.close()
    return ConversationHandler.END

# Команда /mywords
async def my_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cur = conn.cursor()
    
    # Находим пользователя
    cur.execute("SELECT id FROM users WHERE telegram_id = %s", (update.effective_user.id,))
    user = cur.fetchone()
    
    if user:
        user_id = user[0]
        
        # Берем слова ТОЛЬКО этого пользователя
        cur.execute("""
            SELECT id, russian, english 
            FROM user_words 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """, (user_id,))
        
        words = cur.fetchall()
        
        if words:
            text = "📚 <b>Твои слова:</b>\n\n"
            for word in words:
                text += f"{word[0]}. {word[1]} - <b>{word[2]}</b>\n"
            
            text += "\n🗑️ Для удаления напиши /delete и номер слова"
        else:
            text = "📝 У тебя пока нет своих слов.\nДобавь через /add"
    else:
        text = "❌ Сначала напиши /start"
    
    await update.message.reply_text(text, parse_mode='HTML')
    
    cur.close()
    conn.close()

# Команда /delete
async def delete_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🗑️ Напиши номер слова для удаления (см. в /mywords):\n"
        "Например: <code>1</code>",
        parse_mode='HTML'
    )
    return WAITING_DELETE

# Удаление слова
async def process_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        word_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Нужно ввести номер цифрой")
        return ConversationHandler.END
    
    conn = get_db()
    cur = conn.cursor()
    
    # Находим пользователя
    cur.execute("SELECT id FROM users WHERE telegram_id = %s", (update.effective_user.id,))
    user = cur.fetchone()
    
    if user:
        user_id = user[0]
        
        # Удаляем ТОЛЬКО слово этого пользователя
        cur.execute("""
            DELETE FROM user_words 
            WHERE id = %s AND user_id = %s
        """, (word_id, user_id))
        
        conn.commit()
        
        if cur.rowcount > 0:
            await update.message.reply_text("✅ Слово удалено из твоего словаря")
        else:
            await update.message.reply_text("❌ Не найдено слово с таким номером")
    else:
        await update.message.reply_text("❌ Сначала напиши /start")
    
    cur.close()
    conn.close()
    return ConversationHandler.END

# Команда /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cur = conn.cursor()
    
    # Находим пользователя
    cur.execute("SELECT id FROM users WHERE telegram_id = %s", (update.effective_user.id,))
    user = cur.fetchone()
    
    if user:
        user_id = user[0]
        
        # Получаем статистику
        cur.execute("""
            SELECT correct_answers, wrong_answers 
            FROM learning_stats 
            WHERE user_id = %s
        """, (user_id,))
        
        stats_data = cur.fetchone()
        
        # Считаем персональные слова
        cur.execute("SELECT COUNT(*) FROM user_words WHERE user_id = %s", (user_id,))
        personal_words = cur.fetchone()[0]
        
        if stats_data:
            correct = stats_data[0] or 0
            wrong = stats_data[1] or 0
            total = correct + wrong
            
            if total > 0:
                accuracy = (correct / total) * 100
            else:
                accuracy = 0
            
            text = (
                f"📊 <b>Твоя статистика:</b>\n\n"
                f"✅ Правильных ответов: {correct}\n"
                f"❌ Неправильных ответов: {wrong}\n"
                f"🎯 Точность: {accuracy:.1f}%\n"
                f"📝 Персональных слов: {personal_words}"
            )
        else:
            text = "📈 Начни учить слова через /learn"
    else:
        text = "❌ Сначала напиши /start"
    
    await update.message.reply_text(text, parse_mode='HTML')
    
    cur.close()
    conn.close()

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ <b>Помощь по командам:</b>\n\n"
        "/learn - Тест с 4 вариантами ответов\n"
        "/add - Добавить свое слово (формат: слово-перевод)\n"
        "/mywords - Посмотреть свои слова\n"
        "/delete - Удалить слово по номеру\n"
        "/stats - Статистика обучения\n"
        "/help - Эта справка\n\n"
        "📌 Примеры:\n"
        "<code>/add собака-dog</code>\n"
        "<code>/add компьютер-computer</code>"
    )
    await update.message.reply_text(text, parse_mode='HTML')

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Операция отменена")
    return ConversationHandler.END

# Главная функция
def main():
    # Инициализируем БД (4 таблицы!)
    init_db()
    
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Ошибка: добавь BOT_TOKEN в файл .env")
        return
    
    # Создаем бота
    app = Application.builder().token(token).build()
    
    # ConversationHandler для добавления слов
    add_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_word)],
        states={
            WAITING_WORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_word)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # ConversationHandler для удаления слов
    delete_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("delete", delete_word)],
        states={
            WAITING_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_delete)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Регистрируем все команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("learn", learn))
    app.add_handler(CommandHandler("mywords", my_words))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(add_conv_handler)
    app.add_handler(delete_conv_handler)
    app.add_handler(CallbackQueryHandler(check_answer, pattern="^answer_"))
    
    print("✅ Бот запущен с PostgreSQL базой данных")
    app.run_polling()

if __name__ == "__main__":
    main()
