import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from config import BOT_TOKEN
from database import Database
from config import BOT_TOKEN, ADMIN_IDS 
from database import Database  
from repository import Repository 
# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database()

# Словари для хранения состояния пользователей
user_states = {}  # {user_id: {'expecting_english': True/False, 'expecting_russian': True/False}}

# ========== КОМАНДЫ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    
    # Добавляем пользователя в БД
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user.id, user.username, user.first_name)
    )
    conn.commit()
    conn.close()
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот для изучения английских слов!

📚 Доступные команды:
/start - Начать работу
/learn - Учить слова (квиз)
/addword - Добавить своё слово
/mywords - Мои слова
/deleteword - Удалить слово
/help - Помощь

Нажми /learn чтобы начать учить слова! 🎯
    """
    
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = """
📖 Помощь по командам:

/start - Начать работу
/learn - Учить слова (4 варианта ответа)
/addword - Добавить своё слово
/mywords - Показать мои слова
/deleteword - Удалить моё слово
/help - Эта справка

💡 Как работает:
1. /learn - начинается квиз
2. Показывается русское слово
3. Выбираете правильный английский вариант
4. Учите и запоминаете!

✏️ Добавить слово:
1. /addword
2. Введите английское слово
3. Введите русский перевод

🗑️ Удалить слово:
1. /deleteword
2. Введите английское слово
    """
    await update.message.reply_text(help_text)

async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /learn - начало квиза"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Получаем случайное слово
    cursor.execute("SELECT english, russian FROM standard_words ORDER BY RANDOM() LIMIT 1")
    word = cursor.fetchone()
    
    if not word:
        await update.message.reply_text("❌ Нет слов для изучения")
        conn.close()
        return
    
    correct_word = dict(word)
    
    # Получаем 3 неправильных варианта
    cursor.execute(
        "SELECT english FROM standard_words WHERE english != ? ORDER BY RANDOM() LIMIT 3",
        (correct_word['english'],)
    )
    wrong_options = [row['english'] for row in cursor.fetchall()]
    
    conn.close()
    
    # Создаем 4 варианта (1 правильный + 3 неправильных)
    options = wrong_options + [correct_word['english']]
    random.shuffle(options)
    
    # Создаем кнопки
    keyboard = []
    for option in options:
        keyboard.append([InlineKeyboardButton(option, callback_data=f"quiz_{option}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Сохраняем правильный ответ для проверки
    context.user_data['correct_answer'] = correct_word['english']
    context.user_data['russian_word'] = correct_word['russian']
    
    await update.message.reply_text(
        f"📚 Переведите слово:\n\n🔹 *{correct_word['russian']}*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ответов на квиз"""
    query = update.callback_query
    await query.answer()
    
    selected = query.data.replace('quiz_', '')
    correct = context.user_data.get('correct_answer', '')
    russian = context.user_data.get('russian_word', '')
    
    if selected == correct:
        await query.edit_message_text(
            f"✅ *Правильно!*\n\n*{russian}* = *{correct}*",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            f"❌ *Неправильно!*\n\nПравильный ответ: *{correct}*\n*{russian}* = *{correct}*",
            parse_mode='Markdown'
        )
    
    # Кнопка для следующего слова
    keyboard = [[InlineKeyboardButton("➡️ Следующее слово", callback_data="next_word")]]
    await query.message.reply_text(
        "Хотите продолжить?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def next_word_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для следующего слова"""
    query = update.callback_query
    await query.answer()
    
    # Удаляем предыдущее сообщение
    await query.delete_message()
    
    # Запускаем новый квиз
    await learn_with_message(query.message, context)

async def learn_with_message(message, context):
    """Вспомогательная функция для запуска квиза"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT english, russian FROM standard_words ORDER BY RANDOM() LIMIT 1")
    word = cursor.fetchone()
    
    if not word:
        await message.reply_text("❌ Нет слов для изучения")
        conn.close()
        return
    
    correct_word = dict(word)
    
    cursor.execute(
        "SELECT english FROM standard_words WHERE english != ? ORDER BY RANDOM() LIMIT 3",
        (correct_word['english'],)
    )
    wrong_options = [row['english'] for row in cursor.fetchall()]
    
    conn.close()
    
    options = wrong_options + [correct_word['english']]
    random.shuffle(options)
    
    keyboard = []
    for option in options:
        keyboard.append([InlineKeyboardButton(option, callback_data=f"quiz_{option}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.user_data['correct_answer'] = correct_word['english']
    context.user_data['russian_word'] = correct_word['russian']
    
    await message.reply_text(
        f"📚 Переведите слово:\n\n🔹 *{correct_word['russian']}*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def addword(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /addword"""
    user_id = update.effective_user.id
    user_states[user_id] = {'expecting_english': True}
    
    await update.message.reply_text(
        "✏️ *Добавление нового слова*\n\nВведите английское слово:",
        parse_mode='Markdown'
    )

async def deleteword(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /deleteword"""
    user_id = update.effective_user.id
    user_states[user_id] = {'expecting_delete': True}
    
    # Показываем слова пользователя
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT english, russian FROM user_words WHERE user_id = ?",
        (user_id,)
    )
    words = cursor.fetchall()
    conn.close()
    
    if words:
        words_list = "\n".join([f"• {w['english']} - {w['russian']}" for w in words[:5]])
        text = f"🗑️ *Удаление слова*\n\nВаши слова:\n{words_list}\n\nВведите английское слово для удаления:"
    else:
        text = "📭 У вас нет своих слов.\nВведите английское слово для удаления (если добавите потом):"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def mywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /mywords"""
    user_id = update.effective_user.id
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT english, russian, created_at FROM user_words WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    words = cursor.fetchall()
    conn.close()
    
    if not words:
        await update.message.reply_text("📭 У вас пока нет своих слов. Используйте /addword чтобы добавить.")
        return
    
    text = f"📚 *Ваши слова* ({len(words)}):\n\n"
    for i, word in enumerate(words, 1):
        text += f"{i}. *{word['english']}* - {word['russian']}\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик всех текстовых сообщений"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_states:
        await update.message.reply_text("Используйте команды из меню или /help")
        return
    
    state = user_states[user_id]
    
    # Добавление слова
    if state.get('expecting_english'):
        # Пользователь ввел английское слово
        state['english'] = text.lower()
        state['expecting_english'] = False
        state['expecting_russian'] = True
        
        await update.message.reply_text(
            f"Английское слово: *{text}*\n\nТеперь введите перевод на русский:",
            parse_mode='Markdown'
        )
    
    elif state.get('expecting_russian'):
        # Пользователь ввел русский перевод
        english_word = state.get('english', '')
        
        if not english_word:
            await update.message.reply_text("Ошибка. Начните заново: /addword")
            del user_states[user_id]
            return
        
        # Добавляем слово в БД
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO user_words (user_id, english, russian) VALUES (?, ?, ?)",
                (user_id, english_word, text)
            )
            conn.commit()
            
            # Считаем сколько слов у пользователя
            cursor.execute(
                "SELECT COUNT(*) as count FROM user_words WHERE user_id = ?",
                (user_id,)
            )
            count = cursor.fetchone()['count']
            
            await update.message.reply_text(
                f"✅ Слово добавлено!\n\n*{english_word}* - {text}\n\nВсего ваших слов: *{count}*",
                parse_mode='Markdown'
            )
            
        except sqlite3.IntegrityError:
            await update.message.reply_text(
                f"❌ Слово *{english_word}* уже есть в вашем словаре",
                parse_mode='Markdown'
            )
        
        finally:
            conn.close()
            del user_states[user_id]
    
    # Удаление слова
    elif state.get('expecting_delete'):
        word_to_delete = text.lower()
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM user_words WHERE user_id = ? AND english = ?",
            (user_id, word_to_delete)
        )
        deleted = cursor.rowcount > 0
        conn.commit()
        
        # Считаем оставшиеся слова
        cursor.execute(
            "SELECT COUNT(*) as count FROM user_words WHERE user_id = ?",
            (user_id,)
        )
        remaining = cursor.fetchone()['count']
        conn.close()
        
        if deleted:
            await update.message.reply_text(
                f"✅ Слово *{word_to_delete}* удалено!\n\nОсталось слов: *{remaining}*",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ Слово *{word_to_delete}* не найдено в вашем словаре",
                parse_mode='Markdown'
            )
        
        del user_states[user_id]
    
    else:
        await update.message.reply_text("Используйте команды из меню или /help")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    
    if update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз."
        )

def main() -> None:
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("learn", learn))
    application.add_handler(CommandHandler("addword", addword))
    application.add_handler(CommandHandler("deleteword", deleteword))
    application.add_handler(CommandHandler("mywords", mywords))
    
    # Регистрируем обработчики кнопок
    application.add_handler(CallbackQueryHandler(quiz_callback, pattern="^quiz_"))
    application.add_handler(CallbackQueryHandler(next_word_callback, pattern="^next_word"))
    
    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    print("🤖 Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
