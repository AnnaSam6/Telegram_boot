"""
Telegram бот для изучения английского языка.
Основной модуль бота с обработчиками команд.
"""

import logging
import random
from datetime import datetime
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from config import BOT_TOKEN, ADMIN_IDS
from repository import Repository

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация репозитория
repo = Repository()

# Глобальные переменные для хранения состояния
user_states: Dict[int, Dict[str, Any]] = {}


def get_user_state(user_id: int) -> Dict[str, Any]:
    """Получение или создание состояния пользователя."""
    if user_id not in user_states:
        user_states[user_id] = {
            'quiz_active': False,
            'current_word': None,
            'quiz_options': [],
            'awaiting_word': False,
            'awaiting_translation': False,
            'awaiting_delete': False
        }
    return user_states[user_id]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    user_id = user.id
    
    # Добавляем пользователя в БД
    repo.add_user(
        user_id=user_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Приветственное сообщение
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот для изучения английских слов. Я помогу тебе:
• Учить слова с помощью квизов
• Добавлять свои слова
• Отслеживать прогресс

📚 Доступные команды:
/start - Начать работу с ботом
/learn - Начать изучение слов
/addword - Добавить новое слово
/mywords - Показать мои слова
/deleteword - Удалить слово
/stats - Статистика обучения
/help - Помощь по командам

Выбери команду из меню или напиши /learn чтобы начать учить слова! 🎯
    """
    
    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    help_text = """
📖 Помощь по командам:

/start - Начать работу с ботом
/learn - Начать изучение слов (квиз с 4 вариантами ответа)
/addword - Добавить новое слово в свой словарь
/mywords - Показать все ваши слова
/deleteword - Удалить слово из вашего словаря
/stats - Показать статистику обучения
/help - Эта справка

💡 Как работает бот:
1. Используйте /learn для начала квиза
2. Вам показывается русское слово и 4 варианта на английском
3. Выбираете правильный перевод
4. За правильные ответы растет ваша статистика

✏️ Добавление слов:
1. Используйте /addword
2. Введите английское слово
3. Введите русский перевод
4. Слово добавится в ваш личный словарь

🗑️ Удаление слов:
Используйте /deleteword и введите английское слово для удаления

Удачи в изучении английского! 🎓
    """
    
    await update.message.reply_text(help_text)


async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /learn - начало квиза."""
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    
    # Получаем случайное слово
    word = repo.get_random_standard_word()
    if not word:
        await update.message.reply_text("❌ В базе данных нет слов для изучения.")
        return
    
    # Получаем варианты ответов
    options = repo.get_random_word_options(word, 4)
    if len(options) < 4:
        await update.message.reply_text("❌ Недостаточно слов для создания квиза.")
        return
    
    # Сохраняем состояние
    state['quiz_active'] = True
    state['current_word'] = word
    state['quiz_options'] = options
    
    # Создаем клавиатуру с вариантами
    keyboard = []
    for option in options:
        keyboard.append([InlineKeyboardButton(
            option['english'],
            callback_data=f"quiz_{option['english']}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем вопрос
    question_text = f"📚 Переведите слово:\n\n🔹 *{word['russian']}*"
    await update.message.reply_text(
        question_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback'ов от квиза."""
    query = update.callback_query
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    
    await query.answer()
    
    if not state['quiz_active'] or not state['current_word']:
        await query.edit_message_text("❌ Сессия квиза завершена. Используйте /learn чтобы начать заново.")
        return
    
    # Получаем выбранный вариант
    selected_english = query.data.replace('quiz_', '')
    correct_word = state['current_word']
    is_correct = selected_english == correct_word['english']
    
    # Обновляем статистику
    repo.update_learning_stats(
        user_id=user_id,
        word_id=correct_word['id'],
        word_type='standard',
        is_correct=is_correct
    )
    
    # Формируем ответ
    if is_correct:
        result_text = "✅ *Правильно!* 🎉\n\n"
        result_text += f"*{correct_word['russian']}* = *{correct_word['english']}*"
    else:
        result_text = "❌ *Неправильно!*\n\n"
        result_text += f"Правильный ответ: *{correct_word['english']}*\n"
        result_text += f"*{correct_word['russian']}* = *{correct_word['english']}*"
    
    # Добавляем кнопку для следующего слова
    keyboard = [[InlineKeyboardButton("➡️ Следующее слово", callback_data="next_word")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def next_word_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для перехода к следующему слову."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    await query.answer()
    
    # Получаем новое случайное слово
    word = repo.get_random_standard_word()
    if not word:
        await query.edit_message_text("❌ В базе данных нет слов для изучения.")
        return
    
    # Получаем варианты ответов
    options = repo.get_random_word_options(word, 4)
    if len(options) < 4:
        await query.edit_message_text("❌ Недостаточно слов для создания квиза.")
        return
    
    # Обновляем состояние
    state = get_user_state(user_id)
    state['current_word'] = word
    state['quiz_options'] = options
    
    # Создаем новую клавиатуру
    keyboard = []
    for option in options:
        keyboard.append([InlineKeyboardButton(
            option['english'],
            callback_data=f"quiz_{option['english']}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем новый вопрос
    question_text = f"📚 Переведите слово:\n\n🔹 *{word['russian']}*"
    await query.edit_message_text(
        question_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def addword_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /addword - начало добавления слова."""
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    
    state['awaiting_word'] = True
    state['awaiting_translation'] = False
    state['awaiting_delete'] = False
    
    await update.message.reply_text(
        "✏️ *Добавление нового слова*\n\n"
        "Введите английское слово:",
        parse_mode='Markdown'
    )


async def deleteword_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /deleteword - удаление слова."""
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    
    # Получаем слова пользователя
    user_words = repo.get_user_words(user_id)
    
    if not user_words:
        await update.message.reply_text("📭 У вас пока нет своих слов для удаления.")
        return
    
    state['awaiting_word'] = False
    state['awaiting_translation'] = False
    state['awaiting_delete'] = True
    
    # Показываем список слов для удаления
    words_list = "\n".join([f"• {word['english']} - {word['russian']}" 
                           for word in user_words[:10]])  # Показываем первые 10
    
    await update.message.reply_text(
        f"🗑️ *Удаление слова*\n\n"
        f"Ваши слова:\n{words_list}\n\n"
        f"Введите английское слово для удаления:",
        parse_mode='Markdown'
    )


async def mywords_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /mywords - показать слова пользователя."""
    user_id = update.effective_user.id
    
    # Получаем слова пользователя
    user_words = repo.get_user_words(user_id)
    word_count = repo.get_user_word_count(user_id)
    
    if not user_words:
        await update.message.reply_text("📭 У вас пока нет своих слов. Используйте /addword чтобы добавить.")
        return
    
    # Формируем список слов
    words_text = f"📚 *Ваши слова* ({word_count} слов):\n\n"
    
    for i, word in enumerate(user_words[:50], 1):  # Ограничиваем 50 словами
        date_str = datetime.strptime(word['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
        words_text += f"{i}. *{word['english']}* - {word['russian']}"
        if word.get('category'):
            words_text += f" ({word['category']})"
        words_text += f" - добавлено {date_str}\n"
    
    if len(user_words) > 50:
        words_text += f"\n... и еще {len(user_words) - 50} слов"
    
    await update.message.reply_text(words_text, parse_mode='Markdown')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /stats - статистика обучения."""
    user_id = update.effective_user.id
    
    # Получаем статистику
    stats = repo.get_user_stats(user_id)
    
    # Формируем текст статистики
    stats_text = f"📊 *Статистика обучения*\n\n"
    stats_text += f"👤 Пользователь: {update.effective_user.first_name}\n"
    stats_text += f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}\n\n"
    
    stats_text += f"🎯 *Общая статистика:*\n"
    stats_text += f"• Изучено слов: {stats['words_learned']}\n"
    stats_text += f"• Ваших слов: {stats['user_words_count']}\n"
    stats_text += f"• Правильных ответов: {stats['total_correct']}/{stats['total_attempts']}\n"
    stats_text += f"• Успешность: {stats['success_rate']}%\n\n"
    
    stats_text += f"📈 *Сегодня:*\n"
    stats_text += f"• Вопросов: {stats['today_questions']}\n"
    stats_text += f"• Правильных: {stats['today_correct']}\n"
    
    if stats['today_questions'] > 0:
        today_rate = round((stats['today_correct'] / stats['today_questions']) * 100, 1)
        stats_text += f"• Успешность: {today_rate}%\n"
    
    stats_text += f"\n💪 Продолжайте в том же духе!"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений."""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    state = get_user_state(user_id)
    
    # Если пользователь добавляет слово
    if state['awaiting_word'] and not state['awaiting_translation']:
        if len(text.split()) > 3:
            await update.message.reply_text("❌ Слишком длинный текст. Введите одно английское слово:")
            return
        
        state['english_word'] = text.lower()
        state['awaiting_word'] = False
        state['awaiting_translation'] = True
        
        await update.message.reply_text(
            f"Английское слово: *{text}*\n\n"
            f"Теперь введите перевод на русский:",
            parse_mode='Markdown'
        )
        return
    
    # Если пользователь вводит перевод
    elif state['awaiting_translation']:
        english_word = state.get('english_word', '')
        
        if not english_word:
            state['awaiting_translation'] = False
            await update.message.reply_text("❌ Ошибка. Начните заново с /addword")
            return
        
        # Добавляем слово в БД
        success, message = repo.add_user_word(
            user_id=user_id,
            english=english_word,
            russian=text
        )
        
        # Сбрасываем состояние
        state['awaiting_word'] = False
        state['awaiting_translation'] = False
        state['english_word'] = None
        
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    # Если пользователь удаляет слово
    elif state['awaiting_delete']:
        success, message = repo.delete_user_word(user_id=user_id, english=text.lower())
        
        # Сбрасываем состояние
        state['awaiting_delete'] = False
        
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    # Если это обычное сообщение
    else:
        await update.message.reply_text(
            "🤔 Я не понимаю эту команду.\n\n"
            "Используйте /help чтобы увидеть список доступных команд."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок."""
    logger.error(f"Ошибка при обработке обновления: {context.error}")
    
    if update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз."
        )


def main() -> None:
    """Основная функция запуска бота."""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("learn", learn_command))
    application.add_handler(CommandHandler("addword", addword_command))
    application.add_handler(CommandHandler("deleteword", deleteword_command))
    application.add_handler(CommandHandler("mywords", mywords_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Регистрируем обработчики callback'ов
    application.add_handler(CallbackQueryHandler(quiz_callback, pattern="^quiz_"))
    application.add_handler(CallbackQueryHandler(next_word_callback, pattern="^next_word"))
    
    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
