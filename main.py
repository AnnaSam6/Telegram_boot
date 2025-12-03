import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler

from config import BOT_TOKEN
from services import LearningService
from bot_handlers import BotHandlers, ADD_WORD_RUSSIAN, ADD_WORD_ENGLISH, DELETE_WORD

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Запуск бота"""
    # Создаем сервис обучения
    learning_service = LearningService()
    
    # Создаем обработчики
    handlers = BotHandlers(learning_service)
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("learn", handlers.learn_command))
    application.add_handler(CommandHandler("stats", handlers.show_stats))
    application.add_handler(CommandHandler("my_words", handlers.show_my_words))
    
    # ConversationHandler для добавления слова
    add_word_conv = ConversationHandler(
        entry_points=[CommandHandler('add_word', handlers.add_word_start)],
        states={
            ADD_WORD_RUSSIAN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.add_word_russian)
            ],
            ADD_WORD_ENGLISH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.add_word_english)
            ],
        },
        fallbacks=[CommandHandler('cancel', handlers.cancel)]
    )
    
    # ConversationHandler для удаления слова
    delete_word_conv = ConversationHandler(
        entry_points=[CommandHandler('delete_word', handlers.delete_word_start)],
        states={
            DELETE_WORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.delete_word_confirm)
            ],
        },
        fallbacks=[CommandHandler('cancel', handlers.cancel)]
    )
    
    application.add_handler(add_word_conv)
    application.add_handler(delete_word_conv)
    
    # Обработчик ответов на вопросы
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_answer)
    )
    
    # Запуск бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
