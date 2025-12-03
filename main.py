import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update, context):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_html(
        f"👋 Привет, {user.first_name}!\n\n"
        f"Добро пожаловать в EnglishCard - бота для изучения английских слов!\n\n"
        f"📚 Доступные команды:\n"
        f"/start - Начало работы\n"
        f"/learn - Начать изучение\n"
        f"/add_word - Добавить слово\n"
        f"/delete_word - Удалить слово\n"
        f"/stats - Статистика\n"
        f"/help - Помощь"
    )

def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    
    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
    main()
