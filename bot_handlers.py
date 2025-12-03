from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
import logging

# Состояния для ConversationHandler
ADD_WORD_RUSSIAN, ADD_WORD_ENGLISH, DELETE_WORD = range(3)

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, learning_service):
        self.service = learning_service
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        
        welcome_text = f"""
        👋 Привет, {user.first_name}!
        
        🎯 Добро пожаловать в <b>EnglishCard</b> - бота для изучения английских слов!
        
        📚 <b>Доступные команды:</b>
        /start - Начать работу с ботом
        /learn - Начать изучение слов
        /add_word - Добавить новое слово
        /delete_word - Удалить слово
        /stats - Показать статистику
        /help - Помощь
        
        🎮 Начните изучение слов с команды /learn!
        """
        
        await update.message.reply_html(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
        📖 <b>Помощь по использованию бота:</b>
        
        <b>Основные команды:</b>
        /learn - Начать тренировку. Бот покажет слово на русском и 4 варианта перевода на английском.
        
        <b>Работа со словарем:</b>
        /add_word - Добавить свое слово в персональный словарь
        /delete_word - Удалить слово из вашего словаря
        
        <b>Статистика:</b>
        /stats - Показать вашу статистику обучения
        
        <b>Пример добавления слова:</b>
        1. Нажмите /add_word
        2. Введите слово на русском
        3. Введите перевод на английском
        
        ❓ Если возникли проблемы - обратитесь к разработчику.
        """
        
        await update.message.reply_html(help_text)
    
    async def learn_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /learn - начало обучения"""
        question_data = self.service.get_question(update.effective_user.id)
        
        if not question_data:
            await update.message.reply_text(
                "📝 У вас пока нет слов для изучения. Добавьте слова через /add_word"
            )
            return
        
        # Сохраняем данные вопроса в контексте
        context.user_data['current_question'] = question_data
        
        # Создаем клавиатуру с вариантами ответов
        keyboard = [
            [KeyboardButton(option)] for option in question_data['options']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_html(
            question_data['question'],
            reply_markup=reply_markup
        )
    
    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ответа пользователя"""
        user_answer = update.message.text
        question_data = context.user_data.get('current_question')
        
        if not question_data:
            await update.message.reply_text(
                "Начните новую тренировку с /learn"
            )
            return
        
        # Проверяем ответ
        is_correct = self.service.check_answer(
            question_data['user_id'],
            question_data['word_id'],
            question_data['word_type'],
            user_answer
        )
        
        # Отправляем результат
        if is_correct:
            await update.message.reply_text(
                "✅ <b>Правильно!</b> Отличная работа!",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                f"❌ <b>Неправильно.</b> Правильный ответ: <b>{question_data['correct_answer']}</b>",
                parse_mode='HTML'
            )
        
        # Удаляем клавиатуру
        remove_keyboard = ReplyKeyboardMarkup([[]], resize_keyboard=True)
        await update.message.reply_text(
            "Продолжим? Нажмите /learn для следующего слова",
            reply_markup=remove_keyboard
        )
        
        # Очищаем текущий вопрос
        context.user_data.pop('current_question', None)
    
    async def add_word_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса добавления слова"""
        await update.message.reply_text(
            "📝 Введите слово на <b>русском</b> языке:",
            parse_mode='HTML'
        )
        return ADD_WORD_RUSSIAN
    
    async def add_word_russian(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение русского слова"""
        context.user_data['russian_word'] = update.message.text
        
        await update.message.reply_text(
            "📝 Теперь введите перевод на <b>английском</b> языке:",
            parse_mode='HTML'
        )
        return ADD_WORD_ENGLISH
    
    async def add_word_english(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение английского слова и сохранение"""
        russian_word = context.user_data['russian_word']
        english_word = update.message.text
        
        # Добавляем слово
        result = self.service.add_personal_word(
            update.effective_user.id,
            russian_word,
            english_word
        )
        
        # Получаем количество слов пользователя
        words_count = self.service.get_personal_words_count(update.effective_user.id)
        
        if result > 0:
            await update.message.reply_text(
                f"✅ Слово <b>{russian_word} - {english_word}</b> успешно добавлено!\n"
                f"📊 Теперь в вашем словаре: <b>{words_count}</b> слов.",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                f"⚠️ Слово <b>{russian_word} - {english_word}</b> уже есть в вашем словаре.",
                parse_mode='HTML'
            )
        
        # Очищаем временные данные
        context.user_data.pop('russian_word', None)
        
        return ConversationHandler.END
    
    async def delete_word_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса удаления слова"""
        await update.message.reply_text(
            "🗑️ Введите <b>ID слова</b>, которое хотите удалить.\n"
            "Для просмотра ваших слов используйте /my_words",
            parse_mode='HTML'
        )
        return DELETE_WORD
    
    async def delete_word_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удаление слова по ID"""
        try:
            word_id = int(update.message.text)
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите числовой ID слова."
            )
            return ConversationHandler.END
        
        # Удаляем слово
        result = self.service.delete_personal_word(
            update.effective_user.id,
            word_id
        )
        
        if result > 0:
            await update.message.reply_text(
                f"✅ Слово с ID <b>{word_id}</b> успешно удалено.",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                f"❌ Слово с ID <b>{word_id}</b> не найдено в вашем словаре.",
                parse_mode='HTML'
            )
        
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена операции"""
        await update.message.reply_text(
            "Операция отменена.",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
        )
        return ConversationHandler.END
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику"""
        user_id = update.effective_user.id
        
        # Получаем пользователя
        from database import Database
        db = Database()
        user = db.get_user(user_id)
        
        # Получаем статистику
        stats = db.execute_query(
            """SELECT 
                   SUM(correct_answers) as total_correct,
                   SUM(wrong_answers) as total_wrong,
                   COUNT(DISTINCT word_id) as words_learned
               FROM learning_stats 
               WHERE user_id = %s""",
            (user['id'],),
            fetchone=True
        )
        
        # Получаем количество персональных слов
        personal_words = db.get_user_words_count(user['id'])
        
        if stats['total_correct'] or stats['total_wrong']:
            total = stats['total_correct'] + stats['total_wrong']
            accuracy = (stats['total_correct'] / total * 100) if total > 0 else 0
            
            stats_text = f"""
            📊 <b>Ваша статистика:</b>
            
            ✅ Правильных ответов: {stats['total_correct']}
            ❌ Неправильных ответов: {stats['total_wrong']}
            🎯 Точность: {accuracy:.1f}%
            
            📝 Изучено слов: {stats['words_learned']}
            📚 Ваших слов: {personal_words}
            
            Продолжайте в том же духе! 💪
            """
        else:
            stats_text = """
            📊 <b>Ваша статистика:</b>
            
            У вас пока нет статистики.
            Начните обучение с /learn!
            """
        
        await update.message.reply_html(stats_text)
        
        db.close()
    
    async def show_my_words(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать слова пользователя"""
        from database import Database
        db = Database()
        
        user = db.get_user(update.effective_user.id)
        
        # Получаем слова пользователя
        words = db.execute_query(
            """SELECT id, russian, english, created_at 
               FROM user_words 
               WHERE user_id = %s 
               ORDER BY created_at DESC 
               LIMIT 50""",
            (user['id'],),
            fetchall=True
        )
        
        if words:
            words_text = "📚 <b>Ваши слова:</b>\n\n"
            for word in words:
                words_text += f"{word['id']}. {word['russian']} - <b>{word['english']}</b>\n"
            
            words_text += "\nДля удаления слова используйте /delete_word и введите ID слова"
        else:
            words_text = "📝 У вас пока нет персональных слов.\nДобавьте их через /add_word"
        
        await update.message.reply_html(words_text)
        
        db.close()
